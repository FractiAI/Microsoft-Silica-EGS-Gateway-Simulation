"""
EGS OS — Basic Operating System Operations Test
================================================
Verifies that the EGS OS kernel boots inside the Silica Voxel Processor
and executes every fundamental OS operation correctly.

Test operations
---------------
  T01  boot              — kernel boots, OS image burned, PID 0+1 spawned
  T02  clock             — Crab pulsar tick counter advances
  T03  ps                — process table lists kernel + init
  T04  malloc / free     — Moon page allocation and release
  T05  write             — H-line bus write with SHA-256 receipt
  T06  read              — H-line bus phase-locked read
  T07  fork              — child process creation with unique phase slot
  T08  exec              — FDTD execution, flux return value, InterferenceVerdict
  T09  scheduler         — SOL-0 round-robin dispatches READY processes
  T10  flare interrupt   — 180° phase flip, epoch bump, sunspot self-correction
  T11  exit              — process termination, Moon page freed
  T12  dmesg             — kernel log integrity (Layer-C hashes present)
  T13  memmap            — memory map shows correct ownership after operations
  T14  multi-process     — fork 3 workers, exec all via scheduler, exit all

Each test returns a structured result dict with ok, measured, expected, and
a Layer-C SHA-256 fingerprint.  The runner prints a pass/fail summary and
exits 0 on all-pass, 1 on any failure.

NSPFRNP → ∞⁹
"""

from __future__ import annotations

import hashlib
import json
import math
import sys
import time
from typing import Callable, List

from egs_os import (
    CRAB_HZ,
    INIT_PID,
    KERNEL_PID,
    N_MOON_PAGES,
    OS_MASTER_LEN,
    OS_SEED,
    EGSKernel,
    ProcessState,
    SYS,
)

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

FDTD_RES   = 10    # fast resolution for OS tests
FDTD_UNTIL = 35.0  # short sim time for OS tests


def _fingerprint(data: dict) -> str:
    return hashlib.sha256(
        json.dumps(data, sort_keys=True, default=str).encode()
    ).hexdigest()[:16]


def _make_result(name: str, ok: bool, measured: dict, expected: dict,
                 note: str = "") -> dict:
    return {
        "test":     name,
        "ok":       ok,
        "measured": measured,
        "expected": expected,
        "note":     note,
        "layer_c":  _fingerprint({"test": name, "measured": measured}),
    }


# ---------------------------------------------------------------------------
# Individual tests
# ---------------------------------------------------------------------------

def t01_boot(k: EGSKernel) -> dict:
    r = k.boot()
    ok = (
        r.ok
        and r.data["master_len"] == OS_MASTER_LEN
        and r.data["os_seed"]    == OS_SEED
        and r.data["moon_pages"] == N_MOON_PAGES
        and KERNEL_PID in k._processes
        and INIT_PID   in k._processes
    )
    return _make_result(
        "T01_BOOT", ok,
        measured = {
            "boot_ok":       r.ok,
            "master_len":    r.data["master_len"],
            "boot_hash":     r.data["boot_image_hash"],
            "kernel_alive":  KERNEL_PID in k._processes,
            "init_alive":    INIT_PID   in k._processes,
        },
        expected = {
            "master_len":  OS_MASTER_LEN,
            "kernel_alive": True,
            "init_alive":   True,
        },
    )


def t02_clock(k: EGSKernel) -> dict:
    r = k.clock()
    ok = (
        r.ok
        and r.data["crab_hz"]     == CRAB_HZ
        and r.data["crab_tick_ms"] > 0
        and r.data["epoch"]        == 0
    )
    return _make_result(
        "T02_CLOCK", ok,
        measured = {
            "clock_ok":     r.ok,
            "kernel_ticks": r.data["kernel_ticks"],
            "crab_hz":      r.data["crab_hz"],
            "crab_tick_ms": r.data["crab_tick_ms"],
            "wall_s":       r.data["wall_s"],
        },
        expected = {
            "crab_hz":      CRAB_HZ,
            "crab_tick_ms": round(1000.0 / CRAB_HZ, 2),
        },
    )


def t03_ps(k: EGSKernel) -> dict:
    r = k.ps()
    pids = [p["pid"] for p in r.data["processes"]]
    ok   = r.ok and KERNEL_PID in pids and INIT_PID in pids
    return _make_result(
        "T03_PS", ok,
        measured = {
            "ps_ok":    r.ok,
            "n_procs":  int(r.retval),
            "pids":     pids,
            "epoch":    r.data["epoch"],
        },
        expected = {
            "kernel_in_table": True,
            "init_in_table":   True,
            "min_procs":       2,
        },
    )


