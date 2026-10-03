# Third-Party Software and Dependencies

This document summarizes the principal third-party software, libraries, and platforms
used throughout the Dissolve™ ecosystem, including simulation, mesh generation,
visualization, data processing, and high-performance computing workflows.

All trademarks and software copyrights remain the property of their respective owners.
Users are responsible for complying with the licensing terms of any third-party
software installed alongside Dissolve™.

## Core Simulation

| Software | Version | Purpose in Dissolve™ | License | Website |
|---|---|---|---|---|
| **FreeFEM** | 4.14 | Primary multiphysics finite-element platform supporting the Dissolve™ degradation simulation engine. | LGPL v3 | <https://freefem.org> |
| **PETSc** | Included with FreeFEM installation | Parallel solver infrastructure providing scalable numerical solution of large sparse systems arising from transport, reaction, and interface-evolution equations. | BSD 2-Clause | <https://petsc.org> |
| **OpenMPI** | Included with FreeFEM installation | Distributed-memory parallel computing framework used for high-performance execution across multi-core and cluster computing environments. | BSD 3-Clause | <https://www.open-mpi.org> |

## Meshing and Geometry

| Software | Version | Purpose in Dissolve™ | License | Website |
|---|---|---|---|---|
| **Gmsh** | 4.13.1 | Geometry construction, surface processing, and finite-element mesh generation for implant, scaffold, TPMS, and lattice architectures used within Dissolve™ workflows. | GPL v2+ | <https://gmsh.info> |
| **TetGen** | Bundled with FreeFEM build | Tetrahedral mesh generation and volumetric discretization of simulation domains for finite-element analysis. | AGPL v3* | <https://wias-berlin.de/software/tetgen> |
| **MMG (mmg3d / mmgs)** | Bundled with FreeFEM build | Adaptive anisotropic remeshing and mesh-quality optimization during geometry evolution and interface tracking. | LGPL v3 | <https://www.mmgtools.org> |
| **Mshmet** | Bundled with FreeFEM build | Mesh-metric generation for solution-adaptive refinement and mesh sizing. | Research License | <https://github.com/ISCDtoolbox/Mshmet> |
| **Medit** | Bundled with FreeFEM build | Mesh visualization, inspection, and support for the Medit mesh format used throughout the Dissolve™ workflow. | Research License | <https://github.com/ISCDtoolbox/Medit> |
| **scikit-image** | Current supported version | Marching-cubes surface extraction from implicit (signed-distance-field) geometry definitions in each geometry's `Mesh Generation/<Geometry>/` STL generator. | BSD 3-Clause | <https://scikit-image.org> |
| **trimesh** | Current supported version | Watertight mesh cleanup, validation, and STL export in the STL generation stage. | MIT | <https://trimesh.org> |
| **meshio** | Current supported version | Reads/writes the Medit `.mesh` format in `Mesh Generation/stl_to_freefem_mesh.py`. | MIT | <https://github.com/nschloe/meshio> |

\* TetGen's AGPL v3 license permits free use for open-source/research purposes; commercial
or proprietary use requires a separate commercial license from the author — see the
TetGen website for terms.

## Python Scientific Stack

| Software | Version | Purpose in Dissolve™ | License | Website |
|---|---|---|---|---|
| **Python** | 3.x | Primary scripting environment for workflow automation, calibration routines, preprocessing, postprocessing, and data analysis tasks within the Dissolve™ ecosystem. | PSF License | <https://www.python.org> |
| **SciPy** | Current supported version | Scientific computing and numerical optimization library used for parameter identification, calibration, sensitivity analysis, and kinetic model fitting. | BSD 3-Clause | <https://scipy.org> |
| **Matplotlib** | Current supported version | Generation of convergence plots, validation figures, calibration visualizations, and simulation performance analytics. | Matplotlib License (BSD-style) | <https://matplotlib.org> |

## Visualization

| Software | Version | Purpose in Dissolve™ | License | Website |
|---|---|---|---|---|
| **ParaView** | Current supported version | Visualization and analysis of Dissolve™ simulation results (`.pvd` and `.vtu` files), including mass-loss distributions, ionic concentration fields, evolving degradation fronts, and degraded implant geometries. | BSD 3-Clause | <https://www.paraview.org> |

## HPC Infrastructure

| Software | Version | Purpose in Dissolve™ | License | Website |
|---|---|---|---|---|
| **Slurm** | HPC Cluster Installation | Job scheduling and resource management for Dissolve™ simulations using batch submission scripts (`.slurm`) on high-performance computing clusters. | GPL v2 | <https://slurm.schedmd.com> |
| **Apptainer / Singularity** | HPC Cluster Installation | Containerized FreeFEM execution environment (`freefem.sif`) used to ensure reproducible Dissolve™ simulation runs across HPC platforms. | Apache License 2.0 | <https://apptainer.org> |

## Data and Documentation

| Software | Version | Purpose in Dissolve™ | License | Website |
|---|---|---|---|---|
| **Microsoft Excel** | Microsoft 365 / Office | Storage and review of calibration, optimization, validation, and simulation-result workbooks (`.xlsx`). | Proprietary | <https://www.microsoft.com/microsoft-365/excel> |
| **LibreOffice Calc** | Current supported version | Open-source alternative for accessing and editing Dissolve™ spreadsheet datasets and result files. | MPL 2.0 | <https://www.libreoffice.org> |

## Licensing Notice

Dissolve™ incorporates or depends upon software distributed under a variety of
open-source licenses. These licenses apply only to the respective third-party
components and do not modify the licensing terms of Dissolve™ itself.

For complete licensing information, version histories, and installation resources,
please refer to the official websites and repositories of the corresponding projects.

## Acknowledgements

The Dissolve™ development team gratefully acknowledges the open-source scientific
computing community, whose software frameworks and tools provide the foundation for
advanced computational modelling and simulation workflows.
