"""
score_global.py -- Phase 1 scoring + Phase 2 GP/EI setup for the joint
(k_f, k_d, k_ORR) BO calibration on disc_10x2_coarse_hmin0.5.mesh.

For each completed global-DoE run:
  1. loads its raw coarse-mesh mass-loss curve (results/result_global_run*.txt)
  2. applies the coarse->fine bias correction established in
     Correlation_Study/ (fine ~= 1.355846*coarse - 0.001584, Pearson
     r=0.998644 on disc_10x2_coarse_hmin0.5 vs disc_10x2_hmin0.25)
  3. interpolates the corrected curve onto the target's 7 timepoints
     (0-336h, target_jmst2018.csv, DOI 10.1016/j.jmst.2018.05.005)
  4. scores RMSE (%) against the real immersion-test data
Then fits a 3D GP (log10 k_f, log10 k_d, log10 k_orr) -> RMSE over all 12
points and reports the top candidates + proposes the next EI-guided
batch (Phase 2) within the SAME wide global bounds.
"""
import os
import numpy as np
import pandas as pd
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel

DIR = os.path.dirname(os.path.abspath(__file__))

# Coarse(disc_10x2_coarse_hmin0.5) -> fine(disc_10x2_hmin0.25) bias correction
# (Correlation_Study/correlation_results.txt)
CORR_SLOPE = 1.355846
CORR_INTERCEPT = -0.001584

BOUNDS = {
    "k_f":   (1.0, 100.0),
    "k_d":   (5.0, 100.0),
    "k_orr": (0.05, 5.0),
}

target = pd.read_csv(os.path.join(DIR, "target_jmst2018.csv"), comment="#")
t_target = target["t_hours"].values.astype(float)
ml_target = target["mass_loss_pct"].values.astype(float)

design = pd.read_csv(os.path.join(DIR, "doe_design_global.csv"))

rows = []
for _, d in design.iterrows():
    run_id = int(d["run_id"])
    fpath = os.path.join(DIR, "results", f"result_global_run{run_id}.txt")
    if not os.path.exists(fpath):
        print(f"WARNING: missing {fpath}, skipping run_id={run_id}")
        continue
    df = pd.read_csv(fpath, sep=r"\s+")
    t_model = df["TimeHours"].values.astype(float)
    ml_model_raw = df["MassLossPercent"].values.astype(float)

    if t_model.max() < t_target.max() - 1e-6:
        print(f"WARNING: run_id={run_id} incomplete (max t={t_model.max()}), skipping")
        continue

    ml_model_corrected = CORR_SLOPE * ml_model_raw + CORR_INTERCEPT
    ml_interp = np.interp(t_target, t_model, ml_model_corrected)
    rmse = float(np.sqrt(np.mean((ml_interp - ml_target) ** 2)))

    rows.append(dict(run_id=run_id, k_f=d["k_f"], k_d=d["k_d"], k_orr=d["k_orr"],
                      rmse=rmse, final_raw=ml_model_raw[-1],
                      final_corrected=ml_model_corrected[-1]))

res = pd.DataFrame(rows).sort_values("rmse")
out_txt = os.path.join(DIR, "global_doe_scores.txt")
res.to_csv(out_txt, sep="\t", index=False, float_format="%.6f")
print(f"Saved: {out_txt}\n")
print(res.to_string(index=False))

best = res.iloc[0]
print(f"\nBest so far: run_id={int(best.run_id)}  "
      f"k_f={best.k_f:.4f} k_d={best.k_d:.4f} k_orr={best.k_orr:.4f}  "
      f"RMSE={best.rmse:.5f}%")

# -- GP fit + EI-based proposals for Phase 2 (still within global bounds) ---
# Fit in NORMALIZED log10-space (each dim rescaled to roughly [-1,1] over
# its own search-box bounds), not raw log10(param). With only 12 points
# and raw log10 values, the k_d dimension's optimal length-scale ran off
# to the sklearn default upper bound (1e5, a ConvergenceWarning) -- the
# GP was reading essentially "no information" for that axis, which is a
# numerical artifact of an unbounded, un-normalized search, not a
# physically meaningful "k_d doesn't matter" conclusion (the kinetic
# sensitivity sweep showed k_d clearly does). Normalizing puts all three
# axes on the same O(1) scale and lets an explicit, sane length_scale_bounds
# actually constrain the fit instead of drifting to a degenerate flat GP.
names = list(BOUNDS.keys())
lo = np.log10([BOUNDS[n][0] for n in names])
hi = np.log10([BOUNDS[n][1] for n in names])
mid = (lo + hi) / 2.0
half_range = (hi - lo) / 2.0


