# Dissolve™ – Degradation In-Silico Solver

Dissolve™ is a 3D reaction-diffusion and level-set simulation platform for predicting
degradation of biodegradable zinc-based implants and porous scaffolds in physiological
environments. Built using FreeFEM, MPI, and PETSc, the solver combines mechanistic
corrosion kinetics, multi-species ionic transport, corrosion-product film evolution, and
moving-boundary tracking to predict mass loss, degradation morphology, and
degradation-driven geometric evolution over time.

The current implementation models oxygen-reduction-reaction (ORR)-controlled zinc
degradation by coupling:

- Oxygen reduction reaction (ORR) surface kinetics
- Multi-species transport of Zn²⁺, Cl⁻, OH⁻, and O₂
- Chloride-mediated corrosion-product film growth and dissolution
- Level-set-based interface evolution
- Adaptive finite-element discretization and parallel HPC execution

Dissolve™ is designed for virtual testing, degradation assessment, implant
optimization, and computational design of biodegradable metallic devices.

## Documentation

The project documentation is organized by topic:

| Document | Description |
|---|---|
| **[`INSTALL.md`](INSTALL.md)** | Complete installation and deployment guide, including building FreeFEM 4.14 with MPI and PETSc support, WSL2 setup, HPC deployment, and troubleshooting. |
| **[`THEORY.md`](THEORY.md)** | Governing equations, numerical methods, reaction kinetics, transport formulations, level-set implementation, and theoretical background with supporting references. |
| **[`VALIDATION.md`](VALIDATION.md)** | Solver verification, calibration methodology, validation studies, known limitations, and benchmark results. |

New users should begin with `INSTALL.md` before attempting to run any simulations.

## Software Architecture

Dissolve™ follows a modular architecture in which physics, numerical methods, mesh
management, and I/O functionality are separated into dedicated components — each stage
of the pipeline lives in its own folder:

```
Src Codes/
├── dissolve.edp                    # entry point — run this with mpirun/FreeFem++-mpi
├── config/
│   ├── dependencies.idp            # FreeFEM plugin loads, CLI arg parsing
│   └── settings.idp                # every tunable parameter (-flag overrides)
├── domain/
│   └── mesh_setup.idp              # mesh import/generation, partitioning
├── state/
│   ├── fields.idp                  # finite-element field declarations
│   └── initial_state.idp           # initial conditions, solver setup
├── physics/
│   ├── governing_equations.idp     # weak forms of the coupled PDEs
│   ├── interface_kinetics.idp      # Stefan condition (Newton solve)
│   └── interface_velocity.idp      # per-step interface velocity
├── numerics/
│   ├── timestep_solver.idp         # per-step PDE solves + redistancing
│   └── mesh_refinement.idp         # adaptive remeshing around the interface
├── io/
│   ├── write_results.idp           # VTK snapshots, mass-loss & mechanism logs
│   ├── export_geometry.idp         # periodic scaffold mesh export
│   ├── write_final_state.idp       # final-state VTK dump
│   ├── checkpoint_write.idp        # periodic full-state checkpoint (-checkpoint_each_time)
│   └── checkpoint_read.idp         # resume from checkpoint (-restart_from)
└── utils/
    └── helpers.idp                 # shared macros & small utility functions
```

`dissolve.edp` includes each `.idp` file in pipeline order (dependencies →
settings → helpers → mesh → fields → equations → Stefan init → initial
state → time loop), so it doubles as a map of how the solver actually runs.

Calibration/sensitivity scripts now live in [`../Calibration/`](../Calibration/)
at the repo root (a sibling of `Src Codes/`, not a subfolder of it) — see that
folder's section below.

### Module Overview

| Module | Purpose |
|---|---|
| `dissolve.edp` | Main solver entry point and simulation workflow driver |
| `config/` | Runtime settings, dependency loading, and command-line argument handling |
| `domain/` | Mesh import, partitioning, geometry preparation, and domain setup |
| `state/` | Field definitions, variable allocation, and initialization |
| `physics/` | Reaction kinetics, transport equations, interface evolution, and governing equations |
| `numerics/` | Time integration, adaptive remeshing, stabilization, and solver execution |
| `io/` | Result export, VTK generation, checkpoints, and restart functionality |
| `utils/` | Shared helper functions and utility macros |

The main solver (`dissolve.edp`) executes these modules in sequence, providing a
transparent and extensible simulation workflow.

## Quick Start

Need FreeFEM++ built with MPI/PETSc first — see **[`INSTALL.md`](INSTALL.md)**
for the full step-by-step guide (WSL2-based; native Windows MPI is unreliable
for this solver).

