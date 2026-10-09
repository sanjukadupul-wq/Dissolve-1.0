#!/bin/bash
#SBATCH --job-name=zn_sf_fine
#SBATCH --account=uj24
#SBATCH --time=12:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=16
#SBATCH --cpus-per-task=1
#SBATCH --mem=64G
#SBATCH --constraint=intel
#SBATCH --array=0-5
#SBATCH --output=v4_sf_fine_%A_%a.log
# Fine-mesh (hmin0.25) partners of six hmin1.0 film-calibration runs (h1p1 runs 0,1,5,7,8,13): same parameters, 336 h, film thickness 1 um.
cd /fs04/uj24/zinc_simulation_v4 || exit 1
case $SLURM_ARRAY_TASK_ID in
 0) L=h1p1_0;  KF=100000;  KD=10000000;  KORR=120;;
 1) L=h1p1_1;  KF=100000;  KD=10000000;  KORR=60;;
 2) L=h1p1_5;  KF=3000000; KD=100000000; KORR=40;;
 3) L=h1p1_7;  KF=1000000; KD=1000000;   KORR=40;;
 4) L=h1p1_8;  KF=300000;  KD=100000000; KORR=80;;
 5) L=h1p1_13; KF=100000;  KD=100000000; KORR=60;;
esac
OUTDIR="bo_sf/fine_${L}"; mkdir -p "$OUTDIR"
module load singularity
SIF_PATH=~/software/freefem.sif
srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "disc_10x2_hmin0.25_topinlet.mesh" -dt_hours 4.0 -sim_duration 336.0 -save_interval 4.0 \
    -k_orr "$KORR" -k_f "$KF" -k_d "$KD" -film_tortuosity 120.0 -conservative 2 -film_mode 1 -film_thickness 0.001 -kf_rate_units 1 -kd_mass_units 1 -o2_relax_omega 1.0 -o2_relax_scale_dt 0 \
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -checkpoint_each_time 336 -checkpoint_dir "$OUTDIR" -results_file "$OUTDIR/result_disc.txt" \
    -emit_vtk 0 -dump_final_state 0 -export_geometry 0
