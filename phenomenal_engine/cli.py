from __future__ import annotations
import argparse, json
from pathlib import Path
from .mod_loader import load_mod, validate_mod
from .memory import new_memory, save_memory
from .engine import Engine
from .rng import PCG32
from .game_theory import (
    AlwaysCooperate, AlwaysDefect, TitForTat, GenerousTitForTat,
    WinStayLoseShift, GrimTrigger, RandomStrategy, round_robin, evolve_memory_one
)
from .physics import planck_budget

def cmd_validate(args):
    paths = []
    p = Path(args.path)
    if p.is_dir():
        paths = list(p.glob("*.json"))
    else:
        paths = [p]
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
    memory = new_memory(mod, args.seed)
    save_memory(args.output, memory)
    print(args.output)

def cmd_step(args):
    mod = load_mod(args.mod)
    memory = new_memory(mod, args.seed)
    engine = Engine(mod, memory, args.queue)
    packet = engine.step(args.action, args.skill, args.difficulty, args.context, significance=args.significance)
    if args.save:
        save_memory(args.save, memory)
    print(json.dumps(packet, indent=2, ensure_ascii=False))

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

    p = sub.add_parser("new-save")
    p.add_argument("mod")
    p.add_argument("output")
    p.add_argument("--seed", default="story-seed")
    p.set_defaults(func=cmd_new_save)

    p = sub.add_parser("step")
    p.add_argument("mod")
    p.add_argument("action")
    p.add_argument("--seed", default="story-seed")
    p.add_argument("--skill", type=float, default=0.0)
    p.add_argument("--difficulty", type=float, default=0.0)
    p.add_argument("--context", type=float, default=0.0)
    p.add_argument("--significance", type=float, default=0.5)
    p.add_argument("--queue", default=None)
    p.add_argument("--save", default=None)
    p.set_defaults(func=cmd_step)

    args = ap.parse_args(argv)
    args.func(args)

if __name__ == "__main__":
    main()
