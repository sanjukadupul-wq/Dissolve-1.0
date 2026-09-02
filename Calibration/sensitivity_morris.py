#!/usr/bin/env python3
"""
Morris (Elementary Effects) global sensitivity analysis of Dissolve's 8
kinetic/transport parameters, run against the real dissolve.edp solver.

Ported from the original BioDeg project's sensitivity_analysis.py to this
repo's dissolve.edp CLI. The SALib problem definition (parameter names,
bounds, num_vars) and Morris settings (trajectories, levels) are UNCHANGED
from the original -- only flag names, the solver entry point, launcher
command, and stdout-parsing patterns were updated to match the current
codebase. See calibrate_bayesian.py's docstring for the full flag-mapping
table (mesh/k1/k2/k_orr/final_time/time_step/redistance_time/save_each/
output-file flags all map the same way here).

Requirements (not part of this project's core dependencies -- install
separately): pandas, numpy, matplotlib, seaborn (optional), SALib, rich.

Usage (run from Src Codes/, with a mesh available):
    python3 calibration/sensitivity_morris.py
    CALIB_LAUNCHER=m3 python3 calibration/sensitivity_morris.py   # on an M3 SLURM job

Total simulations = r * (k + 1) = 5 * (8 + 1) = 45 runs.
"""

import os
import subprocess
import re
import pandas as pd
import numpy as np
import time
import datetime
import json
import glob
from pathlib import Path
import matplotlib.pyplot as plt
try:
    import seaborn as sns
except ImportError:
    sns = None
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich import box
from SALib.sample import morris
from SALib.analyze import morris as analyze

console = Console()

# ---------------------------------------------------------------------------
# Fixed run configuration
# ---------------------------------------------------------------------------
WORKDIR = Path(__file__).resolve().parent.parent / "Src Codes"  # solver root
# (this script itself lives in Calibration/, a sibling of Src Codes/ -- moved
# out of Src Codes/calibration/, hence the extra "/ Src Codes" here)
MESH_FILE = os.environ.get("CALIB_MESH", "cylinder_10x2_scaffold_in_box.mesh")  # supply this

CORES = int(os.environ.get("SLURM_NTASKS", os.environ.get("CALIB_NP", "8")))
FINAL_TIME = 24.0
TIME_STEP = 1.0
REDISTANCE_TIME = 1.0

# Morris Method Settings (unchanged from the original)
NUM_TRAJECTORIES = 5  # r=5 -> 5*(8+1) = 45 simulations

timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
RESULTS_DIR = str(WORKDIR / "output_sensitivity" / f"sensitivity_{timestamp}")
os.makedirs(RESULTS_DIR, exist_ok=True)
DEFAULT_OUTPUT = str(WORKDIR / "output_sensitivity" / "MassLoss_Sensitivity.txt")
CHECKPOINT_FILE = str(WORKDIR / "output_sensitivity" / "sensitivity_checkpoint.json")

# ---------------------------------------------------------------------------
# Launcher: "local" (default) runs ff-mpirun directly. "m3" runs inside an
# already-allocated SLURM job via srun+singularity -- same pattern as
# calibrate_kinetics.py / calibrate_bayesian.py.
# ---------------------------------------------------------------------------
LAUNCHER = os.environ.get("CALIB_LAUNCHER", "local")
SIF_PATH = os.environ.get("CALIB_SIF_PATH", str(Path.home() / "software" / "freefem.sif"))


def build_command(k1, k2, k_orr, d_o2, initial_o2, d_zn, d_cl, d_oh):
    """Parameter names here match the SALib problem definition below
    (kept unchanged from the original); mapped to the current solver's
    flag names on the actual CLI."""
    out_rel = os.path.relpath(DEFAULT_OUTPUT, WORKDIR)
    dissolve_args = [
        "-input_mesh", MESH_FILE,
        "-k_f", str(k1), "-k_d", str(k2), "-k_orr", str(k_orr),
        "-diff_o2", str(d_o2), "-o2_initial", str(initial_o2),
        "-diff_zn", str(d_zn), "-diff_cl", str(d_cl), "-diff_oh", str(d_oh),
        "-sim_duration", str(FINAL_TIME), "-dt_hours", str(TIME_STEP),
        "-redistance_interval", str(REDISTANCE_TIME), "-save_interval", "24",
        "-results_file", out_rel,
        "-emit_vtk", "0", "-dump_final_state", "0", "-export_geometry", "0",
    ]
    if LAUNCHER == "m3":
        return (["srun", "--mpi=pmi2", "-n", str(CORES),
                  "singularity", "exec", SIF_PATH,
                  "FreeFem++-mpi", "-nw", "dissolve.edp", "-v", "0"] + dissolve_args)
    else:
        return (["nice", "-n", "10", "ff-mpirun", "-np", str(CORES), "dissolve.edp", "-nw", "-v", "0"] + dissolve_args)


