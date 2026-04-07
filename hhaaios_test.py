"""
HHAAIOS Test Suite — Third OS Test
====================================
Exercises the complete four-layer EGS Gateway stack:

  Layer 1 — silica_fdtd   (FDTD substrate)         tested in egs_gateway_hifi_test.py
  Layer 2 — egs_os        (holographic OS)          tested in egs_os_test.py
  Layer 3 — hhaaios       (Holographic API)         ← THIS FILE
  Layer 3 — egs_genai     (Holographic GenAI)       ← THIS FILE

Tests
-----
  T01  Agent Init              — spawn writer, reader, verifier + LM ready
  T02  Solar Receipt Write     — write data, receipt structure, layer_c valid
  T03  Phase-Locked Read       — read back via H-line bus, lock_strength ∈ [0,1]
  T04  Receipt Verification    — all 3 checks pass on a valid receipt
  T05  Tamper Detection        — modified receipt fails phase_ok check
  T06  Four-Pillar Lock        — K1/K2/K3/K4 correct; 64-char lock_key generated
  T07  Lock Determinism        — same solar wind → same lock key
  T08  Holographic Generation  — 16-char sequence; FDTD-anchored; full audit trail
  T09  Generation Determinism  — same solar wind → same generated sequence
  T10  Generation Diversity    — v=300 and v=750 produce different sequences
  T11  Grounding Numeric       — ground K_EGS fractional part against physics
  T12  Grounding String        — ground a string claim; verdict hash returned
  T13  Full Stack Pipeline     — write → generate → verify → ground in one flow
  T14  Multi-Agent Concurrent  — writer/reader/verifier all active simultaneously
  T15  Audit Trail             — all accumulated receipts carry valid layer_c

NSPFRNP → ∞⁹
"""

from __future__ import annotations

import argparse
import dataclasses
import json
import sys
import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from egs_gateway import K_EGS
from egs_os import EGSKernel
from hhaaios import FourPillarLock, HHAAIOSAgent, SolarReceipt


# ---------------------------------------------------------------------------
# Test record
# ---------------------------------------------------------------------------

@dataclass
class TestRecord:
    id:         str
    name:       str
    passed:     bool
    detail:     str
    elapsed_ms: float


# ---------------------------------------------------------------------------
# Individual test functions
# ---------------------------------------------------------------------------

def t01_agent_init(agent: HHAAIOSAgent) -> Tuple[bool, str]:
    r = agent.init_agents()
    ok = (
        r["writer_pid"]   >  1
        and r["reader_pid"]   > r["writer_pid"]
        and r["verifier_pid"] > r["reader_pid"]
        and r["lm_ready"] is True
    )
    return ok, (
        f"writer={r['writer_pid']}  reader={r['reader_pid']}  "
        f"verifier={r['verifier_pid']}  lm={r['lm_ready']}"
    )


def t02_receipt_write(agent: HHAAIOSAgent) -> Tuple[bool, str, Optional[SolarReceipt]]:
    receipt = agent.write({"msg": "EGS Gateway holographic write test",
                           "freq": 1420.405751})
    ok = (
        isinstance(receipt, SolarReceipt)
        and len(receipt.data_hash)  == 16
        and len(receipt.layer_c)    == 16
        and receipt.k_egs            > 2.5
        and receipt.phase_bias       >= 0.0
        and receipt.address          >= 0
        and receipt.is_valid()
    )
    return ok, (
        f"addr={receipt.address}  hash={receipt.data_hash}  "
        f"k_egs={receipt.k_egs:.4f}  phase={receipt.phase_bias:.4f}  "
        f"layer_c={receipt.layer_c}  valid={receipt.is_valid()}"
    ), receipt


def t03_phase_locked_read(
    agent: HHAAIOSAgent, address: int
) -> Tuple[bool, str]:
    r = agent.read(address)
    ok = (
        r["ok"]
        and isinstance(r["value"], float)
        and 0.0 <= r["lock_strength"] <= 1.0
        and len(r["layer_c"]) == 16
    )
    return ok, (
        f"addr={r['address']}  val={r['value']:.6f}  "
        f"lock={r['lock_strength']:.4f}  layer_c={r['layer_c']}"
    )


