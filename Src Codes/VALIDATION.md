# Verification History and Current Status (v1.1.0)

This document records the verification activities for Dissolve™, the implementation
errors identified during development and review, their corrective actions, and the
current status of the solver. Version v1.1.0 is the frozen solver used for the revised
study.

## Current Status

```text
✓ Interface velocity derived from the oxygen flux removed at the interface (flux-first)
✓ Zn : O₂ ratio (molar 2 : 1) enforced by construction; checked within the regression tolerance
✓ Mass loss reported from the exact cut-cell volume, with a flux-integrated value alongside
✓ Level-set reinitialisation is volume-preserving (tolerance 1e-9)
✓ Inconsistent flags and projection imbalance stop the run
✓ Checkpoint/restart verified

⚠ OH⁻ / pH output is not validated
⚠ Calibrated parameters depend on mesh resolution and geometry
```

Calibration and validation against experimental data for the revised study are reported
in the manuscript and its Supporting Information. Numbers from earlier releases were
produced with the superseded probe-based formulation and should not be reused.

## Verification tests

The maintained regression suite is `tests/check.py`, run through `tests/run_tests.sbatch`
(see [`INSTALL.md`](INSTALL.md) for the local and Slurm commands). All checks fail closed.

Release candidate: the tested content is the solver source and tests of this repository
(`config/`, `physics/`, `state/`, `numerics/`, `io/`, `domain/`, `utils/`, `tests/` and
`dissolve.edp`, 21 files), exported from the git index with `git archive` before the release
commit was made. The sha256 of the sorted per-file sha256 listing is `aec39fe1dbe4b271c11627a937700ff3b2fb75159c94d94ee6ae869ae357595c`; the documentation
files are not part of the tested content.

**Environment.** Slurm job 62901421, 4 MPI ranks, 15 min 16 s. FreeFEM 4.12, PETSc 3.18.2, MPICH 4.0.2,
Ubuntu 22.04.1 container image `freefem.sif` (sha256
`14b627e77793ce0d3f615b072f65aec9368625b9609ce1e33f8fcbe255a10373`) run with Apptainer 1.5.1 and
`srun --mpi=pmi2` (full table in [`INSTALL.md`](INSTALL.md)).

**Meshes** (built by the study authors; not distributed): closed-box disc, sha256 `2479ec84ca978846b6912e279a926b79ae1b2a98aa9a1f91e85b6b0c1ca92dae`; open-top disc,
sha256 `7b7e2fde875e98eb288e7961f7c6c7abbc85fb9b7e4006bc9d7e90cd4521f129`; both 3 902 vertices and 21 407 tetrahedra (Ø10 × 2 mm disc in a 30 × 30 × 30 mm box).

**Command** (see [`INSTALL.md`](INSTALL.md), Step 8, for the local and Slurm forms):

```bash
cd "Src Codes"
export SOLVER_DIR=$PWD MESH=/path/to/closed_box_disc.mesh MESH_INLET=/path/to/open_top_disc.mesh
export FREEFEM_SIF=/path/to/freefem.sif FREEFEM_BIND=/path/to/shared/filesystem OUT_DIR=/path/to/shared/filesystem/tests_out
sbatch --account=<account> --export=ALL tests/run_tests.sbatch
```

The runs use `Δt` = 4 h and 168 h. All except the defaults-only run give `-flux_first 1 -v_picard 0
-conservative 2 -oh_fix 1` explicitly; the closed-box runs use `C_O2,0` = 3.5 mg/L; the open-top and
film-barrier runs use 6.2 mg/L with `k_ORR` = 200, `k_f` = 4×10⁵ and `k_d` = 3×10⁶. The defaults-only run
gives no coupling flags and must reproduce the explicit-flag closed-box run.

**Result: ALL PASS** (28 of 28 checks passed). Output of `tests/check.py`, which states each
tolerance and, for the projection checks, both the residual before and after the exact rescaling:

