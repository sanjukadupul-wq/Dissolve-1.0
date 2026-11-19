"""Regression checks for Dissolve v1.1.0 (flux-first interface coupling).  usage: check.py <tests_out dir> <solver dir>
Reads the outputs written by tests/run_tests.sbatch.  Every check fails closed (missing output = FAIL).  Tolerances are stated in each message.
 T1  static: version banner, Table 1 constants, flag guards present in the source
 T2  closed box (30 mm box, 3.5 mg/L): Zn released per unit O2 consumed = 1 (2 Zn : 1 O2); mass loss and O2 sink respect the oxygen inventory
 T3  cut-cell volume loss against the flux-integrated mass loss (same run)
 T4  level-set reinitialisation conserves volume (per call and cumulative), and does not change the mass loss
 T5  flux-first projection residuals (every step)
 T6  guards: inconsistent flags and projection imbalance exit with the documented error codes
 T7  open-top film run: Zn inventory closure (dissolved + retained + removed against the oxidised flux)
 T8  film-barrier option (-film_mech 1): conservation, projection residuals, and the barrier lowers the mass loss
 T9  code defaults: -flux_first 1 -v_picard 0 -conservative 2 -oh_fix 1 are the defaults and a run without coupling flags reproduces the explicit-flag run"""
import re, sys, os
import numpy as np
out, sol = sys.argv[1], sys.argv[2]
M_ZN, M_O2 = 65.38, 31.998
ok = True


def report(name, passed, msg):
    global ok
    ok &= bool(passed)
    print(("PASS " if passed else "FAIL ") + name + " : " + msg)


def read(p):
    try:
        return open(p, errors="ignore").read()
    except OSError:
        return ""


def table(p):
    rows = [l.rstrip("\n").split("\t") for l in read(p).splitlines() if l.strip()]
    if len(rows) < 2:
        return {}
    a = np.array([[float(x) for x in r] for r in rows[1:] if len(r) == len(rows[0])])
    return {h: a[:, i] for i, h in enumerate(rows[0])}


# ---- T1 static
edp = read(os.path.join(sol, "dissolve.edp")); st = read(os.path.join(sol, "config/settings.idp"))
report("T1a version banner", 'DISSOLVE_VERSION v1.1.0' in edp, "dissolve.edp prints DISSOLVE_VERSION v1.1.0")
report("T1b Table 1 film values", 'getARGV("-film_tortuosity", 2.00)' in st and 'getARGV("-film_porosity", 0.25)' in st, "tortuosity 2, porosity 0.25")
report("T1c Table 1 diffusivities", all(x in st for x in ('getARGV("-diff_o2", 9.36)', 'getARGV("-diff_zn", 2.7216)', 'getARGV("-diff_cl", 7.776)', 'getARGV("-diff_oh", 20.16)')), "O2 9.36, Zn 2.7216, Cl 7.776, OH 20.16 mm2/h")
report("T1d flag guards in source", "ERROR_FLUXFIRST_REQUIRES_V_PICARD_0" in edp and "ERROR_FLUXFIRST_REQUIRES_O2_AND_CONSERVATIVE_MODE_2" in edp, "both flux-first flag guards present")
dflt = {"-flux_first": "1", "-v_picard": "0", "-conservative": "2", "-oh_fix": "1"}
got = {k: (re.search(r'getARGV\("%s", *([0-9.]+)\)' % k, st).group(1) if re.search(r'getARGV\("%s", *([0-9.]+)\)' % k, st) else None) for k in dflt}
report("T1f code defaults select the flux-first formulation", got == dflt, "defaults in settings.idp: " + ", ".join("%s %s" % (k, got[k]) for k in dflt))
report("T1e Zn:O2 constants", abs(2 * M_ZN / M_O2 - 4.0863) < 1e-3 and "getARGV(\"-zn_molar_conc\", 1.09e-4)" in st, "2 M_Zn / M_O2 = %.4f" % (2 * M_ZN / M_O2))

