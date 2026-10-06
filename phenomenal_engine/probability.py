from __future__ import annotations
from dataclasses import dataclass
import math
from .rng import PCG32

def clamp(x: float, lo: float, hi: float) -> float:
    return max(lo, min(hi, x))

def sigmoid(x: float) -> float:
    if x >= 0:
        z = math.exp(-x)
        return 1 / (1 + z)
    z = math.exp(x)
    return z / (1 + z)

def logistic_success_probability(
    skill: float,
    difficulty: float,
    context: float = 0.0,
    temperature: float = 1.0,
    floor: float = 0.01,
    ceiling: float = 0.99,
) -> float:
    """Smooth success odds instead of arbitrary target numbers."""
    if temperature <= 0:
        raise ValueError("temperature must be positive")
    p = sigmoid((skill + context - difficulty) / temperature)
    return clamp(p, floor, ceiling)

def hazard_probability(rate_per_unit: float, duration: float) -> float:
    """Poisson-process probability of >=1 event during duration."""
    if rate_per_unit < 0 or duration < 0:
        raise ValueError("rate and duration must be nonnegative")
    return 1.0 - math.exp(-rate_per_unit * duration)

@dataclass
class BetaBelief:
    """Conjugate Bayesian belief for an unknown Bernoulli probability."""
    alpha: float = 1.0
    beta: float = 1.0

    @property
    def mean(self) -> float:
        return self.alpha / (self.alpha + self.beta)

    @property
    def effective_samples(self) -> float:
        return self.alpha + self.beta

    def update(self, success: bool, weight: float = 1.0) -> None:
        if weight < 0:
            raise ValueError("weight must be nonnegative")
        if success:
            self.alpha += weight
        else:
            self.beta += weight

    def sample(self, rng: PCG32) -> float:
        return rng.beta(self.alpha, self.beta)

def sample_skill_check(
    rng: PCG32,
    skill: float,
    difficulty: float,
    context: float = 0.0,
    temperature: float = 1.0,
) -> dict:
    p = logistic_success_probability(skill, difficulty, context, temperature)
    u = rng.random()
    margin = (skill + context - difficulty) + rng.normal(0, 0.20 * temperature)
    return {
        "success_probability": p,
        "uniform_draw": u,
        "success": u < p,
        "margin": margin,
        "confidence": abs(p - 0.5) * 2,
    }

def cholesky(matrix: list[list[float]]) -> list[list[float]]:
    """Tiny pure-Python Cholesky for correlated narrative factors."""
    n = len(matrix)
    L = [[0.0] * n for _ in range(n)]
    for i in range(n):
        for j in range(i + 1):
            s = sum(L[i][k] * L[j][k] for k in range(j))
            if i == j:
                v = matrix[i][i] - s
                if v <= 0:
                    raise ValueError("matrix must be positive definite")
                L[i][j] = math.sqrt(v)
            else:
                L[i][j] = (matrix[i][j] - s) / L[j][j]
    return L

def correlated_normals(
    rng: PCG32,
    means: list[float],
    covariance: list[list[float]],
) -> list[float]:
    if len(means) != len(covariance):
        raise ValueError("dimension mismatch")
    L = cholesky(covariance)
    z = [rng.normal() for _ in means]
    out = []
    for i, mean in enumerate(means):
        out.append(mean + sum(L[i][j] * z[j] for j in range(i + 1)))
    return out

def consequence_severity(rng: PCG32, base: float, uncertainty: float = 0.35) -> float:
    """Positive heavy-tailed magnitude for costs/injuries/damage without a flat die."""
    if base < 0:
        raise ValueError("base must be nonnegative")
    if base == 0:
        return 0.0
    sigma = max(1e-9, uncertainty)
    mu = math.log(base) - 0.5 * sigma * sigma
    return math.exp(rng.normal(mu, sigma))
