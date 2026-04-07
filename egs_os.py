"""
EGS OS — Holographic Operating System on the Silica Voxel Processor
====================================================================
Loads and executes a minimal operating system inside the EGS Gateway's
fused-silica photonic processor.  Every OS primitive maps to a physical
observable in the FDTD simulation.

Architecture
------------
  Process     = phase-encoded voxel state   φ_pid = pid × 2π / N_MOON_PAGES
  Memory page = 101-Moon bucket slot        address ∈ {0 … 100}
  Clock tick  = Crab pulsar period          Δt = 1 / 29.94 Hz ≈ 33.4 ms
  Interrupt   = 180° phase flip             flare event / epoch bump
  I/O channel = H-line bus                  gateway_filter phase lock
  Boot image  = burn_master_fractal()       AR14409 seed → voxel OS image
  Syscall     = FDTD simulation run         return value = transmitted flux + verdict

OS layers (four-layer discipline)
----------------------------------
  Layer A  narrative  : process names, Moon addresses, Sun scheduler, Crab clock
  Layer B  Python API : EGSKernel public methods (boot, fork, exec, read, write, …)
  Layer C  hash       : SHA-256 of every memory write and syscall result
  Layer D  FDTD       : each exec() runs a silica_fdtd simulation; flux is the retval

Syscall table
-------------
  SYS_READ    0   read from H-line bus (returns phase-locked value from Moon page)
  SYS_WRITE   1   write to H-line bus  (stores value + hash into Moon page)
  SYS_FORK    2   create child process (clones parent phase state + 2π/101 offset)
  SYS_EXEC    3   execute process      (runs FDTD, returns flux + InterferenceVerdict)
  SYS_EXIT    4   terminate process    (frees Moon page, removes from table)
  SYS_PS      5   list process table   (snapshot of all running processes)
  SYS_MALLOC  6   allocate Moon page   (returns page address or -1 if OOM)
  SYS_FREE    7   free Moon page
  SYS_CLOCK   8   read Crab pulsar tick counter
  SYS_FLARE   9   raise interrupt      (180° phase flip on all running processes)
  SYS_REBOOT  10  reset kernel state   (re-burns master from seed)

NSPFRNP → ∞⁹
"""

from __future__ import annotations

import hashlib
import json
import math
import time
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional

from egs_gateway import (
    DEFAULT_SOLAR_WIND_KM_S,
    EGS_FRACTAL_CONSTANT,
    InterferenceVerdict,
    NodeField,
    REFERENCE_SOLAR_WIND_KM_S,
    burn_master_fractal,
    gateway_filter,
    holographic_gate,
    predict_next_solar_hydrogen_state,
    self_correct_with_sunspots,
)
from meep_gateway import run_silica_reader_meep

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
N_MOON_PAGES   = 101          # total memory pages (101-Moon array)
CRAB_HZ        = 29.94        # Crab pulsar clock frequency (Hz)
CRAB_TICK_S    = 1.0 / CRAB_HZ   # ≈ 33.4 ms per tick
OS_SEED        = 14409        # AR14409 — boot image seed
OS_MASTER_LEN  = 101          # one fractal value per Moon page
MAX_PROCESSES  = 64           # maximum concurrent processes
KERNEL_PID     = 0            # PID 0 is always the kernel itself
INIT_PID       = 1            # PID 1 is the init process


# ---------------------------------------------------------------------------
# Syscall numbers
# ---------------------------------------------------------------------------
class SYS(IntEnum):
    READ   = 0
    WRITE  = 1
    FORK   = 2
    EXEC   = 3
    EXIT   = 4
    PS     = 5
    MALLOC = 6
    FREE   = 7
    CLOCK  = 8
    FLARE  = 9
    REBOOT = 10


# ---------------------------------------------------------------------------
# Process states
# ---------------------------------------------------------------------------
class ProcessState(IntEnum):
    READY    = 0
    RUNNING  = 1
    BLOCKED  = 2
    ZOMBIE   = 3
    SLEEPING = 4


