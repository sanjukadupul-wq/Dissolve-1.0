#!/bin/bash
#SBATCH --job-name=zn_bo_disc_p2
#SBATCH --account=uj24
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --array=0-7
#SBATCH --output=bo_disc_phase2_%A_%a.log
#SBATCH --mail-type=END,FAIL

# Phase 2 of the joint (k_f, k_d, k_ORR) BO calibration on
# disc_10x2_coarse_hmin0.5.mesh -- 8 points: k_f/k_orr are the GP+EI
# proposals from score_global.py (fit on the 12-point global DoE,
# scored against target_jmst2018.csv, DOI 10.1016/j.jmst.2018.05.005),
# k_d is a log-stratified sweep across the full global bounds [5,100]
# (the GP could not yet resolve k_d's length-scale from only 12 points,
# so this round deliberately buys real k_d information instead of using
# EI's uninformative incidental k_d values). Same OLD-physics codebase,
# same numerical settings, sim_duration=336h (target only extends to
# 336h) as Phase 1.

module load singularity
SIF_PATH=~/software/freefem.sif
cd /fs04/uj24/zinc_simulation || { echo "FATAL: could not cd to /fs04/uj24/zinc_simulation"; exit 1; }

TID=$SLURM_ARRAY_TASK_ID
CSV="bo_disc_coarse_joint/doe_design_phase2.csv"
ROW=$((TID + 2))  # +1 header, +1 1-indexed sed

LINE=$(sed -n "${ROW}p" "$CSV")
IFS=',' read -r RUN_ID KF KD KORR <<< "$LINE"

if [ -z "$KF" ]; then
    echo "FATAL: empty parameter row for TID=$TID (row=$ROW) from $CSV"
    exit 1
fi

OUTDIR="bo_disc_coarse_joint/output_phase2_run${TID}"
mkdir -p "$OUTDIR/vtk"

echo "Phase 2 run_id=$RUN_ID (array task $TID): k_f=$KF k_d=$KD k_orr=$KORR -> $OUTDIR"

srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "disc_10x2_coarse_hmin0.5.mesh" \
    -dt_hours 4.0 -sim_duration 336.0 -save_interval 4.0 \
    -k_orr "$KORR" -k_f "$KF" -k_d "$KD" -film_tortuosity 120.0 \
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -checkpoint_each_time 24 -checkpoint_dir "$OUTDIR" \
    -results_file "$OUTDIR/result_disc.txt" \
    -emit_vtk 0 -dump_final_state 0 -export_geometry 0