After completing installation, launch a simulation from the `Src Codes` directory:

```bash
cd "Src Codes"

mpirun -np 4 FreeFem++-mpi -nw dissolve.edp \
  -input_mesh path/to/your.mesh \
  -sim_duration 672
```

where:

- `-np 4` specifies the number of MPI processes
- `-input_mesh` specifies the simulation mesh
- `-sim_duration` specifies the degradation duration (hours)

Example:

```bash
mpirun -np 8 FreeFem++-mpi -nw dissolve.edp \
  -input_mesh ../Meshes/gyroid70.mesh \
  -sim_duration 672
```

Run from this folder (`Src Codes/`) so the relative `include` paths in
`dissolve.edp` resolve correctly. All parameters in `config/settings.idp`
can be overridden from the command line, e.g. `-k_f`, `-k_orr`, `-dt_hours`,
`-emit_vtk`.

**Important: mesh paths must not contain spaces.** FreeFEM's `getARGV` truncates
`-input_mesh` (and any other string argument) at the first space in the
path — this has caused several silent failures during development. Keep
meshes in a space-free directory.

## Validated configuration

The parameters below reproduce the experimental mass-loss curve within
10% at every measured timepoint (24/72/168/336/672h) on the production
mesh. Full derivation, the bugs that had to be fixed first, and what's
still open: **[`VALIDATION.md`](VALIDATION.md)** — read this before trusting
or extending any result from this solver.

```bash
mpirun -np 16 FreeFem++-mpi -nw dissolve.edp -v 0 \
  -input_mesh path/to/your.mesh \
  -dt_hours 4.0 -sim_duration 672.0 -save_interval 4.0 \
  -k_orr 0.25 -k_f 10 -k_d 39.22 -film_tortuosity 120.0 \
  -enable_redistance 0 -vel_extension 1 -h_interface 0.05 -search_method 1 \
  -checkpoint_each_time 24 \
  -results_file output/result.txt
```

These fitted values (`kORR`, `k_f`, `tau`) are specific to this mesh's
resolution — see `VALIDATION.md`'s "Mesh Dependency" section before reusing
them on a different mesh or geometry.

## Key Features

- 3D degradation simulation of biodegradable zinc implants
- Reaction-diffusion modelling of corrosion processes
- ORR-controlled electrochemical degradation kinetics
- Multi-species transport of Zn²⁺, Cl⁻, OH⁻, and O₂
- Corrosion-product film formation and degradation
- Level-set-based tracking of evolving implant surfaces
- Adaptive remeshing around moving interfaces
- MPI/PETSc-enabled high-performance computing support
- Checkpoint and restart capability
- Calibration and sensitivity-analysis frameworks
- ParaView-compatible visualization output

## Command-line reference

Every setting below is overridable from `config/settings.idp`'s defaults.
Grouped by what each one actually controls, not by file.

**Kinetics** (`config/settings.idp`)
| flag | default | meaning |
|---|---|---|
| `-k_f` | 125 | film formation rate |
| `-k_d` | 40 | chloride-driven film degradation rate |
| `-k_orr` | 0.015 | oxygen reduction reaction rate constant |
| `-film_tortuosity` | 2.0 | film tortuosity (diffusion-blocking strength) |
| `-diff_zn`, `-diff_cl`, `-diff_oh`, `-diff_o2` | material defaults | species diffusivities |

**Interface-velocity numerics** (`physics/interface_velocity.idp`)
| flag | default | meaning |
|---|---|---|
| `-vel_extension` | 0 | `1` = probe at a fixed distance from the interface (`φ`) rather than from each node — see `VALIDATION.md`'s "Velocity Extension Method" section |
| `-search_method` | 0 | `1` = robust FreeFEM point location; required with `-vel_extension 1` |
| `-h_interface` | 0.002 | interface probe distance (mm); `-1` = use the mesh-derived value instead |
| `-delta_eps` | -1 | width of the regularized delta function used for surface-averaged diagnostics; `-1` = mesh `hmin` |
| `-legacy_vo2diff_sign` | 0 | `1` = restore the pre-fix (incorrect) `vO2Diff` sign, for A/B comparison only |
| `-use_vzn` | 1 | `0` = drop the Zn-transport branch from `v = max(vZn, vO2)` (diagnostic) |
| `-force_v` | 0 | force a uniform interface velocity in the near-interface band (diagnostic) |
| `-debug_probe` | 0 | `1` = print per-step O₂/φ/DeO2/F values at the interface probe (adds per-step cost) |

