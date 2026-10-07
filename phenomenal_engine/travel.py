from __future__ import annotations

from dataclasses import dataclass
import heapq
import math
import re
from typing import Any


def _norm(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", value.lower()).strip()


def _location_defs(mod: dict, memory: dict | None = None) -> dict[str, dict]:
    locations = {
        item["id"]: item
        for item in mod.get("locations", [])
        if isinstance(item, dict) and item.get("id")
    }
    if memory:
        for item in memory.get("travel_state", {}).get("dynamic_nodes", {}).values():
            if isinstance(item, dict) and item.get("id"):
                locations[item["id"]] = item
    return locations


def _route_defs(mod: dict, memory: dict | None = None) -> list[dict]:
    routes = [
        item for item in mod.get("travel_network", {}).get("routes", [])
        if isinstance(item, dict) and item.get("id") and item.get("from") and item.get("to")
    ]
    if memory:
        routes.extend(
            item for item in memory.get("travel_state", {}).get("dynamic_routes", {}).values()
            if isinstance(item, dict) and item.get("id") and item.get("from") and item.get("to")
        )
    return routes


def initial_travel_state(mod: dict) -> dict:
    current = mod.get("starting_state", {}).get("location")
    known_nodes = []
    for item in mod.get("locations", []):
        if not isinstance(item, dict) or not item.get("id"):
            continue
        if item.get("known_by_default", True) or item["id"] == current:
            known_nodes.append(item["id"])

    known_routes = []
    for route in mod.get("travel_network", {}).get("routes", []):
        if not isinstance(route, dict) or not route.get("id"):
            continue
        if route.get("visibility", "public") == "public":
            known_routes.append(route["id"])

    return {
        "known_nodes": sorted(set(known_nodes)),
        "known_routes": sorted(set(known_routes)),
        "visited_nodes": [current] if current else [],
        "route_overrides": {},
        "dynamic_nodes": {},
        "dynamic_routes": {},
        "last_route": None,
        "active_journey": None,
        "last_journey": None,
        "journey_history": [],
    }


def ensure_travel_state(mod: dict, memory: dict) -> dict:
    state = memory.setdefault("travel_state", initial_travel_state(mod))
    state.setdefault("known_nodes", [])
    state.setdefault("known_routes", [])
    state.setdefault("visited_nodes", [])
    state.setdefault("route_overrides", {})
    state.setdefault("dynamic_nodes", {})
    state.setdefault("dynamic_routes", {})
    state.setdefault("last_route", None)
    state.setdefault("active_journey", None)
    state.setdefault("last_journey", None)
    state.setdefault("journey_history", [])
    current = memory.get("world_state", {}).get("location")
    if current and current not in state["known_nodes"]:
        state["known_nodes"].append(current)
    if current and current not in state["visited_nodes"]:
        state["visited_nodes"].append(current)
    return state


def resolve_location(mod: dict, memory: dict, text: str, known_only: bool = True) -> str | None:
    query = _norm(text)
    if not query:
        return None
    locations = _location_defs(mod, memory)
    state = ensure_travel_state(mod, memory)
    known = set(state["known_nodes"])

    candidates: list[tuple[int, int, str]] = []
    for loc_id, item in locations.items():
        if known_only and loc_id not in known:
            continue
        labels = [loc_id, item.get("name", ""), *item.get("aliases", [])]
        for label in labels:
            label_norm = _norm(str(label))
            if not label_norm:
                continue
            if query == label_norm:
                return loc_id
            if label_norm in query:
                candidates.append((len(label_norm.split()), len(label_norm), loc_id))

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][2]
    return None


def infer_destination(mod: dict, memory: dict, action: str) -> str | None:
    return resolve_location(mod, memory, action, known_only=True)


def discover_node(mod: dict, memory: dict, node_id: str) -> bool:
    if node_id not in _location_defs(mod, memory):
        return False
    state = ensure_travel_state(mod, memory)
    if node_id in state["known_nodes"]:
        return False
    state["known_nodes"].append(node_id)
    state["known_nodes"].sort()
    return True


