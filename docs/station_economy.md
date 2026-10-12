# Station economies — v0.6.0

Arriving at a station now reveals a persistent local market, named businesses,
NPCs, districts, paid work, services and onward delivery contracts. This is a
fictional game economy using station credits; it never spends real money.

## Places with people and work

| Hub | Businesses | Districts | Job templates | Character |
|---|---:|---:|---:|---|
| Earth Escape Gate | 5 | 6 | 8 | Fuel co-op, refit yard, provisions, graded salvage, dispatch |
| Nacre Station / Nacre Center | 6 | 6 | 10 | Repair union, hydroponic growers, relay exchange, clinic, materials, labor desk |
| Other authored stations | 1 each | 2 each | 3 each | Supplies, services and locally appropriate station work |

There are 9 configured stations, 18 vendors, 39 recurring job templates and 12
tradable item types. The hidden destination's market becomes observer-visible
only after reaching it; global activity packets do not reveal its name.
"Nacre Center" and "Nacre Centre" are aliases of the existing Nacre Station
travel node, not a new location with inconsistent distances.

The Gate offers manifest reconciliation, tug scheduling, salvage grading,
survey work, missing shipment investigation, provision routing, and physical
deliveries toward Nacre or Far Relay. Nacre offers radiator records, supervised
fitting work, harvest manifests, message routing, optical navigation checks,
shift mediation, clinic stores, panel grading and inward cargo contracts.

Read `mods/economies/mirror_delivery.json` for the authored businesses, people,
sector hooks, prices, stock, services, contracts and activity cycles. Mods use
the whitelisted `economy_profile` ID; game text cannot load arbitrary files.

## Persistent resources and honest migration

The authored starter grant is **4,000 station credits**, **2,500 kg cargo
capacity**, **three crew**, and **45 crew-days** of food and life-support
replenishment, plus repair kits, seals, coolant, medical stores and propellant
canisters. A ration pack or life-support bundle covers one crew-day. These are
abstract game units, not an astronautical life-support specification. Readiness
scores remain abstract; a 0.82 propellant margin is not 82% of measured fuel.

New campaigns record this economy from creation. An old save previews the
authored baseline with `initialization_pending=true`; nothing is written or
retroactively bought. Its first executed new turn initializes the economy at
the existing world clock **before** new travel/work time, then records the
initialization in the action outcome. Old event hashes, actions and rolls stay
unchanged. Development/publication does not advance or rewrite a live campaign.

Inventory and accepted delivery cargo count against capacity. Food and
life-support stocks are consumed once per elapsed whole day, per crew member.
Fractional days carry forward. A shortage is recorded as unmet crew-days, never
negative inventory or an invented death. The director must explain shortages
and resolve their further consequences through the applicable game mechanics.

## A market that keeps moving

World time drives periodic freight arrivals, maintenance shifts, departure
demand and community markets. Vendors replenish stock, sell to civilian
customers, and receive bounded external station-business income. Scarcity,
local markup, the current activity cycle and earned station reputation change
quotes. Selling returns 60% of the current retail quote, rounded down (minimum
one credit). Buy/sell operations transfer both money and goods between player
and vendor; they never create player funds.

Daily flows are authored deterministic schedules, seeded for each station's
phase. They are not a forecast of real economic behavior. Bulk time passage
composes periodic stock flows in logarithmic time and gives the same inventory
as advancing those days separately. Vendors have finite budgets and storage;
production and civilian demand are explicit external flows. Browsing has no
time cost and cannot farm restocks. Waiting consumes ship supplies and can
expire contracts. Station history summaries are bounded; authoritative turn
history stays in the hash-chained ledger.

## Trades and services

Buy and sell commands require the exact quoted unit price. The engine rejects
changed quotes, unknown/local-inaccessible vendors, insufficient credit or
stock, vendor cash/storage limits, nonpositive quantities and cargo overload.
A rejected transaction changes neither saved state nor RNG.