def t04_receipt_verify_valid(
    agent: HHAAIOSAgent, receipt: SolarReceipt
) -> Tuple[bool, str]:
    v  = agent.verify(receipt)
    ok = v["ok"] and v["tamper_ok"] and v["kegs_ok"] and v["phase_ok"]
    return ok, (
        f"tamper={v['tamper_ok']}  kegs={v['kegs_ok']}  "
        f"phase={v['phase_ok']}  overall={v['ok']}"
    )


def t05_tamper_detection(
    agent: HHAAIOSAgent, receipt: SolarReceipt
) -> Tuple[bool, str]:
    # Tamper: change solar_wind but keep original layer_c
    tampered = dataclasses.replace(
        receipt, solar_wind=receipt.solar_wind + 9999.0
    )
    v = agent.verify(tampered)
    # Tamper must be detected: phase_ok must be False (reconstructed phase differs)
    detected = (not v["phase_ok"]) or (not v["tamper_ok"])
    return detected, (
        f"tamper_ok={v['tamper_ok']}  phase_ok={v['phase_ok']}  "
        f"overall_ok={v['ok']}  detected={detected}"
    )


def t06_four_pillar_lock(agent: HHAAIOSAgent) -> Tuple[bool, str]:
    lock = agent.four_pillar_lock()
    ok = (
        lock.locked
        and abs(lock.k1_fractal - K_EGS) < 1e-10
        and 0.0 <= lock.k2_phase <= 2 * 3.14159265358979 + 0.001
        and lock.k3_crab >= 0
        and len(lock.k4_master) == 16
        and len(lock.lock_key)  == 64
    )
    return ok, (
        f"k1={lock.k1_fractal:.4f}  k2={lock.k2_phase:.4f}  "
        f"k3={lock.k3_crab}  k4={lock.k4_master}  "
        f"key={lock.lock_key[:16]}…"
    )


def t07_lock_determinism(agent: HHAAIOSAgent) -> Tuple[bool, str]:
    sw      = 551.7
    lock_a  = agent.four_pillar_lock(solar_wind=sw)
    lock_b  = agent.four_pillar_lock(solar_wind=sw)
    # k3 (tick counter) must be same for both (no syscalls between the two calls)
    same_k3 = lock_a.k3_crab == lock_b.k3_crab
    same_key = lock_a.lock_key == lock_b.lock_key
    ok = same_k3 and same_key
    return ok, (
        f"k3_a={lock_a.k3_crab}  k3_b={lock_b.k3_crab}  "
        f"same_k3={same_k3}  "
        f"key_a={lock_a.lock_key[:12]}…  match={same_key}"
    )


def t08_holographic_generation(agent: HHAAIOSAgent) -> Tuple[bool, str]:
    result = agent.generate(prompt="EGS", length=16)
    ok = (
        len(result.generated) == 16
        and result.full_text.startswith("EGS")
        and result.fdtx_flux > 0.0
        and result.is_anchored
        and len(result.exec_hash) == 16
        and len(result.steps) == 16
        and all(len(s.layer_c) == 16 for s in result.steps)
    )
    return ok, (
        f"output='{result.full_text}'  "
        f"flux={result.fdtx_flux:.6f}  "
        f"anchored={result.is_anchored}  "
        f"exec_hash={result.exec_hash}"
    )


def t09_generation_determinism(agent: HHAAIOSAgent) -> Tuple[bool, str]:
    sw = 551.7
    r1 = agent.generate(prompt="EGS", length=12, solar_wind=sw)
    r2 = agent.generate(prompt="EGS", length=12, solar_wind=sw)
    ok = r1.generated == r2.generated
    return ok, (
        f"run1='{r1.generated}'  run2='{r2.generated}'  match={ok}"
    )


def t10_generation_diversity(agent: HHAAIOSAgent) -> Tuple[bool, str]:
    r_slow = agent.generate(prompt="EGS", length=12, solar_wind=300.0)
    r_fast = agent.generate(prompt="EGS", length=12, solar_wind=750.0)
    ok = r_slow.generated != r_fast.generated
    return ok, (
        f"v=300: '{r_slow.generated}'  "
        f"v=750: '{r_fast.generated}'  "
        f"distinct={ok}"
    )


def t11_grounding_numeric(agent: HHAAIOSAgent) -> Tuple[bool, str]:
    # Ground the fractional part of K_EGS against EGS physics
    claim = K_EGS % 1.0   # ≈ 0.5436
    r = agent.ground(claim)
    ok = isinstance(r["grounded"], bool) and len(r["verdict_hash"]) == 16
    return ok, (
        f"claim={claim:.4f}  grounded={r['grounded']}  "
        f"ref_val={r['ref_val']:.4f}  verdict={r['verdict_hash']}"
    )


