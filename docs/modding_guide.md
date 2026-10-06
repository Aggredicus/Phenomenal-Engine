# Modding Guide

A mod is data, not engine code.

## Minimum structure

See `schemas/mod.schema.json`. Start by copying one of `mods/*.json`.

The strongest mods define:
- **premise**: the fantasy of play,
- **truth_boundary**: what is factual vs speculative/invented,
- **simulation_profile**: time, randomness, physics, image cadence,
- **starting_state**: canonical initial variables,
- **world_model**: causal rules,
- **factions / characters / locations**,
- **quests and clocks**,
- **encounters**: dilemmas with multiple mechanically distinct approaches,
- **mechanics**,
- **memory_rules**,
- **image_direction**,
- **llm_directives**,
- **endings**: families of emergent resolution, not one canonical answer.

## Good mod principle

Put *truth* in the JSON and *prose* in the model.

Do not script paragraphs of future narration. Script:
- stable facts,
- causal systems,
- sensory parameters,
- motives,
- thresholds,
- clocks,
- consequences.

Then let play create the composition.

## Randomness

A mod should specify what is:
- sampled once when the world is created,
- redrawn each event,
- deterministic,
- learned only through evidence.

Avoid randomizing identity facts every turn.

## Physics

Only request a high-fidelity solver when it can change the player's observation or decision. Most scenes can use reduced-order models.

## Images

`image_cadence` may be:
- `off`
- `every_turn`
- `key_moments`
- `every_N`, e.g. `every_3`

`every_turn` is immersive but potentially expensive/slow in hosted environments. The narrative remains playable even when images arrive later or are disabled.
