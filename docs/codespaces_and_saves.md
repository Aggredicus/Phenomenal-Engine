# Optional Codespaces and Saves

**Codespaces is opt-in.** Phenomenal Engine does not automatically create or start a Codespace when a player says "Play Phenomenal Engine." The normal route uses an existing trusted Python runtime.

GitHub offers limited included Codespaces usage. Exceeding the allowance can incur compute and storage charges. Review your plan, remaining usage, and spending limits before starting one:
https://github.com/pricing

Phenomenal Engine includes a ready-to-use GitHub Codespaces configuration at `.devcontainer/devcontainer.json`, but this file is used **only when the user deliberately creates a Codespace**.

Codespaces is a convenient **user-controlled Python execution surface**. It is not, by itself, the long-term private save database.

## When the option should be suggested

At the first game startup the AI should mention Codespaces once as an optional advanced workspace and offer to skip it. Choosing "no" must not change the ability to play using a separate trusted runtime.

If the user chooses Codespaces, the CLI `python -m phenomenal_engine start --codespaces` returns manual instructions; it does not provision infrastructure. The player must deliberately create the Codespace through GitHub, or later approve a supported provisioning integration after reviewing costs.

## Start a Codespace (only after opt-in)

From your fork, choose **Code -> Codespaces -> Create codespace**.

The container uses Python 3.12 and automatically runs only the lightweight startup validation:

~~~bash
python -m phenomenal_engine validate mods
~~~

The full unit suite is intentionally **not** a blocking Codespace creation step. GitHub CI runs it on pull requests and `main`; developers can still run it explicitly with:

~~~bash
python -m unittest discover -s tests -q
~~~

This keeps interactive startup fast while preserving the full correctness gate where it belongs. No ports are forwarded by default.

## Start a persistent campaign

~~~bash
python -m phenomenal_engine play \
  mods/mirror_delivery.json \
  runtime/mirror.json \
  "Inspect the sealed Mir vault." \
  --seed "my-campaign" \
  --idempotency-key opening-1
~~~

Continue:

~~~bash
python -m phenomenal_engine play \
  mods/mirror_delivery.json \
  runtime/mirror.json \
  "I ask Juno about the other couriers." \
  --idempotency-key turn-2
~~~

Inspect:

~~~bash
python -m phenomenal_engine status runtime/mirror.json
~~~

## Persistence warning

`runtime/` is ignored by Git to prevent accidental publication. The file survives ordinary Codespace stops, but deleting the Codespace can remove uncommitted local state.

For durable campaign persistence, copy/synchronize saves to a designated private repository or private save service.

## Write-capable chatbot + Codespace

A write-capable GitHub connection and a Codespace solve different problems:

- GitHub write access: authorized repository mutations/persistence;
- Codespace: Python execution.

A production integration can combine them, but should expose narrow game operations rather than a generic credentialed shell.

## Performance policy

Interactive play must not wait for repository CI, benchmark sweeps, or heavyweight simulation validation.

Use three levels:

1. **Player startup** — no CI wait; load validated game state and play.
2. **Codespace startup** — cheap structural/mod validation only.
3. **PR/main CI** — complete normal test suite and persistence/integrity checks.

Long-running soak tests, broad seed sweeps, profiling, or release qualification should be invoked only when a specific engineering question justifies the extra wait.

## Security

- Keep forwarded ports private.
- Do not put PATs or production service secrets in the fork.
- Use Codespaces secrets only when genuinely needed for development.
- Do not execute unreviewed user-modified engine code with privileged service credentials.
- Do not auto-create or auto-start Codespaces merely because a repo was connected or the player started a campaign.
- Do not assume included monthly usage is unlimited.
- Respect a player's "skip" choice for the current setup; do not repeat the suggestion during every turn.

GitHub security guidance:
https://docs.github.com/en/codespaces/reference/security-in-github-codespaces