def discover_route(mod: dict, memory: dict, route_id: str) -> bool:
    if route_id not in {r["id"] for r in _route_defs(mod, memory)}:
        return False
    state = ensure_travel_state(mod, memory)
    if route_id in state["known_routes"]:
        return False
    state["known_routes"].append(route_id)
    state["known_routes"].sort()
    return True


def set_route_override(mod: dict, memory: dict, route_id: str, **changes: Any) -> None:
    if route_id not in {r["id"] for r in _route_defs(mod, memory)}:
        raise ValueError(f"unknown route: {route_id}")
    state = ensure_travel_state(mod, memory)
    override = state["route_overrides"].setdefault(route_id, {})
    override.update(changes)


def register_dynamic_node(
    mod: dict,
    memory: dict,
    node_id: str,
    name: str,
    *,
    map_position: dict | None = None,
    aliases: list[str] | None = None,
    known: bool = True,
) -> dict:
    if not node_id or node_id in _location_defs(mod, memory):
        raise ValueError(f"location id already exists or is invalid: {node_id!r}")
    state = ensure_travel_state(mod, memory)
    node = {
        "id": node_id,
        "name": name,
        "map": map_position or {},
        "aliases": aliases or [],
        "dynamic": True,
    }
    state["dynamic_nodes"][node_id] = node
    if known:
        discover_node(mod, memory, node_id)
    return node


def register_dynamic_route(
    mod: dict,
    memory: dict,
    route_id: str,
    from_id: str,
    to_id: str,
    *,
    minutes: float,
    mode: str = "walk",
    risk: float = 0.0,
    distance_m: float | None = None,
    bidirectional: bool = True,
    known: bool = True,
) -> dict:
    locations = _location_defs(mod, memory)
    if from_id not in locations or to_id not in locations:
        raise ValueError("dynamic route endpoints must already exist")
    if route_id in {r["id"] for r in _route_defs(mod, memory)}:
        raise ValueError(f"route id already exists: {route_id}")
    state = ensure_travel_state(mod, memory)
    route = {
        "id": route_id,
        "from": from_id,
        "to": to_id,
        "minutes": float(minutes),
        "mode": mode,
        "risk": float(risk),
        "distance_m": None if distance_m is None else max(0.0, float(distance_m)),
        "bidirectional": bool(bidirectional),
        "visibility": "public" if known else "hidden",
        "dynamic": True,
    }
    state["dynamic_routes"][route_id] = route
    if known:
        discover_route(mod, memory, route_id)
    return route


def _effective_route(route: dict, state: dict) -> dict:
    effective = dict(route)
    effective.update(state.get("route_overrides", {}).get(route["id"], {}))
    return effective


def _route_is_available(route: dict, state: dict) -> bool:
    if route["id"] not in set(state.get("known_routes", [])):
        return False
    effective = _effective_route(route, state)
    if effective.get("closed", False):
        return False
    return True


def _neighbors(mod: dict, memory: dict) -> dict[str, list[tuple[str, dict]]]:
    state = ensure_travel_state(mod, memory)
    graph: dict[str, list[tuple[str, dict]]] = {}
    for raw in _route_defs(mod, memory):
        if not _route_is_available(raw, state):
            continue
        route = _effective_route(raw, state)
        graph.setdefault(route["from"], []).append((route["to"], route))
        if route.get("bidirectional", True):
            reverse = dict(route)
            reverse["_reverse"] = True
            graph.setdefault(route["to"], []).append((route["from"], reverse))
    return graph


def _route_weight(route: dict, preference: str) -> float:
    minutes = max(0.0, float(route.get("minutes", 1.0)))
    risk = max(0.0, float(route.get("risk", 0.0)))
    if preference == "safest":
        return minutes + risk * 120.0
    if preference == "scenic":
        scenic = max(0.0, min(1.0, float(route.get("scenic", 0.0))))
        return minutes + risk * 20.0 - scenic * min(10.0, minutes * 0.35)
    return minutes + risk * 15.0


