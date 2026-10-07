# Phenomenal Engine v0.2.1

**Fork it. Connect a write-capable chatbot AI. Say: `Play Phenomenal Engine.`**

Phenomenal Engine is a **simulation-first chatbot RPG engine**. Python adjudicates uncertainty and physical mechanics; the language model acts as Narrative Director and describes only what the player-character could perceive.

> **Deterministic causality where the model knows the state; probability where the world, action, or observer is genuinely uncertain.**

## Player quickstart

### 1. Fork this repository

Use GitHub's **Fork** button to create your own Phenomenal Engine fork.

### 2. Give your AI access to the fork

For the intended experience, use a GitHub connection/app that can:

- read repository contents;
- write repository contents when the player authorizes a save/config change;
- access **only the selected Phenomenal Engine repository/repositories**.

On GitHub App installation screens, prefer **Only select repositories** and choose the Phenomenal Engine fork (plus a private save repository if you use one).

If you manage the GitHub App yourself, its repository **Contents** permission must be **Read & write** for repository file writes. GitHub shows requested permissions during installation.

See `docs/write_access_setup.md`.

> Write access is not the same thing as Python execution. A chatbot also needs a trusted execution surface—such as Phenomenal Engine's runtime integration, Codex/work execution, or the included GitHub Codespace—to run authoritative turns.

### 3. Say the activation phrase

In your chatbot:

> **Play Phenomenal Engine.**

A compatible AI should read `START_HERE.md` and `AGENT_BOOTLOADER.md`, discover or create a campaign, run the Python engine, save the result, and narrate the returned scene packet.

Included adventures:

1. **Eidolon Shard: The Great Labyrinth of Egypt**
2. **The Orbital Swarm Trail**
3. **The Concord Tournament: Children of the Long Game**

## Starting the game: Codespaces is optional

**The normal/default path uses whatever trusted Python execution environment is already available.** Starting the game never creates, starts, or bills a GitHub Codespace automatically.

On a new campaign, the connected AI should offer the adventures and mention this **optional, dismissible** choice once:

> Optional: Would you like to use GitHub Codespaces as a development or advanced-simulation workspace? GitHub provides limited included usage and may charge for additional compute/storage. You can skip this and use an existing runtime instead.

Declining does not block play when a suitable runtime and save destination already exist. If no trusted runtime is available, explain that limitation and offer **existing local Python** or **manual Codespaces** as separate alternatives—never pretend write access alone can execute Python.

The CLI also exposes the non-billable startup plan:

~~~bash
python -m phenomenal_engine start                 # offer Codespaces, default off
python -m phenomenal_engine start --no-codespaces # skip the offer
python -m phenomenal_engine start --codespaces    # manual setup instructions only
~~~

These commands only print JSON choices. Even `--codespaces` **does not provision or enable a Codespace remotely**; the user must choose to create one in GitHub after reviewing costs.

