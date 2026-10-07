# Chatbot Quickstart

Phenomenal Engine v0.2.1 is designed for the flow:

> **Fork -> connect a write-capable AI -> say “Play Phenomenal Engine.”**

## 1. Fork

Fork the public Phenomenal Engine repository into your GitHub account.

## 2. Connect

Authorize your AI integration to the selected fork.

For the intended experience, repository writes require **Contents: Read & write** on the selected repository. Prefer **Only select repositories** during GitHub App installation.

See `docs/write_access_setup.md`.

If you want durable private campaign saves in Git, also authorize a designated **private** save repository with Contents read/write.

## 3. Ensure there is an execution surface

GitHub read/write access does not itself run Python.

**Codespaces is optional and off by default.** Prefer an already available execution environment:

- the Phenomenal Engine runtime integration, when available;
- a chatbot/agent/work environment that can execute Python;
- local Python 3.11+;
- GitHub Codespaces **only if you opt in**.

Codespaces has limited included usage and may incur charges for compute/storage. You do not need it if another trusted Python environment is available. Connecting a fork never creates a Codespace.

## 4. Start

Say:

> **Play Phenomenal Engine.**

The AI should read `START_HERE.md` and `AGENT_BOOTLOADER.md`.

If there is no campaign, it should offer:

1. Eidolon Shard: The Great Labyrinth of Egypt
2. The Orbital Swarm Trail
3. Mirror Delivery

It should also make this single **optional** suggestion during first-run onboarding:

> Want to use GitHub Codespaces for development or heavy simulations? It's optional; GitHub's included usage is limited and additional charges may apply. We can use an existing Python runtime instead.

Saying **No** skips Codespaces without penalty. Saying **Yes** only opens manual setup guidance and **does not automatically create a Codespace**.

A trusted runtime can expose the startup choices using:

~~~bash
python -m phenomenal_engine start
python -m phenomenal_engine start --no-codespaces
python -m phenomenal_engine start --codespaces
~~~

None of these commands provisions infrastructure.

## What should happen mechanically?

A full integration should call the equivalent of:

~~~bash
python -m phenomenal_engine play MOD SAVE "PLAYER ACTION" \
  --idempotency-key UNIQUE_TURN_ID
~~~

The engine creates the save on the first turn and reloads it on later turns.

The AI should narrate only after the command/tool returns a successful `scene_packet` and confirms persistence.

## Resume later

Say:

> **Resume my Phenomenal Engine campaign.**

A compatible integration should locate the authorized campaign, verify its ledger, and continue from the same state.

## Capability check

If unsure, say:

> Before we play, verify whether you can read and write my Phenomenal Engine repository and whether you can actually execute Python.

The AI should report those as separate capabilities.

## Privacy

Public forks are not private campaign stores. For private play, keep durable save state in a private repository/service.

Local Codespace tests may use `runtime/`; it is ignored by Git.

## Safety expectations

Normal play should never require:

- a PAT pasted into chat;
- repository Administration permission;
- access to unrelated repositories;
- public Codespaces ports;
- arbitrary scripts requested by a mod;
- secrets committed to Git.

See `SECURITY.md`.
