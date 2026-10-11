# Public GitHub Campaign Saves (opt-in developer integration)

**Destination:** public repository **Aggredicus/Phenomenal-Engine**, dedicated public branch **campaign-saves**, path **campaigns/<campaign-id>.json**. Installing the feature does not create a campaign or publish a save.

**Status:** Python/REST integration for a trusted existing runtime, not a hosted autonomous chatbot service. The [Player Covenant](PLAYER_COVENANT.md) remains a legal-review draft. Codespaces stays disabled and is not required.

## Exact public save disclosure

An authoritative campaign JSON includes:
- Player/character identity; character records; relationships; mod identity/version.
- Player actions, random outcomes, scene packets, chronicle and event-ledger history.
- World, story, quest, belief, facts (including hidden facts), travel, and consequence state.
- Master seed, PCG32 RNG streams, event hashes, idempotency keys and image-job records.
- Session ID, turn/state version, timestamps, summaries, GitHub publication destination and Covenant digest.

The complete ChatGPT transcript, credentials such as GITHUB_TOKEN, and the local consent receipt are **not automatically included**. Do not supply personal secrets or private third-party information as in-game actions. The basic secret scanner is not complete. Public Git history and third-party copies may remain available after deleting a save.

## Optimized connected-app alternative (no player token or local installation)

If a trusted server-side Python executor is available, prefer [fast tokenless turns](fast_tokenless_turns.md) instead of using a player-provided GitHub token. The already authenticated connected GitHub app handles save reads/conditional writes/readback; Python only computes the next state, in memory. The new public format stores the verified last scene in its ledger once and reconstructs last_scene_packet when loading older or newer files. **This code does not currently connect an autonomous Python runtime to ChatGPT; do not claim it is live until verified.**

## Technical prerequisites

1. Use Python 3.11+ in an already trusted runtime with the repository checked out. Do not run untrusted Python/mods with privileged credentials.
2. Set the **GITHUB_TOKEN environment variable locally**, using a narrowly scoped GitHub **user** token with Contents read/write permissions for this repository. Never paste tokens in chat or commit them. The authenticated account's login must match the locally consented account ID.
3. The dedicated campaign-saves branch must already exist. Its gameplay commits do not trigger normal main-branch CI.
4. GitHub API must independently confirm the target repository remains PUBLIC, the branch exists, and the account identity matches.

## Preview first — no save or publication

Select an adventure and a fresh lowercase campaign ID. Mirror Delivery below is only an example; do not automatically select it for the player.

~~~bash
python -m phenomenal_engine.github_saves preview pilot_one mods/mirror_delivery.json
python -m phenomenal_engine covenant --full
~~~

This prints the exact GitHub destination, top-level field names and current Covenant version + SHA-256 digest without simulating or publishing a turn.

## Player's required independent consent

Before *any* new public campaign is saved, the player must actively select PUBLIC storage and affirm each separate item (never preselected):

1. **Publication understanding:** public data can be searched, copied and retained, even after deletion; I will not enter secrets or private third-party information.
2. **Conduct/compute:** I accept participation and compute-use rules; independent infrastructure authorization may incur charges.
3. **Agreement acceptance:** I reviewed and accept the displayed Covenant review-draft version and exact SHA-256 digest; material changes require renewed consent.
4. **Adult eligibility:** I affirm I am 18 or older.

The player must explicitly run the acknowledgment after reviewing the full draft, replacing YOUR_GITHUB_LOGIN with their GitHub login:

~~~bash
python -m phenomenal_engine accept-covenant runtime/pilot_one.json \
  --account-id YOUR_GITHUB_LOGIN \
  --repository Aggredicus/Phenomenal-Engine \
  --visibility public --storage-choice public \
  --publication-understood --rules-accepted --agree --adult
~~~

The consent receipt is stored **locally only** under runtime/pilot_one.json.consent.json (Git-ignored). This CLI asserts rather than authenticates acceptance. The GitHub bridge separately checks the actual authenticated user and repository visibility before any PUT.

After a **separate first-publication confirmation**, run:

~~~bash
python -m phenomenal_engine.github_saves play pilot_one \
  mods/mirror_delivery.json \
  "I request a predeparture briefing." \
  --idempotency-key opening-pilot-one-001 \
  --confirm-first-publication
~~~

Subsequent turns:

~~~bash
python -m phenomenal_engine.github_saves play pilot_one \
  mods/mirror_delivery.json \
  "I inspect the manifest." \
  --idempotency-key pilot-one-002
~~~

Status without playing:

~~~bash
python -m phenomenal_engine.github_saves status pilot_one
~~~

A new action gets a new idempotency key. Duplicate keys return the stored scene without advancing. GitHub blob SHAs provide optimistic concurrency; a race or failed write blocks canonical new narration. The Python engine is executed in memory, then the commit must succeed and be fetched back with matching bytes before reporting persisted=true, remote_verified=true.

## Resuming across conversations

The public save is at this pattern:
https://github.com/Aggredicus/Phenomenal-Engine/blob/campaign-saves/campaigns/pilot_one.json

A new chat can read it using GitHub tools, but a write-capable connection **does not execute Python**. The next authentic turn still needs a trusted engine execution surface and a consent receipt in that runtime. Receipt files are not publicly committed, so a fresh runtime requires a new explicit acceptance before further publication.

## Safeguards and limitations

- Missing/changed consent, incorrect repository or visibility, GitHub identity mismatch, missing token, invalid campaign ID, unverified commits, invalid ledger, mismatched mod/version and conflicting writes all block completion.
- First publication requires both a consent receipt and --confirm-first-publication.
- Only Aggredicus/Phenomenal-Engine, public campaign-saves, and campaigns/<slug>.json are supported.
- No Codespace is provisioned; no GitHub credential is written into the campaign JSON.
- This is not yet an official hosted public-service rollout. Attorney review, privacy notices, provider-attested consent receipts and a secure ChatGPT execution bridge remain separate future work.
