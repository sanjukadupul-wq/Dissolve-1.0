#!/bin/bash
#SBATCH --job-name=zn_bo_disc_doe
#SBATCH --account=uj24
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --array=0-7
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
cd /fs04/uj24/zinc_simulation || { echo "FATAL: could not cd to /fs04/uj24/zinc_simulation"; exit 1; }

TID=$SLURM_ARRAY_TASK_ID
CSV="bo_disc_coarse_joint/doe_design.csv"
ROW=$((TID + 2))  # +1 header, +1 1-indexed sed

LINE=$(sed -n "${ROW}p" "$CSV")
IFS=',' read -r RUN_ID KF KD KORR <<< "$LINE"

if [ -z "$KF" ]; then
    echo "FATAL: empty parameter row for TID=$TID (row=$ROW) from $CSV"
    exit 1
fi

OUTDIR="bo_disc_coarse_joint/output_doe_run${TID}"
mkdir -p "$OUTDIR/vtk"

echo "DoE run_id=$RUN_ID (array task $TID): k_f=$KF k_d=$KD k_orr=$KORR -> $OUTDIR"

srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "disc_10x2_coarse_hmin0.5.mesh" \
    -dt_hours 4.0 -sim_duration 672.0 -save_interval 4.0 \
    -k_orr "$KORR" -k_f "$KF" -k_d "$KD" -film_tortuosity 120.0 \
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -checkpoint_each_time 24 -checkpoint_dir "$OUTDIR" \
    -results_file "$OUTDIR/result_disc.txt" \
    -emit_vtk 0 -dump_final_state 0 -export_geometry 0