def plan_route(
    mod: dict,
    memory: dict,
    destination: str,
    *,
    origin: str | None = None,
    preference: str = "fastest",
) -> dict:
    state = ensure_travel_state(mod, memory)
    locations = _location_defs(mod, memory)
    origin_id = origin or memory.get("world_state", {}).get("location")
    dest_id = destination if destination in locations else resolve_location(mod, memory, destination)

    if not origin_id or origin_id not in locations:
        return {"status": "invalid_origin", "origin": origin_id, "destination": dest_id}
    if not dest_id or dest_id not in locations:
        return {"status": "unknown_destination", "origin": origin_id, "destination": destination}
    if dest_id not in set(state["known_nodes"]):
        return {"status": "unknown_destination", "origin": origin_id, "destination": dest_id}
    if origin_id == dest_id:
        return {
            "status": "already_there",
            "origin": origin_id,
            "destination": dest_id,
            "nodes": [origin_id],
            "segments": [],
            "total_minutes": 0.0,
            "total_distance_m": 0.0,
            "total_risk": 0.0,
            "preference": preference,
        }

    graph = _neighbors(mod, memory)
    queue: list[tuple[float, str]] = [(0.0, origin_id)]
    best = {origin_id: 0.0}
    prev: dict[str, tuple[str, dict]] = {}

    while queue:
        cost, node = heapq.heappop(queue)
        if cost != best.get(node):
            continue
        if node == dest_id:
            break
        for neighbor, route in graph.get(node, []):
            new_cost = cost + _route_weight(route, preference)
            if new_cost < best.get(neighbor, math.inf):
                best[neighbor] = new_cost
                prev[neighbor] = (node, route)
                heapq.heappush(queue, (new_cost, neighbor))

    if dest_id not in prev:
        return {
            "status": "unreachable",
            "origin": origin_id,
            "destination": dest_id,
            "preference": preference,
        }

    segments = []
    node = dest_id
    while node != origin_id:
        prior, route = prev[node]
        segments.append({
            "route_id": route["id"],
            "from": prior,
            "to": node,
            "mode": route.get("mode", "walk"),
            "minutes": float(route.get("minutes", 1.0)),
            "risk": float(route.get("risk", 0.0)),
            "distance_m": (
                None if route.get("distance_m") is None
                else max(0.0, float(route.get("distance_m", 0.0)))
            ),
            "scenic": float(route.get("scenic", 0.0)),
            "access": route.get("access", "public"),
            "description": route.get("description"),
            "reverse": bool(route.get("_reverse", False)),
        })
        node = prior
    segments.reverse()

    nodes = [origin_id] + [segment["to"] for segment in segments]
    total_minutes = sum(segment["minutes"] for segment in segments)
    measured_distances = [
        segment["distance_m"] for segment in segments
        if segment.get("distance_m") is not None
    ]
    total_distance_m = (
        sum(measured_distances) if len(measured_distances) == len(segments) else None
    )
    survival = 1.0
    for segment in segments:
        survival *= 1.0 - max(0.0, min(1.0, segment["risk"]))
    total_risk = 1.0 - survival

    return {
        "status": "ok",
        "origin": origin_id,
        "destination": dest_id,
        "nodes": nodes,
        "segments": segments,
        "total_minutes": round(total_minutes, 3),
        "total_distance_m": (
            None if total_distance_m is None else round(total_distance_m, 3)
        ),
        "total_risk": round(total_risk, 6),
        "preference": preference,
    }


def travel_pulses(mod: dict, route_plan: dict) -> int:
    if route_plan.get("status") != "ok":
        return 1
    minutes_per_pulse = max(
        1.0,
        float(mod.get("travel_network", {}).get("minutes_per_world_pulse", 10.0)),
    )
    return max(1, int(math.ceil(float(route_plan.get("total_minutes", 0.0)) / minutes_per_pulse)))


