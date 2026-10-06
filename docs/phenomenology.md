# Physics → Phenomenology → Prose

The engine should not narrate the world directly from hidden state.

Use three stages:

1. **World state** — what physically exists.
2. **Observer transform** — what reaches the character's senses/sensors, with noise and occlusion.
3. **Narrative composition** — language that renders those observations into a scene.

Example:

World:
- 2 kW acoustic source,
- 180 m away,
- behind a wall,
- source approaching.

Observer:
- attenuated low-frequency energy,
- partial occlusion,
- rising pitch,
- 0.5 s propagation delay,
- uncertain direction because of reflections.

Narrative:
- describe the low throb arriving through the structure,
- then a slight rise in pitch,
- then perhaps a delayed reflection,
- never say "the machine is exactly 180 m away" unless the character has measured that.

This architecture allows the same physics to drive:
- prose,
- generated imagery,
- audio,
- UI telemetry,
- NPC perception,
- stealth/detection mechanics.

It also prevents an LLM from leaking omniscient facts into first-person experience.
