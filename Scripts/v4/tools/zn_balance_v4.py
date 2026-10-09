"""Global Zn / O2 / charge balance from stored VTK fields + the code's own cumulative 'O2 consumed (g)' log line.
usage: zn_balance_v4.py <outdir> <logfile> <hours,...> <vtk cadence h>"""
import pyvista as pv, numpy as np, sys, re
d, log = sys.argv[1], sys.argv[2]; hours=[float(h) for h in sys.argv[3].split(",")]; every=float(sys.argv[4])
M0=1.1217; MZN=65.38; MO2=31.998
def integ(m, arr):
    m=m.copy(); m.point_data["x"]=arr; return m.integrate_data().point_data["x"][0]
def load(h): return pv.read(f"{d}/vtk/output_4_{int(round(h/every)):04d}.pvtu")
def inv(m):
    liq=np.ones(m.n_points)  # v4: Zn, F, O2 are zero inside the solid, so integrate unmasked (exact FE integral)
    return [integ(m,np.asarray(m.point_data[k])*liq) for k in ("Zn","F","O2")]
cons={}
for L in open(log):
    m=re.match(r"Time: (\d+)h .*O2 consumed \(g\): ([0-9.eE+-]+)",L)
    if m: cons[float(m.group(1))]=float(m.group(2))
res=np.loadtxt(f"{d}/result_disc.txt",skiprows=1)
z0,f0,o0=inv(load(0))
print("t_h,ML_raw_pct,Zn_removed_g,Zn_dissolved_g,Zn_in_film_g,Zn_residual_g,Zn_residual_pct_of_removed,O2_consumed_g,O2_needed_for_Zn_removed_g,O2_resid_pct,O2_supplied_via_boundary_g,charge_Zn_mol_e,charge_O2_mol_e,charge_resid_pct")
for h in hours:
    z,f,o=inv(load(h)); ml=np.interp(h,res[:,0],res[:,1]); A=M0*ml/100
    dz=z-z0; fz=f-f0; resid=dz+fz-A; oc=cons.get(h,np.nan); on=A/MZN/2*MO2
    sup=(o-o0)+oc; qz=2*A/MZN; qo=4*oc/MO2
    print("%.0f,%.4f,%.4e,%.4e,%.4e,%.3e,%.2f,%.4e,%.4e,%.2f,%.4e,%.4e,%.4e,%.2f"%(h,ml,A,dz,fz,resid,100*resid/A,oc,on,100*(oc-on)/on,sup,qz,qo,100*(qo-qz)/qz))
