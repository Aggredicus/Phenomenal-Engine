# Action adjudication — v0.5.0

Routine execution should be reliable. Uncertainty belongs in meaningful stakes,
opposition, hidden information, resource constraints and difficult execution.
The connected turn bridge no longer silently uses skill=0, difficulty=0,
context=0 for every action.

## Before a turn

The trusted Narrative Director supplies an `adjudication` object separately
from player action text. Describe the stakes, relevant character strength,
challenge and evidence before rolling. Reward useful choices and preparation,
not verbosity, polished prose, a user's personal identity, or agreeing with the
director. A concise effective plan receives the same benefit as a long speech.

Unassessed connected turns are refused before state changes or RNG draws.
Authored deterministic rules, including Mir's guarded activation interlock,
still resolve without a director override. Their physical preconditions remain
authoritative. An assessment has no permission to write arbitrary game state,
execute tools, purchase resources or bypass a rule.

## Character strengths and difficulty

Mirror Delivery's authored captain baseline has piloting 2; leadership,
diplomacy, logistics and investigation 1; engineering and general 0. Ratings
mean 0 untrained, 1 trained, 2 expert, 3 exceptional. They are fictional starting
training, not facts inferred from the human user's profile. The campaign stores
`player_profile`. Old saves adopt this baseline on their next executed turn;
preview only reads it, and historical events/hashes are never rewritten.

Difficulty is a situational rating: -1 easy, 0 ordinary, 1 demanding, 2 hard,
3 severe, 4 extreme. A capability rating and a difficulty are on the same scale.
NPC motives, urgency, opposition, equipment and constraints determine the actual
rating. Give a concrete, observer-safe `difficulty_reason`; do not expose hidden
canon just to explain a modifier.

Each modifier has a `value`, `reason` and distinct `source`. Each value is bounded
to +/-0.5; total context is capped at +/-1.0. Count a preparation or concession
once, and do not double-count something already represented by skill or
difficulty. Sources/reasons are director assertions, not independently verified
evidence; the trusted host must adjudicate honestly from established state.

With Mirror Delivery's temperature 0.72:

| Situation | Skill | Difficulty | Context | Probability |
|---|---:|---:|---:|---:|
| Untrained, easy | 0 | -1 | 0 | 80.0% |
| Trained, ordinary | 1 | 0 | 0 | 80.0% |
| Expert, ordinary | 2 | 0 | 0 | 94.1% |
| Expert, demanding | 2 | 1 | 0 | 80.0% |
| Expert, hard | 2 | 2 | 0 | 50.0% |
| Expert, hard, useful preparation | 2 | 2 | +0.5 | 66.7% |

`p = clamp(sigmoid((skill + context - difficulty) / temperature), .01, .99)`.
Skill is looked up from the character sheet: the request cannot invent a rating.

## Automatic tasks

```json
{
  "mode": "automatic",
  "task": "request_service",
  "reason": "The staffed propulsion dock accepts routine service inquiries."
}
```

Supported scopes: `read_available_information`, `send_message`,
`request_service`, `observe_public_area`, `routine_movement`. This deliberately
does not infer automatic success from a broad keyword in free-form action text.
The director must choose a supported scope and explain why uncertainty is absent.

Sending an invitation is not securing agreement. Requesting dock service is not
repairing/refueling a ship. Reading available information does not reveal a
hidden truth. These scopes consume no **action** RNG; a consequential turn still
advances the background story and samples a separately reported world hazard.
For actual inventory, purchases and completed service orders, use the explicit
validated commands in [Station economies](station_economy.md); a bare routine
inquiry does not authorize a transaction.

## Skill check

See `examples/diplomacy_assessment.json`. Supply `mode: check`, `skill_id`,
`difficulty`, `difficulty_reason`, `modifiers`, and `stakes` describing success,
partial success and failure. Optional `target_id` must identify an existing NPC.
Assessments are validated by Python; the JSON schema is
`schemas/adjudication.schema.json`.

The outcome records the complete prepared assessment, probability, actual
uniform draw, draw margin, log-odds margin, degree, and applicable narrative
stakes in the hash-chained event ledger. Stakes are narrative constraints, not
automatic effects on money, inventory, treaties or relationships.

## Different NPCs, different decisions

See `examples/courier_cooperation_assessment.json`. `mode: group` includes one
check per distinct NPC, each with its own difficulty, modifiers and stakes.
`success_policy: all` requires unanimity; `any` requires one success. It returns
every check separately, so a mixed response cannot be narrated as unanimous
agreement. A combined probability uses independent conditional checks: product
of probabilities for `all`, or `1 - product(1-p)` for `any`. Shared conditions
must be represented honestly; this is not a correlated convoy survival model.

For the courier proposal, consider Ren's schedule, Cairn's custody requirements
and Mara's concerns independently. Addressing payload isolation may remove an
objection without guaranteeing anyone's acceptance. A counteroffer or condition
can be useful progress even when unanimity is not achieved.

## Degrees from the actual roll

Success remains `u < p`. The strongest 10% of the success interval is
`exceptional_success`. The first 20% of the failure interval is
`partial_success`; the last 20% is `major_setback`; the rest is `failure`.
Partial success does not meet the full binary goal. Use its predeclared stakes
for a condition, cost, delay or limited agreement. A major setback never
authorizes an invented injury or automatic damage.

`draw_margin = p - u`. `margin = temperature * (logit(p) - logit(u))`, with
endpoint protection. Its sign now agrees with success; no independent normal
draw generates a contradictory margin. Successful checks have zero consequence
severity; failures retain a separate log-normal severity hint, not an applied
damage amount. Background hazard odds and their draw are also returned explicitly.

## Read-only preview and visible progress

```bash
python -m phenomenal_engine preview-action mods/mirror_delivery.json SAVE.json \
  "I propose mutual assistance." --adjudication examples/diplomacy_assessment.json
python -m phenomenal_engine play mods/mirror_delivery.json SAVE.json \
  "I propose mutual assistance." --adjudication examples/diplomacy_assessment.json \
  --idempotency-key UNIQUE_TURN_KEY
```

The existing consent requirement still applies to play. `preview-action` is
read-only and does not consume RNG, initialize a profile, or write a save.

For connected-app turns, add the raw `adjudication` to the existing
`turn_exchange` request. Set `operation: preview` to get the prepared odds and
`adjudication_sha256`, without proposing a save. Show this assessment to the
player, then send `operation: propose` (the default) with the same request and
`expected_adjudication_sha256` from preview. A changed assessment is refused.
The hash check is optional for backward-compatible hosts, but hosts should use
it to bind the displayed odds to the executed turn. The same idempotency key
cannot be reused with a different action or assessment.

`resolution` in the proposal permits an immediate math/progress display, marked
**provisional**, while persistence is pending. A proposal is still
`persisted=false`, `remote_verified=false`. Commit through the authenticated
GitHub app, verify remote readback, then reveal canonical story consequences.
Do not fabricate timed progress transitions or wait for CI during gameplay.

Legacy low-level `Engine.step` and numeric CLI flags remain supported and label
their inputs `legacy_numeric` with a warning. Old wrappers must adopt explicit
assessments; they do not automatically understand the player's prose. All new
connected gameplay must use the strict assessment path.

## Compatibility

Version 0.5.0 preserves saved PCG states and historical ledger entries. Future
RNG consumption changes intentionally: quality uses the same draw as success,
automatic tasks consume no action RNG, and background hazards use the existing
`world` stream. Earlier rolls are never replayed or revised. The running
campaign stays on its current turn until the player acts after deployment.
