"""
Reusable STL -> FreeFEM-ready scaffold-in-box mesh pipeline.
classify surfaces -> build scaffold volume -> build box -> box-minus-scaffold
medium volume -> distance-field adaptive grading near interface -> Medit .mesh
with correct region/surface labels (scaffold=1, medium=2, Wall=3, interface=6).
"""
import gmsh
import meshio
import numpy as np
import math
import argparse


def build(stl_path, out_mesh, center, box_size, size_min, size_max, dist_min, dist_max,
          classify_angle_deg=40, overlap_tol_deg=None):
    cx, cy, cz = center
    Lx, Ly, Lz = box_size
    bx0, bx1 = cx - Lx / 2, cx + Lx / 2
    by0, by1 = cy - Ly / 2, cy + Ly / 2
    bz0, bz1 = cz - Lz / 2, cz + Lz / 2

    gmsh.initialize()
    gmsh.option.setNumber("General.Terminal", 1)
    gmsh.model.add("scaffold_in_box")
    gmsh.merge(stl_path)

    print(f"Classifying and building scaffold surface/volume (angle={classify_angle_deg} deg)...", flush=True)
    angle = classify_angle_deg * math.pi / 180
    gmsh.model.mesh.classifySurfaces(angle, True, True, 180 * math.pi / 180)
    gmsh.model.mesh.createGeometry()

    scaffold_surfaces = gmsh.model.getEntities(2)
    scaffold_surf_tags = [s[1] for s in scaffold_surfaces]
    scaffold_loop = gmsh.model.geo.addSurfaceLoop(scaffold_surf_tags)
    vol_scaffold = gmsh.model.geo.addVolume([scaffold_loop])

    print(f"Building bounding box ({Lx} x {Ly} x {Lz} mm)...", flush=True)
    p = [
        gmsh.model.geo.addPoint(bx0, by0, bz0, size_max),
        gmsh.model.geo.addPoint(bx1, by0, bz0, size_max),
        gmsh.model.geo.addPoint(bx1, by1, bz0, size_max),
        gmsh.model.geo.addPoint(bx0, by1, bz0, size_max),
        gmsh.model.geo.addPoint(bx0, by0, bz1, size_max),
        gmsh.model.geo.addPoint(bx1, by0, bz1, size_max),
        gmsh.model.geo.addPoint(bx1, by1, bz1, size_max),
        gmsh.model.geo.addPoint(bx0, by1, bz1, size_max),
    ]
    l = [
        gmsh.model.geo.addLine(p[0], p[1]), gmsh.model.geo.addLine(p[1], p[2]),
        gmsh.model.geo.addLine(p[2], p[3]), gmsh.model.geo.addLine(p[3], p[0]),
        gmsh.model.geo.addLine(p[4], p[5]), gmsh.model.geo.addLine(p[5], p[6]),
        gmsh.model.geo.addLine(p[6], p[7]), gmsh.model.geo.addLine(p[7], p[4]),
        gmsh.model.geo.addLine(p[0], p[4]), gmsh.model.geo.addLine(p[1], p[5]),
        gmsh.model.geo.addLine(p[2], p[6]), gmsh.model.geo.addLine(p[3], p[7]),
    ]
    loops = [
        gmsh.model.geo.addCurveLoop([l[0], l[1], l[2], l[3]]),
        gmsh.model.geo.addCurveLoop([l[4], l[5], l[6], l[7]]),
        gmsh.model.geo.addCurveLoop([l[0], l[9], -l[4], -l[8]]),
        gmsh.model.geo.addCurveLoop([l[1], l[10], -l[5], -l[9]]),
        gmsh.model.geo.addCurveLoop([l[2], l[11], -l[6], -l[10]]),
        gmsh.model.geo.addCurveLoop([l[3], l[8], -l[7], -l[11]]),
    ]
    box_surfs = [gmsh.model.geo.addPlaneSurface([loop]) for loop in loops]
    box_loop = gmsh.model.geo.addSurfaceLoop(box_surfs)
    vol_medium = gmsh.model.geo.addVolume([box_loop, -scaffold_loop])

    gmsh.model.geo.synchronize()

    gmsh.model.addPhysicalGroup(3, [vol_scaffold], tag=1, name="scaffold")
    gmsh.model.addPhysicalGroup(3, [vol_medium], tag=2, name="medium")
    gmsh.model.addPhysicalGroup(2, box_surfs, tag=3, name="wall")
    gmsh.model.addPhysicalGroup(2, scaffold_surf_tags, tag=6, name="scaffold_medium_interface")

    print("Setting up distance-based adaptive sizing field near the interface...", flush=True)
    gmsh.model.mesh.field.add("Distance", 1)
    gmsh.model.mesh.field.setNumbers(1, "SurfacesList", scaffold_surf_tags)
    gmsh.model.mesh.field.setNumber(1, "Sampling", 100)

    gmsh.model.mesh.field.add("Threshold", 2)
    gmsh.model.mesh.field.setNumber(2, "InField", 1)
    gmsh.model.mesh.field.setNumber(2, "SizeMin", size_min)
    gmsh.model.mesh.field.setNumber(2, "SizeMax", size_max)
    gmsh.model.mesh.field.setNumber(2, "DistMin", dist_min)
    gmsh.model.mesh.field.setNumber(2, "DistMax", dist_max)
    gmsh.model.mesh.field.setAsBackgroundMesh(2)

    gmsh.option.setNumber("Mesh.MeshSizeExtendFromBoundary", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromPoints", 0)
    gmsh.option.setNumber("Mesh.MeshSizeFromCurvature", 0)
    if overlap_tol_deg is not None:
        gmsh.option.setNumber("Mesh.AngleToleranceFacetOverlap", overlap_tol_deg)

    print("Generating 3D mesh with adaptive grading...", flush=True)
    gmsh.model.mesh.generate(3)

    elem_types, elem_tags, _ = gmsh.model.mesh.getElements(dim=3)
    ntets = sum(len(t) for t in elem_tags) if elem_tags else 0
    nnodes = len(gmsh.model.mesh.getNodes()[0])
    print(f"RESULT: nodes={nnodes}, tetrahedra={ntets}", flush=True)

    gmsh.write(out_mesh)
    gmsh.finalize()
    print(f"Saved: {out_mesh}", flush=True)


def fix_triangle_refs(path):
    m = meshio.read(path)
    new_cell_data = {}
    for key, blocks in m.cell_data.items():
        new_blocks = []
        for cb, arr in zip(m.cells, blocks):
            arr = np.asarray(arr).copy()
            if cb.type == "triangle":
                uniq = np.unique(arr)
                wall_refs = set(np.sort(uniq)[-6:].tolist())  # 6 box faces, created last
                wall_mask = np.isin(arr, list(wall_refs))
                arr[wall_mask] = 3
                arr[~wall_mask] = 6
                print(f"  triangle ref fix: {wall_mask.sum()} -> Wall(3), {(~wall_mask).sum()} -> interface(6)")
            new_blocks.append(arr)
        new_cell_data[key] = new_blocks
    m.cell_data = new_cell_data
    meshio.write(path, m, file_format="medit")

    m2 = meshio.read(path)
    for key, blocks in m2.cell_data.items():
        for cb, arr in zip(m2.cells, blocks):
            arr = np.asarray(arr).ravel()
            uniq, counts = np.unique(arr, return_counts=True)
            print(f"  FINAL [{cb.type}] {key}: {dict(zip(uniq.tolist(), counts.tolist()))}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--stl", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--center", nargs=3, type=float, default=[0, 0, 0])
    ap.add_argument("--box", nargs=3, type=float, required=True, help="Lx Ly Lz in mm")
    ap.add_argument("--size_min", type=float, default=0.15)
    ap.add_argument("--size_max", type=float, default=3.0)
    ap.add_argument("--dist_min", type=float, default=0.3)
    ap.add_argument("--dist_max", type=float, default=6.0)
    ap.add_argument("--angle", type=float, default=40.0,
                     help="classifySurfaces angle threshold in degrees (default 40; "
                          "gentler-curvature shapes like Schwarz P may need e.g. 90)")
    ap.add_argument("--overlap_tol", type=float, default=None,
                     help="Mesh.AngleToleranceFacetOverlap in degrees (gmsh default 0.1). "
                          "Lower this below a reported 'nearly self-intersecting facets' "
                          "dihedral angle to allow genuinely-close-but-not-touching surfaces "
                          "(e.g. tight strut clearances) through without erroring.")
    args = ap.parse_args()

    build(args.stl, args.out, tuple(args.center), tuple(args.box),
          args.size_min, args.size_max, args.dist_min, args.dist_max,
          classify_angle_deg=args.angle, overlap_tol_deg=args.overlap_tol)
    fix_triangle_refs(args.out)
