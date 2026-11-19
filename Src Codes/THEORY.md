# Theoretical Background

## Overview

Dissolve™ is a three-dimensional multiphysics degradation simulator for biodegradable
metallic implants based on a coupled reaction-diffusion-moving-boundary formulation.
The solver combines electrochemical degradation kinetics, ionic transport,
corrosion-product film evolution, and interface tracking within a finite-element
framework to predict degradation kinetics, mass loss, and morphology evolution of
zinc-based biodegradable implants.

The mathematical and numerical framework is implemented primarily in:

```text
physics/governing_equations.idp
physics/flux_first.idp
physics/interface_kinetics.idp
physics/interface_velocity.idp   (legacy probe-based formulation)
```

with supporting numerical infrastructure contained in:

```text
numerics/
domain/
state/
```

The current implementation models oxygen-reduction-reaction (ORR) controlled
degradation of zinc in physiological environments through the interaction of:

- Metal dissolution kinetics
- Oxygen reduction reaction (ORR)
- Multi-species ionic transport
- Corrosion-product film formation and degradation
- Moving interface evolution
- Finite-element discretization
- Adaptive remeshing

Together these processes govern the spatial and temporal evolution of scaffold
degradation.

## Model Architecture

The Dissolve™ framework can be viewed as five coupled physical subsystems:

```text
 Oxygen Transport
        │
        ▼
 ORR Kinetics ───► Interface Velocity
        │
        ▼
 Level-Set Evolution
        │
        ▼
 Geometry and Morphology Change
        ▲
        │
 Zn2+, Cl-, OH- Transport
        ▲
        │
 Corrosion Product Film
```

At each timestep the solver (v1.1.0 flux-first mode, Section 6):

1. Solves oxygen transport on the current interface with the implicit ORR sink.
2. Projects the oxygen flux removed by the sink to the interface recession velocity and
   verifies the flux balance.
3. Updates the corrosion-product film state and accumulates the oxygen and zinc tallies
   on the current interface.
4. Advances the level-set interface (reinitialising at the set interval) and solves the
   Zn²⁺, Cl⁻ and OH⁻ equations.
5. Optionally solves the flow field and adapts the mesh.
6. Exports simulation results.

## 1. Moving-Boundary Degradation Problem

Dissolve™ treats biodegradation as a moving-boundary problem in which the scaffold
geometry evolves continuously as material is removed from the surface.

### Computational Domains

```text
Ωs   : Metallic scaffold
Ωf   : Physiological fluid
Γ(t) : Time-dependent scaffold-fluid interface
```

### Physical Processes

```text
Zn Dissolution
      ↓
Species Transport
      ↓
Film Formation / Breakdown
      ↓
Interface Recession
      ↓
Geometry Evolution
```

### Model Behaviour

During each timestep, the solver:

1. Computes species transport within the fluid domain.
2. Evaluates surface reaction kinetics at the scaffold interface.
3. Updates corrosion-product film formation and degradation.
4. Calculates the local interface recession rate.
5. Advances the scaffold-fluid boundary.
6. Updates the scaffold geometry for the next timestep.

### Key Characteristics

- Geometry changes throughout the simulation.
- Surface area evolves as degradation progresses.
- Local transport conditions influence degradation rates.
- Corrosion behaviour and geometry evolution are fully coupled.
- Non-uniform degradation patterns emerge naturally from local reaction and transport
  conditions.

### Model Outputs

The moving-boundary formulation enables prediction of:

- Mass loss
- Volume loss
- Surface recession
- Degradation morphology
- Evolution of porous scaffold architectures
- Time-dependent geometry changes

### Mathematical Framework

The degradation problem belongs to the class of Stefan-type moving-boundary problems,
in which interface motion is governed by coupled transport and reaction processes
occurring at the interface.

### References

1. Crank, J. *Free and Moving Boundary Problems.* Oxford University Press, 1984.
2. Alexiades, V., & Solomon, A. D. *Mathematical Modeling of Melting and Freezing
   Processes.* Hemisphere Publishing, 1993.
3. Rubinstein, L. I. *The Stefan Problem.* American Mathematical Society, 1971.

## 2. Level-Set Interface Tracking

Dissolve™ tracks degradation using the level-set method, in which the scaffold
surface is represented implicitly by a scalar field rather than an explicit moving
surface mesh.

### Interface Representation

```text
φ > 0 : Scaffold domain
φ = 0 : Scaffold-fluid interface
φ < 0 : Fluid domain
```

The scaffold surface is therefore defined by the zero contour of the level-set field.

### Interface Evolution

```text
Interface Velocity
        ↓
Level-Set Update
        ↓
Surface Movement
        ↓
Geometry Evolution
```

At each timestep, the local degradation velocity is used to advance the level-set
field, causing the scaffold boundary to move according to the predicted corrosion
rate.

### Why Level Sets?

Biodegradable implants often contain complex geometries that evolve during
degradation. Examples include:

- Thinning scaffold struts
- Expanding pore networks
- Surface merging
- Loss of structural connectivity
- Disappearance of small features

The level-set method captures these changes automatically without requiring
reconstruction of a moving surface mesh.

### Key Characteristics

- Implicit representation of the scaffold surface
- Naturally handles complex topology changes
- Suitable for TPMS and lattice architectures
- Compatible with adaptive remeshing
- Robust for large geometry changes
- MPI-parallel implementation

### Reinitialization

Accurate interface tracking requires the level-set field to remain close to a
signed-distance function. Dissolve™ periodically performs level-set reinitialization
(`-enable_redistance 1`, default; interval `-redistance_interval`, **default 24 h**) to:

- Maintain stable interface normals
- Improve curvature estimation
- Preserve numerical accuracy near the boundary
- Support robust interface-velocity calculations

In v1.1.0 the reinitialization is volume-preserving: after the signed-distance
recomputation the zero level set is shifted until the cut-cell solid volume matches its value
before reinitialization (relative tolerance `-redist_tol`, default 1×10⁻⁹, at most
`-redist_max_corr` iterations; the correction length scale is `-h_redist`). The cumulative
reinitialization volume change is tallied in `mass_loss.txt` (`ReinitDVCum_mm3`), a
non-convergent correction prints `WARNING_REDIST_CORRECTION_NOT_CONVERGED`, and the film
inventory carried by the interface is remapped consistently with the interface
(film mode 1). The v1.0.x releases reinitialized every 1 h without volume preservation; the
v1.1.0 default interval is 24 h, which is the value used for the revised study.

### Model Outputs

The level-set framework provides:

- Evolving scaffold geometry
- Surface recession maps
- Local degradation velocities
- Time-dependent degradation morphology
- Updated domains for transport and reaction calculations

