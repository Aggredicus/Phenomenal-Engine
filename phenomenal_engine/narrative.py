from __future__ import annotations
from dataclasses import dataclass, asdict
from .physics import sound_level_at_distance, sabine_rt60

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

def build_scene_packet(mod: dict, memory: dict, action: str, outcome: dict, frame: PhenomenologyFrame | None = None) -> dict:
    frame = frame or PhenomenologyFrame()
    return {
        "schema_version": "1.0.0",
        "mod_id": mod["id"],
        "turn": memory["turn"],
        "action": action,
        "simulation_outcome": outcome,
        "phenomenology": frame.perceptual_summary(),
        "known_world_state": memory.get("world_state", {}),
        "open_threads": memory.get("open_threads", []),
        "narrative_directives": [
            "Describe only what the viewpoint character could perceive or infer.",
            "Let physical causes precede their visible/audible consequences.",
            "Use at least two sensory channels when they materially differ.",
            "Do not convert hidden engine state into character knowledge.",
            "Preserve established facts and delayed consequences.",
            "End with a concrete affordance, dilemma, discovery, or question for the player.",
        ],
        "image_prompt_directives": mod.get("image_direction", {}),
    }
