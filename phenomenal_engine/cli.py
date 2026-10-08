from __future__ import annotations
import argparse, json
from pathlib import Path
from .mod_loader import load_mod
from .memory import (
    find_event_by_idempotency_key,
    load_memory,
    new_memory,
    save_memory,
    validate_memory_for_mod,
)
from .engine import Engine
from .rng import PCG32
from .game_theory import (
    AlwaysCooperate, AlwaysDefect, TitForTat, GenerousTitForTat,
    WinStayLoseShift, GrimTrigger, RandomStrategy, round_robin, evolve_memory_one
)
from .physics import planck_budget
from .travel import plan_route, visible_map
from .map_ui import serve_map_ui
from .director import build_director_state, load_director_command, validate_director_command

def cmd_validate(args):
    p = Path(args.path)
    paths = list(p.glob("*.json")) if p.is_dir() else [p]
    failed = 0
    for path in paths:
        try:
            mod = load_mod(path)
            print(f"OK  {path.name}  {mod['title']} v{mod['version']}")
        except Exception as e:
            failed += 1
            print(f"ERR {path}: {e}")
    raise SystemExit(1 if failed else 0)

def cmd_tournament(args):
    rng = PCG32(args.seed, 99)
    strategies = [
        AlwaysCooperate(), AlwaysDefect(), TitForTat(),
        GenerousTitForTat(args.forgiveness), WinStayLoseShift(),
        GrimTrigger(), RandomStrategy(),
    ]
    print(json.dumps(round_robin(strategies, args.rounds, rng, args.repetitions, args.error_rate), indent=2))

def cmd_evolve(args):
    rng = PCG32(args.seed, 101)
    history = evolve_memory_one(rng, args.generations, args.population, args.rounds, args.error_rate)
    print(json.dumps(history[-min(10, len(history)):], indent=2))

def cmd_planck(args):
    print(json.dumps(planck_budget(), indent=2))

def cmd_new_save(args):
    mod = load_mod(args.mod)
    output = Path(args.output)
    if output.exists() and not args.force:
        raise FileExistsError(f"save already exists: {output}; pass --force to replace it")
    memory = new_memory(mod, args.seed)
    save_memory(output, memory)
    print(json.dumps({
        "status": "ok",
        "created": True,
        "campaign_id": memory["session_id"],
        "state_version": memory["state_version"],
        "turn": memory["turn"],
        "persisted": True,
        "save_path": str(output),
        "mod": memory["mod"],
    }, indent=2, ensure_ascii=False))

def cmd_step(args):
    """Stateless one-turn diagnostic command. Use play for persistent campaigns."""
    mod = load_mod(args.mod)
    memory = new_memory(mod, args.seed)
    engine = Engine(mod, memory, args.queue)
    packet = engine.step(
        args.action,
        args.skill,
        args.difficulty,
        args.context,
        significance=args.significance,
    )
    if args.save:
        save_memory(args.save, memory)
    print(json.dumps(packet, indent=2, ensure_ascii=False))

def cmd_play(args):
    mod = load_mod(args.mod)
    save_path = Path(args.save)
    created = not save_path.exists()

    if created:
        memory = new_memory(mod, args.seed)
    else:
        memory = load_memory(save_path)
        validate_memory_for_mod(
            memory,
            mod,
            allow_version_mismatch=args.allow_mod_version_mismatch,
        )

    duplicate = find_event_by_idempotency_key(memory, args.idempotency_key)
    if duplicate is not None:
        print(json.dumps({
            "status": "duplicate",
            "campaign_id": memory["session_id"],
            "created": False,
            "state_version": memory.get("state_version", memory.get("turn", 0)),
            "turn": memory.get("turn", 0),
            "persisted": True,
            "save_path": str(save_path),
            "idempotency_key": args.idempotency_key,
            "scene_packet": duplicate.get("payload", {}).get("scene_packet"),
        }, indent=2, ensure_ascii=False))
        return

    engine = Engine(mod, memory, args.queue)
    packet = engine.step(
        args.action,
        args.skill,
        args.difficulty,
        args.context,
        significance=args.significance,
        idempotency_key=args.idempotency_key,
    )
    save_memory(save_path, memory)
    print(json.dumps({
        "status": "ok",
        "campaign_id": memory["session_id"],
        "created": created,
        "state_version": memory["state_version"],
        "turn": memory["turn"],
        "persisted": True,
        "save_path": str(save_path),
        "mod": memory["mod"],
        "scene_packet": packet,
    }, indent=2, ensure_ascii=False))