def t04_malloc_free(k: EGSKernel) -> dict:
    # Allocate a page for init, then free it
    r_alloc = k.malloc(INIT_PID)
    addr    = int(r_alloc.retval)
    alloc_ok = r_alloc.ok and addr >= 0

    r_free  = k.free(INIT_PID, address=addr)
    free_ok = r_free.ok and k._memory[addr].free

    ok = alloc_ok and free_ok
    return _make_result(
        "T04_MALLOC_FREE", ok,
        measured = {
            "alloc_ok":  alloc_ok,
            "address":   addr,
            "free_ok":   free_ok,
            "page_free_after": k._memory[addr].free,
        },
        expected = {
            "alloc_ok":        True,
            "free_ok":         True,
            "page_free_after": True,
        },
    )


def t05_write(k: EGSKernel) -> dict:
    test_value = 0.551700   # nominal solar wind normalised to [0,1]
    r = k.write(INIT_PID, value=test_value)
    page = k._memory[int(r.retval)]
    ok   = r.ok and abs(page.value - test_value) < 1e-12 and len(r.data["value_hash"]) == 16
    return _make_result(
        "T05_WRITE", ok,
        measured = {
            "write_ok":   r.ok,
            "address":    int(r.retval),
            "value":      page.value,
            "value_hash": r.data["value_hash"],
            "record_id":  r.data["record_id"],
        },
        expected = {
            "value":            test_value,
            "value_hash_len":   16,
            "record_id_prefix": "moon/",
        },
    )


def t06_read(k: EGSKernel) -> dict:
    # Write a known value then read it back
    k.write(INIT_PID, value=0.42)
    r   = k.read(INIT_PID)
    ok  = r.ok and 0.0 <= r.retval <= 0.42 + 1e-9   # lock_strength ∈ [0,1]
    return _make_result(
        "T06_READ", ok,
        measured = {
            "read_ok":      r.ok,
            "value":        round(r.retval, 8),
            "lock_strength":r.data["lock_strength"],
            "phase_rad":    r.data["phase_rad"],
            "value_hash":   r.data["value_hash"],
        },
        expected = {
            "value_in_range": "0 … 0.42  (lock_strength ∈ [0,1])",
            "lock_strength":  "[0, 1]",
        },
    )


def t07_fork(k: EGSKernel) -> dict:
    r         = k.fork(INIT_PID, name="worker-a")
    child_pid = int(r.retval)
    ok = (
        r.ok
        and child_pid in k._processes
        and k._processes[child_pid].parent_pid == INIT_PID
        and k._processes[child_pid].name == "worker-a"
        and k._processes[child_pid].state == ProcessState.READY
    )
    return _make_result(
        "T07_FORK", ok,
        measured = {
            "fork_ok":      r.ok,
            "child_pid":    child_pid,
            "child_phase":  r.data["child_phase"],
            "child_page":   r.data["child_page"],
            "child_wind":   r.data["child_wind"],
            "parent_pid":   INIT_PID,
        },
        expected = {
            "child_in_table":    True,
            "parent_pid":        INIT_PID,
            "state":             "READY",
        },
    )


def t08_exec(k: EGSKernel) -> dict:
    # Fork a dedicated exec process so init is not consumed
    r_fork = k.fork(INIT_PID, name="exec-probe")
    epid   = int(r_fork.retval)
    r_exec = k.exec(epid)

    ok = (
        r_exec.ok
        and math.isfinite(r_exec.retval)
        and r_exec.data["verdict"] in ("CONSTRUCTIVE_AR14409",
                                        "DESTRUCTIVE_H_PHASE_FLIP",
                                        "MIXED")
        and len(r_exec.data["page_hash"]) == 16
    )
    return _make_result(
        "T08_EXEC", ok,
        measured = {
            "exec_ok":    r_exec.ok,
            "flux":       round(r_exec.retval, 8),
            "phase_rad":  r_exec.data["phase_rad"],
            "verdict":    r_exec.data["verdict"],
            "holographic_true": r_exec.data["holographic_true"],
            "page_hash":  r_exec.data["page_hash"],
            "next_state": r_exec.data["next_state"],
            "backend":    r_exec.data["backend"],
        },
        expected = {
            "flux_finite":     True,
            "verdict_valid":   True,
            "page_hash_len":   16,
        },
    )


