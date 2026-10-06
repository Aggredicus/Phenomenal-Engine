# Per-Turn Image Pipeline

The sample mods set `image_cadence` to `every_turn`.

## Host behavior

After simulation:
1. Build the `scene_packet`.
2. Immediately produce the readable narrative.
3. Create an image job from the same observer-limited scene packet.
4. If the platform supports a background worker, enqueue the job and attach the finished image to the corresponding turn when ready.
5. If only synchronous image generation is available, generate after the prose rather than delaying the simulation.
6. If no image tool is available, preserve the prompt in memory and continue play.

This package does not include credentials or a network-specific image API. `phenomenal_engine.image_jobs` creates provider-neutral JSONL jobs.

## Why the image uses the scene packet

The image model should not see unrestricted hidden world state. It should receive:
- current visible geometry,
- characters actually present,
- light and atmosphere,
- observer viewpoint,
- established continuity details,
- action/outcome information visible in the moment.

That keeps image generation from accidentally spoiling a concealed enemy, secret door, hidden injury, or unknown identity.

## Continuity

For each recurring character/object, hosts should maintain an asset/continuity record:
- appearance description,
- reference-image identifier if available,
- clothing/equipment,
- injuries,
- persistent environmental changes.

Images are illustrations of canon. They do not create canon unless the player explicitly adopts a newly generated visual detail.