### Implementation

```text
physics/interface_velocity.idp
physics/interface_kinetics.idp
physics/governing_equations.idp
numerics/timestep_solver.idp
```

### References

1. Osher, S., & Sethian, J. A. "Fronts Propagating with Curvature-Dependent Speed:
   Algorithms Based on Hamilton-Jacobi Formulations." *Journal of Computational
   Physics*, 1988.
2. Sethian, J. A. *Level Set Methods and Fast Marching Methods.* Cambridge University
   Press, 1999.
3. Osher, S., & Fedkiw, R. *Level Set Methods and Dynamic Implicit Surfaces.*
   Springer, 2003.

## 3. Multi-Species Transport

Dissolve™ models degradation as a coupled transport problem involving dissolved
chemical species and a corrosion-product film field that interact through diffusion,
surface reactions, and interface evolution.

### Fields Included

```text
Zn²⁺ : Dissolved zinc ions
Cl⁻  : Chloride ions
OH⁻  : Hydroxide ions
O₂   : Dissolved oxygen
F    : Corrosion-product film
```

Each field evolves continuously throughout the simulation and contributes to the
overall degradation behaviour.

### Governing Equations

Transport is a reaction-diffusion system (Nernst-Planck without electromigration
or convection under static immersion), with film-modified effective diffusivity.
`Γ` is the moving Zn-electrolyte interface (`δΓ` its surface delta function). In molar
form (concentrations `C_i` in mol L⁻¹):

```text
∂C_O2/∂t = ∇·(D_O2^eff ∇C_O2) − k_ORR κ(θ) C_O2 δΓ                    (7)
∂C_Cl/∂t = ∇·(D_Cl^eff ∇C_Cl)                                          (8)
∂C_Zn/∂t = ∇·(D_Zn^eff ∇C_Zn) + 2 k_ORR κ(θ) C_O2 δΓ − (film exchange)  (9)
∂C_OH/∂t = ∇·(D_OH^eff ∇C_OH) + 4 k_ORR κ(θ) C_O2 δΓ − 2 (film exchange) (10)
D_i^eff  = D_i^0 [ (1 − F/Fmax) + (F/Fmax) δ ε/τ ]                      (12)
```

The film exchange is the Zn²⁺ removed by precipitation minus the film dissolved
(Section 4). The stoichiometric factors 2 and 4 are **molar**: each mole of O₂ consumed
(O₂ + 2H₂O + 4e⁻ → 4OH⁻, paired with 2Zn → 2Zn²⁺ + 4e⁻) releases 2 mol of Zn²⁺ and
4 mol of OH⁻.

**Units as implemented** (`physics/governing_equations.idp`, `config/settings.idp`):

| Quantity | Unit in the code | Relation |
|---|---|---|
| `C_O2`, `C_Zn`, `C_Cl`, `F` | g mm⁻³ (mass-based) | molar `C = C_mass / M_i`; `M_O2` = 31.998, `M_Zn` = 65.38, `M_Cl` = 35.45 g mol⁻¹ |
| `C_OH` | mol L⁻¹ | `pH = 14 + log10 C_OH` |
| `k_ORR` | mm h⁻¹ | first-order surface rate constant |
| Oxygen flux `J_O2 = k_ORR κ C_O2\|Γ` | g mm⁻² h⁻¹ | removed at the interface by the Robin sink |
| Zn²⁺ interface source | g mm⁻² h⁻¹ | `ρ_Zn \|v\| = (2 M_Zn / M_O2) J_O2` |
| OH⁻ interface source (`-oh_fix 1`) | mol L⁻¹ mm h⁻¹ | `(4×10⁶ / M_O2) J_O2` (`10⁶` converts mm³ to L) |
| `k_d` | mm⁶ g⁻² h⁻¹ | with `C_Cl` in g mm⁻³; in molar form `k_d' = k_d / clMolarConv²`, `clMolarConv = 10⁶ / M_Cl ≈ 28 209` (mol L⁻¹) per (g mm⁻³) |

Because the species are mass-based, the molar stoichiometric factors become mass factors
in the Zn²⁺ equation: the mass of zinc oxidised per unit mass of oxygen consumed is
`2 M_Zn / M_O2 ≈ 4.09`. In the v1.1.0 mode (`-conservative 2`) the Zn²⁺ source is built from
the recession velocity, `ρ_Zn |v|`, which is tied to `J_O2` by this factor, so the units are
consistent. The legacy `-conservative 0` Zn²⁺ source and the legacy `-oh_fix 0` OH⁻ sources
apply the molar factors 2 and 4 directly to mass-based quantities and are **not**
unit-consistent. The v1.1.0 default is `-oh_fix 1`, which gives the molar-consistent OH⁻ sources
shown above. OH⁻ and pH output are not validated.

Notes on the implementation:

- The ORR sink, the Zn²⁺ source and the OH⁻ source are `int2d(..., levelset=phi)` interface
  integrals.
- `Fmax` is the film capacity `ρ_film (1 − ε)` (Section 4).
- Film formation consumes Zn²⁺ and OH⁻; chloride-driven dissolution returns them.
  Cl⁻ is catalytic and is not consumed.
- With `-conservative 2` the Zn²⁺ field has no reservoir inside the solid: it is not pinned
  inside `φ > 0` and its diffusion is masked to the electrolyte. The pinning to `[Zn]_sat`
  by a penalty term belongs to the legacy `-conservative 0` mode.

### Field Interactions

```text
O₂ Transport ──┐
               ▼
          ORR Kinetics
               ▼
          Zn Dissolution
               ▼
          Film Formation
               ▼
       Modified Transport
               ▼
        Interface Motion
```

### Field Roles

**Zinc Ions (Zn²⁺)** — generated by metal dissolution:

- Produced at the scaffold surface during corrosion.
- Diffuse into the surrounding electrolyte.
- Represent the primary anodic degradation product.
- Contribute to local interface recession rates.

**Dissolved Oxygen (O₂)** — consumed by oxygen reduction:

- Primary cathodic reactant.
- Controls ORR-driven degradation kinetics.
- Can become transport-limited in poorly accessible regions.
- Strongly influences local degradation rates.

**Hydroxide Ions (OH⁻)** — generated by oxygen reduction:

- Produced during cathodic reactions.
- Alters local chemical conditions.
- Contributes to corrosion-product formation.
- Affects the near-surface environment.

**Chloride Ions (Cl⁻)** — present in physiological fluids:

- Diffuse throughout the electrolyte.
- Promote corrosion-product breakdown.
- Influence film stability.
- Affect long-term degradation behaviour.

