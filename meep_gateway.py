"""
EGS Gateway FDTD coupling.

Backend priority:
  1. MIT Meep (pymeep via conda-forge) — research-grade FDTD
  2. silica_fdtd               — our own pure-Python+NumPy 2D TM Yee FDTD

Both backends expose the same Meep-compatible API, so this file is
backend-agnostic.  No Conda, no WSL, no external C library required
for the silica_fdtd path.

NSPFRNP → ∞⁹
"""

from __future__ import annotations

import cmath
from typing import Any

from egs_gateway import DEFAULT_SOLAR_WIND_KM_S, LAMBDA_READER_NM, gateway_filter


# ---------------------------------------------------------------------------
# Backend discovery
# ---------------------------------------------------------------------------

def _backend_name() -> str:
    try:
        import meep  # noqa: F401
        return "meep"
    except ImportError:
        pass
    try:
        import silica_fdtd  # noqa: F401
        return "silica_fdtd"
    except ImportError:
        return "none"


def meep_available() -> bool:
    """True when any FDTD backend (Meep or silica_fdtd) is importable."""
    return _backend_name() != "none"


def _import_mp() -> Any:
    """Import and return the active FDTD backend module."""
    name = _backend_name()
    if name == "meep":
        import meep as mp
        return mp
    if name == "silica_fdtd":
        import silica_fdtd as mp
        return mp
    raise RuntimeError(
        "No FDTD backend found. "
        "silica_fdtd should always be present in this repo — "
        "check that silica_fdtd/__init__.py and _core.py exist."
    )


# ---------------------------------------------------------------------------
# Material constants
# ---------------------------------------------------------------------------

def fused_silica_epsilon() -> float:
    """Fused silica ε ≈ n² at 1 µm (n ≈ 1.45)."""
    return 1.45 ** 2   # ≈ 2.1025


# ---------------------------------------------------------------------------
# Gateway FDTD run
# ---------------------------------------------------------------------------

def run_silica_reader_meep(
    solar_wind_km_s: float = DEFAULT_SOLAR_WIND_KM_S,
    *,
    reader_wavelength_nm: float = LAMBDA_READER_NM,
    resolution: int = 16,
    until: float | None = None,
    decay_dt: float = 50.0,
    decay_level: float = 1e-5,
) -> dict[str, float | str]:
    """
    2D TM (Ez) FDTD: gateway-phase-biased Gaussian pulse, fused-silica slab,
    flux monitor past the slab.

    Length unit a = 1 µm; frequency = 1/λ₀ (Meep / silica_fdtd units, c=1).

    Returns gateway_filter diagnostics plus the transmitted flux at fcen.
    """
    mp  = _import_mp()
    gf  = gateway_filter(solar_wind_km_s, reader_wavelength_nm=reader_wavelength_nm)
    phase = float(gf["phase_bias_rad"])
    amp   = cmath.exp(1j * phase)   # complex source amplitude carries the EGS phase

    wavelength_um = reader_wavelength_nm / 1000.0
    fcen = 1.0 / wavelength_um          # center frequency in Meep units
    df   = 0.12 * fcen                  # bandwidth

    # Domain geometry (µm)
    sx      = 18.0
    sy      = 8.0
    dpml    = 1.0
    glass_w = 2.0
    glass_h = sy - 2 * dpml            # 6 µm — interior y span

    cell  = mp.Vector3(sx, sy, 0)
    _eps  = fused_silica_epsilon()
    glass = mp.Block(
        center   = mp.Vector3(0, 0, 0),
        size     = mp.Vector3(glass_w, glass_h, 0),
        material = mp.Medium(epsilon_diag=mp.Vector3(_eps, _eps, _eps)),
    )

    # Line source spanning glass interior in y, set back in x
    src_x = -0.32 * sx
    sources = [
        mp.Source(
            src       = mp.GaussianSource(frequency=fcen, fwidth=df),
            component = mp.Ez,
            center    = mp.Vector3(src_x, 0, 0),
            size      = mp.Vector3(0, glass_h, 0),
            amplitude = amp,
        )
    ]

    sim = mp.Simulation(
        cell_size       = cell,
        boundary_layers = [mp.PML(dpml)],
        geometry        = [glass],
        sources         = sources,
        resolution      = resolution,
    )

    # Flux monitor on the exit side
    mon_x = 0.32 * sx
    region = mp.FluxRegion(
        center = mp.Vector3(mon_x, 0, 0),
        size   = mp.Vector3(0, glass_h, 0),
    )
    flux = sim.add_flux(fcen, df, 1, region)

    if until is not None:
        sim.run(until=until)
    else:
        sim.run(
            until_after_sources=mp.stop_when_fields_decayed(decay_dt, decay_level)
        )

    fluxes      = mp.get_fluxes(flux)
    transmitted = float(fluxes[0]) if fluxes else float("nan")
    backend_ver = getattr(mp, "__version__", "unknown")

    return {
        "backend":                     str(_backend_name()),
        "backend_version":             str(backend_ver),
        "fcen":                        fcen,
        "transmitted_flux":            transmitted,
        "phase_bias_rad":              phase,
        "lock_strength":               float(gf["lock_strength"]),
        "effective_wavelength_shift_nm": float(gf["effective_wavelength_shift_nm"]),
        # legacy key kept for compatibility
        "meep_version":                str(backend_ver),
    }


__all__ = [
    "fused_silica_epsilon",
    "meep_available",
    "run_silica_reader_meep",
]
