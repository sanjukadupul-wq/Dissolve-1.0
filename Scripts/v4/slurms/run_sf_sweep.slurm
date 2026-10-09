#!/bin/bash
#SBATCH --job-name=zn_sf_sweep
#SBATCH --account=uj24
#SBATCH --time=01:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --array=0-6
#SBATCH --output=v4_sf_sweep_%A_%a.log
# Final one-at-a-time sweeps, v4 surface film, hmin1.0 mesh, 168 h, VTK every 4 h. Centre k_f 3e5 h-1, k_d 1e8 mm6 g-2 h-1, k_ORR 80 mm h-1 (film thickness 1 um, tau 120, rho_film 3.998).
cd /fs04/uj24/zinc_simulation_v4 || exit 1
case $SLURM_ARRAY_TASK_ID in
 0) L=mid;      KF=300000;  KD=100000000; KORR=80;;
 1) L=kf_lo;    KF=43000;   KD=100000000; KORR=80;;
 2) L=kf_hi;    KF=1300000; KD=100000000; KORR=80;;
 3) L=kd_lo;    KF=300000;  KD=19000000;  KORR=80;;
 4) L=kd_hi;    KF=300000;  KD=440000000; KORR=80;;
 5) L=korr_lo;  KF=300000;  KD=100000000; KORR=16;;
 6) L=korr_hi;  KF=300000;  KD=100000000; KORR=400;;
esac
OUTDIR="output_sfsweep_${L}"; mkdir -p "$OUTDIR/vtk"
module load singularity
SIF_PATH=~/software/freefem.sif
srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "disc_10x2_hmin1.0_topinlet.mesh" -dt_hours 4.0 -sim_duration 168.0 -save_interval 4.0 \
    -k_orr "$KORR" -k_f "$KF" -k_d "$KD" -film_tortuosity 120.0 -conservative 2 -film_mode 1 -film_thickness 0.001 -kf_rate_units 1 -kd_mass_units 1 -o2_relax_omega 1.0 -o2_relax_scale_dt 0 \
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -checkpoint_each_time 168 -checkpoint_dir "$OUTDIR" -results_file "$OUTDIR/result_disc.txt" \
    -emit_vtk 1 -save_vtk_each_time 4 -vtk_prefix "$OUTDIR/vtk/output" -dump_final_state 0 -export_geometry 0
