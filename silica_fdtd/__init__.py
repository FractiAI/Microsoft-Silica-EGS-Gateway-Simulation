"""
silica_fdtd
===========
EGS Gateway FDTD engine — pure Python + NumPy.

Seed : Maxwell on a Yee grid.
Edge : 1030 nm gateway-phase-biased pulse through fused silica → flux.

Meep-compatible API; drop-in backend when pymeep is not installed.
Install requirement: numpy only.

NSPFRNP → ∞⁹
"""

from ._core import (
    # Field / direction constants
    Ez, Hx, Hy, X, Y, Z, AUTOMATIC, NO_DIRECTION,
    # Geometry
    Vector3, Medium, Block,
    # Sources
    GaussianSource, Source,
    # Boundary
    PML,
    # Monitors
    FluxRegion, DftFlux,
    # Simulation
    Simulation,
    # Helpers
    get_fluxes,
    stop_when_fields_decayed,
)

__version__ = "1.0.0-egs"

__all__ = [
    "Ez", "Hx", "Hy", "X", "Y", "Z", "AUTOMATIC", "NO_DIRECTION",
    "Vector3", "Medium", "Block",
    "GaussianSource", "Source",
    "PML",
    "FluxRegion", "DftFlux",
    "Simulation",
    "get_fluxes",
    "stop_when_fields_decayed",
    "__version__",
]