def _journey_snapshot(journey: dict | None) -> dict | None:
    if not journey:
        return None
    segments = journey.get("segments", [])
    index = int(journey.get("next_segment_index", 0))
    current_node = journey.get("current_node", journey.get("origin"))
    next_segment = segments[index] if 0 <= index < len(segments) else None
    return {
        "status": journey.get("status", "active"),
        "origin": journey.get("origin"),
        "destination": journey.get("destination"),
        "preference": journey.get("preference", "fastest"),
        "nodes": list(journey.get("nodes", [])),
        "segments": list(segments),
        "current_node": current_node,
        "next_node": next_segment.get("to") if next_segment else None,
        "next_segment_index": index,
        "completed_segments": index,
        "total_segments": len(segments),
        "total_minutes": float(journey.get("total_minutes", 0.0)),
        "total_distance_m": journey.get("total_distance_m"),
        "elapsed_minutes": float(journey.get("elapsed_minutes", 0.0)),
        "elapsed_distance_m": float(journey.get("elapsed_distance_m", 0.0)),
        "remaining_minutes": max(
            0.0,
            float(journey.get("total_minutes", 0.0))
            - float(journey.get("elapsed_minutes", 0.0)),
        ),
        "remaining_distance_m": (
            None if journey.get("total_distance_m") is None
            else max(
                0.0,
                float(journey.get("total_distance_m", 0.0))
                - float(journey.get("elapsed_distance_m", 0.0)),
            )
        ),
        "started_turn": journey.get("started_turn"),
        "blocked_reason": journey.get("blocked_reason"),
    }


def active_journey(memory: dict) -> dict | None:
    return _journey_snapshot(memory.get("travel_state", {}).get("active_journey"))


def begin_journey(
    mod: dict,
    memory: dict,
    destination: str,
    *,
    preference: str = "fastest",
) -> dict:
    state = ensure_travel_state(mod, memory)
    plan = plan_route(mod, memory, destination, preference=preference)
    if plan.get("status") == "already_there":
        completed = {
            **plan,
            "status": "completed",
            "current_node": plan.get("destination"),
            "next_segment_index": 0,
            "elapsed_minutes": 0.0,
            "started_turn": memory.get("turn"),
        }
        state["last_journey"] = completed
        state["active_journey"] = None
        return _journey_snapshot(completed) or completed
    if plan.get("status") != "ok":
        return plan

    previous = state.get("active_journey")
    if previous:
        previous = dict(previous)
        previous["status"] = "rerouted"
        state["journey_history"].append(_journey_snapshot(previous))

    journey = {
        **plan,
        "status": "active",
        "current_node": plan["origin"],
        "next_segment_index": 0,
        "elapsed_minutes": 0.0,
        "elapsed_distance_m": 0.0,
        "started_turn": memory.get("turn"),
        "blocked_reason": None,
    }
    state["active_journey"] = journey
    return _journey_snapshot(journey) or journey


def _effective_segment(mod: dict, memory: dict, segment: dict) -> dict | None:
    state = ensure_travel_state(mod, memory)
    route_id = segment.get("route_id")
    for raw in _route_defs(mod, memory):
        if raw.get("id") != route_id:
            continue
        if not _route_is_available(raw, state):
            return None
        route = _effective_route(raw, state)
        forward = route.get("from") == segment.get("from") and route.get("to") == segment.get("to")
        reverse = (
            bool(route.get("bidirectional", True))
            and route.get("to") == segment.get("from")
            and route.get("from") == segment.get("to")
        )
        if not (forward or reverse):
            return None
        return {
            "route_id": route["id"],
            "from": segment["from"],
            "to": segment["to"],
            "mode": route.get("mode", "walk"),
            "minutes": float(route.get("minutes", 1.0)),
            "risk": float(route.get("risk", 0.0)),
            "distance_m": (
                None if route.get("distance_m") is None
                else max(0.0, float(route.get("distance_m", 0.0)))
            ),
            "scenic": float(route.get("scenic", 0.0)),
            "access": route.get("access", "public"),
            "description": route.get("description"),
            "reverse": reverse,
        }
    return None


