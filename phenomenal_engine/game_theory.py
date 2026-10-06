from __future__ import annotations
from dataclasses import dataclass, field
from typing import Protocol
from .rng import PCG32

C, D = "C", "D"

@dataclass(frozen=True)
class Payoffs:
    temptation: float = 5.0
    reward: float = 3.0
    punishment: float = 1.0
    sucker: float = 0.0

    def score(self, a: str, b: str) -> tuple[float, float]:
        if a == C and b == C: return self.reward, self.reward
        if a == C and b == D: return self.sucker, self.temptation
        if a == D and b == C: return self.temptation, self.sucker
        return self.punishment, self.punishment

class Strategy(Protocol):
    name: str
    def move(self, my: list[str], other: list[str], my_scores: list[float], rng: PCG32) -> str: ...

@dataclass
class AlwaysCooperate:
    name: str = "Always Cooperate"
    def move(self, my, other, my_scores, rng): return C

@dataclass
class AlwaysDefect:
    name: str = "Always Defect"
    def move(self, my, other, my_scores, rng): return D

@dataclass
class TitForTat:
    name: str = "Tit for Tat"
    def move(self, my, other, my_scores, rng): return C if not other else other[-1]

@dataclass
class GenerousTitForTat:
    forgiveness: float = 0.10
    name: str = "Generous Tit for Tat"
    def move(self, my, other, my_scores, rng):
        if not other or other[-1] == C: return C
        return C if rng.random() < self.forgiveness else D

@dataclass
class GrimTrigger:
    name: str = "Grim Trigger"
    def move(self, my, other, my_scores, rng): return D if D in other else C

@dataclass
class WinStayLoseShift:
    aspiration: float = 3.0
    name: str = "Win-Stay Lose-Shift"
    def move(self, my, other, my_scores, rng):
        if not my: return C
        if my_scores[-1] >= self.aspiration:
            return my[-1]
        return D if my[-1] == C else C

@dataclass
class RandomStrategy:
    cooperate_probability: float = 0.5
    name: str = "Random"
    def move(self, my, other, my_scores, rng):
        return C if rng.random() < self.cooperate_probability else D

@dataclass
class MemoryOne:
    """p = P(cooperate | previous outcome CC, CD, DC, DD) from player's view."""
    p_cc: float = 1.0
    p_cd: float = 0.0
    p_dc: float = 1.0
    p_dd: float = 0.0
    first: float = 1.0
    name: str = "Memory-One"

    def move(self, my, other, my_scores, rng):
        if not my:
            p = self.first
        else:
            key = my[-1] + other[-1]
            p = {"CC": self.p_cc, "CD": self.p_cd, "DC": self.p_dc, "DD": self.p_dd}[key]
        return C if rng.random() < p else D

    def genome(self):
        return [self.first, self.p_cc, self.p_cd, self.p_dc, self.p_dd]

    @classmethod
    def from_genome(cls, g, name="Evolved Memory-One"):
        vals = [max(0.0, min(1.0, float(x))) for x in g]
        return cls(vals[1], vals[2], vals[3], vals[4], vals[0], name)

def _maybe_error(action: str, error_rate: float, rng: PCG32) -> str:
    if rng.random() < error_rate:
        return D if action == C else C
    return action

def play_match(a: Strategy, b: Strategy, rounds: int, rng: PCG32, payoffs: Payoffs | None = None, error_rate: float = 0.0) -> dict:
    payoffs = payoffs or Payoffs()
    ah, bh, ascores, bscores = [], [], [], []
    for _ in range(rounds):
        am = _maybe_error(a.move(ah, bh, ascores, rng), error_rate, rng)
        bm = _maybe_error(b.move(bh, ah, bscores, rng), error_rate, rng)
        sa, sb = payoffs.score(am, bm)
        ah.append(am); bh.append(bm); ascores.append(sa); bscores.append(sb)
    return {
        "a": getattr(a, "name", type(a).__name__),
        "b": getattr(b, "name", type(b).__name__),
        "rounds": rounds,
        "a_score": sum(ascores),
        "b_score": sum(bscores),
        "a_cooperation": ah.count(C) / rounds,
        "b_cooperation": bh.count(C) / rounds,
        "history": ["".join(x) for x in zip(ah, bh)],
    }

