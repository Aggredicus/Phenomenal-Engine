from __future__ import annotations
from dataclasses import dataclass
import hashlib
import math
from typing import Iterable, Sequence, TypeVar

T = TypeVar("T")
MASK64 = (1 << 64) - 1
MASK32 = (1 << 32) - 1

@dataclass
class PCG32:
    """Small, stable, reproducible PCG-XSH-RR generator.

    Gameplay simulations should be replayable.  Python's stdlib random module is
    excellent for normal use, but this implementation makes the algorithm part
    of the engine's file format so a saved campaign can reproduce rolls across
    machines and future Python versions.
    """
    state: int = 0
    inc: int = 0xDA3E39CB94B95BDB

    def __init__(self, seed: int = 0, seq: int = 1):
        self.state = 0
        self.inc = ((seq << 1) | 1) & MASK64
        self._normal_cache = None
        self._next_uint32()
        self.state = (self.state + (seed & MASK64)) & MASK64
        self._next_uint32()

    def _next_uint32(self) -> int:
        old = self.state
        self.state = (old * 6364136223846793005 + self.inc) & MASK64
        xorshifted = (((old >> 18) ^ old) >> 27) & MASK32
        rot = (old >> 59) & 31
        return ((xorshifted >> rot) | (xorshifted << ((-rot) & 31))) & MASK32

    def random(self) -> float:
        return self._next_uint32() / 4294967296.0

    def randint(self, a: int, b: int) -> int:
        if b < a:
            raise ValueError("b must be >= a")
        span = b - a + 1
        threshold = ((1 << 32) - span) % span
        while True:
            r = self._next_uint32()
            if r >= threshold:
                return a + (r % span)

    def choice(self, seq: Sequence[T]) -> T:
        if not seq:
            raise ValueError("empty sequence")
        return seq[self.randint(0, len(seq) - 1)]

    def weighted_choice(self, items: Sequence[T], weights: Sequence[float]) -> T:
        if len(items) != len(weights) or not items:
            raise ValueError("items and weights must have equal nonzero length")
        total = sum(max(0.0, w) for w in weights)
        if total <= 0:
            raise ValueError("weights must contain a positive value")
        x = self.random() * total
        acc = 0.0
        for item, weight in zip(items, weights):
            acc += max(0.0, weight)
            if x < acc:
                return item
        return items[-1]

    def normal(self, mu: float = 0.0, sigma: float = 1.0) -> float:
        if sigma < 0:
            raise ValueError("sigma must be nonnegative")
        if self._normal_cache is not None:
            z = self._normal_cache
            self._normal_cache = None
            return mu + sigma * z
        u1 = max(self.random(), 1e-15)
        u2 = self.random()
        mag = math.sqrt(-2.0 * math.log(u1))
        z0 = mag * math.cos(2 * math.pi * u2)
        self._normal_cache = mag * math.sin(2 * math.pi * u2)
        return mu + sigma * z0

    def exponential(self, rate: float) -> float:
        if rate <= 0:
            raise ValueError("rate must be positive")
        return -math.log(max(1e-15, 1.0 - self.random())) / rate

    def gamma(self, shape: float, scale: float = 1.0) -> float:
        if shape <= 0 or scale <= 0:
            raise ValueError("shape and scale must be positive")
        if shape < 1:
            # Ahrens-Dieter transform
            return self.gamma(shape + 1, scale) * self.random() ** (1.0 / shape)
        d = shape - 1.0 / 3.0
        c = 1.0 / math.sqrt(9.0 * d)
        while True:
            x = self.normal()
            v = (1.0 + c * x) ** 3
            if v <= 0:
                continue
            u = self.random()
            if u < 1.0 - 0.0331 * (x ** 4):
                return scale * d * v
            if math.log(max(u, 1e-15)) < 0.5 * x * x + d * (1 - v + math.log(v)):
                return scale * d * v

    def beta(self, alpha: float, beta: float) -> float:
        x = self.gamma(alpha)
        y = self.gamma(beta)
        return x / (x + y)

    def poisson(self, lam: float) -> int:
        if lam < 0:
            raise ValueError("lam must be nonnegative")
        if lam == 0:
            return 0
        if lam < 30:
            limit = math.exp(-lam)
            k, p = 0, 1.0
            while p > limit:
                k += 1
                p *= self.random()
            return k - 1
        # Fast approximation appropriate for narrative event counts.
        return max(0, int(round(self.normal(lam, math.sqrt(lam)))))

    def binomial(self, n: int, p: float) -> int:
        if n < 0 or not 0 <= p <= 1:
            raise ValueError("invalid n or p")
        if n <= 128:
            return sum(self.random() < p for _ in range(n))
        mu = n * p
        var = n * p * (1 - p)
        return min(n, max(0, int(round(self.normal(mu, math.sqrt(var))))))

    def state_dict(self) -> dict:
        return {"algorithm": "pcg32-xsh-rr", "state": self.state, "inc": self.inc}

    @classmethod
    def from_state_dict(cls, data: dict) -> "PCG32":
        obj = cls(0, 1)
        obj.state = int(data["state"]) & MASK64
        obj.inc = int(data["inc"]) & MASK64
        obj._normal_cache = None
        return obj

def derive_stream(master_seed: int | str, label: str) -> PCG32:
    payload = f"{master_seed}|{label}".encode("utf-8")
    digest = hashlib.blake2b(payload, digest_size=16).digest()
    seed = int.from_bytes(digest[:8], "little")
    seq = int.from_bytes(digest[8:], "little")
    return PCG32(seed=seed, seq=seq)
