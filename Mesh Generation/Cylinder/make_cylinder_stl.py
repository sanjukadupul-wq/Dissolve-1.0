import trimesh
import numpy as np

# 10 mm diameter, 2 mm height disc/cylinder -- matches the paper's Zn disc specimen
radius = 5.0
height = 2.0
cyl = trimesh.creation.cylinder(radius=radius, height=height, sections=96)

print(f"vertices={len(cyl.vertices)}, faces={len(cyl.faces)}")
print(f"is_watertight={cyl.is_watertight}")
print(f"bounds=\n{cyl.bounds}")

edges = cyl.edges_unique_length
print(f"edge length: min={edges.min():.4f} max={edges.max():.4f} mean={edges.mean():.4f} median={np.median(edges):.4f}")

out = r"C:\Users\hari0008\Downloads\cylinder_10x2.stl"
cyl.export(out)
print(f"Saved: {out}")
