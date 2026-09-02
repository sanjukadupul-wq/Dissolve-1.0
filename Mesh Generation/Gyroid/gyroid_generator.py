"""
TPMS unit-cell generator: 3x3x3 array of 2mm unit cells, porosity-calibrated,
watertight STL output (solid end-caps via padded-solid boundary trick).
"""
import numpy as np
from skimage import measure
import trimesh

CELL_MM = 2.0
N_CELLS = 3
DOMAIN_MM = CELL_MM * N_CELLS  # 6mm
SPACING = 0.08  # mm per grid step

FIELDS = {
    "gyroid": lambda X, Y, Z: np.sin(X) * np.cos(Y) + np.sin(Y) * np.cos(Z) + np.sin(Z) * np.cos(X),
    "diamond": lambda X, Y, Z: (np.sin(X) * np.sin(Y) * np.sin(Z) + np.sin(X) * np.cos(Y) * np.cos(Z)
                                 + np.cos(X) * np.sin(Y) * np.cos(Z) + np.cos(X) * np.cos(Y) * np.sin(Z)),
    "schwarzp": lambda X, Y, Z: np.cos(X) + np.cos(Y) + np.cos(Z),
}


def build_grid(pad_cells=2):
    n_real = int(round(DOMAIN_MM / SPACING)) + 1
    pad_n = int(round(pad_cells))
    n_total = n_real + 2 * pad_n
    coords_mm = (np.arange(n_total) - pad_n) * SPACING  # mm, real domain = [0, DOMAIN_MM]
    x, y, z = np.meshgrid(coords_mm, coords_mm, coords_mm, indexing="ij")
    # map mm -> radians, period = one unit cell (CELL_MM)
    X = 2 * np.pi * x / CELL_MM
    Y = 2 * np.pi * y / CELL_MM
    Z = 2 * np.pi * z / CELL_MM
    return coords_mm, x, y, z, X, Y, Z, pad_n, n_real


def calibrate_thresholds(field_fn, X, Y, Z, x, pad_n, n_real, porosities):
    # real-domain-only field values for calibration (exclude the artificial pad layer)
    F = field_fn(X, Y, Z)
    real_slice = F[pad_n:pad_n + n_real, pad_n:pad_n + n_real, pad_n:pad_n + n_real]
    thresholds = {}
    for p in porosities:
        # skimage marching_cubes encloses {F < level} as "inside" (verified empirically:
        # using quantile(p) directly gave solid_fraction == p, i.e. inverted vs. intent).
        # Want solid_fraction = 1 - porosity, i.e. P(F < c) = 1 - p  =>  c = quantile(1 - p)
        c = np.quantile(real_slice, 1.0 - p)
        thresholds[p] = c
    return F, thresholds


def make_solid_stl(F, coords_mm, pad_n, n_real, threshold, out_path, solid_pad_value=None):
    Fc = F.copy()
    if solid_pad_value is None:
        solid_pad_value = F.max() + 10.0
    # force the padding border to be unambiguously "solid" -> caps the surface at the true boundary
    Fc[:pad_n, :, :] = solid_pad_value
    Fc[-pad_n:, :, :] = solid_pad_value
    Fc[:, :pad_n, :] = solid_pad_value
    Fc[:, -pad_n:, :] = solid_pad_value
    Fc[:, :, :pad_n] = solid_pad_value
    Fc[:, :, -pad_n:] = solid_pad_value

    verts, faces, normals, _ = measure.marching_cubes(Fc, level=threshold, spacing=(SPACING,) * 3)
    verts = verts + (coords_mm[0])  # shift to true mm coordinates
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals()

    # drop spurious tiny disconnected fragments (marching-cubes artifacts at the
    # sharp padding-boundary transition) -- keep only the main solid
    comps = mesh.split(only_watertight=False)
    if len(comps) > 1:
        mesh = max(comps, key=lambda c: len(c.faces))
        print(f"    (dropped {len(comps)-1} spurious fragment(s), kept main component)")

    print(f"  {out_path}: verts={len(mesh.vertices)}, faces={len(mesh.faces)}, "
          f"watertight={mesh.is_watertight}, volume={mesh.volume:.4f} mm^3 "
          f"(domain={DOMAIN_MM**3:.1f} mm^3, solid_frac={mesh.volume/DOMAIN_MM**3:.3f})")
    mesh.export(out_path)
    return mesh


def generate_type(name, porosities=(0.3, 0.5, 0.7), out_dir="."):
    print(f"=== {name} ===")
    coords_mm, x, y, z, X, Y, Z, pad_n, n_real = build_grid(pad_cells=2)
    F, thresholds = calibrate_thresholds(FIELDS[name], X, Y, Z, x, pad_n, n_real, porosities)
    results = {}
    for p in porosities:
        out_path = f"{out_dir}/{name}_p{int(p*100)}.stl"
        m = make_solid_stl(F, coords_mm, pad_n, n_real, thresholds[p], out_path)
        results[p] = (out_path, m)
    return results


if __name__ == "__main__":
    import sys
    name = sys.argv[1] if len(sys.argv) > 1 else "gyroid"
    out_dir = sys.argv[2] if len(sys.argv) > 2 else r"C:\Users\hari0008\Downloads"
    generate_type(name, out_dir=out_dir)
