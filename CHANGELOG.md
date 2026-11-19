# Changelog

## v1.1.0

Frozen solver implementation used for the revised study. This release substantially revises
the interface–oxygen coupling and mass-accounting formulation; results obtained with v1.0.x
are not expected to be reproduced by v1.1.0. The v1.0.1 release is unchanged.

The revised-manuscript mode is `-flux_first 1 -v_picard 0 -conservative 2` (with `-oh_fix 1`); these are
now the code defaults. The `-conservative`
modes and the other coupling flags are defined in [Solver modes](Src%20Codes/README.md#solver-modes).

### Errors corrected

- **Inconsistent coupling between interface velocity and oxygen consumption.** In the previous
  implementation, recession velocity was calculated using a probe-point oxygen concentration
  from the beginning of the time step, whereas oxygen consumption was evaluated separately
  during the step. This could produce Zn removal inconsistent with the integrated oxygen supply.
- **Reinitialization-related volume change and mass-loss reporting.** The previous smoothed
  mass-loss output was not invariant to level-set reinitialization, which could also introduce
  a change in reconstructed solid volume.

### Major changes

- Used a flux-first update in which the oxygen sink and interface velocity are derived from the
  same interfacial oxygen flux. The Zn:O₂ stoichiometric ratio is 2:1 on a molar basis (mass ratio 2 M_Zn / M_O₂ ≈ 4.09);
  it is enforced by construction and checked within the regression tolerance.
- Calculated geometric mass loss from the cut-cell solid volume and retained flux-integrated mass
  loss as an independent conservation diagnostic.
- Added volume-preserving level-set reinitialization, with film inventory remapped consistently
  with interface motion.
- Added global mass-balance, mass-loss, and interface-oxygen diagnostic outputs
  (`global_balance.tsv`, `mass_loss.txt`, `o2_interface_diag.tsv`).
- Added run-time safeguards for inconsistent solver options and projection imbalance.
- Retained the previous probe-based and conservative modes (`-flux_first 0`, `-conservative 0|1`)
  only as superseded, non-default options for controlled reproduction of earlier results.
- Changed code defaults: `-flux_first 1` (was 0), `-v_picard 0` (was 2) and `-oh_fix 1` (was 0), so that a
  default run uses the flux-first formulation and molar-consistent OH⁻ sources.
- Added `.gitattributes` so that shell, Python and FreeFEM sources and Markdown keep Unix line endings.
- Updated the regression suite (`Src Codes/tests/`) and aligned the documentation with the revised
  manuscript and Supporting Information.

### Known limitations

- OH⁻ / pH output is not validated.
- Calibrated parameters depend on mesh resolution and geometry.
