"""
generate_doe.py -- Phase 1 of the joint (k_f, k_d, k_ORR) BO calibration on
disc_10x2_coarse_hmin0.5.mesh (see Correlation_Study/ for the coarse<->fine
correlation this whole calibration relies on: fine ~ 1.355846*coarse -
0.001584, Pearson r=0.998644, corrected RMSE=0.004074% mass loss).

Generates an 8-point Latin Hypercube design in log10-space, LOCAL bounds
(~3x around the current baseline k_f=10, k_d=39.22, k_ORR=0.25 -- see
run plan discussion: a global search from wide bounds needs ~30-40 evals
to be reliable, but a local refinement around an already-working baseline
is well covered by the ~24-eval budget this project's time constraint
allows), and writes:
  - doe_design.csv          (run_id, k_f, k_d, k_orr)
  - run_bo_disc_joint_doe.slurm  (SLURM array job, one task per DoE point)
"""
import numpy as np
from scipy.stats import qmc
import csv
import os

DIR = os.path.dirname(os.path.abspath(__file__))

# Local-refinement bounds (log10-uniform), ~3x around the current
# calibrated baseline (k_f=10, k_d=39.22, k_orr=0.25).
BOUNDS = {
    "k_f":   (3.0, 30.0),
    "k_d":   (15.0, 80.0),
    "k_orr": (0.05, 1.0),
}
N_DOE = 8
SEED = 42

names = list(BOUNDS.keys())
lo = np.log10([BOUNDS[n][0] for n in names])
hi = np.log10([BOUNDS[n][1] for n in names])

sampler = qmc.LatinHypercube(d=3, seed=SEED)
unit = sampler.random(n=N_DOE)
log_samples = lo + unit * (hi - lo)
samples = 10 ** log_samples

csv_path = os.path.join(DIR, "doe_design.csv")
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["run_id", "k_f", "k_d", "k_orr"])
    for i, row in enumerate(samples):
        w.writerow([i, f"{row[0]:.6f}", f"{row[1]:.6f}", f"{row[2]:.6f}"])

print(f"Saved {N_DOE}-point LHS design (log10-uniform, local bounds) to {csv_path}")
print(f"{'run_id':>6} {'k_f':>10} {'k_d':>10} {'k_orr':>10}")
for i, row in enumerate(samples):
    print(f"{i:>6} {row[0]:>10.4f} {row[1]:>10.4f} {row[2]:>10.4f}")

SLURM_TEMPLATE = """#!/bin/bash
#SBATCH --job-name=zn_bo_disc_doe
#SBATCH --account=uj24
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --array=0-{n_max}
#SBATCH --output=bo_disc_doe_%A_%a.log
#SBATCH --mail-type=END,FAIL

# Phase 1 (initial DoE) of the joint (k_f, k_d, k_ORR) BO calibration on
# disc_10x2_coarse_hmin0.5.mesh. Same OLD-physics codebase and numerical
# settings as the coarse/fine correlation study (run_disc_10x2_coarse_hmin0.5.slurm)
# -- only k_f/k_d/k_orr and output paths vary per array task.
# Design: doe_design.csv (8-point LHS, local bounds around the current
# calibrated baseline k_f=10, k_d=39.22, k_orr=0.25).

module load singularity
SIF_PATH=~/software/freefem.sif
cd /fs04/uj24/zinc_simulation || {{ echo "FATAL: could not cd to /fs04/uj24/zinc_simulation"; exit 1; }}

TID=$SLURM_ARRAY_TASK_ID
CSV="bo_disc_coarse_joint/doe_design.csv"
ROW=$((TID + 2))  # +1 header, +1 1-indexed sed

LINE=$(sed -n "${{ROW}}p" "$CSV")
IFS=',' read -r RUN_ID KF KD KORR <<< "$LINE"

if [ -z "$KF" ]; then
    echo "FATAL: empty parameter row for TID=$TID (row=$ROW) from $CSV"
    exit 1
fi

OUTDIR="bo_disc_coarse_joint/output_doe_run${{TID}}"
mkdir -p "$OUTDIR/vtk"

echo "DoE run_id=$RUN_ID (array task $TID): k_f=$KF k_d=$KD k_orr=$KORR -> $OUTDIR"

srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \\
    -input_mesh "disc_10x2_coarse_hmin0.5.mesh" \\
    -dt_hours 4.0 -sim_duration 672.0 -save_interval 4.0 \\
    -k_orr "$KORR" -k_f "$KF" -k_d "$KD" -film_tortuosity 2.0 \\
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \\
    -checkpoint_each_time 24 -checkpoint_dir "$OUTDIR" \\
    -results_file "$OUTDIR/result_disc.txt" \\
    -emit_vtk 0 -dump_final_state 0 -export_geometry 0
"""

slurm_path = os.path.join(DIR, "run_bo_disc_joint_doe.slurm")
with open(slurm_path, "w", newline="\n") as f:
    f.write(SLURM_TEMPLATE.format(n_max=N_DOE - 1))
print(f"\nSaved SLURM array script to {slurm_path}")
