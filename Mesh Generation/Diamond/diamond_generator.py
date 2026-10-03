"""
Strut-lattice generator via signed-distance-field union (same technique as
tpms_generator.py: implicit field -> marching cubes -> watertight STL).
No CSG/OCC booleans -- just numpy, which is what made the TPMS shapes fast.
"""
import numpy as np
from skimage import measure
import trimesh

CELL_MM = 2.0
N_CELLS = 3
DOMAIN_MM = CELL_MM * N_CELLS  # 6mm
SPACING = 0.08  # mm per grid step


# ---------------------------------------------------------------- topology --
def bcc_topology(n=N_CELLS):
    nodes, struts = {}, []
    def key(p): return tuple(round(c, 6) for c in p)
    for i in range(n):
        for j in range(n):
            for k in range(n):
                center = (i + 0.5, j + 0.5, k + 0.5)
                nodes[key(center)] = center
                for dx in (0, 1):
                    for dy in (0, 1):
                        for dz in (0, 1):
                            c = (i + dx, j + dy, k + dz)
                            nodes[key(c)] = c
                            struts.append((center, c))
    return nodes, struts


def fcc_topology(n=N_CELLS):
    nodes, struts = {}, []
    done_faces = set()
    def key(p): return tuple(round(c, 6) for c in p)
    for i in range(n):
        for j in range(n):
            for k in range(n):
                faces = [
                    ((i, j + 0.5, k + 0.5), [(i, j, k), (i, j + 1, k), (i, j, k + 1), (i, j + 1, k + 1)]),
                    ((i + 1, j + 0.5, k + 0.5), [(i + 1, j, k), (i + 1, j + 1, k), (i + 1, j, k + 1), (i + 1, j + 1, k + 1)]),
                    ((i + 0.5, j, k + 0.5), [(i, j, k), (i + 1, j, k), (i, j, k + 1), (i + 1, j, k + 1)]),
                    ((i + 0.5, j + 1, k + 0.5), [(i, j + 1, k), (i + 1, j + 1, k), (i, j + 1, k + 1), (i + 1, j + 1, k + 1)]),
                    ((i + 0.5, j + 0.5, k), [(i, j, k), (i + 1, j, k), (i, j + 1, k), (i + 1, j + 1, k)]),
                    ((i + 0.5, j + 0.5, k + 1), [(i, j, k + 1), (i + 1, j, k + 1), (i, j + 1, k + 1), (i + 1, j + 1, k + 1)]),
                ]
                for fc, fcorners in faces:
                    fk = key(fc)
                    if fk in done_faces:
                        continue
                    done_faces.add(fk)
                    nodes[fk] = fc
                    for c in fcorners:
                        nodes[key(c)] = c
                        struts.append((fc, c))
    return nodes, struts


def diamond_topology(n=N_CELLS):
    nodes, struts = {}, []
    even_tet = [(0, 0, 0), (1, 1, 0), (1, 0, 1), (0, 1, 1)]
    odd_tet = [(1, 0, 0), (0, 1, 0), (0, 0, 1), (1, 1, 1)]
    def key(p): return tuple(round(c, 6) for c in p)
    for i in range(n):
        for j in range(n):
            for k in range(n):
                center = (i + 0.5, j + 0.5, k + 0.5)
                nodes[key(center)] = center
                tet = even_tet if (i + j + k) % 2 == 0 else odd_tet
                for dx, dy, dz in tet:
                    c = (i + dx, j + dy, k + dz)
                    nodes[key(c)] = c
                    struts.append((center, c))
    return nodes, struts


TOPOLOGIES = {"bcc": bcc_topology, "fcc": fcc_topology, "diamond": diamond_topology}


# ------------------------------------------------------------------- field --
# NOTE: unlike tpms_generator.py, struts do NOT need (and must NOT use) the
# forced-solid boundary-padding trick. A capsule (strut + rounded end-caps) is
# already a fully closed shape on its own -- it never had an "open surface at
# the domain edge" problem the way a periodic TPMS surface does. Forcing a
# very-negative padding value there was capping the ENTIRE outer face solid
# (since -10 dominates any real field value of -0.17..0.6), silently sealing
# the whole lattice inside a solid box. Fix: extend the grid by a small margin
# (room for boundary-touching struts' rounded caps) and extract the raw field
# directly, no padding override.
def build_grid(margin_mm=0.5):
    n_real = int(round(DOMAIN_MM / SPACING)) + 1
    pad_n = int(round(margin_mm / SPACING))
    n_total = n_real + 2 * pad_n
    coords_mm = (np.arange(n_total) - pad_n) * SPACING
    X, Y, Z = np.meshgrid(coords_mm, coords_mm, coords_mm, indexing="ij")
    return coords_mm, X, Y, Z, pad_n, n_real