def advance_journey(mod: dict, memory: dict, *, legs: int = 1) -> dict:
    state = ensure_travel_state(mod, memory)
    journey = state.get("active_journey")
    if not journey:
        return {"status": "no_active_journey"}

    if journey.get("status") == "blocked":
        return _journey_snapshot(journey) or {"status": "blocked"}

    legs = max(1, int(legs))
    traversed = []
    leg_minutes = 0.0

    for _ in range(legs):
        index = int(journey.get("next_segment_index", 0))
        segments = journey.get("segments", [])
        if index >= len(segments):
            break

        planned = segments[index]
        current = memory.get("world_state", {}).get("location")
        if current != planned.get("from"):
            journey["status"] = "blocked"
            journey["blocked_reason"] = "location_changed"
            break

        effective = _effective_segment(mod, memory, planned)
        if effective is None:
            journey["status"] = "blocked"
            journey["blocked_reason"] = "route_unavailable"
            break

        ws = memory.setdefault("world_state", {})
        ws["location"] = effective["to"]
        ws["world_time_minutes"] = (
            float(ws.get("world_time_minutes", 0.0)) + effective["minutes"]
        )
        journey["current_node"] = effective["to"]
        journey["next_segment_index"] = index + 1
        journey["elapsed_minutes"] = (
            float(journey.get("elapsed_minutes", 0.0)) + effective["minutes"]
        )
        if effective.get("distance_m") is not None:
            journey["elapsed_distance_m"] = (
                float(journey.get("elapsed_distance_m", 0.0))
                + float(effective["distance_m"])
            )
        leg_minutes += effective["minutes"]
        traversed.append(effective)

        if effective["to"] not in state["visited_nodes"]:
            state["visited_nodes"].append(effective["to"])
        if effective["to"] not in state["known_nodes"]:
            state["known_nodes"].append(effective["to"])

    state["visited_nodes"].sort()
    state["known_nodes"].sort()

    if (
        journey.get("status") != "blocked"
        and int(journey.get("next_segment_index", 0)) >= len(journey.get("segments", []))
    ):
        journey["status"] = "completed"
        journey["current_node"] = journey.get("destination")
        snapshot = _journey_snapshot(journey) or dict(journey)
        snapshot["traversed_segments"] = traversed
        snapshot["leg_minutes"] = leg_minutes
        state["last_journey"] = dict(journey)
        state["journey_history"].append(_journey_snapshot(journey))
        del state["journey_history"][:-20]
        state["last_route"] = {
            "status": "ok",
            "origin": journey.get("origin"),
            "destination": journey.get("destination"),
            "nodes": journey.get("nodes", []),
            "segments": journey.get("segments", []),
            "total_minutes": journey.get("total_minutes", 0.0),
            "total_risk": journey.get("total_risk", 0.0),
            "preference": journey.get("preference", "fastest"),
        }
        state["active_journey"] = None
        return snapshot

    snapshot = _journey_snapshot(journey) or dict(journey)
    snapshot["traversed_segments"] = traversed
    snapshot["leg_minutes"] = leg_minutes
    return snapshot


def reroute_journey(
    mod: dict,
    memory: dict,
    *,
    preference: str | None = None,
) -> dict:
    state = ensure_travel_state(mod, memory)
    journey = state.get("active_journey")
    if not journey:
        return {"status": "no_active_journey"}
    destination = journey.get("destination")
    chosen = preference or journey.get("preference", "fastest")
    return begin_journey(mod, memory, destination, preference=chosen)


def cancel_journey(mod: dict, memory: dict) -> dict:
    state = ensure_travel_state(mod, memory)
    journey = state.get("active_journey")
    if not journey:
        return {"status": "no_active_journey"}
    journey = dict(journey)
    journey["status"] = "cancelled"
    snapshot = _journey_snapshot(journey) or journey
    state["last_journey"] = journey
    state["journey_history"].append(snapshot)
    del state["journey_history"][:-20]
    state["active_journey"] = None
    return snapshot


def travel_pulses_for_minutes(mod: dict, minutes: float) -> int:
    if minutes <= 0:
        return 1
    minutes_per_pulse = max(
        1.0,
        float(mod.get("travel_network", {}).get("minutes_per_world_pulse", 10.0)),
    )
    pulses = max(1, int(math.ceil(float(minutes) / minutes_per_pulse)))
    max_pulses = max(
        1,
        int(mod.get("travel_network", {}).get("max_world_pulses_per_leg", 24)),
    )
    return min(pulses, max_pulses)


