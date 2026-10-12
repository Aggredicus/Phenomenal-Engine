# v0.7.0 — Complete Mirror Delivery campaign

- Added 25 scenes, 58 choices, 13 NPC conversation topics and six ending paths.
- Added persistent courier agreements, individual responses, faction standing,
  discovered evidence, crew decisions, rescues and optional investigation routes.
- Added typed campaign actions and read-only, hash-bound connected previews;
  authored checks accept explained preparation modifiers and safe alternatives.
- Added physical-share verification at Mercury, actual custody receipts,
  finite once-only mission rewards and consequence-specific epilogues.
- Added bounded, lossless archives for longer public ledgers, retaining every
  event and hash with compatibility in both save loaders.
- Kept sealed Mir silent and activation separate from typed scene/market prose.
- Older campaigns initialize the new layer only on their next executed turn;
  development leaves historical ledgers and live campaign saves untouched.

# v0.6.0 — Living station economies

- Added 9 station economies, 18 named vendors, 39 recurring job templates,
  12 item types and distinct Gate/Nacre exploration districts.
- Added bounded markets, stock/demand flows, scarcity/event/reputation prices,
  finite vendor budgets, cargo capacity, credits and daily crew provisioning.
- Added escrowed work/delivery quests, progress, deadlines, abandonment,
  once-only rewards and station reputation.
- Added paid inspections/refueling/repairs/cooling, owned-supply use, typed
  economic commands and immutable quote previews for connected gameplay.
- Added deterministic ongoing activity with logarithmic time catch-up,
  observer-safe station projections and Nacre Center travel aliases.
- Fixed historical event/sensory snapshot aliasing during in-memory turns.
- Old saves initialize documented resources before their next new action;
  development does not rewrite their campaign or advance a turn.

# v0.5.0 — Explicit action adjudication

- Added recorded character skills, explained challenge ratings and bounded,
  auditable situational modifiers.
- Added automatic routine task scopes, read-only odds previews, and distinct
  per-NPC checks with mixed/group outcomes.
- Connected turns now refuse missing assessments instead of silently using 50%.
- Success, margin and degree share one draw; automatic tasks preserve action
  RNG, and background hazard probability/draw are visible on the world stream.
- Added CLI/public-backend assessment inputs, retry assessment checks, schemas,
  examples, regression tests and migration documentation.
- Explicit task/skill assessments prevent incidental journey words from
  misclassifying service inquiries and diplomacy as travel.
- Historical v0.4 release publishers are manual-only so later version bumps
  do not automatically queue obsolete release jobs.
- Existing campaign ledgers remain intact; shops and service transactions are
  still separate unimplemented mechanics.

# Changelog

## 0.4.0 — 2026-10-07
- Added a JSON-first director interface: stable director-state projection, command schema, CLI export/validation, and tests for human/AI co-directing.
- Added a hard director-level approval gate for Mir activation; validation never executes commands and narrative text cannot grant software authority.
- Demoted Google Sheets from database to optional accessible adapter, with a current-spreadsheet-only Apps Script bridge and no Drive-wide access.
- Mirror Delivery now treats deliberate activation of Mir as an irreversible declarative choice: pristine status, trust, Mercury acceptance, and later story access change in authoritative state.
- Long interplanetary legs advance exact travel time but cap background simulation pulses to keep play responsive.
- Added an interactive loopback map UI: tap/focus previews destination, distance, time, legs, risk, and route modes; explicit Confirm Travel is required before movement.
- Travel now persists as an edge-by-edge journey so intermediate nodes can host encounters and interruptions; Continue, Reroute, and Cancel operate from the current node.
- Added authored physical route distances to Mirror Delivery; schematic screen coordinates are never treated as literal orbital distance.
- CI now runs once per pull request (plus direct `main` pushes), cancels superseded runs, uses a five-minute hard timeout, and keeps the full normal gate because it completes quickly.
- Codespace creation no longer blocks on the full unit suite; startup runs only lightweight mod validation while full tests remain in CI or explicit developer commands.
- Added persistent node-map travel with stable locations, route edges, travel time, risk, access metadata, and fastest/safest/scenic multi-hop pathfinding.
- Added discovered shortcuts, dynamic runtime locations/routes, persistent route overrides, and scene-packet map state.
- Travel time now advances living-world pulses so NPC agendas and world events can progress during longer journeys.
- Added `map` and `route` inspection commands plus persistent arbitrary-location travel topology.
- Added living-world story hierarchy, breadcrumb-to-quest promotion, NPC agendas, and campaign-local ethical player-experience adaptation.
- Replaced the Concord narrative with Mirror Delivery, a four-courier inner-system expedition built around a sealed high-capability AI payload, living-world choices, and hidden strategic mechanics.
- Added explicit copyright-safe authorship guidance for original settings, quests, characters, maps, and visual expression.

## 0.2.1
- Made GitHub Codespaces opt-in and disabled by default, with a once-per-setup optional suggestion and explicit cost disclosure.
- Added a non-billable `start` CLI command that lists adventures and returns runtime/Codespaces choices.
- Added `--codespaces` (manual instructions only) and `--no-codespaces` (skip offer), with tests guaranteeing no provisioning.
- Updated startup, chatbot, Codespaces, integration, and support documentation to prefer existing trusted Python execution.

## 0.2.0
- Added persistent `play` / `continue` CLI flow that creates or reloads a campaign, restores RNG streams, runs one turn, and atomically saves state.
- Added idempotency keys so retried agent/tool calls do not duplicate turns.
- Added `status` save verification and structured persistence metadata.
- New campaigns initialize characters, quests, state version, a genesis ledger event, and the last scene packet.
- Added write-capable chatbot/GitHub onboarding, least-privilege setup guidance, Codespaces configuration, and permanent CI.
- Added persistent campaign tests and manifest verification in CI.

## 0.1.0
- First packaged reference engine.
- Stable PCG32 streams and probabilistic mechanics.
- Physics/acoustics/light helpers and local wave demo.
- Persistent tamper-evident JSON memory.
- Per-turn image job protocol.
- Iterated Prisoner's Dilemma tournament and evolutionary memory-one demo.
- Three standardized adventure mods.
