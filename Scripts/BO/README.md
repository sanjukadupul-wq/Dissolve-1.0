# Final mass-loss BO scripts

Proposal and scoring scripts for the mass-loss-only calibration of `k_f`, `k_d` and `k_ORR` on the 10 x 2 mm disc (v2 solver). Only the Python scripts are distributed; the DoE designs, score tables and run outputs are not included.

| Script | Role |
|---|---|
| `propose_phase2_v2.py` | Phase 2: fits a Matern 2.5 GP to the Phase 1 scores (`phase1_scores.csv`) and proposes 8 points by expected improvement |
| `propose_phase3_massloss.py` | Phase 3: local expected improvement on the mass-loss RMSE (`combined_objective_scores.csv`); run as `python propose_phase3_massloss.py <EI_seed> <LHS_seed>` |
| `objective_v2.py` | Scores a run against the calibration target (Liu et al., 2018, DOI 10.1016/j.jmst.2018.05.005) over 24-336 h, after the coarse-to-fine mesh correction |

The scripts read their inputs (`phase1_scores.csv`, `combined_objective_scores.csv`, `target_jmst2018.csv`) from the folder they are run in.

**Solver flags.** These scripts do not launch the solver: they propose parameter sets and score results from runs you make. Run every
calibration evaluation with the v1.1.0 formulation given explicitly, not only through the code defaults:

```bash
-flux_first 1 -v_picard 0 -conservative 2 -oh_fix 1 -film_mode 1 -kf_rate_units 1 -kd_mass_units 1
```

The parameter bounds and units hard-coded in `propose_phase2_v2.py` and `propose_phase3_massloss.py` belong to the earlier (v2-solver)
search and are not the search ranges of the revised study (see `Src Codes/THEORY.md`, Section 9); set them before reuse.
