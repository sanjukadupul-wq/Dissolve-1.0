# Mesh Generation

This directory contains the geometry-generation and meshing workflows used to create
the simulation-ready meshes used by Dissolve™. The workflow converts implant
geometries into fully-labelled 3D finite-element meshes suitable for degradation
simulations.

## Supported Geometries

The current workflow supports:

```text
Cylinder
Stent
BCC Lattice
FCC Lattice
Diamond (Strut Lattice)
Gyroid TPMS
Schwarz-P TPMS
```

Each geometry is provided in a dedicated folder containing the script required to
generate its STL surface (stage 1). STL-to-mesh conversion (stage 2) is shared across
every geometry — one script, `stl_to_freefem_mesh.py`, at the root of this directory:

```text
Mesh Generation/
├── stl_to_freefem_mesh.py   # shared stage-2 STL -> FreeFEM .mesh converter
├── Cylinder/
│   └── make_cylinder_stl.py
├── Stent/
│   └── generate_stent_multiring.py
├── BCC/
│   └── bcc_generator.py
├── FCC/
│   └── fcc_generator.py
├── Diamond/
│   └── diamond_generator.py
├── Gyroid/
│   └── gyroid_generator.py
└── SchwarzP/
    └── schwarzp_generator.py
```

## Workflow Overview

All geometries follow the same basic pipeline:

```text
Geometry Definition
        ↓
STL Surface Generation
        ↓
Surface Cleanup
        ↓
Volume Meshing
        ↓
Scaffold-in-Box Domain Creation
        ↓
Region Labelling
        ↓
FreeFEM .mesh Export
```

The final output is a simulation-ready Medit mesh compatible with Dissolve™.

## Stage 1: Geometry Generation

Geometries are first generated as watertight STL surfaces. Depending on the geometry
type, this may involve analytical geometry definitions, implicit surfaces, TPMS
functions, or lattice unit-cell definitions.

For TPMS structures, the repository includes support for Gyroid and Schwarz-P using
porosity-calibrated implicit surface generation:

```text
Unit Cell Definition
        ↓
Periodic Replication
        ↓
Porosity Calibration
        ↓
Marching Cubes Extraction
        ↓
Watertight STL
```

## Stage 2: STL to Finite-Element Mesh Conversion

Generated STL surfaces are converted into volumetric finite-element meshes using Gmsh
(`stl_to_freefem_mesh.py`):

```text
Import STL
        ↓
Surface Classification
        ↓
Volume Reconstruction
        ↓
Bounding Box Generation
        ↓
Scaffold-Fluid Domain Creation
        ↓
Adaptive Mesh Refinement
        ↓
Medit .mesh Export
```

```bash
python3 stl_to_freefem_mesh.py \
  --stl Gyroid/gyroid_p50.stl \
  --out gyroid50.mesh \
  --box 6 6 6 \
  --size_min 0.08 --size_max 1.5 \
  --dist_min 0.3 --dist_max 6.0
```

`--angle` (default 40°) may need raising for gentler-curvature shapes like Schwarz-P;
`--overlap_tol` helps with tight strut clearances that gmsh otherwise flags as "nearly
self-intersecting." Run with `--help` for the full flag list.

## Computational Domain

Dissolve™ requires two distinct volumetric regions:

```text
Region 1 : Scaffold
Region 2 : Physiological Medium
```

The meshing workflow automatically creates the scaffold volume and the surrounding
fluid volume within a bounding simulation domain.

### Boundary Labels

The generated meshes contain all boundary conditions required by Dissolve™:

| Label | Description |
|---|---|
| 1 | Scaffold region |
| 2 | Fluid region |
| 3 | External box walls |
| 6 | Scaffold-fluid interface |

These labels are assigned automatically during mesh generation.

## Adaptive Meshing

To improve accuracy near the degrading surface, mesh density is increased near the
scaffold-fluid interface:

```text
Interface → Fine Elements → Accurate Transport Gradients
```

while coarser elements are used further from the scaffold:

```text
Far Field → Larger Elements → Reduced Computational Cost
```

This produces efficient meshes while maintaining resolution where degradation occurs.

## TPMS Structures

The TPMS workflow (`Gyroid/`, `SchwarzP/`) generates periodic porous architectures
directly from their implicit equations.

Features:

- Porosity-controlled generation
- Periodic unit-cell replication
- Watertight STL export
- Automatic finite-element meshing
- Dissolve™ compatibility

## Lattice Structures

Supported lattice architectures (`BCC/`, `FCC/`, `Diamond/`):

Features:

- Strut-based geometry generation
- User-defined porosity
- Simulation-ready meshes
- Automatic region labelling

## Stent Meshes

The stent workflow (`Stent/`) supports patient-specific designs, generic stent
geometries, and porous stent structures, generating fully-labelled scaffold-in-fluid
meshes suitable for degradation simulations.

## Output Files

Typical outputs include:

| Extension | Description |
|---|---|
| `.stl` | Geometry surface |
| `.msh` | Gmsh mesh |
| `.mesh` | FreeFEM / Medit mesh |

The `.mesh` file is the format used directly by Dissolve™.

## Using Generated Meshes

```bash
mpirun -np 4 FreeFem++-mpi -nw dissolve.edp \
  -input_mesh path/to/gyroid70.mesh \
  -sim_duration 672
```

## Geometry Customization

Users may modify porosity, unit-cell size, strut thickness, bounding box dimensions,
mesh density, and interface refinement distance to generate custom implant designs.

## Software Requirements

The mesh-generation workflow uses Python, NumPy, scikit-image, Trimesh, Gmsh, and
Meshio, depending on the geometry type and workflow stage — see
[`../Third-Party Software/README.md`](../Third-Party%20Software/README.md).

## Notes

- Meshes distributed with publications are not included in this repository.
- Large meshes can occupy hundreds of megabytes.
- All geometries can be regenerated using the scripts provided here.
- Mesh independence should be verified when generating new geometries or resolutions.
