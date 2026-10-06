# Phenomenal Engine v0.1.0

A **simulation-first chatbot RPG kit**: Python computes the uncertain world; the language model narrates only what an observer could perceive.

The central rule is:

> **Deterministic causality where the model knows the state; probability where the world, action, or observer is genuinely uncertain.**

This package is intentionally pure-Python and dependency-free. It is designed to be attached to an AI-agent conversation, embedded in a local application, or used as a reference implementation for a richer game client.

## Included

- Stable seeded `PCG32` random number generator with independent named streams.
- Logistic skill checks, hazards, Bayesian beliefs, correlated uncertainty, heavy-tailed consequences.
- Small physical helpers for gravity, symplectic orbital stepping, sound, electromagnetic light, Doppler shift, reverberation, and Planck-scale budget estimates.
- A local finite-difference wave-equation example.
- Iterated Prisoner's Dilemma tournament and an evolutionary memory-one strategy experiment.
- Tamper-evident, append-only JSON memory ledger.
- Provider-neutral image-job queue and per-turn scene prompts.
- Standard JSON mod schema.
- Three complete mods:
  1. `great_labyrinth_of_egypt.json`
  2. `orbital_swarm_trail.json`
  3. `concord_tournament.json`

## Quick start

From this directory:

```bash
python -m phenomenal_engine validate mods
python -m phenomenal_engine tournament --rounds 100 --error-rate 0.02
python -m phenomenal_engine evolve --generations 30
python -m phenomenal_engine planck-budget
python -m phenomenal_engine step mods/great_labyrinth_of_egypt.json "I listen at the sealed door." --skill 1.2 --difficulty 0.8
```

Create a save:

```bash
python -m phenomenal_engine new-save mods/concord_tournament.json runtime/concord-save.json --seed "my-campaign"
```

## The realism model

Do **not** simulate an entire universe at Planck resolution. The engine uses a ladder:

1. **Narrative/event scale** — most world objects are state variables and causal graphs.
2. **Rigid-body/orbital scale** — integrate only bodies relevant to the scene.
3. **Wave/ray scale** — use acoustics or optics only when observable differences matter.
4. **Microscopic/quantum scale** — use statistical or symbolic models when a plot event depends on them.
5. **Planck scale** — constants and conceptual boundaries, not a literal lattice.

The full observable universe contains on the order of `10^185` Planck volumes; stepping those across cosmic history approaches `10^246` cell updates. A compelling game needs **adaptive refinement**, not brute-force metaphysics.

## AI image generation

Each scene can emit a provider-neutral image job. The default sample mods request one every turn. In a host application, a worker can submit these prompts to an image model while narration remains usable. In an AI-chat environment with an image tool, the agent can generate the image after the narrative response and store the returned reference in memory.

See `docs/image_pipeline.md`.

## Persistent memory

Every consequential action is appended to a hash-chained event ledger. Saves contain:
- world state
- character and relationship state
- quests and open threads
- Bayesian beliefs with confidence/provenance
- long-term consequences
- RNG stream states
- chronicle and summaries
- image jobs

See `docs/memory_protocol.md`.

A staged route toward substantially richer physics is in `docs/roadmap.md`.

## Design status

This is a **reference engine**, not a general-relativistic or quantum field simulator. Its purpose is to produce physically and probabilistically coherent story consequences while remaining fast enough for turn-by-turn play.
