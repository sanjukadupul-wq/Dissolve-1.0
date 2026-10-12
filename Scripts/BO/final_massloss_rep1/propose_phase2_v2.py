"""Phase 2 (EI-guided) for the v2-code joint BO. Reads phase1_scores.csv, fits a 3D GP on
normalised log10 params -> log10(RMSE), proposes 8 points by Expected Improvement with a
minimum separation. Unlike the original Phase 2 there is NO k_d stratification: k_d is
already informative in this dataset (tenfold spread in mass loss)."""
import os, numpy as np, pandas as pd
from scipy.stats import norm
from sklearn.gaussian_process import GaussianProcessRegressor
from sklearn.gaussian_process.kernels import Matern, WhiteKernel
DIR = os.path.dirname(os.path.abspath(__file__))
B = {"k_f": (1.0, 100.0), "k_d": (1.0, 100.0), "k_orr": (0.05, 5.0)}
names = list(B); lo = np.log10([B[n][0] for n in names]); hi = np.log10([B[n][1] for n in names])
mid, hr = (lo + hi) / 2, (hi - lo) / 2
nz = lambda L: (L - mid) / hr
res = pd.read_csv(os.path.join(DIR, "phase1_scores.csv")).sort_values("RMSE")
X = nz(np.column_stack([np.log10(res[n].values) for n in names])); y = np.log10(res["RMSE"].values)
gp = GaussianProcessRegressor(Matern(length_scale=[1, 1, 1], length_scale_bounds=(0.05, 5.0), nu=2.5)
                              + WhiteKernel(1e-3, (1e-5, 1e-1)), normalize_y=True,
                              n_restarts_optimizer=20, random_state=0).fit(X, y)
print("kernel:", gp.kernel_)
rng = np.random.default_rng(123); cl = lo + rng.random((30000, 3)) * (hi - lo); c = nz(cl)
mu, sd = gp.predict(c, return_std=True); sd = np.maximum(sd, 1e-12)
imp = y.min() - mu - 0.01; z = imp / sd; ei = np.maximum(imp * norm.cdf(z) + sd * norm.pdf(z), 0)
chosen = []
for i in np.argsort(-ei):
    if all(np.linalg.norm(c[i] - c[j]) > 0.15 for j in chosen): chosen.append(i)
    if len(chosen) >= 8: break
out = pd.DataFrame(10 ** cl[chosen], columns=names); out.insert(0, "run_id", range(8))
out["pred_RMSE"] = 10 ** mu[chosen]; out["ei"] = ei[chosen]
# The GP's k_f and k_d length scales sit at the search-box bound (5.0): the 12 points
# resolve only k_orr (ridge near 0.14-0.17). Pure EI therefore piles all 8 points on that
# ridge with arbitrary k_f/k_d at the box edge. As in the original Phase 2, keep the
# resolved axis (k_orr, narrowed to the EI ridge) and STRATIFY the unresolved ones.
from scipy.stats import qmc
u = qmc.LatinHypercube(d=3, seed=11).random(8)
kor = 10 ** (np.log10(0.12) + u[:, 2] * (np.log10(0.20) - np.log10(0.12)))
kf = 10 ** (lo[0] + u[:, 0] * (hi[0] - lo[0])); kd = 10 ** (lo[1] + u[:, 1] * (hi[1] - lo[1]))
out["k_f"], out["k_d"], out["k_orr"] = kf, kd, kor
out[["run_id", "k_f", "k_d", "k_orr"]].to_csv(os.path.join(DIR, "doe_design_phase2.csv"), index=False, float_format="%.6f")
print(out.round(4).to_string(index=False))
