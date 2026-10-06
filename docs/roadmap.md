# Physics & Simulation Roadmap

## v0.2 — Better observer physics
- Material tables for acoustic absorption and optical reflectance.
- Air absorption, occlusion, diffraction heuristics, and simple room impulse estimates.
- Observer models for vision, hearing, sensor noise, thresholds, and attention.
- Causal long-term consequence scheduler.

## v0.3 — Spatial engine
- Bounding-volume hierarchy for rays and collision queries.
- Delaunay/Voronoi navigation and environmental sampling.
- Rigid-body transforms using quaternions / SO(3) and SE(3).
- Sparse graph state for large worlds.

## v0.4 — Local field solvers
- Optional NumPy/SciPy backend for 2-D/3-D acoustic wave patches.
- Maxwell FDTD patches for scenes where interference or electromagnetic propagation matters.
- Heat/diffusion/advection solvers.
- Solver-error estimates exposed to the narrative layer.

## v0.5 — Astronomical layer
- Hierarchical N-body system with symplectic integrators.
- Adaptive timesteps and close-encounter solver switching.
- Relativistic corrections where measurable.
- Observation light-time, Doppler, and uncertainty propagation.

## v0.6 — Statistical / microscopic layer
- Monte Carlo transport.
- Chemical-kinetic and thermodynamic reduced models.
- Stochastic population/ecology modules.
- Quantum-effective models for plot-relevant experiments without pretending to simulate all quantum fields.

## v1.0 — Solver federation
A scene declares what observables matter. A planner chooses the cheapest solver whose error bounds are small enough to distinguish the player's available choices. The result is cached into persistent world state and converted through an observer model before narration.

This is the central scalability idea: **simulate distinctions that can matter, not every degree of freedom that exists.**
