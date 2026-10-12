# Mirror Delivery campaign — v0.7.0

The authored campaign carries Captain Jun Zan and Morrowglass from Cislunar
Exchange through the inner system to Mercury. It adds 25 scenes, 58 choices,
13 conversation topics and six ending paths to the existing travel graph,
station economies and two-stage Mir activation protocol. This guide describes
mechanics without disclosing investigation answers or unrevealed endings.

## Playable arcs

| Arc | Places | Play |
|---|---|---|
| Custody and departure | Cislunar Exchange, Earth Escape Gate, Far Relay | Contract review, courier histories, departure records, insurance, crew farewells |
| Working communities | Nacre Station / Center | Repair union, public representation, crew relationships, navigation recovery, courier assistance |
| Inward passage | Venus Tangent, Perihelic Shelter Nine | Beacon investigation, urgent clinic request, messages home, weather shelter, inspectors, archive work |
| Optional investigation | A discoverable travel branch | Provenance, withheld records, supply work and alternate approaches |
| Arrival and acceptance | Mercury High Orbit, Caloris Terminus | Custody audit, evidence disclosure, worker testimony, registration, hearing and aftermath |

Every scene has concrete choices and success, partial-success and failure
consequences. Routine inquiry and reliable alternatives resolve automatically;
risky approaches use the saved character's skill and an authored difficulty.
Essential information and delivery have accessible alternatives even when an
optional investigation or persuasion attempt fails. Some opportunities are
location- or time-dependent; missing the urgent clinic window records the
station's fallback response, not an invented fatality.

The campaign and station job board coexist. Scene rewards are finite and paid
once; recurring economic contracts still use accept/work/deliver/claim. Supplies,
fees and scene time affect the same inventory, credits and world clock as travel.

## Read-only inspection and preview

```bash
python -m phenomenal_engine campaign mods/mirror_delivery.json runtime/mirror.json
python -m phenomenal_engine campaign mods/mirror_delivery.json runtime/mirror.json \
  --command examples/mirror_delivery_cairn_talk.json
```

Neither command saves, advances time or consumes RNG. The view exposes available
local scenes, unlocked topic IDs, discovered evidence, recorded courier replies,
faction standing and the recent journal. Future outcome text and undiscovered
evidence remain outside the view. A quote identifies the choice, time range and
assessment, plus `quote_sha256`; it does not narrate an outcome in advance.

## One typed action per turn

`schemas/campaign_command.schema.json` defines three commands:

```json
{"kind":"talk","npc_id":"sister_cairn","topic_id":"ships"}
```

```json
{"kind":"propose_cooperation","policy":"emergency_comms","npc_ids":["ren_ivo","sister_cairn","mara_ves"]}
```

```json
{"kind":"choose","scene_id":"gate_insurer","choice_id":"clarify"}
```

Choose IDs from the current view. Execute through the persistent command:

```bash
python -m phenomenal_engine play mods/mirror_delivery.json runtime/mirror.json \
  "I ask Sister Cairn about the four ships" \
  --campaign-command examples/mirror_delivery_cairn_talk.json \
  --idempotency-key cairn-ships-1
```

The usual Player Covenant and authorized destination requirements apply. One
turn can contain either an economy command or a campaign command. Player prose
cannot supply effects, bypass prerequisites, change authored difficulty or
trigger an additional text-matched action during a typed command.

For connected saves, send `campaign_command` in the existing `turn_exchange`
request. Use `operation: "preview"`, show the odds, then bind
`expected_campaign_sha256` and `expected_adjudication_sha256` when proposing.
For uncertain scalar choices only, an optional assessment may add explained,
bounded modifiers while keeping the authored skill and difficulty. Automatic
conversations and group proposals use their authored assessments. Invalid,
stale, expired, unfunded or inaccessible commands leave memory and RNG unchanged.
Reuse an idempotency key only for the identical intended action and command;
retrying a verified saved action returns its existing result.

## Courier and crew responses

Conversations return actual authored replies, including Cairn's account of all
four ships. Reading available testimony is automatic and takes ten minutes.
Repeated topics cannot farm relationship rewards. Proposals use distinct courier
checks and return each agreement, condition or refusal. Existing accepted pacts
need no new persuasion roll. Communications and route coordination agreements
forbid payload networking or shared custody; they do not teleport couriers or
implement a formation-flight controller. Other couriers retain independent
arrival schedules and rescue consequences.

Crew topics and local choices record trust, evidence and downstream consequences.
Mir topics appear only after deliberate activation through the existing separate
two-stage process. No conversation, service, rescue or scene wakes the local Mir.
Remote divergence becomes known only through accessible, recorded testimony.

## Receiving evidence and endings

Arrival reports establish availability, not verified hardware shares. Receiving
system audits or registration verify available physical shares. A deployment
settlement requiring three shares cannot use mere radio messages as a quorum.
The hearing requires actual Caloris arrival and preparation; each ending respects
pristine/divergent provenance, the evidence gathered, the selected governance
choice and actual check result. Physical custody transfer is distinct from
permission to deploy. A custody receipt closes delivery and the hearing and
prevents Morrowglass from activating the transferred vault. Continuing without
a handoff keeps custody and awards no delivery payment.

Endings record an epilogue with crew trust, courier relationships, faction
standing, rescues and evidence. Station economy and travel remain playable after
a completed handoff. The six authored epilogue definitions are developer content
in `mods/campaigns/mirror_delivery.json`; avoid reading that file during play if
you want investigation and endings to remain discoveries.

## Existing saves

Older saves lack the optional `campaign` table. Inspection previews the baseline
with `initialization_pending: true` on a copy. The next actual new turn initializes
at the saved clock, introduces current accessible scenes and records ensuing
results. It does not infer completed optional scenes or unanimous agreements from
past prose, reroll old outcomes, edit history or advance time during development.
The engine version becomes 0.7.0 on actual execution. Other adventures keep their
existing gameplay; this profile extends Mirror Delivery specifically.

Long public campaigns use the lossless ledger archive described in
[Fast tokenless turns](fast_tokenless_turns.md). The latest packet remains
readable JSON; both supported save loaders restore and verify all old events.
