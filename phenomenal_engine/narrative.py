from __future__ import annotations
from dataclasses import dataclass
from .story import experience_directives, visible_story_state
from .travel import visible_map

def _light_word(lux: float) -> str:
    if lux < 0.01: return "near-total darkness"
    if lux < 1: return "very dim light"
    if lux < 50: return "dim interior light"
    if lux < 500: return "comfortable working light"
    if lux < 10_000: return "bright light"
    return "intense daylight"

def _sound_word(db: float) -> str:
    if db < 20: return "almost silent"
    if db < 40: return "quiet"
    if db < 60: return "conversational"
    if db < 80: return "loud"
    return "overwhelmingly loud"

@dataclass
class PhenomenologyFrame:
    visible_lux: float = 100.0
    dominant_wavelength_nm: float | None = None
    sound_db: float = 30.0
    sound_centroid_hz: float | None = None
    reverb_rt60_s: float = 0.5
    air_temp_c: float = 20.0
    wind_mps: float = 0.0
    vibration_hz: float | None = None
    uncertainty: float = 0.1

    def perceptual_summary(self) -> dict:
        return {
            "visual": _light_word(self.visible_lux),
            "auditory": _sound_word(self.sound_db),
            "reverberation": (
                "dry and close" if self.reverb_rt60_s < 0.4
                else "gently reverberant" if self.reverb_rt60_s < 1.5
                else "long, architectural reverberation"
            ),
            "temperature_c": self.air_temp_c,
            "wind_mps": self.wind_mps,
            "spectral_color_nm": self.dominant_wavelength_nm,
            "sound_centroid_hz": self.sound_centroid_hz,
            "vibration_hz": self.vibration_hz,
            "perceptual_uncertainty": self.uncertainty,
        }

def build_scene_packet(
    mod: dict,
    memory: dict,
    action: str,
    outcome: dict,
    frame: PhenomenologyFrame | None = None,
    story_update: dict | None = None,
) -> dict:
    frame = frame or PhenomenologyFrame()
    story_update = story_update or {}
    story_design = mod.get("story_design", {})
    return {
        "schema_version": "1.0.0",
        "mod_id": mod["id"],
        "turn": memory["turn"],
        "action": action,
        "simulation_outcome": outcome,
        "phenomenology": frame.perceptual_summary(),
        "known_world_state": memory.get("world_state", {}),
        "open_threads": memory.get("open_threads", []),
        "story_state": visible_story_state(memory),
        "world_map": visible_map(mod, memory),
        "story_update": story_update,
        "presentation": {
            "mechanics_visibility": story_design.get("mechanics_visibility", "submerged"),
            "default_scene_style": story_design.get("default_scene_style", "immersive"),
            "quest_marker_policy": story_design.get("quest_marker_policy", "diegetic"),
        },
        "narrative_directives": [
            "Describe only what the viewpoint character could perceive or reasonably infer.",
            "Let physical causes precede their visible or audible consequences.",
            "Use concrete sensory detail selectively; favor memorable specificity over adjective density.",
            "Do not convert hidden engine state into character knowledge.",
            "Preserve established facts, injuries, promises, relationships, and delayed consequences.",
            "Treat the game-theory and probability machinery as submerged causality. Do not lecture about models, payoff matrices, or raw rolls unless the player deliberately asks to inspect them.",
            "Begin from people, place, desire, danger, mystery, humor, beauty, or practical stakes rather than from abstract systems.",
            "Keep the world larger than the active objective. Let NPCs have schedules, loyalties, private goals, friendships, grudges, work, and off-screen consequences.",
            "Plant optional details that can remain mere atmosphere. Promote them into story threads only when the player shows interest.",
            "Support simultaneous main, faction, side, local, and emergent threads. Never imply the player is playing incorrectly for ignoring the main story.",
            "Do not announce every breadcrumb as a quest. Use diegetic clues, overheard conversation, objects, changes in place, and character behavior.",
            "Honor the persistent travel graph. Distances, route order, travel modes, closures, shortcuts, and the player current location must remain consistent with world_map and story_update.travel.",
            "Conflict should have positioning, environment, morale, alternatives, and persistent consequences; opponents should have motives rather than existing only as targets.",
            "Failure should transform the situation, reveal cost or information, or open a different route more often than it simply blocks progress.",
            "End with a concrete affordance, dilemma, discovery, interruption, or natural opening for free-form action.",
            *mod.get("llm_directives", []),
            *story_update.get("experience_directives", experience_directives(memory)),
        ],
        "image_prompt_directives": mod.get("image_direction", {}),
    }
