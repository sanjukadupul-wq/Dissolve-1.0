"""Phase 3 (re-run) on MASS LOSS ONLY. GP on normalised log10 params -> log10(mass-loss RMSE) over the 20 Phase 1+2
evaluations (combined_objective_scores.csv, 20 rows); expected improvement, 8 points, min separation 0.15; axes whose GP length
scale sits at the upper bound (k_f, k_d) are stratified by Latin hypercube within a factor 3 of the best-RMSE point.
usage: python propose_phase3_massloss.py <EI_seed> <LHS_seed>   (run inside a repeat's folder)"""
import os, sys, numpy as np, pandas as pd
from scipy.stats import norm, qmc
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel
DIR = os.getcwd(); EI_SEED, LHS_SEED = int(sys.argv[1]), int(sys.argv[2])
B = {"k_f": (1.0, 100.0), "k_d": (0.1, 100.0), "k_orr": (0.05, 5.0)}
names = list(B); lo = np.log10([B[n][0] for n in names]); hi = np.log10([B[n][1] for n in names])
mid, hr = (lo + hi) / 2, (hi - lo) / 2; nz = lambda L: (L - mid) / hr
d = pd.read_csv(os.path.join(DIR, "combined_objective_scores.csv")); assert len(d) == 20, len(d)
d = d.sort_values("RMSE_ML")
X = nz(np.column_stack([np.log10(d[n].values) for n in names])); y = np.log10(d["RMSE_ML"].values)
gp = GaussianProcessRegressor(Matern([1, 1, 1], (0.05, 5.0), nu=2.5) + WhiteKernel(1e-3, (1e-5, 1e-1)), normalize_y=True,
                              n_restarts_optimizer=20, random_state=0).fit(X, y)
ls = gp.kernel_.k1.length_scale; print("kernel:", gp.kernel_)
rng = np.random.default_rng(EI_SEED); cl = lo + rng.random((30000, 3)) * (hi - lo); c = nz(cl)
mu, sd = gp.predict(c, return_std=True); sd = np.maximum(sd, 1e-12)
imp = y.min() - mu - 0.01; z = imp / sd; ei = np.maximum(imp * norm.cdf(z) + sd * norm.pdf(z), 0)
ch = []
for i in np.argsort(-ei):
    if all(np.linalg.norm(c[i] - c[j]) > 0.15 for j in ch): ch.append(i)
    if len(ch) >= 8: break
out = pd.DataFrame(10 ** cl[ch], columns=names); out.insert(0, "run_id", range(8))
pinned = [n for n, l in zip(names, ls) if l > 4.9]; print("pinned axes:", pinned)
best = d.iloc[0]; print("best so far:", best[["k_f", "k_d", "k_orr", "RMSE_ML"]].to_dict())
if pinned:
    u = qmc.LatinHypercube(d=3, seed=LHS_SEED).random(8)
    for k, n in enumerate(names):
        if n in pinned:
            b = best[n]; out[n] = (10 ** (np.log10(b / 3) + u[:, k] * (np.log10(b * 3) - np.log10(b / 3)))).clip(*B[n])
out["pred_RMSE"] = 10 ** mu[ch]
out[["run_id", "k_f", "k_d", "k_orr"]].to_csv("doe_design_phase3b.csv", index=False, float_format="%.6f")
print(out.round(4).to_string(index=False))
