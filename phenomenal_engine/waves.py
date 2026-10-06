from __future__ import annotations
from dataclasses import dataclass
import math

@dataclass
class Wave1D:
    """Finite-difference wave equation demo.

    This is deliberately local and small. Large-scale scenes should use rays or
    reduced-order acoustics/optics and refine to a field solver only where wave
    effects matter.
    """
    n: int
    dx: float
    dt: float
    speed: float

    def __post_init__(self):
        if self.n < 3 or self.dx <= 0 or self.dt <= 0 or self.speed <= 0:
            raise ValueError("invalid wave grid")
        self.courant = self.speed * self.dt / self.dx
        if self.courant > 1:
            raise ValueError("unstable grid: Courant number must be <= 1")
        self.prev = [0.0] * self.n
        self.curr = [0.0] * self.n

    def impulse(self, index: int, amplitude: float = 1.0):
        self.curr[index] += amplitude

    def step(self, damping: float = 0.0):
        r2 = self.courant * self.courant
        nxt = [0.0] * self.n
        for i in range(1, self.n - 1):
            nxt[i] = (
                2 * self.curr[i] - self.prev[i]
                + r2 * (self.curr[i + 1] - 2 * self.curr[i] + self.curr[i - 1])
            ) * (1.0 - damping)
        # simple fixed boundaries
        self.prev, self.curr = self.curr, nxt
        return self.curr

def superpose_sines(t: float, components: list[tuple[float, float, float]]) -> float:
    """components = (amplitude, frequency_hz, phase_rad)."""
    return sum(a * math.sin(2 * math.pi * f * t + phase) for a, f, phase in components)

def spectral_centroid(components: list[tuple[float, float, float]]) -> float:
    weights = [abs(a) for a, _, _ in components]
    total = sum(weights)
    if total == 0:
        return 0.0
    return sum(w * f for w, (_, f, _) in zip(weights, components)) / total
