# Changelog

## 0.2.1
- Made GitHub Codespaces opt-in and disabled by default, with a once-per-setup optional suggestion and explicit cost disclosure.
- Added a non-billable `start` CLI command that lists adventures and returns runtime/Codespaces choices.
- Added `--codespaces` (manual instructions only) and `--no-codespaces` (skip offer), with tests guaranteeing no provisioning.
- Updated startup, chatbot, Codespaces, integration, and support documentation to prefer existing trusted Python execution.

## 0.2.0
- Added persistent `play` / `continue` CLI flow that creates or reloads a campaign, restores RNG streams, runs one turn, and atomically saves state.
- Added idempotency keys so retried agent/tool calls do not duplicate turns.
- Added `status` save verification and structured persistence metadata.
- New campaigns initialize characters, quests, state version, a genesis ledger event, and the last scene packet.
- Added write-capable chatbot/GitHub onboarding, least-privilege setup guidance, Codespaces configuration, and permanent CI.
- Added persistent campaign tests and manifest verification in CI.

## 0.1.0
- First packaged reference engine.
- Stable PCG32 streams and probabilistic mechanics.
- Physics/acoustics/light helpers and local wave demo.
- Persistent tamper-evident JSON memory.
- Per-turn image job protocol.
- Iterated Prisoner's Dilemma tournament and evolutionary memory-one demo.
- Three standardized adventure mods.
