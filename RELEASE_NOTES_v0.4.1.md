# Phenomenal Engine v0.4.1

Patch release for authoritative Mirror Delivery gameplay and player identity.

- Captain Jun Zan (Captain Zan) is the default Mirror Delivery captain and persists in structured campaign saves.
- Real-world account names must never be substituted for player-character identity.
- Chat integrations must execute and persist an authoritative engine turn before claiming a gameplay turn was saved.
- Added regression coverage for player identity and save integrity.
- Preserves four complete, isolated Mir copies as canonical story architecture.

**Compatibility:** Existing campaign saves remain supported; older saves without player identity use a generic Captain fallback until explicitly migrated. The previous improvised chat-only Wayfarer narrative was not an authoritative save and is not migrated.