**Corrosion-Product Film (F)** — forms and degrades on the scaffold surface:

- Represents accumulated corrosion products.
- Grows through precipitation and surface reactions.
- Degrades through chloride-mediated film breakdown.
- Introduces transport resistance between the metal and surrounding fluid.
- Couples degradation kinetics with species transport.

### Film-Transport Coupling

```text
Film Growth
      ↓
Reduced Transport
      ↓
Lower O₂ Availability
      ↓
Modified ORR Rate
      ↓
Modified Degradation Rate
```

The corrosion-product film acts as a dynamic transport barrier. As film coverage
increases, the effective diffusivity of Zn²⁺, Cl⁻, OH⁻, and O₂ is reduced, increasing
transport resistance near the scaffold surface. This enables the model to capture:

- Surface passivation
- Diffusion-limited degradation
- Film formation and breakdown cycles
- Spatially heterogeneous corrosion behaviour

### Key Characteristics

- Four dissolved species fields and one film field.
- Fully coupled reaction-diffusion formulation.
- Film-modified transport properties.
- ORR-controlled degradation kinetics.
- Transport-limited and reaction-limited regimes.
- Spatially varying degradation behaviour.

### Model Outputs

The transport framework provides:

- Zn²⁺ concentration fields
- Cl⁻ concentration fields
- OH⁻ concentration fields
- O₂ concentration fields
- Corrosion-product film distributions
- Species fluxes
- Effective transport properties
- Local transport limitations

### Implementation

```text
physics/governing_equations.idp
physics/interface_velocity.idp
state/fields.idp
```

### References

1. Crank, J. *The Mathematics of Diffusion.* Oxford University Press, 1975.
2. Cussler, E. L. *Diffusion: Mass Transfer in Fluid Systems.* Cambridge University
   Press, 2009.
3. Jones, D. A. *Principles and Prevention of Corrosion.* Prentice Hall, 1996.
4. Marcus, P. *Corrosion Mechanisms in Theory and Practice.* CRC Press, 2011.

## 4. Corrosion-Product Film Model

The corrosion-product film is represented as a dynamic field that forms on the
scaffold surface during degradation and evolves throughout the simulation. Rather
than explicitly modelling individual corrosion-product phases, Dissolve™ uses a
lumped film variable (`F`) to capture their combined influence on degradation
behaviour and species transport.

### Film variables and definitions

| Symbol | Meaning | Unit | Definition / relation |
|---|---|---|---|
| `F` | volumetric film field (`-film_mode 0`) | g mm⁻³ | stored as Zn-equivalent mass with `-vol_film_units 1` |
| `Fmax` | film capacity | g mm⁻³ | `ρ_film (1 − ε)`, `ρ_film` = 5.606×10⁻³ g mm⁻³, `ε` = 0.25; times `M_Zn / M_film` with `-vol_film_units 1` (`M_film` = 81.38 g mol⁻¹) |
| `F / Fmax` | film saturation | – | enters the effective diffusivity (Eq. 12), clipped to [0, 1] |
| `θ` | interface film state (`-film_mode 1`) | – | `θ = L / L_f`; in [0, 1] for `-film_mech 0`, uncapped for `-film_mech 1, 2` |
| `L_f` | film thickness at `θ = 1` | mm | `-film_thickness`, default 0.001 mm |
| `L` | film thickness | mm | `L = θ L_f` |
| `m_f` | film inventory per unit area at `θ = 1` | g Zn mm⁻² | `ρ_film (1 − ε) L_f M_Zn / M_film`; inventory = `θ m_f` |
| `κ(θ)` | multiplier of `k_ORR` | – | film barrier on the ORR, below |

In film mode 1 the figures plot `F/Fmax` as `θ`: the output `Film_Interface` equals
`θ Fmax`, so `Film_Interface / Fmax = θ = L / L_f`.

**Film mode 1 evolution.** With the retained share `s = min(1, k_f L_f² / D_Zn)`
(`-kf_rate_units 1`, `k_f` in h⁻¹):

```text
dθ/dt = s ρ_Zn |v| (1 − θ)^[film_mech 0] / m_f  −  k_d C_Cl² θ
Zn²⁺ source = ρ_Zn |v| − m_f dθ/dt
```

The factor `(1 − θ)` applies to `-film_mech 0` only; `-film_mech 1, 2` use the uncapped
formation term. Zinc is conserved: precipitated zinc leaves the Zn²⁺ source and dissolved
film returns to it.

**Barrier `κ(θ)`** (with `D_f = D_O2 δ ε / τ`):

```text
film_mech 0:  κ = 1 / (1 + k_ORR θ L_f / D_f)          (series resistance, -film_resistance 1)
film_mech 1:  κ = exp(−β_eff θ L_f)                     (L_f in µm, β_eff in µm⁻¹)
film_mech 2:  κ = 1 / (1 + k_ORR θ L_f / D_f)          (uncapped θ)
```

with `β_eff = β (τ/ε) / (τ_ref/ε_ref)` when `-film_beta_couple 1`, and `β_eff = β` otherwise.
The revised study uses `-film_mech 1 -film_beta 12 -film_beta_couple 1` with `τ_ref` = 2, `ε_ref` = 0.25,
so `β_ref` = 12 µm⁻¹ at the reference film (`ε` = 0.25, `τ` = 2) and `L_f` = 1 µm. The `τ/ε` dependence of
the exponent is an assumed scaling, not a fitted one, and `β_ref` is fixed, not calibrated.

### Film Evolution

```text
Metal Dissolution
      ↓
Film Formation
      ↓
Transport Resistance
      ↓
Reduced Species Fluxes
      ↓
Modified Degradation Rate
```

The film is continuously updated as degradation proceeds and acts as the primary
coupling mechanism between surface chemistry and mass transport.

### Physical Representation

The film field represents the accumulation of corrosion products commonly observed on
degrading zinc implants, including:

```text
Zinc Oxides
Zinc Hydroxides
Basic Zinc Salts
Mixed Physiological Corrosion Products
```

Rather than tracking each phase separately, the model combines their overall effect
into a single variable that evolves with time and location.

### Film Formation

```text
Zn Dissolution
      ↓
Corrosion Product Generation
      ↓
Film Growth
```

Film formation is controlled by the film-formation rate parameter `k_f`. Higher
formation rates lead to faster surface coverage and increased transport resistance
around the degrading scaffold.

### Film Degradation

```text
Chloride Exposure
      ↓
Film Destabilization
      ↓
Film Breakdown
```

