#!/bin/bash
#SBATCH --job-name=zn_sf_domain
#SBATCH --account=uj24
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --array=0-6
#SBATCH --output=v4_sf_domain_%A_%a.log
# Reviewer comment 8: domain size / top boundary / medium renewal, v4 surface film at the calibrated centre (k_f 3e5, k_d 1e8, k_ORR 80, delta_f 1 um).
cd /fs04/uj24/zinc_simulation_v4 || exit 1
A=/fs04/uj24/zinc_simulation/ablation_meshes
case $SLURM_ARRAY_TASK_ID in
 0) L=box15_top;    MESH=disc_10x2_coarse_box15_topinlet.mesh; T=168; X="";;
 1) L=box30_top;    MESH=disc_10x2_coarse_box30_topinlet.mesh; T=168; X="";;
 2) L=box60_top;    MESH=disc_10x2_coarse_box60_topinlet.mesh; T=168; X="";;
 3) L=box30_allopen; MESH=disc_10x2_coarse_box30.mesh;         T=168; X="-tag_inlet 3";;
 4) L=box30_closed; MESH=disc_10x2_coarse_box30.mesh;          T=168; X="";;
 5) L=h1_noreset;   MESH=disc_10x2_hmin1.0_topinlet.mesh;      T=336; X="";;
 6) L=h1_reset48;   MESH=disc_10x2_hmin1.0_topinlet.mesh;      T=336; X="-medium_reset_hours 48";;
esac
OUTDIR="output_sfdom_${L}"; mkdir -p "$OUTDIR"
module load singularity
SIF_PATH=~/software/freefem.sif
srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "$MESH" -dt_hours 4.0 -sim_duration $T -save_interval 4.0 \
    -k_orr 80 -k_f 300000 -k_d 100000000 -film_tortuosity 120.0 -conservative 2 -film_mode 1 -film_thickness 0.001 -kf_rate_units 1 -kd_mass_units 1 -o2_relax_omega 1.0 -o2_relax_scale_dt 0 $X \
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -checkpoint_each_time $T -checkpoint_dir "$OUTDIR" -results_file "$OUTDIR/result_disc.txt" \
    -emit_vtk 0 -dump_final_state 0 -export_geometry 0
