# Scripts/

Calibration, sensitivity and uncertainty tooling for the Dissolve solver.
Install dependencies with `pip install -r requirements.txt`. The solver-driving
scripts expect to be run from the repository root and call `Src Codes/dissolve.edp`.

| Folder | Contents |
|---|---|
| `BO/` | `calibrate_bayesian.py`: generic GP Bayesian-optimization driver for kf / kd / kORR, and `optimization_results.xlsx` (results of the earlier calibration). |
| `BO/final_massloss_rep1/` | The final mass-loss-only BO reported in the paper (repeat 1, 28 evaluations): Phase 2 and 3 proposal scripts, the objective, designs, SLURM jobs, target data and the evaluations table. See its README. |
| `GSA/` | `sensitivity_morris.py`: Morris global sensitivity analysis, and `run_gsa_full_v2.slurm`: the 180-run (r = 20 x 8 parameters) cluster array job. |
| `Uncertainty/` | `compute_95ci.py`: post-hoc GP/bootstrap 95 % intervals from the 32 BO trials in `final_all_evaluations.txt` (taken from the paper's Figure 3b source data); needs no new FreeFEM runs. |

The `.slurm` files are the cluster job
definitions used for the calibration. Film tortuosity is set to the paper's
value. They still carry cluster paths and the
cluster-era numerical flags (dt = 4 h, 336 h, redistancing off); see
`Src Codes/README.md` for the paper's current solver defaults before
re-running them.