def round_robin(strategies: list[Strategy], rounds: int, rng: PCG32, repetitions: int = 3, error_rate: float = 0.01) -> list[dict]:
    totals = {s.name: {"score": 0.0, "cooperation_sum": 0.0, "matches": 0} for s in strategies}
    for i, a in enumerate(strategies):
        for j, b in enumerate(strategies[i:], start=i):
            for rep in range(repetitions):
                result = play_match(a, b, rounds, rng, error_rate=error_rate)
                totals[a.name]["score"] += result["a_score"]
                totals[a.name]["cooperation_sum"] += result["a_cooperation"]
                totals[a.name]["matches"] += 1
                if i != j:
                    totals[b.name]["score"] += result["b_score"]
                    totals[b.name]["cooperation_sum"] += result["b_cooperation"]
                    totals[b.name]["matches"] += 1
    ranking = []
    for name, x in totals.items():
        ranking.append({
            "strategy": name,
            "total_score": x["score"],
            "mean_cooperation": x["cooperation_sum"] / max(1, x["matches"]),
            "matches": x["matches"],
        })
    return sorted(ranking, key=lambda x: x["total_score"], reverse=True)

def mutate_memory_one(parent: MemoryOne, rng: PCG32, sigma: float = 0.08) -> MemoryOne:
    g = [max(0.0, min(1.0, x + rng.normal(0, sigma))) for x in parent.genome()]
    return MemoryOne.from_genome(g)

def evolve_memory_one(rng: PCG32, generations: int = 30, population_size: int = 24, rounds: int = 40, error_rate: float = 0.02) -> list[dict]:
    """Small genetic algorithm for teaching—not a claim about biological inevitability."""
    population = [MemoryOne.from_genome([rng.random() for _ in range(5)], f"m{i}") for i in range(population_size)]
    history = []
    opponents = [AlwaysCooperate(), AlwaysDefect(), TitForTat(), GenerousTitForTat(), WinStayLoseShift()]
    for gen in range(generations):
        scored = []
        for s in population:
            score = 0.0
            coop = 0.0
            for o in opponents:
                r = play_match(s, o, rounds, rng, error_rate=error_rate)
                score += r["a_score"]
                coop += r["a_cooperation"]
            scored.append((score, coop / len(opponents), s))
        scored.sort(key=lambda x: x[0], reverse=True)
        best = scored[0]
        history.append({"generation": gen, "best_score": best[0], "cooperation": best[1], "genome": best[2].genome()})
        elites = [s for _, _, s in scored[: max(2, population_size // 4)]]
        new_pop = elites[:2]
        while len(new_pop) < population_size:
            parent = rng.choice(elites)
            new_pop.append(mutate_memory_one(parent, rng))
        population = new_pop
    return history

def axelrod_traits(strategy: Strategy, rng: PCG32 | None = None) -> dict:
    """Approximate behavioral descriptors inspired by Axelrod's four robust traits."""
    rng = rng or PCG32(12345, 7)
    first = strategy.move([], [], [], rng)
    retaliation_test = strategy.move([C], [D], [0.0], rng)
    forgiveness_test = strategy.move([D, D], [D, C], [1.0, 5.0], rng)
    return {
        "nice": first == C,
        "provocable": retaliation_test == D,
        "forgiving": forgiveness_test == C,
        "clear": type(strategy).__name__ in {"AlwaysCooperate", "AlwaysDefect", "TitForTat", "GrimTrigger", "WinStayLoseShift"},
    }
