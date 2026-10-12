# Fast, tokenless connected-app turn path

## Goal

**Spend time playing, not waiting on infrastructure.** No user-provided GitHub personal access token, local installation on the player's device, Codespaces, dynamically generated GitHub Actions workflows, or per-turn full CI.

Two separate capabilities remain necessary:
- A trusted Python executor running the actual checked-out Phenomenal Engine source (can be ChatGPT-managed/cloud; **not** required on the player's device).
- The already authorized connected GitHub app for read/write operations, so Python needs **no** GitHub credential.

The **current GitHub connection does not itself provide Python execution**. This protocol is implemented and locally testable in CI, but automated chat-to-executor wiring is not deployed yet. Do not claim a simulated, published or resumed turn until its execution and remote readback are proven.

## Minimal turn protocol (existing campaigns)

| Stage | What happens | External GitHub calls |
|---|---|---|
| Immediate prelude | Present established facts from last verified observer-safe state, with no outcomes | 0 if scene already known |
| Load | Connected GitHub app reads the exact public campaign blob and SHA | 1 |
| Simulate | Host passes read JSON + expected SHA + action to Python turn_exchange in the **same trusted executor** | 0 |
| Commit | Connected GitHub app updates exactly the campaign file, passing original blob SHA for optimistic concurrency | 1 |
| Verify | Connected app fetches the committed file and compares saved bytes/blob SHA, session ID, state version, idempotency key and ledger | 1 |
| Reveal | Narrate the committed last-scene packet and invitation for the next action | 0 |

**Target: 3 campaign-content GitHub operations per turn** (one read, one conditional write, one readback). Authenticated identity, public visibility and scope checks remain necessary; this is not a license to cache security assertions indefinitely or skip consent.

In contrast, the legacy direct REST runner checks repo, branch and identity, then fetches, writes and refetches the save (up to 6 requests). A long-lived, approved connection can reduce repeated setup checks safely using provider-issued authorization; the host is responsible for that, not the game text.

## Exact computation-only Python interface

As of v0.5.0, new turns require an `adjudication` object in addition to the
fields below. See [Action adjudication](action_adjudication.md) and
`examples/diplomacy_assessment.json`. Use `operation: preview` to display the
prepared odds without RNG/state changes, then bind them on the proposal with
`expected_adjudication_sha256`. Authored deterministic rules need no override.
The proposal's `resolution` permits provisional math/progress output before
the GitHub commit; canonical consequences still require verified readback.

The executor receives a single JSON object on standard input; the mod is whitelisted and loaded from the trusted engine checkout:

~~~json
{
  "campaign_id": "mirror_delivery_20261011_fresh",
  "mod_id": "mirror_delivery",
  "expected_state_version": 1,
  "expected_blob_sha": "THE_40_HEX_SHA_FROM_VERIFIED_GITHUB_READ",
  "save_json": "EXACT_JSON_TEXT_FROM_THE_CONNECTED_GITHUB_READ",
  "action": "I review the other courier crews while I inspect the ship and prepare for departure.",
  "idempotency_key": "mirror_delivery_20261011_fresh-turn-002"
}
~~~

Invoke **the trusted Python executor**, not a player's local machine:

~~~bash
python -m phenomenal_engine.turn_exchange < request.json
~~~

It emits either:
- **proposal** with proposed compact state JSON, resulting blob SHA, and the *original* expected SHA; **persisted=false** and **remote_verified=false**, so the story outcome must not be narrated yet.
- **duplicate** with the scene already in the supplied source, no new write required; Python still returns persisted=false and the connected app must verify that source really came from GitHub before narration.
- **proposal_refused** for inconsistent metadata, stale revision, wrong mod, mismatched consent, invalid hash, tampered ledger or unsafe content.

The actual commit and verification are **GitHub connected-app operations**, not Python REST requests. Only after a successful conditional update with original SHA and readback of the new blob can the external orchestrator report a canonical \`scene_packet\` to narration.

The computation worker has **no GitHub credentials and no network dependency**. It does not write save files, alter the repo, create compute instances, run general shell commands from player text, or provision a Codespace. The authenticated connected GitHub app must separately enforce user identity, repository ownership/scope, destination visibility and affirmative consent.

## Save format optimization

The public backend uses compact UTF-8 JSON and stores the latest scene **only once** in the hash-chained event ledger. \`decode_state\` reconstructs \`last_scene_packet\` in memory. The legacy pretty-printed JSON remains supported; new writes upgrade the format losslessly, without rewriting or dropping the hashed event history.

Measured on the actual turn-1 public save:
- Original pretty JSON: **54,568 bytes**
- Compact only: **37,964 bytes** (30% smaller)
- Compact + derived last scene: **25,425 bytes** (53% smaller)

These are *payload* byte comparisons, not end-to-end latency measurements. JSON compression doesn't solve Python provisioning; actual latency improvement still depends on an approved hosted Python execution bridge.

## Runtime / UI priorities

1. Avoid a full mod/manifest read or test suite on every action. Engine source is loaded from the verified deployment; reload once when the engine version changes.
2. Keep the latest observer-safe packet available in memory in the chat so scene-setting can stream immediately.
3. Use one Python execution per consequential turn, never one process per game subsystem.
4. Use the existing GitHub connector for only one target campaign path. No broad repo searches, branch creation or workflow-file commits per turn.
5. Use idempotency keys and blob SHA comparison. On uncertain commit, refetch and reconcile before any reroll.
6. Never introduce fake progress timers; read-only prelude may be interleaved with genuine execution statuses and outcome only after verified persistence.
7. Defer pictures/optional world visualizations to after successful save; let the player respond while decorating noncanonical scene context if desired.

## Limits

The public save still includes cumulative event history and will grow with turn count. Removing *old* scene packets, compressing them further, or replacing the ledger with append-only shards needs a separate backwards-compatible migration and performance benchmark. Do not erase events or hashes simply to hit a payload target.
