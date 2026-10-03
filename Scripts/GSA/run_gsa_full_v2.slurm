#!/bin/bash
#SBATCH --job-name=zn_gsa_full_v2
#SBATCH --account=uj24
#SBATCH --time=2:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=1
#SBATCH --mem=8G
#SBATCH --constraint=intel
#SBATCH --array=0-179
#SBATCH --output=gsa_full_v2_%A_%a.log
#SBATCH --mail-type=END,FAIL

# Re-run of the full 180-run Morris GSA (r=20 trajectories x 8 params),
# SAME design (morris_full_design.csv, seed=7, identical literature-informed
# bounds) as the original run (job 60076785), but using the corrected
# physics in /fs04/uj24/zinc_simulation_v2: the Cl molar-unit fix
# (config/settings.idp clMolarConv, physics/governing_equations.idp
# fDissolutionRate kd*F*(clMolarConv*Cl)^2) that made kd sensitive across
# its literature range (validated: kd=1/25/50 now give 0.324/0.574/0.609%
# mass loss instead of a flat 0.234% for all three -- job 60079264).
# Running from the isolated copy, NOT /fs04/uj24/zinc_simulation (original,
# unmodified, still used by the running curvature study job 60063760).
#
# Parameters read from morris_full_design.csv by row (run_id = array task
# id), same as the original GSA script -- identical design, only the code
# differs, so before/after fix comparison is apples-to-apples.

cd /fs04/uj24/zinc_simulation_v2 || { echo "FATAL: could not cd to /fs04/uj24/zinc_simulation_v2"; exit 1; }

TID=$SLURM_ARRAY_TASK_ID
CSV="morris_full_design.csv"
ROW=$((TID + 2))  # +1 for header, +1 for 1-indexed sed

LINE=$(sed -n "${ROW}p" "$CSV")
IFS=',' read -r RUN_ID KF KD KORR D_O2 C_O2_0 D_ZN D_CL D_OH <<< "$LINE"

if [ -z "$KF" ]; then
    echo "FATAL: empty parameter row for TID=$TID (row=$ROW) from $CSV"
    exit 1
fi

MESH="Cylinder/cylinder_10x2_DEBUG_coarse.mesh"
OUTDIR="output_gsa_full_v2_run${TID}"
mkdir -p "$OUTDIR"

echo "Array task $TID (run_id=$RUN_ID): kf=$KF kd=$KD kORR=$KORR D_O2=$D_O2 C_O2_0=$C_O2_0 D_Zn=$D_ZN D_Cl=$D_CL D_OH=$D_OH -> $OUTDIR"

module load singularity
SIF_PATH=~/software/freefem.sif

srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "$MESH" \
    -dt_hours 4.0 -sim_duration 168.0 -save_interval 4.0 \
    -k_f "$KF" -k_d "$KD" -k_orr "$KORR" \
    -diff_o2 "$D_O2" -o2_initial "$C_O2_0" -diff_zn "$D_ZN" \
    -diff_cl "$D_CL" -diff_oh "$D_OH" \
    -film_tortuosity 2.0 \
    -enable_redistance 1 -redistance_interval 24.0 \
    -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -min_disk_free_gb 20 \
    -checkpoint_each_time 168 -checkpoint_dir "$OUTDIR" \
    -results_file "$OUTDIR/result.txt" \
    -emit_vtk 0 \
    -dump_final_state 0 -export_geometry 0