```text
PASS T1a version banner : dissolve.edp prints DISSOLVE_VERSION v1.1.0
PASS T1b Table 1 film values : tortuosity 2, porosity 0.25
PASS T1c Table 1 diffusivities : O2 9.36, Zn 2.7216, Cl 7.776, OH 20.16 mm2/h
PASS T1d flag guards in source : both flux-first flag guards present
PASS T1f code defaults select the flux-first formulation : defaults in settings.idp: -flux_first 1, -v_picard 0, -conservative 2, -oh_fix 1
PASS T1e Zn:O2 constants : 2 M_Zn / M_O2 = 4.0865
PASS T2a run completed : exit code 0 and v1.1.0 banner
PASS T2b Zn per supported O2 = 1 (|dev| < 2e-3, t >= 8 h) : min 1.00000 max 1.00000
PASS T2c mass loss <= 1.02 x oxygen cap : 0.0344 % vs cap 0.0351 % (ratio 0.978)
PASS T2d O2 sink <= 1.02 x initial inventory : 9.223e-05 g vs 9.396e-05 g (ratio 0.982)
PASS T3 cut-cell and flux-integrated mass loss agree within 5 % at the end : cut 0.0344 %, flux 0.0345 %, difference 0.35 %
PASS T4a reinitialisation ran : 7 calls
PASS T4b volume change per call < 1e-3 % : max |dV| = 9.92e-08 %
PASS T4c volume correction converged every call : no non-convergence warning
PASS T4d cumulative reinitialisation volume change < 1e-4 of the initial volume : cumulative -7.29e-07 mm3 (4.76e-09 of V0)
PASS T4e mass loss with reinitialisation within 10 % of without : on 0.0344 % vs off 0.0340 %
PASS T5 closed: projection residuals (pre < 1e-4, post < 1e-8) : 43 steps, max pre 8.40e-07, max post 5.71e-15
PASS T5 open_film: projection residuals (pre < 1e-4, post < 1e-8) : 43 steps, max pre 1.08e-05, max post 4.88e-15
PASS T6 guard_picard exits 2 with ERROR_FLUXFIRST_REQUIRES_V_PICARD_0 : exit code 2, message found
PASS T6 guard_cons exits 2 with ERROR_FLUXFIRST_REQUIRES_O2_AND_CONSERVATIVE_MODE_2 : exit code 2, message found
PASS T6 guard_proj exits 3 with ERROR_FLUXFIRST_PROJECTION_BALANCE : exit code 3, message found
PASS T7a Zn closure residual < 1 % of the zinc oxidised : residual -1.645e-05 g of 1.652e-03 g (-0.996 %)
PASS T7b open-top Zn per supported O2 = 1 (|dev| < 2e-3) : min 1.00000 max 1.00000
PASS T8 film_mech1_b0: Zn per supported O2 = 1 (|dev| < 2e-3) and projection residuals (pre < 1e-3, post < 1e-8) : Zn/O2 min 1.00000 max 1.00000, max pre 7.75e-15, max post 5.80e-16, mass loss 0.1526 %
PASS T8 film_mech1_b12: Zn per supported O2 = 1 (|dev| < 2e-3) and projection residuals (pre < 1e-3, post < 1e-8) : Zn/O2 min 1.00000 max 1.00000, max pre 2.81e-04, max post 4.79e-15, mass loss 0.1335 %
PASS T8 barrier lowers mass loss (beta 12 below 0.9 x beta 0) : 0.1335 % vs 0.1526 %
PASS T9a defaults-only run uses the flux-first path : exit code 0, 43 DEBUG_PROJ lines (flux-first projection active)
PASS T9b defaults-only run equals the explicit-flag run (relative difference < 1e-9) : mass loss 0.034364 % vs 0.034364 % (relative difference 0.0e+00)
ALL PASS
exit code 0
```

Notes:

- The Zn:O₂ check compares the zinc released with `(2 M_Zn / M_O2)` times the oxygen consumed, i.e. the
  molar 2:1 ratio; a value of 1 means exact stoichiometry.