Film degradation is controlled by `k_d` (mm⁶ g⁻² h⁻¹, with `C_Cl` in g mm⁻³), which governs the
chloride-mediated removal of corrosion products and the reopening of transport
pathways to the scaffold surface.

### Transport Coupling

The film directly modifies the effective transport properties of all dissolved
species (Zn²⁺, Cl⁻, OH⁻, O₂). As film thickness increases:

- Oxygen transport becomes more restricted.
- Zinc diffusion away from the surface decreases.
- Chloride penetration is hindered.
- Hydroxide transport slows.

This introduces local transport limitations that can significantly alter degradation
kinetics.

### Model Behaviour

```text
Thin Film → High Transport → Rapid Corrosion

Thick Film → Transport Limitation → Reduced Corrosion
```

The competition between film formation and film breakdown determines whether
degradation remains reaction-controlled or becomes transport-controlled.

### Key Characteristics

- Dynamic corrosion-product accumulation.
- Chloride-mediated film degradation.
- Transport-dependent passivation effects.
- Fully coupled to species transport.
- Fully coupled to interface evolution.
- Spatially varying film distribution.
- Supports localized degradation behaviour.

### Model Outputs

The film model provides:

- Corrosion-product film distribution.
- Film growth and degradation history.
- Effective diffusivity fields.
- Local transport resistance.
- Surface passivation behaviour.
- Film-controlled degradation regions.

### Implementation

```text
physics/governing_equations.idp
physics/interface_velocity.idp
state/fields.idp
```

### References

1. Wagner, C. "Beitrag zur Theorie des Anlaufvorgangs." *Zeitschrift für Physikalische
   Chemie*, 1933.
2. Jones, D. A. *Principles and Prevention of Corrosion.* Prentice Hall, 1996.
3. Marcus, P. *Corrosion Mechanisms in Theory and Practice.* CRC Press, 2011.
4. Revie, R. W. *Uhlig's Corrosion Handbook.* Wiley, 2011.

## 5. Electrochemical Degradation Kinetics

Electrochemical reactions provide the driving force for scaffold degradation.
Dissolve™ models corrosion using a coupled anodic-cathodic framework in which zinc
dissolution and oxygen reduction occur simultaneously at the scaffold surface. The
competition between these reactions, together with local transport conditions and
film resistance, determines the degradation rate at every point on the implant
surface.

### Electrochemical System

```text
Anodic Reaction
      +
Cathodic Reaction
      ↓
Surface Corrosion
      ↓
Interface Recession
```

Both reactions must occur simultaneously to maintain charge balance during
degradation.

### Anodic Dissolution

```text
Zn → Zn²⁺ + 2e⁻
```

The anodic reaction represents the loss of metallic zinc from the scaffold surface.
Its effects include:

- Production of dissolved zinc ions.
- Reduction of scaffold mass.
- Recession of the metal surface.
- Generation of corrosion products.

The dissolution process supplies the material removal mechanism that drives geometry
evolution.

### Cathodic Oxygen Reduction Reaction (ORR)

```text
O₂ + 2H₂O + 4e⁻ → 4OH⁻
```

The oxygen reduction reaction (ORR) is the primary cathodic reaction included in
Dissolve™. Its effects include:

- Consumption of dissolved oxygen.
- Production of hydroxide ions.
- Control of local corrosion activity.
- Coupling of oxygen transport with degradation kinetics.

Because oxygen must diffuse through the electrolyte and any corrosion-product film
before reaching the interface, ORR can become transport limited in regions with
restricted oxygen access.

### ORR Control Parameter

The cathodic reaction rate is governed by `k_ORR` (mm/h), which controls the intensity of
oxygen reduction at the scaffold surface. Increasing `k_ORR` generally leads to:

```text
Faster Oxygen Consumption
        ↓
Higher Corrosion Rates
        ↓
Greater Surface Recession
```

provided sufficient oxygen remains available.

### Competing Kinetic Regimes

Corrosion behaviour may operate in two limiting regimes:

**Reaction-Controlled** (fast transport + slow surface reactions) — reactants are
readily available and degradation is controlled primarily by reaction kinetics.

**Transport-Controlled** (slow transport + fast surface reactions) — oxygen delivery
and species transport become limiting, restricting the degradation rate even when
reaction kinetics are favourable.

### Coupling with Transport

```text
O₂ Transport
      ↓
ORR Kinetics
      ↓
OH⁻ Production
      ↓
Film Evolution
      ↓
Modified Transport
```

The electrochemical model is therefore tightly coupled with the transport and film
models. Changes in oxygen concentration, zinc concentration, chloride concentration,
hydroxide concentration, and film coverage all influence local degradation rates.

### Coupling with Interface Motion

```text
Electrochemical Reactions
        ↓
Interface Velocity
        ↓
Level-Set Evolution
        ↓
Geometry Change
```

The local degradation velocity used for level-set evolution is derived directly from
the electrochemical reaction rates and transport conditions at the scaffold surface.
This provides the physical link between corrosion chemistry and scaffold morphology
evolution.

### Key Characteristics

- Mixed anodic-cathodic corrosion framework.
- Zinc dissolution driven degradation.
- ORR-controlled cathodic kinetics.
- Coupled with multi-species transport.
- Coupled with corrosion-product film evolution.
- Supports reaction-limited and transport-limited degradation.
- Produces spatially varying degradation behaviour.

### Model Outputs

The kinetic model provides:

- Local corrosion rates.
- Oxygen consumption rates.
- Zinc dissolution rates.
- Hydroxide generation rates.
- Surface reaction distributions.
- Time-dependent interface recession rates.

### Implementation

```text
physics/governing_equations.idp
physics/interface_velocity.idp
physics/interface_kinetics.idp
```

### References

1. Bockris, J. O'M., & Reddy, A. K. N. *Modern Electrochemistry 2B: Electrodics in
   Chemistry, Engineering, Biology, and Environmental Science.* Kluwer
   Academic/Plenum, 2000.
2. Bard, A. J., & Faulkner, L. R. *Electrochemical Methods: Fundamentals and
   Applications.* 2nd ed., Wiley, 2001.
3. Jones, D. A. *Principles and Prevention of Corrosion.* 2nd ed., Prentice Hall,
   1996.
4. Newman, J., & Thomas-Alyea, K. E. *Electrochemical Systems.* 3rd ed., Wiley, 2004.

## 6. Interface Velocity Formulation (flux-first)

The interface velocity determines how quickly the scaffold surface recedes and links
the electrochemistry to the geometry. From v1.1.0 the velocity is derived from the
same discrete oxygen flux that the oxygen equation removes at the interface, so that
oxygen consumed, zinc released and metal lost are tied together by construction. This is the
v1.1.0 default (`-flux_first 1 -v_picard 0 -conservative 2 -oh_fix 1`).

