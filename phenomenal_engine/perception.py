from __future__ import annotations
import math


def wavelength_to_visible_band(nm: float | None) -> str | None:
    """Coarse human-visible spectral label; not a color-management system."""
    if nm is None:
        return None
    if nm < 380 or nm > 750:
        return "outside ordinary human visible range"
    if nm < 450: return "violet"
    if nm < 495: return "blue"
    if nm < 570: return "green"
    if nm < 590: return "yellow"
    if nm < 620: return "orange"
    return "red"


def pitch_band(hz: float | None) -> str | None:
    if hz is None:
        return None
    if hz < 20: return "infrasonic"
    if hz < 80: return "deep bass"
    if hz < 250: return "low"
    if hz < 2000: return "midrange"
    if hz < 8000: return "high"
    if hz <= 20_000: return "very high"
    return "ultrasonic"


def weber_fraction_detectable(base: float, change: float, fraction: float) -> bool:
    """Toy Weber-law threshold: |delta I| / I >= k."""
    if base <= 0 or fraction < 0:
        raise ValueError("base must be positive and fraction nonnegative")
    return abs(change) / base >= fraction


def apparent_loudness_ratio(delta_db: float) -> float:
    """Approximate physical intensity ratio corresponding to a dB difference."""
    return 10 ** (delta_db / 10.0)


def temporal_resolution_merge(interval_s: float, threshold_s: float = 0.05) -> bool:
    """Whether two short events are close enough to plausibly fuse perceptually in a toy observer."""
    return interval_s >= 0 and interval_s < threshold_s
