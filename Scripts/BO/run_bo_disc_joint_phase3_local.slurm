#!/bin/bash
#SBATCH --job-name=zn_bo_disc_p3
#SBATCH --account=uj24
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --array=0-7
#SBATCH --output=bo_disc_phase3_%A_%a.log
#SBATCH --mail-type=END,FAIL

# Phase 3 (local refinement) of the joint (k_f, k_d, k_ORR) BO calibration
# on disc_10x2_coarse_hmin0.5.mesh. 8-point LHS centered on the current
# best point (k_f=35.9058, k_d=27.1696, k_orr=0.5075, RMSE=0.0424%),
# +/-2.5x per axis in log10-space. Same OLD-physics codebase, same
# numerical settings, sim_duration=336h as Phase 1/2.

module load singularity
SIF_PATH=~/software/freefem.sif
cd /fs04/uj24/zinc_simulation || { echo "FATAL: could not cd to /fs04/uj24/zinc_simulation"; exit 1; }

TID=$SLURM_ARRAY_TASK_ID
CSV="bo_disc_coarse_joint/doe_design_phase3_local.csv"
ROW=$((TID + 2))  # +1 header, +1 1-indexed sed

LINE=$(sed -n "${ROW}p" "$CSV")
IFS=',' read -r RUN_ID KF KD KORR <<< "$LINE"

if [ -z "$KF" ]; then
    echo "FATAL: empty parameter row for TID=$TID (row=$ROW) from $CSV"
    exit 1
fi

OUTDIR="bo_disc_coarse_joint/output_phase3_run${TID}"
mkdir -p "$OUTDIR/vtk"

echo "Phase 3 run_id=$RUN_ID (array task $TID): k_f=$KF k_d=$KD k_orr=$KORR -> $OUTDIR"

srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "disc_10x2_coarse_hmin0.5.mesh" \
    -dt_hours 4.0 -sim_duration 336.0 -save_interval 4.0 \
    -k_orr "$KORR" -k_f "$KF" -k_d "$KD" -film_tortuosity 120.0 \
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -checkpoint_each_time 24 -checkpoint_dir "$OUTDIR" \
    -results_file "$OUTDIR/result_disc.txt" \
    -emit_vtk 0 -dump_final_state 0 -export_geometry 0