### Update sequence at every time step

```text
1. Solve O₂ on the current interface Γₙ (implicit Robin sink, film coverage θₙ)
2. Take the flux the sink removed, J = k_ORR κ(θ) C_O2|Γ
3. Project J to the recession velocity v (conservative, interface-weighted)
4. Update the film coverage θ from this v
5. Accumulate the O₂ and Zn tallies on Γₙ
6. Advance the level set with v, then solve the remaining species
```

### Velocity from the removed flux

The oxygen sink at the interface is the Robin condition

```text
−D_O2^eff ∇C_O2·n = k_ORR κ(θ) C_O2      on Γ
```

where κ(θ) is the film multiplier on the ORR (film coverage θ, Section 4). Each mole of
O₂ consumed oxidises two moles of zinc (O₂ + 2Zn + 2H₂O → 2Zn²⁺ + 4OH⁻), so on a molar
basis Zn:O₂ is 2:1 and, in mass, the zinc oxidised per unit oxygen consumed is
`2 M_Zn / M_O2 ≈ 4.09`. The recession velocity is

```text
v = −2 k_ORR κ(θ) C_O2|Γ / [Zn]sol      (C_O2 in mol/mm³, [Zn]sol = ρ_Zn / M_Zn)
ρ_Zn |v| = (2 M_Zn / M_O2) J_O2        (mass ratio 2 M_Zn / M_O2 ≈ 4.09; molar Zn:O₂ = 2:1)
```

In the solver, J is projected onto a P1 field with a lumped, interface-weighted
projection, `v_i = N_i / W_i`, where `W_i = ∫_Γ ψ_i` and `N_i` is the integral of the
removed flux against `ψ_i`. Because `Σ ψ_i = 1`, the integral of `v` over Γ equals the
integral of the removed flux exactly, using the same quadrature as the sink. Nodes that
carry no interface weight take `v` from their foot point on the interface (φ is a signed
distance). No displaced probe and no Picard iteration are used, so there is neither a
spatial nor a temporal lag between the oxygen sink and the velocity.

### Conservation checks

Before the interface moves the solver verifies that the projected zinc flux equals the
target `(2 M_Zn/M_O2) ∫_Γ J` (relative mismatch below `-flux_proj_tol`, default 1e-4,
followed by an exact rescaling and a post-projection residual check below 1e-8). A larger
mismatch stops the run with `ERROR_FLUXFIRST_PROJECTION_BALANCE`. Inconsistent flags
(`-flux_first 1` with `-v_picard` ≠ 0, with `-conservative` ≠ 2, or without the oxygen
equation) also stop the run. Oxygen and zinc tallies are accumulated on Γₙ before the
interface advances and are written to `mass_loss.txt`, `global_balance.tsv` and
`o2_interface_diag.tsv`.

### Reaction and diffusion control

Early on the interface is reaction-controlled. As the product film forms and oxygen near the
surface is depleted, the interface becomes diffusion-controlled. The transition is quantified by
the interface Damköhler number used for the manuscript's reaction/diffusion boundary:

```text
Da = C_b / ⟨C_O2|Γ⟩ − 1
```

`C_b` is the Dirichlet oxygen concentration (`-o2_initial`) and `⟨C_O2|Γ⟩` the area-mean oxygen
concentration over the interface. The solver diagnostic is `o2_interface_diag.tsv`:
`Da = 1 / Ratio_Iface_over_Initial − 1`. `Da < 1` is reaction-controlled, `Da > 1`
diffusion-controlled, and `Da = 1` is where the interface oxygen has fallen to half the bulk value.

**Derivation.** With the Robin sink `J = k_ORR κ(θ) C_Γ` and a quasi-steady supply through a
transport layer, `J = h_m (C_b − C_Γ)` with `h_m = D_O2^eff / δ`, so `C_b / C_Γ − 1 = k_ORR κ / h_m`:
the ratio of the film-modified reaction rate constant to the mass-transfer coefficient. This holds
for a spatially uniform film state; it is not an identity on a non-uniform interface.

**Related quantities are different proxies, not equivalents.**

| Quantity | Definition | Relation to `Da` |
|---|---|---|
| `Da` (above) | `C_b / ⟨C_Γ⟩ − 1` | the quantity used for the manuscript transition |
| `Da_J` | `k_ORR ⟨κ⟩ C_b / ⟨J⟩ − 1`, `⟨J⟩` = `O2FluxDensity_g_mm2_h` | equals `Da` only if `κ` is uniform on `Γ` |
| `Da_v` | `v_max / \|v_n\| − 1` with `v_max = 2 k_ORR C_b / [Zn]sol` (no film factor) | `(1/κ − 1) + k_ORR / h_m`: includes the film resistance; equals `Da` only for `κ = 1` |
| `Da_v(θ)` | the same with `v_max(θ) = 2 k_ORR κ(θ) C_b / [Zn]sol` | `C_b / C_Γ − 1` pointwise, since `\|v_n\| = 2 k_ORR κ C_Γ / [Zn]sol` |

Numerical comparison for the 3-D validation run (`k_ORR` = 200, `k_f` = 4×10⁵, `k_d` = 3×10⁶,
`C_b` = 6.2 mg/L, 0–672 h, from `o2_interface_diag.tsv`):

| Quantity | Crosses 1 at | Value at 24 / 168 / 336 / 672 h |
|---|---|---|
| `Da`, `C_b` = `-o2_initial` | 158.5 h | 17.8 / 0.875 / 0.204 / 0.074 |
| `Da`, `C_b` = liquid-mean oxygen | 120.1 h | 10.3 / 0.463 / 0.111 / 0.041 |
| `Da_J` | 165.9 h | 22.6 / 0.968 / 0.208 / 0.075 |
| `Da_v`, `κ = 1` in `v_max` | never | 49 / 141 / 389 / 933 |

The mean film factor `⟨κ⟩` falls to 0.37, 0.013, 0.003 and 0.001 at those times, which is why
`Da_v` with a film-free `v_max` never reaches 1: it measures the film and the transport together.
The transition of the manuscript (158.5 h) is the `Da` row. The Supporting Information must use
this definition, or state `Da_v(θ)`, and must name `C_b`.

In the flux-first formulation the transition emerges from the oxygen solve itself, because the
Robin sink already includes the diffusion limit; no minimum over rate limitations is taken.

### Film effects

```text
Film Growth → Reduced ORR (κ(θ) decreases) → Smaller removed flux → Lower interface velocity
```

