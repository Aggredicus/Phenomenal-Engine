from __future__ import annotations
from dataclasses import dataclass
import math

C = 299_792_458.0
G = 6.67430e-11
H = 6.62607015e-34
HBAR = H / (2 * math.pi)
KB = 1.380649e-23
PLANCK_LENGTH = 1.616255e-35
PLANCK_TIME = 5.391247e-44
PLANCK_MASS = 2.176434e-8

@dataclass(frozen=True)
class Vec3:
    x: float
    y: float
    z: float

    def __add__(self, other): return Vec3(self.x + other.x, self.y + other.y, self.z + other.z)
    def __sub__(self, other): return Vec3(self.x - other.x, self.y - other.y, self.z - other.z)
    def __mul__(self, scalar: float): return Vec3(self.x * scalar, self.y * scalar, self.z * scalar)
    def dot(self, other) -> float: return self.x * other.x + self.y * other.y + self.z * other.z
    def norm(self) -> float: return math.sqrt(self.dot(self))
    def unit(self):
        n = self.norm()
        if n == 0: return Vec3(0.0, 0.0, 0.0)
        return self * (1.0 / n)

def gravity_acceleration(point: Vec3, masses: list[tuple[float, Vec3]], softening: float = 0.0) -> Vec3:
    ax = ay = az = 0.0
    eps2 = softening * softening
    for mass, pos in masses:
        r = pos - point
        r2 = r.dot(r) + eps2
        if r2 <= 0:
            continue
        scale = G * mass / (r2 * math.sqrt(r2))
        ax += r.x * scale
        ay += r.y * scale
        az += r.z * scale
    return Vec3(ax, ay, az)

def leapfrog_step(position: Vec3, velocity: Vec3, dt: float, acceleration_fn):
    """Symplectic kick-drift-kick integration for long-lived orbital behavior."""
    a0 = acceleration_fn(position)
    vhalf = velocity + a0 * (0.5 * dt)
    p1 = position + vhalf * dt
    a1 = acceleration_fn(p1)
    v1 = vhalf + a1 * (0.5 * dt)
    return p1, v1

def sound_speed_air(temp_c: float = 20.0) -> float:
    return 331.3 * math.sqrt((temp_c + 273.15) / 273.15)

def sound_level_at_distance(
    source_db_at_ref: float,
    distance_m: float,
    ref_distance_m: float = 1.0,
    absorption_db_per_m: float = 0.0,
) -> float:
    d = max(distance_m, ref_distance_m)
    spreading = 20.0 * math.log10(d / ref_distance_m)
    absorption = max(0.0, d - ref_distance_m) * absorption_db_per_m
    return source_db_at_ref - spreading - absorption

def doppler_sound(emitted_hz: float, source_radial_mps: float, observer_radial_mps: float = 0.0, temp_c: float = 20.0) -> float:
    """Positive source_radial_mps means source moving toward observer."""
    c = sound_speed_air(temp_c)
    denominator = c - source_radial_mps
    if denominator <= 0:
        raise ValueError("simple Doppler formula invalid at/supersonic approach")
    return emitted_hz * (c + observer_radial_mps) / denominator

def light_wavelength(frequency_hz: float) -> float:
    return C / frequency_hz

def photon_energy(frequency_hz: float) -> float:
    return H * frequency_hz

def relativistic_doppler_light(emitted_hz: float, beta_receding: float) -> float:
    """Longitudinal special-relativistic Doppler; beta>0 means receding."""
    if not -1 < beta_receding < 1:
        raise ValueError("|beta| must be < 1")
    return emitted_hz * math.sqrt((1 - beta_receding) / (1 + beta_receding))

def inverse_square_flux(power_w: float, distance_m: float) -> float:
    if distance_m <= 0:
        raise ValueError("distance must be positive")
    return power_w / (4 * math.pi * distance_m * distance_m)

def sabine_rt60(volume_m3: float, absorption_area_m2_sabins: float) -> float:
    if volume_m3 < 0 or absorption_area_m2_sabins <= 0:
        raise ValueError("invalid room parameters")
    return 0.161 * volume_m3 / absorption_area_m2_sabins

def planck_budget(observable_radius_m: float = 4.4e26, elapsed_s: float = 4.35e17) -> dict:
    volume = 4.0 / 3.0 * math.pi * observable_radius_m ** 3
    spatial_cells = volume / PLANCK_LENGTH ** 3
    time_steps = elapsed_s / PLANCK_TIME
    return {
        "spatial_cells": spatial_cells,
        "time_steps": time_steps,
        "cell_updates": spatial_cells * time_steps,
        "log10_cell_updates": math.log10(spatial_cells * time_steps),
    }
