"""Inspectable, credential-free action assessments. No RNG or state writes here.

Assessments are supplied by the trusted director, never parsed as instructions
from player text. They describe narrative stakes, not arbitrary state effects.
"""
from __future__ import annotations

from copy import deepcopy
import json
import math
from pathlib import Path

from .probability import logistic_success_probability
from .story import matching_action_rule

VERSION = "1.0.0"
AUTOMATIC_TASKS = {
    "read_available_information", "send_message", "request_service",
    "observe_public_area", "routine_movement",
}


class AdjudicationError(ValueError):
    pass


def _text(value, label, limit=600):
    if not isinstance(value, str) or not value.strip() or len(value) > limit:
        raise AdjudicationError(f"{label} must be nonempty text (max {limit} characters)")
    return value.strip()


def _number(value, label, lo, hi):
    if type(value) not in (int, float) or not math.isfinite(value) or not lo <= value <= hi:
        raise AdjudicationError(f"{label} must be a finite number in [{lo}, {hi}]")
    return float(value)


def player_profile(mod, memory):
    """Old saves use the authored baseline without rewriting their old ledger."""
    if "player_profile" in memory:
        raw, source = memory["player_profile"], "campaign"
    else:
        raw = mod.get("player_setup", {}).get("character_profile", {"skills": {"general": 0}})
        source = "mod_default_for_legacy_save"
    if not isinstance(raw, dict) or not isinstance(raw.get("skills"), dict):
        raise AdjudicationError("character profile requires a skills object")
    skills = {}
    for name, value in raw["skills"].items():
        _text(name, "skill ID", 80)
        skills[name] = _number(value, "skill rating", 0, 3)
    if not skills:
        raise AdjudicationError("character profile needs at least one skill")
    return {**deepcopy(raw), "skills": skills}, source


