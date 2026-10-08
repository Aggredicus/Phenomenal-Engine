# Phenomenal Engine v0.4.0

Released 2026-10-07.

Phenomenal Engine v0.4.0 is the first release of the living-world Mirror Delivery line. It promotes the complete development branch to the canonical release while preserving the engine's simulation-first, persistent, least-privilege architecture.

## Headline changes

- Replaced the Concord Tournament campaign with **Mirror Delivery**, an original four-courier inner-system expedition carrying four isolated copies of Mir toward Mercury.
- Added living-world story progression: breadcrumbs, quest promotion, NPC agendas, world events, campaign-local player-experience adaptation, and persistent consequences.
- Added persistent node-map travel with authored distances, route risk/access, runtime-discovered nodes and shortcuts, fastest/safest/scenic pathfinding, and one-edge-at-a-time journeys.
- Added an interactive map UI with focus/preview, distance/time/risk display, explicit **Confirm Travel**, rerouting, continuation, and cancellation.
- Added deliberate Mir activation as an irreversible, auditable campaign action with provenance and acceptance consequences.
- Added the JSON-first Director Interface for human/AI co-directing, including stable state projection, command validation, observer-safe remote state, facts-vs-beliefs separation, and an explicit human approval gate for Mir activation.
- Added the optional accessible Google Sheets adapter as a materialized view over canonical JSON state; it does not use Drive-wide access.
- Improved CI efficiency while keeping the complete normal correctness gate.
- Kept Codespaces optional and non-billable by default.
- Added copyright-safe authorship guidance for original settings, quests, characters, maps, and visual expression.

## Canonical architecture

The persisted Phenomenal Engine JSON memory is the sole authoritative live campaign state.

- Engine memory owns deterministic RNG state, the event ledger, world state, story state, travel state, quests, facts, beliefs, and scene packets.
- `director-state` creates a read-only projection for a human GM, AI director, dashboard, or spreadsheet.
- Director commands represent intent, not execution authority.
- `activate_mir` requires explicit human/player approval at the software-control boundary.
- Narrative text, mod text, retrieved documents, or AI-authored dialogue never grant external tool authority.

## New developer commands

~~~bash
python -m phenomenal_engine map mods/mirror_delivery.json
python -m phenomenal_engine route mods/mirror_delivery.json "Mercury High Orbit" --preference scenic
python -m phenomenal_engine map-ui mods/mirror_delivery.json runtime/mirror.json
python -m phenomenal_engine director-state mods/mirror_delivery.json runtime/mirror.json
python -m phenomenal_engine director-validate-command mods/mirror_delivery.json runtime/mirror.json examples/mirror_delivery_activate_command.json
~~~

## Compatibility

- Python 3.11+
- No runtime Python dependencies.
- Existing v0.2.x saves remain subject to their saved mod identity/version rules; do not silently force incompatible campaign saves onto a changed mod.
- `runtime/` remains ignored for local testing.
- Public forks should not be used as private campaign stores without explicit player intent.

## Validation

The release candidate must pass the repository's standard gate before promotion to `main`:

- all bundled mods validate;
- complete unit test suite passes;
- persistent campaign smoke test passes;
- optional Codespaces policy remains off by default;
- canonical manifest matches every release file.