Service commands require a listed local service and its exact price. Providers
must have the required parts. Fees transfer to the provider, materials leave
its stock, service time advances, and readiness changes are recorded. Available
services include inspection, propellant top-up, hull repairs, cooling work and
a four-hour departure service package. Service effects are whitelisted to hull,
propellant and thermal readiness. No service powers, mounts or networks Mir.

Owned repair kits, seals, coolant, propellant canisters and thermal blankets
can be used through `use_item`; quantities leave inventory and bounded physical
readiness effects are recorded. Data and relay equipment can support a relevant
explained adjudication modifier; merely owning gear does not guarantee success.

## Quest lifecycle and rewards

1. **Accept** an available local funded contract. Its sponsor places the promised
   credits in escrow; delivery cargo uses ship capacity immediately.
2. **Work** on a local objective using its authored character skill/difficulty,
   with validated, relevant role-playing modifiers when appropriate. Success
   advances work; exceptional success can advance two steps; partial success
   advances one with a complication. Failure still spends the work interval.
3. **Deliver** contract cargo at its actual destination, or finish all local work
   steps. The job becomes ready for payment, not silently paid already.
4. **Claim** the reward locally. Escrow becomes player credits, item rewards enter
   inventory, the quest is completed and reputation improves.

No payment is available before the objective is ready. Completed contracts
cannot pay twice even with a fresh idempotency key. Retry keys also bind the
exact economy command. Jobs expire after their stated deadline; abandonment or
expiry returns escrow to the sponsor and clears the active delivery obligation.
Recurring templates create distinct offers after their repeat interval, with
bounded sponsor funding. Job rewards and progress are persistent quest state.

## Player/agent interface

Read the current station without a turn:

```bash
python -m phenomenal_engine economy mods/mirror_delivery.json SAVE.json
python -m phenomenal_engine economy mods/mirror_delivery.json SAVE.json \
  --command '{"kind":"service","service_id":"full_service","expected_price":1100}'
```

Execute one authorized interaction using ordinary persistent play (the existing
consent gate still applies):

```bash
python -m phenomenal_engine play mods/mirror_delivery.json SAVE.json \
  "I have Morrowglass serviced." --idempotency-key UNIQUE_KEY \
  --economy-command '{"kind":"service","service_id":"full_service","expected_price":1100}'
```

Command kinds: `visit_sector`, `buy`, `sell`, `service`, `use_item`, `accept_job`,
`work_job`, `deliver_job`, `claim_reward`, `abandon_job`, `wait`. Exact shapes are
in `schemas/economy_command.schema.json`. Do not accept arbitrary state effects,
prices or rewards from player prose. Typed intent follows the player's actual
choice; don't buy items or accept jobs merely because they appear on the board.

Connected-app turns include `economy_command` in the normal `turn_exchange`
request. Routine validated trades/services have automatic assessments; work
uses the job's authored skill and difficulty. Read-only `operation: preview`
returns `economy_quote`, the price/time/resource effects, prepared action odds,
and quote/assessment hashes. Show these before executing and bind them with
`expected_economy_sha256` and `expected_adjudication_sha256`. A stale quote is
refused. A work assessment may supply bounded modifiers but cannot replace the
job's authored skill/difficulty or supply arbitrary reward effects.

The proposal still reports `persisted=false`. Save with the connected GitHub
app, verify remote readback, then narrate actual goods, rewards, service results
and local developments. Scene packets/director projections include only the
current `station_economy`, not competing save state. Browsing displays are
read-only; completed economic operations appear in the turn outcome and ledger.

## Scope

This release supplies playable station economies, not a universal economics
simulator. It does not infer every free-form purchase automatically, run global
NPC balance sheets, model liters of fuel, apply medical treatment without a
health system, or authorize real-world transactions. Narration can make people
and places vivid; credits, inventory, quest progress and ship services must come
from the executed state.