# ---------------------------------------------------------------------------
# Experimental data -- inline, matching calibrate_kinetics.py's checkpoints
# (this repo has no experimental_data.xlsx export; the original external
# CSV dependency is replaced with the same values used elsewhere in this
# project, restricted to checkpoints within FINAL_TIME=24h).
# ---------------------------------------------------------------------------
_ALL_EXP = pd.DataFrame({
    "TimeHours": [24, 72, 168, 336, 672],
    "MassLossPercent": [0.045, 0.105, 0.209, 0.254, 0.31],
})
EXP_DATA = _ALL_EXP[_ALL_EXP["TimeHours"] <= FINAL_TIME].reset_index(drop=True)
if EXP_DATA.empty:
    console.print("[bold red]CRITICAL: No experimental checkpoints fall within FINAL_TIME. "
                   "RMSE would be computed against nothing.[/bold red]")

# --- Define Problem (SALib format, UNCHANGED from the original) ---
problem = {
    'num_vars': 8,
    'names': ['k1', 'k2', 'k_orr', 'd_o2', 'initial_o2', 'd_zn', 'd_cl', 'd_oh'],
    'bounds': [
        [50.0, 200.0],      # k1
        [1.0, 50.0],        # k2
        [0.1, 5.0],         # k_orr
        [5.0, 20.0],        # d_o2
        [1e-9, 1e-7],       # initial_o2
        [1.5, 5.0],         # d_zn (Default ~3.38)
        [5.0, 15.0],        # d_cl (Default ~9.7)
        [15.0, 35.0]        # d_oh (Default ~25.45)
    ]
}


# --- Checkpoint Management ---
def load_checkpoint():
    if not os.path.exists(CHECKPOINT_FILE):
        return {}
    data = {}
    try:
        with open(CHECKPOINT_FILE, 'r') as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    if 'index' in entry:
                        data[entry['index']] = entry['result']
        console.print(f"[bold green]Resuming from checkpoint: Found {len(data)} completed runs.[/bold green]")
        return data
    except Exception as e:
        console.print(f"[bold red]Error loading checkpoint:[/bold red] {e}")
        return {}


def save_checkpoint_entry(index, params, result):
    entry = {"index": index, "params": params, "result": result}
    with open(CHECKPOINT_FILE, 'a') as f:
        f.write(json.dumps(entry) + "\n")


