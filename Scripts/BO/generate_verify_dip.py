"""
generate_verify_dip.py -- 4-point verification batch for the GP's
speculative interior dip (k_f~48.4, k_d~29.5, k_orr~0.596, predicted
RMSE~0.037%) found by score_combined.py on the 20-point combined dataset.
This sits between conflicting evidence (good at k_f~12, worse at
k_f~55-66), so before committing sample budget to local refinement in
one region or the other, directly test whether a real dip exists there:
  - point 0: the GP's exact predicted minimum
  - points 1-3: small LHS around it (+/-40% in log-space per axis) to
    check the dip is a real local feature, not a single lucky/unlucky
    evaluation
"""
import numpy as np
from scipy.stats import qmc
import csv
import os

DIR = os.path.dirname(os.path.abspath(__file__))

CENTER = {"k_f": 48.4118, "k_d": 29.5251, "k_orr": 0.5962}
SPREAD_FACTOR = 1.4  # log-space +/- range around center

names = list(CENTER.keys())
center_log = np.log10([CENTER[n] for n in names])
half_range = np.log10(SPREAD_FACTOR)

points = [10 ** center_log]  # point 0: exact GP-predicted minimum

sampler = qmc.LatinHypercube(d=3, seed=55)
unit = sampler.random(n=3)
log_samples = (center_log - half_range) + unit * (2 * half_range)
points.extend(10 ** log_samples)

csv_path = os.path.join(DIR, "doe_design_verify_dip.csv")
with open(csv_path, "w", newline="") as f:
    w = csv.writer(f)
    w.writerow(["run_id", "k_f", "k_d", "k_orr"])
    for i, row in enumerate(points):
        w.writerow([i, f"{row[0]:.6f}", f"{row[1]:.6f}", f"{row[2]:.6f}"])

print(f"Saved 4-point dip-verification design to {csv_path}")
print(f"{'run_id':>6} {'k_f':>10} {'k_d':>10} {'k_orr':>10}")
for i, row in enumerate(points):
    print(f"{i:>6} {row[0]:>10.4f} {row[1]:>10.4f} {row[2]:>10.4f}")
