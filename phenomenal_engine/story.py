from __future__ import annotations

from copy import deepcopy
import re

from .travel import apply_route, discover_node, discover_route, infer_destination, plan_route, set_route_override, travel_pulses

ACTION_MODES = {
    "combat": {
        "attack", "fight", "strike", "shoot", "fire", "stab", "punch", "kick",
        "wrestle", "ambush", "duel", "weapon", "combat", "block", "parry"
    },
    "investigate": {
        "investigate", "inspect", "examine", "search", "trace", "analyze", "analyse",
        "question", "interrogate", "evidence", "clue", "scan", "audit", "decode"
    },
    "explore": {
        "explore", "wander", "look", "visit", "enter", "follow", "climb", "descend",
        "walk", "roam", "peek", "open", "door", "alley", "tunnel"
    },
    "social": {
        "talk", "ask", "tell", "persuade", "bargain", "negotiate", "comfort",
        "threaten", "apologize", "apologise", "promise", "joke", "listen"
    },
    "stealth": {
        "hide", "sneak", "stealth", "shadow", "conceal", "bypass", "pick", "silent"
    },
    "travel": {
        "travel", "ride", "fly", "ferry", "train", "rail", "depart", "leave", "return",
        "cross", "journey", "wait", "rest", "sleep"
    },
    "craft": {
        "build", "repair", "craft", "make", "modify", "assemble", "cook", "program",
        "rewire", "fix", "design"
    },
}

MODE_ORDER = ("combat", "investigate", "explore", "social", "stealth", "travel", "craft", "general")


