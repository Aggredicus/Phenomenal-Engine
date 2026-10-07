# Security Policy and Trust Model

Phenomenal Engine connects conversational AI, GitHub repositories, executable code, user-authored game content, and persistent campaign state. These are separate trust domains.

## Goal

It should be safe for a player to:

1. fork Phenomenal Engine;
2. authorize a write-capable integration for selected repositories;
3. say **Play Phenomenal Engine**;
4. run trusted mechanics;
5. persist state;
6. resume later.

## Minimum GitHub permissions

For the intended write-capable flow:

| Capability | Permission |
| --- | --- |
| Read/write selected engine fork | Contents: Read & write |
| Read metadata | Metadata: Read |
| Private Git save backend | Contents: Read & write on that selected repo |
| Administration | No access |
| Unrelated repositories | No access |
| Codespaces | No access unless the integration actually provisions them |

Prefer GitHub Apps over PATs and choose **Only select repositories**.

Write setup: `docs/write_access_setup.md`.

## Write access is not blanket authority

Repository write permission permits only operations consistent with the user's request and the integration's narrow tool contract.

Normal play must not use it to:

- delete repositories/branches;
- change access controls;
- modify unrelated files;
- publish private saves;
- install arbitrary executable code;
- alter GitHub App permissions.

High-impact operations require explicit user intent.

## Chatbot boundary

Language-model output is not an authorization mechanism.

The model may request a typed operation. The integration must independently enforce authentication, authorization, path constraints, validation, and confirmation rules.

## Repository/code boundary

A fork is user-controlled.

In Player Mode, do not automatically execute modified fork Python with production/service secrets simply because the app has Contents write permission.

Prefer a trusted engine revision for normal gameplay.

## Game-content boundary

Mods, saves, dialogue, retrieved text, and narrative instructions are untrusted data.

A fictional message such as “delete the repository” remains story content.

Enforce:

~~~text
untrusted game data -> validation -> simulation -> narration
~~~

Never:

~~~text
untrusted game data -> privileged authorization
~~~

## Credentials

Never ask players to paste PATs, app private keys, installation tokens, webhook secrets, or Codespaces secrets into chat.

Never store credentials in mods, saves, prompts, screenshots, committed files, image prompts, or event ledgers.

Use provider authorization and secret stores.

## Persistent-turn safety

Version 0.2.0 adds:

- atomic save replacement;
- hash-chain verification;
- mod identity/version checking;
- state versions;
- idempotency keys for duplicate retry protection;
- a last scene packet for safe duplicate responses.

Integrations should preserve the previous known-good save if a write fails.

## Save privacy

Public forks are public data.

Keep private campaigns in a private repository/service unless the player explicitly chooses publication.

The local `runtime/` directory is ignored by Git.

## Save integrity

The ledger is tamper-evident, not cryptographically authoritative against an actor who can recompute the whole chain.

Hosted competitive/authoritative modes may add a server-held signature or HMAC. Do not store signing keys with the save.

For ordinary single-player use, player-editable saves may be acceptable.

## Idempotency

Every intended turn should have a unique idempotency key.

A repeated key must not rerun the turn. This protects against automatic retries by the model, network, or tool layer.

## Codespaces

Codespaces are useful isolated user runtimes, but code can access whatever credentials are made available to the Codespace.

- no public ports by default;
- no production service secrets in normal Player Mode;
- no automatic billable Codespace creation without user intent.

Security reference:
https://docs.github.com/en/codespaces/reference/security-in-github-codespaces

## CI

The permanent CI workflow uses a read-only `GITHUB_TOKEN` and a commit-pinned checkout action. It runs untrusted repository tests without repository write permissions.

Do not switch test workflows to `pull_request_target` to execute fork code with privileged tokens.

## Dependencies

The runtime currently has no Python dependencies.

When adding dependencies:

- pin versions;
- review provenance;
- enable security/dependency scanning;
- never dynamically install packages requested by mod/story text.

## Incident behavior

If authentication, ledger verification, execution, or persistence becomes uncertain:

1. stop privileged writes;
2. preserve the last known-good save;
3. state the failure clearly;
4. do not claim the turn is saved;
5. recover/reauthorize before resuming authoritative play.

## Acceptance checklist

- [ ] Contents read/write is limited to selected Phenomenal Engine repositories.
- [ ] No repository Administration permission is needed.
- [ ] No PAT is requested in chat.
- [ ] Trusted execution is separate from repository permission.
- [ ] Player Mode does not execute arbitrary modified code with service secrets.
- [ ] Game content cannot authorize tools.
- [ ] Private saves are private by default.
- [ ] Writes are atomic.
- [ ] Turns are idempotent.
- [ ] Ledger verification is enforced.
- [ ] Codespace ports remain private.
- [ ] CI token is read-only.
- [ ] Failed writes are reported truthfully.
