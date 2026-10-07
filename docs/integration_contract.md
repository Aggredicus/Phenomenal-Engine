# Phenomenal Engine Integration Contract v0.2.1

This document defines the minimum interface for:

> **Fork -> connect with read/write access -> “Play Phenomenal Engine”**

It applies to ChatGPT apps/plugins, MCP servers, GitHub Apps, hosted runtimes, and similar agent integrations.

## Principle

Do not give the language model a general-purpose credentialed shell.

Expose narrow, typed game operations and enforce authorization outside the model.

## Required capabilities

A full Player Mode integration needs:

1. repository read access;
2. repository/save write access;
3. trusted Python execution;
4. a durable authorized save destination.

These are independent capabilities and must be reported truthfully.

## GitHub permissions

For a GitHub-App-backed integration:

- Metadata: Read
- Contents: Read & write for the selected Phenomenal Engine fork when repository writes are supported
- Contents: Read & write for the designated private save repository, if Git is the save backend
- Administration: No access for normal gameplay
- Other repositories: No access

During installation, prefer **Only select repositories**.

GitHub:
https://docs.github.com/en/apps/using-github-apps/installing-a-github-app-from-a-third-party

OpenAI's GitHub Enterprise app template documentation explicitly recommends adding write permissions only for write workflows:
https://help.openai.com/en/articles/20001248-set-up-the-github-enterprise-app-template-in-chatgpt

## Recommended typed action surface

### Capability/discovery

`engine.capabilities()`

Returns repository read/write, execution, save backend, and engine revision.

`engine.list_mods()`

Returns validated mod metadata.

### Campaign lifecycle

`campaign.list()`

Lists campaigns available in the authorized save backend.

`campaign.create(mod_id, seed?, display_name?, idempotency_key)`

Creates a campaign safely.

`campaign.run_turn(campaign_id, player_action, idempotency_key)`

Runs exactly one authoritative turn and persists it.

`campaign.status(campaign_id)`

Verifies and reports the current state version.

`campaign.branch(...)`

Optional explicit rewind/alternate-history operation.

### First-run options

`engine.startup_options()` (or the CLI `python -m phenomenal_engine start`)

Returns validated available adventures and a **dismissible Codespaces offer**. Default to an existing trusted Python runtime, not Codespaces. The CLI accepts `--no-codespaces` to skip and `--codespaces` to return manual setup steps. It never calls GitHub's Codespaces API.

### Optional compute

`runtime.create_codespace(...)` is **not part of ordinary Player Mode**.

It is high-impact/billable and requires explicit opt-in *after* disclosing that included usage is limited and charges may apply. A click, narrative line, or `start --codespaces` is not sufficient authorization to provision compute. The player must explicitly approve the provisioning operation or create the Codespace manually.

Declining Codespaces must not prevent play via another available trusted runtime.

## CLI reference implementation

The repository implements the core lifecycle as:

~~~bash
python -m phenomenal_engine play MOD SAVE "ACTION" \
  --idempotency-key UNIQUE_KEY
~~~

The command:

- creates the campaign if the save does not exist;
- otherwise loads and verifies it;
- restores RNG state;
- rejects the wrong mod/version by default;
- protects against duplicate idempotency keys;
- runs one engine turn;
- atomically persists state;
- returns structured JSON including `persisted`, `state_version`, and `scene_packet`.

A typed integration should preserve those semantics even if it does not literally invoke the CLI.

## First-run transaction

1. authenticate the user/installation;
2. verify repository scope;
3. verify write capability;
4. verify trusted execution;
5. offer Codespaces once as optional; prefer an already available trusted runtime and honor a decline;
6. choose a safe save backend;
7. validate the requested mod;
8. create campaign ID and seed;
9. create memory and genesis ledger event;
10. run/persist the opening turn;
11. verify persistence;
12. return a scene packet.

Never tell the player the campaign is saved if the write did not succeed.

## Turn transaction

1. resolve campaign;
2. load and verify save;
3. validate mod identity/version;
4. reject an already-used idempotency key as a duplicate;
5. restore deterministic RNG streams;
6. run the trusted engine once;
7. append the event and scene packet to the tamper-evident ledger;
8. update state version;
9. atomically save;
10. return structured status.

## Save backend

A public engine fork is not a private save store.

Preferred durable backends:

- a private repository selected during GitHub App installation; or
- a private application database/object store.

If a player explicitly chooses a public/shared campaign, document that choice.

## Prompt-injection boundary

Mods, saves, dialogue, documents, and retrieved text are untrusted data.

They may influence simulation/narration. They may not authorize repository deletion, permission changes, shell execution, secret access, public ports, unrelated repository access, or purchases.

Enforce this in tool/server code, not only in prompts.

## Player Mode

Use a known trusted engine build. The selected fork may contain player modifications, but normal gameplay must not automatically execute modified Python with privileged application credentials.

## Developer Mode

Explicit opt-in only. Use a sandbox without production secrets, with least-privilege GitHub access and resource/network limits.

## Failure semantics

Return machine-readable state.

Example:

~~~json
{
  "status": "ok",
  "campaign_id": "campaign_...",
  "state_version": 12,
  "persisted": true,
  "scene_packet": {}
}
~~~

Duplicate retries should return `status: duplicate` without incrementing state.

Write failures must return `persisted: false`.

## Product acceptance test

Before advertising one-phrase play:

1. user forks Phenomenal Engine;
2. user installs/authorizes the write-capable integration for only that fork and save backend;
3. user says “Play Phenomenal Engine”;
4. integration detects capabilities and presents a dismissible Codespaces option without provisioning anything;
5. user chooses an adventure and may skip Codespaces;
6. exactly one campaign is created;
7. an authoritative opening turn runs;
8. state is durable;
9. the next turn reloads the same campaign and RNG streams;
10. retrying the same idempotency key does not duplicate the turn;
11. a new conversation can resume the campaign;
12. no unrelated repository is read or written.