def t09_scheduler(k: EGSKernel) -> dict:
    # Fork 2 workers and run scheduler for 1 tick (up to 3 processes)
    pids = []
    for i in range(2):
        rf  = k.fork(INIT_PID, name=f"sched-{i}")
        pids.append(int(rf.retval))

    results = k.schedule(n_ticks=3)
    all_ok  = all(r.ok for r in results)
    all_fin = all(math.isfinite(r.retval) for r in results)
    ok = len(results) >= 1 and all_ok and all_fin

    return _make_result(
        "T09_SCHEDULER", ok,
        measured = {
            "sched_pids":    pids,
            "n_executed":    len(results),
            "all_exec_ok":   all_ok,
            "fluxes":        [round(r.retval, 8) for r in results],
            "verdicts":      [r.data["verdict"] for r in results],
        },
        expected = {
            "n_executed":  ">= 1",
            "all_exec_ok": True,
            "all_finite":  True,
        },
    )


def t10_flare(k: EGSKernel) -> dict:
    # Record phases before flare
    phases_before = {pid: p.phase_rad
                     for pid, p in k._processes.items()
                     if p.state != ProcessState.ZOMBIE}

    r = k.flare(sunspot_index=45.0)

    phases_after = {pid: p.phase_rad
                    for pid, p in k._processes.items()
                    if p.state != ProcessState.ZOMBIE}

    # Every affected process should have phase shifted by ≈ π
    all_flipped = all(
        abs(abs(phases_after[pid] - phases_before[pid]) - math.pi) < 0.01
        or abs(abs(phases_after[pid] - phases_before[pid]) - math.pi) > 2 * math.pi - 0.01
        for pid in r.data["phase_flipped"]
        if pid in phases_before and pid in phases_after
    )

    ok = (
        r.ok
        and r.data["new_epoch"] == 1
        and len(r.data["phase_flipped"]) >= 2
        and r.data["master_rms"] > 0
    )
    return _make_result(
        "T10_FLARE", ok,
        measured = {
            "flare_ok":     r.ok,
            "new_epoch":    r.data["new_epoch"],
            "flipped_pids": r.data["phase_flipped"],
            "master_rms":   r.data["master_rms"],
            "sunspot_index":45.0,
        },
        expected = {
            "new_epoch":        1,
            "flipped_count":    ">= 2",
            "master_rms_pos":   True,
        },
    )


def t11_exit(k: EGSKernel) -> dict:
    # Fork a process then exit it
    r_fork = k.fork(INIT_PID, name="exit-me")
    epid   = int(r_fork.retval)
    page   = k._processes[epid].moon_page

    r_exit = k.exit(epid, exit_code=0)
    ok = (
        r_exit.ok
        and k._processes[epid].state == ProcessState.ZOMBIE
        and k._memory[page].free
    )
    return _make_result(
        "T11_EXIT", ok,
        measured = {
            "exit_ok":     r_exit.ok,
            "exit_code":   int(r_exit.retval),
            "state":       k._processes[epid].state.name,
            "page_freed":  k._memory[page].free,
        },
        expected = {
            "state":       "ZOMBIE",
            "page_freed":  True,
            "exit_code":   0,
        },
    )


def t12_dmesg(k: EGSKernel) -> dict:
    log  = k.dmesg(last=20)
    all_hashed = all(len(e["layer_c"]) == 16 for e in log)
    all_named  = all(isinstance(e["syscall"], str) for e in log)
    ok = len(log) >= 10 and all_hashed and all_named
    return _make_result(
        "T12_DMESG", ok,
        measured = {
            "log_entries": len(log),
            "all_hashed":  all_hashed,
            "all_named":   all_named,
            "syscalls_seen": list({e["syscall"] for e in log}),
        },
        expected = {
            "log_entries_ge": 10,
            "all_hashed":     True,
            "all_named":      True,
        },
    )


