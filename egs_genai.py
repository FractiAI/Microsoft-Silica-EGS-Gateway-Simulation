"""
EGS Holographic Generative Model
=================================
Layer 3 / 4 of the EGS Gateway four-layer stack.

A character-level autoregressive generative model where every component
maps to a physical observable in the FDTD simulation:

  Weights      = 101-Moon page fractal values (burned from AR14409 seed)
  Embedding    = phase encoding  φ_token = token_id × 2π / VOCAB_SIZE
  Scoring      = predict_next_solar_hydrogen_state() — fractal + gateway phase
  Entropy      = live solar wind phase bias (physically sourced)
  Logic gate   = holographic_gate (InterferenceVerdict) — constructive = True
  Anchor       = one FDTD SYS_EXEC per generation sequence (physical receipt)
  Audit        = SHA-256 Layer-C hash at every generation step

This is not a language model trained on a text corpus.
It is a physics-native generative model: the AR14409 fractal master IS the
prior.  The solar wind IS the entropy source.  The holographic gate IS the
activation function.  The FDTD transmitted flux IS the generation receipt.

Generation algorithm
--------------------
For each token position t:
  1. context_key  = K_EGS-weighted hash of last 4 chars → Moon page [0, 100]
  2. next_val     = predict_next_solar_hydrogen_state(master, solar_wind, key)
  3. token_id     = floor(next_val × VOCAB_SIZE)
  4. char         = VOCAB[token_id]
  5. layer_c      = SHA-256[:16] of {step, key, next_val, token_id}

After the full sequence: one SYS_EXEC anchors the generation to a real FDTD
run.  The transmitted flux IS the generation receipt.

NSPFRNP → ∞⁹
"""

from __future__ import annotations

import hashlib
import json
import math
from dataclasses import dataclass, field
from typing import List

from egs_gateway import (
    DEFAULT_SOLAR_WIND_KM_S,
    K_EGS,
    predict_next_solar_hydrogen_state,
)
from egs_os import EGSKernel, N_MOON_PAGES, SYS

# ---------------------------------------------------------------------------
# Vocabulary
# ---------------------------------------------------------------------------

VOCAB: List[str] = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .-:")
VOCAB_SIZE: int = len(VOCAB)  # 40


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------

@dataclass
class TokenStep:
    """One autoregressive generation step."""
    step:        int
    context_key: int      # Moon page address used as weight index
    fractal_val: float    # predict_next_solar_hydrogen_state result ∈ [0, 1)
    token_id:    int      # index into VOCAB
    char:        str      # the generated character
    layer_c:     str      # SHA-256[:16] tamper-evident audit hash


@dataclass
class GenerationResult:
    """Complete result of one holographic generation run."""
    prompt:     str
    generated:  str       # characters produced after the prompt
    full_text:  str       # prompt + generated
    solar_wind: float     # km/s — entropy source used
    fdtx_flux:  float     # FDTD transmitted flux (physical anchor receipt)
    verdict:    str       # InterferenceVerdict from the anchor FDTD exec
    exec_hash:  str       # Layer-C hash from the anchor SYS_EXEC syscall
    steps:      List[TokenStep] = field(default_factory=list)

    @property
    def is_anchored(self) -> bool:
        """True iff the generation is anchored to a physical FDTD run."""
        return self.fdtx_flux > 0.0

    @property
    def full_audit(self) -> List[dict]:
        return [
            {"step": s.step, "page": s.context_key,
             "val": round(s.fractal_val, 8), "char": s.char,
             "layer_c": s.layer_c}
            for s in self.steps
        ]


# ---------------------------------------------------------------------------
# EGS Holographic Language Model
# ---------------------------------------------------------------------------

class EGSHolographicLM:
    """
    Holographic language model running on the EGS Silica Voxel Processor.

    Weights are the 101-Moon fractal pages burned from the AR14409 seed.
    Inference = predict_next_solar_hydrogen_state (fractal + gateway filter).
    One FDTD SYS_EXEC per sequence anchors generation to physical compute.

    Parameters
    ----------
    kernel : EGSKernel
        A booted EGS OS kernel.  The fractal master (101 values) is read
        directly from kernel._master; Moon pages provide phase-locked weights.
    """

    def __init__(self, kernel: EGSKernel) -> None:
        self.kernel = kernel

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _context_key(self, context: str) -> int:
        """
        Map the last 4 characters of `context` to a Moon page address in
        [0, N_MOON_PAGES).

        Uses a K_EGS-weighted polynomial hash so that:
          - nearby characters in the vocab produce different keys
          - the mapping is deterministic and scale-invariant
        """
        h = sum(
            ord(c) * (K_EGS ** i)
            for i, c in enumerate(reversed(context[-4:]))
        )
        return int(abs(h)) % N_MOON_PAGES

    # ------------------------------------------------------------------
    # Generation
    # ------------------------------------------------------------------

    def generate(
        self,
        prompt:     str   = "EGS",
        length:     int   = 24,
        solar_wind: float = DEFAULT_SOLAR_WIND_KM_S,
        exec_pid:   int   = 1,
    ) -> GenerationResult:
        """
        Autoregressively generate `length` characters after `prompt`.

        Parameters
        ----------
        prompt     : seed text (uppercased before use)
        length     : number of characters to generate
        solar_wind : km/s — the live solar wind speed driving generation entropy
        exec_pid   : PID of the process used for the anchor FDTD exec

        Returns
        -------
        GenerationResult with full audit trail and FDTD anchor receipt.
        """
        if not self.kernel._booted:
            raise RuntimeError("EGSKernel must be booted before generation")
        if length < 1:
            raise ValueError("length must be >= 1")

        master    = self.kernel._master
        context   = prompt.upper()
        generated = ""
        steps: List[TokenStep] = []

        for step in range(length):
            # 1. Map context → Moon page address
            key = self._context_key(context + generated)
            idx = key % len(master)

            # 2. Predict next state: fractal master + solar wind entropy
            next_val = predict_next_solar_hydrogen_state(master, solar_wind, idx)

            # 3. Map [0, 1) → token index → character
            token_id = int(next_val * VOCAB_SIZE) % VOCAB_SIZE
            char     = VOCAB[token_id]

            # 4. Layer-C audit hash for this step
            payload = json.dumps(
                {"s": step, "k": key, "v": round(next_val, 8), "t": token_id},
                sort_keys=True,
            ).encode()
            layer_c = hashlib.sha256(payload).hexdigest()[:16]

            steps.append(TokenStep(step, key, next_val, token_id, char, layer_c))
            generated += char

        # 5. Physical anchor: one FDTD SYS_EXEC — flux IS the generation receipt
        exec_r    = self.kernel.syscall(SYS.EXEC, exec_pid)
        flux      = exec_r.retval
        verdict   = exec_r.data.get("verdict", "UNKNOWN")
        exec_hash = exec_r.layer_c

        return GenerationResult(
            prompt     = context,
            generated  = generated,
            full_text  = context + generated,
            solar_wind = solar_wind,
            fdtx_flux  = flux,
            verdict    = verdict,
            exec_hash  = exec_hash,
            steps      = steps,
        )


__all__ = [
    "VOCAB",
    "VOCAB_SIZE",
    "TokenStep",
    "GenerationResult",
    "EGSHolographicLM",
]