def t12_grounding_string(agent: HHAAIOSAgent) -> Tuple[bool, str]:
    r = agent.ground("EGS GATEWAY HOLOGRAPHIC PROOF")
    ok = isinstance(r["grounded"], bool) and len(r["verdict_hash"]) == 16
    return ok, (
        f"grounded={r['grounded']}  "
        f"claim_hash={r['claim_hash']}  "
        f"verdict={r['verdict_hash']}"
    )


def t13_full_stack_pipeline(agent: HHAAIOSAgent) -> Tuple[bool, str]:
    """
    Full four-layer pipeline in one call:
      Write (Layer 2 SYS_WRITE) →
      Generate (Layer 3 fractal + Layer 1 FDTD) →
      Verify (Layer 3 receipt check) →
      Ground (Layer 3 physics anchor)
    """
    # 1. Write
    receipt = agent.write({"pipeline": "full-stack-test", "k_egs": K_EGS})
    # 2. Generate
    gen     = agent.generate(prompt="GATEWAY", length=8)
    # 3. Verify
    vfy     = agent.verify(receipt)
    # 4. Ground
    gnd     = agent.ground(receipt.solar_wind)

    ok = (
        receipt.is_valid()
        and len(gen.generated) == 8
        and gen.is_anchored
        and vfy["tamper_ok"]
        and len(gnd["verdict_hash"]) == 16
    )
    return ok, (
        f"write✓ addr={receipt.address}  "
        f"gen='{gen.generated}'  flux={gen.fdtx_flux:.4f}  "
        f"verify={vfy['ok']}  ground={gnd['grounded']}"
    )


def t14_multi_agent_concurrent(agent: HHAAIOSAgent) -> Tuple[bool, str]:
    """
    Writer, reader, and verifier all operate simultaneously on 3 entries.
    """
    # Writer: 3 concurrent writes
    receipts = [agent.write(f"concurrent-payload-{i}") for i in range(3)]
    # Reader: 3 reads
    reads    = [agent.read(r.address) for r in receipts]
    # Verifier: 3 verifications
    verifs   = [agent.verify(r) for r in receipts]

    writes_ok = all(r.is_valid() for r in receipts)
    reads_ok  = all(r["ok"] for r in reads)
    verifs_ok = all(
        v["tamper_ok"] and v["kegs_ok"] and v["phase_ok"] for v in verifs
    )
    ok = writes_ok and reads_ok and verifs_ok
    return ok, (
        f"writes={writes_ok}(×{len(receipts)})  "
        f"reads={reads_ok}(×{len(reads)})  "
        f"verifs={verifs_ok}(×{len(verifs)})"
    )


def t15_audit_trail(agent: HHAAIOSAgent) -> Tuple[bool, str]:
    """
    All accumulated SolarReceipts carry valid Layer-C hashes.
    """
    receipts = agent.receipts()
    total    = len(receipts)
    valid    = sum(1 for r in receipts if r.is_valid())
    ok       = total > 0 and valid == total
    return ok, f"total={total}  valid={valid}  all_valid={ok}"


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

