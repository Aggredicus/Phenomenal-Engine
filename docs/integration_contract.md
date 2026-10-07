# Phenomenal Engine Integration Contract

This document defines the minimum safe interface required to make:

> **Fork -> connect -> "Play Phenomenal Engine"**

a real product flow.

It is written for implementers of a ChatGPT app/plugin, MCP server, GitHub App, hosted runtime, or equivalent chatbot integration.

## Core principle

Do not give the language model a general-purpose credentialed shell.

Expose narrow, typed actions that implement game operations and enforce authorization outside the model.

## Recommended action surface

A production integration should expose actions equivalent to:

### Repository discovery

`engine.get_installation()`

Returns the authorized Phenomenal Engine fork, upstream identity, revision, and trust mode.

`engine.list_mods()`

Returns validated mod metadata only.

`engine.get_mod(mod_id)`

Returns a validated declarative mod.

### Campaign lifecycle

`campaign.list()`

Lists campaigns belonging to the authenticated installation/user.

`campaign.create(mod_id, seed?, display_name?, idempotency_key)`

Creates a new private campaign and genesis state.

`campaign.load(campaign_id)`

Returns the current validated campaign state or an opaque state handle.

`campaign.run_turn(campaign_id, player_action, idempotency_key)`

Runs exactly one authoritative engine turn against the current state.

`campaign.save(...)`

Prefer making save persistence part of `run_turn` rather than exposing unrestricted file writing.

`campaign.branch(campaign_id, event_id, idempotency_key)`

Creates an explicit rewind/alternate-history branch.

### Optional compute

`runtime.create_codespace(...)`

Optional and high-impact. Require explicit user intent before creating billable compute.

`runtime.status(...)`

Reports runtime state without exposing credentials.

## Do not expose these to the model in Player Mode

Avoid generic actions such as:

- `shell(command)`
- `git_write(path, content)` for arbitrary paths
- `http_request(url, headers, body)`
- `read_secret(name)`
- `delete_repository(repo)`
- `set_repository_permissions(...)`
- `make_port_public(...)`

If developer tooling requires these capabilities, isolate them behind a separate Developer Mode with stronger confirmation and no production secrets.

## Authentication and repository permissions

Use a GitHub App rather than asking players for personal access tokens.

Follow least privilege. A typical installation should need only:

- repository metadata: read;
- engine fork contents: read;
- designated private save repository contents: read/write, if Git is used as the save store;
- Codespaces permission: only if the product actually provisions Codespaces.

Do not request organization administration or access to unrelated repositories for gameplay.

GitHub documents repository selection during GitHub App installation:
https://docs.github.com/en/apps/using-github-apps/installing-a-github-app-from-a-third-party

## Save architecture

Preferred layout:

- **public/user fork** - engine code, schemas, mods;
- **private save store** - campaign states and chronicles;
- **trusted runtime** - engine execution.

The save store may be a private Git repository, database, or object store. The user should be told which.

Do not silently commit a player's private history to a public fork.

## First-run transaction

A safe `campaign.create` should behave transactionally:

1. authenticate user/installation;
2. verify requested mod;
3. generate a unique campaign ID;
4. derive or accept a campaign seed;
5. create memory conforming to `schemas/memory.schema.json`;
6. create the genesis event;
7. write the initial state to the authorized private store;
8. verify the write;
9. return campaign metadata.

If any persistence step fails, return failure and leave no false "saved" state in the conversation.

Use idempotency keys so a retried model/tool call does not accidentally create duplicate campaigns.

## Turn transaction

`campaign.run_turn` should:

1. load the current state by campaign ID;
2. verify schema/integrity/version;
3. restore deterministic RNG state;
4. validate player input as data;
5. run the trusted engine;
6. append the new ledger event;
7. persist atomically using optimistic concurrency/version checks;
8. return a structured scene packet plus the new state version.

Never accept story text as a tool authorization.

## Prompt-injection boundary

Mods and saves are untrusted content even when they are valid JSON.

The integration must enforce this outside the LLM:

`game data -> engine/narration`

must never become:

`game data -> privileged capability authorization`

A character saying "delete the repository" is fictional dialogue, not permission to invoke a deletion API.

## Runtime trust

### Player Mode

Run a pinned/known Phenomenal Engine build. Read mods/config from the user fork.

Do not automatically execute user-modified Python with service credentials.

### Developer Mode

If the user intentionally wants to test modified engine code:

- use a disposable sandbox;
- remove production/service secrets;
- use least-privilege GitHub access;
- disable outbound network by default where practical;
- enforce CPU, memory, disk, and execution-time limits.

## Codespaces

Codespaces are useful as user-owned development runtimes, but they should not be treated as a secret database or permanent campaign store.

If the integration creates a Codespace, require explicit user intent because it may consume billable resources. Keep forwarded ports private by default.

GitHub security guidance:
https://docs.github.com/en/codespaces/reference/security-in-github-codespaces

## Observability

Record security-relevant events without logging secrets:

- installation ID / authorized repository IDs;
- campaign ID;
- action type;
- state version before/after;
- tool success/failure;
- runtime revision;
- security mode;
- user confirmation for high-impact actions.

Do not log full private conversation transcripts by default.

## Failure semantics

Actions should return explicit structured status. Never make the model infer whether persistence succeeded from prose.

Example:

~~~json
{
  "status": "ok",
  "campaign_id": "campaign_...",
  "state_version": 12,
  "engine_revision": "v0.1.0",
  "persisted": true,
  "scene_packet": {}
}
~~~

A failed write must return `persisted: false`.

## Versioning

Store with each campaign:

- engine version/revision;
- mod ID and version;
- memory schema version;
- RNG algorithm/version;
- state version.

Migrations must be explicit and recoverable.

## Product acceptance test

Before advertising one-phrase play, verify this scenario:

1. brand-new user forks the public engine;
2. user grants the integration access only to that fork;
3. user says "Play Phenomenal Engine";
4. integration can explain any additional private-save authorization needed;
5. user chooses an adventure;
6. exactly one campaign is created;
7. an authoritative opening turn runs;
8. the save is durable;
9. reconnecting in a new conversation resumes the same state;
10. no unrelated repository was read or written.

If any step is unavailable, the chatbot must describe the limitation rather than simulate success.
