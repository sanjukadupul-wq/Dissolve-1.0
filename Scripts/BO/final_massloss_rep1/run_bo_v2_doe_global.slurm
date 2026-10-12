#!/bin/bash
#SBATCH --job-name=zn_bov2_doe_g
#SBATCH --account=uj24
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --array=0-11
#SBATCH --output=bov2_doe_global_%A_%a.log
#SBATCH --mail-type=END,FAIL

# BO re-calibration on the v2 code (zinc_simulation_v2) -- Cl molar-unit fix
# active, so k_d now acts on molar Cl- and the literature range (1-50) is
# meaningful. The earlier BO (zinc_simulation, "OLD physics") calibrated k_d
# against raw g/mm^3 Cl (Cl^2 ~ 2.5e-11), where k_d was effectively inert.
# Phase 1 (GLOBAL DoE): 12-point LHS, log10-uniform, k_f=[1,100], k_d=[1,100],
# k_orr=[0.05,5.0]. Same mesh, numerics and 336 h horizon as the original BO.

module load singularity
SIF_PATH=~/software/freefem.sif
cd /fs04/uj24/zinc_simulation_v2 || { echo "FATAL: cd to v2 failed"; exit 1; }

TID=$SLURM_ARRAY_TASK_ID
CSV="bo_disc_coarse_joint_v2/doe_design_global.csv"
ROW=$((TID + 2))
LINE=$(sed -n "${ROW}p" "$CSV")
IFS=',' read -r RUN_ID KF KD KORR <<< "$LINE"
if [ -z "$KF" ]; then echo "FATAL: empty parameter row TID=$TID"; exit 1; fi

OUTDIR="bo_disc_coarse_joint_v2/output_global_run${TID}"
mkdir -p "$OUTDIR/vtk"
echo "v2 Global DoE run_id=$RUN_ID (task $TID): k_f=$KF k_d=$KD k_orr=$KORR -> $OUTDIR"

srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "disc_10x2_coarse_hmin0.5.mesh" \
    -dt_hours 4.0 -sim_duration 336.0 -save_interval 4.0 \
    -k_orr "$KORR" -k_f "$KF" -k_d "$KD" -film_tortuosity 120.0 \
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -checkpoint_each_time 24 -checkpoint_dir "$OUTDIR" \
    -results_file "$OUTDIR/result_disc.txt" \
    -emit_vtk 0 -dump_final_state 0 -export_geometry 0
