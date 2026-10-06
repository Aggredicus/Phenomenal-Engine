from pathlib import Path
from phenomenal_engine.mod_loader import load_mod
from phenomenal_engine.memory import new_memory
from phenomenal_engine.engine import Engine
from phenomenal_engine.narrative import PhenomenologyFrame

base = Path(__file__).resolve().parents[1]
mod = load_mod(base / "mods" / "great_labyrinth_of_egypt.json")
memory = new_memory(mod, "demo-seed")
engine = Engine(mod, memory, base / "runtime" / "image_queue.jsonl")

packet = engine.step(
    "I put my ear near the sealed stone and listen for a repeating echo.",
    skill=1.3,
    difficulty=0.9,
    context=0.2,
    frame=PhenomenologyFrame(
        visible_lux=0.4,
        sound_db=28,
        sound_centroid_hz=180,
        reverb_rt60_s=2.7,
        air_temp_c=18,
        wind_mps=0.05,
        uncertainty=0.18,
    ),
    significance=0.72,
)
print(packet)
