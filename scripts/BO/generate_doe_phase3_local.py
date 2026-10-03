"""
generate_doe_phase3_local.py -- Phase 3 (local refinement) of the joint
(k_f, k_d, k_ORR) BO calibration on disc_10x2_coarse_hmin0.5.mesh.

Centered on the current overall best point found so far (dip-verification
batch, run_id=1): k_f=35.9058, k_d=27.1696, k_orr=0.5075, RMSE=0.0424%
(vs. 0.0461% for the original global-DoE best and 0.0464% for the GP's
own predicted-minimum point -- see combined_scores.txt / dip verification
results). This is now the local-refinement center, NOT the original
literature baseline (k_f=10, k_d=39.22, k_orr=0.25), since the global
search + dip-verification batch showed this intermediate-k_f region
genuinely fits the target curve better.

8-point LHS, log10-uniform, +/-2.5x around the center on each axis.
"""
import numpy as np
from scipy.stats import qmc
import csv
import os

DIR = os.path.dirname(os.path.abspath(__file__))

CENTER = {"k_f": 35.9058, "k_d": 27.1696, "k_orr": 0.5075}
FACTOR = 2.5  # local bounds = center / FACTOR .. center * FACTOR

names = list(CENTER.keys())
center_log = np.log10([CENTER[n] for n in names])
half_range = np.log10(FACTOR)
lo = center_log - half_range
hi = center_log + half_range

BOUNDS = {n: (10 ** lo[i], 10 ** hi[i]) for i, n in enumerate(names)}
print("Phase 3 local bounds:")
for n in names:
    print(f"  {n}: [{BOUNDS[n][0]:.4f}, {BOUNDS[n][1]:.4f}]")

N_DOE = 8
SEED = 314

sampler = qmc.LatinHypercube(d=3, seed=SEED)
unit = sampler.random(n=N_DOE)
log_samples = lo + unit * (hi - lo)
samples = 10 ** log_samples

csv_path = os.path.join(DIR, "doe_design_phase3_local.csv")
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["run_id", "k_f", "k_d", "k_orr"])
    for i, row in enumerate(samples):
        w.writerow([i, f"{row[0]:.6f}", f"{row[1]:.6f}", f"{row[2]:.6f}"])

print(f"\nSaved {N_DOE}-point local LHS design to {csv_path}")
print(f"{'run_id':>6} {'k_f':>10} {'k_d':>10} {'k_orr':>10}")
for i, row in enumerate(samples):
    print(f"{i:>6} {row[0]:>10.4f} {row[1]:>10.4f} {row[2]:>10.4f}")

SLURM_TEMPLATE = """#!/bin/bash
#SBATCH --job-name=zn_bo_disc_p3
#SBATCH --account=uj24
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --array=0-{n_max}
#SBATCH --output=bo_disc_phase3_%A_%a.log
#SBATCH --mail-type=END,FAIL

# Phase 3 (local refinement) of the joint (k_f, k_d, k_ORR) BO calibration
# on disc_10x2_coarse_hmin0.5.mesh. 8-point LHS centered on the current
# best point (k_f=35.9058, k_d=27.1696, k_orr=0.5075, RMSE=0.0424%),
# +/-2.5x per axis in log10-space. Same OLD-physics codebase, same
# numerical settings, sim_duration=336h as Phase 1/2.

module load singularity
SIF_PATH=~/software/freefem.sif
cd /fs04/uj24/zinc_simulation || {{ echo "FATAL: could not cd to /fs04/uj24/zinc_simulation"; exit 1; }}

TID=$SLURM_ARRAY_TASK_ID
CSV="bo_disc_coarse_joint/doe_design_phase3_local.csv"
ROW=$((TID + 2))  # +1 header, +1 1-indexed sed

LINE=$(sed -n "${{ROW}}p" "$CSV")
IFS=',' read -r RUN_ID KF KD KORR <<< "$LINE"

if [ -z "$KF" ]; then
    echo "FATAL: empty parameter row for TID=$TID (row=$ROW) from $CSV"
    exit 1
fi

OUTDIR="bo_disc_coarse_joint/output_phase3_run${{TID}}"
mkdir -p "$OUTDIR/vtk"

echo "Phase 3 run_id=$RUN_ID (array task $TID): k_f=$KF k_d=$KD k_orr=$KORR -> $OUTDIR"

srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \\
    -input_mesh "disc_10x2_coarse_hmin0.5.mesh" \\
    -dt_hours 4.0 -sim_duration 336.0 -save_interval 4.0 \\
    -k_orr "$KORR" -k_f "$KF" -k_d "$KD" -film_tortuosity 120.0 \\
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \\
    -checkpoint_each_time 24 -checkpoint_dir "$OUTDIR" \\
    -results_file "$OUTDIR/result_disc.txt" \\
    -emit_vtk 0 -dump_final_state 0 -export_geometry 0
"""

slurm_path = os.path.join(DIR, "run_bo_disc_joint_phase3_local.slurm")
with open(slurm_path, "w", newline="\n") as f:
    f.write(SLURM_TEMPLATE.format(n_max=N_DOE - 1))
print(f"\nSaved SLURM array script to {slurm_path}")
