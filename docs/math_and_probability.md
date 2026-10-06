# Mathematics for Realistic RPG Probability

## Why a d20 feels artificial

A tabletop die often collapses several different uncertainties into one draw:
- whether the character executes an action correctly,
- whether hidden environmental conditions are favorable,
- whether the observer notices the result,
- how large the consequence is,
- whether a rare background event occurs.

A computer can model those separately.

## Recommended stack

### 1. Stable pseudorandom streams
Use an explicit algorithm and save its state. Separate streams (`actions`, `world`, `encounters`, `images`) prevent adding a cosmetic random draw from changing tomorrow's weather.

### 2. Logistic action resolution
For skill `s`, difficulty `d`, context `c`, and temperature `tau`:

`P(success) = sigmoid((s + c - d) / tau)`

This behaves like a smooth contest rather than a hard target number.

### 3. Hazard functions
Rare events are better represented as processes in time:

`P(event by t) = 1 - exp(-lambda * t)`

Travel pace, weather, disease exposure, equipment stress, or detection can change `lambda`.

### 4. Bayesian uncertainty
If an NPC, sensor, bridge, or AI system has an unknown reliability, do not redraw its "true reliability" every turn. Give the world a hidden parameter and let characters update beliefs from evidence. Beta-Bernoulli updating is a compact example.

### 5. Correlated variables
Weather, fatigue, visibility, road damage, morale, and error rates often move together. Use multivariate distributions or latent shared factors rather than independent rolls.

### 6. Heavy-tailed consequences
Damage and delay are rarely uniform. Log-normal, gamma, or mixture distributions create common small effects and rare large ones.

### 7. Monte Carlo counterfactuals
For strategic choices, run many plausible futures from the same current state and summarize the distribution. Do not use Monte Carlo to decide what "morally should" happen; use it to estimate consequences.

### 8. Hidden-state sampling vs repeated sampling
Sample persistent world facts once:
- whether the bridge contains a latent defect,
- an NPC's private goal,
- the actual reliability of a sensor.

Sample transient noise repeatedly:
- wind gust,
- execution slip,
- packet loss.

This single distinction makes procedural worlds feel much more coherent.

## Most useful Gallier subjects

From Jean Gallier's book collection, the highest-value subjects for this engine are:

1. **Linear Algebra and Optimization with Applications to Machine Learning** — state vectors, least-squares inference, covariance, optimization, numerical geometry.
2. **Differential Geometry and Lie Groups** — rotations, rigid motion, manifolds, coordinate-independent thinking, continuous symmetry.
3. **Aspects of Harmonic Analysis and Representation Theory** — Fourier/spectral descriptions of sound and electromagnetic waves.
4. **Geometric Methods and Applications / Geometric Modeling** — meshes, projective geometry, camera geometry, curves, surfaces, spatial algorithms.
5. **Discrete Mathematics** — graphs, routing, combinatorics, finite state systems, networked worlds.
6. **Convex Geometry / Linear Programming / Voronoi / Delaunay** — collision/visibility geometry, spatial partitions, feasible action regions, optimization.
7. **Topology and Homology** — connectivity, holes, tunnels, field defects, map invariants; powerful but less central to the first physics prototype.
8. **Logic, Computability, and Automata** — rule verification, quest automata, formal constraints, reproducible agent behavior.

For a true physics engine, supplement these with numerical ODE/PDE methods, classical/Hamiltonian mechanics, electromagnetism, acoustics, statistical mechanics, relativity, quantum mechanics, and numerical analysis.
