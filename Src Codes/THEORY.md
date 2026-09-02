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
physics/interface_velocity.idp
physics/interface_kinetics.idp
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

At each timestep the solver:

1. Solves species transport equations.
2. Updates corrosion-product film evolution.
3. Computes interfacial reaction rates.
4. Calculates degradation velocity.
5. Advances the moving interface.
6. Updates the computational mesh.
7. Exports simulation results.

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
to:

- Maintain stable interface normals
- Improve curvature estimation
- Preserve numerical accuracy near the boundary
- Support robust interface-velocity calculations

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

Film formation is controlled by the film-formation rate parameter `kf`. Higher
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

Film degradation is controlled by `kd`, which governs the removal of corrosion
products and the reopening of transport pathways to the scaffold surface.

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

The cathodic reaction rate is governed by `kORR`, which controls the intensity of
oxygen reduction at the scaffold surface. Increasing `kORR` generally leads to:

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

## 6. Interface Velocity Formulation

The interface velocity determines how quickly the scaffold surface recedes during
degradation and provides the link between electrochemical processes and geometry
evolution. At every timestep, Dissolve™ calculates a local surface velocity and uses
it to advance the level-set interface.

### Role in the Simulation

```text
Species Transport
      ↓
Surface Reactions
      ↓
Interface Velocity
      ↓
Level-Set Evolution
      ↓
Geometry Update
```

The interface velocity acts as the mechanism that converts local corrosion activity
into physical material loss.

### Velocity Components

Dissolve™ evaluates degradation from two complementary perspectives:

```text
Zn Transport-Limited Dissolution  →  vZn

Oxygen Reduction Controlled Dissolution  →  vO2
```

These contributions represent the transport and reaction limitations governing the
degradation process.

### Zinc-Controlled Velocity

```text
Zn Dissolution
      ↓
Zn²⁺ Flux
      ↓
Interface Recession
```

The zinc component is derived from the flux of dissolved zinc species leaving the
scaffold surface. This mechanism captures:

- Anodic dissolution
- Species transport limitations
- Material removal from the scaffold

Regions with larger zinc fluxes experience higher local recession rates.

### Oxygen-Controlled Velocity

```text
O₂ Availability
      ↓
ORR Activity
      ↓
Corrosion Rate
      ↓
Interface Recession
```

The oxygen component reflects the influence of the oxygen reduction reaction on
degradation. The formulation considers:

- Oxygen concentration
- ORR kinetics
- Film transport resistance
- Local transport limitations

This allows oxygen accessibility to directly influence scaffold degradation.

### Velocity Selection

The overall interface velocity is determined from the coupled electrochemical and
transport behaviour:

```text
Zn Transport + O₂ Transport + ORR Kinetics + Film Effects
                       ↓
               Interface Velocity
```

This approach ensures degradation remains physically consistent under both
reaction-controlled and transport-controlled conditions.

### Interface Probing

Accurate velocity calculation requires evaluating species concentrations close to the
scaffold surface:

```text
Interface
    ↓
Concentration Probe
    ↓
Local Fluxes
    ↓
Velocity Calculation
```

Dissolve™ supports multiple probing strategies to improve robustness on complex
meshes and degrading geometries.

### Film Effects

The corrosion-product film directly influences interface motion:

```text
Film Growth
      ↓
Reduced O₂ Transport
      ↓
Reduced ORR Activity
      ↓
Lower Interface Velocity
```

As film accumulation increases, transport resistance grows and degradation rates can
decrease.

### Key Characteristics

- Converts reaction and transport behaviour into geometry evolution.
- Directly coupled to Zn²⁺ and O₂ transport.
- Accounts for corrosion-product film effects.
- Supports reaction-limited and transport-limited degradation.
- Produces spatially varying surface recession rates.
- Drives level-set interface evolution.

### Model Outputs

The interface velocity formulation provides:

- Local degradation velocities.
- Surface recession rates.
- Velocity distributions along the scaffold surface.
- Transport-limited degradation regions.
- Reaction-limited degradation regions.
- Time-dependent geometry changes.

### Implementation

```text
physics/interface_velocity.idp
physics/interface_kinetics.idp
physics/governing_equations.idp
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

Fluid flow can be enabled through `-solve_fluid 1`. When disabled (`-solve_fluid 0`),
species transport is governed by diffusion and reaction processes only.

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

### Parameters Commonly Calibrated

```text
kf   : Film formation rate
kd   : Film degradation rate
kORR : Oxygen reduction reaction rate
τ    : Film tortuosity
```

Depending on the study, transport coefficients and additional model parameters may
also be investigated.

### Available Workflows

**Kinetic Parameter Calibration**

```text
Experimental Mass Loss
        ↓
Nelder-Mead Optimization
        ↓
Updated Parameters
        ↓
Simulation Re-run
```

The primary calibration workflow adjusts degradation parameters to minimize
differences between simulated and measured mass-loss data. This is how the
validated parameters in `VALIDATION.md` were originally derived; the
Nelder-Mead script itself isn't included in this repository — use
`calibrate_bayesian.py` below to recalibrate against new data.

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
promising regions of parameter space.

Implementation: `../Calibration/calibrate_bayesian.py`

**Sensitivity Analysis**

```text
Parameter Perturbation
      ↓
Simulation Response
      ↓
Sensitivity Ranking
```

Sensitivity studies identify which parameters have the greatest influence on
degradation predictions.

Implementation: `../Calibration/sensitivity_morris.py`

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
../Calibration/calibrate_bayesian.py
../Calibration/sensitivity_morris.py
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

By replacing large numbers of physical degradation experiments with computational
studies, Dissolve™ can accelerate implant development and design evaluation.

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
