# Final mass-loss Bayesian optimisation (repeat 1)

Scripts, designs and results of the mass-loss-only calibration of `k_f`, `k_d` and `k_ORR` on the 10 x 2 mm disc (coarse mesh, 336 h), run on the v2 solver. This is the 28-evaluation repeat reported in the paper.

## Workflow

| Phase | Points | How the points were chosen | Files |
|---|---|---|---|
| 1 | 12 | Global Latin-hypercube design over `k_f` 1-100, `k_d` 1-100, `k_ORR` 0.05-5 (log scale) | `doe_design_global.csv`, `run_bo_v2_doe_global.slurm`, `phase1_scores.csv` |
| 2 | 8 | Expected improvement on a Matern 2.5 GP fitted to log10 RMSE | `propose_phase2_v2.py`, `doe_design_phase2.csv`, `run_bo_v2_phase2.slurm`, `phase2_scores.csv` |
| 3 | 8 | Local expected improvement on mass loss only; axes whose GP length scale is at its upper bound (`k_f`, `k_d`) are stratified by Latin hypercube within a factor 3 of the best point | `propose_phase3_massloss.py`, `doe_design_phase3b.csv`, `run_bo_v2_phase3b.slurm` |

`objective_v2.py` scores a run against `target_jmst2018.csv` (Liu et al., 2018, DOI 10.1016/j.jmst.2018.05.005) over t = 24-336 h. The simulated mass loss is first corrected from the coarse to the fine mesh (1.355846 x - 0.001584); the corrosion rate it also reports is the cumulative-average penetration rate. The Phase 3 objective is the mass-loss RMSE only.

`propose_phase3_massloss.py` is run inside the repeat's folder as `python propose_phase3_massloss.py <EI_seed> <LHS_seed>` and reads `combined_objective_scores.csv` (the 20 Phase 1 + 2 evaluations).

## Results

| File | Content |
|---|---|
| `optimization_runs_v2_massloss_rep1.csv` | All 28 evaluations: parameters, mass-loss RMSE (%), mass loss at the end of the run (%) and stage |
| `combined_objective_scores_all28.csv` | The same 28 runs with the combined mass-loss + corrosion-rate objective J |
| `combined_objective_scores.csv` | The 20 Phase 1 + 2 evaluations used to fit the Phase 3 GP |

Lowest mass-loss RMSE: run 25, `k_f` = 2.7468, `k_d` = 5.1937, `k_ORR` = 0.1612 (RMSE 0.0173 %, mass loss 0.339 %).

## Notes

- Parameters are in the units of the v2 solver used for this calibration. The v4 solver uses different units for `k_f`, `k_d` and `k_ORR`, so these values cannot be used directly with `Src Codes/` as it now stands; the v4 calibration inputs are in `Scripts/v4/`.
- The SLURM files keep their cluster paths and account name. The solver paths and flags (dt = 4 h, 336 h, redistancing off, `-film_tortuosity 120`) are those used for the runs; see `Src Codes/README.md` before re-running them elsewhere.