def _words(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9'-]+", text.lower()))


def classify_action(action: str) -> str:
    words = _words(action)
    scored = []
    for mode, keywords in ACTION_MODES.items():
        scored.append((len(words & keywords), mode))
    score, mode = max(scored, default=(0, "general"))
    return mode if score > 0 else "general"


def initial_story_state(mod: dict) -> dict:
    threads = {}
    for item in mod.get("story_threads", []):
        if not isinstance(item, dict) or not item.get("id"):
            continue
        status = item.get("initial_status", "hidden")
        threads[item["id"]] = {
            "id": item["id"],
            "title": item.get("title", item["id"]),
            "tier": item.get("tier", "side"),
            "status": status,
            "interest": int(item.get("initial_interest", 0)),
            "stage": int(item.get("initial_stage", 0)),
            "last_touched_turn": None,
        }

    npc_agendas = {}
    for item in mod.get("npc_agendas", []):
        if not isinstance(item, dict) or not item.get("id"):
            continue
        npc_agendas[item["id"]] = {
            "id": item["id"],
            "character_id": item.get("character_id"),
            "progress": 0,
            "last_advanced_turn": None,
        }

    world_events = {}
    for item in mod.get("world_events", []):
        if not isinstance(item, dict) or not item.get("id"):
            continue
        world_events[item["id"]] = {
            "id": item["id"],
            "triggered": False,
            "last_checked_turn": 0,
        }

    return {
        "world_pulse": 0,
        "threads": threads,
        "npc_agendas": npc_agendas,
        "world_events": world_events,
        "ambient_history": [],
    }


def initial_player_experience() -> dict:
    return {
        "mode_counts": {mode: 0 for mode in MODE_ORDER},
        "recent_modes": [],
        "recent_actions": [],
        "explicit_preferences": {},
        "principles": [
            "Use play choices as weak evidence, not proof of what the player enjoys.",
            "Keep adaptation inspectable and campaign-local.",
            "Do not optimize for compulsive use, session length, spending, or emotional dependency.",
            "Prefer variety, agency, clarity, and satisfying consequences over retention metrics.",
        ],
    }


def _thread_definition(mod: dict, thread_id: str) -> dict | None:
    for item in mod.get("story_threads", []):
        if isinstance(item, dict) and item.get("id") == thread_id:
            return item
    return None


def _quest_definition(mod: dict, quest_id: str) -> dict | None:
    for item in mod.get("quests", []):
        if isinstance(item, dict) and item.get("id") == quest_id:
            return item
    return None


def _touches_thread(action: str, thread: dict) -> bool:
    haystack = action.lower()
    for trigger in thread.get("triggers", []):
        if str(trigger).lower() in haystack:
            return True
    return False


def _promote_thread(memory: dict, mod: dict, state: dict, definition: dict) -> dict | None:
    previous = state["status"]
    interest = state["interest"]
    rumor_at = int(definition.get("rumor_at", 1))
    lead_at = int(definition.get("lead_at", 2))
    active_at = int(definition.get("active_at", 3))
    if interest >= active_at:
        state["status"] = "active"
    elif interest >= lead_at:
        state["status"] = "lead"
    elif interest >= rumor_at:
        state["status"] = "rumor"

    if state["status"] == previous:
        return None

    linked_quest = definition.get("quest_id")
    if linked_quest and state["status"] == "active":
        quest = memory.setdefault("quests", {}).get(linked_quest)
        if quest is not None and quest.get("status") in {"hidden", "rumor", "available"}:
            quest["status"] = "open"
        for node_id in definition.get("unlock_nodes", []):
            discover_node(mod, memory, node_id)
        for route_id in definition.get("unlock_routes", []):
            discover_route(mod, memory, route_id)

    public = definition.get("public_reveals", {})
    return {
        "thread_id": state["id"],
        "title": state["title"],
        "tier": state["tier"],
        "from": previous,
        "to": state["status"],
        "reveal": public.get(state["status"]),
    }


def _advance_npc_agendas(memory: dict, mod: dict, rng, pulses: int) -> list[dict]:
    developments = []
    story = memory["story_state"]
    turn = int(memory.get("turn", 0))
    for _ in range(pulses):
        for definition in mod.get("npc_agendas", []):
            if not isinstance(definition, dict) or not definition.get("id"):
                continue
            state = story["npc_agendas"].setdefault(
                definition["id"],
                {"id": definition["id"], "character_id": definition.get("character_id"), "progress": 0, "last_advanced_turn": None},
            )
            cadence = max(1, int(definition.get("cadence", 3)))
            chance = max(0.0, min(1.0, float(definition.get("chance", 0.35))))
            if (story["world_pulse"] + int(definition.get("offset", 0))) % cadence != 0:
                continue
            if rng.random() >= chance:
                continue
            state["progress"] += 1
            state["last_advanced_turn"] = turn
            hints = definition.get("public_hints", [])
            if hints:
                hint = hints[min(state["progress"] - 1, len(hints) - 1)]
                developments.append({
                    "kind": "npc_agenda",
                    "character_id": definition.get("character_id"),
                    "text": hint,
                    "source_id": definition["id"],
                })
    return developments


def _apply_effects(world_state: dict, effects: dict) -> None:
    for key, delta in effects.items():
        if isinstance(delta, (int, float)) and not isinstance(delta, bool):
            current = world_state.get(key, 0.0)
            if isinstance(current, (int, float)) and not isinstance(current, bool):
                world_state[key] = current + delta


def _advance_world_events(memory: dict, mod: dict, rng) -> list[dict]:
    developments = []
    story = memory["story_state"]
    ws = memory.setdefault("world_state", {})
    for definition in mod.get("world_events", []):
        if not isinstance(definition, dict) or not definition.get("id"):
            continue
        state = story["world_events"].setdefault(
            definition["id"], {"id": definition["id"], "triggered": False, "last_checked_turn": 0}
        )
        if state.get("triggered") and definition.get("once", True):
            continue

        state["last_checked_turn"] = story["world_pulse"]
        after_pulse = int(definition.get("after_pulse", 0))
        if story["world_pulse"] < after_pulse:
            continue
        chance = max(0.0, min(1.0, float(definition.get("chance", 0.0))))
        if chance <= 0.0 or rng.random() >= chance:
            continue

        state["triggered"] = True
        _apply_effects(ws, definition.get("effects", {}))
        for route_id, changes in definition.get("route_changes", {}).items():
            if isinstance(changes, dict):
                try:
                    set_route_override(mod, memory, route_id, **changes)
                except ValueError:
                    pass
        text = definition.get("public_text")
        if text:
            developments.append({
                "kind": "world_event",
                "text": text,
                "source_id": definition["id"],
            })
    return developments


def _update_experience(memory: dict, action: str, mode: str) -> None:
    xp = memory.setdefault("player_experience", initial_player_experience())
    counts = xp.setdefault("mode_counts", {m: 0 for m in MODE_ORDER})
    counts[mode] = int(counts.get(mode, 0)) + 1

    recent_modes = xp.setdefault("recent_modes", [])
    recent_modes.append(mode)
    del recent_modes[:-8]

    recent_actions = xp.setdefault("recent_actions", [])
    recent_actions.append(action[:240])
    del recent_actions[:-6]


def experience_directives(memory: dict) -> list[str]:
    xp = memory.get("player_experience", {})
    counts = xp.get("mode_counts", {})
    recent = xp.get("recent_modes", [])
    directives = [
        "Treat behavioral adaptation as a gentle suggestion, never as a command.",
        "Do not tell the player that an inferred activity pattern is their identity or preference.",
        "Never optimize scenes for compulsive engagement, spending, fear of missing out, or emotional dependency.",
    ]
    ranked = sorted(
        ((int(counts.get(mode, 0)), mode) for mode in MODE_ORDER if mode != "general"),
        reverse=True,
    )
    if ranked and ranked[0][0] >= 3:
        directives.append(
            f"The player has repeatedly chosen {ranked[0][1]} actions; keep that avenue rich while preserving alternatives."
        )
    if len(recent) >= 3 and len(set(recent[-3:])) == 1:
        directives.append(
            "The last several actions used the same play mode; offer a contrasting opportunity without forcing a change."
        )
    if not any(int(v) >= 3 for v in counts.values() if isinstance(v, int)):
        directives.append(
            "The preference signal is still sparse; prioritize authored variety and clear world affordances over personalization."
        )
    return directives


def visible_story_state(memory: dict) -> dict:
    story = memory.get("story_state", {})
    visible_threads = []
    for state in story.get("threads", {}).values():
        if state.get("status") == "hidden":
            continue
        visible_threads.append({
            "id": state.get("id"),
            "title": state.get("title"),
            "tier": state.get("tier"),
            "status": state.get("status"),
            "stage": state.get("stage", 0),
        })

    visible_quests = []
    for quest in memory.get("quests", {}).values():
        if quest.get("status") == "hidden":
            continue
        visible_quests.append({
            "id": quest.get("id"),
            "title": quest.get("title"),
            "tier": quest.get("tier", "side"),
            "status": quest.get("status", "open"),
        })

    return {
        "world_pulse": story.get("world_pulse", 0),
        "threads": visible_threads,
        "quests": visible_quests,
    }


def advance_story(mod: dict, memory: dict, action: str, outcome: dict, rng) -> dict:
    memory.setdefault("story_state", initial_story_state(mod))
    memory.setdefault("player_experience", initial_player_experience())

    mode = classify_action(action)
    _update_experience(memory, action, mode)

    travel_update = None
    elapsed_pulses = 1
    if mode == "travel":
        destination = infer_destination(mod, memory, action)
        if destination:
            words = _words(action)
            preference = (
                "safest" if words & {"safe", "safer", "safest", "careful", "carefully"}
                else "scenic" if words & {"scenic", "beautiful", "interesting", "long", "wander"}
                else "fastest"
            )
            travel_update = plan_route(
                mod,
                memory,
                destination,
                preference=preference,
            )
            if travel_update.get("status") in {"ok", "already_there"}:
                elapsed_pulses = travel_pulses(mod, travel_update)
                apply_route(mod, memory, travel_update)
        else:
            travel_update = {
                "status": "no_destination",
                "origin": memory.get("world_state", {}).get("location"),
            }

    story = memory["story_state"]

    breadcrumbs = []
    for definition in mod.get("story_threads", []):
        if not isinstance(definition, dict) or not definition.get("id"):
            continue
        state = story["threads"].setdefault(
            definition["id"],
            {
                "id": definition["id"],
                "title": definition.get("title", definition["id"]),
                "tier": definition.get("tier", "side"),
                "status": definition.get("initial_status", "hidden"),
                "interest": 0,
                "stage": 0,
                "last_touched_turn": None,
            },
        )
        if _touches_thread(action, definition):
            state["interest"] = int(state.get("interest", 0)) + 1
            state["last_touched_turn"] = memory.get("turn")
            promoted = _promote_thread(memory, mod, state, definition)
            if promoted:
                breadcrumbs.append(promoted)

    ambient = []
    for _ in range(elapsed_pulses):
        story["world_pulse"] = int(story.get("world_pulse", 0)) + 1
        ambient.extend(_advance_npc_agendas(memory, mod, rng, 1))
        ambient.extend(_advance_world_events(memory, mod, rng))

    if ambient:
        history = story.setdefault("ambient_history", [])
        history.extend(deepcopy(ambient))
        del history[:-30]

    return {
        "action_mode": mode,
        "travel": travel_update,
        "elapsed_world_pulses": elapsed_pulses,
        "breadcrumbs": breadcrumbs,
        "ambient_developments": ambient,
        "experience_directives": experience_directives(memory),
    }
