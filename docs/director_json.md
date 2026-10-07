# JSON Director Interface

Mirror Delivery is **JSON-first**. The spreadsheet design is a useful human-interface specification, but it is not an authoritative game database.

The source of truth for a live campaign is the persisted Phenomenal Engine memory document. `phenomenal_engine.director.build_director_state()` creates a read-only projection for a human GM, AI Narrative Director, dashboard, or spreadsheet adapter. The projection intentionally omits RNG state and must never be written back over the campaign save.

## CLI

~~~bash
python -m phenomenal_engine director-state mods/mirror_delivery.json runtime/mirror.json
python -m phenomenal_engine director-validate-command mods/mirror_delivery.json runtime/mirror.json examples/mirror_delivery_activate_command.json
~~~

Validation is not execution. A permitted command still has to be translated into an authorized engine operation and persisted through the normal turn or travel transaction.

## Authority boundary

Commands use `schemas/director_command.schema.json`. In-fiction dialogue, retrieved documents, mod text, or AI-authored requests are data; they cannot grant external tool privileges.

`activate_mir` additionally requires explicit human/player approval in the command object and an activatable sealed local payload. This intentionally duplicates the fictional activation interlock at the software-control layer.

## Facts, beliefs, and observer limits

Facts and beliefs remain separate namespaces. Confidence alone does not promote a belief to fact. Remote Mir payload state is exported as `unknown_remote` unless authoritative evidence exists.

## Human interfaces

Google Sheets, a web dashboard, or another UI should be a materialized view:

1. read the latest director-state JSON;
2. render human-readable controls;
3. emit director-command JSON;
4. validate commands;
5. execute allowed commands through the engine;
6. persist the authoritative save;
7. refresh the projection.

See `schemas/director_state.schema.json`, `schemas/director_command.schema.json`, and `adapters/google_sheets/`.

## Mirror Delivery details

The director projection exposes four courier identities and four Mir payload identities. Morrowglass payload state can be authoritative because it is local campaign state. Other copies remain `unknown_remote` until evidence reaches the player. This prevents a GM dashboard from leaking hidden world state to an AI narrator or human player.