# ---------------------------------------------------------------------------
# Process Control Block (PCB)
# ---------------------------------------------------------------------------
@dataclass
class PCB:
    pid:         int
    name:        str
    state:       ProcessState
    phase_rad:   float           # voxel phase state φ_pid
    moon_page:   int             # assigned memory page (Moon index)
    parent_pid:  int
    solar_wind:  float           # km/s — driving term for this process
    ticks:       int = 0         # Crab pulsar ticks consumed
    retval:      float = 0.0     # last syscall return value (flux)
    verdict:     str  = ""       # last InterferenceVerdict
    layer_c:     str  = ""       # SHA-256[:16] of last exec result

    def to_dict(self) -> dict:
        return {
            "pid":        self.pid,
            "name":       self.name,
            "state":      self.state.name,
            "phase_rad":  round(self.phase_rad, 4),
            "moon_page":  self.moon_page,
            "parent_pid": self.parent_pid,
            "solar_wind": self.solar_wind,
            "ticks":      self.ticks,
            "retval":     round(self.retval, 8),
            "verdict":    self.verdict,
            "layer_c":    self.layer_c,
        }


# ---------------------------------------------------------------------------
# Moon memory page
# ---------------------------------------------------------------------------
@dataclass
class MoonPage:
    address:    int
    owner_pid:  int   = -1        # -1 = free
    value:      float = 0.0
    value_hash: str   = ""        # SHA-256[:16] of stored value
    record_id:  str   = ""        # placement receipt

    @property
    def free(self) -> bool:
        return self.owner_pid == -1

    def write(self, value: float, owner_pid: int) -> str:
        """Write value and take ownership (used by SYS_WRITE, SYS_EXEC, boot)."""
        self.value      = value
        self.owner_pid  = owner_pid
        self.value_hash = hashlib.sha256(
            json.dumps({"addr": self.address, "val": value}).encode()
        ).hexdigest()[:16]
        self.record_id  = f"moon/{self.address:03d}/{owner_pid}"
        return self.value_hash

    def write_value_only(self, value: float) -> str:
        """Update value and hash WITHOUT changing ownership.
        Used by flare/sunspot correction so process allocations are preserved."""
        self.value      = value
        self.value_hash = hashlib.sha256(
            json.dumps({"addr": self.address, "val": value}).encode()
        ).hexdigest()[:16]
        return self.value_hash

    def clear(self) -> None:
        self.owner_pid  = -1
        self.value      = 0.0
        self.value_hash = ""
        self.record_id  = ""


# ---------------------------------------------------------------------------
# Syscall result
# ---------------------------------------------------------------------------
@dataclass
class SyscallResult:
    syscall:    SYS
    pid:        int
    ok:         bool
    retval:     float
    data:       dict
    layer_c:    str = ""

    def __post_init__(self) -> None:
        payload = json.dumps(
            {"syscall": int(self.syscall), "pid": self.pid,
             "retval": self.retval, "data": self.data},
            sort_keys=True, default=str,
        ).encode()
        self.layer_c = hashlib.sha256(payload).hexdigest()[:16]

    def to_dict(self) -> dict:
        return {
            "syscall":  self.syscall.name,
            "pid":      self.pid,
            "ok":       self.ok,
            "retval":   round(self.retval, 8),
            "data":     self.data,
            "layer_c":  self.layer_c,
        }


