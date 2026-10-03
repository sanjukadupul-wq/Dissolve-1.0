# Dissolve™ – In-Silico Degradation Solver for Biodegradable Metallic Implants

> **DISSOLVE** = **D**egradation **I**n-**S**ilico **SOLVE**r

Supporting code, mesh-generation scripts, calibration, and validation results for the
paper *"Mechanistic modeling of zinc degradation in physiological environments governed
by oxygen reduction kinetics."*

Dissolve™ is a high-fidelity computational platform for predicting degradation of
biodegradable zinc-based implants and porous scaffolds in physiological environments.
Built on a 3D reaction-diffusion and level-set framework using FreeFEM++, MPI, and
PETSc, the solver enables quantitative simulation of implant corrosion, morphology
evolution, and mass loss over clinically relevant time scales.

The software couples oxygen-reduction-reaction (ORR) controlled surface kinetics with
multi-species ionic transport, including Zn²⁺, Cl⁻, OH⁻, and dissolved O₂, together with
corrosion-product film formation and evolution. This mechanistic approach captures both
global degradation behavior and localized corrosion phenomena, providing a predictive
digital environment for implant design and optimization.

## Key Capabilities

- Three-dimensional degradation simulation of biodegradable metallic implants and
  lattice scaffolds.
- Mechanistic ORR-driven corrosion modelling for zinc and zinc-alloy systems.
- Multi-species reaction-diffusion transport in physiological media.
- Dynamic corrosion-product film growth and dissolution modelling.
- Level-set-based interface tracking for accurate geometry evolution.
- Parallel HPC execution using MPI and PETSc for large-scale simulations.
- Mass loss, volume loss, surface recession, and morphology prediction throughout
  degradation.
- Integration with computational design workflows for implant optimization and virtual
  testing.

## Applications

Dissolve™ supports a broad range of biomedical engineering and medical-device
development activities, including:

- Biodegradable orthopaedic implant design
- Bioabsorbable vascular scaffold development
- Patient-specific implant optimization
- Corrosion and degradation assessment
- Digital prototyping and virtual testing
- Research and industrial R&D workflows
- Regulatory and preclinical simulation studies

## Validation and Calibration

The solver has been systematically calibrated and validated against controlled 28-day
HBSS immersion experiments of pure Zn, with ongoing verification across multiple
implant geometries and degradation conditions. Validation workflows include
degradation kinetics, mass-loss evolution, corrosion morphology, and sensitivity
analysis to ensure predictive reliability across a range of biodegradable zinc-alloy
applications.

## Software Architecture

The source code is organized into modular components covering:

- Geometry and mesh generation
- Species transport solvers
- Electrochemical reaction models
- Corrosion-product film kinetics
- Level-set interface evolution
- Parallel execution and solver infrastructure
- Calibration and optimization workflows
- Post-processing and visualization tools

## Technology Stack

- FreeFEM++
- MPI
- PETSc
- High-Performance Computing (HPC) Environments
- Python-based Pre- and Post-processing Utilities

## Developer

**Henaka Ariyarathna**
Computational Modelling and Biodegradable Implant Design

*Accelerating the design of next-generation biodegradable implants through
physics-based virtual degradation testing.*

## Repository Layout

