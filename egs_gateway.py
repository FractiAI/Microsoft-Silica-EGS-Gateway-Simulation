"""
EGS Gateway: real-time translator between solar-hydrogen frequencies and digital logic.

Implements resonant filtering (1030 nm reader), the EGS Fractal Constant (gateway key),
and holographic interference logic (AR14409 vs hydrogen phase-flip).
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum, auto
from typing import Sequence

# --- Physical / reference anchors (simulation units) ---------------------------------
LAMBDA_READER_NM = 1030.0
# H-alpha rest wavelength (nm): geometric anchor for hydrogen line locking
LAMBDA_H_ALPHA_NM = 656.28
# Baseline solar wind speed used to normalize live input (km/s)
REFERENCE_SOLAR_WIND_KM_S = 400.0
# Live nominal from Seed
DEFAULT_SOLAR_WIND_KM_S = 551.7

PHI = (1.0 + math.sqrt(5.0)) / 2.0


def egs_fractal_constant() -> float:
    """
    The EGS Fractal Constant: bridges El Gran Sol's effective optical scale to
    hydrogen's geometric scaling (reader / H-alpha in φ-weighted form).

    Scale-invariant lock: same dimensionless key at any voxel diffraction order.
    """
    ratio = LAMBDA_READER_NM / LAMBDA_H_ALPHA_NM
    return PHI * ratio


K_EGS = egs_fractal_constant()
EGS_FRACTAL_CONSTANT = K_EGS


def gateway_filter(
    solar_wind_speed_km_s: float = DEFAULT_SOLAR_WIND_KM_S,
    *,
    reader_wavelength_nm: float = LAMBDA_READER_NM,
) -> dict[str, float]:
    """
    Apply live solar wind as a phase bias to the virtual 1030 nm reader.

    Phase bias is proportional to normalized wind speed and the fractal key,
    wrapped to [0, 2π). Effective wavelength shift (nm) is a first-order
    coupling for lock diagnostics.
    """
    if solar_wind_speed_km_s <= 0:
        raise ValueError("solar_wind_speed_km_s must be positive")

    norm = solar_wind_speed_km_s / REFERENCE_SOLAR_WIND_KM_S
    phase_bias_rad = (2.0 * math.pi * norm * K_EGS) % (2.0 * math.pi)
    # Small dispersive shift tied to lock (simulation model)
    effective_shift_nm = reader_wavelength_nm * (K_EGS * 1e-4) * math.sin(phase_bias_rad)

    return {
        "phase_bias_rad": phase_bias_rad,
        "effective_wavelength_shift_nm": effective_shift_nm,
        "reader_wavelength_nm": reader_wavelength_nm,
        "lock_strength": abs(math.cos(phase_bias_rad)),
    }


class InterferenceVerdict(Enum):
    """Holographic logic: not raw Boolean — interference outcome at named nodes."""

    CONSTRUCTIVE_AR14409 = auto()  # "True" branch
    DESTRUCTIVE_H_PHASE_FLIP = auto()  # "False" branch
    MIXED = auto()


@dataclass(frozen=True)
class NodeField:
    """Complex amplitude at a holographic node (living resonator model)."""

    re: float
    im: float

    @property
    def magnitude(self) -> float:
        return math.hypot(self.re, self.im)

    def __add__(self, other: NodeField) -> NodeField:
        return NodeField(self.re + other.re, self.im + other.im)

    def scaled(self, s: float) -> NodeField:
        return NodeField(self.re * s, self.im * s)


def _interference_intensity(a: NodeField, b: NodeField) -> float:
    """|a + b|^2 — constructive vs destructive comparison."""
    s = a + b
    return s.re * s.re + s.im * s.im


def holographic_gate(
    ar14409: NodeField,
    hydrogen_phase_flip: NodeField,
    *,
    reference: NodeField | None = None,
    margin: float = 1e-9,
) -> InterferenceVerdict:
    """
    Interference logic gates:

    - "True": constructive interference dominates at the AR14409 node (vs reference beat).
    - "False": destructive outcome dominates at the Hydrogen Phase-Flip node.
    """
    ref = reference if reference is not None else NodeField(1.0, 0.0)

    i_ar = _interference_intensity(ar14409, ref)
    # Phase-flip node: compare against conjugate-beat (destructive when out of phase)
    h_conj = NodeField(hydrogen_phase_flip.re, -hydrogen_phase_flip.im)
    i_h = _interference_intensity(hydrogen_phase_flip, h_conj)

    if i_ar > i_h + margin:
        return InterferenceVerdict.CONSTRUCTIVE_AR14409
    if i_h > i_ar + margin:
        return InterferenceVerdict.DESTRUCTIVE_H_PHASE_FLIP
    return InterferenceVerdict.MIXED


def is_holographic_true(verdict: InterferenceVerdict) -> bool:
    return verdict is InterferenceVerdict.CONSTRUCTIVE_AR14409


def is_holographic_false(verdict: InterferenceVerdict) -> bool:
    return verdict is InterferenceVerdict.DESTRUCTIVE_H_PHASE_FLIP


# --- Master burn + prediction ----------------------------------------------------------


def burn_master_fractal(seed: int, length: int) -> list[float]:
    """
    Deterministic 'burned' fractal pattern on the master (logistic map in φ-scaled form).
    """
    if length < 1:
        raise ValueError("length must be >= 1")
    x = (seed % 1000) / 1000.0
    if x <= 0.0 or x >= 1.0:
        x = 0.5
    out: list[float] = []
    r = 3.2 + (K_EGS % 1.0)  # keep r in chaotic-but-stable band for demo
    for _ in range(length):
        x = r * x * (1.0 - x)
        out.append(x)
    return out


def predict_next_solar_hydrogen_state(
    master_pattern: Sequence[float],
    solar_wind_speed_km_s: float,
    index: int,
) -> float:
    """
    Predict the next solar-hydrogen coupled state using the burned master and live wind.

    Uses gateway phase bias to rotate the fractal iterate — self-correcting when
    the Sun's driving term (wind) shifts.
    """
    if not master_pattern:
        raise ValueError("master_pattern must be non-empty")
    if index < 0 or index >= len(master_pattern):
        raise ValueError("index out of range for master_pattern")

    gf = gateway_filter(solar_wind_speed_km_s)
    phase = gf["phase_bias_rad"]
    base = master_pattern[index]
    # Couple wind phase to hydrogen line scale via K_EGS
    correction = K_EGS * 0.01 * math.sin(phase)
    nxt_idx = (index + 1) % len(master_pattern)
    predicted = (master_pattern[nxt_idx] + base * correction + math.sin(phase) * 0.05) % 1.0
    return predicted


def self_correct_with_sunspots(
    master_pattern: Sequence[float],
    sunspot_index: float,
    solar_wind_speed_km_s: float,
) -> list[float]:
    """
    Apply sunspot activity as a slow amplitude on the master (no human in the loop).
    """
    gf = gateway_filter(solar_wind_speed_km_s)
    lock = gf["lock_strength"]
    scale = 1.0 + 0.02 * math.sin(sunspot_index) * lock
    return [min(1.0, max(0.0, float(x) * scale)) for x in master_pattern]


__all__ = [
    "DEFAULT_SOLAR_WIND_KM_S",
    "EGS_FRACTAL_CONSTANT",
    "InterferenceVerdict",
    "K_EGS",
    "LAMBDA_H_ALPHA_NM",
    "LAMBDA_READER_NM",
    "NodeField",
    "REFERENCE_SOLAR_WIND_KM_S",
    "burn_master_fractal",
    "egs_fractal_constant",
    "gateway_filter",
    "holographic_gate",
    "is_holographic_false",
    "is_holographic_true",
    "predict_next_solar_hydrogen_state",
    "self_correct_with_sunspots",
]