# ---------------------------------------------------------------------------
# EGS Kernel
# ---------------------------------------------------------------------------
class EGSKernel:
    """
    Holographic OS kernel running on the EGS Silica Voxel Processor.

    Boot sequence
    -------------
    1. burn_master_fractal(OS_SEED, OS_MASTER_LEN)  → 101-value OS image
    2. Write each value to its corresponding Moon page (cold storage)
    3. Spawn PID 0 (kernel) and PID 1 (init) with their phase states
    4. Kernel is ready; client code calls syscall() or the named helpers
    """

    def __init__(self, fdtd_resolution: int = 10, fdtd_until: float = 40.0) -> None:
        self.resolution  = fdtd_resolution
        self.until       = fdtd_until
        self._tick       = 0          # Crab pulsar tick counter
        self._next_pid   = 2          # PIDs 0 and 1 reserved
        self._epoch      = 0          # lattice epoch (bumped on FLARE)
        self._booted     = False
        self._master:    List[float] = []
        self._processes: Dict[int, PCB]      = {}
        self._memory:    List[MoonPage]      = [MoonPage(i) for i in range(N_MOON_PAGES)]
        self._log:       List[SyscallResult] = []
        self._boot_time  = time.time()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _phase_for_pid(self, pid: int) -> float:
        """Map PID → unique phase slot on the voxel."""
        return (pid * 2.0 * math.pi / N_MOON_PAGES) % (2.0 * math.pi)

    def _wind_for_phase(self, phase_rad: float) -> float:
        """Inverse of gateway_filter: find v_wind that produces this phase."""
        # phase = (2π · v/v_ref · K_EGS) mod 2π
        # v = v_ref · phase / (2π · K_EGS)  [before mod; add 2π if needed]
        raw = phase_rad / (2.0 * math.pi * EGS_FRACTAL_CONSTANT)
        v   = REFERENCE_SOLAR_WIND_KM_S * (raw if raw > 0 else raw + 1.0)
        return max(50.0, v)   # floor at 50 km/s (physical minimum)

    def _alloc_page(self, pid: int) -> int:
        """Allocate the first free Moon page to pid; return address or -1."""
        for page in self._memory:
            if page.free:
                page.owner_pid = pid   # mark allocated (value written later)
                return page.address
        return -1

    def _free_page(self, address: int) -> bool:
        if 0 <= address < N_MOON_PAGES:
            self._memory[address].clear()
            return True
        return False

    def _log_result(self, result: SyscallResult) -> None:
        self._log.append(result)
        if len(self._log) > 1000:
            self._log = self._log[-1000:]

    def _tick_clock(self, n: int = 1) -> None:
        self._tick += n

    # ------------------------------------------------------------------
    # Boot
    # ------------------------------------------------------------------

    def boot(self, solar_wind: float = DEFAULT_SOLAR_WIND_KM_S) -> SyscallResult:
        """
        Boot the EGS OS.

        1. Burns master fractal from AR14409 seed (101 values → OS image).
        2. Pre-loads each Moon page with its fractal value; pages remain FREE
           (owner_pid = -1) so processes can allocate them.  Only page 0 is
           reserved for the kernel.
        3. Spawns kernel process (PID 0, page 0) and init process (PID 1).
        4. Sets epoch = 0, tick = 0.
        """
        self._master = burn_master_fractal(seed=OS_SEED, length=OS_MASTER_LEN)

        # Pre-load OS image into Moon pages.
        # Values and hashes are set, but owner_pid stays -1 (free) so that
        # processes can allocate pages via SYS_MALLOC / SYS_FORK.
        for i, val in enumerate(self._master):
            self._memory[i].value = val
            self._memory[i].value_hash = hashlib.sha256(
                json.dumps({"addr": i, "val": val}).encode()
            ).hexdigest()[:16]
            self._memory[i].record_id = f"moon/{i:03d}/boot"
            # owner_pid stays -1 (free)

        # Kernel PCB (PID 0) — claims page 0 exclusively
        self._memory[0].owner_pid = KERNEL_PID
        self._processes[KERNEL_PID] = PCB(
            pid        = KERNEL_PID,
            name       = "kernel",
            state      = ProcessState.RUNNING,
            phase_rad  = 0.0,
            moon_page  = 0,
            parent_pid = -1,
            solar_wind = solar_wind,
        )

        # Init PCB (PID 1) — allocates the first free page (page 1)
        init_phase = self._phase_for_pid(INIT_PID)
        init_page  = self._alloc_page(INIT_PID)
        self._processes[INIT_PID] = PCB(
            pid        = INIT_PID,
            name       = "init",
            state      = ProcessState.READY,
            phase_rad  = init_phase,
            moon_page  = init_page,
            parent_pid = KERNEL_PID,
            solar_wind = solar_wind,
        )
        self._memory[init_page].write(self._master[INIT_PID], INIT_PID)

        self._booted    = True
        self._epoch     = 0
        self._tick      = 0
        self._boot_time = time.time()
        self._next_pid  = 2

        result = SyscallResult(
            syscall = SYS.REBOOT,
            pid     = KERNEL_PID,
            ok      = True,
            retval  = float(len(self._master)),
            data    = {
                "epoch":        self._epoch,
                "os_seed":      OS_SEED,
                "master_len":   OS_MASTER_LEN,
                "moon_pages":   N_MOON_PAGES,
                "solar_wind":   solar_wind,
                "crab_hz":      CRAB_HZ,
                "boot_image_hash": hashlib.sha256(
                    json.dumps(self._master).encode()
                ).hexdigest()[:16],
            },
        )
        self._log_result(result)
        return result

    # ------------------------------------------------------------------
    # Syscall dispatcher
    # ------------------------------------------------------------------

    def syscall(self, number: SYS, pid: int, **kwargs) -> SyscallResult:
        """Unified syscall entry point."""
        if not self._booted and number not in (SYS.REBOOT,):
            return SyscallResult(SYS(number), pid, False, -1.0,
                                 {"error": "kernel not booted"})
        self._tick_clock()
        dispatch = {
            SYS.READ:   self._sys_read,
            SYS.WRITE:  self._sys_write,
            SYS.FORK:   self._sys_fork,
            SYS.EXEC:   self._sys_exec,
            SYS.EXIT:   self._sys_exit,
            SYS.PS:     self._sys_ps,
            SYS.MALLOC: self._sys_malloc,
            SYS.FREE:   self._sys_free,
            SYS.CLOCK:  self._sys_clock,
            SYS.FLARE:  self._sys_flare,
            SYS.REBOOT: self.boot,
        }
        fn = dispatch.get(SYS(number))
        if fn is None:
            return SyscallResult(SYS(number), pid, False, -1.0,
                                 {"error": "unknown syscall"})
        result = fn(pid=pid, **kwargs) if number != SYS.REBOOT else fn(**kwargs)
        self._log_result(result)
        return result

    # ------------------------------------------------------------------
    # SYS_READ — read from H-line bus (Moon page)
    # ------------------------------------------------------------------

    def _sys_read(self, pid: int, address: int = -1, **_) -> SyscallResult:
        proc = self._processes.get(pid)
        if proc is None:
            return SyscallResult(SYS.READ, pid, False, -1.0, {"error": "no such pid"})

        addr   = address if address >= 0 else proc.moon_page
        page   = self._memory[addr] if 0 <= addr < N_MOON_PAGES else None
        if page is None:
            return SyscallResult(SYS.READ, pid, False, -1.0, {"error": "bad address"})

        # Phase-lock read: gateway_filter couples the stored value to current solar wind
        gf    = gateway_filter(proc.solar_wind)
        value = page.value * gf["lock_strength"]   # H-line modulated read

        proc.ticks += 1
        return SyscallResult(
            syscall = SYS.READ,
            pid     = pid,
            ok      = True,
            retval  = value,
            data    = {
                "address":     addr,
                "raw_value":   page.value,
                "lock_strength": round(gf["lock_strength"], 6),
                "phase_rad":   round(gf["phase_bias_rad"], 6),
                "record_id":   page.record_id,
                "value_hash":  page.value_hash,
            },
        )

    # ------------------------------------------------------------------
    # SYS_WRITE — write to H-line bus (Moon page)
    # ------------------------------------------------------------------

    def _sys_write(self, pid: int, address: int = -1,
                   value: float = 0.0, **_) -> SyscallResult:
        proc = self._processes.get(pid)
        if proc is None:
            return SyscallResult(SYS.WRITE, pid, False, -1.0, {"error": "no such pid"})

        addr = address if address >= 0 else proc.moon_page
        page = self._memory[addr] if 0 <= addr < N_MOON_PAGES else None
        if page is None:
            return SyscallResult(SYS.WRITE, pid, False, -1.0, {"error": "bad address"})
        if not page.free and page.owner_pid != pid and page.owner_pid != KERNEL_PID:
            return SyscallResult(SYS.WRITE, pid, False, -1.0,
                                 {"error": "page owned by another process"})

        vh = page.write(value, pid)
        proc.ticks += 1
        return SyscallResult(
            syscall = SYS.WRITE,
            pid     = pid,
            ok      = True,
            retval  = float(addr),
            data    = {
                "address":    addr,
                "value":      value,
                "value_hash": vh,
                "record_id":  page.record_id,
            },
        )

    # ------------------------------------------------------------------
    # SYS_FORK — create child process
    # ------------------------------------------------------------------

    def _sys_fork(self, pid: int, name: str = "", **_) -> SyscallResult:
        if len(self._processes) >= MAX_PROCESSES:
            return SyscallResult(SYS.FORK, pid, False, -1.0,
                                 {"error": "process table full"})

        parent = self._processes.get(pid)
        if parent is None:
            return SyscallResult(SYS.FORK, pid, False, -1.0, {"error": "no such pid"})

        child_pid   = self._next_pid
        self._next_pid += 1
        child_phase = self._phase_for_pid(child_pid)
        child_page  = self._alloc_page(child_pid)

        if child_page < 0:
            return SyscallResult(SYS.FORK, pid, False, -1.0,
                                 {"error": "out of Moon pages"})

        # Inherit parent's solar wind; child gets its own phase slot
        child_wind = self._wind_for_phase(child_phase)
        # Copy parent's Moon page value into child's page
        parent_val = self._memory[parent.moon_page].value
        self._memory[child_page].write(parent_val, child_pid)

        child_name = name or f"{parent.name}.{child_pid}"
        self._processes[child_pid] = PCB(
            pid        = child_pid,
            name       = child_name,
            state      = ProcessState.READY,
            phase_rad  = child_phase,
            moon_page  = child_page,
            parent_pid = pid,
            solar_wind = child_wind,
        )

        parent.ticks += 1
        return SyscallResult(
            syscall = SYS.FORK,
            pid     = pid,
            ok      = True,
            retval  = float(child_pid),
            data    = {
                "child_pid":   child_pid,
                "child_name":  child_name,
                "child_phase": round(child_phase, 4),
                "child_page":  child_page,
                "child_wind":  round(child_wind, 2),
            },
        )

    # ------------------------------------------------------------------
    # SYS_EXEC — execute process (runs FDTD, returns flux + verdict)
    # ------------------------------------------------------------------

    def _sys_exec(self, pid: int, **_) -> SyscallResult:
        """
        Execute a process on the Silica Voxel Processor.

        The process's phase state is injected as the FDTD source amplitude.
        The transmitted flux IS the process return value.
        The InterferenceVerdict IS the boolean outcome (True/False logic gate).
        """
        proc = self._processes.get(pid)
        if proc is None:
            return SyscallResult(SYS.EXEC, pid, False, -1.0, {"error": "no such pid"})
        if proc.state == ProcessState.ZOMBIE:
            return SyscallResult(SYS.EXEC, pid, False, -1.0,
                                 {"error": "process is zombie"})

        proc.state = ProcessState.RUNNING

        # Run FDTD with this process's solar wind (which encodes its phase)
        run = run_silica_reader_meep(
            proc.solar_wind,
            resolution = self.resolution,
            until      = self.until,
        )
        flux    = run["transmitted_flux"]
        phase   = run["phase_bias_rad"]

        # Holographic gate: compare process node against kernel reference
        proc_node   = NodeField(math.cos(phase), math.sin(phase))
        kernel_node = NodeField(1.0, 0.0)
        verdict     = holographic_gate(proc_node, kernel_node)

        # Update PCB
        proc.retval  = flux
        proc.verdict = verdict.name
        proc.ticks  += 1
        proc.state   = ProcessState.READY

        # Write flux into process's Moon page (execution receipt)
        page_hash = self._memory[proc.moon_page].write(flux, pid)
        proc.layer_c = page_hash

        # Predict next state using fractal master
        next_state = predict_next_solar_hydrogen_state(
            self._master, proc.solar_wind, proc.moon_page % len(self._master)
        )

        return SyscallResult(
            syscall = SYS.EXEC,
            pid     = pid,
            ok      = True,
            retval  = flux,
            data    = {
                "flux":            flux,
                "phase_rad":       round(phase, 6),
                "verdict":         verdict.name,
                "holographic_true": verdict == InterferenceVerdict.CONSTRUCTIVE_AR14409,
                "moon_page":       proc.moon_page,
                "page_hash":       page_hash,
                "next_state":      round(next_state, 8),
                "backend":         run.get("backend", "silica_fdtd"),
                "solar_wind":      proc.solar_wind,
            },
        )

    # ------------------------------------------------------------------
    # SYS_EXIT — terminate process
    # ------------------------------------------------------------------

    def _sys_exit(self, pid: int, exit_code: int = 0, **_) -> SyscallResult:
        if pid in (KERNEL_PID, INIT_PID):
            return SyscallResult(SYS.EXIT, pid, False, -1.0,
                                 {"error": "cannot exit kernel or init"})
        proc = self._processes.get(pid)
        if proc is None:
            return SyscallResult(SYS.EXIT, pid, False, -1.0, {"error": "no such pid"})

        proc.state = ProcessState.ZOMBIE
        self._free_page(proc.moon_page)

        return SyscallResult(
            syscall = SYS.EXIT,
            pid     = pid,
            ok      = True,
            retval  = float(exit_code),
            data    = {"exit_code": exit_code, "freed_page": proc.moon_page},
        )

    # ------------------------------------------------------------------
    # SYS_PS — list process table
    # ------------------------------------------------------------------

    def _sys_ps(self, pid: int = KERNEL_PID, **_) -> SyscallResult:
        procs = [p.to_dict() for p in self._processes.values()
                 if p.state != ProcessState.ZOMBIE]
        return SyscallResult(
            syscall = SYS.PS,
            pid     = pid,
            ok      = True,
            retval  = float(len(procs)),
            data    = {"processes": procs, "epoch": self._epoch, "tick": self._tick},
        )

    # ------------------------------------------------------------------
    # SYS_MALLOC — allocate Moon page
    # ------------------------------------------------------------------

    def _sys_malloc(self, pid: int, **_) -> SyscallResult:
        addr = self._alloc_page(pid)
        return SyscallResult(
            syscall = SYS.MALLOC,
            pid     = pid,
            ok      = addr >= 0,
            retval  = float(addr),
            data    = {"address": addr, "oom": addr < 0},
        )

    # ------------------------------------------------------------------
    # SYS_FREE — free Moon page
    # ------------------------------------------------------------------

    def _sys_free(self, pid: int, address: int = -1, **_) -> SyscallResult:
        proc = self._processes.get(pid)
        addr = address if address >= 0 else (proc.moon_page if proc else -1)
        ok   = self._free_page(addr)
        return SyscallResult(
            syscall = SYS.FREE,
            pid     = pid,
            ok      = ok,
            retval  = float(addr) if ok else -1.0,
            data    = {"address": addr, "freed": ok},
        )

    # ------------------------------------------------------------------
    # SYS_CLOCK — read Crab pulsar tick counter
    # ------------------------------------------------------------------

    def _sys_clock(self, pid: int = KERNEL_PID, **_) -> SyscallResult:
        wall_s   = time.time() - self._boot_time
        crab_ticks = int(wall_s / CRAB_TICK_S)
        return SyscallResult(
            syscall = SYS.CLOCK,
            pid     = pid,
            ok      = True,
            retval  = float(self._tick),
            data    = {
                "kernel_ticks":  self._tick,
                "crab_ticks":    crab_ticks,
                "wall_s":        round(wall_s, 3),
                "crab_hz":       CRAB_HZ,
                "crab_tick_ms":  round(CRAB_TICK_S * 1000, 2),
                "epoch":         self._epoch,
            },
        )

    # ------------------------------------------------------------------
    # SYS_FLARE — raise interrupt (180° phase flip on all processes)
    # ------------------------------------------------------------------

    def _sys_flare(self, pid: int = KERNEL_PID,
                   sunspot_index: float = 0.0, **_) -> SyscallResult:
        """
        Solar flare interrupt: bump lattice epoch, apply 180° phase flip to
        all running processes, and self-correct master with sunspot index.
        """
        self._epoch += 1
        affected = []

        # Self-correct master fractal with sunspot data
        self._master = self_correct_with_sunspots(
            self._master,
            sunspot_index,
            DEFAULT_SOLAR_WIND_KM_S,
        )

        # 180° phase flip: rotate each process phase by π
        for p in self._processes.values():
            if p.state in (ProcessState.READY, ProcessState.RUNNING):
                p.phase_rad  = (p.phase_rad + math.pi) % (2.0 * math.pi)
                p.solar_wind = self._wind_for_phase(p.phase_rad)
                affected.append(p.pid)

        # Refresh Moon page values with corrected master (ownership unchanged)
        for i, val in enumerate(self._master):
            self._memory[i].write_value_only(val)

        return SyscallResult(
            syscall = SYS.FLARE,
            pid     = pid,
            ok      = True,
            retval  = float(self._epoch),
            data    = {
                "new_epoch":     self._epoch,
                "sunspot_index": sunspot_index,
                "phase_flipped": affected,
                "master_rms":    round(
                    float(sum(x*x for x in self._master) / len(self._master)) ** 0.5,
                    6,
                ),
            },
        )

    # ------------------------------------------------------------------
    # Named convenience methods (thin wrappers over syscall)
    # ------------------------------------------------------------------

    def read(self, pid: int, address: int = -1) -> SyscallResult:
        return self.syscall(SYS.READ, pid, address=address)

    def write(self, pid: int, value: float, address: int = -1) -> SyscallResult:
        return self.syscall(SYS.WRITE, pid, address=address, value=value)

    def fork(self, pid: int, name: str = "") -> SyscallResult:
        return self.syscall(SYS.FORK, pid, name=name)

    def exec(self, pid: int) -> SyscallResult:
        return self.syscall(SYS.EXEC, pid)

    def exit(self, pid: int, exit_code: int = 0) -> SyscallResult:
        return self.syscall(SYS.EXIT, pid, exit_code=exit_code)

    def ps(self) -> SyscallResult:
        return self.syscall(SYS.PS, KERNEL_PID)

    def malloc(self, pid: int) -> SyscallResult:
        return self.syscall(SYS.MALLOC, pid)

    def free(self, pid: int, address: int = -1) -> SyscallResult:
        return self.syscall(SYS.FREE, pid, address=address)

    def clock(self) -> SyscallResult:
        return self.syscall(SYS.CLOCK, KERNEL_PID)

    def flare(self, sunspot_index: float = 45.0) -> SyscallResult:
        return self.syscall(SYS.FLARE, KERNEL_PID, sunspot_index=sunspot_index)

    # ------------------------------------------------------------------
    # Scheduler: round-robin SOL-0 dispatch
    # ------------------------------------------------------------------

    def schedule(self, n_ticks: int = 3) -> List[SyscallResult]:
        """
        SOL-0 round-robin scheduler.  Executes up to n_ticks READY processes
        in PID order, then yields back to caller.  Returns list of exec results.
        """
        results = []
        ready = sorted(
            [p for p in self._processes.values() if p.state == ProcessState.READY],
            key=lambda p: p.pid,
        )
        for proc in ready[:n_ticks]:
            results.append(self.exec(proc.pid))
        return results

    # ------------------------------------------------------------------
    # Kernel log access
    # ------------------------------------------------------------------

    def dmesg(self, last: int = 20) -> List[dict]:
        """Return the last N syscall log entries (kernel message buffer)."""
        return [r.to_dict() for r in self._log[-last:]]

    # ------------------------------------------------------------------
    # Memory map
    # ------------------------------------------------------------------

    def memmap(self) -> List[dict]:
        """Return current state of all 101 Moon pages."""
        return [
            {
                "address":    p.address,
                "owner_pid":  p.owner_pid,
                "value":      round(p.value, 8),
                "value_hash": p.value_hash,
                "record_id":  p.record_id,
                "free":       p.free,
            }
            for p in self._memory
        ]
