"""
Multi-ring connected stent, matching Yang et al. (Biomaterials 2017) actual
geometry: Dout=3.0mm, strut 165um. Same SDF+marching-cubes technique proven
for BCC/FCC (robust, no manual watertightness fights) -- reuses the .edp's
own rounded-box cross-section distance formula (dTube/dBand/fillet), just
evaluated as a numpy field instead of run through FreeFEM.
"""
import numpy as np
from skimage import measure
import trimesh

Dout = 3.0
Rout = Dout / 2.0
strut = 0.165          # strut thickness = width (square-ish cross-section)
Rin = Rout - strut
centerr = (Rout + Rin) / 2.0
fillet = 0.05
halfT = strut / 2.0 - fillet
halfW = strut / 2.0 - fillet

A = 0.5                 # serpentine amplitude per ring (mm)
N = 6                    # crowns per ring
N_RINGS = 6
DZ = 1.5                 # axial spacing between rings (mm)
z_centers = [(-((N_RINGS - 1) * DZ) / 2.0) + i * DZ for i in range(N_RINGS)]

SPACING = 0.03
margin = 0.4
x_lo, x_hi = -Rout - margin, Rout + margin
z_lo = min(z_centers) - A - strut - margin
z_hi = max(z_centers) + A + strut + margin
nx = int(round((x_hi - x_lo) / SPACING)) + 1
nz = int(round((z_hi - z_lo) / SPACING)) + 1
xs = np.linspace(x_lo, x_hi, nx)
ys = np.linspace(x_lo, x_hi, nx)
zs = np.linspace(z_lo, z_hi, nz)
X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
print(f"grid: {X.shape}, {X.size/1e6:.1f}M points", flush=True)

r = np.sqrt(X**2 + Y**2)
theta = np.arctan2(Y, X)
dTube = np.abs(r - centerr) - halfT

phase = [0.0 if i % 2 == 0 else np.pi for i in range(N_RINGS)]  # alternate rings
field = np.full(X.shape, np.inf, dtype=np.float32)
for zc0, ph in zip(z_centers, phase):
    cz = A * np.sin(N * theta + ph) + zc0
    dBand = np.abs(Z - cz) - halfW
    ring = np.maximum(dTube, dBand) - fillet
    np.minimum(field, ring, out=field)
print("rings done", flush=True)

# connectors: short straight struts between adjacent-ring peak/valley
# positions -- with alternating phase, ring i's peak (sin=+1) lands exactly
# where ring i+1 has a valley (sin=-1) at the SAME theta, so a purely axial
# connector actually reaches both surfaces (typical flexible-stent linkage)
def peak_thetas(k_list, ph):
    return [((np.pi / 2 - ph) + 2 * np.pi * k) / N for k in k_list]

connectors = []
for i in range(N_RINGS - 1):
    z1, z2 = z_centers[i], z_centers[i + 1]
    ph1 = phase[i]
    ks = [0, N // 2] if i % 2 == 0 else [1, N // 2 + 1]
    for th in peak_thetas(ks, ph1):
        # ring i peak at this theta:
        cz1 = A * np.sin(N * th + ph1) + z1
        cz2 = A * np.sin(N * th + phase[i + 1]) + z2  # should be the valley (-A) of ring i+1
        p1 = np.array([centerr * np.cos(th), centerr * np.sin(th), cz1])
        p2 = np.array([centerr * np.cos(th), centerr * np.sin(th), cz2])
        connectors.append((p1, p2))
print(f"{len(connectors)} connector struts", flush=True)
for p1, p2 in connectors:
    print(f"  connector z: {p1[2]:.3f} -> {p2[2]:.3f}", flush=True)

conn_r = strut / 2.0
for p1, p2 in connectors:
    d = p2 - p1
    seglen2 = float(d @ d)
    px, py, pz = X - p1[0], Y - p1[1], Z - p1[2]
    t = (px * d[0] + py * d[1] + pz * d[2]) / seglen2
    np.clip(t, 0.0, 1.0, out=t)
    cx = p1[0] + t * d[0]; cy = p1[1] + t * d[1]; cz2 = p1[2] + t * d[2]
    dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2 + (Z - cz2) ** 2) - conn_r
    np.minimum(field, dist, out=field)
print("connectors done, extracting surface...", flush=True)

verts, faces, _, _ = measure.marching_cubes(field, level=0.0, spacing=(SPACING,) * 3)
verts = verts + np.array([x_lo, x_lo, z_lo])
mesh = trimesh.Trimesh(vertices=verts, faces=faces)
mesh.remove_unreferenced_vertices()
mesh.fix_normals()
comps = mesh.split(only_watertight=False)
if len(comps) > 1:
    print(f"  ({len(comps)-1} spurious fragment(s) dropped)", flush=True)
    mesh = max(comps, key=lambda c: len(c.faces))

if mesh.volume < 0:
    mesh.invert()

print(f"watertight={mesh.is_watertight}, volume={mesh.volume:.4f} mm^3, "
      f"n_verts={len(mesh.vertices)}, n_faces={len(mesh.faces)}", flush=True)
print(f"bounds: {mesh.bounds.tolist()}", flush=True)

out = r"C:\Users\hari0008\Downloads\stent_multiring.stl"
mesh.export(out)
print(f"Saved: {out}", flush=True)