The film coverage is updated from the same velocity that moves the interface, and the
zinc source is the oxidised zinc minus the zinc retained in the film (and plus the film
dissolved), so zinc is conserved at every node.

### Legacy probe-based formulation (superseded)

This subsection describes the formulation of v1.0.x, retained only for controlled
reproduction of earlier results. It is **not** the v1.1.0 formulation and is not used for the
revised study. It is selected with `-flux_first 0` (not the default); `-conservative 0|1` select
the older minimum-of-rates rules.

```text
Zn²⁺ transport-limited (Stefan)   →  vZn
ORR reaction-limited              →  vORR = −2 k_ORR C_O2 / [Zn]sol        (probe concentration)
O₂ transport-limited              →  vO2  = −2 D_O2^eff ∇C_O2·n / [Zn]sol
v = max(vZn, vO2)  on the non-positive velocities (the hard minimum of the rate magnitudes)
```

The oxygen concentration is sampled at a probe point beyond the interface
(`-h_interface`, `-vel_extension`, `-search_method`) from the start-of-step field, optionally
refined by `-v_picard N` semi-implicit passes (`-v_picard_w`). Diagnostic switches are
`-use_vzn`, `-force_v`, `-delta_eps`, `-legacy_vo2diff_sign` and `-debug_probe`. Because the
probe concentration and the oxygen sink are not the same discrete quantity, zinc removal could
be inconsistent with the oxygen consumed (Section 6, Errors corrected in `VALIDATION.md`).

### Key Characteristics

- Velocity, oxygen consumption and zinc release derive from one flux; the molar Zn:O₂ ratio (2:1) is enforced by construction.
- No probe point and no Picard iteration in the flux-first path.
- Reaction- and diffusion-controlled regimes follow from the Robin sink.
- Spatially varying recession rates drive the level-set evolution.
- Conservation is checked every step and fails closed.

### Model Outputs

- Local degradation velocities and surface recession rates.
- Oxygen and zinc tallies, global balances and interface oxygen diagnostics.
- Time-dependent geometry changes.

### Implementation

```text
physics/flux_first.idp
physics/governing_equations.idp
physics/interface_kinetics.idp
physics/interface_velocity.idp   (legacy probe-based path)
```

### References

1. Crank, J. *Free and Moving Boundary Problems.* Oxford University Press, 1984.
2. Alexiades, V., & Solomon, A. D. *Mathematical Modeling of Melting and Freezing
   Processes.* Hemisphere Publishing, 1993.
3. Bard, A. J., & Faulkner, L. R. *Electrochemical Methods: Fundamentals and
   Applications.* 2nd ed., Wiley, 2001.
4. Osher, S., & Sethian, J. A. "Fronts Propagating with Curvature-Dependent Speed:
   Algorithms Based on Hamilton-Jacobi Formulations." *Journal of Computational
   Physics*, 1988.

## 7. Optional Fluid Flow

By default, Dissolve™ assumes transport is dominated by diffusion, which is
appropriate for many static immersion experiments. For applications involving
flowing physiological fluids, perfusion systems, or vascular environments, an
optional fluid-flow module can be enabled to account for advective transport.

### Flow Coupling

```text
Fluid Flow
      ↓
Species Advection
      ↓
Modified Concentration Fields
      ↓
Modified Corrosion Rates
      ↓
Interface Evolution
```

Fluid motion can alter the delivery of reactants and the removal of corrosion
products, leading to degradation behaviour that differs significantly from purely
diffusion-controlled conditions.

### Governing Physics

When enabled, Dissolve™ solves the incompressible Navier-Stokes equations within the
fluid domain to obtain a velocity field `u = [ux, uy, uz]`. This velocity field is
then coupled to the transport equations for Zn²⁺, Cl⁻, OH⁻, and O₂ through advective
transport terms.

### Effects on Degradation

Fluid flow influences several aspects of the degradation process:

```text
Increased Oxygen Supply → Higher ORR Activity → Faster Degradation

Faster Removal of Zn²⁺ → Reduced Local Accumulation → Modified Dissolution Behaviour

Enhanced Chloride Transport → Film Destabilization → Changes in Passivation
```

### Application Areas

The fluid-flow model is particularly useful for:

- Bioreactor simulations
- Perfusion-based degradation studies
- Vascular implant applications
- Stent degradation modelling
- Device-fluid interaction studies
- Flow-assisted mass transport investigations

### Key Characteristics

- Three-dimensional incompressible flow solver.
- Fully coupled to species transport.
- Supports advection-diffusion-reaction modelling.
- Captures transport enhancement due to fluid motion.
- Compatible with evolving implant geometries.
- MPI-parallel implementation.

### Activation

Fluid flow is enabled with `-enable_flow 1` (default 0; `-enable_full_ns` selects the full
Navier-Stokes form, `-flow_solve_interval` the solve interval). When disabled,
species transport is governed by diffusion and reaction processes only.

**Validation status.** The flow-coupled degradation mode has not undergone systematic
experimental validation, and the regression suite does not exercise it. The calibration and
evaluation reported for v1.1.0 are for static immersion without flow. Treat flow-coupled
results as unvalidated.

### Model Outputs

The fluid-flow module provides:

- Velocity fields
- Pressure fields
- Flow streamlines
- Advection-enhanced species transport
- Flow-modified degradation distributions
- Spatially varying corrosion behaviour

### Implementation

```text
physics/governing_equations.idp
numerics/timestep_solver.idp
state/fields.idp
```

### References

1. Galdi, G. P. *An Introduction to the Mathematical Theory of the Navier-Stokes
   Equations.* Springer, 2011.
2. Elman, H. C., Silvester, D. J., & Wathen, A. J. *Finite Elements and Fast
   Iterative Solvers.* Oxford University Press, 2014.
3. Bird, R. B., Stewart, W. E., & Lightfoot, E. N. *Transport Phenomena.* Wiley,
   2002.

## 8. Finite Element Discretization

Dissolve™ solves all governing equations using the finite element method (FEM)
implemented through FreeFEM. This framework provides the flexibility required to
model complex implant geometries, evolving degradation fronts, coupled transport
phenomena, and moving boundaries within a single computational environment.

### Numerical Workflow

```text
Geometry & Mesh
      ↓
Field Initialization
      ↓
Weak Form Assembly
      ↓
Linear/Nonlinear Solvers
      ↓
Field Update
      ↓
Interface Update
      ↓
Next Time Step
```

Every simulation timestep consists of assembling and solving the coupled transport,
film, interface, and optional fluid-flow equations before advancing the geometry.

### Mesh Representation