def apply_route(mod: dict, memory: dict, route_plan: dict) -> dict:
    if route_plan.get("status") not in {"ok", "already_there"}:
        return route_plan

    state = ensure_travel_state(mod, memory)
    ws = memory.setdefault("world_state", {})
    destination = route_plan["destination"]
    ws["location"] = destination
    ws["world_time_minutes"] = float(ws.get("world_time_minutes", 0.0)) + float(route_plan.get("total_minutes", 0.0))

    for node in route_plan.get("nodes", []):
        if node not in state["visited_nodes"]:
            state["visited_nodes"].append(node)
        if node not in state["known_nodes"]:
            state["known_nodes"].append(node)
    state["visited_nodes"].sort()
    state["known_nodes"].sort()
    state["last_route"] = route_plan
    return route_plan


def visible_map(mod: dict, memory: dict) -> dict:
    state = ensure_travel_state(mod, memory)
    locations = _location_defs(mod, memory)
    known_nodes = set(state["known_nodes"])
    nodes = []
    for loc_id in sorted(known_nodes):
        item = locations.get(loc_id)
        if not item:
            continue
        nodes.append({
            "id": loc_id,
            "name": item.get("name", loc_id),
            "map": item.get("map", {}),
            "region": item.get("region"),
            "visited": loc_id in set(state["visited_nodes"]),
            "current": loc_id == memory.get("world_state", {}).get("location"),
        })

    edges = []
    for route in _route_defs(mod, memory):
        if route["id"] not in set(state["known_routes"]):
            continue
        effective = _effective_route(route, state)
        if effective["from"] not in known_nodes or effective["to"] not in known_nodes:
            continue
        edges.append({
            "id": effective["id"],
            "from": effective["from"],
            "to": effective["to"],
            "minutes": float(effective.get("minutes", 1.0)),
            "mode": effective.get("mode", "walk"),
            "risk": float(effective.get("risk", 0.0)),
            "distance_m": (
                None if effective.get("distance_m") is None
                else max(0.0, float(effective.get("distance_m", 0.0)))
            ),
            "access": effective.get("access", "public"),
            "closed": bool(effective.get("closed", False)),
            "bidirectional": bool(effective.get("bidirectional", True)),
        })

    journey = active_journey(memory)
    active_nodes = set(journey.get("nodes", [])) if journey else set()
    active_route_ids = {
        item.get("route_id") for item in journey.get("segments", [])
    } if journey else set()
    destination = journey.get("destination") if journey else None
    next_stop = journey.get("next_node") if journey else None

    for node in nodes:
        node["on_active_journey"] = node["id"] in active_nodes
        node["destination"] = node["id"] == destination
        node["next_stop"] = node["id"] == next_stop
        node["selectable_destination"] = not node["current"]
    for edge in edges:
        edge["on_active_journey"] = edge["id"] in active_route_ids

    return {
        "current_location": memory.get("world_state", {}).get("location"),
        "world_time_minutes": float(memory.get("world_state", {}).get("world_time_minutes", 0.0)),
        "nodes": nodes,
        "edges": edges,
        "active_journey": journey,
        "interaction": {
            "destination_selection": True,
            "selection_behavior": "focus_and_preview_only",
            "movement_requires_confirmation": True,
            "preview_fields": [
                "destination",
                "total_distance_m",
                "total_minutes",
                "segments",
                "risk",
                "access",
            ],
            "route_preferences": ["fastest", "safest", "scenic"],
            "start": {
                "kind": "travel_start",
                "label": "Confirm Travel",
                "required": ["destination_id"],
                "optional": ["preference"],
            },
            "continue": {
                "kind": "travel_continue",
                "enabled": bool(journey and journey.get("status") == "active"),
            },
            "reroute": {
                "kind": "travel_reroute",
                "enabled": bool(journey),
                "optional": ["preference"],
            },
            "cancel": {
                "kind": "travel_cancel",
                "enabled": bool(journey),
            },
            "default_advance": "one_edge_per_authoritative_turn",
        },
    }
