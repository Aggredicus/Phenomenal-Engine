"""Persistent, bounded station markets and jobs. Commands are typed game data.

Read-only quotes use a private copy. Money/items move only during an engine turn;
world time, not repeated browsing, replenishes stations and rotates their activity.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import json
from pathlib import Path


class EconomyError(ValueError):
    pass


PROFILE_FILES = {"mirror_delivery": "mirror_delivery.json"}
SERVICE_FIELDS = {"morrowglass_hull", "morrowglass_propellant_margin", "morrowglass_thermal_margin"}
ITEM_EFFECTS = {"repair_kit": ("morrowglass_hull", .05), "spare_seals": ("morrowglass_hull", .01),
                "propellant_canister": ("morrowglass_propellant_margin", .03),
                "coolant_pack": ("morrowglass_thermal_margin", .04),
                "thermal_blanket": ("morrowglass_thermal_margin", .01)}


def _integer(value, label, minimum=0, maximum=100_000_000):
    if type(value) is not int or not minimum <= value <= maximum:
        raise EconomyError(f"{label} must be an integer in [{minimum}, {maximum}]")
    return value


def load_profile(mod):
    key = mod.get("economy_profile")
    if key is None:
        return None
    if key not in PROFILE_FILES:
        raise EconomyError("unknown economy profile")
    path = Path(__file__).resolve().parents[1] / "mods" / "economies" / PROFILE_FILES[key]
    data = json.loads(path.read_text(encoding="utf-8"))
    validate_profile(data)
    return data


def validate_profile(data):
    if not isinstance(data, dict) or data.get("schema_version") != "1.0.0":
        raise EconomyError("invalid economy profile")
    if not isinstance(data.get("items"), dict) or not isinstance(data.get("stations"), dict):
        raise EconomyError("economy requires item and station catalogs")
    start = data["starting_resources"]
    for key in ("credits", "cargo_capacity_g", "crew_count"):
        _integer(start[key], key, 1)
    for key, count in start["inventory"].items():
        if key not in data["items"]:
            raise EconomyError("starting inventory references unknown item")
        _integer(count, "inventory quantity")
    for item in data["items"].values():
        _integer(item["base_price"], "base price", 1)
        _integer(item["mass_g"], "item mass", 1)
    for station in data["stations"].values():
        if not isinstance(station.get("events"), list) or not 1 <= len(station["events"]) <= 16:
            raise EconomyError("stations require a bounded activity cycle")
        for event in station["events"]:
            _integer(event.get("restock_permille", 1000), "restock factor", 0, 2000)
            _integer(event.get("demand_permille", 1000), "demand factor", 0, 2000)
            for factor in event.get("price_factors", {}).values():
                _integer(factor, "price factor", 500, 2000)
        sectors = {s["id"] for s in station["sectors"]}
        vendors = station["vendors"]
        for vendor in vendors.values():
            if vendor["sector_id"] not in sectors:
                raise EconomyError("vendor references unknown sector")
            _integer(vendor["credits"], "vendor budget")
            _integer(vendor["markup_permille"], "markup", 500, 2000)
            for item_id, offer in vendor["stock"].items():
                if item_id not in data["items"]:
                    raise EconomyError("vendor references unknown item")
                cap = _integer(offer["capacity"], "stock capacity", 1)
                _integer(offer["quantity"], "stock quantity", 0, cap)
                _integer(offer["daily_restock"], "daily restock")
                _integer(offer.get("daily_demand", 0), "daily civilian demand")
        for service in station["services"].values():
            if service["vendor_id"] not in vendors or set(service.get("effects", {})) - SERVICE_FIELDS:
                raise EconomyError("invalid service vendor or effect")
            _integer(service["price"], "service price", 1)
            _integer(service["minutes"], "service duration", 1, 1440)
            for key, delta in service.get("effects", {}).items():
                if type(delta) not in (float, int) or not 0 < delta <= 1:
                    raise EconomyError("service effects must be bounded positive readiness changes")
            for item_id, count in service.get("materials", {}).items():
                if item_id not in vendors[service["vendor_id"]]["stock"]:
                    raise EconomyError("service material unavailable from provider")
                _integer(count, "service material count", 1)
        for job in station["jobs"].values():
            if job["sponsor_id"] not in vendors or job["kind"] not in {"work", "delivery"}:
                raise EconomyError("invalid job sponsor or kind")
            _integer(job["reward_credits"], "reward credits")
            _integer(job["deadline_minutes"], "deadline", 60)
            _integer(job["repeat_days"], "repeat interval", 1, 30)
            _integer(job["work_minutes"], "work duration", 1, 1440)
            _integer(job["work_steps"], "work steps", 1, 10)
            if type(job["difficulty"]) not in (int, float) or not -2 <= job["difficulty"] <= 4:
                raise EconomyError("job difficulty outside adjudication scale")
            for item_id, count in job.get("reward_items", {}).items():
                if item_id not in data["items"]:
                    raise EconomyError("unknown job reward")
                _integer(count, "reward quantity", 1)
            if job["kind"] == "delivery":
                if job["destination_id"] not in data["stations"]:
                    raise EconomyError("unknown delivery destination")
                _integer(job["cargo_mass_g"], "contract cargo mass", 1)
    return data


def initial_economy(mod, clock=0):
    profile = load_profile(mod)
    if profile is None:
        return None
    start = profile["starting_resources"]
    stations = {}
    for station_id, station in profile["stations"].items():
        stations[station_id] = {"last_day": clock // 1440, "reputation": 0,
            "vendors": {vendor_id: {"credits": vendor["credits"], "stock": {key: value["quantity"] for key, value in vendor["stock"].items()}}
                        for vendor_id, vendor in station["vendors"].items()}}
    return {"schema_version": "1.0.0", "credits": start["credits"],
            "inventory": deepcopy(start["inventory"]), "cargo_capacity_g": start["cargo_capacity_g"],
            "crew_count": start["crew_count"], "consumption_clock": clock,
            "stations": stations, "jobs": {}, "visited_sectors": {}, "local_sector": None,
            "activity_log": [], "shortages": {},
            "initialization": {"at_world_minute": clock, "source": "authored starting-resource baseline; no retroactive purchases or consumption"}}


def _state(mod, memory):
    profile = load_profile(mod)
    if profile is None:
        raise EconomyError("this adventure has no station economy")
    if "economy" not in memory:
        memory["economy"] = initial_economy(mod, int(memory.get("world_state", {}).get("world_time_minutes", 0)))
    local = profile["stations"].get(memory.get("world_state", {}).get("location"))
    if local:
        for vendor in local["vendors"].values():
            npc = vendor["npc"]
            memory.setdefault("characters", {}).setdefault(npc["id"], deepcopy(npc))
    return profile, memory["economy"]


def cargo_mass(profile, economy):
    mass = sum(profile["items"][key]["mass_g"] * qty for key, qty in economy["inventory"].items())
    return mass + sum(job.get("cargo_mass_g", 0) for job in economy["jobs"].values()
                      if job["status"] == "active" and job["kind"] == "delivery")


def _capacity(profile, economy):
    if cargo_mass(profile, economy) > economy["cargo_capacity_g"]:
        raise EconomyError("insufficient cargo capacity")


def _station(profile, memory, economy):
    key = memory.get("world_state", {}).get("location")
    if key not in profile["stations"]:
        raise EconomyError("no accessible local station market")
    return key, profile["stations"][key], economy["stations"][key]


def _event(profile, station_id, day, seed):
    events = profile["stations"][station_id]["events"]
    offset = int.from_bytes(hashlib.sha256((str(seed) + station_id).encode()).digest()[:4], "big")
    return events[(day + offset) % len(events)]


def _stock_flow(qty, definition, station_id, last_day, elapsed, profile, seed):
    """Compose periodic clamp/translation flows in O(log(days)), without
    changing results when a trip is split into shorter intervals."""
    cap = definition["capacity"]
    def compose(first, second):
        a, lo, hi = first; b, low, high = second
        clamp = lambda x: min(high, max(low, x))
        return a + b, clamp(lo + b), clamp(hi + b)
    identity = (0, 0, cap)
    period = len(profile["stations"][station_id]["events"])
    daily = []
    for offset in range(1, period + 1):
        event = _event(profile, station_id, last_day + offset, seed)
        incoming = definition["daily_restock"] * event.get("restock_permille", 1000) // 1000
        outgoing = definition.get("daily_demand", 0) * event.get("demand_permille", 1000) // 1000
        daily.append((incoming - outgoing, 0, max(0, cap - outgoing)))
    cycle = identity
    for flow in daily:
        cycle = compose(cycle, flow)
    cycles, remainder = divmod(elapsed, period)
    aggregate, power = identity, cycle
    while cycles:
        if cycles & 1:
            aggregate = compose(aggregate, power)
        power = compose(power, power)
        cycles >>= 1
    for flow in daily[:remainder]:
        aggregate = compose(aggregate, flow)
    change, low, high = aggregate
    return min(high, max(low, qty + change))


def settle_economy(mod, memory):
    """O(stations * stock), even after a long trip. Browsing never advances this."""
    if not mod.get("economy_profile"):
        return []
    profile, economy = _state(mod, memory)
    clock = int(memory.get("world_state", {}).get("world_time_minutes", 0))
    if clock < economy["consumption_clock"]:
        raise EconomyError("economy clock cannot run backwards")
    developments = []
    elapsed_days = (clock - economy["consumption_clock"]) // 1440
    if elapsed_days:
        for item_id in ("ration_pack", "life_support_day"):
            required = elapsed_days * economy["crew_count"]
            have = economy["inventory"].get(item_id, 0)
            used = min(have, required)
            economy["inventory"][item_id] = have - used
            deficit = required - used
            if deficit:
                economy["shortages"][item_id] = economy["shortages"].get(item_id, 0) + deficit
            developments.append({"kind": "consumption", "item_id": item_id, "used": used, "unmet_crew_days": deficit})
        economy["consumption_clock"] += elapsed_days * 1440
    day = clock // 1440
    for station_id, station in profile["stations"].items():
        state = economy["stations"][station_id]
        elapsed = day - state["last_day"]
        if elapsed <= 0:
            continue
        for vendor_id, vendor in station["vendors"].items():
            v = state["vendors"][vendor_id]
            v["credits"] = min(vendor["credits"] * 3, v["credits"] + elapsed * vendor["daily_income"])
            for item_id, definition in vendor["stock"].items():
                v["stock"][item_id] = _stock_flow(v["stock"][item_id], definition, station_id,
                                                state["last_day"], elapsed, profile, memory["master_seed"])
        state["last_day"] = day
        developments.append({"kind": "station_activity", "station_id": station_id,
                             "elapsed_days": elapsed, "event": _event(profile, station_id, day, memory["master_seed"])["text"]})
    for job_id, job in economy["jobs"].items():
        if job["status"] in {"active", "ready_for_payment"} and clock > job["deadline"]:
            sponsor = economy["stations"][job["origin_id"]]["vendors"][job["sponsor_id"]]
            sponsor["credits"] += job["escrow"]
            job["escrow"] = 0
            job["status"] = "expired"
            memory.get("quests", {}).get("economy:" + job_id, {})["status"] = "failed"
            developments.append({"kind": "job_expired", "job_id": job_id, "title": job["title"]})
    economy["activity_log"].extend(developments)
    del economy["activity_log"][:-40]
    known = set(memory.get("travel_state", {}).get("known_nodes", []))
    known.add(memory.get("world_state", {}).get("location"))
    return [event for event in developments if "station_id" not in event or event["station_id"] in known]


def _price(profile, memory, station_id, state, vendor_id, item_id):
    vendor = profile["stations"][station_id]["vendors"][vendor_id]
    qty = state["vendors"][vendor_id]["stock"][item_id]
    capacity = vendor["stock"][item_id]["capacity"]
    scarcity = 1500 - qty * 500 // capacity
    event = _event(profile, station_id, int(memory["world_state"].get("world_time_minutes", 0)) // 1440, memory["master_seed"])
    event_factor = event.get("price_factors", {}).get(profile["items"][item_id]["category"], 1000)
    reputation_factor = 1000 - min(50, max(0, state["reputation"]) * 5)
    numerator = profile["items"][item_id]["base_price"] * vendor["markup_permille"] * scarcity * event_factor * reputation_factor
    return max(1, (numerator + 10**12 - 1) // 10**12)


def _offers(profile, memory, station_id, station, state, economy):
    day = int(memory["world_state"].get("world_time_minutes", 0)) // 1440
    offers = []
    for code, definition in station["jobs"].items():
        job_id = station_id + ":" + code + ":" + str(day // definition["repeat_days"])
        if job_id in economy["jobs"]:
            continue
        if state["vendors"][definition["sponsor_id"]]["credits"] < definition["reward_credits"]:
            continue
        offers.append({"job_id": job_id, **deepcopy(definition)})
    return offers


def station_snapshot(mod, memory):
    """Observer-visible projection; never mutates the caller or consumes RNG."""
    copy = deepcopy(memory)
    profile, economy = _state(mod, copy)
    if copy.get("world_state", {}).get("location") not in profile["stations"]:
        return None
    settle_economy(mod, copy)
    station_id, station, state = _station(profile, copy, economy)
    vendors = []
    for vendor_id, vendor in station["vendors"].items():
        offers = [{"item_id": key, "name": profile["items"][key]["name"], "unit": profile["items"][key]["unit"],
                   "stock": state["vendors"][vendor_id]["stock"][key],
                   "buy_price": _price(profile, copy, station_id, state, vendor_id, key),
                   "sell_price": max(1, _price(profile, copy, station_id, state, vendor_id, key) * 3 // 5)}
                  for key in vendor["stock"] if profile["items"][key].get("tradeable", True)]
        vendors.append({"vendor_id": vendor_id, "name": vendor["name"], "npc": vendor["npc"],
                        "sector_id": vendor["sector_id"], "description": vendor["description"],
                        "credits": state["vendors"][vendor_id]["credits"], "offers": offers})
    day = int(copy["world_state"].get("world_time_minutes", 0)) // 1440
    return {"station_id": station_id, "name": station["name"], "description": station["description"],
            "event": _event(profile, station_id, day, copy["master_seed"]), "sectors": station["sectors"],
            "vendors": vendors, "services": station["services"],
            "job_board": _offers(profile, copy, station_id, station, state, economy),
            "active_jobs": [deepcopy(job) for job in economy["jobs"].values() if job["status"] in {"active", "ready_for_payment"}],
            "player": {"credits": economy["credits"], "inventory": deepcopy(economy["inventory"]),
                       "cargo_mass_g": cargo_mass(profile, economy), "cargo_capacity_g": economy["cargo_capacity_g"],
                       "crew_count": economy["crew_count"], "shortages": economy["shortages"]},
            "initialization_pending": "economy" not in memory, "read_only": True}


FIELDS = {
    "visit_sector": {"kind", "sector_id"}, "buy": {"kind", "vendor_id", "item_id", "quantity", "expected_unit_price"},
    "sell": {"kind", "vendor_id", "item_id", "quantity", "expected_unit_price"},
    "service": {"kind", "service_id", "expected_price"}, "accept_job": {"kind", "job_id"},
    "work_job": {"kind", "job_id"}, "deliver_job": {"kind", "job_id"},
    "claim_reward": {"kind", "job_id"}, "abandon_job": {"kind", "job_id"}, "wait": {"kind", "minutes"},
    "use_item": {"kind", "item_id", "quantity"},
}


def _job(economy, job_id):
    if job_id not in economy["jobs"]:
        raise EconomyError("unknown accepted job")
    return economy["jobs"][job_id]


def _apply(profile, memory, command, outcome=None):
    """Apply to a private candidate during planning, or transactional engine memory."""
    economy = memory["economy"]
    station_id, station, state = _station(profile, memory, economy)
    kind = command["kind"]
    clock = int(memory["world_state"].get("world_time_minutes", 0))
    result = {"kind": kind, "station_id": station_id, "minutes": 0}
    if kind == "visit_sector":
        sector = next((s for s in station["sectors"] if s["id"] == command["sector_id"]), None)
        if sector is None:
            raise EconomyError("unknown local sector")
        economy["local_sector"] = {"station_id": station_id, "sector_id": sector["id"]}
        visited = economy["visited_sectors"].setdefault(station_id, [])
        if sector["id"] not in visited:
            visited.append(sector["id"])
        result.update(sector=deepcopy(sector), minutes=15)
    elif kind in {"buy", "sell"}:
        vendor_id, item_id = command["vendor_id"], command["item_id"]
        if vendor_id not in station["vendors"] or item_id not in station["vendors"][vendor_id]["stock"]:
            raise EconomyError("vendor does not trade this item")
        if not profile["items"][item_id].get("tradeable", True):
            raise EconomyError("item is not tradeable")
        vendor = state["vendors"][vendor_id]
        price = _price(profile, memory, station_id, state, vendor_id, item_id)
        if kind == "sell":
            price = max(1, price * 3 // 5)
        if command["expected_unit_price"] != price:
            raise EconomyError("price changed; inspect a fresh quote before trading")
        qty = _integer(command["quantity"], "trade quantity", 1, 10000)
        total = price * qty
        if kind == "buy":
            if vendor["stock"][item_id] < qty or economy["credits"] < total:
                raise EconomyError("insufficient vendor stock or player credits")
            economy["credits"] -= total; vendor["credits"] += total
            vendor["stock"][item_id] -= qty
            economy["inventory"][item_id] = economy["inventory"].get(item_id, 0) + qty
        else:
            if economy["inventory"].get(item_id, 0) < qty or vendor["credits"] < total:
                raise EconomyError("insufficient player items or vendor credits")
            if vendor["stock"][item_id] + qty > station["vendors"][vendor_id]["stock"][item_id]["capacity"]:
                raise EconomyError("vendor storage is full")
            economy["credits"] += total; vendor["credits"] -= total
            economy["inventory"][item_id] -= qty; vendor["stock"][item_id] += qty
        _capacity(profile, economy)
        result.update(item_id=item_id, quantity=qty, unit_price=price, total_credits=total, minutes=10)
    elif kind == "service":
        service = station["services"].get(command["service_id"])
        if service is None:
            raise EconomyError("unknown local service")
        if command["expected_price"] != service["price"]:
            raise EconomyError("service price mismatch")
        if economy["credits"] < service["price"]:
            raise EconomyError("insufficient credits for service")
        vendor = state["vendors"][service["vendor_id"]]
        for item_id, qty in service.get("materials", {}).items():
            if vendor["stock"].get(item_id, 0) < qty:
                raise EconomyError("service provider lacks required materials")
        changes = {}
        for key, delta in service.get("effects", {}).items():
            old = memory["world_state"][key]
            new = min(1.0, round(old + delta, 6))
            changes[key] = {"before": old, "after": new}
        if changes and all(c["before"] == c["after"] for c in changes.values()):
            raise EconomyError("ship already at full readiness for this service")
        economy["credits"] -= service["price"]; vendor["credits"] += service["price"]
        for item_id, qty in service.get("materials", {}).items():
            vendor["stock"][item_id] -= qty
        for key, change in changes.items():
            memory["world_state"][key] = change["after"]
        result.update(service_id=command["service_id"], total_credits=service["price"],
                      ship_changes=changes, report=service["description"], minutes=service["minutes"])
        result["inspection_report"] = {key: memory["world_state"][key] for key in sorted(SERVICE_FIELDS)}
    elif kind == "use_item":
        item_id = command["item_id"]
        qty = _integer(command["quantity"], "use quantity", 1, 100)
        if item_id not in ITEM_EFFECTS or economy["inventory"].get(item_id, 0) < qty:
            raise EconomyError("no compatible usable ship supply in inventory")
        field, delta = ITEM_EFFECTS[item_id]
        old = memory["world_state"][field]
        if old >= 1:
            raise EconomyError("ship is already fully ready in this area")
        new = min(1.0, round(old + delta * qty, 6))
        economy["inventory"][item_id] -= qty
        memory["world_state"][field] = new
        result.update(item_id=item_id, quantity=qty, minutes=30,
                      ship_changes={field: {"before": old, "after": new}})
    elif kind == "accept_job":
        offer = next((o for o in _offers(profile, memory, station_id, station, state, economy) if o["job_id"] == command["job_id"]), None)
        if offer is None:
            raise EconomyError("job is unavailable, already accepted, or no longer funded")
        offer.update(status="active", origin_id=station_id, deadline=clock + offer["deadline_minutes"],
                     progress=0, escrow=offer["reward_credits"])
        state["vendors"][offer["sponsor_id"]]["credits"] -= offer["escrow"]
        economy["jobs"][offer["job_id"]] = offer
        _capacity(profile, economy)
        memory.setdefault("quests", {})["economy:" + offer["job_id"]] = {
            "id": "economy:" + offer["job_id"], "title": offer["title"], "tier": "local",
            "status": "open", "summary": offer["description"], "reward_credits": offer["reward_credits"]}
        result.update(job=deepcopy(offer), minutes=10)
    elif kind == "work_job":
        job = _job(economy, command["job_id"])
        if job["status"] != "active" or job["kind"] != "work" or job["origin_id"] != station_id:
            raise EconomyError("work requires an active local work contract")
        if clock + job["work_minutes"] > job["deadline"]:
            raise EconomyError("not enough time remains before the job deadline")
        if outcome is not None:
            progress = 2 if outcome.get("degree") == "exceptional_success" else 1 if outcome.get("success") or outcome.get("degree") == "partial_success" else 0
            job["progress"] = min(job["work_steps"], job["progress"] + progress)
            if job["progress"] == job["work_steps"]:
                job["status"] = "ready_for_payment"
        result.update(job_id=job["job_id"], progress=job["progress"], required=job["work_steps"],
                      status=job["status"], minutes=job["work_minutes"])
    elif kind == "deliver_job":
        job = _job(economy, command["job_id"])
        if job["status"] != "active" or job["kind"] != "delivery" or job["destination_id"] != station_id:
            raise EconomyError("delivery requires an active contract at its destination")
        job["status"] = "ready_for_payment"
        result.update(job_id=job["job_id"], status=job["status"], minutes=15)
    elif kind == "claim_reward":
        job = _job(economy, command["job_id"])
        destination = job.get("destination_id", job["origin_id"])
        if job["status"] != "ready_for_payment" or destination != station_id:
            raise EconomyError("reward requires a completed objective at the paying station")
        economy["credits"] += job["escrow"]
        job["escrow"] = 0; job["status"] = "completed"
        for item_id, qty in job.get("reward_items", {}).items():
            economy["inventory"][item_id] = economy["inventory"].get(item_id, 0) + qty
        _capacity(profile, economy)
        state["reputation"] = min(20, state["reputation"] + 1)
        memory["quests"]["economy:" + job["job_id"]]["status"] = "completed"
        result.update(job_id=job["job_id"], reward_credits=job["reward_credits"],
                      reward_items=job.get("reward_items", {}), minutes=10)
    elif kind == "abandon_job":
        job = _job(economy, command["job_id"])
        if job["status"] not in {"active", "ready_for_payment"}:
            raise EconomyError("job is not active")
        economy["stations"][job["origin_id"]]["vendors"][job["sponsor_id"]]["credits"] += job["escrow"]
        job["escrow"] = 0; job["status"] = "abandoned"
        memory["quests"]["economy:" + job["job_id"]]["status"] = "failed"
        result.update(job_id=job["job_id"], minutes=10)
    elif kind == "wait":
        result["minutes"] = _integer(command["minutes"], "wait duration", 1, 10080)
    memory["world_state"]["world_time_minutes"] = clock + result["minutes"]
    memory["world_state"]["mission_day"] = (clock + result["minutes"]) // 1440
    return result


def prepare_command(mod, memory, command):
    if not isinstance(command, dict) or command.get("kind") not in FIELDS:
        raise EconomyError("unknown economy command")
    if set(command) != FIELDS[command["kind"]]:
        raise EconomyError("economy command fields must exactly match its schema")
    for key, value in command.items():
        if key.endswith("_id") and (not isinstance(value, str) or not value or len(value) > 160):
            raise EconomyError("invalid economy identifier")
    if "expected_unit_price" in command:
        _integer(command["expected_unit_price"], "quoted price", 1)
    if "expected_price" in command:
        _integer(command["expected_price"], "quoted price", 1)
    candidate = deepcopy(memory)
    profile, economy = _state(mod, candidate)
    settle_economy(mod, candidate)
    quote = _apply(profile, candidate, command)
    if command["kind"] == "work_job":
        job = economy["jobs"][command["job_id"]]
        assessment = {"mode": "check", "skill_id": job["skill_id"], "difficulty": job["difficulty"],
                      "difficulty_reason": job["challenge"], "modifiers": [],
                      "stakes": {"success": "Complete one objective step", "partial_success": "Complete a step with a complication",
                                 "failure": "Spend the work interval without completing an objective step"}}
    else:
        task = "observe_public_area" if command["kind"] == "visit_sector" else "request_service"
        assessment = {"mode": "automatic", "task": task,
                      "reason": "Validated station transaction or routine interaction with its required resources and preconditions"}
    result = {"command": deepcopy(command), "quote": quote, "adjudication": assessment,
              "credits_after": economy["credits"], "cargo_mass_after_g": cargo_mass(profile, economy),
              "state_version": memory.get("state_version", 0), "initialization_pending": "economy" not in memory}
    result["quote_sha256"] = hashlib.sha256(json.dumps(result, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return result


def resolve_assessment(plan, assessment=None):
    expected = plan["adjudication"]
    if assessment is None:
        return expected
    if expected["mode"] != "check" or not isinstance(assessment, dict):
        raise EconomyError("routine economy transactions use their validated automatic assessment")
    if any(assessment.get(k) != expected[k] for k in ("mode", "skill_id", "difficulty")):
        raise EconomyError("job work must use its authored skill and difficulty")
    return {**expected, "modifiers": assessment.get("modifiers", [])}


def execute_command(mod, memory, command, outcome):
    profile, economy = _state(mod, memory)
    settle_economy(mod, memory)
    result = _apply(profile, memory, command, outcome)
    economy["activity_log"].append(result)
    del economy["activity_log"][:-40]
    return result
