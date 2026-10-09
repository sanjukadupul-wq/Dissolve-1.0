#!/bin/bash
#SBATCH --job-name=zn_v4_bo_p2
#SBATCH --account=uj24
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --array=0-7
#SBATCH --output=v4_bo_p2_%A_%a.log
# v4 recalibration, phase 2 (8 pts: k_ORR narrowed to the EI ridge 20-32, k_f/k_d stratified): coarse disc, top-face Dirichlet O2, conservative mode 2, omega=1, 336 h.
cd /fs04/uj24/zinc_simulation_v4 || exit 1
ROW=$(sed -n "$((SLURM_ARRAY_TASK_ID+2))p" v4_doe_phase2.csv); IFS=',' read -r RID KF KD KORR <<< "$ROW"
OUTDIR="bo_v4/phase2_run${RID}"; mkdir -p "$OUTDIR"
module load singularity
SIF_PATH=~/software/freefem.sif
srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "disc_10x2_coarse_hmin0.5_topinlet.mesh" -dt_hours 4.0 -sim_duration 336.0 -save_interval 4.0 \
    -k_orr "$KORR" -k_f "$KF" -k_d "$KD" -film_tortuosity 120.0 -conservative 2 -o2_relax_omega 1.0 -o2_relax_scale_dt 0 \
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -checkpoint_each_time 336 -checkpoint_dir "$OUTDIR" -results_file "$OUTDIR/result_disc.txt" \
    -emit_vtk 0 -dump_final_state 0 -export_geometry 0
