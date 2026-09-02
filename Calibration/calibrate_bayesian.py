#!/usr/bin/env python3
"""
Bayesian Optimization calibration of Dissolve's kinetic parameters (k1, k2,
k_orr), against experimental disc mass-loss data.

Ported from the original BioDeg project's optimize_parameters.py to this
repo's dissolve.edp CLI. Search bounds, run budgets, and every other
optimization setting are UNCHANGED from the original -- only flag names,
the solver entry point, launcher command, and stdout-parsing patterns were
updated to match the current codebase (see the flag-mapping table below).

Flag mapping (old -> current, config/settings.idp):
    -mesh_file      -> -input_mesh
    -k1             -> -k_f
    -k2             -> -k_d
    -k_orr          -> -k_orr   (unchanged)
    -d_o2           -> -diff_o2
    -initial_o2     -> -o2_initial
    -final_time     -> -sim_duration
    -time_step      -> -dt_hours
    -redistance_time -> -redistance_interval
    -save_each      -> -save_interval (now hours, not step count -- dt was
                       always 1h in the original scripts, so the numeric
                       value carries over unchanged: -save_each 1 == -save_interval 1.0)
    -text_output_file -> -results_file
    main.edp        -> dissolve.edp

Requirements (not part of this project's core dependencies -- install
separately): pandas, numpy, matplotlib, seaborn (optional), scikit-learn,
bayes_opt (`pip install bayesian-optimization`), rich, psutil (optional).

Usage (run from Src Codes/, with a mesh available -- see MESH_FILE below):
    python3 calibration/calibrate_bayesian.py
    CALIB_LAUNCHER=m3 python3 calibration/calibrate_bayesian.py   # on an M3 SLURM job
"""

import os
import subprocess
import multiprocessing
import datetime
import re
try:
    import psutil
except ImportError:
    psutil = None
import pandas as pd
import numpy as np
import time
import json
try:
    import seaborn as sns
except ImportError:
    sns = None
import matplotlib.pyplot as plt
from sklearn.ensemble import RandomForestRegressor
from bayes_opt import BayesianOptimization
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeElapsedColumn
from rich.panel import Panel
from rich import box
from pathlib import Path

console = Console()
timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

# ---------------------------------------------------------------------------
# Fixed run configuration
# ---------------------------------------------------------------------------
WORKDIR = Path(__file__).resolve().parent.parent / "Src Codes"  # solver root
# (this script itself lives in Calibration/, a sibling of Src Codes/ -- moved
# out of Src Codes/calibration/, hence the extra "/ Src Codes" here)
MESH_FILE = os.environ.get("CALIB_MESH", "cylinder_10x2_scaffold_in_box.mesh")  # supply this
RESULTS_DIR = str(WORKDIR / "output_bo")
SIMULATION_OUTPUT_FILE = str(WORKDIR / "output_bo" / "MassLoss.txt")
CHECKPOINT_FILE = str(WORKDIR / "output_bo" / "optimization_checkpoint.json")
GEOMETRY_NAME = "Cylinder_Medium_Corrected"

os.makedirs(RESULTS_DIR, exist_ok=True)

# --- Load Correction Parameters (multi-fidelity coarse->fine correlation) ---
CORRECTION_FILE = str(WORKDIR / "output_bo" / "correction_factor" / "correction_params.txt")
CORRECTION_SLOPE = 1.0
CORRECTION_INTERCEPT = 0.0

if os.path.exists(CORRECTION_FILE):
    try:
        with open(CORRECTION_FILE, "r") as f:
            for line in f:
                if "SLOPE" in line: CORRECTION_SLOPE = float(line.split("=")[1])
                if "INTERCEPT" in line: CORRECTION_INTERCEPT = float(line.split("=")[1])
        console.print(f"[bold green]Multi-Fidelity Correction Loaded: y = {CORRECTION_SLOPE:.4f}x + {CORRECTION_INTERCEPT:.4f}[/bold green]")
    except Exception:
        console.print("[yellow]Warning: Could not parse correction params. Using uncorrected values.[/yellow]")
else:
    console.print("[yellow]No correction params found. Running raw simulation.[/yellow]")

