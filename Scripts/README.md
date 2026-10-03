# Scripts/

Calibration, sensitivity and uncertainty tooling for the Dissolve solver.
Install dependencies with `pip install -r requirements.txt`. The solver-driving
scripts expect to be run from the repository root and call `Src Codes/dissolve.edp`.

| Folder | Contents |
|---|---|
| `BO/` | Bayesian optimization of kf / kd / kORR: `calibrate_bayesian.py` (driver), `generate_doe_global.py` (12-point global LHS), `generate_doe.py` (local LHS), `generate_verify_dip.py` (dip verification), `generate_doe_phase3_local.py` (local refinement around the best point), `score_global.py` (scores the global DoE and proposes the Phase 2 EI-guided points), the SLURM jobs (`run_bo_disc_joint_doe.slurm`, `..._doe_global.slurm`, `..._phase2.slurm`, `..._phase3_local.slurm`, `run_bo_disc_verify_dip.slurm` and the fine-mesh check `run_bo_disc_phase4_fine_verify.slurm`), `target_jmst2018.csv` (calibration target, Liu et al. 2018) and `optimization_results.xlsx`. |
| `GSA/` | `sensitivity_morris.py`: Morris global sensitivity analysis, and `run_gsa_full_v2.slurm`: the 180-run (r = 20 x 8 parameters) cluster array job. |
| `Uncertainty/` | `compute_95ci.py`: post-hoc GP/bootstrap 95 % intervals from the 32 BO trials in `final_all_evaluations.txt` (taken from the paper's Figure 3b source data); needs no new FreeFEM runs. |

The `generate_doe*.py` scripts and the `.slurm` files are the cluster job
definitions used for the calibration. Film tortuosity is set to the paper's
value (`-film_tortuosity 2.0`). They still carry cluster paths and the
cluster-era numerical flags (dt = 4 h, 336 h, redistancing off); see
`Src Codes/README.md` for the paper's current solver defaults before
re-running them.
