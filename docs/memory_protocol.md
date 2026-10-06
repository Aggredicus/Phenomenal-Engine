# Persistent JSON Memory Protocol

## Goals

A long campaign needs more than an LLM context window. The save file is the canonical state.

### Facts vs beliefs
A sensor report is not a fact merely because it appeared in prose.

- `facts.revealed`: established truths available to the player.
- `beliefs`: uncertain hypotheses with confidence and provenance.
- hidden state remains in world/mod-specific state where the narrative agent cannot casually expose it.

### Event ledger
Every consequential turn receives:
- index,
- turn,
- kind,
- payload,
- previous event hash,
- current event hash.

The hash chain is tamper-evident, not cryptographic access control. It makes accidental silent rewriting detectable.

### RNG state
Each named random stream is saved. Replays can reproduce the same future so long as the same stream receives the same calls.

### Long-term consequences
A consequence should contain:
- cause event ID,
- affected entities,
- activation condition or due time,
- visibility,
- resolution state.

This is how a promise made on turn 12 can matter on turn 240.

### Summaries
Summaries are context compression, not canon. If summary text conflicts with the ledger or structured state, structured state wins.

## Recommended write cadence

Write the save atomically after every consequential player turn and after major autonomous world-clock changes.