- The zinc inventory closure residual (−0.996 % of the zinc oxidised) is close to its 1 % tolerance and is a
  known limit.
- The film-barrier runs use `-flux_proj_tol 1e-3`. With the default 1e-4 the `β` = 12 run on this coarse mesh
  stops at 8 h with `ERROR_FLUXFIRST_PROJECTION_BALANCE` (residual 1.2×10⁻⁴ before the exact rescaling). The
  default is unchanged.
- The tests use coarse disc meshes for 168 h. They do not exercise the stent geometry, 672 h runs, the flow
  module or the legacy probe-based path.

## Implementation errors corrected in v1.1.0

### 1. Mismatch between the interface velocity and the oxygen sink

**Status:** ✓ Fixed
**Components:** `physics/flux_first.idp`, `physics/interface_velocity.idp`, `dissolve.edp`

The recession velocity was evaluated from the oxygen concentration at a probe point in the
medium, taken from the start-of-step field, whereas oxygen consumption was imposed as a
separate surface integral applied during the step. The velocity therefore saw more oxygen
than the sink removed (spatial mismatch) and lagged the oxygen depletion (temporal lag).
Zinc removal could therefore be inconsistent with the integrated oxygen supply, and in a closed
box the predicted mass loss could exceed the oxygen-limited maximum.

**Resolution:** with `-flux_first 1` oxygen is solved first, the flux removed by the sink
gives the zinc oxidation flux, and this flux is projected conservatively onto the interface
to give the velocity. No probe and no Picard iteration are used.

### 2. Reinitialisation volume change and mass-loss reporting

**Status:** ✓ Fixed
**Components:** `numerics/timestep_solver.idp`, `io/write_results.idp`

The level-set reinitialisation left a volume change (tolerance 1e-6), and the smoothed-
Heaviside mass-loss file was not invariant to reinitialisation. Reinitialisation now applies
a volume-preserving shift (tolerance 1e-9, default interval 24 h, `-redistance_interval`),
the film inventory is remapped with the interface, and mass loss is reported from the exact
cut-cell volume (`mass_loss.txt`) together with the flux-integrated value.

### 3. Film bookkeeping and tallies

**Status:** ✓ Fixed
**Components:** `physics/governing_equations.idp`, `physics/flux_first.idp`

The retained film appeared in the Zn and film equations with slightly different terms, and
the retained share was not bounded. The same terms are now used in both equations, the
retained share is capped at 1, and the oxygen and zinc tallies are accumulated on the
current interface before it moves.

### 4. Output and run guards

**Status:** ✓ Added
**Components:** `io/write_results.idp`, `dissolve.edp`, `physics/flux_first.idp`

New outputs: `global_balance.tsv` (oxygen inventory, sink and boundary supply; zinc
dissolved, retained, removed and oxidised; closure residual), `mass_loss.txt`, and
`o2_interface_diag.tsv`. The solver exits on inconsistent flag combinations and when the
projected zinc flux does not match the oxygen sink.

## Earlier corrections (retained)

- Oxygen-limited velocity sign error corrected; velocity quantities stored as spatially
  varying fields; Stefan velocity units made consistent (zinc mass density).
- Mass-lumped level-set transport; oxygen under-relaxation scaled with the time step.
- Legacy probe-based path only (superseded, see `README.md`): probe distance configurable through
  `-h_interface`; optional `-vel_extension 1` and `-search_method 1`.
- Checkpoint and restart (`-checkpoint_each_time`, `-restart_from`): restarted runs match
  uninterrupted reference runs to 0.004 % relative error.

## Parameters