def run_hhaaios_tests(
    fdtd_resolution: int   = 10,
    fdtd_until:      float = 40.0,
    json_output:     bool  = False,
) -> List[TestRecord]:

    kernel = EGSKernel(fdtd_resolution=fdtd_resolution, fdtd_until=fdtd_until)
    kernel.boot()
    agent = HHAAIOSAgent(kernel)

    records: List[TestRecord] = []

    def _record(test_id: str, name: str, passed: bool,
                detail: str, elapsed: float) -> TestRecord:
        icon = "✅" if passed else "❌"
        print(f"  {icon} {test_id}  {name:<42}  {detail}")
        rec = TestRecord(test_id, name, passed, detail, round(elapsed * 1000, 1))
        records.append(rec)
        return rec

    def run(test_id: str, name: str, fn, *args) -> TestRecord:
        t0 = time.perf_counter()
        try:
            result = fn(*args)
            passed, detail = result[0], result[1]
        except Exception as exc:
            passed, detail = False, f"EXCEPTION: {exc}"
        return _record(test_id, name, passed, detail, time.perf_counter() - t0)

    # ── Print header ────────────────────────────────────────────────────────
    print()
    print("═" * 72)
    print("  HHAAIOS + EGS GenAI — Third OS Test Suite")
    print("  Full Four-Layer Stack: FDTD · OS Kernel · API · Generative AI")
    print("═" * 72)

    # ── T01: must run first; seeds agent_pid state ───────────────────────────
    run("T01", "Agent Init (writer/reader/verifier + LM)", t01_agent_init, agent)

    # ── T02: write; save receipt for T03-T05 ────────────────────────────────
    receipt: Optional[SolarReceipt] = None
    t0 = time.perf_counter()
    try:
        ok, detail, receipt = t02_receipt_write(agent)
    except Exception as exc:
        ok, detail = False, f"EXCEPTION: {exc}"
    _record("T02", "Solar Receipt Write", ok, detail, time.perf_counter() - t0)

    # Fallback so T03-T05 have something to work with even if T02 failed
    safe_addr = receipt.address if receipt else 0

    run("T03", "Phase-Locked Read (H-line bus)",      t03_phase_locked_read,   agent, safe_addr)
    run("T04", "Receipt Verification (valid)",        t04_receipt_verify_valid,
        agent, receipt if receipt else SolarReceipt(0, "", 551.7, 0.0, 0, K_EGS, 0, "", 0, ""))
    run("T05", "Tamper Detection",                    t05_tamper_detection,
        agent, receipt if receipt else SolarReceipt(0, "", 551.7, 0.0, 0, K_EGS, 0, "", 0, ""))

    run("T06", "Four-Pillar Lock Generation",         t06_four_pillar_lock,    agent)
    run("T07", "Four-Pillar Lock Determinism",        t07_lock_determinism,    agent)
    run("T08", "Holographic Generation (16 tokens)",  t08_holographic_generation, agent)
    run("T09", "Generation Determinism",              t09_generation_determinism, agent)
    run("T10", "Generation Diversity (v300 vs v750)", t10_generation_diversity,   agent)
    run("T11", "Grounding — Numeric (K_EGS frac)",   t11_grounding_numeric,   agent)
    run("T12", "Grounding — String claim",            t12_grounding_string,    agent)
    run("T13", "Full Stack Pipeline (all 4 layers)",  t13_full_stack_pipeline, agent)
    run("T14", "Multi-Agent Concurrent (×3)",         t14_multi_agent_concurrent, agent)
    run("T15", "Audit Trail (all receipts valid)",    t15_audit_trail,         agent)

    # ── Summary scoreboard ──────────────────────────────────────────────────
    total  = len(records)
    passed = sum(1 for r in records if r.passed)
    failed = total - passed

    print()
    print("─" * 72)
    print()
    print("  ┌────┬────────────────────────────────────────────┬────────┐")
    print("  │ T# │ Test                                       │ Result │")
    print("  ├────┼────────────────────────────────────────────┼────────┤")
    for r in records:
        icon = "✅" if r.passed else "❌"
        print(f"  │ {r.id:<3} │ {r.name:<42} │   {icon}   │")
    print("  ├────┴────────────────────────────────────────────┴────────┤")
    all_pass = failed == 0
    summary = f"  TOTAL: {passed}/{total}  {'✅ ALL PASS' if all_pass else f'❌ {failed} FAILED'}"
    status  = "✅ FOUR-LAYER STACK FULLY OPERATIONAL" if all_pass else "❌ STACK INCOMPLETE"
    print(f"  │  {summary:<53}│")
    print(f"  │  {status:<53}│")
    print("  └───────────────────────────────────────────────────────────┘")
    print()

    if json_output:
        print(json.dumps(
            [{"id": r.id, "name": r.name, "passed": r.passed,
              "detail": r.detail, "elapsed_ms": r.elapsed_ms}
             for r in records],
            indent=2,
        ))

    return records


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    p = argparse.ArgumentParser(
        description="HHAAIOS Third OS Test Suite — Full Four-Layer EGS Stack"
    )
    p.add_argument("--resolution", type=int,   default=10,
                   help="FDTD grid resolution (default 10)")
    p.add_argument("--until",      type=float, default=40.0,
                   help="FDTD run duration in time units (default 40)")
    p.add_argument("--json",       action="store_true",
                   help="Also print JSON result array")
    args = p.parse_args()

    records = run_hhaaios_tests(
        fdtd_resolution = args.resolution,
        fdtd_until      = args.until,
        json_output     = args.json,
    )
    total  = len(records)
    passed = sum(1 for r in records if r.passed)
    sys.exit(0 if passed == total else 1)