def normalize(log_params):
    return (log_params - mid) / half_range


X_log = np.column_stack([np.log10(res[n].values) for n in names])
X_norm = normalize(X_log)
y = res["rmse"].values

kernel = (Matern(length_scale=[1.0, 1.0, 1.0], length_scale_bounds=(0.05, 5.0), nu=2.5)
          + WhiteKernel(noise_level=1e-3, noise_level_bounds=(1e-5, 1e-1)))
gp = GaussianProcessRegressor(kernel=kernel, normalize_y=True,
                               n_restarts_optimizer=20, random_state=0)
gp.fit(X_norm, y)
print(f"\nFitted kernel: {gp.kernel_}")
print(f"  (length scales are in NORMALIZED units -- 1.0 means the "
      f"correlation length spans the full half-width of the search box "
      f"for that parameter; a small value = the RMSE surface varies "
      f"sharply across that axis, a large value near the 5.0 bound = "
      f"nearly flat/weak dependence over this box)")
for n, ls in zip(names, gp.kernel_.k1.length_scale):
    print(f"    {n}: length_scale={ls:.4f}")

rng = np.random.default_rng(123)
n_cand = 20000
cand_log = lo + rng.random((n_cand, 3)) * (hi - lo)
cand = normalize(cand_log)
mu, sigma = gp.predict(cand, return_std=True)

best_so_far = float(y.min())
xi = 0.01
sigma_safe = np.maximum(sigma, 1e-12)
imp = best_so_far - mu - xi
z = imp / sigma_safe
ei = imp * norm.cdf(z) + sigma_safe * norm.pdf(z)
ei = np.maximum(ei, 0.0)

# Greedy top-N with a minimum separation in NORMALIZED space (comparable
# across axes now), so the 8 proposed points aren't clustered on top of
# each other (pure top-N by EI tends to pick near-duplicates around the
# single best peak).
order = np.argsort(-ei)
chosen = []
min_sep = 0.15  # normalized units (full box half-width = 1.0 per axis)
for idx in order:
    pt = cand[idx]
    if all(np.linalg.norm(pt - cand[c]) > min_sep for c in chosen):
        chosen.append(idx)
    if len(chosen) >= 8:
        break

next_points = 10 ** cand_log[chosen]
next_df = pd.DataFrame(next_points, columns=names)
next_df.insert(0, "run_id", range(len(next_df)))
next_df["predicted_rmse_mu"] = mu[chosen]
next_df["predicted_rmse_sigma"] = sigma[chosen]
next_df["ei"] = ei[chosen]

# k_d's GP length-scale is pinned at the search-box bound (see printout
# above) -- with only 12 points the GP genuinely can't resolve any
# structure along that axis yet, so pure-EI k_d values are essentially
# incidental/uninformative. Override them with a log-spaced stratified
# sweep across the FULL k_d bounds instead, keeping the GP's own (real,
# resolved) k_f/k_orr picks untouched -- this round buys actual k_d
# information for the next GP fit instead of wasting sample budget on
# arbitrary k_d values EI wasn't actually discriminating on.
k_d_strat = np.logspace(np.log10(BOUNDS["k_d"][0]), np.log10(BOUNDS["k_d"][1]), len(next_df))
rng2 = np.random.default_rng(99)
rng2.shuffle(k_d_strat)  # avoid correlating k_d order with the EI-rank order of k_f/k_orr
next_df["k_d"] = k_d_strat

out_next = os.path.join(DIR, "doe_design_phase2.csv")
next_df[["run_id", "k_f", "k_d", "k_orr"]].to_csv(out_next, index=False, float_format="%.6f")
print(f"\nSaved Phase 2 (EI-guided k_f/k_orr, stratified k_d) proposals to {out_next}")
print(next_df.to_string(index=False))