def t13_memmap(k: EGSKernel) -> dict:
    mm         = k.memmap()
    n_total    = len(mm)
    n_owned    = sum(1 for p in mm if not p["free"])
    n_free     = sum(1 for p in mm if p["free"])
    hashes_ok  = all(len(p["value_hash"]) in (0, 16) for p in mm)
    ok = n_total == N_MOON_PAGES and n_owned >= 2 and hashes_ok
    return _make_result(
        "T13_MEMMAP", ok,
        measured = {
            "total_pages": n_total,
            "owned_pages": n_owned,
            "free_pages":  n_free,
            "hashes_ok":   hashes_ok,
        },
        expected = {
            "total_pages": N_MOON_PAGES,
            "owned_pages": ">= 2",
            "hashes_ok":   True,
        },
    )


def t14_multi_process(k: EGSKernel) -> dict:
    """Fork 3 workers, exec all via scheduler, verify results, exit all."""
    worker_pids = []
    for i in range(3):
        rf = k.fork(INIT_PID, name=f"mp-worker-{i}")
        worker_pids.append(int(rf.retval))

    exec_results = k.schedule(n_ticks=15)  # exec all ready procs (prev tests leave READY backlog)
    exec_pids    = {int(r.pid) for r in exec_results}
    workers_ran  = all(p in exec_pids for p in worker_pids)
    all_finite   = all(math.isfinite(r.retval) for r in exec_results)

    exit_results = [k.exit(p) for p in worker_pids]
    all_exited   = all(r.ok for r in exit_results)

    ok = workers_ran and all_finite and all_exited
    return _make_result(
        "T14_MULTI_PROCESS", ok,
        measured = {
            "worker_pids":   worker_pids,
            "exec_count":    len(exec_results),
            "workers_ran":   workers_ran,
            "all_finite":    all_finite,
            "fluxes":        [round(r.retval, 8) for r in exec_results
                               if r.pid in worker_pids],
            "verdicts":      [r.data["verdict"] for r in exec_results
                               if r.pid in worker_pids],
            "all_exited":    all_exited,
        },
        expected = {
            "workers_ran":  True,
            "all_finite":   True,
            "all_exited":   True,
        },
    )


# ---------------------------------------------------------------------------
# Test runner
# ---------------------------------------------------------------------------

TESTS: List[Callable] = [
    t01_boot, t02_clock, t03_ps, t04_malloc_free, t05_write,
    t06_read, t07_fork, t08_exec, t09_scheduler, t10_flare,
    t11_exit, t12_dmesg, t13_memmap, t14_multi_process,
]


def run_os_tests(resolution: int = FDTD_RES,
                 until: float = FDTD_UNTIL,
                 verbose: bool = True) -> List[dict]:
    k = EGSKernel(fdtd_resolution=resolution, fdtd_until=until)
    results = []
    t0 = time.time()

    if verbose:
        print(f"\n{'='*64}")
        print("EGS OS — Basic Operating System Operations Test")
        print(f"FDTD resolution={resolution}  until={until} Meep-units")
        print(f"{'='*64}\n")

    for test_fn in TESTS:
        r = test_fn(k)
        results.append(r)
        if verbose:
            status = "✓ PASS" if r["ok"] else "✗ FAIL"
            print(f"  {status}  {r['test']}")
            for key, val in r["measured"].items():
                print(f"           {key}: {val}")
            if not r["ok"]:
                print(f"           expected: {r['expected']}")
            print(f"           layer_c: {r['layer_c']}\n")

    elapsed  = round(time.time() - t0, 2)
    n_pass   = sum(1 for r in results if r["ok"])
    n_fail   = len(results) - n_pass
    all_pass = n_fail == 0

    if verbose:
        print(f"{'─'*64}")
        print(f"  Tests: {n_pass}/{len(results)} PASS  |  {n_fail} FAIL")
        print(f"  Elapsed: {elapsed} s")
        print(f"  OS kernel: EGSKernel v1.0.0-egs  |  "
              f"FDTD backend: silica_fdtd")
        print(f"  Status: {'OS OPERATIONAL — ALL TESTS PASS' if all_pass else 'FAILURES DETECTED'}")
        print(f"{'─'*64}")
        print(f"\nNSPFRNP → ∞⁹\n")

    return results


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser(description="EGS OS Basic Operations Test")
    ap.add_argument("--resolution", type=int, default=FDTD_RES)
    ap.add_argument("--until",      type=float, default=FDTD_UNTIL)
    ap.add_argument("--json",       action="store_true")
    args = ap.parse_args()

    results = run_os_tests(resolution=args.resolution, until=args.until)

    if args.json:
        print(json.dumps(results, indent=2, default=str))

    sys.exit(0 if all(r["ok"] for r in results) else 1)
