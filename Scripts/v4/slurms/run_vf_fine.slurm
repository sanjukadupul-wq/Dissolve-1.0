#!/bin/bash
#SBATCH --job-name=zn_vf_fine
#SBATCH --account=uj24
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH --cpus-per-task=1
#SBATCH --mem=64G
#SBATCH --constraint=intel
#SBATCH --array=0-3
#SBATCH --output=v4_vf_fine_%A_%a.log
# fine-mesh (hmin0.25) partners of volumetric-film runs: k_ORR 15, 25, 35, 45 (hmin1.0 partners = vf_h1 runs 0, 2, 4, 6)
cd /fs04/uj24/zinc_simulation_v4 || exit 1
KORRS=(15 25 35 45); KORR=${KORRS[$SLURM_ARRAY_TASK_ID]}
OUTDIR="bo_vf/fine_k${KORR}"; mkdir -p "$OUTDIR"
module load singularity
SIF_PATH=~/software/freefem.sif
srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "disc_10x2_hmin0.25_topinlet.mesh" -dt_hours 4.0 -sim_duration 336.0 -save_interval 4.0 \
    -k_orr "$KORR" -k_f 100 -k_d 10 -film_tortuosity 2.0 -rho_film 0.005606 -conservative 2 -film_mode 0 -o2_relax_omega 1.0 -o2_relax_scale_dt 0 \
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -checkpoint_each_time 336 -checkpoint_dir "$OUTDIR" -results_file "$OUTDIR/result_disc.txt" \
    -emit_vtk 0 -dump_final_state 0 -export_geometry 0
