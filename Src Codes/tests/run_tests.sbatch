#!/bin/bash
#SBATCH --job-name=dissolve_tests
#SBATCH --time=04:00:00
#SBATCH --nodes=1
#SBATCH --ntasks=4
#SBATCH --mem=16G
#SBATCH --output=dissolve_tests_%j.log
# Regression tests for Dissolve v1.1.0 (flux-first interface coupling).
# Required environment:
#   MESH          closed-box disc mesh (30 x 30 x 30 mm box, tag 3 = wall; no inlet)
#   MESH_INLET    open-top disc mesh (top face tag 4 = oxygen inlet)
# Optional environment:
#   SOLVER_DIR    Src Codes directory (required under Slurm; default when run locally: parent of this tests/ folder)
#   OUT_DIR       output directory (default: ./tests_out_<jobid>)
#   FREEFEM_SIF   Singularity/Apptainer image providing FreeFem++-mpi (required unless FREEFEM_CMD is set)
#   FREEFEM_BIND  directory to bind into the container so meshes and outputs are visible (e.g. /scratch); optional
#   FREEFEM_CMD   overrides the whole FreeFem++-mpi launch command (e.g. a native install)
# Usage: sbatch --account=<account> run_tests.sbatch      (or: bash run_tests.sbatch on a workstation)
set -u
if [ -z "${SOLVER_DIR:-}" ]; then
  if [ -n "${SLURM_JOB_ID:-}" ]; then echo "Under Slurm, set SOLVER_DIR to the Src Codes directory (the batch script is copied to a spool directory)."; exit 1; fi
  SOLVER_DIR=$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)
fi
: "${MESH:?set MESH to the closed-box disc mesh}"; : "${MESH_INLET:?set MESH_INLET to the open-top disc mesh}"
T=${OUT_DIR:-./tests_out_${SLURM_JOB_ID:-local}}; mkdir -p "$T"
if [ -z "${FREEFEM_CMD:-}" ]; then
  : "${FREEFEM_SIF:?set FREEFEM_SIF (Singularity/Apptainer image with FreeFem++-mpi) or set FREEFEM_CMD}"
  module load singularity 2>/dev/null || true
  FREEFEM_CMD="srun --mpi=pmi2 singularity exec ${FREEFEM_BIND:+--bind $FREEFEM_BIND} $FREEFEM_SIF FreeFem++-mpi -nw"
fi
cd "$SOLVER_DIR"
FF="$FREEFEM_CMD dissolve.edp -v 0"
COMMON="-save_interval 4 -emit_vtk 0 -dump_final_state 0 -export_geometry 0 -flux_first 1 -v_picard 0 -conservative 2 -oh_fix 1"
run() { d=$1; shift; mkdir -p "$T/$d"; $FF "$@" -checkpoint_each_time 168 -checkpoint_dir "$T/$d" -results_file "$T/$d/result_disc.txt" > "$T/$d/run.log" 2>&1; echo $? > "$T/$d/exit_code"; }
run closed         -input_mesh "$MESH" -dt_hours 4 -sim_duration 168 $COMMON
run closed_noreinit -input_mesh "$MESH" -dt_hours 4 -sim_duration 168 $COMMON -enable_redistance 0
run open_film      -input_mesh "$MESH_INLET" -tag_inlet 4 -dt_hours 4 -sim_duration 168 $COMMON -o2_initial 6.2e-9 -k_orr 200 -k_f 4e5 -k_d 3e6
# defaults only: no coupling flags are given, so this run verifies that the code defaults select the flux-first formulation
run defaults_closed -input_mesh "$MESH" -dt_hours 4 -sim_duration 168 -save_interval 4 -emit_vtk 0 -dump_final_state 0 -export_geometry 0
# film-barrier option (-film_mech 1): exponential barrier on the ORR, uncapped retained film; beta = 0 is the no-barrier reference.
# -flux_proj_tol 1e-3: on the coarse test mesh the default 1e-4 stops the beta = 12 run (projection residual 1.2e-4 before the exact rescaling).
run film_mech1_b0  -input_mesh "$MESH_INLET" -tag_inlet 4 -dt_hours 4 -sim_duration 168 $COMMON -o2_initial 6.2e-9 -k_orr 200 -k_f 4e5 -k_d 3e6 -film_mech 1 -film_beta 0 -film_beta_couple 1 -flux_proj_tol 1e-3
run film_mech1_b12 -input_mesh "$MESH_INLET" -tag_inlet 4 -dt_hours 4 -sim_duration 168 $COMMON -o2_initial 6.2e-9 -k_orr 200 -k_f 4e5 -k_d 3e6 -film_mech 1 -film_beta 12 -film_beta_couple 1 -flux_proj_tol 1e-3
# guard checks: inconsistent flags and projection imbalance must fail closed
run guard_picard   -input_mesh "$MESH" -dt_hours 4 -sim_duration 8 -save_interval 4 -emit_vtk 0 -dump_final_state 0 -export_geometry 0 -flux_first 1 -v_picard 2 -conservative 2
run guard_cons     -input_mesh "$MESH" -dt_hours 4 -sim_duration 8 -save_interval 4 -emit_vtk 0 -dump_final_state 0 -export_geometry 0 -flux_first 1 -v_picard 0 -conservative 0
run guard_proj     -input_mesh "$MESH" -dt_hours 4 -sim_duration 8 $COMMON -flux_proj_tol 1e-30
python3 "$SOLVER_DIR/tests/check.py" "$T" "$SOLVER_DIR"
rc=$?; echo "exit code $rc"; exit $rc