# ---- T2 closed box
cd = os.path.join(out, "closed"); log = read(os.path.join(cd, "run.log")); mb = table(os.path.join(cd, "mass_loss.txt"))
report("T2a run completed", read(os.path.join(cd, "exit_code")).strip() == "0" and "DISSOLVE_VERSION v1.1.0" in log, "exit code 0 and v1.1.0 banner")
if mb:
    sel = mb["TimeHours"] >= 8; z = mb["ZnPerSupported"][sel]
    report("T2b Zn per supported O2 = 1 (|dev| < 2e-3, t >= 8 h)", len(z) > 0 and np.abs(z - 1).max() < 2e-3, "min %.5f max %.5f" % (z.min(), z.max()) if len(z) else "no rows")
    V0 = float(re.search(r"Initial size:\s*([0-9.]+)", log).group(1)); cap = 3.5e-9 * (27000.0 - V0) * (2 * M_ZN / M_O2) / (V0 * 7.14e-3) * 100; inv = 3.5e-9 * (27000.0 - V0)
    ml = mb["MassLossCut_pct"][-1]; sink = mb["O2SinkCum_g"][-1]
    report("T2c mass loss <= 1.02 x oxygen cap", ml <= 1.02 * cap, "%.4f %% vs cap %.4f %% (ratio %.3f)" % (ml, cap, ml / cap))
    report("T2d O2 sink <= 1.02 x initial inventory", sink <= 1.02 * inv, "%.3e g vs %.3e g (ratio %.3f)" % (sink, inv, sink / inv))
else:
    report("T2 outputs", False, "mass_loss.txt missing or empty")

# ---- T3 cut-cell against flux
if mb:
    cut, fl = mb["MassLossCut_pct"][-1], mb["MassLossFlux_pct"][-1]
    report("T3 cut-cell and flux-integrated mass loss agree within 5 % at the end", cut > 0 and abs(fl - cut) / cut < 0.05, "cut %.4f %%, flux %.4f %%, difference %.2f %%" % (cut, fl, 100 * (fl - cut) / cut if cut else float("nan")))

# ---- T4 reinitialisation
red = re.findall(r"DEBUG_REDIST t=([0-9.]+) V_before=([0-9.eE+-]+) V_after=([0-9.eE+-]+) dV=([0-9.eE+-]+) dV_pct=([0-9.eE+-]+)", log)
if red:
    dp = np.abs(np.array([float(x[4]) for x in red])); dv = np.abs(np.array([float(x[3]) for x in red])).sum()
    report("T4a reinitialisation ran", True, "%d calls" % len(red))
    report("T4b volume change per call < 1e-3 %", dp.max() < 1e-3, "max |dV| = %.2e %%" % dp.max())
    report("T4c volume correction converged every call", "WARNING_REDIST_CORRECTION_NOT_CONVERGED" not in log, "no non-convergence warning")
    report("T4d cumulative reinitialisation volume change < 1e-4 of the initial volume", mb and abs(mb["ReinitDVCum_mm3"][-1]) / V0 < 1e-4, "cumulative %.2e mm3 (%.2e of V0)" % (mb["ReinitDVCum_mm3"][-1], abs(mb["ReinitDVCum_mm3"][-1]) / V0) if mb else "no data")
else:
    report("T4a reinitialisation ran", False, "no DEBUG_REDIST lines")
mo = table(os.path.join(out, "closed_noreinit", "mass_loss.txt"))
if mb and mo:
    a, b = mb["MassLossCut_pct"][-1], mo["MassLossCut_pct"][-1]
    report("T4e mass loss with reinitialisation within 10 % of without", abs(a - b) / b < 0.10, "on %.4f %% vs off %.4f %%" % (a, b))
else:
    report("T4e reinit on/off comparison", False, "missing output")

# ---- T5 projection residuals
for d in ("closed", "open_film"):
    pr = re.findall(r"DEBUG_PROJ t=([0-9.eE+-]+) preResidual=([0-9.eE+-]+) fluxScale=([0-9.eE+-]+) postResidual=([0-9.eE+-]+)", read(os.path.join(out, d, "run.log")))
    if pr:
        pre = max(float(x[1]) for x in pr); post = max(float(x[3]) for x in pr)
        report("T5 %s: projection residuals (pre < 1e-4, post < 1e-8)" % d, pre < 1e-4 and post < 1e-8, "%d steps, max pre %.2e, max post %.2e" % (len(pr), pre, post))
    else:
        report("T5 %s" % d, False, "no DEBUG_PROJ lines")

