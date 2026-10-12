# Final mass-loss BO scripts (repeat 1)

Proposal and scoring scripts for the mass-loss-only calibration of `k_f`, `k_d` and `k_ORR` on the 10 x 2 mm disc (v2 solver). Only the Python scripts are distributed; the DoE designs, score tables and run outputs are not included.

| Script | Role |
|---|---|
| `propose_phase2_v2.py` | Phase 2: fits a Matern 2.5 GP to the Phase 1 scores (`phase1_scores.csv`) and proposes 8 points by expected improvement |
| `propose_phase3_massloss.py` | Phase 3: local expected improvement on the mass-loss RMSE (`combined_objective_scores.csv`); run as `python propose_phase3_massloss.py <EI_seed> <LHS_seed>` |
| `objective_v2.py` | Scores a run against the calibration target (Liu et al., 2018, DOI 10.1016/j.jmst.2018.05.005) over 24-336 h, after the coarse-to-fine mesh correction |

The scripts read their inputs (`phase1_scores.csv`, `combined_objective_scores.csv`, `target_jmst2018.csv`) from the folder they are run in.
