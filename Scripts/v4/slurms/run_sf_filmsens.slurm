#!/bin/bash
#SBATCH --job-name=zn_sf_filmsens
#SBATCH --account=uj24
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --array=0-10
#SBATCH --output=v4_sf_filmsens_%A_%a.log
# Reviewer comment 10: sensitivity to film porosity, tortuosity, density and thickness (one at a time), hmin1.0 mesh, 336 h.
# Baseline: k_f 3e5 h-1, k_d 1e8 mm6 g-2 h-1, k_ORR 80, delta_f 1 um, tau 120, eps 0.25, rho_film 3.998 g/cm3.
cd /fs04/uj24/zinc_simulation_v4 || exit 1
case $SLURM_ARRAY_TASK_ID in
 0) L=base;      X="";;
 1) L=eps0p10;   X="-film_porosity 0.10";;
 2) L=eps0p40;   X="-film_porosity 0.40";;
 3) L=tau2;      X="-film_tortuosity 2.0";;
 4) L=tau10;     X="-film_tortuosity 10.0";;
 5) L=tau500;    X="-film_tortuosity 500.0";;
 6) L=rho3p0;    X="-rho_film 0.003";;
 7) L=rho5p606;  X="-rho_film 0.005606";;
 8) L=df0p5;     X="-film_thickness 0.0005";;
 9) L=df2;       X="-film_thickness 0.002";;
 10) L=df5;      X="-film_thickness 0.005";;
esac
OUTDIR="output_sffs_${L}"; mkdir -p "$OUTDIR"
module load singularity
SIF_PATH=~/software/freefem.sif
srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "disc_10x2_hmin1.0_topinlet.mesh" -dt_hours 4.0 -sim_duration 336.0 -save_interval 4.0 \
    -k_orr 80 -k_f 300000 -k_d 100000000 -film_tortuosity 120.0 -film_thickness 0.001 -conservative 2 -film_mode 1 -kf_rate_units 1 -kd_mass_units 1 -o2_relax_omega 1.0 -o2_relax_scale_dt 0 $X \
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -checkpoint_each_time 336 -checkpoint_dir "$OUTDIR" -results_file "$OUTDIR/result_disc.txt" \
    -emit_vtk 0 -dump_final_state 0 -export_geometry 0
