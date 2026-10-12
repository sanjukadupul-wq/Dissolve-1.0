# Scripts/

Calibration, sensitivity and uncertainty tooling for the Dissolve solver.
Install dependencies with `pip install -r requirements.txt`. The solver-driving
scripts expect to be run from the repository root and call `Src Codes/dissolve.edp`.

| Folder | Contents |
|---|---|
| `BO/` | `calibrate_bayesian.py`: Gaussian-process Bayesian-optimization driver for kf / kd / kORR (settings as in Supporting Information Table S9). |
| `BO/final_massloss_rep1/` | Python scripts of the final mass-loss-only BO (Phase 2 and 3 proposals and the objective). See its README. |
| `GSA/` | `sensitivity_morris.py`: Morris global sensitivity analysis with the ranges and design of Supporting Information Tables S4 and S5, and `run_gsa_full_v2.slurm`: the 180-run (r = 20 x 8 parameters) cluster array job. |
| `Uncertainty/` | `compute_95ci.py`: post-hoc GP/bootstrap 95 % intervals from the 32 BO trials in `final_all_evaluations.txt` (taken from the paper's Figure 3b source data); needs no new FreeFEM runs. |

The `.slurm` files are the cluster job
definitions used for the calibration. Film tortuosity is set to the paper's
value. They still carry cluster paths and the
cluster-era numerical flags (dt = 4 h, 336 h, redistancing off); see
`Src Codes/README.md` for the paper's current solver defaults before
re-running them.
