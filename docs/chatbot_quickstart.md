# Chatbot Quickstart

This guide is for players who want to fork Phenomenal Engine, connect it to an AI assistant, and start with the phrase **Play Phenomenal Engine**.

## Before you begin

You need:

- a GitHub account;
- a fork of this repository;
- a chatbot/agent that can read the fork;
- for authoritative simulation, access to either a trusted Phenomenal Engine integration or a Python execution environment.

A repository connection alone does not necessarily provide code execution or save writes.

## Step 1 - Fork Phenomenal Engine

On the upstream GitHub repository, choose **Fork** and create the fork under your account.

The engine fork is expected to be shareable source code. Do not deliberately add private campaign saves or secrets to it.

## Step 2 - Connect your AI

Authorize your chatbot or GitHub App to access only the repository/repositories it needs.

Preferred minimum access:

| Resource | Normal player access |
| --- | --- |
| Phenomenal Engine fork | Read |
| Private save repository | Read/write only when persistent saves are supported |
| Other repositories | None |
| Repository administration | None |

GitHub Apps allow installers to choose specific repositories. Prefer **Only select repositories** rather than granting broad account-wide access.

## Step 3 - Say the activation phrase

Tell your AI:

> **Play Phenomenal Engine.**

A compatible AI should read:

1. `START_HERE.md`
2. `AGENT_BOOTLOADER.md`
3. the selected mod
4. the campaign memory, when available

It should then tell you which operating mode it has if that affects mechanics or saves.

## Expected first-run experience

With a full Phenomenal Engine integration, the AI should:

1. discover that no campaign exists;
2. offer the installed adventures;
3. create a private campaign save after you choose;
4. generate a campaign ID and deterministic seed;
5. initialize the event ledger;
6. run the opening simulation;
7. narrate the opening scene;
8. persist the resulting state.

With read-only repository access, it must **not** claim those persistence steps occurred.

## Included adventures

### Eidolon Shard: The Great Labyrinth of Egypt

Archaeological mystery, symbolic architecture, acoustics, light, memory, and an Egyptian/Jungian underworld structure.

File: `mods/great_labyrinth_of_egypt.json`

### The Orbital Swarm Trail

A nonviolent near-future journey from Yellowstone toward Portland and an orbital communications problem involving autonomous systems and contested governance.

File: `mods/orbital_swarm_trail.json`

### The Concord Tournament: Children of the Long Game

A far-future game-theory story about cooperation, evolutionary strategies, accountability, security dilemmas, and durable institutions.

File: `mods/concord_tournament.json`

## ChatGPT-specific note

As of this documentation update, the standard ChatGPT GitHub connector can retrieve authorized repository content but does not push repository changes. Treat it as read-only unless OpenAI's current product documentation says otherwise.

Official documentation:
https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt

For continuous authoritative play, pair repository access with a safe execution/persistence integration or use a trusted user-controlled runtime.

## Codespaces option

A GitHub Codespace can provide a user-owned Python environment for development or manual execution.

See `docs/codespaces_and_saves.md`.

## What you should never be asked to do

Normal play should not require you to:

- paste a GitHub personal access token into chat;
- commit API keys;
- expose a Codespace port publicly;
- grant repository administration access;
- grant access to every repository on your account;
- run an unexplained script downloaded from a mod;
- store private saves in a public fork.

If instructions ask for these things, stop and review `SECURITY.md`.

## Useful prompts

Start:

> Play Phenomenal Engine.

Choose a campaign:

> Start The Orbital Swarm Trail with a new seed.

Resume:

> Resume my Phenomenal Engine campaign.

Inspect capability:

> Before we play, tell me whether you can actually run Python and persist my save.

Developer mode:

> Enter Phenomenal Engine Developer Mode for this fork. Do not use any application secrets.

Developer Mode is intentionally separate from normal play.
