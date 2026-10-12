"""Combined objective for the v2 BO: mass loss + corrosion rate vs target_jmst2018.csv.
Simulated corrosion rate follows the project's own convention (verified against the
'Disc In Vitro' sheet and the target file): CR(t) = ML(t)/100*m0 / (t * rho * A) * 8760 mm/yr,
i.e. CUMULATIVE-AVERAGE penetration rate, m0=1.1217 g, rho=0.00714 g/mm3, A=238 mm2
(late-time disc surface area; 237-240 mm2 for t>=24 h). Check: target ML 0.32% @336 h -> 0.0553
(target 0.0552). Mass loss is first coarse->fine corrected (1.355846*x-0.001584); CR is computed
from the corrected mass loss.
J = sqrt( 0.5*(RMSE_ML/mean(ML_target))^2 + 0.5*(RMSE_CR/mean(CR_target))^2 )  over t=24..336 h."""
import numpy as np, pandas as pd, os
DIR = os.path.dirname(os.path.abspath(__file__))
S, I = 1.355846, -0.001584
M0, RHO, A = 1.1217, 0.00714, 238.0
tg = pd.read_csv(os.path.join(DIR, "target_jmst2018.csv"), comment="#")
tt = tg.t_hours.values[1:].astype(float); ml_t = tg.mass_loss_pct.values[1:]; cr_t = tg.corrosion_rate_mmpyr.values[1:]
def evaluate(path):
    m = np.loadtxt(path, skiprows=1)
    ml = np.interp(tt, m[:, 0], S * m[:, 1] + I)
    cr = np.clip(ml, 0, None) / 100 * M0 / (tt * RHO * A) * 8760
    r_ml = np.sqrt(np.mean((ml - ml_t) ** 2)); r_cr = np.sqrt(np.mean((cr - cr_t) ** 2))
    J = np.sqrt(0.5 * (r_ml / ml_t.mean()) ** 2 + 0.5 * (r_cr / cr_t.mean()) ** 2)
    return r_ml, r_cr, J, ml, cr
if __name__ == "__main__":
    rows = []
    for stage, csv, pref in (("phase1", "doe_design_global.csv", "result_global_run"), ("phase2", "doe_design_phase2.csv", "result_phase2_run")):
        for _, r in pd.read_csv(os.path.join(DIR, csv)).iterrows():
            a, b, J, ml, cr = evaluate(os.path.join(DIR, "results", f"{pref}{int(r.run_id)}.txt"))
            rows.append((stage, int(r.run_id), r.k_f, r.k_d, r.k_orr, a, b, J))
    d = pd.DataFrame(rows, columns=["stage", "run", "k_f", "k_d", "k_orr", "RMSE_ML", "RMSE_CR", "J"]).sort_values("J")
    d.to_csv(os.path.join(DIR, "combined_objective_scores.csv"), index=False)
    print(d.round(4).to_string(index=False))
    print("target mean ML %.3f, CR %.4f" % (ml_t.mean(), cr_t.mean()))
