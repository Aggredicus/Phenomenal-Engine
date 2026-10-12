"""Authored campaign scenes, NPC conversations and consequence-driven endings.

Profiles are trusted declarative game content. Player prose cannot supply effects.
Views/quotes work on copies; execution occurs inside the transactional engine.
"""
from __future__ import annotations
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path

from .economy import _state as economy_state, _capacity, EconomyError
from .travel import discover_node, discover_route


class CampaignError(ValueError):
    pass


FILES = {"mirror_delivery": "mirror_delivery.json"}
ENDING_IDS = {"pristine_seed", "mir_of_morrowglass", "plural_mirrors", "open_sun", "sealed_away", "unfinished_delivery"}
SHIP_FIELDS = {"morrowglass_hull", "morrowglass_propellant_margin", "morrowglass_thermal_margin", "crew_trust", "heliograph_trust", "mercury_acceptance_probability", "tension"}
EFFECT_FIELDS = {"flags", "evidence", "relationships", "factions", "ship", "items_gain", "items_cost", "credits_gain", "credits_cost", "minutes", "ending", "unlock_nodes", "unlock_routes", "quest_updates"}
COMMAND_FIELDS = {"talk": {"kind", "npc_id", "topic_id"},
                  "propose_cooperation": {"kind", "policy", "npc_ids"},
                  "choose": {"kind", "scene_id", "choice_id"}}


def load_profile(mod):
    key = mod.get("campaign_profile")
    if key is None:
        return None
    if key not in FILES:
        raise CampaignError("unknown campaign profile")
    p = Path(__file__).resolve().parents[1] / "mods" / "campaigns" / FILES[key]
    data = json.loads(p.read_text(encoding="utf-8"))
    validate_profile(data)
    return data


def validate_profile(data):
    if not isinstance(data, dict) or data.get("schema_version") != "1.0.0":
        raise CampaignError("invalid campaign profile")
    if type(data.get("reward_pool")) is not int or data["reward_pool"] < 0:
        raise CampaignError("invalid campaign reward pool")
    for key in ("scenes", "couriers", "dialogues", "evidence", "epilogues"):
        if not isinstance(data.get(key), dict):
            raise CampaignError("campaign profile requires authored tables")

    def requirements(value):
        allowed = {"locations", "flags", "evidence", "exclude_flags", "awake", "sealed", "divergent_copy", "after_minutes", "before_minutes", "quorum"}
        if not isinstance(value, dict) or set(value) - allowed:
            raise CampaignError("unknown campaign requirement")
        for key in ("locations", "flags", "evidence", "exclude_flags"):
            if key in value and (not isinstance(value[key], list) or any(not isinstance(v, str) for v in value[key])):
                raise CampaignError("invalid campaign requirement list")
        for key in ("after_minutes", "before_minutes", "quorum"):
            if key in value and (type(value[key]) is not int or value[key] < 0):
                raise CampaignError("invalid campaign requirement threshold")
        for key in ("awake", "sealed", "divergent_copy"):
            if key in value and type(value[key]) is not bool:
                raise CampaignError("invalid campaign requirement flag")

    def effects(value):
        if not isinstance(value, dict) or set(value) - EFFECT_FIELDS or set(value.get("ship", {})) - SHIP_FIELDS:
            raise CampaignError("unsupported campaign effect; protected payload state cannot be changed")
        if value.get("ending") and (value["ending"] not in ENDING_IDS or value["ending"] not in data["epilogues"]):
            raise CampaignError("unknown ending")
        if type(value.get("minutes", 0)) is not int or not 0 <= value.get("minutes", 0) <= 10080:
            raise CampaignError("invalid scene duration")
        for key in value.get("evidence", []):
            if key not in data["evidence"]:
                raise CampaignError("unknown evidence reference")
        quantities = [value.get(k, 0) for k in ("credits_gain", "credits_cost")]
        quantities += list(value.get("items_gain", {}).values()) + list(value.get("items_cost", {}).values())
        if any(type(q) is not int or q < 0 for q in quantities):
            raise CampaignError("campaign resource effects require nonnegative integer quantities")
        deltas = list(value.get("ship", {}).values()) + list(value.get("relationships", {}).values()) + list(value.get("factions", {}).values())
        if any(type(d) not in (int, float) or not math.isfinite(d) for d in deltas):
            raise CampaignError("campaign deltas must be finite numbers")
        if set(value.get("relationships", {})) - set(data["couriers"]) or set(value.get("factions", {})) - set(data["factions"]):
            raise CampaignError("unknown campaign relationship or faction")

    for scene in data["scenes"].values():
        if not scene.get("locations") or not scene.get("choices"):
            raise CampaignError("scene requires locations and choices")
        requirements(scene.get("requires", {}))
        for choice in scene["choices"].values():
            requirements(choice.get("requires", {}))
            if choice.get("skill_id") and (type(choice.get("difficulty")) not in (int, float) or not -2 <= choice["difficulty"] <= 4):
                raise CampaignError("invalid scene difficulty")
            for branch in ("success", "partial_success", "failure"):
                effects(choice["outcomes"][branch].get("effects", {}))
    for topics in data["dialogues"].values():
        for topic in topics.values():
            requirements(topic.get("requires", {}))
            effects(topic.get("effects", {}))
    return data


