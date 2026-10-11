# New Chat Playtest — Mirror Delivery (Review Branch)

**Status:** Python-engine playtest ready. **Not** a hosted, autonomous ChatGPT game service. The legal covenant remains a review draft. This version does **not** upload public campaign history to GitHub.

## What is verified

- The real Phenomenal Engine Python package exists in this repository and its CI tests run.
- The \`play\` command simulates one turn and atomically saves JSON with a hash-chained ledger and PCG32 RNG state.
- A consent-gate receipt is now required for \`play\` and \`new-save\` on this branch.
- The new \`scripts/chat_playtest.py\` launcher creates a new local save, requests non-default affirmations, executes the authoritative opening turn, and prints a full scene packet.
- The launcher **cannot** authenticate GitHub account identity, check repository visibility, push saves to GitHub, or connect itself to a new ChatGPT conversation. The console explicitly says so.
- Existing campaigns are never overwritten: each \`--new\` test gets a unique save filename.

## One-command test in your existing Codespace

From your repository's Codespace terminal, switch to the PR branch **without discarding uncommitted work**:

\`\`\`bash
git fetch origin feature/player-covenant-consent-gate
git switch feature/player-covenant-consent-gate
\`\`\`

If that branch doesn't exist locally yet, instead run:

\`\`\`bash
git switch --track origin/feature/player-covenant-consent-gate
\`\`\`

Start the first genuine turn with:

\`\`\`bash
python scripts/chat_playtest.py --new --once
\`\`\`

Review the complete draft covenant first, if desired:

\`\`\`bash
python -m phenomenal_engine covenant --full
\`\`\`

During setup the launcher requests your **intended** publication choice, a repo reference, and four explicit \`YES\` acknowledgements. The acceptance is **local and unverified**. The save is always written under \`runtime/\` (ignored by Git), regardless of the public/private *intention* selected. Nothing is made public by this program.

The script executes one turn and prints \`scene_packet\`, confirmed \`persisted: true\`, and the actual local save location. Copy only the \`scene_packet\` into your ChatGPT chat to have the assistant narrate it. **Do not paste the private save file**, API tokens, secrets, or a full terminal dump.

Resume a local game by the safe filename stem printed in the save location:

\`\`\`bash
python scripts/chat_playtest.py --resume mirror-test-YYYYMMDDTHHMMSS-xxxxxx --once --action "I inspect the sealed Mir vault."
\`\`\`

Or use \`--resume\` without \`--once\` for a continuous terminal session.

## New Chat / ChatGPT Work

A fresh ChatGPT conversation does not automatically inherit an authenticated Codespaces terminal. If the user has ChatGPT Work, its browser/computer workflow may be able to access the Codespace; connection and command execution must be **verified in the new session**, not assumed.

Copy this in a **new ChatGPT conversation**:

> I want to test Phenomenal Engine: Mirror Delivery from a **fresh game**. My repository is Aggredicus/Phenomenal-Engine. Read \`START_HERE.md\` and \`AGENT_BOOTLOADER.md\` from branch \`feature/player-covenant-consent-gate\`, then read \`docs/NEW_CHAT_PLAYTEST.md\` on the same branch. This is a technical playtest, not a published public campaign. Present the consent gate and explain the real Python and save capabilities you can verify. If you can operate my existing Codespace through Work, use \`python scripts/chat_playtest.py --new --once\` and then narrate **only** its returned \`scene_packet\`. Otherwise explain that the terminal is not connected, give me the one-line Codespace command to run, and let me paste the resulting packet. Never fabricate rolls, persistence, user acceptance, GitHub uploads, or billing controls. Use Captain Jun Zan, aboard Morrowglass. Do not load earlier campaigns.

## Release gate still outstanding

Before enabling public save publishing or describing the agreement as effective:

1. Counsel review; operator/contact and privacy notices.
2. Provider-authenticated agreement consent and GitHub repository visibility verification.
3. User-owned GitHub save commits with concurrency protection, content safety checks, and successful remote persistence before canonical narration.
4. Resource/billing limits and abuse reporting.

Do not merge this review branch into \`main\` solely to perform a local playtest.