def strut_field(X, Y, Z, struts_mm, radius, smooth_k=0.0):
    """Union-over-struts capped-cylinder (capsule) signed distance, minus
    radius. smooth_k=0 (default, BCC/FCC-validated path): hard min of raw
    centerline distance, radius subtracted once at the end -- fast, and
    mathematically identical to a hard union of capsules.

    smooth_k>0 (diamond fix): polynomial smooth-min union of the actual
    per-strut SDFs (radius subtracted BEFORE blending, since smooth-min only
    makes sense applied to真 signed distances, not raw centerline distance).
    Rounds the sharp creases where multiple struts meet at diamond's acute
    tetrahedral (~109.5 deg) junction angles -- those creases were producing
    the non-watertight marching-cubes output (2,187 near-degenerate face
    junctions) that blocked diamond earlier. Same fix family as the stent's
    fillet increase: give tight-angle joints more geometric clearance rather
    than fighting the mesher's tolerance after the fact."""
    if smooth_k <= 0:
        field = np.full(X.shape, np.inf, dtype=np.float32)
        for (p1, p2) in struts_mm:
            p1 = np.asarray(p1, dtype=np.float32)
            p2 = np.asarray(p2, dtype=np.float32)
            d = p2 - p1
            seglen2 = float(d @ d)
            px, py, pz = X - p1[0], Y - p1[1], Z - p1[2]
            t = (px * d[0] + py * d[1] + pz * d[2]) / seglen2
            np.clip(t, 0.0, 1.0, out=t)
            cx = p1[0] + t * d[0]
            cy = p1[1] + t * d[1]
            cz = p1[2] + t * d[2]
            dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2 + (Z - cz) ** 2)
            np.minimum(field, dist, out=field)
        field -= radius
        return field

    field = np.full(X.shape, 1e6, dtype=np.float32)
    for (p1, p2) in struts_mm:
        p1 = np.asarray(p1, dtype=np.float32)
        p2 = np.asarray(p2, dtype=np.float32)
        d = p2 - p1
        seglen2 = float(d @ d)
        px, py, pz = X - p1[0], Y - p1[1], Z - p1[2]
        t = (px * d[0] + py * d[1] + pz * d[2]) / seglen2
        np.clip(t, 0.0, 1.0, out=t)
        cx = p1[0] + t * d[0]
        cy = p1[1] + t * d[1]
        cz = p1[2] + t * d[2]
        dist = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2 + (Z - cz) ** 2)
        sdf = (dist - radius).astype(np.float32)
        h = np.clip(0.5 + 0.5 * (sdf - field) / smooth_k, 0.0, 1.0).astype(np.float32)
        field = sdf * (1 - h) + field * h - smooth_k * h * (1 - h)
    return field


def solid_fraction_at(topo_name, radius, coords_mm, X, Y, Z, pad_n, n_real, smooth_k=0.0):
    nodes, struts = TOPOLOGIES[topo_name]()
    struts_mm = [([c * CELL_MM for c in p1], [c * CELL_MM for c in p2]) for (p1, p2) in struts]
    F = strut_field(X, Y, Z, struts_mm, radius, smooth_k=smooth_k)
    real = F[pad_n:pad_n + n_real, pad_n:pad_n + n_real, pad_n:pad_n + n_real]
    return float(np.mean(real <= 0.0)), F


def _extract_mesh(F, coords_mm):
    verts, faces, _, _ = measure.marching_cubes(F, level=0.0, spacing=(SPACING,) * 3)
    verts = verts + coords_mm[0]
    mesh = trimesh.Trimesh(vertices=verts, faces=faces)
    mesh.remove_unreferenced_vertices()
    mesh.fix_normals()
    comps = mesh.split(only_watertight=False)
    dropped = 0
    if len(comps) > 1:
        dropped = len(comps) - 1
        mesh = max(comps, key=lambda c: len(c.faces))
    return mesh, dropped


def real_solid_fraction(topo_name, radius, coords_mm, X, Y, Z, smooth_k=0.0):
    """Expensive but accurate: actually extract the mesh and measure its volume,
    rather than the cheap grid-point-counting proxy (which was found to be
    ~10% off from the true marching-cubes volume -- close enough to bracket
    a starting radius, not close enough to trust for the final porosity)."""
    nodes, struts = TOPOLOGIES[topo_name]()
    struts_mm = [([c * CELL_MM for c in p1], [c * CELL_MM for c in p2]) for (p1, p2) in struts]
    F = strut_field(X, Y, Z, struts_mm, radius, smooth_k=smooth_k)
    mesh, _ = _extract_mesh(F, coords_mm)
    return mesh.volume / (DOMAIN_MM ** 3), mesh


