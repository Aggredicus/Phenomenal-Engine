# ReviewForge pilot: safe, bounded integration

This pilot never starts Codespaces, publishes campaign saves, changes GitHub
permissions, or automatically merges the draft PR. Existing fast CI remains
unchanged. Additional stress checks are on pull requests and manual dispatch
only, with a read-only token and 12-minute timeout; no nightly paid runs.

Confirmed code defects addressed:
RNG-01: randint for widths > 2**32 could loop forever with a 32-bit RNG.
RNG-02: normal() had an unrecorded Box-Muller cached draw, breaking replay
after an odd normal draw when restoring serialized state.

The full ReviewForge 1.0 CLI is distributed separately: this PR provides the
project-specific .reviewgate configurations and review contract, but does not
claim its scanner is installed or executed in CI. Install that vetted toolkit
in a local clone before running its verify command. The workflow here executes
real project regression and bounded property tests independently.

Evidence required before merge: CI logs/commit SHA, executed test counts,
fresh-context functional review, dedicated security review, findings disposition,
human approval. A green test badge alone does not certify the implementation.