# Simulation Settings
if os.environ.get("SLURM_NTASKS"):
    CORES = int(os.environ["SLURM_NTASKS"])
    print(f"DEBUG: Detected SLURM_NTASKS. Using {CORES} cores.")
else:
    CORES = int(os.environ.get("CALIB_NP", "8"))

P_CORES = list(range(CORES))
try:
    if psutil:
        p = psutil.Process()
        p.cpu_affinity(P_CORES)
        print(f"DEBUG: Process affinity restricted to: {p.cpu_affinity()}")
    else:
        print("WARNING: psutil not installed. CPU affinity not set.")
except Exception as e:
    print(f"WARNING: Could not set CPU affinity: {e}")

print(f"DEBUG: Using {CORES} cores for simulation.")

# --- Optimization budget/targets (unchanged from the original) ---
TOTAL_RUNS = 20        # Initial batch size
MAX_TOTAL_RUNS = 100    # Limit runs to 100
TARGET_RMSE = 0.05      # Research Grade Goal
INIT_POINTS = 5

FINAL_TIME = 336.0      # Matches largest calibration point
TIME_STEP = 1.0         # 1h Time Step
REDISTANCE_TIME = 1.0   # 1h Redistance

# ---------------------------------------------------------------------------
# Launcher: "local" (default) runs ff-mpirun directly. "m3" runs inside an
# already-allocated SLURM job via srun+singularity -- same pattern as
# calibrate_kinetics.py, so both scripts behave identically on M3.
# ---------------------------------------------------------------------------
LAUNCHER = os.environ.get("CALIB_LAUNCHER", "local")
SIF_PATH = os.environ.get("CALIB_SIF_PATH", str(Path.home() / "software" / "freefem.sif"))


def build_command(k1, k2, k_orr):
    """k1/k2 here are this script's own parameter names (kept unchanged from
    the original); mapped to -k_f/-k_d on the actual solver CLI."""
    dissolve_args = [
        "-input_mesh", MESH_FILE,
        "-k_f", str(k1), "-k_d", str(k2), "-k_orr", str(k_orr),
        "-diff_o2", "7.2", "-o2_initial", "6.72e-9",
        "-sim_duration", str(FINAL_TIME), "-dt_hours", str(TIME_STEP),
        "-redistance_interval", str(REDISTANCE_TIME), "-save_interval", "1",
        "-results_file", os.path.relpath(SIMULATION_OUTPUT_FILE, WORKDIR),
        "-emit_vtk", "0", "-dump_final_state", "0", "-export_geometry", "0",
    ]
    if LAUNCHER == "m3":
        return (["srun", "--mpi=pmi2", "-n", str(CORES),
                  "singularity", "exec", SIF_PATH,
                  "FreeFem++-mpi", "-nw", "dissolve.edp", "-v", "0"] + dissolve_args)
    else:
        return (["ff-mpirun", "-np", str(CORES), "dissolve.edp", "-nw", "-v", "0"] + dissolve_args)


# ---------------------------------------------------------------------------
# Experimental data -- inline, matching calibrate_kinetics.py's checkpoints
# (this repo has no experimental_data_v2.csv; the original external-file
# dependency is replaced with the same values already used elsewhere in
# this project for consistency).
# ---------------------------------------------------------------------------
EXP_DATA = pd.DataFrame({
    "TimeHours": [24, 72, 168, 336, 672],
    "MassLossPercent": [0.045, 0.105, 0.209, 0.254, 0.31],
})
EXP_DATA = EXP_DATA[EXP_DATA["TimeHours"] <= FINAL_TIME].reset_index(drop=True)

# Early Stopping Configuration
MAX_EXP_LOSS = EXP_DATA['MassLossPercent'].max()
LOSS_THRESHOLD_MULTIPLIER = 1.6
if CORRECTION_SLOPE > 1e-3:
    SCALED_EXP_LIMIT = MAX_EXP_LOSS / CORRECTION_SLOPE
else:
    SCALED_EXP_LIMIT = MAX_EXP_LOSS

