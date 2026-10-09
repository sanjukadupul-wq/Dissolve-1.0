#!/bin/bash
#SBATCH --job-name=zn_sf_final
#SBATCH --account=uj24
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --array=0-1
#SBATCH --output=v4_sf_final_%A_%a.log
# Reviewer comment 12: Zn and O2 balance of the final model to 672 h (top-face O2 and closed-box reference), hmin1.0 mesh.
# Baseline: k_f 3e5 h-1, k_d 1e8 mm6 g-2 h-1, k_ORR 80, delta_f 1 um, tau 120, eps 0.25, rho_film 3.998 g/cm3.
cd /fs04/uj24/zinc_simulation_v4 || exit 1
case $SLURM_ARRAY_TASK_ID in
 0) L=top;    MESH=disc_10x2_hmin1.0_topinlet.mesh; X="";;
 1) L=closed; MESH=disc_10x2_hmin1.0.mesh;          X="";;
esac
OUTDIR="output_sffinal_${L}"; mkdir -p "$OUTDIR"
module load singularity
SIF_PATH=~/software/freefem.sif
srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "$MESH" -dt_hours 4.0 -sim_duration 672.0 -save_interval 4.0 \
    -k_orr 80 -k_f 300000 -k_d 100000000 -film_tortuosity 120.0 -film_thickness 0.001 -conservative 2 -film_mode 1 -kf_rate_units 1 -kd_mass_units 1 -o2_relax_omega 1.0 -o2_relax_scale_dt 0 $X \
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -checkpoint_each_time 672 -checkpoint_dir "$OUTDIR" -results_file "$OUTDIR/result_disc.txt" \
    -emit_vtk 0 -dump_final_state 0 -export_geometry 0
