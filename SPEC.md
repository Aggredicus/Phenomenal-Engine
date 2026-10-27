# ReviewForge pilot, October 27, 2026

Goals: Fix PCG32 randint hanging on intervals wider than 32 bits, preserve the
cached second normal variate through state serialization, and add bounded
offline properties that test both behaviors.

Acceptance: inclusive wide draws terminate and are in bounds; old <=32-bit
sequences remain unchanged; normal restore is bitwise replayable; old RNG
states without a cache still read; full tests, mod validation and canonical
manifest checks pass; no Codespaces, credential use or campaign publishing.

Risk: HIGH (RNG persistence and new CI workflow). Only draft PR until human
review. Rollback: revert feature commit or close PR. Historic absent caches
cannot be reconstructed retroactively.