| Folder | Description |
|---|---|
| [`Src Codes/`](Src%20Codes/) | Core Dissolve™ simulation engine and supporting modules. Contains the FreeFEM++ degradation solver (`dissolve.edp`) together with modular implementations for configuration management, computational domains, state variables, physics models, numerical methods, input/output, and utility functions. Also includes calibration and parameter-identification workflows. See its own [README](Src%20Codes/README.md) for the module map, **[`INSTALL.md`](Src%20Codes/INSTALL.md)** for installation, and **[`THEORY.md`](Src%20Codes/THEORY.md)** for the theoretical background. |
| [`Mesh Generation/`](Mesh%20Generation/) | Automated geometry and meshing workflows for biodegradable implant simulations. Includes tools for generating cylinders, TPMS structures (Gyroid, Schwarz-P, Diamond), strut lattices (BCC, FCC), and a multi-ring coronary stent, across a range of porosities. The pipeline converts implicit geometry definitions into watertight surfaces and high-quality tetrahedral finite-element meshes compatible with Dissolve™. |
| [`Calibration/`](Calibration/) | Parameter calibration and sensitivity-analysis resources: `calibrate_bayesian.py` (Bayesian optimization kf/kd/kORR sweep), `sensitivity_morris.py` (Morris global sensitivity), plus `optimization_results.xlsx` — the 50-run calibration sweep and coarse→fine mesh correlation. See [`Src Codes/README.md`](Src%20Codes/README.md#calibration-and-analysis-tools) for how each script is invoked. |
| [`Results/`](Results/) | Reference simulation outputs, validation datasets, and benchmark studies. Includes experimental degradation measurements and corresponding computational predictions used to assess model performance across different degradation scenarios and implant geometries. |
| [`Third-Party Software/`](Third-Party%20Software/) | Summary of external software, libraries, and dependencies used throughout the Dissolve™ ecosystem, including version information, licensing details, and reference links. |

## Key Repository Components

- **Physics-Based Degradation Solver** for biodegradable metallic implants.
- **Automated Mesh Generation Pipeline** for complex lattice and TPMS geometries.
- **Calibration & Validation Frameworks** for predictive model development.
- **Benchmark Experimental Datasets** for verification studies.
- **High-Performance Computing Support** through MPI and PETSc.
- **Extensive Documentation** covering theory, installation, and usage.

This repository provides the complete computational workflow required to generate
implant geometries, perform degradation simulations, calibrate model parameters, and
analyze degradation outcomes within a unified physics-based framework.

## Mesh Assets

Dissolve™ includes the complete mesh-generation workflow but does not distribute
pre-generated simulation meshes. Large finite-element meshes for lattice and TPMS
geometries can range from tens to hundreds of megabytes, making repository
distribution impractical.

All meshes used within the Dissolve™ workflow can be reproduced using the tools
provided in [`Mesh Generation/`](Mesh%20Generation/), including:

- Implicit geometry generation for cylindrical, lattice, and TPMS architectures
- Watertight STL surface generation
- Automated STL-to-tetrahedral mesh conversion
- Region and boundary labeling for simulation-ready models

This approach ensures full reproducibility while allowing users to generate meshes
tailored to their specific implant dimensions, porosities, and design configurations.

For enterprise users requiring validated benchmark meshes, archived reference mesh
packages are available separately upon request.

## Getting Started

Launch a simulation from the solver directory:

```bash
cd "Src Codes"
ff-mpirun -np 4 dissolve.edp \
  -input_mesh path/to/your.mesh \
  -sim_duration 672
```

This example executes a 672-hour degradation simulation using four MPI processes.
Solver behavior, material parameters, transport properties, boundary conditions, and
output options can be configured through the input files and runtime parameters
described in the documentation.

For detailed installation instructions, parameter definitions, workflow examples, and
developer resources, refer to [`Src Codes/README.md`](Src%20Codes/README.md).

## Deployment Options

Dissolve™ supports deployment across a range of computing environments, including:

- Engineering workstations
- Linux servers
- High-Performance Computing (HPC) clusters
- Cloud-based simulation platforms
- Containerized environments

Parallel execution is enabled through MPI and PETSc to support large-scale implant and
scaffold simulations.

## Software Dependencies

Dissolve™ is built on a robust scientific-computing ecosystem including:

- FreeFEM++
- PETSc
- MPI
- Gmsh
- ParaView
- Python Scientific Stack
- Slurm Workload Manager
- Apptainer / Singularity

A complete list of third-party software, version requirements, licensing information,
and installation guidance is provided in
[`Third-Party Software/README.md`](Third-Party%20Software/README.md).

## License

Dissolve™ is released under the **GNU General Public License v3.0 (GPL-3.0)**.

You are free to use, study, modify, and redistribute this software under the terms of
the GPL v3 license. Any derivative works distributed to third parties must also be
released under GPL-compatible terms and accompanied by the corresponding source code.

A copy of the full license is provided in the repository's [`LICENSE`](LICENSE) file.

### Copyright

© 2026 Henaka Ariyarathna. All rights reserved except as granted under the GNU General
Public License v3.0.

### Disclaimer

This software is provided "as is", without warranty of any kind, express or implied,
including but not limited to warranties of merchantability, fitness for a particular
purpose, or non-infringement. The authors shall not be liable for any claim, damages,
or other liability arising from the use of the software.

## Citation & Acknowledgement

If Dissolve™ contributes to published research, technical reports, regulatory
submissions, or product-development activities, please acknowledge the software using
the recommended citation below.

> Henaka Ariyarathna (2026). *Dissolve™: In-Silico Degradation Solver for
> Biodegradable Metallic Implants.*

Additional citation information and related publications will be provided through
future software releases and documentation updates.

If you use this code or data, please also cite the paper named at the top of this
README. *(Full citation to be added once published.)*
