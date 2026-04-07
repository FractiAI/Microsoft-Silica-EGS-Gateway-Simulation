"""
HHAAIOS — Holographic Hydrogen AI OS API
=========================================
Layer 3 of the EGS Gateway four-layer stack.

Exposes the EGS OS kernel and holographic FDTD substrate as a clean,
high-level API suitable for AI agents, LLMs, and external applications.

Architecture
------------
  Writer Agent     → encodes data as phase state, writes to H-line bus
                     with a cryptographic SolarReceipt anchored to the Sun
  Reader Agent     → phase-locked read from Moon page via H-line bus
  Verifier Agent   → validates SolarReceipts against physical constants
                     without re-running the FDTD

Solar Compute Receipt
---------------------
  Every write operation produces a receipt anchored to:
    • solar_wind    → live phase bias at time of write (km/s)
    • phase_bias    → gateway_filter(solar_wind)["phase_bias_rad"]
    • crab_tick     → kernel tick counter (Crab pulsar proxy)
    • k_egs         → EGS Fractal Constant 2.5436… (cosmic anchor)
    • epoch         → lattice epoch (incremented on SYS_FLARE)
    • data_hash     → SHA-256[:16] of the written data
    • layer_c       → SHA-256[:16] of all the above (tamper-evident)

  Verification checks:
    1. layer_c      matches recomputed hash (tamper evidence)
    2. k_egs        matches K_EGS universal constant (cosmic anchor)
    3. phase_bias   matches gateway_filter(solar_wind) (deterministic)

Four-Pillar Lock
----------------
  K1 = K_EGS              (EGS Fractal Constant — universe-anchored)
  K2 = solar phase bias   (live, physically sourced entropy)
  K3 = Crab pulsar tick   (cosmic clock — kernel tick counter proxy)
  K4 = AR14409 master hash (boot image fingerprint — SHA-256[:16])

  lock_key = SHA-256( K1 ‖ K2 ‖ K3 ‖ K4 )

  The lock is deterministic for fixed (K1, K2, K3, K4).
  K2 changes with solar wind; K3 advances with every syscall.
  A new lock at a different solar wind or tick will produce a different key.

Claim Grounding
---------------
  ground(claim) checks whether a value or string is consistent with
  EGS physical constants at the current solar wind:
    • numeric claim : |claim % 1.0 − ref_val| < 0.15  (15 % tolerance)
    • string claim  : first 2 hex digits of SHA-256(claim) match ref_hash

NSPFRNP → ∞⁹
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from egs_gateway import (
    DEFAULT_SOLAR_WIND_KM_S,
    K_EGS,
    gateway_filter,
)
from egs_os import EGSKernel, KERNEL_PID, N_MOON_PAGES, SYS
from egs_genai import EGSHolographicLM, GenerationResult


# ---------------------------------------------------------------------------
# Solar Compute Receipt
# ---------------------------------------------------------------------------

@dataclass
class SolarReceipt:
    """
    Cryptographic receipt anchored to the solar wind at time of write.

    Immutable once layer_c is set.  Verify with is_valid().
    """

    address:    int
    data_hash:  str     # SHA-256[:16] of the serialised data
    solar_wind: float   # km/s
    phase_bias: float   # gateway_filter phase_bias_rad
    crab_tick:  int     # kernel tick counter at write time
    k_egs:      float   # K_EGS (always 2.5436…)
    epoch:      int     # lattice epoch
    layer_c:    str     # tamper-evident receipt hash (set by __post_init__)
    writer_pid: int
    record_id:  str

    def __post_init__(self) -> None:
        if not self.layer_c:
            self.layer_c = self._compute_layer_c()

    def _compute_layer_c(self) -> str:
        payload = json.dumps(
            {
                "address":    self.address,
                "data_hash":  self.data_hash,
                "solar_wind": self.solar_wind,
                "phase_bias": round(self.phase_bias, 8),
                "crab_tick":  self.crab_tick,
                "k_egs":      round(self.k_egs, 10),
                "epoch":      self.epoch,
            },
            sort_keys=True,
        ).encode()
        return hashlib.sha256(payload).hexdigest()[:16]

    def is_valid(self) -> bool:
        """True iff the receipt has not been tampered with."""
        return self.layer_c == self._compute_layer_c()

    def to_dict(self) -> dict:
        return {
            "address":    self.address,
            "data_hash":  self.data_hash,
            "solar_wind": self.solar_wind,
            "phase_bias": round(self.phase_bias, 8),
            "crab_tick":  self.crab_tick,
            "k_egs":      round(self.k_egs, 10),
            "epoch":      self.epoch,
            "layer_c":    self.layer_c,
            "writer_pid": self.writer_pid,
            "record_id":  self.record_id,
            "valid":      self.is_valid(),
        }


# ---------------------------------------------------------------------------
# Four-Pillar Lock
# ---------------------------------------------------------------------------

@dataclass
class FourPillarLock:
    """
    Four-pillar authentication key derived from physical constants.

    K1 = K_EGS  (fractal constant)
    K2 = solar phase bias (live)
    K3 = Crab pulsar tick (kernel counter)
    K4 = AR14409 master hash[:16] (boot image)
    lock_key = SHA-256(K1 ‖ K2 ‖ K3 ‖ K4)
    """

    k1_fractal: float   # K_EGS
    k2_phase:   float   # solar phase bias_rad
    k3_crab:    int     # Crab tick counter
    k4_master:  str     # SHA-256[:16] of kernel._master
    lock_key:   str     # 64-char hex SHA-256
    epoch:      int

    @property
    def locked(self) -> bool:
        return bool(self.lock_key)

    def to_dict(self) -> dict:
        return {
            "k1_fractal": self.k1_fractal,
            "k2_phase":   round(self.k2_phase, 8),
            "k3_crab":    self.k3_crab,
            "k4_master":  self.k4_master,
            "lock_key":   self.lock_key,
            "epoch":      self.epoch,
            "locked":     self.locked,
        }


# ---------------------------------------------------------------------------
# HHAAIOS Agent
# ---------------------------------------------------------------------------

class HHAAIOSAgent:
    """
    Holographic Hydrogen AI OS API agent — Layer 3 of the EGS Gateway stack.

    Wraps EGSKernel and EGSHolographicLM to expose a unified API for:
      write / read    — H-line bus I/O with SolarReceipt proof
      verify          — receipt validation without re-running FDTD
      four_pillar_lock— cosmic authentication key
      generate        — holographic autoregressive sequence generation
      ground          — claim verification against physical constants

    Agents
    ------
      writer_pid   — process that encodes and writes data to the H-line bus
      reader_pid   — process that performs phase-locked reads
      verifier_pid — process that validates receipts
    """

    def __init__(
        self,
        kernel:     EGSKernel,
        solar_wind: float = DEFAULT_SOLAR_WIND_KM_S,
    ) -> None:
        self.kernel     = kernel
        self.solar_wind = solar_wind
        self._lm:            Optional[EGSHolographicLM] = None
        self.writer_pid:   int  = -1
        self.reader_pid:   int  = -1
        self.verifier_pid: int  = -1
        self._receipts:    List[SolarReceipt] = []
        self._init_done:   bool = False

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def init_agents(self) -> Dict[str, Any]:
        """
        Spawn writer, reader, and verifier processes on the EGS OS kernel.
        Instantiate the holographic language model.

        Must be called once after kernel.boot() and before any other method.
        """
        if not self.kernel._booted:
            raise RuntimeError("Boot the EGSKernel before calling init_agents()")

        # Fork writer from init (PID 1)
        r_w = self.kernel.fork(1, name="hhaaios.writer")
        if not r_w.ok:
            raise RuntimeError(f"Writer fork failed: {r_w.data}")
        self.writer_pid = int(r_w.retval)

        # Fork reader from writer
        r_r = self.kernel.fork(self.writer_pid, name="hhaaios.reader")
        if not r_r.ok:
            raise RuntimeError(f"Reader fork failed: {r_r.data}")
        self.reader_pid = int(r_r.retval)

        # Fork verifier from reader
        r_v = self.kernel.fork(self.reader_pid, name="hhaaios.verifier")
        if not r_v.ok:
            raise RuntimeError(f"Verifier fork failed: {r_v.data}")
        self.verifier_pid = int(r_v.retval)

        self._lm = EGSHolographicLM(self.kernel)
        self._init_done = True

        return {
            "writer_pid":   self.writer_pid,
            "reader_pid":   self.reader_pid,
            "verifier_pid": self.verifier_pid,
            "lm_ready":     True,
        }

    # ------------------------------------------------------------------
    # Write — H-line bus write with SolarReceipt
    # ------------------------------------------------------------------

    def write(
        self,
        data:       Any,
        solar_wind: float = None,
        address:    int   = -1,
    ) -> SolarReceipt:
        """
        Encode `data` and write it to holographic memory via the H-line bus.

        Parameters
        ----------
        data       : any JSON-serialisable value
        solar_wind : override solar wind for this write (default: agent default)
        address    : Moon page address (-1 = next free page)

        Returns
        -------
        SolarReceipt anchored to solar wind, phase, Crab tick, and K_EGS.
        """
        self._check_init()
        sw = solar_wind if solar_wind is not None else self.solar_wind

        # Serialise data → deterministic float ∈ [0, 1)
        data_str  = json.dumps(data, sort_keys=True, default=str)
        data_hash = hashlib.sha256(data_str.encode()).hexdigest()[:16]
        float_val = int(data_hash[:8], 16) / 0xFFFFFFFF

        # SYS_WRITE via the writer process
        result = self.kernel.write(self.writer_pid, float_val, address)
        if not result.ok:
            raise RuntimeError(f"SYS_WRITE failed: {result.data}")

        addr = int(result.retval)
        gf   = gateway_filter(sw)

        receipt = SolarReceipt(
            address    = addr,
            data_hash  = data_hash,
            solar_wind = sw,
            phase_bias = gf["phase_bias_rad"],
            crab_tick  = self.kernel._tick,
            k_egs      = K_EGS,
            epoch      = self.kernel._epoch,
            layer_c    = "",    # computed in __post_init__
            writer_pid = self.writer_pid,
            record_id  = result.data.get("record_id", ""),
        )
        self._receipts.append(receipt)
        return receipt

    # ------------------------------------------------------------------
    # Read — phase-locked H-line bus read
    # ------------------------------------------------------------------

    def read(self, address: int) -> Dict[str, Any]:
        """
        Perform a phase-locked read from Moon page `address` via the
        reader process's H-line bus coupling.
        """
        self._check_init()
        result = self.kernel.read(self.reader_pid, address)
        return {
            "ok":           result.ok,
            "address":      address,
            "value":        result.retval,
            "lock_strength": result.data.get("lock_strength"),
            "phase_rad":    result.data.get("phase_rad"),
            "value_hash":   result.data.get("value_hash"),
            "record_id":    result.data.get("record_id"),
            "layer_c":      result.layer_c,
        }

    # ------------------------------------------------------------------
    # Verify — validate a SolarReceipt
    # ------------------------------------------------------------------

    def verify(self, receipt: SolarReceipt) -> Dict[str, Any]:
        """
        Verify a SolarReceipt without re-running the FDTD.

        Three checks:
          1. Tamper evidence — layer_c consistent with receipt fields
          2. K_EGS anchor   — k_egs matches universal constant
          3. Phase check    — phase_bias reconstructable from solar_wind
        """
        self._check_init()

        tamper_ok = receipt.is_valid()
        kegs_ok   = abs(receipt.k_egs - K_EGS) < 1e-10

        gf        = gateway_filter(receipt.solar_wind)
        phase_ok  = abs(gf["phase_bias_rad"] - receipt.phase_bias) < 1e-10

        page_hash = (
            self.kernel._memory[receipt.address].value_hash
            if 0 <= receipt.address < N_MOON_PAGES
            else ""
        )

        all_ok = tamper_ok and kegs_ok and phase_ok
        return {
            "ok":             all_ok,
            "tamper_ok":      tamper_ok,
            "kegs_ok":        kegs_ok,
            "phase_ok":       phase_ok,
            "readback_hash":  page_hash,
            "receipt_layer_c": receipt.layer_c,
            "address":        receipt.address,
            "epoch":          receipt.epoch,
        }

    # ------------------------------------------------------------------
    # Four-Pillar Lock
    # ------------------------------------------------------------------

    def four_pillar_lock(self, solar_wind: float = None) -> FourPillarLock:
        """
        Generate a Four-Pillar authentication lock.

        All four pillars are deterministic for the same (solar_wind, tick):
          K1 = K_EGS                          (fractal constant)
          K2 = gateway_filter(sw)["phase_bias_rad"]  (live solar entropy)
          K3 = kernel tick counter             (Crab pulsar proxy)
          K4 = SHA-256[:16] of kernel._master  (AR14409 boot image hash)
        """
        self._check_init()
        sw = solar_wind if solar_wind is not None else self.solar_wind

        k1 = K_EGS
        k2 = gateway_filter(sw)["phase_bias_rad"]
        k3 = self.kernel._tick
        k4 = hashlib.sha256(json.dumps(self.kernel._master).encode()).hexdigest()[:16]
        ep = self.kernel._epoch

        key_payload = json.dumps(
            {"k1": round(k1, 10), "k2": round(k2, 8), "k3": k3, "k4": k4},
            sort_keys=True,
        ).encode()
        lock_key = hashlib.sha256(key_payload).hexdigest()

        return FourPillarLock(
            k1_fractal = k1,
            k2_phase   = k2,
            k3_crab    = k3,
            k4_master  = k4,
            lock_key   = lock_key,
            epoch      = ep,
        )

    # ------------------------------------------------------------------
    # Generate — holographic autoregressive generation
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt:     str   = "EGS",
        length:     int   = 24,
        solar_wind: float = None,
    ) -> GenerationResult:
        """
        Holographic autoregressive generation via EGSHolographicLM.

        Uses the writer process as the FDTD anchor executor so that the
        generation receipt is tied to the same process that writes data.
        """
        self._check_init()
        sw = solar_wind if solar_wind is not None else self.solar_wind
        return self._lm.generate(
            prompt     = prompt,
            length     = length,
            solar_wind = sw,
            exec_pid   = self.writer_pid,
        )

    # ------------------------------------------------------------------
    # Ground — claim verification against physical constants
    # ------------------------------------------------------------------

    def ground(self, claim: Any, solar_wind: float = None) -> Dict[str, Any]:
        """
        Ground a claim against EGS physical constants.

        For numeric claims : checks |claim % 1.0 − ref_val| < 0.15
        For string claims  : checks first 2 hex digits of SHA-256(claim)
                             match the first 2 digits of ref_hash

        ref_val = (K_EGS × lock_strength) % 1.0  — derived from solar physics
        """
        self._check_init()
        sw = solar_wind if solar_wind is not None else self.solar_wind

        claim_str  = json.dumps(claim, default=str)
        claim_hash = hashlib.sha256(claim_str.encode()).hexdigest()[:16]

        gf       = gateway_filter(sw)
        ref_val  = (K_EGS * gf["lock_strength"]) % 1.0
        ref_hash = hashlib.sha256(
            json.dumps({"ref": round(ref_val, 8), "sw": sw}).encode()
        ).hexdigest()[:16]

        if isinstance(claim, (int, float)):
            norm     = float(claim) % 1.0
            grounded = abs(norm - ref_val) < 0.15
        else:
            grounded = claim_hash[:2] == ref_hash[:2]

        verdict_hash = hashlib.sha256(
            json.dumps(
                {"claim_hash": claim_hash, "grounded": grounded,
                 "ref": round(ref_val, 8)},
                sort_keys=True,
            ).encode()
        ).hexdigest()[:16]

        return {
            "grounded":     grounded,
            "claim_hash":   claim_hash,
            "ref_val":      round(ref_val, 6),
            "ref_hash":     ref_hash,
            "solar_wind":   sw,
            "k_egs":        K_EGS,
            "lock_strength": round(gf["lock_strength"], 6),
            "verdict_hash": verdict_hash,
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def receipts(self) -> List[SolarReceipt]:
        """Return all SolarReceipts produced by this agent."""
        return list(self._receipts)

    def _check_init(self) -> None:
        if not self._init_done:
            raise RuntimeError(
                "Call init_agents() before using HHAAIOSAgent methods"
            )


__all__ = [
    "SolarReceipt",
    "FourPillarLock",
    "HHAAIOSAgent",
]