**Redistancing** (`domain/mesh_setup.idp`, `numerics/timestep_solver.idp`)
| flag | default | meaning |
|---|---|---|
| `-enable_redistance` | 1 | periodic `distance()` reinitialization — **not volume-conserving, see `VALIDATION.md`'s "Level-Set Reinitialization Volume Loss" section**; validated runs use `0` |
| `-redistance_interval` | 1.0 | hours between reinitializations, when enabled |

**Checkpoint / restart**
| flag | default | meaning |
|---|---|---|
| `-checkpoint_each_time` | 24.0 | hours between checkpoint writes (overwrites the previous one — bounded disk use) |
| `-checkpoint_dir` | same as `-results_file`'s directory | where checkpoints are written/read |
| `-restart_from <dir>` | (unset) | resume from a checkpoint instead of a cold start. Must use the same mesh, `-np`, and `-dt_hours` as the original run. |

**O₂ under-relaxation** (`numerics/timestep_solver.idp`)
| flag | default | meaning |
|---|---|---|
| `-o2_relax_omega` | 0.3 | reference under-relaxation factor |
| `-o2_relax_ref_dt` | 1.0 | the `-dt_hours` at which `-o2_relax_omega` applies exactly |
| `-o2_relax_scale_dt` | 1 | `0` = restore the old dt-dependent (unscaled) behavior |

**Output**
| flag | default | meaning |
|---|---|---|
| `-emit_vtk` | 0 | write VTK snapshots |
| `-save_vtk_each_time` | 168.0 | hours between snapshots |
| `-overwrite_vtk` | 0 | `1` = allow overwriting an existing VTK series at the same `-vtk_prefix`; otherwise the run refuses to start rather than silently interleave with existing output |
| `-vol_smooth_eps` | 0.05 | width of the continuous (non-quantized) volume metric written to `mass_loss_smooth.txt`, useful when the primary step-function metric is too coarse to resolve slow dissolution |

## Not included here

Mesh binaries (`.mesh`/`.sol`), simulation output, and run logs are left out
of this source-only upload — they're large, environment-specific artifacts
rather than source code. Point `-input_mesh` at your own mesh, or regenerate
one, to run the solver.

## Calibration and Analysis Tools

The root-level [`../Calibration/`](../Calibration/) directory (a sibling of
`Src Codes/`, not a subfolder of it — see its own section in the main repo
README) contains workflows for parameter estimation, optimization, and
uncertainty analysis. All scripts drive `dissolve.edp` directly via subprocess
and share the same `local`/`m3` launcher toggle (`CALIB_LAUNCHER`, `CALIB_NP`,
`CALIB_SIF_PATH` env vars):

| Script | Purpose |
|---|---|
| `calibrate_bayesian.py` | Bayesian optimization (kf/kd/kORR sweep) using Gaussian-process surrogate modelling |
| `sensitivity_morris.py` | Global sensitivity screening using the Morris Elementary Effects method |

These tools interface directly with Dissolve™ and support automated evaluation of
degradation model parameters.

Note: the validated parameters above were originally derived via a log-space
Nelder–Mead screening → grid-search process (parameters here span multiple
orders of magnitude, so a linear-space simplex barely moves off its starting
point in any practical number of evaluations) — see `VALIDATION.md`'s
"Parameter Interpretation" table for the reasoning behind each parameter's
role and why `k_d` has minimal influence in the current validation regime.
That Nelder-Mead script isn't included in this repository; `calibrate_bayesian.py`
below is the provided tool for recalibrating `kf`/`kd`/`kORR` against new data.

- **`calibrate_bayesian.py`** — Gaussian-process Bayesian Optimization
  (`bayes_opt`) over the same three parameters, with early stopping, a
  multi-fidelity coarse→fine correction factor, Random Forest parameter
  importance, GP surrogate landscape plots, and an HTML report. Needs
  `../Calibration/requirements.txt` installed (`bayes_opt`, `scikit-learn`,
  `rich`, etc. — not part of this project's core dependencies).
- **`sensitivity_morris.py`** — Morris (Elementary Effects) global
  sensitivity screening over 8 parameters (`k1`, `k2`, `k_orr`, `d_o2`,
  `initial_o2`, `d_zn`, `d_cl`, `d_oh`) via `SALib`, ranking each by its
  mean absolute effect (μ\*) on RMSE against experimental checkpoints.
  Also needs `../Calibration/requirements.txt`.

## Output and Visualization

Dissolve™ can export:

- VTK (`.vtu`, `.pvd`) visualization files
- Mass-loss histories
- Concentration fields
- Corrosion-product distributions
- Evolving degradation geometries
- Checkpoint files for restart operations

Simulation results can be visualized using ParaView.
