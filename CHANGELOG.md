# Changelog

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