ABORT_THRESHOLD = SCALED_EXP_LIMIT * LOSS_THRESHOLD_MULTIPLIER
console.print(f"[bold cyan]Early Stopping Enabled: Abort if Raw Mass Loss > {ABORT_THRESHOLD:.2f}% "
              f"(Exp Max: {MAX_EXP_LOSS:.2f}%, Scaled Limit: {SCALED_EXP_LIMIT:.2f}%)[/bold cyan]")


# --- Visualization & Reporting ---
def finalize_optimization(optimizer, results_dir, exp_data):
    console.print(Panel("[bold cyan]Generating Final Report & Plots...[/bold cyan]", title="Reporting"))

    try:
        best_params = optimizer.max['params']
        best_target = optimizer.max['target']
    except Exception:
        console.print("[red]No optimization results found to plot.[/red]")
        return

    console.print("[yellow]Re-running simulation with best parameters for plotting...[/yellow]")
    cmd = build_command(best_params['k1'], best_params['k2'], best_params['k_orr'])

    try:
        if os.path.exists(SIMULATION_OUTPUT_FILE):
            os.remove(SIMULATION_OUTPUT_FILE)
        subprocess.run(cmd, cwd=WORKDIR, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        if os.path.exists(SIMULATION_OUTPUT_FILE):
            sim_data = pd.read_csv(SIMULATION_OUTPUT_FILE, sep="\t")
            plt.figure(figsize=(10, 6))
            plt.plot(sim_data['TimeHours'], sim_data['MassLossPercent'], label='Best Simulation', color='blue', linewidth=2)
            plt.scatter(exp_data['TimeHours'], exp_data['MassLossPercent'], label='Experimental Data', color='red', s=100, zorder=5)
            plt.title('Validation: Simulation vs Experiment', fontsize=14)
            plt.xlabel('Time (Hours)', fontsize=12)
            plt.ylabel('Mass Loss (%)', fontsize=12)
            plt.legend(fontsize=12)
            plt.grid(True, alpha=0.3)
            plt.savefig(f"{results_dir}/plot_comparison.png", dpi=300)
            plt.close()
    except Exception as e:
        console.print(f"[red]Error generating comparison plot: {e}[/red]")

    console.print("[bold cyan]Generating Research-Grade Analysis Plots...[/bold cyan]")

    if len(optimizer.res) > 3:
        df_res = pd.DataFrame([res['params'] for res in optimizer.res])
        df_res['RMSE'] = [-res['target'] for res in optimizer.res]
        df_res['Iteration'] = range(1, len(df_res) + 1)
        df_res['Best_RMSE'] = df_res['RMSE'].cummin()

        # 1. CONVERGENCE PLOT
        try:
            plt.figure(figsize=(10, 6))
            plt.scatter(df_res['Iteration'], df_res['RMSE'], color='gray', alpha=0.5, label='Individual Runs')
            plt.plot(df_res['Iteration'], df_res['Best_RMSE'], color='#d62728', linewidth=3, label='Best Observed (Convergence)')
            plt.xlabel("Iteration", fontweight='bold')
            plt.ylabel("RMSE", fontweight='bold')
            plt.title("Optimization Convergence Trace")
            plt.legend()
            plt.grid(True, alpha=0.3)
            plt.savefig(f"{results_dir}/plot_convergence_paper.png", dpi=300)
            plt.close()
        except Exception as e:
            console.print(f"[yellow]Convergence plot failed: {e}[/yellow]")

        # 2. SAMPLE DISTRIBUTION
        if sns:
            try:
                df_res['Phase'] = pd.cut(df_res['Iteration'], bins=3, labels=["Early", "Mid", "Late"])
                g = sns.PairGrid(df_res, vars=['k1', 'k2', 'k_orr', 'RMSE'], hue="Phase", palette="viridis")
                g.map_upper(sns.scatterplot, edgecolor="w")
                g.map_lower(sns.kdeplot, alpha=0.6)
                g.map_diag(sns.histplot)
                g.add_legend()
                g.savefig(f"{results_dir}/plot_sample_distribution.png", dpi=300)
                plt.close()
            except Exception as e:
                console.print(f"[yellow]Sample Dist plot failed: {e}[/yellow]")

        # 3. PARAMETER IMPORTANCE (Random Forest)
        rf = None
        try:
            X = df_res[['k1', 'k2', 'k_orr']]
            y = df_res['RMSE']
            rf = RandomForestRegressor(n_estimators=100, random_state=42)
            rf.fit(X, y)
            importances = rf.feature_importances_
            feature_names = ['k1', 'k2', 'k_orr']
            plt.figure(figsize=(8, 6))
            if sns:
                sns.barplot(x=feature_names, y=importances, palette='Blues_r')
            else:
                plt.bar(feature_names, importances)
            plt.title("Parameter Sensitivity (Random Forest Importance)")
            plt.ylabel("Importance Score")
            plt.grid(axis='y', alpha=0.3)
            plt.savefig(f"{results_dir}/plot_parameter_importance.png", dpi=300)
            plt.close()
        except Exception as e:
            console.print(f"[yellow]Importance plot failed: {e}[/yellow]")

        # 4. SURROGATE LANDSCAPE (RF-predicted RMSE, k1 vs k2)
        try:
            if rf is not None:
                res_grid = 50
                k1_range = np.linspace(df_res['k1'].min(), df_res['k1'].max(), res_grid)
                k2_range = np.linspace(df_res['k2'].min(), df_res['k2'].max(), res_grid)
                K1_grid, K2_grid = np.meshgrid(k1_range, k2_range)
                best_k_orr = best_params['k_orr']
                X_grid = np.c_[K1_grid.ravel(), K2_grid.ravel(), np.full(res_grid * res_grid, best_k_orr)]
                X_df = pd.DataFrame(X_grid, columns=['k1', 'k2', 'k_orr'])
                Z = rf.predict(X_df).reshape(res_grid, res_grid)

                plt.figure(figsize=(8, 6))
                contour = plt.contourf(K1_grid, K2_grid, Z, levels=20, cmap='viridis_r')
                plt.colorbar(contour, label='Predicted RMSE')
                plt.scatter(df_res['k1'], df_res['k2'], c='black', s=20, alpha=0.5, label='Samples')
                plt.scatter(best_params['k1'], best_params['k2'], c='red', marker='*', s=200, label='Optimal')
                plt.xlabel('k1')
                plt.ylabel('k2')
                plt.title(f'Surrogate Landscape (k_orr={best_k_orr:.2f})')
                plt.legend()
                plt.savefig(f"{results_dir}/plot_landscape_k1_k2.png", dpi=300)
                plt.close()
        except Exception as e:
            console.print(f"[yellow]Landscape plot failed: {e}[/yellow]")

    # HTML Report
    html_content = f"""
    <html>
    <head>
        <title>Optimization Report - {timestamp}</title>
        <style>
            body {{ font-family: Arial, sans-serif; margin: 40px; }}
            h1, h2 {{ color: #2c3e50; }}
            .metric {{ padding: 10px; background: #ecf0f1; border-radius: 5px; display: inline-block; margin-right: 20px; }}
            img {{ max-width: 100%; border: 1px solid #ddd; border-radius: 5px; margin-bottom: 20px; }}
            .params {{ background: #f9f9f9; padding: 20px; border-left: 5px solid #27ae60; }}
        </style>
    </head>
    <body>
        <h1>Optimization Report</h1>
        <p><strong>Date:</strong> {datetime.datetime.now()}</p>
        <div class="metric"><strong>Best RMSE:</strong> {-best_target:.5f}</div>
        <div class="metric"><strong>Total Runs:</strong> {len(optimizer.res)}</div>
        <h2>Best Parameters Found</h2>
        <div class="params"><pre>{json.dumps(best_params, indent=4)}</pre></div>
        <h2>1. Simulation Fit</h2>
        <img src="plot_comparison.png" alt="Comparison Plot">
        <h2>2. Optimization Convergence</h2>
        <img src="plot_convergence_paper.png" alt="Convergence Plot">
        <h2>3. Parameter Distributions</h2>
        <img src="plot_sample_distribution.png" alt="Sample Distribution">
        <h2>4. Parameter Importance</h2>
        <img src="plot_parameter_importance.png" alt="Importance">
        <h2>5. Objective Landscape (k1 vs k2)</h2>
        <img src="plot_landscape_k1_k2.png" alt="Landscape">
    </body>
    </html>
    """
    with open(f"{results_dir}/report.html", "w") as f:
        f.write(html_content)

    console.print(Panel(f"[bold green]Report Generated![/bold green]\nopen {results_dir}/report.html", title="Done"))


# --- Checkpoint Management ---
def load_checkpoint():
    if not os.path.exists(CHECKPOINT_FILE):
        return []
    data = []
    try:
        with open(CHECKPOINT_FILE, 'r') as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    params = entry['params']
                    filtered_params = {k: v for k, v in params.items() if k in ['k1', 'k2', 'k_orr']}
                    entry['params'] = filtered_params
                    data.append(entry)
        console.print(f"[bold green]Resuming from checkpoint: Found {len(data)} completed runs.[/bold green]")
        return data
    except Exception as e:
        console.print(f"[bold red]Error loading checkpoint:[/bold red] {e}")
        return []


def save_checkpoint_entry(target, params):
    entry = {"target": target, "params": params}
    with open(CHECKPOINT_FILE, 'a') as f:
        f.write(json.dumps(entry) + "\n")


# --- State ---
checkpoint_data = load_checkpoint()
best_rmse = float('inf')
previous_runs = len(checkpoint_data)
if previous_runs > 0:
    for entry in checkpoint_data:
        rmse = -entry['target']
        if rmse < best_rmse:
            best_rmse = rmse

iteration_count = previous_runs
last_run_stats = None


# --- Objective Function ---
def simulation_objective(k1, k2, k_orr):
    global best_rmse, iteration_count, last_run_stats
    iteration_count += 1

    param_text = f"""[cyan]k1[/cyan]         = {k1:.6f}
[cyan]k2[/cyan]         = {k2:.6f}
[cyan]k_orr[/cyan]      = {k_orr:.6f}"""
    console.print(Panel(param_text, title=f"Run {iteration_count}/{TOTAL_RUNS} Parameters", border_style="blue", box=box.ROUNDED))

    cmd = build_command(k1, k2, k_orr)

    rmse = 1e9
    time.sleep(5)  # brief cooldown between MPI launches

    env = os.environ.copy()
    env["OMP_NUM_THREADS"] = "1"
    env["MKL_NUM_THREADS"] = "1"
    env["OPENBLAS_NUM_THREADS"] = "1"
    env["NUMEXPR_NUM_THREADS"] = "1"
    env["VECLIB_MAXIMUM_THREADS"] = "1"

    with Progress(
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
        TimeElapsedColumn(),
        console=console
    ) as progress:
        task = progress.add_task("[bold green]Running Simulation...[/bold green]", total=100)
        try:
            if os.path.exists(SIMULATION_OUTPUT_FILE):
                os.remove(SIMULATION_OUTPUT_FILE)

            process = subprocess.Popen(cmd, cwd=WORKDIR, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, bufsize=1, env=env)

            current_time = 0.0
            mass_loss = 0.0
            regime = "UNKNOWN"

            # dissolve.edp prints lines like:
            #   Time: 24h  (1d 0h)    Step: 24    O2 consumed (g): ...
            #   Initial size: ...    Current size: ...    % change: 0.045
            # (the "h" suffix and parenthetical duration are new relative to
            # the original main.edp's plain numeric output -- parsed with a
            # regex here instead of naive split()/float() to handle that)
            time_re = re.compile(r"Time:\s*([\d.eE+-]+)h")
            change_re = re.compile(r"%\s*change:\s*([\d.eE+-]+)", re.IGNORECASE)

            while True:
                line = process.stdout.readline()
                if not line and process.poll() is not None:
                    break
                if line:
                    m = time_re.search(line)
                    if m:
                        try:
                            current_time = float(m.group(1))
                            pct = min((current_time / FINAL_TIME) * 100, 100)
                            progress.update(task, completed=pct)
                        except ValueError:
                            pass
                    m2 = change_re.search(line)
                    if m2:
                        try:
                            mass_loss = float(m2.group(1))
                        except ValueError:
                            pass

                    # Speculative: current dissolve.edp is not confirmed to print a
                    # "DOMINANT: REACTION/DIFFUSION" line -- this just degrades
                    # gracefully to "UNKNOWN" if it doesn't. Harmless either way
                    # since the heuristic branch that uses `regime` is disabled
                    # below (use_heuristic=False), matching the original script.
                    if "DOMINANT:" in line:
                        if "REACTION" in line:
                            regime = "REACTION"
                        elif "DIFFUSION" in line:
                            regime = "DIFFUSION"

                    if mass_loss > ABORT_THRESHOLD:
                        process.terminate()
                        console.print(f"[yellow]  -> [STOP] Early Stopping: Mass Loss {mass_loss:.2f}% exceeded limit ({ABORT_THRESHOLD:.2f}%)[/yellow]")
                        return 10.0

                    progress.update(task, description=f"[bold green]Simulating... (t={current_time:.1f}h, Loss={mass_loss:.2f}%)[/bold green]")

            stdout, stderr = process.communicate()

            if process.returncode != 0:
                console.print(f"[bold red]Simulation Failed! Return code: {process.returncode}[/bold red]")
                console.print(f"[red]STDOUT:[/red]\n{stdout}")
                console.print(f"[red]STDERR:[/red]\n{stderr}")
                return -1e9

            if not os.path.exists(SIMULATION_OUTPUT_FILE):
                console.print("[bold red]Output file not found![/bold red]")
                return -1e9
            if os.path.getsize(SIMULATION_OUTPUT_FILE) < 10:
                console.print("[bold red]Output file is empty or corrupted![/bold red]")
                return -1e9

            try:
                sim_data = pd.read_csv(SIMULATION_OUTPUT_FILE, sep="\t")
                if 'TimeHours' not in sim_data.columns or 'MassLossPercent' not in sim_data.columns:
                    raise ValueError("Columns 'TimeHours' or 'MassLossPercent' missing from output")
            except Exception as e:
                console.print(f"[bold red]Error reading simulation output:[/bold red] {e}")
                return -1e9

            check_times = EXP_DATA['TimeHours'].values
            target_mass_loss = EXP_DATA['MassLossPercent'].values

            raw_interp_mass_loss = np.interp(check_times, sim_data['TimeHours'], sim_data['MassLossPercent'])
            interp_mass_loss = CORRECTION_SLOPE * raw_interp_mass_loss + CORRECTION_INTERCEPT
            rmse = np.sqrt(np.mean((interp_mass_loss - target_mass_loss) ** 2))

            peak_raw = np.max(raw_interp_mass_loss)
            peak_corr = np.max(interp_mass_loss)
            console.print(f"[dim]  -> Raw Peak: {peak_raw:.4f}% | Corrected: {peak_corr:.4f}% | "
                           f"Correction: {CORRECTION_SLOPE:.4f}x + {CORRECTION_INTERCEPT:.4f}[/dim]")

            save_checkpoint_entry(-rmse, {
                'k1': k1, 'k2': k2, 'k_orr': k_orr,
                'mass_loss': np.max(interp_mass_loss),
                'regime': regime,
                'geometry': GEOMETRY_NAME
            })

            if rmse < best_rmse:
                improvement = ""
                if best_rmse != float('inf'):
                    pct = (best_rmse - rmse) / best_rmse * 100
                    improvement = f"({pct:.1f}% improvement)"
                best_rmse = rmse
                console.print(f"[bold yellow][NEW BEST]! RMSE: {rmse:.4f}[/bold yellow] {improvement}")

                with open(f"{RESULTS_DIR}/best_params.json", "w") as f:
                    json.dump({"rmse": rmse, "k1": k1, "k2": k2, "k_orr": k_orr}, f, indent=4)

                try:
                    plt.figure(figsize=(10, 6))
                    plt.plot(EXP_DATA['TimeHours'], EXP_DATA['MassLossPercent'], 'ro', label='Experimental Data')
                    corrected_sim_loss = sim_data['MassLossPercent'] * CORRECTION_SLOPE + CORRECTION_INTERCEPT
                    plt.plot(sim_data['TimeHours'], corrected_sim_loss, 'b-', linewidth=2, label=f'Corrected Prediction (RMSE={rmse:.4f})')
                    plt.plot(sim_data['TimeHours'], sim_data['MassLossPercent'], 'k--', linewidth=1, alpha=0.5, label='Raw Prediction')
                    plt.xlabel('Time (Hours)')
                    plt.ylabel('Mass Loss (%)')
                    plt.title(f'Best Fit Comparison\nk1={k1:.2f}, k2={k2:.2f}, k_orr={k_orr:.4f}')
                    plt.legend()
                    plt.grid(True, alpha=0.3)
                    save_path = f"{RESULTS_DIR}/best_fit_iter_{iteration_count}_rmse_{rmse:.4f}.png"
                    plt.savefig(save_path, dpi=100)
                    plt.close()
                    console.print(f"  Plot saved to {save_path}")
                except Exception as e:
                    console.print(f"[red]Error plotting:[/red] {e}")
            else:
                console.print(f"  RMSE: {rmse:.4f} (Current Best: {best_rmse:.4f})")

            last_run_stats = {'k1': k1, 'k2': k2, 'k_orr': k_orr, 'rmse': rmse,
                               'mass_loss': np.max(interp_mass_loss), 'regime': regime}
            return -rmse

        except Exception as e:
            console.print(f"[bold red]Error:[/bold red] {e}")
            return -1e9


# --- Optimization Setup (bounds UNCHANGED from the original) ---
pbounds = {
    'k1': (100.0, 1000.0),
    'k2': (0.0, 100.0),
    'k_orr': (0.1, 10.0)
}

n_completed = len(checkpoint_data)
init_points_remaining = max(0, INIT_POINTS - n_completed)
iter_points_remaining = max(0, TOTAL_RUNS - n_completed - init_points_remaining)

console.print(Panel.fit(
    f"[bold white]Bayesian Optimization for Dissolve Kinetic Parameters[/bold white]\n"
    f"[italic]Cores: {CORES} | Time: {FINAL_TIME}h | Total Runs: {TOTAL_RUNS}[/italic]\n"
    f"[italic]Previous Runs Found: {n_completed}[/italic]\n"
    f"[italic]Remaining: {init_points_remaining} Random + {iter_points_remaining} Guided[/italic]",
    style="bold blue"))

optimizer = BayesianOptimization(f=simulation_objective, pbounds=pbounds, random_state=1, verbose=0)

if n_completed > 0:
    for entry in checkpoint_data:
        try:
            optimizer.register(params=entry['params'], target=entry['target'])
        except KeyError:
            pass

TRAINING_DATA_FILE = str(WORKDIR / "output_bo" / "training_data.csv")
if os.path.exists(TRAINING_DATA_FILE):
    try:
        df_train = pd.read_csv(TRAINING_DATA_FILE)
        console.print(f"[bold cyan]Loading {len(df_train)} points from {TRAINING_DATA_FILE} for warm start...[/bold cyan]")
        count = 0
        for _, row in df_train.iterrows():
            try:
                params = {'k1': row['k1'], 'k2': row['k2'], 'k_orr': row['k_orr']}
                valid = all(pbounds[p][0] <= v <= pbounds[p][1] for p, v in params.items())
                if valid:
                    optimizer.register(params=params, target=-row['RMSE'])
                    count += 1
            except Exception:
                pass
        console.print(f"[bold green]Successfully registered {count} valid warm-start points.[/bold green]")
    except Exception as e:
        console.print(f"[bold red]Error loading training data:[/bold red] {e}")


# --- Optimization Loop ---
console.print(Panel(f"[bold white]Starting Optimization Loop[/bold white]\n[cyan]Target RMSE: {TARGET_RMSE}[/cyan]\n[cyan]Max Runs: {MAX_TOTAL_RUNS}[/cyan]", style="bold green"))

while len(optimizer.space) < MAX_TOTAL_RUNS:
    if best_rmse <= TARGET_RMSE:
        console.print(f"[bold green][SUCCESS] TARGET ACHIEVED! RMSE {best_rmse:.5f} <= {TARGET_RMSE}[/bold green]")
        break
    try:
        n_registered = len(optimizer.space)
        if n_registered < INIT_POINTS:
            optimizer.maximize(init_points=1, n_iter=0)
        else:
            # Pure BayesOpt -- heuristic nudge logic kept below (disabled by
            # default) for reference/future use, matching the original script.
            use_heuristic = False
            if use_heuristic and last_run_stats is not None:
                console.print("[bold magenta][HEURISTIC] " + ("Increase" if last_run_stats['mass_loss'] < 1.5 else "Decrease") + " Logic Activated[/bold magenta]")
                p = last_run_stats
                new_k1, new_k2, new_k_orr = p['k1'], p['k2'], p['k_orr']
                NUDGE = 0.10
                current_loss = p['mass_loss']
                target_loss = MAX_EXP_LOSS
                regime = p.get('regime', 'UNKNOWN')
                console.print(f"[magenta]  -> Feedback Source: {regime} CONTROLLED[/magenta]")

                if current_loss < target_loss:
                    if regime == 'REACTION':
                        new_k_orr *= (1.0 + NUDGE * 2.0)
                        new_k2 *= (1.0 + NUDGE * 0.5)
                    elif regime == 'DIFFUSION':
                        new_k2 *= (1.0 + NUDGE * 2.0)
                        new_k1 *= (1.0 - NUDGE * 2.0)
                        new_k_orr *= (1.0 + NUDGE * 0.2)
                    else:
                        new_k_orr *= (1.0 + NUDGE)
                        new_k2 *= (1.0 + NUDGE)
                        new_k1 *= (1.0 - NUDGE)
                else:
                    if regime == 'REACTION':
                        new_k_orr *= (1.0 - NUDGE * 2.0)
                        new_k2 *= (1.0 - NUDGE * 0.5)
                    elif regime == 'DIFFUSION':
                        new_k2 *= (1.0 - NUDGE * 2.0)
                        new_k1 *= (1.0 + NUDGE * 2.0)
                        new_k_orr *= (1.0 - NUDGE * 0.2)
                    else:
                        new_k_orr *= (1.0 - NUDGE)
                        new_k2 *= (1.0 - NUDGE)
                        new_k1 *= (1.0 + NUDGE)

                new_k1 = max(pbounds['k1'][0], min(pbounds['k1'][1], new_k1))
                new_k2 = max(pbounds['k2'][0], min(pbounds['k2'][1], new_k2))
                new_k_orr = max(pbounds['k_orr'][0], min(pbounds['k_orr'][1], new_k_orr))

                if abs(new_k1 - p['k1']) < 1e-4 and abs(new_k2 - p['k2']) < 1e-4 and abs(new_k_orr - p['k_orr']) < 1e-6:
                    console.print("[bold yellow][WARNING] Stagnation Detected. Forcing Random Exploration.[/bold yellow]")
                    optimizer.maximize(init_points=1, n_iter=0)
                else:
                    dup_found = any(
                        abs(new_k1 - r['params']['k1']) < 1e-3 and
                        abs(new_k2 - r['params']['k2']) < 1e-3 and
                        abs(new_k_orr - r['params']['k_orr']) < 1e-4
                        for r in optimizer.res
                    )
                    if dup_found:
                        console.print("[bold yellow][WARNING] Duplicate Proposal Detected. Forcing Random Exploration.[/bold yellow]")
                        optimizer.maximize(init_points=1, n_iter=0)
                    else:
                        console.print(f"[magenta]  -> Proposing: k1={new_k1:.2f}, k2={new_k2:.2f}, k_orr={new_k_orr:.4f}[/magenta]")
                        optimizer.probe(params={'k1': new_k1, 'k2': new_k2, 'k_orr': new_k_orr}, lazy=False)
            else:
                optimizer.maximize(init_points=0, n_iter=1)
    except Exception as e:
        console.print(f"[bold red]Optimization Loop Warning:[/bold red] {e}")
        break

if len(optimizer.space) >= MAX_TOTAL_RUNS:
    console.print(f"[yellow]Stopped: Max runs ({MAX_TOTAL_RUNS}) reached.[/yellow]")

final_report_path = f"{RESULTS_DIR}/final_report.txt"
with open(final_report_path, "w") as f:
    f.write("Optimization Complete\n")
    f.write(f"Best RMSE: {best_rmse:.5f}\n")
    if len(optimizer.res) > 0:
        f.write(f"Parameters: {optimizer.max['params']}\n")

finalize_optimization(optimizer, RESULTS_DIR, EXP_DATA)
