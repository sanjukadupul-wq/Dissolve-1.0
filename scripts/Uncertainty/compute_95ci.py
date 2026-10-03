# -*- coding: utf-8 -*-
"""
Post-hoc 95% confidence interval for the joint BO calibration
(k_f, k_d, k_orr), computed entirely from final_all_evaluations.txt --
no new FreeFEM runs. Two intervals are reported, answering two different
questions:

1. Predicted-RMSE CI at the calibrated point: refits the exact GP used by
   score_combined.py (same kernel, same log10-normalization, same bounds)
   on all 32 trials, then mu +/- 1.96*sigma at the best point.

2. Parameter CI (the one that matters for reporting k_orr/k_f/k_d
   uncertainty): bootstrap over the 32 trials. Resample with replacement,
   refit the GP, find its posterior minimum over a dense random candidate
   set, repeat N times, and take the 2.5/97.5 percentiles of the resulting
   k_f/k_d/k_orr minima as the 95% CI. This is the standard way to turn a
   GP/BO trial history into a parameter interval when nothing in the
   original pipeline (score_global.py/score_combined.py/generate_doe_*.py)
   computed one directly.
"""
import os
import warnings
import numpy as np
import pandas as pd
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel
from sklearn.exceptions import ConvergenceWarning

warnings.filterwarnings("ignore", category=ConvergenceWarning)

DIR = os.path.dirname(os.path.abspath(__file__))
N_BOOTSTRAP = 400
N_CAND = 20000
RNG_SEED = 42

BOUNDS = {
    "k_f":   (1.0, 100.0),
    "k_d":   (5.0, 100.0),
    "k_orr": (0.05, 5.0),
}
names = list(BOUNDS.keys())
lo = np.log10([BOUNDS[n][0] for n in names])
hi = np.log10([BOUNDS[n][1] for n in names])
mid = (lo + hi) / 2.0
half_range = (hi - lo) / 2.0


def normalize(log_params):
    return (log_params - mid) / half_range


def make_gp(n_restarts=20):
    kernel = (Matern(length_scale=[1.0, 1.0, 1.0], length_scale_bounds=(0.05, 5.0), nu=2.5)
              + WhiteKernel(noise_level=1e-3, noise_level_bounds=(1e-5, 1e-1)))
    return GaussianProcessRegressor(kernel=kernel, normalize_y=True,
                                     n_restarts_optimizer=n_restarts, random_state=0)


# -----------------------------------------------------------------------
# Load all 32 trials
# -----------------------------------------------------------------------
data = pd.read_csv(os.path.join(DIR, "final_all_evaluations.txt"), sep=r"\s+")
print(f"Loaded {len(data)} BO trials from final_all_evaluations.txt")

X_log_full = np.column_stack([np.log10(data[n].values) for n in names])
X_norm_full = normalize(X_log_full)
y_full = data["rmse"].values

best_idx = int(np.argmin(y_full))
best_row = data.iloc[best_idx]
print(f"\nBest evaluated trial: k_f={best_row.k_f:.4f} k_d={best_row.k_d:.4f} "
      f"k_orr={best_row.k_orr:.4f}  RMSE={best_row.rmse:.5f}%  "
      f"(iteration {int(best_row.iteration)}, stage={best_row.stage})")

# -----------------------------------------------------------------------
# 1. Predicted-RMSE 95% CI at the best point (refit on all 32 points)
# -----------------------------------------------------------------------
gp_full = make_gp()
gp_full.fit(X_norm_full, y_full)

x_best_norm = X_norm_full[best_idx:best_idx + 1]
mu_best, sigma_best = gp_full.predict(x_best_norm, return_std=True)
ci_lo = mu_best[0] - 1.96 * sigma_best[0]
ci_hi = mu_best[0] + 1.96 * sigma_best[0]
print(f"\n[1] GP-predicted RMSE at the best point (refit on all 32 trials):")
print(f"    mu={mu_best[0]:.5f}%  sigma={sigma_best[0]:.5f}%")
print(f"    95% CI on predicted RMSE: [{ci_lo:.5f}%, {ci_hi:.5f}%]")

# -----------------------------------------------------------------------
# 2. Bootstrap 95% CI on the calibrated PARAMETERS (k_f, k_d, k_orr)
# -----------------------------------------------------------------------
rng = np.random.default_rng(RNG_SEED)
n = len(data)
boot_minima = np.empty((N_BOOTSTRAP, 3))
cand_log = lo + rng.random((N_CAND, 3)) * (hi - lo)
cand_norm = normalize(cand_log)

print(f"\n[2] Bootstrapping {N_BOOTSTRAP} GP refits (resampling {n} trials with "
      f"replacement each time)...")
n_failed = 0
for b in range(N_BOOTSTRAP):
    idx = rng.integers(0, n, size=n)
    Xb = X_norm_full[idx]
    yb = y_full[idx]
    try:
        gp_b = make_gp(n_restarts=3)
        gp_b.fit(Xb, yb)
        mu_b = gp_b.predict(cand_norm)
        best_b = int(np.argmin(mu_b))
        boot_minima[b] = 10 ** cand_log[best_b]
    except Exception:
        boot_minima[b] = np.nan
        n_failed += 1
    if (b + 1) % 500 == 0:
        print(f"    {b + 1}/{N_BOOTSTRAP} done", flush=True)

if n_failed:
    print(f"    ({n_failed} bootstrap refits failed and were dropped)")
boot_minima = boot_minima[~np.isnan(boot_minima).any(axis=1)]

print(f"\n95% bootstrap CI on the calibrated parameters "
      f"({len(boot_minima)} successful bootstrap refits):")
for i, n_ in enumerate(names):
    vals = boot_minima[:, i]
    p2_5, p50, p97_5 = np.percentile(vals, [2.5, 50, 97.5])
    point_est = float(best_row[n_])
    print(f"    {n_:6s}: point estimate={point_est:.4f}   "
          f"bootstrap median={p50:.4f}   95% CI=[{p2_5:.4f}, {p97_5:.4f}]")

out_path = os.path.join(DIR, "bo_bootstrap_minima.csv")
pd.DataFrame(boot_minima, columns=names).to_csv(out_path, index=False, float_format="%.6f")
print(f"\nSaved raw bootstrap minima ({len(boot_minima)} rows) to {out_path}")