Dissolve™ uses 3D tetrahedral finite-element meshes to represent both the implant
and surrounding fluid domain. This enables simulation of:

- Cylindrical implants
- Lattice scaffolds
- TPMS structures
- Stents
- Patient-specific geometries

### Weak Form Formulation

All governing equations are converted from their differential form into equivalent
weak forms before discretization:

```text
Strong Form PDE
      ↓
Weak Form
      ↓
Finite Element Assembly
      ↓
Linear System
      ↓
Numerical Solution
```

The weak forms are implemented directly within the `varf` blocks of
`physics/governing_equations.idp`.

### Time Integration

The solver advances the system incrementally in time:

```text
Time Step n
      ↓
Solve Fields
      ↓
Update Interface
      ↓
Time Step n+1
```

This allows long-term degradation simulations spanning days, weeks, or months of
implant exposure.

### Transport Stabilization

Reaction-diffusion systems can become numerically challenging when strong
concentration gradients develop near the degrading interface. To improve stability,
Dissolve™ employs **mass lumping**, which diagonalizes the mass matrix and improves
robustness for transport-dominated simulations. Benefits include:

- Improved numerical stability
- Reduced oscillations
- Faster linear solves
- Better behaviour near steep gradients

### Semi-Lagrangian Advection

When advection is present, Dissolve™ uses FreeFEM's `convect()` operator:

```text
Velocity Field
      ↓
Characteristic Tracking
      ↓
Field Advection
```

This approach improves stability for transport-dominated problems and reduces
numerical diffusion compared with conventional advection schemes.

### Parallel Computing

Large degradation simulations can involve millions of elements and multiple coupled
fields. Dissolve™ therefore supports MPI + PETSc for parallel execution. Capabilities
include:

- Distributed mesh partitioning
- Parallel matrix assembly
- Parallel linear solvers
- HPC cluster execution
- Multi-core workstation support

### Adaptive Remeshing

As the scaffold degrades, regions near the moving interface often require additional
resolution:

```text
Interface Motion
      ↓
Mesh Quality Check
      ↓
Adaptive Refinement
      ↓
Updated Mesh
```

Adaptive remeshing concentrates computational effort where it is most needed while
maintaining manageable computational costs.

### Key Characteristics

- Three-dimensional finite element formulation.
- Tetrahedral mesh discretization.
- Weak-form PDE implementation.
- Mass-lumped transport equations.
- Semi-Lagrangian advection.
- Adaptive remeshing support.
- MPI/PETSc parallel execution.
- Compatible with evolving geometries and moving interfaces.

### Numerical Outputs

The discretization framework provides:

- Species concentration fields
- Corrosion-product film fields
- Interface velocity fields
- Level-set fields
- Fluid velocity fields (optional)
- Degradation morphology evolution
- Parallel simulation scalability

### Implementation

```text
physics/governing_equations.idp
numerics/timestep_solver.idp
numerics/mesh_refinement.idp
domain/mesh_setup.idp
```

### References

1. Ciarlet, P. G. *The Finite Element Method for Elliptic Problems.* SIAM, 2002.
2. Brenner, S. C., & Scott, L. R. *The Mathematical Theory of Finite Element
   Methods.* Springer, 2008.
3. Zienkiewicz, O. C., Taylor, R. L., & Zhu, J. Z. *The Finite Element Method: Its
   Basis and Fundamentals.* Elsevier, 2013.
4. Hecht, F. "New Development in FreeFem++." *Journal of Numerical Mathematics*,
   2012.

## 9. Calibration Framework

Dissolve™ includes a calibration framework for identifying model parameters from
experimental degradation data and evaluating parameter sensitivity. These tools
automate the process of running large numbers of simulations and comparing model
predictions against experimental observations.

### Purpose

```text
Experimental Data
      ↓
Simulation Runs
      ↓
Parameter Update
      ↓
Error Evaluation
      ↓
Improved Parameter Set
```

The calibration workflow aims to identify parameter values that best reproduce
experimentally observed degradation behaviour.

### Parameters commonly calibrated

Three effective kinetic parameters are calibrated; film porosity and tortuosity, the film
thickness, the film-barrier parameters and all diffusivities are fixed. The parameter sets
that appear in this repository are distinguished below.

**Code defaults** (`config/settings.idp`; command-line defaults, *not* the calibrated values):

| Parameter | Default | Unit |
|---|---|---|
| `k_f` | 3×10⁵ | h⁻¹ |
| `k_d` | 1×10⁸ | mm⁶ g⁻² h⁻¹ |
| `k_ORR` | 80 | mm h⁻¹ |
| `C_O2,0` | 3.5 | mg L⁻¹ |
| `D_O2`, `D_Zn`, `D_Cl`, `D_OH` | 9.36, 2.7216, 7.776, 20.16 | mm² h⁻¹ |
| `ε`, `τ`, `δ`, `L_f` | 0.25, 2.0, 1.0, 0.001 mm | – |

**Revised-study calibrated values** (Bayesian optimization, balanced objective):

| Parameter | Search range | Calibrated value | Unit |
|---|---|---|---|
| `k_f` | [1×10⁵, 2.5×10⁶] | 4×10⁵ | h⁻¹ |
| `k_d` | [1×10⁴, 1×10⁸] | 3×10⁶ | mm⁶ g⁻² h⁻¹ |
| `k_ORR` | [25, 2500] | 200 | mm h⁻¹ |

`k_d` is bounded from above only: the objective is flat below about 10⁶ and rises above
3×10⁶, and 3×10⁶ is the largest value within 0.5 % of the best objective. The revised study
fixes `C_O2,0` = 6.2 mg L⁻¹, `D_O2` = 18.72, `D_Zn` = 3.384, `D_Cl` = 9.828 and
`D_OH` = 25.56 mm² h⁻¹, `ε` = 0.25, `τ` = 2, `L_f` = 1 µm, `Δt` = 4 h and a 24 h
reinitialization interval, and the film barrier `-film_mech 1` with `β_ref` = 12 µm⁻¹ at `ε` = 0.25,
`τ` = 2 (`-film_beta_couple 1`). The diffusivities, `C_O2,0` and the film-barrier settings differ from
the code defaults and must be given on the command line (full command in `INSTALL.md`).

**Unit-converted values** for the calibrated set (as used internally):

| Quantity | Value |
|---|---|
| retained share `s = k_f L_f² / D_Zn` | 4×10⁵ × (10⁻³)² / 3.384 = 0.118 |
| `k_d` in molar form, `k_d / clMolarConv²` | 3×10⁶ / (28 209)² = 3.8×10⁻³ L² mol⁻² h⁻¹ |

### Available Workflows

