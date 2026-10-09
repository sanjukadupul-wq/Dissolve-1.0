#!/bin/bash
#SBATCH --job-name=zn_sf_dtconv
#SBATCH --account=uj24
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --array=0-8
#SBATCH --output=v4_sf_dtconv_%A_%a.log
# Reviewer comment 16: time-step and level-set re-initialisation convergence, v4 surface film at the calibrated centre, hmin1.0 mesh, 72 h.
# 0-5: dt = 4, 2, 1, 0.5, 0.25, 0.125 h without re-initialisation.  6-8: dt = 0.25 h with re-initialisation every 0.5, 1, 2 h.
cd /fs04/uj24/zinc_simulation_v4 || exit 1
case $SLURM_ARRAY_TASK_ID in
 0) L=dt4;      DT=4.0;   X="-enable_redistance 0";;
 1) L=dt2;      DT=2.0;   X="-enable_redistance 0";;
 2) L=dt1;      DT=1.0;   X="-enable_redistance 0";;
 3) L=dt0p5;    DT=0.5;   X="-enable_redistance 0";;
 4) L=dt0p25;   DT=0.25;  X="-enable_redistance 0";;
 5) L=dt0p125;  DT=0.125; X="-enable_redistance 0";;
 6) L=rd0p5;    DT=0.25;  X="-enable_redistance 1 -redistance_interval 0.5";;
 7) L=rd1;      DT=0.25;  X="-enable_redistance 1 -redistance_interval 1.0";;
 8) L=rd2;      DT=0.25;  X="-enable_redistance 1 -redistance_interval 2.0";;
esac
OUTDIR="output_sfdt_${L}"; mkdir -p "$OUTDIR"
module load singularity
SIF_PATH=~/software/freefem.sif
srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "disc_10x2_hmin1.0_topinlet.mesh" -dt_hours $DT -sim_duration 72.0 -save_interval 4.0 \
    -k_orr 80 -k_f 300000 -k_d 100000000 -film_tortuosity 120.0 -film_thickness 0.001 -conservative 2 -film_mode 1 -kf_rate_units 1 -kd_mass_units 1 -o2_relax_omega 1.0 -o2_relax_scale_dt 0 $X \
    -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -checkpoint_each_time 72 -checkpoint_dir "$OUTDIR" -results_file "$OUTDIR/result_disc.txt" \
    -emit_vtk 0 -dump_final_state 0 -export_geometry 0