def calibrate_and_extract(topo_name, target_porosity, out_stl,
                           r_lo=0.05, r_hi=0.7, tol_cheap=0.02, tol_real=0.003,
                           max_iter_cheap=10, max_iter_real=8, smooth_k=0.0,
                           margin_mm=0.5):
    # margin must exceed the calibrated strut radius, not just be "a bit of
    # room" -- a boundary-touching strut's rounded capsule cap extends
    # `radius` beyond its endpoint node, and if radius > margin the grid
    # edge cuts that cap off, leaving an open hole (this, not junction
    # angles, was diamond's actual non-watertight defect: r_hi=0.7 alone
    # already exceeds the old fixed 0.5mm margin). r_hi is the calibration
    # bisection's own upper bound, so it's a safe estimate of how large the
    # final radius could get.
    # phase 2 can bracket up to r*1.4 where r may itself already be near
    # r_hi, so use r_hi*1.4 (not just r_hi) as the safe upper estimate.
    margin_mm = max(margin_mm, r_hi * 1.4 + 0.1)
    coords_mm, X, Y, Z, pad_n, n_real = build_grid(margin_mm=margin_mm)
    target_solid = 1.0 - target_porosity

    # --- Phase 1: cheap grid-point-counting bisection to get in the ballpark ---
    lo, hi = r_lo, r_hi
    f_lo, _ = solid_fraction_at(topo_name, lo, coords_mm, X, Y, Z, pad_n, n_real, smooth_k=smooth_k)
    f_hi, _ = solid_fraction_at(topo_name, hi, coords_mm, X, Y, Z, pad_n, n_real, smooth_k=smooth_k)
    print(f"  [{topo_name} p={target_porosity}] solid_frac({lo})={f_lo:.3f}, "
          f"solid_frac({hi})={f_hi:.3f}, target={target_solid:.3f}", flush=True)

    r = 0.5 * (lo + hi)
    for it in range(max_iter_cheap):
        r = 0.5 * (lo + hi)
        f_mid, _ = solid_fraction_at(topo_name, r, coords_mm, X, Y, Z, pad_n, n_real, smooth_k=smooth_k)
        print(f"    [cheap] iter {it}: r={r:.5f} solid_frac={f_mid:.4f} (target {target_solid:.4f})", flush=True)
        if abs(f_mid - target_solid) < tol_cheap:
            break
        if f_mid > target_solid:
            hi = r
        else:
            lo = r

    # --- Phase 2: refine against the REAL extracted-mesh volume ---
    r_lo2, r_hi2 = r * 0.7, r * 1.4  # bracket around the cheap-phase estimate
    f_real, mesh = real_solid_fraction(topo_name, r, coords_mm, X, Y, Z, smooth_k=smooth_k)
    print(f"    [real] r={r:.5f} real_solid_frac={f_real:.4f} (target {target_solid:.4f})", flush=True)
    lo2, hi2 = (r_lo2, r) if f_real > target_solid else (r, r_hi2)
    for it in range(max_iter_real):
        if abs(f_real - target_solid) < tol_real:
            break
        r_try = 0.5 * (lo2 + hi2)
        f_real, mesh = real_solid_fraction(topo_name, r_try, coords_mm, X, Y, Z, smooth_k=smooth_k)
        print(f"    [real] iter {it}: r={r_try:.5f} real_solid_frac={f_real:.4f} "
              f"(target {target_solid:.4f})", flush=True)
        r = r_try
        if f_real > target_solid:
            hi2 = r_try
        else:
            lo2 = r_try

    print(f"  {out_stl}: verts={len(mesh.vertices)}, faces={len(mesh.faces)}, "
          f"watertight={mesh.is_watertight}, volume={mesh.volume:.4f} mm^3 "
          f"(domain={DOMAIN_MM**3:.1f} mm^3, solid_frac={mesh.volume/DOMAIN_MM**3:.3f}, "
          f"target_solid_frac={target_solid:.3f})", flush=True)
    mesh.export(out_stl)
    return mesh, r


if __name__ == "__main__":
    import sys
    topo = sys.argv[1] if len(sys.argv) > 1 else "bcc"
    porosity = float(sys.argv[2]) if len(sys.argv) > 2 else 0.5
    out = sys.argv[3] if len(sys.argv) > 3 else rf"C:\Users\hari0008\Downloads\{topo}_p{int(porosity*100)}.stl"
    # diamond's 4-way tetrahedral (~109.5deg) junctions produced non-watertight
    # marching-cubes output under plain hard-min union; smooth-blend those
    # joints. BCC/FCC (3- and 8-way, gentler angles) are unaffected -- smooth_k=0.
    smooth_k = float(sys.argv[4]) if len(sys.argv) > 4 else (0.08 if topo == "diamond" else 0.0)
    calibrate_and_extract(topo, porosity, out, smooth_k=smooth_k)