def load_adjudication(source):
    if source is None:
        return None
    if isinstance(source, dict):
        return deepcopy(source)
    text = str(source).strip()
    value = json.loads(text if text.startswith("{") else Path(source).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise AdjudicationError("adjudication must be an object")
    return value


def _check(mod, memory, spec, temperature, profile, profile_source):
    if not isinstance(spec, dict):
        raise AdjudicationError("each check must be an object")
    allowed = {"skill_id", "difficulty", "difficulty_reason", "modifiers", "stakes", "target_id"}
    if set(spec) - allowed:
        raise AdjudicationError("unknown check fields: " + ", ".join(sorted(set(spec) - allowed)))
    skill_id = _text(spec.get("skill_id"), "skill ID", 80)
    if skill_id not in profile["skills"]:
        raise AdjudicationError(f"unknown character skill: {skill_id}")
    difficulty = _number(spec.get("difficulty"), "difficulty", -2, 4)
    reason = _text(spec.get("difficulty_reason"), "difficulty reason")
    target = spec.get("target_id")
    if target is not None:
        _text(target, "target ID", 80)
        if target not in memory.get("characters", {}):
            from .economy import station_snapshot
            station = station_snapshot(mod, memory) if mod.get("economy_profile") else None
            if not station or target not in {vendor["npc"]["id"] for vendor in station["vendors"]}:
                raise AdjudicationError("unknown NPC target")
    modifiers = spec.get("modifiers", [])
    if not isinstance(modifiers, list) or len(modifiers) > 8:
        raise AdjudicationError("modifiers must be a list of at most eight entries")
    normalized = []
    seen = set()
    for item in modifiers:
        if not isinstance(item, dict) or set(item) != {"value", "reason", "source"}:
            raise AdjudicationError("modifier requires exactly value, reason and source")
        source = _text(item["source"], "modifier source", 120)
        if source in seen:
            raise AdjudicationError("duplicate modifier source; do not count the same advantage twice")
        seen.add(source)
        normalized.append({"value": _number(item["value"], "modifier", -0.5, 0.5),
                           "reason": _text(item["reason"], "modifier reason"), "source": source})
    context = max(-1.0, min(1.0, sum(m["value"] for m in normalized)))
    stakes = spec.get("stakes")
    if not isinstance(stakes, dict) or set(stakes) != {"success", "partial_success", "failure"}:
        raise AdjudicationError("stakes require success, partial_success and failure descriptions")
    stakes = {key: _text(value, f"{key} stakes") for key, value in stakes.items()}
    skill = profile["skills"][skill_id]
    return {"mode": "check", "skill_id": skill_id, "skill": skill,
            "profile_source": profile_source, "difficulty": difficulty,
            "difficulty_reason": reason, "modifiers": normalized, "context": context,
            "temperature": temperature, "success_probability": logistic_success_probability(skill, difficulty, context, temperature),
            "target_id": target, "stakes": stakes}


def prepare_adjudication(mod, memory, action, assessment=None, *, strict=False,
                         skill=0.0, difficulty=0.0, context=0.0, apply_action_rules=True):
    """Preview inputs and odds. Validate everything before any engine mutation."""
    _text(action, "action", 2000)
    temperature = _number(mod.get("simulation_profile", {}).get("skill_temperature", 1.0),
                          "temperature", 0.01, 10)
    profile, profile_source = player_profile(mod, memory)
    rule = matching_action_rule(mod, memory, action) if apply_action_rules else None
    if rule is not None and rule.get("deterministic", False):
        # Authored state guards/interlocks outrank a director's convenience assessment.
        if assessment is not None:
            raise AdjudicationError("authored deterministic action needs no adjudication override")
        return {"version": VERSION, "mode": "automatic", "source": "authored_rule",
                "rule_id": rule["id"], "reason": "Authored deterministic action with satisfied preconditions",
                "success_probability": 1.0, "consumes_action_rng": False}
    if assessment is None:
        if strict:
            raise AdjudicationError("adjudication_required: provide an automatic task assessment or an explained skill check; no silent 50% fallback")
        # Compatibility for existing low-level callers with numeric resolution arguments.
        skill = _number(skill, "skill", -4, 4)
        difficulty = _number(difficulty, "difficulty", -4, 4)
        context = _number(context, "context", -4, 4)
        return {"version": VERSION, "mode": "check", "source": "legacy_numeric",
                "skill": skill, "difficulty": difficulty, "context": context, "temperature": temperature,
                "success_probability": logistic_success_probability(skill, difficulty, context, temperature),
                "warning": "Legacy numeric inputs; use an explicit assessment for role-playing adjudication."}
    if not isinstance(assessment, dict):
        raise AdjudicationError("adjudication must be an object")
    mode = assessment.get("mode")
    if mode == "automatic":
        if set(assessment) != {"mode", "task", "reason"} or assessment.get("task") not in AUTOMATIC_TASKS:
            raise AdjudicationError("automatic assessment requires a supported task and reason")
        return {"version": VERSION, "mode": mode, "source": "director",
                "task": assessment["task"], "reason": _text(assessment["reason"], "automatic reason"),
                "success_probability": 1.0, "consumes_action_rng": False,
                "scope": "The named routine task only; no implied NPC agreement, purchase, repair or resource effect."}
    if mode == "check":
        normalized = _check(mod, memory, {k: v for k, v in assessment.items() if k != "mode"}, temperature, profile, profile_source)
        return {"version": VERSION, "source": "director", **normalized}
    if mode == "group":
        if set(assessment) != {"mode", "checks", "success_policy"}:
            raise AdjudicationError("group assessment requires checks and success_policy")
        specs = assessment["checks"]
        if not isinstance(specs, list) or not 1 <= len(specs) <= 8:
            raise AdjudicationError("group needs one to eight NPC checks")
        checks = [_check(mod, memory, spec, temperature, profile, profile_source) for spec in specs]
        targets = [check["target_id"] for check in checks]
        if None in targets or len(set(targets)) != len(targets):
            raise AdjudicationError("group checks require distinct NPC targets")
        policy = assessment["success_policy"]
        if policy not in {"all", "any"}:
            raise AdjudicationError("success_policy must be all or any")
        ps = [check["success_probability"] for check in checks]
        p = math.prod(ps) if policy == "all" else 1 - math.prod(1 - value for value in ps)
        return {"version": VERSION, "mode": mode, "source": "director", "checks": checks,
                "success_policy": policy, "success_probability": p,
                "probability_assumption": "Independent conditional checks; shared conditions belong in each assessment."}
    raise AdjudicationError("adjudication mode must be automatic, check or group")