# ---- T6 guards
for d, code, tag in (("guard_picard", "2", "ERROR_FLUXFIRST_REQUIRES_V_PICARD_0"), ("guard_cons", "2", "ERROR_FLUXFIRST_REQUIRES_O2_AND_CONSERVATIVE_MODE_2"), ("guard_proj", "3", "ERROR_FLUXFIRST_PROJECTION_BALANCE")):
    ec = read(os.path.join(out, d, "exit_code")).strip(); lg = read(os.path.join(out, d, "run.log"))
    report("T6 %s exits %s with %s" % (d, code, tag), ec == code and tag in lg, "exit code %s, message %s" % (ec or "missing", "found" if tag in lg else "absent"))

# ---- T7 open-top film closure
bal = table(os.path.join(out, "open_film", "global_balance.tsv")); mf = table(os.path.join(out, "open_film", "mass_loss.txt"))
if bal and mf:
    ox = bal["ZnOxidizedFluxCum_g"][-1]; res = bal["ZnClosureResidual_g"][-1]
    report("T7a Zn closure residual < 1 % of the zinc oxidised", ox > 0 and abs(res) / ox < 0.01, "residual %.3e g of %.3e g (%.3f %%)" % (res, ox, 100 * res / ox if ox else float("nan")))
    z = mf["ZnPerSupported"][mf["TimeHours"] >= 8]
    report("T7b open-top Zn per supported O2 = 1 (|dev| < 2e-3)", len(z) > 0 and np.abs(z - 1).max() < 2e-3, "min %.5f max %.5f" % (z.min(), z.max()) if len(z) else "no rows")
else:
    report("T7 open-top film run", False, "missing output")
# ---- T8 film-barrier option (-film_mech 1): same conservation, and the barrier lowers the mass loss
res8 = {}
for d in ("film_mech1_b0", "film_mech1_b12"):
    mf8 = table(os.path.join(out, d, "mass_loss.txt")); pr = re.findall(r"DEBUG_PROJ t=([0-9.eE+-]+) preResidual=([0-9.eE+-]+) fluxScale=([0-9.eE+-]+) postResidual=([0-9.eE+-]+)", read(os.path.join(out, d, "run.log")))
    if mf8 and pr and read(os.path.join(out, d, "exit_code")).strip() == "0":
        z = mf8["ZnPerSupported"][mf8["TimeHours"] >= 8]; res8[d] = mf8["MassLossCut_pct"][-1]
        report("T8 %s: Zn per supported O2 = 1 (|dev| < 2e-3) and projection residuals (pre < 1e-3, post < 1e-8)" % d,
               len(z) > 0 and np.abs(z - 1).max() < 2e-3 and max(float(x[1]) for x in pr) < 1e-3 and max(float(x[3]) for x in pr) < 1e-8,
               "Zn/O2 min %.5f max %.5f, max pre %.2e, max post %.2e, mass loss %.4f %%" % (z.min(), z.max(), max(float(x[1]) for x in pr), max(float(x[3]) for x in pr), res8[d]))
    else:
        report("T8 %s" % d, False, "missing output or non-zero exit code")
if len(res8) == 2:
    report("T8 barrier lowers mass loss (beta 12 below 0.9 x beta 0)", res8["film_mech1_b12"] < 0.9 * res8["film_mech1_b0"], "%.4f %% vs %.4f %%" % (res8["film_mech1_b12"], res8["film_mech1_b0"]))
# ---- T9 defaults-only run
dd = os.path.join(out, "defaults_closed"); dlog = read(os.path.join(dd, "run.log")); dmb = table(os.path.join(dd, "mass_loss.txt"))
dpr = re.findall(r"DEBUG_PROJ t=([0-9.eE+-]+) preResidual=([0-9.eE+-]+) fluxScale=([0-9.eE+-]+) postResidual=([0-9.eE+-]+)", dlog)
report("T9a defaults-only run uses the flux-first path", read(os.path.join(dd, "exit_code")).strip() == "0" and len(dpr) > 0, "exit code 0, %d DEBUG_PROJ lines (flux-first projection active)" % len(dpr))
if dmb and mb:
    rel = abs(dmb["MassLossCut_pct"][-1] - mb["MassLossCut_pct"][-1]) / max(mb["MassLossCut_pct"][-1], 1e-30)
    report("T9b defaults-only run equals the explicit-flag run (relative difference < 1e-9)", rel < 1e-9, "mass loss %.6f %% vs %.6f %% (relative difference %.1e)" % (dmb["MassLossCut_pct"][-1], mb["MassLossCut_pct"][-1], rel))
else:
    report("T9b defaults-only comparison", False, "missing output")
print("ALL PASS" if ok else "SOME FAILED")
sys.exit(0 if ok else 1)
