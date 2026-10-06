# Multiscale Physics Architecture

## Why not Planck-cell brute force?

Using an observable-universe radius around `4.4e26 m`, the number of Planck-length cubic cells is roughly `8e184`. The age of the universe is roughly `8e60` Planck times. A literal cell update per spatial cell per Planck step approaches `10^246` updates.

More importantly, current physics does not establish that spacetime is a simple cubic lattice of Planck cells. Treat Planck length/time as dimensional scales where quantum gravity becomes unavoidable, not as a game-engine voxel size.

## The useful alternative: causal adaptive refinement

Represent the universe as a hierarchy:

### Level A — causal/event graph
Objects have identities, resources, relations, clocks, and equations of motion only when needed.

### Level B — rigid/orbital bodies
Use analytic solutions or symplectic integrators for local orbital systems. Coarse-step distant bodies; refine close approaches.

### Level C — ray fields
For most visible light and many long-range acoustic questions, trace paths, occlusion, reflection, attenuation, and travel time.

### Level D — wave fields
Open a local FDTD/FEM-like wave patch only when diffraction, interference, resonance, or standing waves change what the observer can perceive.

### Level E — microscopic/statistical models
Represent gases, thermal systems, chemistry, and populations statistically unless individual particles matter.

### Level F — quantum models
Use amplitudes, operators, spectra, or effective models for quantum-dependent plot devices. Do not pretend classical particles at Planck resolution reproduce quantum field theory.

## Electromagnetic layer

A serious future implementation should support Maxwell's equations, but the story engine can choose the cheapest valid approximation:

- **geometric optics** for ordinary camera/lighting paths,
- **spectral radiometry** for color and energy,
- **wave optics** for interference/diffraction,
- **Maxwell FDTD/FEM** for small domains where fields matter,
- **relativistic Doppler** for high-speed sources.

The most important narrative output is not raw field values; it is what reaches an observer: brightness, direction, spectrum, polarization if relevant, time delay, flicker, shadow, glare, and uncertainty.

## Sound layer

Likewise:
- ray/energy acoustics for large rooms and outdoor propagation,
- inverse-distance attenuation plus absorption for quick scenes,
- Sabine-style reverberation for gross room character,
- local wave solvers for resonance and diffraction,
- source/observer Doppler for motion.

The observer layer converts this into delay, loudness, direction, pitch shift, reverberation, masking, and vibration.

## Symplectic integration

For long-lived orbital stories, energy-preserving structure often matters more than a locally tiny integration error. Leapfrog / kick-drift-kick is included as the first reference step.