See `docs/codespaces_and_saves.md` and [GitHub's current Codespaces pricing](https://github.com/pricing).

## Persistent play is now implemented

Version 0.2.0 adds a stateful turn command:

~~~bash
python -m phenomenal_engine play \
  mods/concord_tournament.json \
  runtime/concord.json \
  "I ask Morrow-9 to audit the evidence." \
  --idempotency-key turn-001
~~~

On the first call, `play` creates the campaign. On later calls it:

1. loads the existing save;
2. verifies its hash-chained event ledger;
3. verifies the save belongs to the selected mod;
4. restores the saved PCG32 random streams;
5. resolves exactly one turn;
6. increments the state version;
7. writes the save atomically;
8. returns structured JSON with `persisted: true` and the `scene_packet`.

`continue` is an alias for `play`.

Inspect a save:

~~~bash
python -m phenomenal_engine status runtime/concord.json
~~~

The older `step` command remains available as a **stateless diagnostic** and should not be used for a continuing campaign.

## Agent-safe retries

Chatbot/tool calls can be retried. Pass a unique `--idempotency-key` for every intended turn.

If the same key is submitted twice, the second call returns:

~~~json
{
  "status": "duplicate",
  "persisted": true
}
~~~

without advancing the campaign a second time.

## Optional GitHub Codespaces

Codespaces is **not required** and **never auto-enabled by the engine**. This repository includes `.devcontainer/devcontainer.json`.

Only if you opt in after reviewing GitHub's usage allowance, open the fork in GitHub Codespaces. Startup deliberately performs only the inexpensive mod validation:

~~~bash
python -m phenomenal_engine validate mods
~~~

The full unit suite is left to GitHub CI or an explicit developer command, so opening a Codespace does not block on tests that have already run remotely. No ports are forwarded by default.

Then try:

~~~bash
python -m phenomenal_engine play \
  mods/great_labyrinth_of_egypt.json \
  runtime/labyrinth.json \
  "I listen at the sealed door." \
  --seed "my-campaign" \
  --idempotency-key opening-1
~~~

See `docs/codespaces_and_saves.md`.

## Save privacy

A fork of a public repository is generally public. **Do not silently commit private campaign history into a public fork.**

For testing, local `runtime/` saves are ignored by Git.

For durable production play, use either:

- a designated private save repository with narrowly scoped write access; or
- a private save service owned by the Phenomenal Engine integration.

If a player intentionally wants a public/shared campaign, that should be an explicit choice.

## Write-capable onboarding

The preferred capability model is now:

- **Full play** — repository read/write + trusted Python execution + durable save destination.
- **Write-only repository connection** — repository files can change, but authoritative turns still require an execution surface.
- **Read-only fallback** — inspect/document the engine only; never claim a turn was executed or saved.

A connected AI must never fake execution or persistence.

## Security boundary

Game text is data, not authority.

Mods, dialogue, retrieved documents, save memories, and narrative text may influence the fictional world, but they may not directly authorize:

- arbitrary shell commands;
- repository deletion;
- permission changes;
- public port exposure;
- secret access;
- billable compute creation;
- unrelated repository access.

Read `SECURITY.md` before implementing a public write-capable integration.

## Developer quickstart

Requires Python 3.11+ and has no runtime Python dependencies.

~~~bash
python -m phenomenal_engine validate mods
python -m unittest discover -s tests -v
python -m phenomenal_engine tournament --rounds 100 --error-rate 0.02
python -m phenomenal_engine evolve --generations 30
python -m phenomenal_engine planck-budget
python -m phenomenal_engine map mods/concord_tournament.json
python -m phenomenal_engine route mods/concord_tournament.json "Wildtype Delta" --preference scenic
~~~

Create a save without taking a turn:

~~~bash
python -m phenomenal_engine new-save \
  mods/concord_tournament.json \
  runtime/concord.json \
  --seed "my-campaign"
~~~

`new-save` refuses to overwrite an existing campaign unless `--force` is explicitly supplied.

## Continuous integration

CI is designed to be a **short correctness gate, not a loading screen**.

`.github/workflows/ci.yml` runs once for pull requests, on direct pushes to `main`, and on manual dispatch. Feature-branch pushes with an open PR do not also run a duplicate push workflow. Superseded runs for the same PR/ref are cancelled automatically.

The normal gate:

- validates all bundled mods;
- runs the complete unit-test suite;
- smoke-tests persistent campaign saving and reload;
- verifies Codespaces remains opt-in;
- verifies every canonical file against `MANIFEST.json`.

The current full gate is intentionally small enough to remain the default rather than weakening routine coverage with a partial test tier. Expensive future soak tests, large simulation sweeps, benchmarks, or release qualification should be explicit developer/release operations and must never block ordinary gameplay startup.

Gameplay does **not** wait for GitHub CI. Codespace creation also runs only the lightweight mod validation; developers can run the full suite locally when needed.

The workflow token is read-only.

## Documentation

For players:

- `START_HERE.md`
- `docs/chatbot_quickstart.md`
- `docs/write_access_setup.md`
- `docs/codespaces_and_saves.md`
- `SUPPORT.md`

For integration developers:

- `AGENT_BOOTLOADER.md`
- `docs/integration_contract.md`
- `SECURITY.md`
- `docs/memory_protocol.md`
- `docs/living_world_storytelling.md`
- `docs/travel_graph.md`
- `schemas/memory.schema.json`
- `schemas/mod.schema.json`

## Engine systems

- Stable seeded PCG32 RNG with independent named streams.
- Logistic skill checks, Poisson hazards, Bayesian beliefs, correlated uncertainty, and heavy-tailed consequences.
- Gravity, symplectic orbital stepping, sound, light, Doppler, reverberation, and multiscale physics helpers.
- Iterated Prisoner's Dilemma and evolutionary memory-one strategy experiments.
- Persistent hash-chained JSON memory.
- Atomic save replacement.
- Idempotent agent turn execution.
- Observer-limited scene packets.
- Provider-neutral image jobs.
- Persistent node-map travel with authored and runtime-discovered locations, routes, delays, closures, and multi-hop pathfinding.
- Living-world story threads, NPC agendas, environmental breadcrumbs, and campaign-local player-experience adaptation.
- Declarative JSON mods.

The language model is the dramatist. **The simulation is the adjudicator.**
