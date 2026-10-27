"""Bounded, deterministic, no-network RNG property sweep (not gameplay)."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phenomenal_engine.rng import PCG32, derive_stream
from phenomenal_engine.probability import logistic_success_probability

def run(seeds: int, draws: int) -> dict:
    if not (1 <= seeds <= 50000 and 1 <= draws <= 1000):
        raise ValueError("out-of-budget stress parameters")
    start = time.monotonic()
    for seed in range(seeds):
        lo, hi = -(1 << (33 + seed % 48)), (1 << (33 + seed % 48)) + 7
        left, right = PCG32(seed, 3 + seed % 41), PCG32(seed, 3 + seed % 41)
        for _ in range(draws):
            a, b = left.randint(lo, hi), right.randint(lo, hi)
            assert lo <= a <= hi, (seed, "out of range")
            assert a == b, (seed, "replay mismatch")
        left.normal()
        resumed = PCG32.from_state_dict(left.state_dict())
        assert [left.normal() for _ in range(7)] == [resumed.normal() for _ in range(7)]
        assert derive_stream(seed, "navigation").state_dict() != derive_stream(seed, "encounters").state_dict()
        assert 0 < logistic_success_probability(7, 12) < logistic_success_probability(7, 2) < 1
    return {"status": "pass", "seeds": seeds, "wide_draws": seeds * draws,
            "restoration_checks": seeds, "seconds": round(time.monotonic() - start, 3),
            "network_operations": 0}

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--seeds", type=int, default=500)
    parser.add_argument("--draws", type=int, default=100)
    args = parser.parse_args()
    print(json.dumps(run(args.seeds, args.draws), sort_keys=True))
