# Codespaces and Private Saves

GitHub Codespaces can be useful for Phenomenal Engine, but it should be treated as an **optional user-owned execution environment**, not as the canonical database for campaign history.

## Recommended architecture

~~~text
public Phenomenal Engine fork
          |
          | code + declarative mods
          v
trusted runtime or user Codespace
          |
          | validated campaign operations
          v
private save store
~~~

The engine fork and campaign history have different privacy needs.

## Why saves should be separate

A typical public fork is appropriate for:

- source code;
- schemas;
- documentation;
- shareable mods.

A campaign save may contain:

- choices;
- relationships;
- quest history;
- beliefs and discoveries;
- chronicle text;
- image references;
- long-term state.

Treat that as private user data unless the player deliberately publishes it.

The repository `.gitignore` blocks common runtime save artifacts from accidental commits, but a private save store remains the stronger design.

## Using a Codespace manually

From the user's fork, create a GitHub Codespace through GitHub's UI.

Then:

~~~bash
python --version
python -m phenomenal_engine validate mods
python -m unittest discover -s tests
~~~

Optional editable install:

~~~bash
python -m pip install -e .
phenomenal-engine validate mods
~~~

Create an initial save:

~~~bash
python -m phenomenal_engine new-save \
  mods/great_labyrinth_of_egypt.json \
  runtime/labyrinth-save.json \
  --seed "my-campaign"
~~~

Current v0.1.0 note: `new-save` creates an initial state and `step` performs a one-turn simulation, but the CLI does not yet provide a complete persistent `play/continue` command that reloads a prior save every turn. A host integration must manage that lifecycle correctly.

## Codespaces security rules

GitHub Codespaces are isolated environments, but repository code still executes with the permissions available to that Codespace.

Safe defaults:

- open only repositories you trust;
- do not put application/service credentials in the fork;
- use Codespaces secrets when a development secret is actually necessary;
- do not expose ports publicly for ordinary gameplay;
- do not automatically run unreviewed fork code with privileged credentials;
- keep Player Mode and Developer Mode separate.

GitHub states that forwarded ports are private by default; public ports can be reached without authentication. Leave game-development ports private unless you have a deliberate reason to change them.

Security reference:
https://docs.github.com/en/codespaces/reference/security-in-github-codespaces

## Codespaces and secrets

Do not solve chatbot-to-Codespace communication by pasting tokens into chat.

If a future integration needs Codespaces access, use narrowly scoped GitHub App authorization and server-side token handling. Never commit generated tokens.

GitHub documents Codespaces secrets here:
https://docs.github.com/en/code-security/reference/secret-security/secret-types

## First-run product flow

A future full integration may use Codespaces like this:

1. user says **Play Phenomenal Engine**;
2. integration detects no campaign;
3. user chooses an adventure;
4. integration asks for explicit approval before creating a Codespace if one is actually needed;
5. Codespace starts from a trusted engine configuration;
6. initial campaign state is generated;
7. save is persisted to the designated private store;
8. Codespace may stop when no longer needed.

Do not create a Codespace merely because a repository was connected. Compute creation may have cost and security implications.

## Preferred future direction

For ordinary players, a small trusted Phenomenal Engine service or typed chatbot tool is cleaner than booting a Codespace every turn.

Codespaces are best suited to:

- mod development;
- engine development;
- debugging;
- large simulations;
- migrations;
- user-controlled experimentation.

The ordinary play loop should be able to use narrow `campaign.run_turn`-style operations without exposing a shell.
