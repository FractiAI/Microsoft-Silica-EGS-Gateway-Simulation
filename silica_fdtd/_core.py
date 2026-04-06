"""
silica_fdtd._core
=================
2D TM Yee FDTD engine — pure Python + NumPy.

Seed : Maxwell's equations on a staggered Yee grid (Yee 1966).
Edge : EGS Gateway 1030 nm reader path — gateway-phase-biased pulse
       propagating through a fused-silica slab; flux at the exit monitor.

Meep-compatible public API so meep_gateway.py can swap backends with one
import change.  Length unit a = 1 µm; c = 1 (Meep natural units).

NSPFRNP → ∞⁹
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass, field
from typing import Any, List, Optional

import numpy as np

# ---------------------------------------------------------------------------
# Component / direction constants (Meep-compatible names)
# ---------------------------------------------------------------------------
Ez = "Ez"
Hx = "Hx"
Hy = "Hy"
X  = "X"
Y  = "Y"
Z  = "Z"
AUTOMATIC    = "AUTOMATIC"
NO_DIRECTION = "NO_DIRECTION"


# ---------------------------------------------------------------------------
# Geometry primitives
# ---------------------------------------------------------------------------

@dataclass
class Vector3:
    x: float = 0.0
    y: float = 0.0
    z: float = 0.0

    def __mul__(self, n: float) -> "Vector3":           # noqa: D105
        return Vector3(self.x * n, self.y * n, self.z * n)


@dataclass
class Medium:
    """Isotropic or diagonally anisotropic non-dispersive medium."""
    epsilon: float = 1.0
    epsilon_diag: Optional[Vector3] = None

    def __post_init__(self) -> None:
        if self.epsilon_diag is not None:
            # Use x-component as scalar permittivity (sufficient for TM)
            self.epsilon = float(self.epsilon_diag.x)


@dataclass
class Block:
    """Rectangular block of material."""
    center:   Vector3
    size:     Vector3
    material: Medium


# ---------------------------------------------------------------------------
# Sources
# ---------------------------------------------------------------------------

@dataclass
class GaussianSource:
    """
    Gaussian-enveloped sinusoidal source.

    The temporal profile is:
        s(t) = exp(-½((t - t₀)/width)²) · cos(2π·frequency·t)
    where  t₀ = start_time + cutoff·width.
    """
    frequency:  float
    fwidth:     float = 0.0
    width:      float = 0.0
    start_time: float = 0.0
    cutoff:     float = 5.0
    wavelength: Optional[float] = None

    def __post_init__(self) -> None:
        if self.wavelength is not None:
            self.frequency = 1.0 / self.wavelength
        # Resolve width ↔ fwidth
        if self.fwidth > 0.0 and self.width == 0.0:
            self.width = 1.0 / self.fwidth
        elif self.width > 0.0 and self.fwidth == 0.0:
            self.fwidth = 1.0 / self.width
        if self.width == 0.0:
            self.width = 5.0 / max(self.frequency, 1e-12)

    def envelope(self, t: float) -> float:
        t0 = self.start_time + self.cutoff * self.width
        return math.exp(-0.5 * ((t - t0) / self.width) ** 2)

    def __call__(self, t: float) -> float:
        return self.envelope(t)


@dataclass
class Source:
    """Places a source component on the grid."""
    src:       GaussianSource
    component: str
    center:    Vector3
    size:      Vector3 = field(default_factory=lambda: Vector3(0, 0, 0))
    amplitude: complex = 1.0 + 0j


# ---------------------------------------------------------------------------
# Boundary layers
# ---------------------------------------------------------------------------

@dataclass
class PML:
    """Perfectly-Matched Layer absorbing boundary."""
    thickness: float


# ---------------------------------------------------------------------------
# Monitors
# ---------------------------------------------------------------------------

@dataclass
class FluxRegion:
    """Region over which to accumulate DFT Poynting flux."""
    center:    Vector3
    size:      Vector3 = field(default_factory=lambda: Vector3(0, 0, 0))
    direction: str = AUTOMATIC
    weight:    float = 1.0


class DftFlux:
    """
    Accumulates frequency-domain Poynting flux (x-directed: Sx = −Ez·Hy)
    at a vertical monitor plane ix = const over y ∈ [j0, j1).

    The DFT is computed as:
        Ẽ(f) = Σₙ Ez[n] · exp(−2πi·f·tₙ) · dt
    Flux  = Re(Σⱼ −Ẽz[j] · Ħy*[j]) · dy
    """

    def __init__(self, ix: int, j0: int, j1: int, fcen: float,
                 Ny: int, dy: float) -> None:
        self.ix   = ix
        self.j0   = max(0, j0)
        self.j1   = min(Ny, j1)
        self.fcen = fcen
        self.dy   = dy
        self.Ny   = Ny
        self._Ez_dft: np.ndarray = np.zeros(Ny, dtype=complex)
        self._Hy_dft: np.ndarray = np.zeros(Ny, dtype=complex)

    def accumulate(self, Ez_row: np.ndarray, Hy_row: np.ndarray,
                   t: float, dt: float) -> None:
        phase = cmath.exp(-2j * math.pi * self.fcen * t) * dt
        self._Ez_dft += Ez_row * phase
        self._Hy_dft += Hy_row * phase

    def flux(self) -> float:
        """Return scalar x-directed power flux at fcen."""
        integrand = -self._Ez_dft[self.j0:self.j1] * np.conj(
            self._Hy_dft[self.j0:self.j1]
        )
        return float(np.real(np.sum(integrand)) * self.dy)


# ---------------------------------------------------------------------------
# Stopping criterion
# ---------------------------------------------------------------------------

class _StopWhenDecayed:
    """Stop after sources end once max|Ez| decays to level · peak."""

    def __init__(self, decay_dt: float, level: float) -> None:
        self._decay_dt   = decay_dt
        self._level      = level
        self._peak: float      = 0.0
        self._last_check: float = 0.0
        self._src_end: Optional[float] = None

    def __call__(self, sim: "Simulation") -> bool:
        if self._src_end is None and sim._sources:
            s = sim._sources[0].src
            self._src_end = s.start_time + 2.0 * s.cutoff * s.width
        if self._src_end is not None and sim._t < self._src_end:
            return False
        cur = float(np.max(np.abs(sim._Ez)))
        self._peak = max(self._peak, cur)
        if sim._t - self._last_check >= self._decay_dt:
            self._last_check = sim._t
            if self._peak > 0.0 and cur < self._level * self._peak:
                return True
        return False


def stop_when_fields_decayed(
    decay_dt: float = 50.0,
    level:    float = 1e-5,
) -> _StopWhenDecayed:
    return _StopWhenDecayed(decay_dt, level)


def get_fluxes(dft_flux: DftFlux) -> List[float]:
    """Return list of flux values (length == nfreq, here always 1)."""
    return [dft_flux.flux()]


# ---------------------------------------------------------------------------
# Main simulation class
# ---------------------------------------------------------------------------

class Simulation:
    """
    2D TM Yee FDTD simulation with PML, material blocks, Gaussian sources,
    and DFT flux monitors.

    Update equations (leapfrog, conductivity-FDTD form):
        Hx[i,j]  = Ca_h[i,j]·Hx[i,j]  − Ch[i,j]/dy · (Ez[i,j+1]−Ez[i,j])
        Hy[i,j]  = Ca_h[i,j]·Hy[i,j]  + Ch[i,j]/dx · (Ez[i+1,j]−Ez[i,j])
        Ez[i,j]  = Ca[i,j]·Ez[i,j]
                 + Cb[i,j]·((Hy[i,j]−Hy[i−1,j])/dx − (Hx[i,j]−Hx[i,j−1])/dy)

    where Ca = (1−σdt/2)/(1+σdt/2),  Cb = dt/ε / (1+σdt/2).
    PML conductivity σ: polynomial-graded (m=3) matching target R = 1e-8.
    """

    __version__ = "1.0.0-egs"

    def __init__(
        self,
        cell_size:         Vector3,
        boundary_layers:   list,
        geometry:          list,
        sources:           list,
        resolution:        int,
        default_material:  Optional[Medium] = None,
    ) -> None:
        sx, sy     = cell_size.x, cell_size.y
        self._Nx   = max(4, round(sx * resolution))
        self._Ny   = max(4, round(sy * resolution))
        self._dx   = sx / self._Nx
        self._dy   = sy / self._Ny
        self._sx   = sx
        self._sy   = sy
        self._res  = resolution
        # Courant factor for 2D: dt = Sc/(c·√2·res), Sc=0.45
        self._dt   = 0.45 / (math.sqrt(2.0) * resolution)
        self._t    = 0.0

        self._sources:  list = list(sources)
        self._monitors: List[DftFlux] = []

        # PML thickness
        self._dpml       = 0.0
        self._dpml_cells = 0
        for bl in boundary_layers:
            if isinstance(bl, PML):
                self._dpml       = bl.thickness
                self._dpml_cells = round(bl.thickness * resolution)

        # Field arrays (all Nx × Ny, real)
        self._Ez = np.zeros((self._Nx, self._Ny), dtype=float)
        self._Hx = np.zeros((self._Nx, self._Ny), dtype=float)
        self._Hy = np.zeros((self._Nx, self._Ny), dtype=float)

        # Material: relative permittivity
        self._eps_r   = np.ones((self._Nx, self._Ny), dtype=float)
        # PML conductivity (same for E and H → impedance matched)
        self._sigma   = np.zeros((self._Nx, self._Ny), dtype=float)

        self._build_geometry(geometry)
        self._build_pml()
        self._precompute_coeffs()

    # ------------------------------------------------------------------
    # Grid construction helpers
    # ------------------------------------------------------------------

    def _xy_to_ij(self, x: float, y: float) -> tuple:
        """Map simulation coordinates (origin at cell centre) → array indices."""
        i = int((x + self._sx * 0.5) * self._res)
        j = int((y + self._sy * 0.5) * self._res)
        return (
            max(0, min(self._Nx - 1, i)),
            max(0, min(self._Ny - 1, j)),
        )

    def _build_geometry(self, geometry: list) -> None:
        for obj in geometry:
            if isinstance(obj, Block):
                cx, cy = obj.center.x, obj.center.y
                hw, hh = obj.size.x * 0.5, obj.size.y * 0.5
                i0, j0 = self._xy_to_ij(cx - hw + 1e-9, cy - hh + 1e-9)
                i1, j1 = self._xy_to_ij(cx + hw - 1e-9, cy + hh - 1e-9)
                self._eps_r[i0 : i1 + 1, j0 : j1 + 1] = obj.material.epsilon

    def _build_pml(self) -> None:
        if self._dpml <= 0.0:
            return
        m         = 3
        R_target  = 1e-8
        sigma_max = -(m + 1) * math.log(R_target) / (2.0 * self._dpml)
        nc        = self._dpml_cells

        for k in range(nc):
            d = (nc - k) * self._dx
            s = sigma_max * (d / self._dpml) ** m
            # x-PML (left / right)
            self._sigma[k, :]            = np.maximum(self._sigma[k, :],            s)
            self._sigma[self._Nx-1-k, :] = np.maximum(self._sigma[self._Nx-1-k, :], s)

        for k in range(nc):
            d = (nc - k) * self._dy
            s = sigma_max * (d / self._dpml) ** m
            # y-PML (bottom / top)
            self._sigma[:, k]            = np.maximum(self._sigma[:, k],            s)
            self._sigma[:, self._Ny-1-k] = np.maximum(self._sigma[:, self._Ny-1-k], s)

    def _precompute_coeffs(self) -> None:
        dt = self._dt
        half = 0.5 * dt
        # E-field coefficients (include material eps)
        denom_e    = 1.0 + self._sigma * half
        self._Ca   = (1.0 - self._sigma * half) / denom_e
        self._Cb   = (dt / self._eps_r) / denom_e      # dt/(eps·(1+σdt/2))
        # H-field coefficients (mu=1, same sigma → impedance match)
        denom_h    = 1.0 + self._sigma * half
        self._Ca_h = (1.0 - self._sigma * half) / denom_h
        self._Ch   = dt / denom_h

    # ------------------------------------------------------------------
    # Monitor registration
    # ------------------------------------------------------------------

    def add_flux(
        self,
        fcen:   float,
        df:     float,
        nfreq:  int,
        region: FluxRegion,
    ) -> DftFlux:
        cx = region.center.x
        cy = region.center.y
        ix, _ = self._xy_to_ij(cx, cy)
        if region.size.y > 0.0:
            hh   = region.size.y * 0.5
            _, j0 = self._xy_to_ij(cx, cy - hh)
            _, j1 = self._xy_to_ij(cx, cy + hh)
            j1 = min(j1 + 1, self._Ny)
        else:
            j0, j1 = 0, self._Ny
        mon = DftFlux(ix, j0, j1, fcen, self._Ny, self._dy)
        self._monitors.append(mon)
        return mon

    # ------------------------------------------------------------------
    # Source evaluation
    # ------------------------------------------------------------------

    def _eval_source(self, src_obj: Source, t: float) -> tuple:
        """Return (ix, j0, j1, Jz) for source at time t."""
        cx, cy = src_obj.center.x, src_obj.center.y
        hy     = src_obj.size.y * 0.5
        ix, _  = self._xy_to_ij(cx, cy)
        _, j0  = self._xy_to_ij(cx, cy - hy)
        _, j1  = self._xy_to_ij(cx, cy + hy)
        j1     = min(j1 + 1, self._Ny)
        src    = src_obj.src
        env    = src.envelope(t)
        amp    = complex(src_obj.amplitude)
        # Real part of complex amplitude × carrier
        carrier = cmath.exp(2j * math.pi * src.frequency * t)
        Jz      = float((amp * env * carrier).real)
        return ix, j0, j1, Jz

    # ------------------------------------------------------------------
    # Time-step
    # ------------------------------------------------------------------

    def _step(self) -> None:
        dx, dy, dt = self._dx, self._dy, self._dt

        # ── H-field update (leapfrog half-step) ─────────────────────
        self._Hx[:, :-1] = (
            self._Ca_h[:, :-1] * self._Hx[:, :-1]
            - self._Ch[:, :-1] / dy * (self._Ez[:, 1:] - self._Ez[:, :-1])
        )
        self._Hy[:-1, :] = (
            self._Ca_h[:-1, :] * self._Hy[:-1, :]
            + self._Ch[:-1, :] / dx * (self._Ez[1:, :] - self._Ez[:-1, :])
        )

        # ── E-field update (full step) ───────────────────────────────
        # curl H at interior nodes (i ≥ 1, j ≥ 1)
        dHy_dx = (self._Hy[1:, 1:] - self._Hy[:-1, 1:]) / dx   # (Nx-1, Ny-1)
        dHx_dy = (self._Hx[1:, 1:] - self._Hx[1:, :-1]) / dy   # (Nx-1, Ny-1)
        self._Ez[1:, 1:] = (
            self._Ca[1:, 1:] * self._Ez[1:, 1:]
            + self._Cb[1:, 1:] * (dHy_dx - dHx_dy)
        )

        self._t += dt

        # ── Soft sources ─────────────────────────────────────────────
        for src_obj in self._sources:
            ix, j0, j1, Jz = self._eval_source(src_obj, self._t)
            # Soft source: inject current via Cb (has 1/eps factor)
            self._Ez[ix, j0:j1] += Jz * self._Cb[ix, j0:j1]

        # ── Accumulate DFT monitors ──────────────────────────────────
        for mon in self._monitors:
            mon.accumulate(
                self._Ez[mon.ix, :],
                self._Hy[mon.ix, :],
                self._t, dt,
            )

    # ------------------------------------------------------------------
    # Run
    # ------------------------------------------------------------------

    def run(
        self,
        *args: Any,
        until:               Optional[float] = None,
        until_after_sources: Optional[Any]   = None,
    ) -> None:
        if until is not None:
            n = max(1, round(until / self._dt))
            for _ in range(n):
                self._step()
        elif until_after_sources is not None:
            for _ in range(200_000):
                self._step()
                if until_after_sources(self):
                    break
        else:
            n = max(1, round(20.0 / self._dt))
            for _ in range(n):
                self._step()

    # Allow positional step-function arguments (Meep style: sim.run(mp.at_end(...)))
    # — silently ignored; we only honour keyword arguments above.
