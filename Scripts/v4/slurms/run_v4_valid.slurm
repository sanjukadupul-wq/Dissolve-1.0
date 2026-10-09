#!/bin/bash
#SBATCH --job-name=zn_v4_valid
#SBATCH --account=uj24
#SBATCH --time=03:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --array=0-1
#SBATCH --output=v4_valid_%A_%a.log
# v4 conservation validation, 672 h, k_ORR 5.158 (= 32 x 0.1612), mode 2, O2 under-relaxation off (omega=1) so the O2 update equals the sink.
# 0: closed box   1: open box, Dirichlet O2 on the TOP face only (z=+15 relabelled 4 = inlet)
cd /fs04/uj24/zinc_simulation_v4 || exit 1
case $SLURM_ARRAY_TASK_ID in
 0) L=val_closed; MESH=disc_10x2_coarse_hmin0.5.mesh;;
 1) L=val_top;    MESH=disc_10x2_coarse_hmin0.5_topinlet.mesh;;
esac
OUTDIR="output_v4_${L}"; mkdir -p "$OUTDIR/vtk"
module load singularity
SIF_PATH=~/software/freefem.sif
srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "$MESH" \
    -dt_hours 4.0 -sim_duration 672.0 -save_interval 4.0 \
    -k_orr 5.158 -k_f 2.7468 -k_d 5.1937 -film_tortuosity 120.0 -conservative 2 -o2_relax_omega 1.0 -o2_relax_scale_dt 0 \
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -checkpoint_each_time 672 -checkpoint_dir "$OUTDIR" \
    -results_file "$OUTDIR/result_disc.txt" \
    -emit_vtk 1 -save_vtk_each_time 24 -vtk_prefix "$OUTDIR/vtk/output" -dump_final_state 0 -export_geometry 0