def initial_campaign(mod, clock=0):
    profile = load_profile(mod)
    if profile is None:
        return None
    return {"schema_version": "1.0.0", "status": "ongoing", "initialized_at": clock,
            "scene_records": {}, "evidence": {}, "flags": {}, "topic_history": {},
            "contacts": {key: {"trust": 0, "emergency_comms": False, "coordinated_route": False,
                                "conditions": None} for key in profile["couriers"]},
            "factions": {key: 0 for key in profile["factions"]}, "journal": [],
            "reward_pool": profile["reward_pool"], "payload_receipt": None, "ending": None,
            "epilogue": None, "arrivals": {}, "last_day": clock // 1440}


def _state(mod, memory):
    profile = load_profile(mod)
    if profile is None:
        raise CampaignError("this adventure has no authored campaign")
    memory.setdefault("campaign", initial_campaign(mod, int(memory["world_state"].get("world_time_minutes", 0))))
    return profile, memory["campaign"]


def _requirements(memory, requires):
    state = memory["campaign"]
    location = memory["world_state"].get("location")
    awake = memory["world_state"].get("mirror_payload_status") == "activated_divergent"
    if requires.get("locations") and location not in requires["locations"]:
        return False
    if any(not state["flags"].get(key) for key in requires.get("flags", [])):
        return False
    if any(key not in state["evidence"] for key in requires.get("evidence", [])):
        return False
    if any(state["flags"].get(key) for key in requires.get("exclude_flags", [])):
        return False
    if requires.get("awake") and not awake or requires.get("sealed") and awake:
        return False
    if requires.get("divergent_copy") and not (awake or state["flags"].get("mara_divergent")):
        return False
    if memory["world_state"].get("world_time_minutes", 0) < requires.get("after_minutes", 0):
        return False
    if requires.get("before_minutes") is not None and memory["world_state"].get("world_time_minutes", 0) >= requires["before_minutes"]:
        return False
    shares = 1 + sum(value["available"] and value["share_verified"] for value in state["arrivals"].values())
    if shares < requires.get("quorum", 0):
        return False
    return True


def sync_campaign(mod, memory):
    if not mod.get("campaign_profile"):
        return []
    profile, state = _state(mod, memory)
    clock = int(memory["world_state"].get("world_time_minutes", 0))
    developments = []
    if state["status"] != "ongoing":
        return developments
    for npc_id, courier in profile["couriers"].items():
        if clock >= courier["arrival_minutes"] and npc_id not in state["arrivals"]:
            available = not (npc_id == "ren_ivo" and state["flags"].get("ren_stranded"))
            state["arrivals"][npc_id] = {"available": available, "share_verified": False,
                                        "public_status": "receiving-system arrival reported" if available else "delayed outside receiving system"}
            developments.append({"kind": "courier_report", "npc_id": npc_id,
                                 "text": courier["arrival_text"] if available else "Amber Wake remains delayed after the unresolved thermal incident."})
    for scene_id, scene in profile["scenes"].items():
        if scene_id in state["scene_records"]:
            continue
        requires = {"locations": scene["locations"], **scene.get("requires", {})}
        if _requirements(memory, requires):
            state["scene_records"][scene_id] = {"status": "available", "introduced_turn": memory.get("turn", 0)}
            developments.append({"kind": "encounter_available", "scene_id": scene_id,
                                 "title": scene["title"], "text": scene["opening"]})
    for scene_id, record in state["scene_records"].items():
        scene = profile["scenes"][scene_id]
        if record["status"] == "available" and scene.get("deadline_minutes"):
            record.setdefault("deadline", clock + scene["deadline_minutes"])
            if clock > record["deadline"]:
                record["status"] = "expired"
                state["journal"].append({"kind": "missed_window", "scene_id": scene_id,
                                         "text": scene["expiry_text"], "world_minute": clock})
                developments.append({"kind": "missed_window", "scene_id": scene_id, "text": scene["expiry_text"]})
    state["last_day"] = clock // 1440
    return developments


def campaign_view(mod, memory):
    candidate = deepcopy(memory)
    profile, state = _state(mod, candidate)
    sync_campaign(mod, candidate)
    location = candidate["world_state"].get("location")
    scenes = []
    for scene_id, record in state["scene_records"].items():
        scene = profile["scenes"][scene_id]
        if record["status"] != "available" or location not in scene["locations"] or not _requirements(candidate, scene.get("requires", {})):
            continue
        choices = [{"choice_id": key, "label": value["label"], "approach": value["approach"]}
                   for key, value in scene["choices"].items() if _requirements(candidate, value.get("requires", {}))]
        scenes.append({"scene_id": scene_id, "title": scene["title"], "act": scene["act"],
                       "opening": scene["opening"], "choices": choices, "deadline": record.get("deadline")})
    topics = {}
    for npc, entries in profile["dialogues"].items():
        if npc == "mirror_instance" and candidate["world_state"].get("mirror_payload_status") != "activated_divergent":
            continue
        topics[npc] = [{"topic_id": key, "title": value["title"]} for key, value in entries.items()
                       if _requirements(candidate, value.get("requires", {}))]
    return {"status": state["status"], "local_scenes": scenes, "conversation_topics": topics,
            "contacts": deepcopy(state["contacts"]), "faction_standing": deepcopy(state["factions"]),
            "evidence": list(deepcopy(state["evidence"]).values()), "journal": deepcopy(state["journal"][-20:]),
            "ending": state["ending"], "epilogue": state["epilogue"], "payload_receipt": state["payload_receipt"],
            "initialization_pending": "campaign" not in memory, "read_only": True}


def _effects(mod, profile, memory, effects):
    state = memory["campaign"]
    if set(effects) - EFFECT_FIELDS or set(effects.get("ship", {})) - SHIP_FIELDS:
        raise CampaignError("invalid effect")
    for key, value in effects.get("flags", {}).items():
        state["flags"][key] = value
    for key in effects.get("evidence", []):
        entry = {"id": key, **deepcopy(profile["evidence"][key])}
        state["evidence"][key] = entry
        if key not in memory.setdefault("facts", {}).setdefault("revealed", []):
            memory["facts"]["revealed"].append(key)
        if key == "quorum_record":
            memory["quests"]["main_fourth_reason"]["status"] = "completed"
        if key == "quorum_record" and memory["world_state"].get("location") in {"mercury_high_orbit", "caloris_terminus"}:
            for arrival in state["arrivals"].values():
                if arrival["available"]:
                    arrival["share_verified"] = True
    for npc, delta in effects.get("relationships", {}).items():
        if npc not in state["contacts"]:
            raise CampaignError("unknown relationship target")
        state["contacts"][npc]["trust"] = max(-3, min(3, state["contacts"][npc]["trust"] + delta))
        memory.setdefault("relationships", {})[npc] = {"trust": state["contacts"][npc]["trust"]}
    for faction, delta in effects.get("factions", {}).items():
        if faction not in state["factions"]:
            raise CampaignError("unknown faction")
        state["factions"][faction] = max(-3, min(3, state["factions"][faction] + delta))
    for field, delta in effects.get("ship", {}).items():
        ceiling = 10 if field == "tension" else 1
        memory["world_state"][field] = max(0, min(ceiling, round(memory["world_state"].get(field, 0) + delta, 6)))
    if any(key in effects for key in ("items_gain", "items_cost", "credits_gain", "credits_cost")):
        econ_profile, economy = economy_state(mod, memory)
        debit, credit = effects.get("credits_cost", 0), effects.get("credits_gain", 0)
        if economy["credits"] < debit or state["reward_pool"] < credit:
            raise CampaignError("insufficient credits or finite mission reward funds")
        economy["credits"] += credit - debit
        state["reward_pool"] += debit - credit
        for key, qty in effects.get("items_cost", {}).items():
            if economy["inventory"].get(key, 0) < qty:
                raise CampaignError("required supply is unavailable")
            economy["inventory"][key] -= qty
        for key, qty in effects.get("items_gain", {}).items():
            if key not in econ_profile["items"]:
                raise CampaignError("unknown authored reward item")
            economy["inventory"][key] = economy["inventory"].get(key, 0) + qty
        _capacity(econ_profile, economy)
    for node_id in effects.get("unlock_nodes", []):
        discover_node(mod, memory, node_id)
    for route_id in effects.get("unlock_routes", []):
        discover_route(mod, memory, route_id)
    for quest_id, status in effects.get("quest_updates", {}).items():
        if quest_id not in memory["quests"]:
            raise CampaignError("unknown quest")
        memory["quests"][quest_id]["status"] = status
    memory["world_state"]["world_time_minutes"] = int(memory["world_state"].get("world_time_minutes", 0)) + effects.get("minutes", 0)
    memory["world_state"]["mission_day"] = memory["world_state"]["world_time_minutes"] // 1440
    ending = effects.get("ending")
    if ending:
        if memory["world_state"].get("location") != "caloris_terminus":
            raise CampaignError("campaign ending requires actual arrival at Caloris Terminus")
        if ending == "pristine_seed" and memory["world_state"].get("mirror_payload_status") != "sealed_pristine":
            raise CampaignError("a divergent copy cannot be delivered as pristine")
        if ending == "mir_of_morrowglass" and memory["world_state"].get("mirror_payload_status") != "activated_divergent":
            raise CampaignError("the lived Morrowglass ending requires deliberate prior activation")
        if ending in {"open_sun", "plural_mirrors"} and ("quorum_record" not in state["evidence"] or 1 + sum(v["available"] and v["share_verified"] for v in state["arrivals"].values()) < 3):
            raise CampaignError("deployment settlement requires evidence and a physical three-share quorum")
        state["ending"] = ending
        state["status"] = "ongoing" if ending == "unfinished_delivery" else "epilogue"
        if ending != "unfinished_delivery":
            state["payload_receipt"] = {"holder": "Caloris receiving authority", "payload_state": memory["world_state"]["mirror_payload_status"],
                                        "world_minute": memory["world_state"]["world_time_minutes"],
                                        "deployment": "paused" if ending == "sealed_away" else "governed" if ending in {"open_sun", "plural_mirrors"} else "study_only"}
            memory["world_state"]["mirror_custody"] = "caloris_receiving_authority"
            memory["quests"]["main_delivery"]["status"] = "completed"
            memory["quests"]["main_mercury_hearing"]["status"] = "completed"
        state["epilogue"] = {"title": profile["epilogues"][ending]["title"], "text": profile["epilogues"][ending]["text"],
                             "crew_trust": memory["world_state"].get("crew_trust"), "courier_contacts": deepcopy(state["contacts"]),
                             "faction_standing": deepcopy(state["factions"]), "rescues": bool(state["flags"].get("ren_rescued")),
                             "evidence_count": len(state["evidence"])}


def _automatic(reason):
    return {"mode": "automatic", "task": "read_available_information", "reason": reason}


def _check(skill, difficulty, reason, modifiers=None):
    return {"mode": "check", "skill_id": skill, "difficulty": difficulty, "difficulty_reason": reason,
            "modifiers": modifiers or [], "stakes": {"success": "The authored approach achieves its goal",
            "partial_success": "The approach yields a limited result or added cost", "failure": "The approach yields its stated fallback consequence"}}


def _context(state):
    modifiers = []
    if state["factions"].get("open_sun_league", 0) > 0:
        modifiers.append({"value": .25, "source": "public_representation", "reason": "Established public representatives support the hearing"})
    if any(contact["emergency_comms"] for contact in state["contacts"].values()):
        modifiers.append({"value": .25, "source": "courier_witnesses", "reason": "A cooperating courier can corroborate your account"})
    return modifiers


def prepare_command(mod, memory, command):
    if not isinstance(command, dict) or not isinstance(command.get("kind"), str) or command.get("kind") not in COMMAND_FIELDS or set(command) != COMMAND_FIELDS[command["kind"]]:
        raise CampaignError("campaign command fields must exactly match its schema")
    for key, value in command.items():
        if key != "npc_ids" and (not isinstance(value, str) or not value or len(value) > 160):
            raise CampaignError("invalid campaign identifier")
    candidate = deepcopy(memory)
    profile, state = _state(mod, candidate)
    sync_campaign(mod, candidate)
    kind = command["kind"]
    preview = {"command": deepcopy(command), "state_version": memory.get("state_version", 0)}
    if kind == "talk":
        npc, topic = command["npc_id"], command["topic_id"]
        entry = profile["dialogues"].get(npc, {}).get(topic)
        if entry is None or not _requirements(candidate, entry.get("requires", {})):
            raise CampaignError("conversation topic is unavailable")
        if npc == "mirror_instance" and candidate["world_state"].get("mirror_payload_status") != "activated_divergent":
            raise CampaignError("Mir cannot speak or observe while sealed")
        preview.update(title=entry["title"], minutes=10, adjudication=_automatic("Available authored conversation; no uncertain persuasion implied"))
    elif kind == "propose_cooperation":
        ids = command["npc_ids"]
        if not isinstance(ids, list) or not 1 <= len(ids) <= 3 or any(not isinstance(n, str) for n in ids) or len(set(ids)) != len(ids) or any(n not in profile["couriers"] for n in ids):
            raise CampaignError("proposal requires distinct courier recipients")
        policy = command["policy"]
        if policy not in {"emergency_comms", "coordinated_route"}:
            raise CampaignError("unknown cooperation policy")
        unresolved = [n for n in ids if not state["contacts"][n][policy]]
        if not unresolved:
            assessment = _automatic("The selected agreement is already recorded")
        else:
            checks = []
            for npc in unresolved:
                definition = profile["couriers"][npc]
                mods = [{"value": .5, "source": "payload_isolation", "reason": "The policy explicitly forbids payload interconnection and shared custody"}]
                if state["contacts"][npc]["trust"] > 0:
                    mods.append({"value": .25, "source": "earned_trust", "reason": "An established cooperative interaction supports this request"})
                item = _check("leadership", definition["difficulty"][policy], definition["concern"], mods)
                item.pop("mode"); item["target_id"] = npc
                checks.append(item)
            assessment = {"mode": "group", "checks": checks, "success_policy": "any" if policy == "emergency_comms" else "all"}
        preview.update(minutes=15, adjudication=assessment, scope="Crew communications only; payloads remain isolated. No ship movement.")
    else:
        scene_id, choice_id = command["scene_id"], command["choice_id"]
        scene = profile["scenes"].get(scene_id)
        choice = scene.get("choices", {}).get(choice_id) if scene else None
        record = state["scene_records"].get(scene_id, {})
        if state["status"] != "ongoing" or not choice or record.get("status") != "available" or candidate["world_state"].get("location") not in scene["locations"] or not _requirements(candidate, scene.get("requires", {})) or not _requirements(candidate, choice.get("requires", {})):
            raise CampaignError("scene choice is unavailable, resolved, expired, or at another location")
        for branch in choice["outcomes"].values():
            trial = deepcopy(candidate)
            _effects(mod, profile, trial, branch.get("effects", {}))
        assessment = _check(choice["skill_id"], choice["difficulty"], choice["approach"], _context(state) if scene.get("hearing") else []) if choice.get("skill_id") else _automatic(choice["approach"])
        preview.update(title=scene["title"], choice=choice["label"], approach=choice["approach"], adjudication=assessment,
                       time_range_minutes=[min(o.get("effects", {}).get("minutes", 0) for o in choice["outcomes"].values()), max(o.get("effects", {}).get("minutes", 0) for o in choice["outcomes"].values())])
    preview["quote_sha256"] = hashlib.sha256(json.dumps(preview, sort_keys=True, separators=(",", ":")).encode()).hexdigest()
    return preview


def resolve_assessment(plan, supplied=None):
    expected = plan["adjudication"]
    if supplied is None:
        return expected
    if expected["mode"] == "check" and isinstance(supplied, dict) and all(supplied.get(k) == expected[k] for k in ("mode", "skill_id", "difficulty")):
        return {**expected, "modifiers": expected["modifiers"] + supplied.get("modifiers", [])}
    raise CampaignError("campaign action uses its authored assessment; only explained check modifiers may be added")


def execute_command(mod, memory, command, outcome):
    profile, state = _state(mod, memory)
    sync_campaign(mod, memory)
    kind = command["kind"]
    result = {"kind": kind}
    if kind == "talk":
        npc, topic = command["npc_id"], command["topic_id"]
        entry = profile["dialogues"][npc][topic]
        key = npc + ":" + topic
        if key not in state["topic_history"]:
            _effects(mod, profile, memory, entry.get("effects", {}))
            state["topic_history"][key] = True
        result.update(npc_id=npc, topic_id=topic, text=entry["text"])
        memory["world_state"]["world_time_minutes"] += 10
    elif kind == "propose_cooperation":
        responses = []
        rolled = {r["target_id"]: r for r in outcome.get("checks", [])}
        for npc in command["npc_ids"]:
            contact = state["contacts"][npc]
            r = rolled.get(npc)
            if contact[command["policy"]]:
                status = "already_agreed"
            elif r and r["success"]:
                contact[command["policy"]] = True; contact["trust"] = min(3, contact["trust"] + 1)
                status = "agreed"
            elif r and r["degree"] == "partial_success":
                contact["conditions"] = profile["couriers"][npc]["condition"]
                status = "conditional"
            else:
                status = "declined"
            memory.setdefault("relationships", {})[npc] = {"trust": contact["trust"]}
            text = profile["couriers"][npc]["responses"]["success" if status in {"agreed", "already_agreed"} else "partial_success" if status == "conditional" else "failure"]
            responses.append({"npc_id": npc, "status": status, "text": text, "conditions": contact["conditions"]})
        result.update(policy=command["policy"], responses=responses, payload_networking=False)
        memory["world_state"]["world_time_minutes"] += 15
    else:
        scene_id, choice_id = command["scene_id"], command["choice_id"]
        choice = profile["scenes"][scene_id]["choices"][choice_id]
        branch = "success" if outcome.get("success") else "partial_success" if outcome.get("degree") == "partial_success" else "failure"
        selected = choice["outcomes"][branch]
        _effects(mod, profile, memory, selected.get("effects", {}))
        state["scene_records"][scene_id].update(status="resolved", choice_id=choice_id, degree=outcome.get("degree"), turn=memory["turn"])
        result.update(scene_id=scene_id, choice_id=choice_id, text=selected["text"], effects=deepcopy(selected.get("effects", {})))
    memory["world_state"]["mission_day"] = int(memory["world_state"].get("world_time_minutes", 0)) // 1440
    state["journal"].append({**deepcopy(result), "world_minute": memory["world_state"].get("world_time_minutes", 0)})
    return result


def check_payload_custody(mod, memory, action):
    if not mod.get("campaign_profile") or not memory.get("campaign", {}).get("payload_receipt"):
        return
    from .story import matching_action_rule
    rule = matching_action_rule(mod, memory, action)
    if rule and "mir_activation" in rule["id"]:
        raise CampaignError("Mir custody has transferred; Morrowglass cannot activate the delivered vault")
