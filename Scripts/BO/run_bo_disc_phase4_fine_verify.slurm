#!/bin/bash
#SBATCH --job-name=zn_bo_disc_p4fine
#SBATCH --account=uj24
#SBATCH --time=03:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --cpus-per-task=1
#SBATCH --mem=32G
#SBATCH --constraint=intel
#SBATCH --output=bo_disc_phase4_fine_%j.log
#SBATCH --mail-type=END,FAIL

# Phase 4: fine-mesh verification of the final calibrated point found by
# the coarse-mesh BO (global search -> dip verification -> local
# refinement, 32 total coarse evaluations, best coarse+corrected
# RMSE=0.0424% against target_jmst2018.csv):
#   k_f=35.9058, k_d=27.1696, k_orr=0.5075
# Run on the ACTUAL fine mesh (disc_10x2_hmin0.25.mesh) -- no bias
# correction needed here, this is the real fine-mesh result. Confirms
# whether the coarse+correction search found a genuine optimum or an
# artifact of the correction. sim_duration=336h (target only extends to
# 336h). Same OLD-physics codebase as every other run in this study.

module load singularity
SIF_PATH=~/software/freefem.sif
cd /fs04/uj24/zinc_simulation || { echo "FATAL: could not cd to /fs04/uj24/zinc_simulation"; exit 1; }
mkdir -p bo_disc_coarse_joint/output_phase4_fine_verify/vtk

srun --mpi=pmi2 singularity exec --bind /fs04 $SIF_PATH FreeFem++-mpi -nw dissolve.edp -v 0 \
    -input_mesh "disc_10x2_hmin0.25.mesh" \
    -dt_hours 4.0 -sim_duration 336.0 -save_interval 4.0 \
    -k_orr 0.5075 -k_f 35.9058 -k_d 27.1696 -film_tortuosity 120.0 \
    -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \
    -checkpoint_each_time 24 -checkpoint_dir bo_disc_coarse_joint/output_phase4_fine_verify \
    -results_file "bo_disc_coarse_joint/output_phase4_fine_verify/result_disc.txt" \
    -emit_vtk 1 -save_vtk_each_time 8 -vtk_prefix "bo_disc_coarse_joint/output_phase4_fine_verify/vtk/output" \
    -dump_final_state 0 -export_geometry 0