def cmd_status(args):
    memory = load_memory(args.save)
    print(json.dumps({
        "status": "ok",
        "campaign_id": memory["session_id"],
        "state_version": memory.get("state_version", memory.get("turn", 0)),
        "turn": memory.get("turn", 0),
        "mod": memory.get("mod", {}),
        "created_utc": memory.get("created_utc"),
        "updated_utc": memory.get("updated_utc"),
        "ledger_events": len(memory.get("event_ledger", [])),
        "last_scene_packet": memory.get("last_scene_packet"),
    }, indent=2, ensure_ascii=False))

def cmd_start(args):
    """Offer safe first-run choices without creating billable infrastructure."""
    mods_dir = Path(args.mods)
    available_mods = []
    if mods_dir.is_dir():
        for path in sorted(mods_dir.glob("*.json")):
            mod = load_mod(path)
            available_mods.append({
                "id": mod["id"],
                "title": mod["title"],
                "version": mod["version"],
                "path": str(path),
            })
    choice = "off" if args.no_codespaces else "requested" if args.codespaces else "offer"
    codespaces = {
        "optional": True,
        "default_enabled": False,
        "choice": choice,
        "requested": choice == "requested",
        "created": False,
        "may_incur_charges": True,
        "prompt": (
            "Optional: Would you like to use GitHub Codespaces as a separate "
            "development or advanced-simulation workspace? GitHub's included "
            "usage is limited, and charges may apply. It is not needed if an "
            "existing trusted Python runtime is available."
        ) if choice == "offer" else None,
        "setup_steps": [
            "Review current Codespaces pricing and remaining free allowance on GitHub.",
            "Open your fork on GitHub, then Code > Codespaces > Create codespace.",
            "Keep ports private; do not paste tokens into game chat.",
        ] if choice == "requested" else [],
        "pricing_reference": "https://github.com/pricing",
    }
    print(json.dumps({
        "status": "setup_choices",
        "runtime_policy": "prefer_existing_trusted_runtime",
        "codespaces": codespaces,
        "mods": available_mods,
        "next_step": (
            "Choose an adventure. Use an already available trusted runtime; "
            "only enter Codespaces setup after explicit player opt-in."
        ),
        "note": "This command never creates a Codespace or runs a game turn.",
    }, indent=2, ensure_ascii=False))



def _load_map_memory(mod: dict, save: str | None, seed: str):
    if save:
        memory = load_memory(save)
        validate_memory_for_mod(memory, mod)
        return memory
    return new_memory(mod, seed)

def cmd_map(args):
    mod = load_mod(args.mod)
    memory = _load_map_memory(mod, args.save, args.seed)
    print(json.dumps(visible_map(mod, memory), indent=2, ensure_ascii=False))

def cmd_route(args):
    mod = load_mod(args.mod)
    memory = _load_map_memory(mod, args.save, args.seed)
    result = plan_route(
        mod,
        memory,
        args.destination,
        origin=args.origin,
        preference=args.preference,
    )
    print(json.dumps(result, indent=2, ensure_ascii=False))

def cmd_map_ui(args):
    serve_map_ui(
        args.mod,
        args.save,
        port=args.port,
        seed=args.seed,
    )


def cmd_director_state(args):
    mod = load_mod(args.mod)
    memory = load_memory(args.save)
    validate_memory_for_mod(memory, mod)
    print(json.dumps(build_director_state(mod, memory), indent=2, ensure_ascii=False))

def cmd_director_validate_command(args):
    mod = load_mod(args.mod)
    memory = load_memory(args.save)
    validate_memory_for_mod(memory, mod)
    command = load_director_command(args.command)
    result = validate_director_command(command, mod, memory)
    print(json.dumps(result, indent=2, ensure_ascii=False))
    if result["status"] != "allowed":
        raise SystemExit(2)

def add_resolution_args(p):
    p.add_argument("--skill", type=float, default=0.0)
    p.add_argument("--difficulty", type=float, default=0.0)
    p.add_argument("--context", type=float, default=0.0)
    p.add_argument("--significance", type=float, default=0.5)
    p.add_argument("--queue", default=None)

