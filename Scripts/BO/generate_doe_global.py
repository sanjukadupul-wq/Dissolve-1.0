"""
generate_doe_global.py -- Phase 1 (GLOBAL search stage) of the joint
(k_f, k_d, k_ORR) BO calibration on disc_10x2_coarse_hmin0.5.mesh (see
Correlation_Study/ for the coarse<->fine correlation this relies on:
fine ~ 1.355846*coarse - 0.001584, Pearson r=0.998644, corrected
RMSE=0.004074% mass loss).

Revised plan (global-then-local, per explicit request -- more robust than
committing straight to a local box around the current baseline, since a
global stage can catch a better basin the baseline search never explored):
  Phase 1 (this script): 12-point LHS, WIDE bounds spanning the full
    physically-plausible range for each parameter, log10-uniform.
  Phase 2: ~8-10 EI-guided BO iterations still within these wide bounds,
    to hone toward the most promising region(s) found by Phase 1.
  Phase 3: local-refinement DoE + BO (see generate_doe.py, originally
    written as the local-bounds script) re-centered on whatever the
    global stage actually finds -- NOT necessarily the current baseline.

Wide bounds used here:
  k_f:   [1, 100]   (baseline 10;    GSA sweep tested 50-250 previously)
  k_d:   [5, 100]   (baseline 39.22; GSA sweep tested 10-80 previously)
  k_orr: [0.05, 5.0] (baseline 0.25; capped at 5.0, NOT the old script's
         30 -- k_orr>=10 is a flagged unstable regime where O2 can go
         negative, per SOLVER_FIXES_2026-08.md SS4.3)

Writes:
  - doe_design_global.csv            (run_id, k_f, k_d, k_orr)
  - run_bo_disc_joint_doe_global.slurm  (SLURM array job, one task/point)
"""
import numpy as np
from scipy.stats import qmc
import csv
import os

DIR = os.path.dirname(os.path.abspath(__file__))

BOUNDS = {
    "k_f":   (1.0, 100.0),
    "k_d":   (5.0, 100.0),
    "k_orr": (0.05, 5.0),
}
N_DOE = 12
SEED = 7

names = list(BOUNDS.keys())
lo = np.log10([BOUNDS[n][0] for n in names])
hi = np.log10([BOUNDS[n][1] for n in names])

sampler = qmc.LatinHypercube(d=3, seed=SEED)
unit = sampler.random(n=N_DOE)
log_samples = lo + unit * (hi - lo)
samples = 10 ** log_samples

csv_path = os.path.join(DIR, "doe_design_global.csv")
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["run_id", "k_f", "k_d", "k_orr"])
    for i, row in enumerate(samples):
        w.writerow([i, f"{row[0]:.6f}", f"{row[1]:.6f}", f"{row[2]:.6f}"])

print(f"Saved {N_DOE}-point LHS design (log10-uniform, GLOBAL bounds) to {csv_path}")
print(f"{'run_id':>6} {'k_f':>10} {'k_d':>10} {'k_orr':>10}")
for i, row in enumerate(samples):
    print(f"{i:>6} {row[0]:>10.4f} {row[1]:>10.4f} {row[2]:>10.4f}")

SLURM_TEMPLATE = """#!/bin/bash
#SBATCH --job-name=zn_bo_disc_doe_g
#SBATCH --account=uj24
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --array=0-{n_max}
#SBATCH --output=bo_disc_doe_global_%A_%a.log
#SBATCH --mail-type=END,FAIL

# Phase 1 (GLOBAL DoE) of the joint (k_f, k_d, k_ORR) BO calibration on
# disc_10x2_coarse_hmin0.5.mesh. Same OLD-physics codebase and numerical
# settings as the coarse/fine correlation study -- only k_f/k_d/k_orr and
# output paths vary per array task.
# Design: doe_design_global.csv (12-point LHS, WIDE bounds:
# k_f=[1,100], k_d=[5,100], k_orr=[0.05,5.0]).
# sim_duration=336h (NOT 672h) -- target dataset (DOI 10.1016/j.jmst.2018.05.005,
# target_jmst2018.csv) only extends to t=336h, so there is nothing to score
# past that point. Halves the per-run cost vs the earlier 672h correlation runs.

module load singularity
SIF_PATH=~/software/freefem.sif
cd /fs04/uj24/zinc_simulation || {{ echo "FATAL: could not cd to /fs04/uj24/zinc_simulation"; exit 1; }}

TID=$SLURM_ARRAY_TASK_ID
CSV="bo_disc_coarse_joint/doe_design_global.csv"
ROW=$((TID + 2))  # +1 header, +1 1-indexed sed

LINE=$(sed -n "${{ROW}}p" "$CSV")
IFS=',' read -r RUN_ID KF KD KORR <<< "$LINE"

if [ -z "$KF" ]; then
    echo "FATAL: empty parameter row for TID=$TID (row=$ROW) from $CSV"
    exit 1
fi

OUTDIR="bo_disc_coarse_joint/output_global_run${{TID}}"
mkdir -p "$OUTDIR/vtk"

echo "Global DoE run_id=$RUN_ID (array task $TID): k_f=$KF k_d=$KD k_orr=$KORR -> $OUTDIR"

srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \\
    -input_mesh "disc_10x2_coarse_hmin0.5.mesh" \\
    -dt_hours 4.0 -sim_duration 336.0 -save_interval 4.0 \\
    -k_orr "$KORR" -k_f "$KF" -k_d "$KD" -film_tortuosity 120.0 \\
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \\
    -checkpoint_each_time 24 -checkpoint_dir "$OUTDIR" \\
    -results_file "$OUTDIR/result_disc.txt" \\
    -emit_vtk 0 -dump_final_state 0 -export_geometry 0
"""

slurm_path = os.path.join(DIR, "run_bo_disc_joint_doe_global.slurm")
with open(slurm_path, "w", newline="\n") as f:
    f.write(SLURM_TEMPLATE.format(n_max=N_DOE - 1))
print(f"\nSaved SLURM array script to {slurm_path}")
