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
| **[`INSTALL.md`](INSTALL.md)** | Complete installation and deployment guide, including the tested software environment, the v1.1.0 checkout, the regression suite, WSL2 setup, HPC deployment, and troubleshooting. |
| **[`THEORY.md`](THEORY.md)** | Governing equations, numerical methods, reaction kinetics, transport formulations, level-set implementation, and theoretical background with supporting references. |
| **[`VALIDATION.md`](VALIDATION.md)** | Solver verification, calibration methodology, validation studies, known limitations, and benchmark results. |

New users should begin with `INSTALL.md` before attempting to run any simulations.

## Software Architecture

Dissolve™ follows a modular architecture in which physics, numerical methods, mesh
management, and I/O functionality are separated into dedicated components — each stage
of the pipeline lives in its own folder:

```text
Src Codes/
├── dissolve.edp                    # entry point (run with FreeFem++-mpi)
├── config/
│   ├── dependencies.idp            # FreeFEM plugin loads, CLI arg parsing
│   └── settings.idp                # every tunable parameter (-flag overrides)
├── domain/
│   └── mesh_setup.idp              # mesh import, partitioning
├── state/
│   ├── fields.idp                  # finite-element field declarations
│   └── initial_state.idp           # initial conditions, solver setup
├── physics/
│   ├── governing_equations.idp     # weak forms of the coupled PDEs
│   ├── flux_first.idp              # flux-first coupling (-flux_first 1): v1.1.0 formulation
│   ├── interface_kinetics.idp      # Stefan condition (initial velocity)
│   └── interface_velocity.idp      # legacy probe-based velocity (-flux_first 0)
├── numerics/
│   ├── timestep_solver.idp         # per-step solves, level-set advance, reinitialisation
│   └── mesh_refinement.idp         # adaptive remeshing around the interface
├── io/
│   ├── write_results.idp           # VTK snapshots, mass-loss and balance outputs
│   ├── export_geometry.idp         # periodic scaffold mesh export
│   ├── write_final_state.idp       # final-state VTK dump
│   ├── diskspace_guard.idp         # disk-space guard for VTK/checkpoint writes
│   ├── checkpoint_write.idp        # periodic full-state checkpoint (-checkpoint_each_time)
│   └── checkpoint_read.idp         # resume from checkpoint (-restart_from)
├── tests/
│   ├── check.py                    # regression and mass-balance checks
│   └── run_tests.sbatch            # test runner (Slurm or local)
└── utils/
    └── helpers.idp                 # shared macros and small utility functions
```

`dissolve.edp` includes each `.idp` file in pipeline order (dependencies →
settings → helpers → mesh → fields → equations → Stefan init → initial
state → time loop), so it doubles as a map of how the solver actually runs.

Calibration/sensitivity scripts now live in [`../Scripts/`](../Scripts/)
at the repo root (a sibling of `Src Codes/`, not a subfolder of it) — see that
folder's section below.

### Module Overview

| Module | Purpose |
|---|---|
| `dissolve.edp` | Main solver entry point and simulation workflow driver |
| `config/` | Runtime settings, dependency loading, and command-line argument handling |
| `domain/` | Mesh import, partitioning, geometry preparation, and domain setup |
| `state/` | Field definitions, variable allocation, and initialization |
| `physics/` | Governing equations, flux-first interface coupling, interface kinetics and the legacy probe-based velocity |
| `numerics/` | Time integration, level-set reinitialisation, adaptive remeshing, stabilization, and solver execution |
| `io/` | Result export, VTK generation, checkpoints, and restart functionality |
| `tests/` | Regression and mass-balance checks for the solver |
| `utils/` | Shared helper functions and utility macros |

The main solver (`dissolve.edp`) executes these modules in sequence, providing a
transparent and extensible simulation workflow.

## Quick Start

Need FreeFEM++ built with MPI/PETSc first — see **[`INSTALL.md`](INSTALL.md)**
for the full step-by-step guide (WSL2-based; native Windows MPI is unreliable
for this solver).