**Kinetic Parameter Calibration**

```text
Experimental Mass Loss
        ↓
Bayesian Optimization
        ↓
Updated Parameters
        ↓
Simulation Re-run
```

The revised study calibrates `k_f`, `k_d` and `k_ORR` against literature mass-loss data
(Liu et al., 24–336 h) and the 28-day HBSS pure-Zn data (24–672 h) with a balanced
objective, `sqrt(0.5 RMSE_Liu² + 0.5 RMSE_HBSS²)`. Because the HBSS data enter the
objective, the HBSS comparison is a fit check and not an independent validation.

**Bayesian Optimization**

```text
Parameter Space
      ↓
Gaussian Process Surrogate
      ↓
Smart Parameter Selection
      ↓
Simulation Evaluation
```

Bayesian optimization improves search efficiency by focusing evaluations in
promising regions of parameter space. Revised-study settings: Gaussian-process surrogate
(Matérn 5/2, log₁₀ inputs), 12-point Latin hypercube start, expected-improvement acquisition,
32 evaluations, search ranges as in the table above.

Implementation: `../Scripts/BO/`

**Sensitivity Analysis**

```text
Parameter Perturbation
      ↓
Simulation Response
      ↓
Sensitivity Ranking
```

Sensitivity studies identify which parameters have the greatest influence on
degradation predictions. The Morris elementary-effects script in this repository implements
the 8-parameter design (r = 20 trajectories, 180 runs, response = mass loss at 168 h). The
ranking for the revised study (reduced model, 10 parameters, 220 runs) is
C_O2,0 > D_O2 > k_f > k_ORR > D_Zn > porosity > tortuosity > k_d > D_Cl = D_OH = 0 and is
reported in the Supporting Information.

Implementation: `../Scripts/GSA/sensitivity_morris.py`

### Calibration Metrics

Model performance can be assessed using:

- Mass-loss error
- Volume-loss error
- Root Mean Square Error (RMSE)
- Time-dependent degradation trends
- Corrosion morphology agreement
- Experimental benchmark comparisons

### Typical Workflow

```text
Experimental Dataset
      ↓
Select Parameters
      ↓
Run Simulations
      ↓
Calculate Error
      ↓
Update Parameters
      ↓
Repeat Until Convergence
```

### Key Characteristics

- Automated parameter estimation.
- Support for multi-parameter optimization.
- Experimental data fitting.
- Bayesian optimization workflows.
- Global sensitivity analysis.
- Batch simulation support.
- HPC-compatible execution.

### Outputs

The calibration framework can generate:

- Optimized parameter sets
- RMSE histories
- Convergence plots
- Parameter rankings
- Sensitivity indices
- Optimization reports
- Calibration datasets

### Implementation

```text
../Scripts/BO/
../Scripts/GSA/sensitivity_morris.py
```

### References

1. Nelder, J. A., & Mead, R. (1965). "A simplex method for function minimization."
   *The Computer Journal*, 7(4), 308–313.
2. Nocedal, J., & Wright, S. J. *Numerical Optimization.* Springer, 2006.
3. Morris, M. D. (1991). "Factorial sampling plans for preliminary computational
   experiments." *Technometrics*, 33(2), 161–174.
4. Forrester, A., Sobester, A., & Keane, A. *Engineering Design via Surrogate
   Modelling.* Wiley, 2008.

## 10. Application Domain

Dissolve™ is designed for the simulation and virtual testing of biodegradable
metallic implants, with a primary focus on zinc-based materials and porous implant
architectures. The framework combines degradation kinetics, species transport,
corrosion-product evolution, and geometry change within a single computational
environment, enabling investigation of how implant design influences long-term
degradation behaviour.

### Target Applications

- Orthopaedic implants
- Bone scaffolds
- Porous fixation devices
- Biodegradable stents
- Patient-specific implants
- Experimental implant prototypes

### Implant Architectures

Dissolve™ supports a wide range of geometries, including:

- Solid cylinders
- Porous cylinders
- BCC lattices
- FCC lattices
- TPMS structures
- Custom patient-specific geometries

Examples of TPMS-based designs include Gyroid, Schwarz-P, and Diamond.

### Design Questions Addressed

The framework can be used to investigate:

- How fast will an implant degrade?
- How does porosity affect degradation?
- How does geometry influence mass loss?
- How does scaffold architecture affect transport?
- Where will degradation occur first?
- How does the degradation morphology evolve?
- How long does structural support remain?

### Engineering Applications

- Implant design optimization
- Virtual prototyping
- Sensitivity analysis
- Design space exploration
- Material screening
- Benchmarking against experiments

Within the validated scope (Section 9 and `VALIDATION.md`), computational studies can
complement physical degradation experiments in implant design evaluation.

### Research Applications

- Corrosion mechanism investigation
- Transport-limited degradation studies
- ORR-dominated corrosion analysis
- Film formation studies
- Multi-scale modelling workflows
- Parameter calibration

The modular architecture allows researchers to modify transport models, reaction
kinetics, material properties, and degradation mechanisms while retaining the core
simulation framework.

### Computational Design Workflow

```text
Implant Geometry
      ↓
Mesh Generation
      ↓
Dissolve™ Simulation
      ↓
Mass Loss & Morphology
      ↓
Performance Assessment
      ↓
Design Iteration
```

This workflow enables systematic evaluation of implant designs before experimental
testing or manufacturing.

### Future Extensions

Although the current implementation focuses on zinc degradation, the framework can be
extended to additional biodegradable metallic systems through modification of
material properties and reaction models. Potential extensions include:

- Magnesium alloys
- Iron-based implants
- Multi-material systems
- Mechanically coupled degradation
- Biological response models
- Patient-specific simulations

### Key Characteristics

- Designed for biodegradable metallic implants.
- Supports porous and non-porous architectures.
- Applicable to both research and engineering studies.
- Compatible with high-performance computing workflows.
- Suitable for virtual testing and design optimization.
- Extensible to new materials and degradation mechanisms.

### References

1. Bowen, P. K., Drelich, J., & Goldman, J. "Zinc exhibits ideal physiological
   corrosion behavior for bioabsorbable stents." *Advanced Materials*, 2013.
2. Zheng, Y. F., Gu, X. N., & Witte, F. "Biodegradable metals." *Materials Science
   and Engineering R*, 2014.
3. Witte, F. "The history of biodegradable magnesium implants: A review." *Acta
   Biomaterialia*, 2010.
4. Li, H. F., Xie, X. H., Zheng, Y. F., et al. "Development of biodegradable
   Zn-based alloys with nutrient alloying elements." *Scientific Reports*, 2015.
