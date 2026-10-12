from __future__ import annotations
from copy import deepcopy
from .rng import derive_stream, PCG32
from .probability import sample_skill_check, consequence_severity, hazard_probability
from .memory import append_event, ENGINE_VERSION
from .narrative import build_scene_packet, PhenomenologyFrame
from .image_jobs import should_generate, enqueue
from .story import advance_story
from .adjudication import prepare_adjudication, player_profile
from .economy import prepare_command, resolve_assessment, execute_command, settle_economy

class Engine:
    def __init__(self, mod: dict, memory: dict, queue_path: str | None = None):
        self.mod = mod
        self.memory = memory
        self.queue_path = queue_path
        self.streams: dict[str, PCG32] = {}
        for label in ["actions", "world", "encounters", "game_theory", "images", "story"]:
            saved = memory.get("rng_streams", {}).get(label)
            self.streams[label] = PCG32.from_state_dict(saved) if saved else derive_stream(memory["master_seed"], label)

    def _persist_rng(self):
        self.memory["rng_streams"] = {k: v.state_dict() for k, v in self.streams.items()}

    def step(self, action, *args, economy_command=None, **kwargs):
        if economy_command is None:
            return self._step(action, *args, **kwargs)
        # Transactions run against a private candidate. Any validation, capacity
        # or resource error leaves caller memory and RNG untouched.
        worker = Engine(self.mod, deepcopy(self.memory), self.queue_path)
        packet = worker._step(action, *args, economy_command=economy_command, **kwargs)
        self.memory.clear()
        self.memory.update(worker.memory)
        self.streams = worker.streams
        return packet

    def _step(
        self,
        action: str,
        skill: float = 0.0,
        difficulty: float = 0.0,
        context: float = 0.0,
        frame: PhenomenologyFrame | None = None,
        significance: float = 0.5,
        idempotency_key: str | None = None,
        adjudication: dict | None = None,
        require_adjudication: bool = False,
        economy_command: dict | None = None,
    ) -> dict:
        adjudication_request = deepcopy(adjudication)
        if economy_command is not None:
            plan = prepare_command(self.mod, self.memory, economy_command)
            adjudication = resolve_assessment(plan, adjudication)
        assessment = prepare_adjudication(
            self.mod, self.memory, action, adjudication, strict=require_adjudication,
            skill=skill, difficulty=difficulty, context=context,
        )
        adopting_economy = bool(self.mod.get("economy_profile") and "economy" not in self.memory)
        economy_before = settle_economy(self.mod, self.memory)
        # Assessment errors must never consume RNG, initialize profiles or increment a turn.
        if "player_profile" not in self.memory:
            self.memory["player_profile"] = player_profile(self.mod, self.memory)[0]
        self.memory["engine_version"] = ENGINE_VERSION
        self.memory["turn"] += 1
        if assessment["mode"] == "automatic":
            outcome = {
                "success_probability": 1.0,
                "uniform_draw": None,
                "success": True,
                "margin": 1.0,
                "confidence": 1.0,
                "deterministic": True,
                "rule_id": assessment.get("rule_id"),
                "degree": "automatic_success",
            }
            outcome["consequence_severity"] = 0.0
        elif assessment["mode"] == "group":
            results = [self._resolve_check(check) for check in assessment["checks"]]
            successes = [result["success"] for result in results]
            success = all(successes) if assessment["success_policy"] == "all" else any(successes)
            outcome = {"success_probability": assessment["success_probability"],
                       "uniform_draw": None, "success": success,
                       "degree": "success" if all(successes) else "partial_success" if any(successes) else "failure",
                       "checks": results, "consequence_severity": max(result["consequence_severity"] for result in results),
                       "margin": None, "confidence": None}
        else:
            outcome = self._resolve_check(assessment)
        outcome["adjudication"] = assessment
        if adopting_economy:
            outcome["economy_initialization"] = deepcopy(self.memory["economy"]["initialization"])
        if economy_command is not None:
            outcome["economy_result"] = execute_command(self.mod, self.memory, economy_command, outcome)
        hazard_rate = float(self.memory.get("world_state", {}).get("ambient_hazard_rate", 0.0))
        hazard_p = hazard_probability(hazard_rate, 1.0)
        hazard_u = self.streams["world"].random()
        outcome["ambient_hazard_triggered"] = hazard_u < hazard_p
        outcome["ambient_hazard"] = {"rate_per_pulse": hazard_rate, "duration_pulses": 1.0,
                                     "probability": hazard_p, "uniform_draw": hazard_u}

        ws = self.memory.setdefault("world_state", {})
        ws["tension"] = max(
            0.0,
            min(
                10.0,
                float(ws.get("tension", 3.0))
                + (0.35 if not outcome["success"] else -0.15),
            ),
        )
        ws["momentum"] = max(
            -10.0,
            min(
                10.0,
                float(ws.get("momentum", 0.0))
                + (0.3 if outcome["success"] else -0.2),
            ),
        )

        story_update = advance_story(
            self.mod,
            self.memory,
            action,
            outcome,
            self.streams["story"],
        )
        story_update["economy_developments"] = economy_before + settle_economy(self.mod, self.memory)
        packet = build_scene_packet(
            self.mod,
            self.memory,
            action,
            outcome,
            frame,
            story_update=story_update,
        )
        event_payload = {
            "action": action,
            "resolution": outcome,
            "story_update": story_update,
            "scene_packet": packet,
            "adjudication_request": adjudication_request,
            "economy_command": economy_command,
        }
        if idempotency_key:
            event_payload["idempotency_key"] = idempotency_key
        append_event(self.memory, "player_action", event_payload)

        cadence = self.mod["simulation_profile"].get("image_cadence", "key_moments")
        if self.queue_path and should_generate(cadence, self.memory["turn"], significance):
            job = enqueue(self.queue_path, packet, significance)
            self.memory.setdefault("image_jobs", []).append(
                {"id": job["id"], "turn": job["turn"], "status": job["status"]}
            )

        self._persist_rng()
        previous_version = int(self.memory.get("state_version", self.memory["turn"] - 1))
        self.memory["state_version"] = previous_version + 1
        self.memory["last_scene_packet"] = packet
        return packet

    def _resolve_check(self, assessment):
        outcome = sample_skill_check(self.streams["actions"], assessment["skill"],
                                     assessment["difficulty"], assessment["context"], assessment["temperature"])
        outcome["consequence_severity"] = 0.0 if outcome["success"] else consequence_severity(
            self.streams["actions"], base=max(0.1, abs(outcome["margin"]) + 0.5))
        outcome["target_id"] = assessment.get("target_id")
        stakes = assessment.get("stakes", {})
        stake_key = "success" if outcome["success"] else "partial_success" if outcome["degree"] == "partial_success" else "failure"
        outcome["narrative_stakes"] = stakes.get(stake_key)
        return outcome
