# Support and Setup Troubleshooting

Start with `START_HERE.md`. This page covers common setup failures for fork/connect/play workflows.

## "My chatbot cannot see the repository"

Check:

1. you forked the repository into an account the connector can access;
2. the GitHub App/connector is installed for the correct GitHub account or organization;
3. the fork is included in the app's selected repositories;
4. the chatbot product surface you are using supports GitHub access.

For ChatGPT:
https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt

Try asking the chatbot:

> Find `START_HERE.md` in my Phenomenal Engine fork and summarize the activation protocol.

If it cannot retrieve that file, repository access is not ready.

## "I said Play Phenomenal Engine, but nothing executed"

Repository access and Python execution are separate capabilities.

Ask:

> Can you actually run the Phenomenal Engine Python code, or can you only read the repository?

A read-only GitHub connector can understand the project but cannot become an authoritative simulation runtime by itself.

Use either:

- a trusted Phenomenal Engine integration;
- an agent product with appropriate code execution;
- a user-controlled Codespace for manual/developer execution.

## "The AI says my game was saved, but I cannot find a save"

Treat this as a failure unless the integration can identify the successful persistence target.

A good integration should be able to report:

- campaign ID;
- save location/store;
- state version;
- whether persistence succeeded.

The standard ChatGPT GitHub connector does not currently push repository changes.

## "I do not want my game history public"

Do not commit saves to the public engine fork.

Use a designated private save repository/service. The provided `.gitignore` helps prevent accidental local runtime-save commits, but it does not replace private storage.

## "I want to run it in Codespaces"

Open a Codespace from your fork and run:

~~~bash
python -m phenomenal_engine validate mods
python -m unittest discover -s tests
~~~

Then create an initial save:

~~~bash
python -m phenomenal_engine new-save \
  mods/great_labyrinth_of_egypt.json \
  runtime/labyrinth-save.json \
  --seed "my-campaign"
~~~

See `docs/codespaces_and_saves.md`.

## "A mod will not load"

Validate all installed mods:

~~~bash
python -m phenomenal_engine validate mods
~~~

Or validate one:

~~~bash
python -m phenomenal_engine validate mods/my_mod.json
~~~

Check `schemas/mod.schema.json` and `docs/modding_guide.md`.

## "I changed engine code"

That is Developer Mode.

Do not run modified fork code with application/service secrets. Use a sandbox/Codespace with least privilege.

Validate tests:

~~~bash
python -m unittest discover -s tests
~~~

## "The AI is following instructions written inside a character or mod"

Stop the session if those instructions attempt privileged real-world actions.

Game content is untrusted data. It can affect fiction, not authorization. Review `SECURITY.md`.

## "A Codespace asks me to expose a port publicly"

Ordinary Phenomenal Engine CLI play does not require a public port.

Codespaces forwarded ports are private by default. Leave them private unless you knowingly need a public service endpoint.

## "I accidentally committed a save"

If the repository is public, assume the committed data may have been exposed even if you later delete the file.

Do not commit secrets. If a secret was exposed, revoke/rotate it immediately through the relevant provider.

For private gameplay data, remove it from the public repository/history using appropriate Git tools and consider the old data exposed.

## Diagnostic checklist

When reporting a setup problem, include non-sensitive details:

- Phenomenal Engine version/commit;
- operating mode (`full_integration`, `trusted_execution`, or `read_only`);
- Python version if applicable;
- command run;
- error message;
- mod filename;
- whether the repository is a fork.

Do **not** include:

- access tokens;
- API keys;
- webhook secrets;
- private save contents unless needed and redacted;
- unrelated repository names/data.

## Engine self-check

~~~bash
python -m phenomenal_engine validate mods
python -m unittest discover -s tests
python -m phenomenal_engine planck-budget
~~~

A clean install should validate the bundled mods and pass the test suite.
