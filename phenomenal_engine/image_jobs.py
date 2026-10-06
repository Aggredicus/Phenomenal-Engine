from __future__ import annotations
from dataclasses import dataclass, asdict
import json, uuid
from pathlib import Path

@dataclass
class ImageJob:
    id: str
    turn: int
    status: str
    prompt: str
    significance: float
    scene_packet: dict

def should_generate(cadence: str, turn: int, significance: float) -> bool:
    if cadence == "off":
        return False
    if cadence == "every_turn":
        return True
    if cadence == "key_moments":
        return significance >= 0.65
    if cadence.startswith("every_"):
        try:
            n = int(cadence.split("_", 1)[1])
            return n > 0 and turn % n == 0
        except ValueError:
            return False
    return False

def build_prompt(scene_packet: dict, style: dict | None = None) -> str:
    ph = scene_packet.get("phenomenology", {})
    style = style or scene_packet.get("image_prompt_directives", {})
    lines = [
        f"Illustrate turn {scene_packet.get('turn')} of an interactive narrative.",
        f"Player action: {scene_packet.get('action')}",
        f"Outcome: {json.dumps(scene_packet.get('simulation_outcome', {}), ensure_ascii=False)}",
        f"Perceptual conditions: {json.dumps(ph, ensure_ascii=False)}",
        "Show only information the viewpoint character could visually perceive.",
        "No text overlays unless the scene itself contains legible writing.",
    ]
    if style:
        lines.append(f"Art direction: {json.dumps(style, ensure_ascii=False)}")
    return "\n".join(lines)

def enqueue(queue_path: str | Path, scene_packet: dict, significance: float = 0.5) -> dict:
    job = ImageJob(
        id=str(uuid.uuid4()),
        turn=int(scene_packet.get("turn", 0)),
        status="queued",
        prompt=build_prompt(scene_packet),
        significance=float(significance),
        scene_packet=scene_packet,
    )
    p = Path(queue_path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with p.open("a", encoding="utf-8") as f:
        f.write(json.dumps(asdict(job), ensure_ascii=False) + "\n")
    return asdict(job)
