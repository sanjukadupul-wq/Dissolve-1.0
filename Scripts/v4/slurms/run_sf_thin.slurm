#!/bin/bash
#SBATCH --job-name=zn_v4_sf_thin
#SBATCH --account=uj24
#SBATCH --time=02:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --array=0-6
#SBATCH --output=v4_sf_thin_%A_%a.log
# v4 surface-film recalibration, phase 1 (16 round-number points): coarse disc, top-face Dirichlet O2, conservative mode 2, omega=1, 336 h.
cd /fs04/uj24/zinc_simulation_v4 || exit 1
case $SLURM_ARRAY_TASK_ID in
 0) DF=0.001;  KF=1000000; KD=1000000; KORR=40;;
 1) DF=0.001;  KF=1000000; KD=1000000; KORR=60;;
 2) DF=0.001;  KF=1000000; KD=1000000; KORR=100;;
 3) DF=0.0005; KF=4000000; KD=1000000; KORR=60;;
 4) DF=0.0005; KF=4000000; KD=1000000; KORR=100;;
 5) DF=0.001;  KF=3000000; KD=1000000; KORR=60;;
 6) DF=0.002;  KF=250000;  KD=1000000; KORR=40;;
esac
OUTDIR="bo_sf/thin_run${SLURM_ARRAY_TASK_ID}"; mkdir -p "$OUTDIR"
module load singularity
SIF_PATH=~/software/freefem.sif
srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "disc_10x2_coarse_hmin0.5_topinlet.mesh" -dt_hours 4.0 -sim_duration 336.0 -save_interval 4.0 \
    -k_orr "$KORR" -k_f "$KF" -k_d "$KD" -film_tortuosity 120.0 -conservative 2 -film_mode 1 -film_thickness $DF -kf_rate_units 1 -kd_mass_units 1 -o2_relax_omega 1.0 -o2_relax_scale_dt 0 \
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -checkpoint_each_time 336 -checkpoint_dir "$OUTDIR" -results_file "$OUTDIR/result_disc.txt" \
    -emit_vtk 0 -dump_final_state 0 -export_geometry 0
