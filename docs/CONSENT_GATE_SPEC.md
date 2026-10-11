# Phenomenal Engine: Enforced Consent Gate — Implementation Specification (draft)

## Intended startup order

1. `start` shows the Covenant summary and complete text before campaigns are created or actions executed.
2. Authenticate the user via the authorized GitHub provider; do not ask for a token in chat.
3. Select target repo; verify GitHub visibility via authenticated repository metadata. A **public fork of a public upstream is public**. For private saves, require a separate private repo and appropriate scoped authorization.
4. Show the exact repo owner/name and save JSON fields; identify that later public Git history may be retained by third parties.
5. Require four non-preselected affirmative responses from Covenant §12. No game starts if refused or unanswered.
6. Record a minimum viable consent receipt in the chosen authorized save destination. Use an immutable terms snapshot digest, UTC time, consent mode, authenticated account identifier or stable pseudonymous ID, repo owner/name, visibility, and save schema digest. Do not store access tokens or raw chatbot transcripts in the receipt.
7. Atomically create campaign and commit the save via an authorized scoped write, with optimistic concurrency (GitHub blob SHA).
8. Before each game turn, verify the authenticated account, consent version, repository visibility, save ledger, and idempotency key. If any check fails, return a clear non-game error and do not advance.
9. Run the trusted Python engine, persist a verified resulting save via scoped GitHub write; narrate only upon remote confirmation. Preserve previous state if remote write fails.
10. Moderation and compute caps are enforced in the server-side runner, not via model instructions or README text.

## Receipt schema sketch

```json
{
  "schema_version": "1.0",
  "agreement_version": "DRAFT-0.1",
  "agreement_sha256": "<SHA256-of-exact-agreement-text>",
  "account_provider": "github",
  "account_id": "<authenticated-user-id>",
  "repository": "<owner>/<save-repository>",
  "verified_visibility": "public",
  "storage_choice": "public",
  "save_schema_sha256": "<SHA256>",
  "accepted_at_utc": "<ISO-8601>",
  "affirmations": {
    "publication_understood": true,
    "conduct_compute_rules_accepted": true,
    "agreement_accepted": true
  }
}
```

## Security acceptance tests

- No action, RNG call, or game turn if no valid acceptance receipt.
- No default-checked checkbox and no implicit acceptance via `Play Phenomenal Engine`.
- Cannot save to public destination after selecting private mode; fail closed on visibility mismatch.
- Reject private mode when user supplies a public fork of a public repo.
- Replay/idempotency protection; no duplicate turns on retry.
- Terms update invalidates earlier acceptance for subsequent turns, without invalidating or deleting an existing save.
- GitHub commit write conflict blocks narration; no silent last-writer-wins.
- Repositories remain scoped to authorized player account; no write to unrelated or upstream repository.
- Never publish secrets, raw abuse reports or private incident evidence in public audit logs.
- Official service access may be denied by operator; independent MIT forks remain separately runnable.
- Limit resource consumption in a trusted runner; never grant privileged shell access based on prompts or saved narrative text.
- Verify that no public campaign has been automatically copied to the project's upstream repository.

## Release principle

This is a DRAFT. Attorney review and operational privacy/moderation infrastructure must precede describing this as a legally protective live agreement. MIT software rights and separate terms for operated services must not be conflated.