def main(argv=None):
    ap = argparse.ArgumentParser(prog="phenomenal-engine")
    sub = ap.add_subparsers(dest="cmd", required=True)

    p = sub.add_parser("validate", help="validate one mod or a directory of mods")
    p.add_argument("path")
    p.set_defaults(func=cmd_validate)

    p = sub.add_parser("tournament", help="run an iterated Prisoner's Dilemma tournament")
    p.add_argument("--rounds", type=int, default=100)
    p.add_argument("--repetitions", type=int, default=5)
    p.add_argument("--error-rate", type=float, default=0.02)
    p.add_argument("--forgiveness", type=float, default=0.10)
    p.add_argument("--seed", type=int, default=42)
    p.set_defaults(func=cmd_tournament)

    p = sub.add_parser("evolve", help="evolve memory-one cooperation strategies")
    p.add_argument("--generations", type=int, default=30)
    p.add_argument("--population", type=int, default=24)
    p.add_argument("--rounds", type=int, default=40)
    p.add_argument("--error-rate", type=float, default=0.02)
    p.add_argument("--seed", type=int, default=43)
    p.set_defaults(func=cmd_evolve)

    p = sub.add_parser("planck-budget", help="show why literal Planck-grid universe simulation is intractable")
    p.set_defaults(func=cmd_planck)

    p = sub.add_parser("new-save", help="create a new campaign save without running a turn")
    p.add_argument("mod")
    p.add_argument("output")
    p.add_argument("--seed", default="story-seed")
    p.add_argument("--force", action="store_true")
    p.set_defaults(func=cmd_new_save)

    p = sub.add_parser("step", help="run a stateless one-turn diagnostic simulation")
    p.add_argument("mod")
    p.add_argument("action")
    p.add_argument("--seed", default="story-seed")
    add_resolution_args(p)
    p.add_argument("--save", default=None)
    p.set_defaults(func=cmd_step)

    p = sub.add_parser(
        "play",
        aliases=["continue"],
        help="create/load a campaign, run one authoritative turn, and atomically save it",
    )
    p.add_argument("mod")
    p.add_argument("save")
    p.add_argument("action")
    p.add_argument("--seed", default="story-seed", help="used only when the save does not exist")
    add_resolution_args(p)
    p.add_argument("--idempotency-key", default=None)
    p.add_argument("--allow-mod-version-mismatch", action="store_true")
    p.set_defaults(func=cmd_play)

    p = sub.add_parser("start", help="offer adventures and optional Codespaces setup without provisioning compute")
    p.add_argument("--mods", default="mods", help="directory containing adventure mods")
    codespace_choice = p.add_mutually_exclusive_group()
    codespace_choice.add_argument(
        "--codespaces", action="store_true",
        help="request manual Codespaces setup instructions; does not create a Codespace",
    )
    codespace_choice.add_argument(
        "--no-codespaces", action="store_true",
        help="skip the Codespaces offer for this startup",
    )
    p.set_defaults(func=cmd_start)

    p = sub.add_parser("map", help="show the persistent known-location node map")
    p.add_argument("mod")
    p.add_argument("--save", default=None, help="optional campaign save; otherwise uses fresh map state")
    p.add_argument("--seed", default="map-preview")
    p.set_defaults(func=cmd_map)

    p = sub.add_parser("route", help="plan a consistent graph route between known locations")
    p.add_argument("mod")
    p.add_argument("destination")
    p.add_argument("--save", default=None, help="optional campaign save providing current location and discoveries")
    p.add_argument("--from", dest="origin", default=None, help="override origin location id")
    p.add_argument("--preference", choices=["fastest", "safest", "scenic"], default="fastest")
    p.add_argument("--seed", default="map-preview")
    p.set_defaults(func=cmd_route)

    p = sub.add_parser("map-ui", help="serve the interactive node map on loopback")
    p.add_argument("mod")
    p.add_argument("save")
    p.add_argument("--port", type=int, default=8765)
    p.add_argument("--seed", default="map-ui", help="used only when the save does not exist")
    p.set_defaults(func=cmd_map_ui)


    p = sub.add_parser("director-state", help="export a stable JSON director projection from an authoritative save")
    p.add_argument("mod")
    p.add_argument("save")
    p.set_defaults(func=cmd_director_state)

    p = sub.add_parser("director-validate-command", help="validate a director command without executing it")
    p.add_argument("mod")
    p.add_argument("save")
    p.add_argument("command", help="path to a director-command JSON file or inline JSON object")
    p.set_defaults(func=cmd_director_validate_command)

    p = sub.add_parser("status", help="verify and inspect a persistent campaign save")
    p.add_argument("save")
    p.set_defaults(func=cmd_status)

    args = ap.parse_args(argv)
    args.func(args)

if __name__ == "__main__":
    main()
