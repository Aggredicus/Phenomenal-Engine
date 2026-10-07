# Write Access Setup

Phenomenal Engine v0.2.0 is designed so a player can fork the repository, connect a write-capable AI integration, and say:

> **Play Phenomenal Engine.**

Repository write access must be granted deliberately and narrowly.

## What permission is needed?

For repository file creation and updates, the GitHub App backing the chatbot/integration needs:

- **Metadata: Read**
- **Contents: Read & write**

Normal gameplay does **not** require repository Administration permission.

GitHub App settings expose permissions as No access, Read-only, or Read & write:
https://docs.github.com/en/apps/creating-github-apps/registering-a-github-app/registering-a-github-app

## Installation: player steps

When installing the GitHub App/integration:

1. choose the GitHub account that owns your Phenomenal Engine fork;
2. choose **Only select repositories**;
3. select your Phenomenal Engine fork;
4. if using a separate private save repository, select that too;
5. review the requested permissions;
6. install/authorize the app.

GitHub's installation documentation:
https://docs.github.com/en/apps/using-github-apps/installing-a-github-app-from-a-third-party

## If the chatbot currently has read-only GitHub access

Read-only repository access cannot be upgraded by game text.

The integration itself must be configured to request write permission.

If you administer the GitHub App:

1. GitHub -> Settings -> Developer settings -> GitHub Apps;
2. open the app;
3. **Permissions & events**;
4. Repository permissions -> **Contents -> Read & write**;
5. save changes;
6. approve the updated permission request for the installation;
7. keep the installation limited to the selected Phenomenal Engine repositories.

For ChatGPT Enterprise custom GitHub app templates, OpenAI documents starting with read-only permissions and adding write permissions only for the workflows that need them, including Contents for write workflows:
https://help.openai.com/en/articles/20001248-set-up-the-github-enterprise-app-template-in-chatgpt

If your ChatGPT/GitHub connection does not expose a way to grant repository writes, use a write-capable GitHub app/plugin or another supported execution integration rather than pasting a PAT into chat.

## Verify capability

Ask your chatbot:

> Check my Phenomenal Engine fork and tell me whether your GitHub connection has push/write permission. Do not modify anything yet.

A compatible integration should report its actual capability rather than guessing.

Then test a harmless write, for example creating and deleting a temporary file, only if you explicitly want to test the connection.

## Write access is not execution

Repository writes alone do not execute Python.

For authoritative gameplay the AI also needs one of:

- a Phenomenal Engine runtime/tool;
- a user-controlled GitHub Codespace;
- an agent environment capable of running the repository safely.

The included Codespaces configuration is documented in `docs/codespaces_and_saves.md`.

## Save privacy

Do not confuse permission with destination safety.

A public Phenomenal Engine fork remains public even if the app has write access. Keep private campaign state in a private save repository/service.

The app should never silently commit private gameplay data to the public fork.

## Minimum safe permission matrix

| Resource | Contents permission |
| --- | --- |
| Public/user Phenomenal Engine fork | Read; Read & write when the app needs repository writes |
| Private save repository | Read & write |
| Unrelated repositories | No access |
| Repository administration | No access |

## Never paste credentials into chat

Do not use game dialogue or prompts to transmit:

- personal access tokens;
- GitHub App private keys;
- installation tokens;
- webhook secrets;
- Codespaces secrets.

Use the provider's normal authorization flow.