The code defaults, the revised-study calibrated values, their search ranges and the unit-converted
values are tabulated in [`THEORY.md`](THEORY.md), Section 9; the flags are listed in the
[command-line reference](README.md#command-line-reference). The defaults in `config/settings.idp`
are not the calibrated values. The v1.1.0 defaults are `-flux_first 1 -v_picard 0 -conservative 2 -oh_fix 1`;
`-flux_first 1` requires `-v_picard 0` and `-conservative 2`. The full solver command of the revised
study is in [`README.md`](README.md#reference-configuration-revised-study).

### Parameter interpretation

| Parameter | Primary Effect |
|---|---|
| `k_ORR` | Strongest control: initial degradation rate and overall magnitude; high values deepen O₂ depletion and deceleration |
| `k_f` | Higher values grow the film faster and reduce mass loss |
| `k_d` | Higher values dissolve the film faster, lowering coverage and raising mass loss |

## Mesh dependency

**Status:** ⚠ Important limitation

Calibrated parameters depend on mesh resolution. Treat transfer to other meshes or
geometries as something to verify, not assume. For any new geometry: perform a mesh
convergence analysis, recalibrate if necessary, and verify trends against experiments.

## Ongoing limitations

- OH⁻ / pH output is not validated.
- Calibration parameters remain mesh-dependent.
- The HBSS comparison used in the revised study is a fit check: the HBSS data are part of the calibration objective.
- Flow-coupled degradation simulations have not undergone systematic experimental validation.

## Consistency with the manuscript and Supporting Information

Items to keep identical in the manuscript, the Supporting Information (SI) and this repository.

| Item | Repository (v1.1.0) | Check against the SI and manuscript |
|---|---|---|
| Interface Damköhler number | `Da = C_b / ⟨C_Γ⟩ − 1`, `C_b` = `-o2_initial`; crosses 1 at 158.5 h in the 3-D validation run ([`THEORY.md`](THEORY.md), Section 6) | SI Eq. S3 as written (`v_max / \|v_n\| − 1`, no film factor) is a different quantity: with a film-free `v_max` it never crosses 1 in that run. Rewrite Eq. S3 as `C_b / C_Γ − 1`, or use `v_max(θ)` with the film factor, and state `C_b` |
| Robin oxygen sink | `k_ORR κ(θ) C_O2` with the film barrier `κ(θ)` on the ORR | SI oxygen Robin condition and Eq. 7 carry no `κ`; add it |
| Film barrier | `-film_mech 1`, `κ = exp(−β_eff θ L_f)`, `β_ref` = 12 µm⁻¹ at `ε` = 0.25, `τ` = 2 (`-film_beta_couple 1`), `L_f` = 1 µm | State `β_ref`, the `τ/ε` scaling (assumed) and that `β_ref` is fixed, not calibrated |
| Calibrated kinetics | `k_f` 4×10⁵ h⁻¹, `k_d` 3×10⁶ mm⁶ g⁻² h⁻¹, `k_ORR` 200 mm h⁻¹ | Table 2; `k_d` is bounded from above only |
| Search ranges | `k_f` [1×10⁵, 2.5×10⁶], `k_d` [1×10⁴, 1×10⁸], `k_ORR` [25, 2500] | Table S4 and the Bayesian-optimization table |
| Material and numerical inputs | `C_O2,0` 6.2 mg L⁻¹; `D_O2` 18.72, `D_Zn` 3.384, `D_Cl` 9.828, `D_OH` 25.56 mm² h⁻¹; `Δt` 4 h; 672 h | Table 1 and Table S4 (these differ from the code defaults) |
| Reinitialisation | volume-preserving, every 24 h, tolerance 1e-9 | Table S4 interval (v1.0.x used 1 h) |
| HBSS comparison | calibration fit check: the HBSS data are in the objective | do not describe it as independent validation |
| Zn closure | −0.996 % in the coarse regression test; −0.56 % in the 3-D confirmation run | Methods and the mass-balance table |
| Software | FreeFEM 4.12, PETSc 3.18.2, MPICH 4.0.2 | Methods; not FreeFEM 4.14 |
| Stoichiometry | molar Zn : O₂ = 2 : 1; mass ratio `2 M_Zn / M_O2` ≈ 4.09 | state the basis |