After completing installation, launch a simulation from the `Src Codes` directory. The v1.1.0
defaults are `-flux_first 1 -v_picard 0 -conservative 2 -oh_fix 1` (see [Solver modes](#solver-modes));
the commands in this repository still give them explicitly so that the command line records the
formulation used:

```bash
cd "Src Codes"

mpirun -np 4 FreeFem++-mpi -nw dissolve.edp -v 0 \
  -input_mesh /path/to/mesh.mesh \
  -flux_first 1 -v_picard 0 -conservative 2 -oh_fix 1 \
  -dt_hours 4 -sim_duration 672 \
  -results_file output/result.txt
```

where:

- `-np 4` specifies the number of MPI processes.
- `-input_mesh` specifies the simulation mesh, which you generate with the tools in
  [`../Mesh Generation/`](../Mesh%20Generation/) (no meshes are distributed with the repository).
- `-sim_duration` specifies the degradation duration (hours).
- `-results_file` sets the output file; the output folder is taken from its directory.

Run from this folder (`Src Codes/`) so the relative `include` paths in `dissolve.edp` resolve
correctly. All parameters in `config/settings.idp` can be overridden from the command line
(see the [command-line reference](#command-line-reference)).

**Important: mesh paths must not contain spaces.** FreeFEM's `getARGV` truncates
`-input_mesh` (and any other string argument) at the first space in the path. Keep meshes
in a space-free directory.

## Solver modes

v1.1.0 is the frozen solver used for the revised study. All settings in `config/settings.idp`
can be overridden from the command line. The coupling between the oxygen sink and the
interface velocity is selected by three flags.

| Flag | Value | Meaning |
|---|---|---|
| `-flux_first` | `1` (default) | **Canonical v1.1.0 mode.** Oxygen is solved first; the flux removed by the interfacial sink gives the zinc oxidation flux, which is projected conservatively onto the interface to give the recession velocity. No probe and no Picard pass. Requires `-v_picard 0` and `-conservative 2`. |
| | `0` | Probe-based velocity (superseded, non-default; for reproducing earlier results). |
| `-v_picard` | `0` (default) | No semi-implicit passes (required with `-flux_first 1`). |
| | `N > 0` | N extra level-set and species solves per step with the velocity taken from the end-of-step oxygen (probe-based path only). |
| `-conservative` | `2` (default) | Velocity at the interface is the ORR velocity only; oxygen consumed, zinc released and metal lost are tied stoichiometrically; no zinc reservoir inside the solid. Required by `-film_mode 1` and `-flux_first 1`. |
| | `1` | Sources follow the actual recession velocity but the minimum-of-rates rule is kept, with a solubility cap (`-zn_sat`). Unstable; kept for reference. |
| | `0` | Legacy minimum of the zinc-, ORR- and oxygen-limited velocities, with sources not tied to the velocity. Superseded. |

The revised-manuscript mode is `-flux_first 1 -v_picard 0 -conservative 2`, with `-oh_fix 1`
(molar-consistent OH⁻ sources, default 1; `0` is the legacy, unit-inconsistent form). These are the
code defaults in `config/settings.idp`. The probe-based modes (`-flux_first 0`, `-conservative 0|1`)
are superseded, non-default options retained only for controlled reproduction of earlier results
(see [Legacy probe-based formulation](#legacy-probe-based-formulation-superseded)). OH⁻ and pH output
are not validated. [`THEORY.md`](THEORY.md) (Section 6) describes the flux-first formulation.

### Corrosion-product film

`-film_mode 1` (default) treats the film as an interface coverage `θ` with thickness
`θ L_f` (`-film_thickness`, `L_f`, default 0.001 mm), formed from a share of the zinc released
(`-k_f`) and dissolved by chloride (`-k_d`); `-kf_rate_units 1` and `-kd_mass_units 1` select
the unit conventions (`k_f` in h⁻¹, `k_d` in mm⁶ g⁻² h⁻¹). `-film_mode 0` keeps the volumetric
film field. The film reduces the ORR through a multiplier `κ(θ)` on `k_ORR`, selected by
`-film_mech`:

| `-film_mech` | Barrier on the ORR | Coverage |
|---|---|---|
| `0` (default) | Series resistance, `κ = 1 / (1 + k_ORR θ L_f / (D_O2 δ ε/τ))` (`-film_resistance 0` gives the older `1 − θ(1 − δε/τ)`) | `θ` limited to [0, 1] |
| `1` | Exponential electron-transfer barrier, `κ = exp(−β_eff θ L_f)`; `-film_beta` is β in µm⁻¹ (default 3.36) | uncapped retained product |
| `2` | Series resistance with the uncapped thickness `θ L_f` (no β term) | uncapped |

With `-film_beta_couple 1` the barrier exponent follows the film's tortuosity and porosity,
`β_eff = β (τ/ε) / (τ_ref/ε_ref)` (`-film_beta_tau_ref`, `-film_beta_eps_ref`; defaults 2 and
0.25), so β is the value at the reference film; the `τ/ε` dependence is an assumed scaling. The revised
study uses `-film_mech 1 -film_beta 12 -film_beta_couple 1` (`β_ref` = 12 µm⁻¹ at `ε` = 0.25, `τ` = 2,
`L_f` = 1 µm). `-film_porosity` (ε, 0.25), `-film_tortuosity`
(τ, 2) and `-film_constrictivity` (δ, 1) set the film transport properties. Values used for the
revised study are given in [Reference configuration](#reference-configuration-revised-study).

### Example

```bash
mpirun -np 50 FreeFem++-mpi -nw dissolve.edp -v 0 \
  -input_mesh path/to/your.mesh \
  -flux_first 1 -v_picard 0 -conservative 2 -oh_fix 1 \
  -film_mode 1 -kf_rate_units 1 -kd_mass_units 1 \
  -dt_hours 4 -sim_duration 672.0 -redistance_interval 24 \
  -checkpoint_each_time 24 \
  -results_file output/result.txt
```

The values of `-k_f`, `-k_d`, `-k_orr`, the diffusivities and the initial oxygen concentration in
`config/settings.idp` are command-line defaults, not the calibrated values of the revised study;
override them from the command line.

### Reference configuration (revised study)

The solver flags of the 3-D runs behind the revised manuscript (disc of Ø10 × 2 mm in a 30 × 30 × 30 mm
box, oxygen Dirichlet condition on the top face, no medium renewal), in addition to `-input_mesh`
and `-results_file`:

```bash
-flux_first 1 -v_picard 0 -conservative 2 -oh_fix 1 \
  -film_mode 1 -film_mech 1 -film_beta 12 -film_beta_couple 1 \
  -film_beta_tau_ref 2 -film_beta_eps_ref 0.25 -film_thickness 0.001 \
  -film_porosity 0.25 -film_tortuosity 2 -kf_rate_units 1 -kd_mass_units 1 \
  -k_orr 200 -k_f 4e5 -k_d 3e6 -o2_initial 6.2e-9 \
  -diff_o2 18.72 -diff_zn 3.384 -diff_cl 9.828 -diff_oh 25.56 \
  -dt_hours 4 -sim_duration 672 -redistance_interval 24 -tag_inlet 4
```

`-flux_proj_tol` keeps its default (1e-4). On coarse meshes the strong film barrier can exceed it
(for example `β` = 12 on a 3 900-vertex mesh); the run then stops with
`ERROR_FLUXFIRST_PROJECTION_BALANCE` and `-flux_proj_tol 1e-3` is needed (the flux is rescaled exactly
afterwards). The regression suite uses `-flux_proj_tol 1e-3` for its film-barrier runs for this reason.

Run `tests/run_tests.sbatch` to verify an installation (see [`VALIDATION.md`](VALIDATION.md)).
The change history is in [`../CHANGELOG.md`](../CHANGELOG.md).

[`VALIDATION.md`](VALIDATION.md) gives the verification results and the history of bug
fixes; [`THEORY.md`](THEORY.md) lists the governing equations.

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

Defaults are those in `config/settings.idp`, `io/write_results.idp`, `io/diskspace_guard.idp`
and `state/initial_state.idp`. Every setting can be overridden on the command line.

### Coupling and kinetics

| flag | default | meaning |
|---|---|---|
| `-flux_first` | 1 | `1` = flux-first coupling (v1.1.0); requires `-v_picard 0 -conservative 2`; `0` = superseded probe-based formulation |
| `-v_picard` | 0 | semi-implicit passes of the legacy path only; `0` required with `-flux_first 1` |
| `-conservative` | 2 | `0`, `1`, `2` (see [Solver modes](#solver-modes)) |
| `-flux_proj_tol` | 1e-4 | largest relative mismatch between the projected Zn flux and the oxygen sink before the exact rescaling; a larger mismatch stops the run (see the reference configuration) |
| `-oh_fix` | 1 | `1` = molar-consistent OH⁻ sources; `0` = legacy factors on mass-based fluxes |
| `-o2_molar_fix` | 1 | convert `C_O2` from g mm⁻³ to mol mm⁻³ in the velocity laws |
| `-k_f` | 3×10⁵ | film formation rate `k_f` (h⁻¹ with `-kf_rate_units 1`) |
| `-k_d` | 1×10⁸ | chloride-driven film degradation rate `k_d` (mm⁶ g⁻² h⁻¹ with `-kd_mass_units 1`) |
| `-k_orr` | 80 | ORR rate constant `k_ORR` (mm h⁻¹) |
| `-kf_rate_units`, `-kd_mass_units` | 1, 1 | unit conventions of `k_f` and `k_d` |
| `-o2_initial` | 3.5×10⁻⁹ | initial and Dirichlet O₂ (g mm⁻³; 3.5 mg L⁻¹) |
| `-diff_o2`, `-diff_zn`, `-diff_cl`, `-diff_oh` | 9.36, 2.7216, 7.776, 20.16 | diffusivities (mm² h⁻¹) |
| `-rho_zn`, `-rho_film` | 0.00714, 0.005606 | densities (g mm⁻³) |
| `-medium_reset_hours` | 0 | `H > 0` renews the electrolyte every H hours |

The values used for the revised study are given in the manuscript and Supporting
Information (see [`THEORY.md`](THEORY.md), Section 9, for the distinction between the code
defaults and the calibrated values).

### Corrosion-product film

| flag | default | meaning |
|---|---|---|
| `-film_mode` | 1 | `1` = interface coverage `θ`; `0` = volumetric film field `F` |
| `-film_mech` | 0 | barrier on the ORR: `0` series resistance, `1` exponential, `2` series resistance with uncapped thickness |
| `-film_thickness` | 0.001 | `L_f` (mm), film thickness at `θ = 1` |
| `-film_porosity`, `-film_tortuosity`, `-film_constrictivity` | 0.25, 2.0, 1.0 | `ε`, `τ`, `δ` |
| `-film_resistance` | 1 | `0` = older multiplier `1 − θ(1 − δε/τ)` for `-film_mech 0` |
| `-film_beta` | 3.36 | `β` (µm⁻¹), `-film_mech 1` only |
| `-film_beta_couple` | 0 | `1` = `β_eff = β (τ/ε) / (τ_ref/ε_ref)` |
| `-film_beta_tau_ref`, `-film_beta_eps_ref` | 2.0, 0.25 | reference `τ`, `ε` for the coupling |
| `-vol_film_units` | 0 | `1` = `F` stored as Zn-equivalent mass (volumetric mode) |

### Time stepping and reinitialisation

| flag | default | meaning |
|---|---|---|
| `-dt_hours` | 1.0 | time step (h) |
| `-sim_duration` | 672.0 | duration (h) |
| `-save_interval` | `dt` | hours between result rows |
| `-adaptive_dt` | 0 | `1` = grow `dt` while steps are quiet (`-time_step_max`, `-dt_growth_factor`, `-dt_stability_threshold`) |
| `-enable_redistance` | 1 | periodic volume-preserving level-set reinitialisation |
| `-redistance_interval` | 24.0 | hours between reinitialisations |
| `-redist_tol` | 1e-9 | relative tolerance of the volume correction |
| `-redist_max_corr` | 40 | maximum correction iterations |
| `-h_redist` | 0.05 | length scale (mm) of the volume correction |
| `-o2_relax_omega`, `-o2_relax_ref_dt`, `-o2_relax_scale_dt` | 1.0, 1.0, 0 | O₂ under-relaxation (`omega = 1` is no relaxation) |

### Mesh and domain

| flag | default | meaning |
|---|---|---|
| `-input_mesh` | `mesh/sphere.mesh` | mesh file (must not contain spaces) |
| `-tag_scaffold`, `-tag_medium`, `-tag_wall`, `-tag_inlet`, `-tag_outlet` | 1, 2, 3, 4, 5 | region and boundary tags; the O₂ Dirichlet condition is applied on `-tag_inlet` |
| `-adapt_mesh_runtime`, `-adapt_initial_mesh`, `-refine_threshold_pct` | 0, 0, 5.0 | adaptive remeshing |
| `-enable_flow` | 0 | optional flow field; **not validated** (see [`THEORY.md`](THEORY.md), Section 7) |

### Checkpoint, restart and disk guard

| flag | default | meaning |
|---|---|---|
| `-checkpoint_each_time` | 24.0 | hours between checkpoint writes (overwrites the previous one) |
| `-checkpoint_dir` | directory of `-results_file` | where checkpoints are written and read |
| `-restart_from <dir>` | unset | resume from a checkpoint; same mesh, `-np` and `-dt_hours` as the original run |
| `-min_disk_free_gb`, `-disk_guard_max_wait_min` | 20, −1 | pause before a write if the filesystem is nearly full (−1 waits indefinitely) |

### Output

| flag | default | meaning |
|---|---|---|
| `-results_file` | `output/result.txt` | cut-cell mass-loss table (time, percent); the folder also receives `mass_loss.txt`, `global_balance.tsv`, `o2_interface_diag.tsv`, `mechanism_data.txt` |
| `-emit_vtk`, `-vtk_prefix`, `-save_vtk_each_time` | 0, `output/output`, 168.0 | VTK snapshots; `-overwrite_vtk 1` allows reuse of a prefix |
| `-write_smooth_mass` | 0 | `1` also writes the smoothed-Heaviside `mass_loss_smooth.txt` (not invariant to reinitialisation; width `-vol_smooth_eps`, default 0.25 mm) |
| `-dump_final_state`, `-export_geometry` | 1, 0 | final-state dump; periodic geometry export |

## Legacy probe-based formulation (superseded)

These flags belong to the v1.0.x formulation, in which the interface velocity is evaluated from
the oxygen concentration at a probe point and `v = max(vZn, vO2)` (see
[`THEORY.md`](THEORY.md), Section 6). It is active with `-flux_first 0` (not the default) and is retained only for
controlled reproduction of earlier results; it is **not** the v1.1.0 formulation.

| flag | default | meaning |
|---|---|---|
| `-vel_extension` | 1 | `1` = probe relative to the interface rather than each node |
| `-search_method` | 1 | `1` = robust FreeFEM point location |
| `-h_interface` | 1e-6 | probe distance (mm); `-1` = mesh-derived value |
| `-v_picard`, `-v_picard_w` | 0, 1.0 | semi-implicit passes (`N > 0` only with `-flux_first 0`) and their oxygen weighting |
| `-delta_eps` | −1 | width of the regularised delta used for interface averages; `−1` = mesh `hmin` |
| `-use_vzn` | 1 | `0` = drop the Zn-transport branch from `v = max(vZn, vO2)` (diagnostic) |
| `-force_v` | 0 | force a uniform interface velocity (diagnostic) |
| `-legacy_vo2diff_sign` | 0 | `1` = restore the pre-fix (incorrect) `vO2Diff` sign, for A/B comparison only |
| `-debug_probe` | 0 | per-step probe diagnostics (adds cost) |
| `-stefan_alpha` | 0 | Stefan-condition coefficient |

## Not included here

Mesh binaries (`.mesh`/`.sol`), simulation output, and run logs are left out
of this source-only upload — they're large, environment-specific artifacts
rather than source code. Point `-input_mesh` at your own mesh, or regenerate
one, to run the solver.

## Calibration and Analysis Tools

The root-level [`../Scripts/`](../Scripts/) directory (a sibling of
`Src Codes/`, not a subfolder of it — see its own section in the main repo
README) contains workflows for parameter estimation, optimization, and
uncertainty analysis. All scripts drive `dissolve.edp` directly via subprocess
and share the same `local`/`m3` launcher toggle (`CALIB_LAUNCHER`, `CALIB_NP`,
`CALIB_SIF_PATH` env vars):

| Script | Purpose |
|---|---|
| `sensitivity_morris.py` | Global sensitivity screening using the Morris Elementary Effects method |

These tools interface directly with Dissolve™ and support automated evaluation of
degradation model parameters.

The Bayesian-optimization scripts in [`../Scripts/BO/`](../Scripts/BO/) are the provided tools for
recalibrating `k_f`, `k_d` and `k_ORR` against new data; see [`THEORY.md`](THEORY.md), Section 9.
The solver-driving scripts (`Scripts/GSA/sensitivity_morris.py`, `Scripts/GSA/run_gsa_full_v2.slurm`) give
`-flux_first 1 -v_picard 0 -conservative 2 -oh_fix 1` explicitly; the BO scripts do not launch the solver.

- **`sensitivity_morris.py`**: Morris (Elementary Effects) global sensitivity screening
  (r = 20 trajectories, 180 runs, mass loss at 168 h) over 8 parameters (`k_f`, `k_d`, `k_ORR`,
  `D_O2`, `C_O2,0`, `D_Zn`, `D_Cl`, `D_OH`; ranges in Supporting Information Table S4) via
  `SALib`, ranking each by its mean absolute effect (`μ*`). It also needs
  `../Scripts/requirements.txt`.

## Output and Visualization

Dissolve™ can export:

- VTK (`.vtu`, `.pvd`) visualization files
- Mass-loss histories
- Concentration fields
- Corrosion-product distributions
- Evolving degradation geometries
- Checkpoint files for restart operations

Simulation results can be visualized using ParaView.
