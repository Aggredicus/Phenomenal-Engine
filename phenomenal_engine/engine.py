from __future__ import annotations
from .rng import derive_stream, PCG32
from .probability import sample_skill_check, consequence_severity, hazard_probability
from .memory import append_event
from .narrative import build_scene_packet, PhenomenologyFrame
from .image_jobs import should_generate, enqueue
from .story import advance_story, matching_action_rule

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

    def step(
        self,
        action: str,
        skill: float = 0.0,
        difficulty: float = 0.0,
        context: float = 0.0,
        frame: PhenomenologyFrame | None = None,
        significance: float = 0.5,
        idempotency_key: str | None = None,
    ) -> dict:
        self.memory["turn"] += 1
        action_rng = self.streams["actions"]
        action_rule = matching_action_rule(self.mod, self.memory, action)
        if action_rule is not None and action_rule.get("deterministic", False):
            outcome = {
                "success_probability": 1.0,
                "uniform_draw": None,
                "success": True,
                "margin": 1.0,
                "confidence": 1.0,
                "deterministic": True,
                "rule_id": action_rule["id"],
            }
            outcome["consequence_severity"] = 0.0
        else:
            outcome = sample_skill_check(
                action_rng,
                skill,
                difficulty,
                context,
                self.mod["simulation_profile"].get("skill_temperature", 1.0),
            )
            outcome["consequence_severity"] = consequence_severity(
                action_rng,
                base=max(0.1, abs(outcome["margin"]) + 0.5),
            )
        hazard_rate = float(self.memory.get("world_state", {}).get("ambient_hazard_rate", 0.0))
        outcome["ambient_hazard_triggered"] = (
            action_rng.random() < hazard_probability(hazard_rate, 1.0)
        )

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