# --- Simulation Runner ---
def run_simulation(index, params):
    k1, k2, k_orr, d_o2, initial_o2, d_zn, d_cl, d_oh = params

    param_text = f"""[cyan]k1[/cyan]         = {k1:.4f}
[cyan]k2[/cyan]         = {k2:.4f}
[cyan]k_orr[/cyan]      = {k_orr:.4f}
[cyan]d_o2[/cyan]       = {d_o2:.4f}
[cyan]d_zn[/cyan]       = {d_zn:.4f}
[cyan]d_cl[/cyan]       = {d_cl:.4f}
[cyan]d_oh[/cyan]       = {d_oh:.4f}
[cyan]init_o2[/cyan]    = {initial_o2:.2e}"""
    console.print(Panel(param_text, title=f"Run {index}", border_style="blue", box=box.ROUNDED))

    time.sleep(2)  # brief cooldown between MPI launches

    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "1"

    cmd = build_command(k1, k2, k_orr, d_o2, initial_o2, d_zn, d_cl, d_oh)
    rmse = 1e9

    # dissolve.edp prints "Time: <t>h  (...)    Step: ..." -- extract the
    # numeric value with a regex rather than the original's naive split(),
    # since the current console format has an "h" suffix and a parenthetical
    # duration that would break float() on the raw substring.
    time_re = re.compile(r"Time:\s*([\d.eE+-]+)h")

    with Progress(
        SpinnerColumn("dots", style="bold magenta"),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[bold green]Simulating...[/bold green]", total=None)
        try:
            if os.path.exists(DEFAULT_OUTPUT):
                os.remove(DEFAULT_OUTPUT)

            process = subprocess.Popen(cmd, cwd=WORKDIR, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, bufsize=1, env=env)

            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    m = time_re.search(line)
                    if m:
                        progress.update(task, description=f"[bold green]Simulating... t={m.group(1)}h[/bold green]")

            stdout, stderr = process.communicate()

            if process.returncode != 0:
                console.print(f"[bold red]Simulation Failed! Return code: {process.returncode}[/bold red]")
                console.print(Panel(stdout, title="STDOUT", style="red"))
                console.print(Panel(stderr, title="STDERR", style="red"))
                return 1e9

            if not os.path.exists(DEFAULT_OUTPUT):
                console.print("[bold red]Output file not found![/bold red]")
                return 1e9

            sim_data = pd.read_csv(DEFAULT_OUTPUT, sep="\t")
            sim_data.to_csv(f"{RESULTS_DIR}/trace_{index}.csv", index=False)

            if EXP_DATA.empty:
                return 1e9
            check_times = EXP_DATA['TimeHours'].values
            target_mass_loss = EXP_DATA['MassLossPercent'].values
            interp_mass_loss = np.interp(check_times, sim_data['TimeHours'], sim_data['MassLossPercent'])
            rmse = np.sqrt(np.mean((interp_mass_loss - target_mass_loss) ** 2))

            console.print(f"  -> RMSE: {rmse:.4f}")
            return rmse

        except Exception as e:
            console.print(f"[bold red]Error running simulation:[/bold red] {e}")
            return 1e9


# --- Main Logic ---
console.print(Panel.fit("[bold white]Sensitivity Analysis (Morris Method)[/bold white]", style="bold magenta"))

# 1. Generate Samples: N = r * (D + 1)
X = morris.sample(problem, NUM_TRAJECTORIES, num_levels=4)
num_samples = len(X)
console.print(f"Generated {num_samples} parameter sets (using {NUM_TRAJECTORIES} trajectories).")

# 2. Run Simulations
Y = np.zeros(num_samples)
checkpoint = load_checkpoint()

for i, param_set in enumerate(X):
    if i in checkpoint:
        console.print(f"[dim]Skipping run {i} (already in checkpoint)[/dim]")
        Y[i] = checkpoint[i]
    else:
        try:
            res = run_simulation(i + 1, param_set)
        except KeyboardInterrupt:
            console.print("[bold yellow]Interrupted by user. Saving checkpoint and exiting...[/bold yellow]")
            break
        Y[i] = res
        save_checkpoint_entry(i, list(param_set), res)

# 3. Analyze Results
console.print(Panel("[bold cyan]Analyzing Sensitivity...[/bold cyan]"))

try:
    Si = analyze.analyze(problem, X, Y, conf_level=0.95, print_to_console=False)

    results_list = []
    for idx, name in enumerate(Si['names']):
        results_list.append({
            'Parameter': name,
            'Mu_Star': Si['mu_star'][idx],
            'Sigma': Si['sigma'][idx],
            'Mu': Si['mu'][idx]
        })

    df_sensitivity = pd.DataFrame(results_list).sort_values(by='Mu_Star', ascending=False)
    console.print(df_sensitivity)
    df_sensitivity.to_csv(f"{RESULTS_DIR}/sensitivity_metrics.csv", index=False)

    # 1. Bar Chart: Mu*
    plt.figure(figsize=(10, 6))
    if sns:
        sns.barplot(data=df_sensitivity, x='Parameter', y='Mu_Star', palette='viridis')
    else:
        plt.bar(df_sensitivity['Parameter'], df_sensitivity['Mu_Star'])
    plt.title('Parameter Impact Ranking (Morris Mu*)')
    plt.ylabel('Mean Absolute Effect (Mu*)')
    plt.grid(axis='y', alpha=0.3)
    plt.savefig(f"{RESULTS_DIR}/plot_ranking.png", dpi=300)
    plt.close()

    # 2. Scatter: Mu* vs Sigma
    plt.figure(figsize=(8, 8))
    plt.scatter(df_sensitivity['Mu_Star'], df_sensitivity['Sigma'], s=100, c='red', edgecolors='k')
    for _, row in df_sensitivity.iterrows():
        plt.text(row['Mu_Star'] + 0.05, row['Sigma'], row['Parameter'], fontsize=12)
    plt.title('Parameter Nature: Impact vs. Interaction')
    plt.xlabel('Impact (Mu*)')
    plt.ylabel('Interaction/Non-Linearity (Sigma)')
    plt.grid(True, linestyle='--', alpha=0.5)
    max_val = max(df_sensitivity['Mu_Star'].max(), df_sensitivity['Sigma'].max())
    plt.plot([0, max_val], [0, max_val], 'k--', alpha=0.2, label='1:1 Line')
    plt.savefig(f"{RESULTS_DIR}/plot_nature.png", dpi=300)
    plt.close()

    # 3. Spaghetti Plot (Ensemble vs Experiment)
    plt.figure(figsize=(10, 6))
    if not EXP_DATA.empty:
        plt.scatter(EXP_DATA['TimeHours'], EXP_DATA['MassLossPercent'], label='Experimental Data', color='red', s=100, zorder=100)
    for tf in glob.glob(f"{RESULTS_DIR}/trace_*.csv"):
        try:
            df_trace = pd.read_csv(tf)
            plt.plot(df_trace['TimeHours'], df_trace['MassLossPercent'], color='blue', alpha=0.1, linewidth=1)
        except Exception:
            pass
    plt.plot([], [], color='blue', alpha=0.5, label='Simulation Ensemble')
    plt.title('Model Envelope vs Experiment (Sensitivity Runs)')
    plt.xlabel('Time (Hours)')
    plt.ylabel('Mass Loss (%)')
    plt.legend()
    plt.grid(True, alpha=0.3)
    plt.savefig(f"{RESULTS_DIR}/plot_envelope.png", dpi=300)
    plt.close()

    # HTML Report
    html_content = f"""
    <html>
    <head>
        <title>Sensitivity Analysis - {timestamp}</title>
        <style>
            body {{ font-family: 'Segoe UI', Arial, sans-serif; margin: 40px; color: #333; }}
            h1 {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
            h2 {{ color: #e67e22; margin-top: 30px; }}
            table {{ border-collapse: collapse; width: 100%; margin-top: 20px; }}
            th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
            th {{ background-color: #f2f2f2; }}
            tr:nth-child(even) {{ background-color: #f9f9f9; }}
            img {{ max-width: 100%; margin: 20px 0; border: 1px solid #eee; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
            .summary {{ background: #e8f6f3; padding: 20px; border-radius: 8px; border-left: 5px solid #1abc9c; }}
        </style>
    </head>
    <body>
        <h1>Sensitivity Analysis Report</h1>
        <p><strong>Date:</strong> {datetime.datetime.now()}</p>
        <div class="summary">
            <h3>Key Findings</h3>
            <p><strong>Most Influential Parameter:</strong> {df_sensitivity.iloc[0]['Parameter']} (Mu* = {df_sensitivity.iloc[0]['Mu_Star']:.4f})</p>
            <p><strong>Least Influential Parameter:</strong> {df_sensitivity.iloc[-1]['Parameter']} (Mu* = {df_sensitivity.iloc[-1]['Mu_Star']:.4f})</p>
        </div>
        <h2>1. Parameter Ranking (Mu*)</h2>
        <p>This chart shows which parameters have the largest overall effect on the model error (RMSE). Higher bars mean more important parameters.</p>
        <img src="plot_ranking.png" alt="Ranking Plot">
        <h2>2. Interaction Analysis (Sigma vs Mu*)</h2>
        <p><b>X-Axis (Mu*):</b> Total influence.<br>
        <b>Y-Axis (Sigma):</b> How much the parameter's effect depends on other parameters (Interaction) or changes across the range (Non-linearity).<br>
        <i>Parameters high up on Y are involved in complex interactions.</i></p>
        <img src="plot_nature.png" alt="Interaction Plot">
        <h2>3. Detailed Metrics</h2>
        {df_sensitivity.to_html(classes="table", index=False, float_format="%.4f")}
    </body>
    </html>
    """
    with open(f"{RESULTS_DIR}/report.html", "w") as f:
        f.write(html_content)

    console.print(Panel(f"[bold green]Report Generated![/bold green]\nopen {RESULTS_DIR}/report.html", title="Success"))

except Exception as e:
    console.print(f"[bold red]Analysis Failed:[/bold red] {e}")
    console.print("[yellow]Note: Analysis requires all simulations to complete successfully.[/yellow]")
