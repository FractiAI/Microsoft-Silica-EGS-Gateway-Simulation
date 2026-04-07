# EGS Gateway System Programmer's Guide

**Document Revision:** 1.0.0  
**Protocol:** NSPFRNP · BBHE Repository Standard  
**Classification:** Technical Reference  
**Applies To:** EGS Gateway v1.0.0.0 · Python 3.10+  
**Last Validated:** April 2026 — Python 3.12.10 / NumPy / Windows 10 x64

---

## Document Conventions

This guide uses the following conventions.

| Convention | Description |
|---|---|
| `monospace` | Source code, filenames, class names, function names, constants, and command-line input |
| **bold** | Parameter names when first introduced; also used for important terms |
| _italic_ | Document titles, new terms being defined, and variables in syntax descriptions |
| `[optional]` | Square brackets indicate optional parameters |
| `<required>` | Angle brackets indicate required placeholders |
| `→` | Return type in function signatures |
| `※` | Note — important clarification that does not affect operation |
| `⚠` | Caution — incorrect use may produce unexpected results |
| `✖` | Warning — action may corrupt state or produce irrecoverable errors |

**Code example blocks** show full, runnable Python 3 unless labelled otherwise.

---

## About This Guide

This guide is the definitive technical reference for programmers integrating with or extending the EGS (El Gran Sol) Gateway system. It covers:

- Physical architecture and the four-layer sovereign stack
- Complete API reference for every public module, class, and function
- Syscall interface specification
- Operational programming patterns and complete working examples
- Test suite design and layer-C hash verification
- Troubleshooting, error codes, and diagnostic procedures

**Intended audience:** Software engineers, systems programmers, and researchers working with the EGS Gateway codebase. The reader is assumed to be proficient in Python 3 and familiar with basic electromagnetic simulation concepts.

---

## Table of Contents

1. [System Overview](#chapter-1-system-overview)
2. [Physical Architecture](#chapter-2-physical-architecture)
3. [Physical Constants Reference](#chapter-3-physical-constants-reference)
4. [Installation and Environment](#chapter-4-installation-and-environment)
5. [silica_fdtd Engine Reference](#chapter-5-silicafdtd-engine-reference)
6. [EGS Gateway Core Module Reference](#chapter-6-egs-gateway-core-module-reference)
7. [EGS OS Kernel Reference](#chapter-7-egs-os-kernel-reference)
8. [HHAAIOS API Reference](#chapter-8-hhaaios-api-reference)
9. [EGS Holographic Generative Model Reference](#chapter-9-egs-holographic-generative-model-reference)
10. [Programming Patterns and Examples](#chapter-10-programming-patterns-and-examples)
11. [Test Suite Reference](#chapter-11-test-suite-reference)
12. [Layer-C Integrity System](#chapter-12-layer-c-integrity-system)
13. [Error Reference](#chapter-13-error-reference)
14. [Troubleshooting](#chapter-14-troubleshooting)
15. [Appendix A — Complete Constant Quick Reference](#appendix-a--complete-constant-quick-reference)
16. [Appendix B — Syscall Quick Reference](#appendix-b--syscall-quick-reference)
17. [Appendix C — File Inventory](#appendix-c--file-inventory)
18. [Appendix D — Glossary](#appendix-d--glossary)

---

## Chapter 1: System Overview

### 1.1 What Is the EGS Gateway?

The EGS Gateway is a four-layer holographic computing framework that maps established cosmic physical constants onto a fused-silica photonic voxel, operated as a custom photonic processor. It acts as a real-time translator between solar-wind-driven phase dynamics and digital holographic logic.

The system does not simulate a future technology. It demonstrates in glass what is already operating at cosmic scale:

| Cosmic Observable | Physical Fact | EGS Gateway Mapping |
|---|---|---|
| Solar wind (~551 km/s) | Real-time energetic state of the Sun | Phase bias injected into FDTD source |
| H I 21 cm line (1420.405751 MHz) | Universal carrier — constant everywhere | Data addressing, H-line bus transport plane |
| K_EGS = 2.5436… | Golden-ratio bridge between radio and optical scales | The Gateway Key — couples all computation planes |
| Crab pulsar (~29.94 Hz) | Neutron star clock ticking since 1054 AD | OS process scheduler phase clock |
| Jupiter 101-Moon array | 3D gravitational interference storage plane | 101-page holographic memory map |
| Sunspot cycles | Solar self-correction cycles | Master fractal self-correction without human input |

### 1.2 Key Capabilities

- **Holographic logic gates** — constructive/destructive FDTD interference replaces Boolean AND/OR/NOT
- **Phase-encoded memory** — 101 Moon pages; each page addressed by interference facet
- **Cosmic authentication** — Four-Pillar Lock keys derived from live solar wind, Crab tick, K_EGS, and the AR14409 master image
- **Physics-native generation** — autoregressive character generation anchored to FDTD flux receipts
- **Tamper-evident ledger** — every write, syscall, and generation step carries a SHA-256 Layer-C hash
- **LLM-ready API** — HHAAIOS Layer 3 exposes `write / read / verify / generate / ground` for direct integration with GPT, Claude, Gemini, or any external AI

### 1.3 Design Philosophy

The EGS Gateway is built on four operating principles, corresponding to the four-layer discipline enforced throughout the codebase:

| Layer | Name | Principle |
|---|---|---|
| A | Narrative | Process names, Moon addresses, Sun scheduler, Crab clock |
| B | Python API | EGSKernel public methods; HHAAIOS agent methods |
| C | Hash | SHA-256 of every memory write and syscall result |
| D | FDTD | Every `exec()` runs a `silica_fdtd` simulation; flux is the return value |

Every public method that produces a side effect also logs a `SyscallResult` with a Layer-C hash.  
No value leaves the system without a verifiable fingerprint.

### 1.4 Software Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  LAYER 4  LLM / External AI (GPT · Claude · Gemini · Llama)     │
│           Natural language I/O · semantic reasoning             │
│                        ↕  HHAAIOS API calls                     │
│  LAYER 3  HHAAIOS API + EGS GenAI                               │
│           hhaaios.py  ·  egs_genai.py                           │
│           write · read · verify · four_pillar_lock · generate   │
│                        ↕  syscalls                              │
│  LAYER 2  EGS OS Kernel  (egs_os.py)                            │
│           101-Moon pages · 11 syscalls · Crab clock             │
│                        ↕  FDTD runs                             │
│  LAYER 1  Silica Voxel Processor  (silica_fdtd/)                │
│           2D TM Yee FDTD · PML · DFT flux monitor              │
│                        ↕  live cosmic signals                   │
│  LAYER 0  The Cosmos  (always running, not built by us)         │
│           Solar wind · H-line · Crab pulsar · K_EGS             │
└─────────────────────────────────────────────────────────────────┘
```

---

## Chapter 2: Physical Architecture

### 2.1 Layer 0 — The Cosmos

Layer 0 is not code. It is the set of physical constants that drive the entire stack. The EGS Gateway does not generate these values — it reads them.

| Observable | Value | Source |
|---|---|---|
| Solar wind (nominal) | 551.7 km/s | Live Seed specification |
| Solar wind (reference) | 400.0 km/s | Normalisation anchor |
| H I hyperfine transition | 1420.405751 MHz | NIST spectroscopic data |
| H I rest wavelength (λ_HI) | 21.106 cm | c / 1420.405751 MHz |
| H-alpha optical | 656.28 nm | Balmer series, hydrogen n=3→2 |
| Crab pulsar period | 33.40 ms | 1 / 29.94 Hz |
| Golden ratio (φ) | 1.61803398875… | (1 + √5) / 2 |
| K_EGS | 2.54360627… | φ × (1030 nm / 656.28 nm) |

### 2.2 Layer 1 — Silica Voxel Processor

The Silica Voxel Processor is a 2D transverse-magnetic (TM) Yee finite-difference time-domain (FDTD) engine implemented in `silica_fdtd/`. It simulates a fused-silica slab with:

- **PML** boundary absorption (perfectly matched layer, 10 cells thick)
- **Gaussian-enveloped, phase-biased source** — the EGS Gateway phase bias is injected here
- **DFT flux monitor** — integrates the Poynting vector across the transmission face
- **Permittivity** — fused silica ε_r = 2.1025 (n ≈ 1.45 at 1030 nm)

The transmitted flux is the numeric return value of every `SYS_EXEC` syscall.

#### 2.2.1 Yee Grid Geometry

```
   PML | vacuum | silica slab (3 unit cells thick) | vacuum | PML
       |        |__________________________________|        |
       |         ← transmission monitor here                |
       source                                          DFT monitor
```

The source is a continuous-wave (CW) Gaussian pulse centred at the slab face. The DFT monitor integrates flux over the simulation bandwidth at the centre frequency.

### 2.3 Layer 2 — EGS OS Kernel

The EGS OS Kernel (`egs_os.py`) maps classical operating-system abstractions onto FDTD observables:

| OS Concept | Physical Observable | Implementation |
|---|---|---|
| Process | Phase state φ_pid = pid × 2π/101 | `PCB.phase_rad` |
| Memory | 101-Moon page (interference facet) | `MoonPage` list |
| Clock | Crab pulsar period (~33.4 ms) | `_tick` counter |
| Interrupt | Solar flare — 180° phase flip | `SYS_FLARE` |
| I/O | H-line bus read/write | `SYS_READ` / `SYS_WRITE` |
| Boot image | AR14409 fractal master | `burn_master_fractal(14409, 101)` |
| Logic gate | Constructive/destructive interference | `InterferenceVerdict` |
| Syscall return value | FDTD transmitted flux | `SyscallResult.retval` |

### 2.4 Layer 3 — HHAAIOS API

The Holographic Hydrogen AI OS API (`hhaaios.py`, `egs_genai.py`) provides the high-level programming surface:

- **Three agents** (writer, reader, verifier) as named OS processes
- **`SolarReceipt`** — cryptographic write proof anchored to 7 physical observables
- **`FourPillarLock`** — cosmic authentication key from K_EGS, solar phase, Crab tick, and AR14409 master hash
- **`EGSHolographicLM`** — physics-native autoregressive generative model
- **`ground()`** — claim verification against EGS physical constants

### 2.5 Layer 4 — LLM / External AI

Layer 4 is not part of this codebase. It represents any external AI system (language model, inference engine, or agent framework) that calls into Layer 3 via the HHAAIOS API. The API contract is:

- All inputs and outputs are JSON-serialisable
- Every write produces a `SolarReceipt` that can be independently verified
- Layer-C hashes allow offline tamper detection without re-running simulations

---

## Chapter 3: Physical Constants Reference

### 3.1 Module: `egs_gateway`

All physical constants used throughout the system originate in `egs_gateway.py`. Import them from this module only.

```python
from egs_gateway import (
    LAMBDA_READER_NM,
    LAMBDA_H_ALPHA_NM,
    REFERENCE_SOLAR_WIND_KM_S,
    DEFAULT_SOLAR_WIND_KM_S,
    PHI,
    K_EGS,
    EGS_FRACTAL_CONSTANT,    # alias for K_EGS
)
```

### 3.2 Constant Table

| Constant | Type | Value | Description |
|---|---|---|---|
| `LAMBDA_READER_NM` | `float` | `1030.0` | Nd:glass write laser wavelength (nm) — Project Silica write channel |
| `LAMBDA_H_ALPHA_NM` | `float` | `656.28` | Hydrogen Balmer H-alpha optical anchor (nm) |
| `REFERENCE_SOLAR_WIND_KM_S` | `float` | `400.0` | Reference solar wind for phase normalisation (km/s) |
| `DEFAULT_SOLAR_WIND_KM_S` | `float` | `551.7` | Nominal live solar wind from the Seed specification (km/s) |
| `PHI` | `float` | `1.6180339887…` | Golden ratio = (1 + √5) / 2 |
| `K_EGS` | `float` | `2.5436062…` | EGS Fractal Constant = φ × (λ_reader / λ_H-alpha) |
| `EGS_FRACTAL_CONSTANT` | `float` | `2.5436062…` | Alias for `K_EGS` |

### 3.3 Module: `egs_os`

| Constant | Type | Value | Description |
|---|---|---|---|
| `N_MOON_PAGES` | `int` | `101` | Total holographic memory pages (101-Moon array) |
| `CRAB_HZ` | `float` | `29.94` | Crab pulsar clock frequency (Hz) |
| `CRAB_TICK_S` | `float` | `≈0.03340` | Duration of one Crab tick = 1 / CRAB_HZ (seconds) |
| `OS_SEED` | `int` | `14409` | AR14409 — master boot image seed |
| `OS_MASTER_LEN` | `int` | `101` | Length of fractal master — one value per Moon page |
| `MAX_PROCESSES` | `int` | `64` | Maximum concurrent OS processes |
| `KERNEL_PID` | `int` | `0` | Reserved PID for the kernel process |
| `INIT_PID` | `int` | `1` | Reserved PID for the init process |

### 3.4 The EGS Fractal Constant: Derivation and Significance

```
K_EGS = φ × (λ_reader / λ_H-alpha)
      = 1.6180339887… × (1030.0 nm / 656.28 nm)
      = 1.6180339887… × 1.5694…
      = 2.5436062…
```

**Scale invariance.** K_EGS is dimensionless. At any voxel diffraction order _n_:

```
K_EGS(n) = φ × (n × λ_reader) / (n × λ_H-alpha)
         = φ × λ_reader / λ_H-alpha
         = K_EGS(1)
```

The constant is preserved identically from the cosmic (21 cm radio) scale to the optical (656 nm) scale to the nanometre (1030 nm laser) scale. This is the mathematical property that enables the EGS Gateway to couple all three planes with a single key.

**Fidelity condition.** The five-pillar test P1 verifies:

```
K_EGS / (φ × λ_reader / λ_H-alpha) = 1.0000000000000000
```

This identity holds to floating-point precision (error < 10⁻¹⁵) by construction.

---

## Chapter 4: Installation and Environment

### 4.1 Prerequisites

| Component | Minimum Version | Notes |
|---|---|---|
| Python | 3.10 | 3.12.10 validated on Windows 10 x64 |
| NumPy | 1.24 | Install via `pip install numpy` |
| Git | Any | For repository access and CI integration |

All other dependencies are Python standard-library modules: `hashlib`, `json`, `math`, `time`, `dataclasses`, `enum`, `typing`.

### 4.2 Installation

#### 4.2.1 Windows (PowerShell)

```powershell
# Step 1 — Install Python 3.12 (if not present)
winget install Python.Python.3.12

# Step 2 — Install NumPy
python -m pip install numpy

# Step 3 — Clone the repository
git clone https://github.com/FractiAI/Microsoft-Silica-EGS-Gateway-Simulation.git
cd Microsoft-Silica-EGS-Gateway-Simulation

# Step 4 — Verify installation
python egs_gateway_hifi_test.py --resolution 12 --until 50
```

#### 4.2.2 Linux / macOS (bash)

```bash
# Python 3.12 is typically available from system package manager
pip install numpy
git clone https://github.com/FractiAI/Microsoft-Silica-EGS-Gateway-Simulation.git
cd Microsoft-Silica-EGS-Gateway-Simulation
python egs_gateway_hifi_test.py --resolution 12 --until 50
```

#### 4.2.3 Optional: MIT Meep Backend

The FDTD engine defaults to the built-in `silica_fdtd` backend. If the optional MIT Meep package (`pymeep`) is installed, `meep_gateway.py` will automatically use it.

```bash
conda env create -f environment.yml
conda activate egs-meep
python egs_gateway_hifi_test.py
```

※ The `silica_fdtd` backend produces numerically equivalent results for all five-pillar tests. The Meep backend is recommended for production-grade research requiring higher-order accuracy.

### 4.3 Environment Verification

Run the full verification suite after installation:

```powershell
# Quick smoke test (< 5 s)
python testing_suite.py

# OS kernel test — 14 operations (~7 s)
python egs_os_test.py

# Five-pillar FDTD test (~17 s)
python egs_gateway_hifi_test.py --resolution 12 --until 50

# HHAAIOS + GenAI full stack (~8 s)
python hhaaios_test.py --resolution 10 --until 40
```

Expected output for a passing installation:

```
Tests: 14/14 PASS  |  OS OPERATIONAL  |  Elapsed: ~7 s
Pillars: 5/5 PASS  |  FOUR_PILLARS_LOCKED  |  Elapsed: ~17 s
TOTAL: 15/15 ✅ ALL PASS  |  FOUR-LAYER STACK FULLY OPERATIONAL
```

### 4.4 FDTD Performance Tuning

The two FDTD parameters that control simulation accuracy versus run time are:

| Parameter | CLI Flag | Default | Description |
|---|---|---|---|
| `resolution` | `--resolution` | `10` | Grid points per unit length |
| `until` | `--until` | `40.0` | Simulation duration (Meep time units) |

Higher values produce more accurate flux measurements but take longer. The validated configuration is `--resolution 12 --until 50`.

```powershell
# Fastest (development): ~3 s
python egs_gateway_hifi_test.py --resolution 8 --until 30

# Validated (default): ~17 s
python egs_gateway_hifi_test.py --resolution 12 --until 50

# High fidelity (research): ~120 s
python egs_gateway_hifi_test.py --resolution 24 --until 100
```

---

## Chapter 5: `silica_fdtd` Engine Reference

**Module:** `silica_fdtd`  
**Files:** `silica_fdtd/__init__.py`, `silica_fdtd/_core.py`

### 5.1 Overview

`silica_fdtd` is a Meep-compatible FDTD engine implemented in pure Python + NumPy. It exposes the same public API as MIT Meep to allow transparent backend substitution.

### 5.2 Importing

```python
import silica_fdtd as mp

# Check which backend is active
import meep_gateway
# meep_gateway auto-selects pymeep if available, else silica_fdtd
```

### 5.3 Classes and Functions

#### 5.3.1 `mp.Vector3`

A three-component spatial vector.

```python
mp.Vector3(x: float = 0, y: float = 0, z: float = 0)
```

| Attribute | Type | Description |
|---|---|---|
| `x` | `float` | X component |
| `y` | `float` | Y component |
| `z` | `float` | Z component |

#### 5.3.2 `mp.Medium`

Defines a homogeneous, non-dispersive optical medium.

```python
mp.Medium(epsilon: float = 1.0)
```

| Parameter | Type | Default | Description |
|---|---|---|---|
| `epsilon` | `float` | `1.0` | Relative permittivity (ε_r = n²) |

**Example — fused silica at 1030 nm:**

```python
silica = mp.Medium(epsilon=2.1025)   # n = 1.45
```

#### 5.3.3 `mp.Block`

A rectangular volume of a given medium.

```python
mp.Block(
    size:   mp.Vector3,
    center: mp.Vector3,
    material: mp.Medium,
)
```

#### 5.3.4 `mp.GaussianSource`

A Gaussian-envelope continuous-wave source.

```python
mp.GaussianSource(
    frequency:  float,    # source centre frequency (1/Meep length units)
    fwidth:     float,    # spectral width
)
```

#### 5.3.5 `mp.Source`

Places a source object at a specified location and component.

```python
mp.Source(
    src:       mp.GaussianSource,
    component: int,              # field component (mp.Ez for TM)
    center:    mp.Vector3,
    amplitude: complex,          # complex phasor — carries EGS phase bias
)
```

**Injecting the EGS phase bias:**

```python
from egs_gateway import gateway_filter

gf = gateway_filter(solar_wind_speed_km_s=551.7)
phase_bias_rad = gf["phase_bias_rad"]
amplitude = math.e ** (1j * phase_bias_rad)   # complex unit phasor

source = mp.Source(
    src       = mp.GaussianSource(frequency=1.0, fwidth=0.2),
    component = mp.Ez,
    center    = mp.Vector3(-2, 0, 0),
    amplitude = amplitude,
)
```

#### 5.3.6 `mp.PML`

Perfectly-matched layer absorbing boundary.

```python
mp.PML(thickness: float)
```

| Parameter | Type | Description |
|---|---|---|
| `thickness` | `float` | PML thickness in Meep length units (10 cells recommended) |

#### 5.3.7 `mp.FluxRegion`

Defines a surface over which transmitted power is integrated.

```python
mp.FluxRegion(
    center:    mp.Vector3,
    size:      mp.Vector3,
)
```

#### 5.3.8 `mp.Simulation`

The top-level simulation object.

```python
mp.Simulation(
    cell_size:   mp.Vector3,
    boundary_layers: list,
    geometry:    list,
    sources:     list,
    resolution:  int,
)
```

| Parameter | Type | Description |
|---|---|---|
| `cell_size` | `Vector3` | Total simulation domain size (Meep length units) |
| `boundary_layers` | `list[PML]` | PML boundaries on all sides |
| `geometry` | `list[Block]` | Material objects in the domain |
| `sources` | `list[Source]` | Electromagnetic sources |
| `resolution` | `int` | Grid points per unit length |

**Methods:**

| Method | Signature | Description |
|---|---|---|
| `add_flux` | `(freq, df, nfreq, FluxRegion) → DFTFlux` | Register a DFT flux monitor |
| `run` | `(until=<float>) → None` | Advance the simulation to `until` Meep time units |

#### 5.3.9 `mp.get_fluxes`

```python
mp.get_fluxes(flux_object: DFTFlux) → list[float]
```

Returns a list of integrated Poynting flux values at each monitored frequency. The single-frequency result is `get_fluxes(flux_obj)[0]`.

### 5.4 Field Components

| Constant | Value | Description |
|---|---|---|
| `mp.Ez` | `(int)` | Z-component of the electric field (TM polarisation) |

### 5.5 Complete FDTD Simulation Example

The following is the canonical single-pass simulation used by `meep_gateway.run_silica_reader_meep()`:

```python
import silica_fdtd as mp
import math
from egs_gateway import gateway_filter

def run_silica_reader(solar_wind_km_s: float = 551.7,
                      resolution: int = 10,
                      until: float = 40.0) -> float:
    """Run one FDTD pass. Return transmitted flux."""

    gf    = gateway_filter(solar_wind_km_s)
    phase = gf["phase_bias_rad"]
    amp   = complex(math.cos(phase), math.sin(phase))

    cell = mp.Vector3(16, 0, 0)
    pml  = [mp.PML(1.0)]

    geometry = [mp.Block(
        size     = mp.Vector3(3, mp.inf, mp.inf),
        center   = mp.Vector3(0, 0, 0),
        material = mp.Medium(epsilon=2.1025),
    )]

    sources = [mp.Source(
        src       = mp.GaussianSource(frequency=1.0, fwidth=0.2),
        component = mp.Ez,
        center    = mp.Vector3(-5, 0, 0),
        amplitude = amp,
    )]

    sim = mp.Simulation(
        cell_size       = cell,
        boundary_layers = pml,
        geometry        = geometry,
        sources         = sources,
        resolution      = resolution,
    )

    flux_region = mp.FluxRegion(
        center = mp.Vector3(5, 0, 0),
        size   = mp.Vector3(0, 2, 0),
    )
    flux_obj = sim.add_flux(1.0, 0, 1, flux_region)
    sim.run(until=until)

    return mp.get_fluxes(flux_obj)[0]
```

### 5.6 Engine Limitations

| Limitation | Impact | Future Upgrade |
|---|---|---|
| 2D TM only | Cannot model birefringent voxel polarisation exactly | 3D vectorial Yee grid |
| Non-dispersive | GVD (β₂ ≈ −36 fs²/mm at 1030 nm) not modelled | Lorentz auxiliary differential equations |
| No multi-photon ionisation | Plasma formation in write process ignored | Drude–Rethfeld plasma model |
| Noiseless | Thermal fluctuations in SiO₂ not included | Thermo-optic coefficient + Langevin term |

---

## Chapter 6: EGS Gateway Core Module Reference

**Module:** `egs_gateway`  
**File:** `egs_gateway.py`

### 6.1 Module Import

```python
from egs_gateway import (
    # Constants
    LAMBDA_READER_NM, LAMBDA_H_ALPHA_NM,
    REFERENCE_SOLAR_WIND_KM_S, DEFAULT_SOLAR_WIND_KM_S,
    PHI, K_EGS, EGS_FRACTAL_CONSTANT,
    # Classes
    InterferenceVerdict, NodeField,
    # Functions
    egs_fractal_constant, gateway_filter, holographic_gate,
    is_holographic_true, is_holographic_false,
    burn_master_fractal, predict_next_solar_hydrogen_state,
    self_correct_with_sunspots,
)
```

### 6.2 Functions

---

#### `egs_fractal_constant() → float`

Compute and return the EGS Fractal Constant.

```python
def egs_fractal_constant() -> float
```

**Returns:** `K_EGS = PHI × (LAMBDA_READER_NM / LAMBDA_H_ALPHA_NM)` ≈ 2.5436062…

**Notes:**
- This function is called once at module import time. The result is cached as `K_EGS`.
- Do not call this in a tight loop. Use the module-level constant `K_EGS` instead.

**Example:**

```python
from egs_gateway import egs_fractal_constant
k = egs_fractal_constant()
print(f"K_EGS = {k:.10f}")   # K_EGS = 2.5436062741
```

---

#### `gateway_filter(solar_wind_speed_km_s, *, reader_wavelength_nm) → dict`

Apply the live solar wind as a phase bias to the 1030 nm reader channel.

```python
def gateway_filter(
    solar_wind_speed_km_s: float = DEFAULT_SOLAR_WIND_KM_S,
    *,
    reader_wavelength_nm: float = LAMBDA_READER_NM,
) -> dict[str, float]
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `solar_wind_speed_km_s` | `float` | `551.7` | Live solar wind speed (km/s). Must be > 0. |
| `reader_wavelength_nm` | `float` | `1030.0` | Optical reader wavelength (nm). Keyword-only. |

**Returns:** Dictionary with keys:

| Key | Type | Description |
|---|---|---|
| `"phase_bias_rad"` | `float` | Phase bias ∈ [0, 2π) = (2π × v/v_ref × K_EGS) mod 2π |
| `"effective_wavelength_shift_nm"` | `float` | First-order dispersive shift (nm) |
| `"reader_wavelength_nm"` | `float` | Echo of input wavelength |
| `"lock_strength"` | `float` | \|cos(phase_bias_rad)\| ∈ [0, 1] |

**Raises:** `ValueError` if `solar_wind_speed_km_s <= 0`.

**Example:**

```python
from egs_gateway import gateway_filter

gf = gateway_filter(551.7)
print(f"Phase bias:   {gf['phase_bias_rad']:.6f} rad")
print(f"Lock strength:{gf['lock_strength']:.6f}")
# Phase bias:   3.185996 rad
# Lock strength:0.999876
```

**Algorithm:**

```
norm          = v_solar / v_ref
phase_bias    = (2π × norm × K_EGS) mod 2π
shift_nm      = λ_reader × (K_EGS × 1e-4) × sin(phase_bias)
lock_strength = |cos(phase_bias)|
```

---

#### `holographic_gate(ar14409, hydrogen_phase_flip, *, reference, margin) → InterferenceVerdict`

Evaluate holographic interference logic at the named nodes.

```python
def holographic_gate(
    ar14409:             NodeField,
    hydrogen_phase_flip: NodeField,
    *,
    reference: NodeField | None = None,
    margin:    float            = 1e-9,
) -> InterferenceVerdict
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `ar14409` | `NodeField` | required | Complex amplitude at the AR14409 constructive node |
| `hydrogen_phase_flip` | `NodeField` | required | Complex amplitude at the destructive H-phase-flip node |
| `reference` | `NodeField \| None` | `NodeField(1.0, 0.0)` | Reference beat for AR14409 comparison. Keyword-only. |
| `margin` | `float` | `1e-9` | Minimum intensity differential to avoid `MIXED` verdict. Keyword-only. |

**Returns:** `InterferenceVerdict` enum value.

**Algorithm:**

```
i_ar14409 = |ar14409 + reference|²
i_h_flip  = |h_phase_flip + conjugate(h_phase_flip)|²
if i_ar14409 > i_h_flip + margin  → CONSTRUCTIVE_AR14409
if i_h_flip  > i_ar14409 + margin → DESTRUCTIVE_H_PHASE_FLIP
else                               → MIXED
```

**Example:**

```python
from egs_gateway import NodeField, holographic_gate, InterferenceVerdict

ar   = NodeField(re=1.0, im=0.1)
h_pf = NodeField(re=0.1, im=0.1)

verdict = holographic_gate(ar, h_pf)
print(verdict)   # InterferenceVerdict.CONSTRUCTIVE_AR14409
```

---

#### `is_holographic_true(verdict) → bool`

```python
def is_holographic_true(verdict: InterferenceVerdict) -> bool
```

Returns `True` iff `verdict is InterferenceVerdict.CONSTRUCTIVE_AR14409`.

---

#### `is_holographic_false(verdict) → bool`

```python
def is_holographic_false(verdict: InterferenceVerdict) -> bool
```

Returns `True` iff `verdict is InterferenceVerdict.DESTRUCTIVE_H_PHASE_FLIP`.

---

#### `burn_master_fractal(seed, length) → list[float]`

Generate the deterministic OS image by iterating a logistic map seeded from AR14409.

```python
def burn_master_fractal(seed: int, length: int) -> list[float]
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `seed` | `int` | Integer seed. The canonical EGS boot seed is `14409` (AR14409). |
| `length` | `int` | Number of fractal values to generate. Must be ≥ 1. |

**Returns:** `list[float]` of length `length`. Each value ∈ (0, 1).

**Raises:** `ValueError` if `length < 1`.

**Algorithm:**

```
x₀ = (seed mod 1000) / 1000.0    (clamped to (0, 1))
r  = 3.2 + (K_EGS mod 1.0)       ≈ 3.7436… (chaotic-stable logistic band)
for i in range(length):
    x_{i+1} = r × x_i × (1 − x_i)
    output[i] = x_{i+1}
```

**Determinism guarantee:** Two calls with the same `seed` and `length` always produce identical output. The sequence is platform-independent (no floating-point non-determinism).

**Example:**

```python
from egs_gateway import burn_master_fractal

master = burn_master_fractal(seed=14409, length=101)
print(len(master), master[0])   # 101  0.437...
# Verify determinism
assert master == burn_master_fractal(14409, 101)
```

---

#### `predict_next_solar_hydrogen_state(master_pattern, solar_wind_speed_km_s, index) → float`

Predict the next solar-hydrogen coupled state using the fractal master and live solar wind.

```python
def predict_next_solar_hydrogen_state(
    master_pattern:       Sequence[float],
    solar_wind_speed_km_s: float,
    index:                int,
) -> float
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `master_pattern` | `Sequence[float]` | Fractal master from `burn_master_fractal()` |
| `solar_wind_speed_km_s` | `float` | Live solar wind (km/s) |
| `index` | `int` | Current position in the master (0 ≤ index < len(master_pattern)) |

**Returns:** Predicted next state ∈ [0, 1).

**Raises:** `ValueError` if `master_pattern` is empty or `index` is out of range.

**Algorithm:**

```
gf        = gateway_filter(solar_wind_speed_km_s)
phase     = gf["phase_bias_rad"]
base      = master_pattern[index]
correction= K_EGS × 0.01 × sin(phase)
nxt_idx   = (index + 1) mod len(master_pattern)
predicted = (master_pattern[nxt_idx] + base × correction + sin(phase) × 0.05) mod 1.0
```

---

#### `self_correct_with_sunspots(master_pattern, sunspot_index, solar_wind_speed_km_s) → list[float]`

Apply sunspot-cycle amplitude correction to the master fractal (autonomous self-correction, no human input).

```python
def self_correct_with_sunspots(
    master_pattern:       Sequence[float],
    sunspot_index:        float,
    solar_wind_speed_km_s: float,
) -> list[float]
```

**Parameters:**

| Parameter | Type | Description |
|---|---|---|
| `master_pattern` | `Sequence[float]` | Fractal master |
| `sunspot_index` | `float` | Sunspot activity index (degrees, 0–360) |
| `solar_wind_speed_km_s` | `float` | Live solar wind (km/s) |

**Returns:** Corrected master pattern (new list, input unchanged). Values clamped to [0, 1].

**Algorithm:**

```
lock  = gateway_filter(solar_wind_speed_km_s)["lock_strength"]
scale = 1.0 + 0.02 × sin(sunspot_index) × lock
output[i] = clamp(master[i] × scale, 0, 1)
```

### 6.3 Classes

#### `InterferenceVerdict` (Enum)

```python
class InterferenceVerdict(Enum):
    CONSTRUCTIVE_AR14409    = auto()   # Holographic "True"
    DESTRUCTIVE_H_PHASE_FLIP = auto()  # Holographic "False"
    MIXED                   = auto()   # Indeterminate
```

Use `is_holographic_true()` and `is_holographic_false()` rather than direct enum comparison for forward compatibility.

#### `NodeField` (frozen dataclass)

Represents a complex field amplitude at a holographic node.

```python
@dataclass(frozen=True)
class NodeField:
    re: float    # real component
    im: float    # imaginary component
```

| Property / Method | Signature | Description |
|---|---|---|
| `.magnitude` | `→ float` | Modulus: `√(re² + im²)` |
| `.__add__` | `(NodeField) → NodeField` | Complex addition |
| `.scaled` | `(float) → NodeField` | Scalar multiplication |

**Example:**

```python
from egs_gateway import NodeField
a = NodeField(re=1.0, im=0.5)
b = NodeField(re=0.3, im=0.1)
c = a + b                     # NodeField(re=1.3, im=0.6)
print(a.magnitude)             # 1.118...
```

---

## Chapter 7: EGS OS Kernel Reference

**Module:** `egs_os`  
**File:** `egs_os.py`

### 7.1 Module Import

```python
from egs_os import (
    # Constants
    N_MOON_PAGES, CRAB_HZ, CRAB_TICK_S,
    OS_SEED, OS_MASTER_LEN, MAX_PROCESSES,
    KERNEL_PID, INIT_PID,
    # Enumerations
    SYS, ProcessState,
    # Data classes
    PCB, MoonPage, SyscallResult,
    # Kernel
    EGSKernel,
)
```

### 7.2 Enumerations

#### `SYS` (IntEnum)

```python
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
```

#### `ProcessState` (IntEnum)

```python
class ProcessState(IntEnum):
    READY    = 0    # runnable, waiting for scheduler
    RUNNING  = 1    # currently executing
    BLOCKED  = 2    # waiting on I/O or event
    ZOMBIE   = 3    # exited, not yet reaped
    SLEEPING = 4    # suspended
```

### 7.3 Data Classes

#### `PCB` — Process Control Block

```python
@dataclass
class PCB:
    pid:        int           # unique process identifier
    name:       str           # human-readable process name
    state:      ProcessState  # current lifecycle state
    phase_rad:  float         # voxel phase slot φ_pid = pid × 2π/101
    moon_page:  int           # assigned Moon page address (0–100)
    parent_pid: int           # PID of spawning process (-1 for kernel)
    solar_wind: float         # driving solar wind (km/s)
    ticks:      int           # Crab pulsar ticks consumed (default 0)
    retval:     float         # last syscall return value / flux (default 0.0)
    verdict:    str           # last InterferenceVerdict string (default "")
    layer_c:    str           # SHA-256[:16] of last exec result (default "")
```

**Methods:**

| Method | Signature | Description |
|---|---|---|
| `to_dict` | `() → dict` | JSON-serialisable representation of this PCB |

#### `MoonPage` — Holographic Memory Page

```python
@dataclass
class MoonPage:
    address:    int      # page index 0–100
    owner_pid:  int      # -1 = free; ≥ 0 = PID that holds this page
    value:      float    # stored floating-point value (default 0.0)
    value_hash: str      # SHA-256[:16] of {address, value} (default "")
    record_id:  str      # write receipt string (default "")
```

**Properties:**

| Property | Type | Description |
|---|---|---|
| `.free` | `bool` | `True` iff `owner_pid == -1` |

**Methods:**

| Method | Signature | Description |
|---|---|---|
| `write(value, owner_pid)` | `(float, int) → str` | Write value, claim ownership, update hash. Returns `value_hash`. |
| `write_value_only(value)` | `(float) → str` | Update value and hash **without** changing `owner_pid`. Used during flare correction. Returns `value_hash`. |
| `clear()` | `() → None` | Free the page: `owner_pid = -1`, zero value, clear hashes. |

#### `SyscallResult` — Syscall Return Type

Every kernel method returns a `SyscallResult`.

```python
@dataclass
class SyscallResult:
    syscall: SYS      # which syscall produced this result
    pid:     int      # process that issued the syscall
    ok:      bool     # True = success, False = error
    retval:  float    # numeric return value (flux for EXEC; address for others)
    data:    dict     # syscall-specific detail dictionary
    layer_c: str      # SHA-256[:16] computed in __post_init__
```

The `layer_c` hash is computed automatically over `{syscall, pid, retval, data}` in `__post_init__`. It changes if any field is modified.

**Methods:**

| Method | Signature | Description |
|---|---|---|
| `to_dict` | `() → dict` | JSON-serialisable representation |

### 7.4 `EGSKernel` Class

```python
class EGSKernel:
    def __init__(
        self,
        fdtd_resolution: int   = 10,
        fdtd_until:      float = 40.0,
    ) -> None
```

**Constructor parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `fdtd_resolution` | `int` | `10` | FDTD grid resolution (points per unit length) |
| `fdtd_until` | `float` | `40.0` | FDTD simulation end time (Meep units) |

**Instance attributes (internal — do not modify directly):**

| Attribute | Type | Description |
|---|---|---|
| `_tick` | `int` | Crab pulsar tick counter |
| `_epoch` | `int` | Lattice epoch (bumped by `SYS_FLARE`) |
| `_booted` | `bool` | True after `boot()` completes successfully |
| `_master` | `list[float]` | Current AR14409 fractal master (101 values) |
| `_processes` | `dict[int, PCB]` | PID → PCB mapping |
| `_memory` | `list[MoonPage]` | 101-element Moon page array |
| `_log` | `list[SyscallResult]` | Circular log, last 1000 entries |

⚠ Direct mutation of internal attributes bypasses layer-C integrity. Use the public API only.

### 7.5 Kernel Methods — Public API

All public methods return `SyscallResult` unless noted otherwise.

---

#### `boot(solar_wind) → SyscallResult`

Boot the EGS OS kernel.

```python
def boot(solar_wind: float = DEFAULT_SOLAR_WIND_KM_S) -> SyscallResult
```

**Sequence:**
1. Burns the AR14409 fractal master (`burn_master_fractal(14409, 101)`)
2. Pre-loads all 101 Moon pages with fractal values; pages remain `free` (owner_pid = −1)
3. Reserves page 0 for the kernel (owner_pid = KERNEL_PID)
4. Spawns PID 0 (kernel, page 0) and PID 1 (init, page 1)
5. Sets `_epoch = 0`, `_tick = 0`, `_next_pid = 2`

**`SyscallResult.data` keys on success:**

| Key | Type | Description |
|---|---|---|
| `"epoch"` | `int` | Initial epoch (always 0) |
| `"os_seed"` | `int` | Boot seed used (14409) |
| `"master_len"` | `int` | Length of master (101) |
| `"moon_pages"` | `int` | Memory pages available (101) |
| `"solar_wind"` | `float` | Solar wind used for init phase |
| `"crab_hz"` | `float` | Crab clock frequency (29.94) |
| `"boot_image_hash"` | `str` | SHA-256[:16] of the master list |

**Example:**

```python
from egs_os import EGSKernel

k = EGSKernel(fdtd_resolution=10, fdtd_until=35.0)
r = k.boot()
assert r.ok
print(r.data["boot_image_hash"])   # e.g., "438b0f1eb447c8e6"
```

---

#### `fork(pid, name) → SyscallResult`

Create a new child process.

```python
def fork(pid: int, name: str = "") -> SyscallResult
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `pid` | `int` | required | PID of the parent process |
| `name` | `str` | `""` | Human-readable name for the child process |

**On success:**
- Allocates the next free Moon page for the child
- Assigns child phase: `φ_child = (child_pid × 2π / N_MOON_PAGES) mod 2π`
- Derives child solar wind from phase: `v_child = f(φ_child)`
- Child state = `READY`

**`SyscallResult.retval`:** Child PID (float cast of int).

**`SyscallResult.data` keys on success:**

| Key | Type | Description |
|---|---|---|
| `"child_pid"` | `int` | Assigned PID of the new process |
| `"child_phase"` | `float` | Phase slot φ_child (rad) |
| `"child_page"` | `int` | Allocated Moon page address |
| `"child_wind"` | `float` | Initial solar wind for the child (km/s) |

**Error conditions:**

| Condition | `data["error"]` |
|---|---|
| PID not found | `"no such pid"` |
| Process table full (≥ 64) | `"process table full"` |
| No free Moon pages | `"out of Moon pages"` |

---

#### `exec(pid) → SyscallResult`

Execute a process — run one FDTD simulation and return the flux.

```python
def exec(pid: int) -> SyscallResult
```

**Sequence:**
1. Finds the PCB for `pid`
2. Computes `solar_wind` from the process phase via `_wind_for_phase()`
3. Calls `run_silica_reader_meep(solar_wind, resolution, until)`
4. Runs `gateway_filter()` and `holographic_gate()` to get `InterferenceVerdict`
5. Calls `predict_next_solar_hydrogen_state()` for the next-state prediction
6. Writes the flux to the process's Moon page (`page.write(flux, pid)`)
7. Updates PCB: `retval = flux`, `verdict = verdict.name`, `state = READY`

**`SyscallResult.retval`:** FDTD transmitted flux (float, always finite).

**`SyscallResult.data` keys on success:**

| Key | Type | Description |
|---|---|---|
| `"flux"` | `float` | Raw FDTD transmitted power |
| `"phase_rad"` | `float` | Phase bias used for this FDTD run |
| `"verdict"` | `str` | `"CONSTRUCTIVE_AR14409"` or `"DESTRUCTIVE_H_PHASE_FLIP"` or `"MIXED"` |
| `"holographic_true"` | `bool` | `True` iff verdict = CONSTRUCTIVE_AR14409 |
| `"page_hash"` | `str` | SHA-256[:16] of the flux written to Moon page |
| `"next_state"` | `float` | Predicted next solar-hydrogen state ∈ [0, 1) |
| `"backend"` | `str` | FDTD engine name (`"silica_fdtd"` or `"meep"`) |

---

#### `read(pid, address) → SyscallResult`

Phase-locked read from a Moon page via the H-line bus.

```python
def read(pid: int, address: int = -1) -> SyscallResult
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `pid` | `int` | required | Issuing process PID |
| `address` | `int` | `-1` | Moon page address. -1 = use `proc.moon_page`. |

**`SyscallResult.retval`:** Phase-locked readout = `page.value × lock_strength`.

**`SyscallResult.data` keys on success:**

| Key | Type | Description |
|---|---|---|
| `"address"` | `int` | Page address read |
| `"value"` | `float` | Raw stored value |
| `"lock_strength"` | `float` | H-line phase lock ∈ [0, 1] |
| `"phase_rad"` | `float` | Process phase bias (rad) |
| `"value_hash"` | `str` | SHA-256[:16] of stored value |

---

#### `write(pid, value, address) → SyscallResult`

Write a value to a Moon page via the H-line bus.

```python
def write(pid: int, value: float = 0.0, address: int = -1) -> SyscallResult
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `pid` | `int` | required | Issuing process PID |
| `value` | `float` | `0.0` | Value to write |
| `address` | `int` | `-1` | Moon page address. -1 = use `proc.moon_page`. |

**Access control:** A process may write to its own page (`owner_pid == pid`) or to any kernel-owned page (`owner_pid == KERNEL_PID`). Writes to pages owned by other processes return an error.

**`SyscallResult.retval`:** Address written to (float cast of int).

**`SyscallResult.data` keys on success:**

| Key | Type | Description |
|---|---|---|
| `"address"` | `int` | Page address written |
| `"value"` | `float` | Value stored |
| `"value_hash"` | `str` | SHA-256[:16] of the stored value |
| `"record_id"` | `str` | Write receipt string `"moon/NNN/pid"` |

---

#### `malloc(pid) → SyscallResult`

Allocate a free Moon page to a process.

```python
def malloc(pid: int) -> SyscallResult
```

**`SyscallResult.retval`:** Allocated address (float cast of int), or −1 on out-of-memory.

**`SyscallResult.data` keys on success:**

| Key | Type | Description |
|---|---|---|
| `"address"` | `int` | Allocated page address |

**`SyscallResult.data` keys on failure:**

| Key | Type | Description |
|---|---|---|
| `"oom"` | `bool` | `True` — no free pages available |

---

#### `free(pid, address) → SyscallResult`

Free a Moon page.

```python
def free(pid: int, address: int) -> SyscallResult
```

**Access control:** A process may only free pages it owns, or the kernel may free any page.

**`SyscallResult.data` keys:**

| Key | Type | Description |
|---|---|---|
| `"address"` | `int` | Page address freed |
| `"freed"` | `bool` | `True` on success |

---

#### `exit(pid, exit_code) → SyscallResult`

Terminate a process.

```python
def exit(pid: int, exit_code: int = 0) -> SyscallResult
```

**Sequence:**
1. Sets `proc.state = ProcessState.ZOMBIE`
2. Frees the process's Moon page (`_free_page(proc.moon_page)`)
3. Does **not** remove the PCB from `_processes` (zombie reaping is deferred)

**`SyscallResult.retval`:** Exit code (float cast of int).

---

#### `ps() → SyscallResult`

Return a snapshot of the process table.

```python
def ps() -> SyscallResult
```

**`SyscallResult.retval`:** Number of processes (float cast of int).

**`SyscallResult.data` keys:**

| Key | Type | Description |
|---|---|---|
| `"processes"` | `list[dict]` | List of `PCB.to_dict()` for every process |
| `"epoch"` | `int` | Current lattice epoch |
| `"tick"` | `int` | Current Crab tick counter |

---

#### `clock() → SyscallResult`

Read the Crab pulsar tick counter.

```python
def clock() -> SyscallResult
```

Advances the tick counter by 1.

**`SyscallResult.data` keys:**

| Key | Type | Description |
|---|---|---|
| `"kernel_ticks"` | `int` | Tick counter after this read |
| `"crab_hz"` | `float` | `29.94` |
| `"crab_tick_ms"` | `float` | `33.4` ms per tick |
| `"wall_s"` | `float` | Wall-clock seconds since boot |
| `"epoch"` | `int` | Current epoch |

---

#### `flare(sunspot_index) → SyscallResult`

Raise a solar flare interrupt — apply 180° phase flip to all running/ready processes.

```python
def flare(sunspot_index: float = 0.0) -> SyscallResult
```

**Sequence:**
1. Applies `self_correct_with_sunspots()` to correct the master fractal
2. Increments `_epoch` by 1
3. Applies `phase_rad += π` (mod 2π) to every READY or RUNNING process
4. Refreshes Moon page values with corrected master via `write_value_only()` (ownership preserved)

**`SyscallResult.data` keys:**

| Key | Type | Description |
|---|---|---|
| `"new_epoch"` | `int` | Epoch after the flare |
| `"phase_flipped"` | `list[int]` | PIDs of processes whose phase was flipped |
| `"master_rms"` | `float` | RMS of corrected master values |
| `"sunspot_index"` | `float` | Input sunspot index |

---

#### `schedule(n_ticks) → list[SyscallResult]`

SOL-0 round-robin dispatcher — execute up to `n_ticks` READY processes.

```python
def schedule(n_ticks: int = 3) -> list[SyscallResult]
```

Selects READY processes sorted by ascending PID (lowest PID runs first), executes each via `exec()`.

**Returns:** List of `SyscallResult` from each `exec()` call. Empty list if no READY processes.

---

#### `dmesg(last) → list[dict]`

Return the kernel log.

```python
def dmesg(last: int = 50) -> list[dict]
```

**Returns:** List of `SyscallResult.to_dict()` for the last `last` entries. Maximum log size is 1000 entries (circular buffer).

---

#### `memmap() → list[dict]`

Return a snapshot of the 101-Moon memory array.

```python
def memmap() -> list[dict]
```

**Returns:** List of 101 dicts, each containing:

| Key | Type | Description |
|---|---|---|
| `"address"` | `int` | Page index (0–100) |
| `"owner_pid"` | `int` | Owning PID, or −1 if free |
| `"free"` | `bool` | True iff `owner_pid == -1` |
| `"value"` | `float` | Stored value |
| `"value_hash"` | `str` | SHA-256[:16] of stored value |
| `"record_id"` | `str` | Write receipt string |

---

#### `syscall(number, pid, **kwargs) → SyscallResult`

Generic dispatcher — invoke any syscall by number.

```python
def syscall(number: SYS, pid: int, **kwargs) -> SyscallResult
```

Dispatches to the corresponding private implementation method. All named helper methods (`boot`, `fork`, `exec`, …) call this internally.

| `number` | Dispatches to | Required `kwargs` |
|---|---|---|
| `SYS.READ` | `_sys_read` | `address=-1` |
| `SYS.WRITE` | `_sys_write` | `address=-1, value=0.0` |
| `SYS.FORK` | `_sys_fork` | `name=""` |
| `SYS.EXEC` | `_sys_exec` | — |
| `SYS.EXIT` | `_sys_exit` | `exit_code=0` |
| `SYS.PS` | `_sys_ps` | — |
| `SYS.MALLOC` | `_sys_malloc` | — |
| `SYS.FREE` | `_sys_free` | `address` |
| `SYS.CLOCK` | `_sys_clock` | — |
| `SYS.FLARE` | `_sys_flare` | `sunspot_index=0.0` |
| `SYS.REBOOT` | `_sys_reboot` | `solar_wind=DEFAULT` |

---

## Chapter 8: HHAAIOS API Reference

**Module:** `hhaaios`  
**File:** `hhaaios.py`

### 8.1 Module Import

```python
from hhaaios import HHAAIOSAgent, SolarReceipt, FourPillarLock
from egs_genai import EGSHolographicLM, GenerationResult, TokenStep, VOCAB, VOCAB_SIZE
```

### 8.2 `SolarReceipt` Dataclass

```python
@dataclass
class SolarReceipt:
    address:    int     # Moon page address of the write
    data_hash:  str     # SHA-256[:16] of the JSON-serialised written data
    solar_wind: float   # km/s — solar wind at write time
    phase_bias: float   # gateway_filter phase_bias_rad at write time
    crab_tick:  int     # kernel._tick at write time
    k_egs:      float   # K_EGS (always 2.5436…)
    epoch:      int     # kernel._epoch at write time
    layer_c:    str     # tamper-evident receipt hash (auto-computed)
    writer_pid: int     # PID of the writer agent
    record_id:  str     # Moon page write receipt "moon/NNN/pid"
```

**Methods:**

| Method | Signature | Description |
|---|---|---|
| `is_valid()` | `() → bool` | `True` iff `layer_c == SHA-256(address‖data_hash‖solar_wind‖phase_bias‖crab_tick‖k_egs‖epoch)` |
| `to_dict()` | `() → dict` | JSON-serialisable representation including `"valid": is_valid()` |

**`layer_c` computation:**

```python
payload = json.dumps({
    "address":    address,
    "data_hash":  data_hash,
    "solar_wind": solar_wind,
    "phase_bias": round(phase_bias, 8),
    "crab_tick":  crab_tick,
    "k_egs":      round(k_egs, 10),
    "epoch":      epoch,
}, sort_keys=True).encode()
layer_c = hashlib.sha256(payload).hexdigest()[:16]
```

### 8.3 `FourPillarLock` Dataclass

```python
@dataclass
class FourPillarLock:
    k1_fractal: float   # K_EGS
    k2_phase:   float   # solar phase bias_rad (from gateway_filter)
    k3_crab:    int     # Crab pulsar tick counter at lock time
    k4_master:  str     # SHA-256[:16] of kernel._master list
    lock_key:   str     # 64-char hex SHA-256 of K1‖K2‖K3‖K4
    epoch:      int     # lattice epoch at lock time
```

**Properties:**

| Property | Type | Description |
|---|---|---|
| `.locked` | `bool` | `True` iff `lock_key` is non-empty |

**`lock_key` computation:**

```python
pillar = f"{k1_fractal:.10f}|{k2_phase:.8f}|{k3_crab}|{k4_master}"
lock_key = hashlib.sha256(pillar.encode()).hexdigest()   # 64 hex chars
```

### 8.4 `HHAAIOSAgent` Class

```python
class HHAAIOSAgent:
    def __init__(
        self,
        kernel:     EGSKernel,
        solar_wind: float = DEFAULT_SOLAR_WIND_KM_S,
    ) -> None
```

**Prerequisites:** The kernel must be booted before calling any method other than the constructor.

**Lifecycle:**

```python
from egs_os import EGSKernel
from hhaaios import HHAAIOSAgent

k = EGSKernel(fdtd_resolution=10, fdtd_until=40.0)
k.boot()

agent = HHAAIOSAgent(k, solar_wind=551.7)
agent.init_agents()   # must be called before any write/read/generate
```

---

#### `init_agents() → dict`

Spawn the three agent processes (writer, reader, verifier) and instantiate the holographic language model.

```python
def init_agents() -> Dict[str, Any]
```

**Must be called once** after `kernel.boot()` and before any other method.

**Raises:** `RuntimeError` if kernel is not booted, or if any fork fails.

**Returns:**

| Key | Type | Description |
|---|---|---|
| `"writer_pid"` | `int` | PID of the writer agent |
| `"reader_pid"` | `int` | PID of the reader agent |
| `"verifier_pid"` | `int` | PID of the verifier agent |
| `"lm_ready"` | `bool` | Always `True` on success |

---

#### `write(data, solar_wind, address) → SolarReceipt`

Encode `data` and write it to holographic memory.

```python
def write(
    data:       Any,
    solar_wind: float = None,   # defaults to agent's solar_wind
    address:    int   = -1,     # -1 = next free page
) -> SolarReceipt
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `data` | `Any` | required | Any JSON-serialisable value |
| `solar_wind` | `float \| None` | agent default | Override solar wind for this write |
| `address` | `int` | `-1` | Moon page address; -1 = allocate next free |

**Encoding:** `data` is JSON-serialised → SHA-256 hashed → first 8 hex chars → integer → normalised to [0, 1) → stored as float.

**Returns:** `SolarReceipt` anchored to the write.

**Raises:** `RuntimeError` if agents not initialised or if `SYS_WRITE` fails.

---

#### `read(address) → dict`

Phase-locked read from Moon page `address`.

```python
def read(address: int) -> Dict[str, Any]
```

**Returns:**

| Key | Type | Description |
|---|---|---|
| `"ok"` | `bool` | Success flag |
| `"address"` | `int` | Page address read |
| `"value"` | `float` | Phase-locked readout = `raw_value × lock_strength` |
| `"lock_strength"` | `float` | H-line phase lock ∈ [0, 1] |
| `"layer_c"` | `str` | Integrity hash |

---

#### `verify(receipt) → dict`

Verify a `SolarReceipt` against physical constants.

```python
def verify(receipt: SolarReceipt) -> Dict[str, Any]
```

**Performs three independent checks:**

| Check | Condition | What it catches |
|---|---|---|
| Tamper check | `receipt.is_valid()` | Any modification to receipt fields after write |
| K_EGS check | `abs(receipt.k_egs − K_EGS) < 1e-8` | Fraudulent K_EGS values |
| Phase check | `abs(receipt.phase_bias − gateway_filter(receipt.solar_wind)["phase_bias_rad"]) < 1e-6` | Inconsistent solar wind / phase pairs |

**Returns:**

| Key | Type | Description |
|---|---|---|
| `"tamper_evident"` | `bool` | True = no tampering detected |
| `"kegs_valid"` | `bool` | True = K_EGS matches universal constant |
| `"phase_consistent"` | `bool` | True = phase matches solar wind |
| `"overall"` | `bool` | True iff all three checks pass |
| `"details"` | `dict` | Numeric details of each check |

---

#### `four_pillar_lock(solar_wind) → FourPillarLock`

Generate a Four-Pillar authentication key.

```python
def four_pillar_lock(solar_wind: float = None) -> FourPillarLock
```

The lock key changes with every new solar wind or Crab tick. Keys generated at the same (solar_wind, tick) are identical.

---

#### `generate(prompt, length, solar_wind) → GenerationResult`

Generate a holographic character sequence.

```python
def generate(
    prompt:     str   = "EGS",
    length:     int   = 24,
    solar_wind: float = None,
) -> GenerationResult
```

Delegates to `EGSHolographicLM.generate()`. See Chapter 9 for full details.

---

#### `ground(claim, solar_wind) → dict`

Verify whether a claim is consistent with EGS physical constants.

```python
def ground(
    claim:      Any,
    solar_wind: float = None,
) -> Dict[str, Any]
```

**Grounding logic:**

- **Numeric claim:** `abs(claim % 1.0 − (K_EGS % 1.0)) < 0.15` — within 15% of K_EGS fractional part
- **String claim:** first 2 hex chars of `SHA-256(str(claim))` must match first 2 hex chars of `SHA-256(str(K_EGS))`

**Returns:**

| Key | Type | Description |
|---|---|---|
| `"grounded"` | `bool` | True if claim is consistent with EGS physics |
| `"claim_type"` | `str` | `"numeric"` or `"string"` |
| `"ref_val"` | `float` | Reference value compared against |
| `"verdict"` | `str` | SHA-256[:16] of the grounding decision |
| `"solar_wind"` | `float` | Solar wind used |

**Accumulated receipts:** All `write()` calls accumulate `SolarReceipt` objects internally. Call `agent._receipts` to access the audit trail (a list of `SolarReceipt` objects).

---

## Chapter 9: EGS Holographic Generative Model Reference

**Module:** `egs_genai`  
**File:** `egs_genai.py`

### 9.1 Vocabulary

```python
VOCAB: List[str] = list("ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 .-:")
VOCAB_SIZE: int  = 40
```

The model generates characters exclusively from this 40-character vocabulary. Token ID = index into `VOCAB`.

### 9.2 `TokenStep` Dataclass

```python
@dataclass
class TokenStep:
    step:        int      # generation step index (0-based)
    context_key: int      # Moon page used as weight index (0–100)
    fractal_val: float    # predict_next_solar_hydrogen_state result ∈ [0, 1)
    token_id:    int      # index into VOCAB
    char:        str      # the generated character
    layer_c:     str      # SHA-256[:16] audit hash for this step
```

### 9.3 `GenerationResult` Dataclass

```python
@dataclass
class GenerationResult:
    prompt:     str           # input prompt string
    generated:  str           # characters produced after the prompt
    full_text:  str           # prompt + generated
    solar_wind: float         # km/s — entropy source used
    fdtx_flux:  float         # FDTD transmitted flux — physical anchor receipt
    verdict:    str           # InterferenceVerdict from the anchor SYS_EXEC
    exec_hash:  str           # Layer-C hash from the anchor SYS_EXEC syscall
    steps:      List[TokenStep]
```

**Properties:**

| Property | Type | Description |
|---|---|---|
| `.is_anchored` | `bool` | `True` iff `fdtx_flux > 0.0` |
| `.full_audit` | `list[dict]` | Step-by-step audit trail with layer-C hashes |

### 9.4 `EGSHolographicLM` Class

```python
class EGSHolographicLM:
    def __init__(self, kernel: EGSKernel) -> None
```

**Constructor:** Requires a booted `EGSKernel`. The kernel must have valid `_master` values (set during `boot()`).

---

#### `generate(prompt, length, solar_wind, exec_pid) → GenerationResult`

Generate an autoregressive character sequence.

```python
def generate(
    prompt:     str   = "EGS",
    length:     int   = 24,
    solar_wind: float = DEFAULT_SOLAR_WIND_KM_S,
    exec_pid:   int   = 1,
) -> GenerationResult
```

**Parameters:**

| Parameter | Type | Default | Description |
|---|---|---|---|
| `prompt` | `str` | `"EGS"` | Seed context for generation |
| `length` | `int` | `24` | Number of characters to generate |
| `solar_wind` | `float` | `551.7` | Entropy source (km/s) |
| `exec_pid` | `int` | `1` | PID for the FDTD anchor `SYS_EXEC` |

**Generation algorithm (per token):**

```
context_key = K_EGS-weighted polynomial hash of last 4 chars, mod 101
fractal_val = predict_next_solar_hydrogen_state(master, solar_wind, context_key)
token_id    = floor(fractal_val × VOCAB_SIZE)
char        = VOCAB[token_id]
layer_c     = SHA-256[:16]({step, context_key, fractal_val, token_id})
```

**Physical anchor:** After the full sequence, one `SYS_EXEC` is called with `exec_pid`. The transmitted FDTD flux is stored in `GenerationResult.fdtx_flux`. The generation is not anchored until `fdtx_flux > 0`.

**Determinism:** Identical `(prompt, length, solar_wind)` always produces identical output — the fractal master is deterministic and solar wind maps deterministically to phase. Different solar winds produce different sequences (see T10 in the test suite).

**Example:**

```python
from egs_os import EGSKernel
from egs_genai import EGSHolographicLM

k = EGSKernel(fdtd_resolution=10, fdtd_until=40.0)
k.boot()

lm = EGSHolographicLM(k)
result = lm.generate(prompt="EGS", length=16, solar_wind=551.7)

print(result.generated)    # e.g., "6.TJ.TTT7.7..TJ."
print(result.fdtx_flux)    # e.g., 0.001305 (live FDTD receipt)
print(result.is_anchored)  # True
```

---

## Chapter 10: Programming Patterns and Examples

### 10.1 Pattern: Minimum Viable Kernel

```python
from egs_os import EGSKernel, SYS

# Instantiate and boot
k = EGSKernel(fdtd_resolution=10, fdtd_until=35.0)
r = k.boot()
assert r.ok, f"Boot failed: {r.data}"

print(f"Boot OK — master hash: {r.data['boot_image_hash']}")
print(f"Moon pages: {r.data['moon_pages']}")
```

### 10.2 Pattern: Process Lifecycle

```python
from egs_os import EGSKernel, INIT_PID

k = EGSKernel()
k.boot()

# Fork a worker
r_fork = k.fork(INIT_PID, name="my-worker")
assert r_fork.ok
worker_pid = int(r_fork.retval)

# Write a value to the worker's Moon page
r_write = k.write(worker_pid, value=0.7423)
assert r_write.ok
print(f"Wrote to page {int(r_write.retval)}: hash={r_write.data['value_hash']}")

# Execute the worker — runs FDTD
r_exec = k.exec(worker_pid)
assert r_exec.ok
print(f"FDTD flux: {r_exec.retval:.6e}")
print(f"Verdict:   {r_exec.data['verdict']}")

# Read back from the page
r_read = k.read(worker_pid)
print(f"Read: {r_read.retval:.6f}  lock={r_read.data['lock_strength']:.4f}")

# Terminate
r_exit = k.exit(worker_pid)
assert r_exit.ok
```

### 10.3 Pattern: Four-Layer Stack (Full Pipeline)

```python
from egs_os import EGSKernel
from hhaaios import HHAAIOSAgent

# Layer 1 + 2: FDTD + OS
k = EGSKernel(fdtd_resolution=10, fdtd_until=40.0)
k.boot()

# Layer 3: HHAAIOS API
agent = HHAAIOSAgent(k, solar_wind=551.7)
agent.init_agents()

# Write arbitrary data to holographic memory
payload = {"mission": "EGS", "epoch": k._epoch, "status": "ACTIVE"}
receipt = agent.write(payload)
print(f"Receipt — addr:{receipt.address}  hash:{receipt.data_hash}"
      f"  valid:{receipt.is_valid()}")

# Read it back
readout = agent.read(receipt.address)
print(f"Read — value:{readout['value']:.6f}  lock:{readout['lock_strength']:.4f}")

# Verify the receipt (tamper check + K_EGS check + phase check)
vfy = agent.verify(receipt)
print(f"Verify — overall:{vfy['overall']}  tamper:{vfy['tamper_evident']}")

# Generate a holographic sequence
result = agent.generate(prompt="EGS", length=12)
print(f"Generated: '{result.generated}'  flux:{result.fdtx_flux:.6f}")

# Four-Pillar Lock
lock = agent.four_pillar_lock()
print(f"Lock key: {lock.lock_key[:16]}…  locked:{lock.locked}")
```

### 10.4 Pattern: Solar Flare Interrupt and Epoch Handling

```python
from egs_os import EGSKernel, INIT_PID
import math

k = EGSKernel()
k.boot()

r_fork = k.fork(INIT_PID, name="sensor")
spid   = int(r_fork.retval)
phase_before = k._processes[spid].phase_rad

# Raise a flare interrupt (sunspot index in degrees)
r_flare = k.flare(sunspot_index=45.0)
assert r_flare.ok
assert r_flare.data["new_epoch"] == 1

phase_after = k._processes[spid].phase_rad
delta = abs(phase_after - phase_before)
print(f"Phase flip: {delta:.4f} rad (expected π = {math.pi:.4f})")
print(f"Epoch bumped to: {k._epoch}")
```

### 10.5 Pattern: Tamper Detection

```python
from egs_os import EGSKernel
from hhaaios import HHAAIOSAgent

k = EGSKernel()
k.boot()

agent = HHAAIOSAgent(k)
agent.init_agents()

receipt = agent.write("sensitive-data-001")
assert receipt.is_valid()   # good

# Simulate tampering — modify the data_hash field
import dataclasses
tampered = dataclasses.replace(receipt, data_hash="deadbeef12345678")
assert not tampered.is_valid()   # tamper detected

# Full verification
vfy_good    = agent.verify(receipt)
vfy_tampered = agent.verify(tampered)
print(f"Original receipt valid:  {vfy_good['overall']}")       # True
print(f"Tampered receipt valid:  {vfy_tampered['overall']}")   # False
```

### 10.6 Pattern: Batch Scheduler

```python
from egs_os import EGSKernel, INIT_PID

k = EGSKernel()
k.boot()

# Fork 5 workers
worker_pids = []
for i in range(5):
    r = k.fork(INIT_PID, name=f"batch-{i}")
    assert r.ok
    worker_pids.append(int(r.retval))

# Schedule all workers in one pass
results = k.schedule(n_ticks=len(worker_pids) + 2)

for r in results:
    print(f"PID {r.pid:2d}  flux={r.retval:.4e}  verdict={r.data['verdict'][:4]}")

# Exit all workers
for pid in worker_pids:
    k.exit(pid)

# Check memory map
mm = k.memmap()
owned = [p for p in mm if not p["free"]]
print(f"Owned pages after cleanup: {len(owned)}")
```

### 10.7 Pattern: Continuous Audit Trail

```python
from egs_os import EGSKernel
from hhaaios import HHAAIOSAgent

k = EGSKernel()
k.boot()

agent = HHAAIOSAgent(k)
agent.init_agents()

# Write multiple records
for i in range(5):
    agent.write({"record": i, "data": f"entry-{i:04d}"})

# Verify all accumulated receipts
all_valid = all(r.is_valid() for r in agent._receipts)
print(f"Audit trail: {len(agent._receipts)} receipts, all_valid={all_valid}")

# Dump full audit trail
for r in agent._receipts:
    d = r.to_dict()
    print(f"  addr={d['address']:3d}  hash={d['data_hash']}  "
          f"tick={d['crab_tick']}  valid={d['valid']}")
```

### 10.8 Pattern: Layer 4 Integration (LLM Tool Call)

The following illustrates the API contract expected by a Layer 4 LLM integration.

```python
# This is what a Layer 4 tool wrapper would look like
import json
from egs_os import EGSKernel
from hhaaios import HHAAIOSAgent

# ----- Infrastructure setup (done once per session) -----
_kernel = EGSKernel(fdtd_resolution=10, fdtd_until=40.0)
_kernel.boot()
_agent = HHAAIOSAgent(_kernel, solar_wind=551.7)
_agent.init_agents()

# ----- Tool functions callable by the LLM -----

def egs_write(data: dict) -> str:
    """Write data to holographic memory. Returns receipt JSON."""
    receipt = _agent.write(data)
    return json.dumps(receipt.to_dict())

def egs_read(address: int) -> str:
    """Read from holographic memory. Returns value JSON."""
    return json.dumps(_agent.read(address))

def egs_verify(receipt_json: str) -> str:
    """Verify a SolarReceipt. Returns verification JSON."""
    from hhaaios import SolarReceipt
    d = json.loads(receipt_json)
    # Reconstruct receipt from dict (simplified)
    receipt = SolarReceipt(**{k: v for k, v in d.items()
                               if k != "valid"})
    return json.dumps(_agent.verify(receipt))

def egs_generate(prompt: str, length: int = 16) -> str:
    """Generate a holographic sequence. Returns GenerationResult JSON."""
    result = _agent.generate(prompt=prompt, length=length)
    return json.dumps({
        "generated": result.generated,
        "flux":      result.fdtx_flux,
        "anchored":  result.is_anchored,
        "verdict":   result.verdict,
    })

def egs_lock() -> str:
    """Return a Four-Pillar Lock key."""
    lock = _agent.four_pillar_lock()
    return json.dumps(lock.to_dict())
```

---

## Chapter 11: Test Suite Reference

### 11.1 Suite Architecture

Three test suites cover the entire four-layer stack:

| Suite | File | Tests | Scope |
|---|---|---|---|
| Suite 1 | `egs_gateway_hifi_test.py` | 5 | FDTD physics — five pillars |
| Suite 2 | `egs_os_test.py` | 14 | EGS OS kernel — all syscalls |
| Suite 3 | `hhaaios_test.py` | 15 | HHAAIOS API + EGS GenAI |

All tests return structured dictionaries and exit with code `0` (all pass) or `1` (any failure).

### 11.2 Suite 1 — Five-Pillar FDTD Test

**File:** `egs_gateway_hifi_test.py`

```powershell
python egs_gateway_hifi_test.py --resolution 12 --until 50
python egs_gateway_hifi_test.py --resolution 12 --until 50 --json
```

| Pillar | ID | What Is Verified |
|---|---|---|
| P1 | `P1_HYDROGEN_LINE_PHASE_LOCK` | K_EGS fidelity = 1.0000; phase lock strength ≈ 0.999; FDTD flux > 0 |
| P2 | `P2_EGS_FRACTAL_CONSTANT_GATE` | K_EGS scale-invariant across 8/16/32 nm voxel orders; deviation < 1e-6 |
| P3 | `P3_180_PHASE_MIGRATION` | v_π ≈ 478.6 km/s produces δ ≈ π ± 0.5 rad; distinct InterferenceVerdict |
| P4 | `P4_SILICA_VOXEL_PROCESSOR` | 5 phase-offset FDTD runs; Bragg 4-of-5 recovery ≥ 80%; Nyquist satisfied |
| P5 | `P5_FRACTAL_MASTER_PREDICTION` | Deterministic AR14409 burn; 3 distinct wind predictions; RMS < 2.0 |

**Return type:** `TestRecord` dataclass containing a list of `PillarResult` objects.

**`PillarResult` fields:**

| Field | Type | Description |
|---|---|---|
| `pillar` | `str` | Pillar ID string |
| `pass_` | `bool` | Pass/fail |
| `measured` | `dict` | Actual measured values |
| `expected` | `dict` | Expected values / tolerance spec |
| `verdict` | `str` | Human-readable verdict string |
| `hash_` | `str` | SHA-256[:16] layer-C hash |

### 11.3 Suite 2 — EGS OS Kernel Test

**File:** `egs_os_test.py`

```powershell
python egs_os_test.py
python egs_os_test.py --resolution 10 --until 35 --json
```

Tests are stateful — each test function receives the same `EGSKernel` instance, allowing later tests to verify cumulative state:

| Test | ID | Verifies |
|---|---|---|
| T01 | `T01_BOOT` | Kernel boots; 101 pages pre-loaded; PID 0+1 alive |
| T02 | `T02_CLOCK` | Crab tick counter advances; crab_hz = 29.94 |
| T03 | `T03_PS` | Process table contains PID 0 and PID 1; epoch = 0 |
| T04 | `T04_MALLOC_FREE` | `malloc` returns address ≥ 0; `free` sets `page.free = True` |
| T05 | `T05_WRITE` | H-line bus write succeeds; value stored; SHA-256 hash present |
| T06 | `T06_READ` | Phase-locked read returns value × lock_strength |
| T07 | `T07_FORK` | Child PID in table; parent_pid = INIT_PID; state = READY |
| T08 | `T08_EXEC` | FDTD flux finite; verdict valid; page_hash present |
| T09 | `T09_SCHEDULER` | SOL-0 scheduler executes ≥ 1 READY process |
| T10 | `T10_FLARE` | Epoch bumps to 1; ≥ 2 PIDs phase-flipped; master_rms > 0 |
| T11 | `T11_EXIT` | Exited process = ZOMBIE; Moon page freed |
| T12 | `T12_DMESG` | ≥ 10 log entries; all carry layer-C hashes |
| T13 | `T13_MEMMAP` | 101 pages total; ≥ 2 owned; all hashes length 0 or 16 |
| T14 | `T14_MULTI_PROCESS` | Fork 3 workers; schedule runs them all; exit all |

### 11.4 Suite 3 — HHAAIOS + EGS GenAI Test

**File:** `hhaaios_test.py`

```powershell
python hhaaios_test.py --resolution 10 --until 40
python hhaaios_test.py --resolution 10 --until 40 --json
```

| Test | ID | Verifies |
|---|---|---|
| T01 | `T01_AGENT_INIT` | Three agent PIDs spawned; LM instantiated |
| T02 | `T02_RECEIPT_WRITE` | SolarReceipt structure valid; is_valid() = True |
| T03 | `T03_PHASE_LOCKED_READ` | H-line bus read returns lock_strength ∈ [0, 1] |
| T04 | `T04_RECEIPT_VERIFY_VALID` | All three verify checks pass on valid receipt |
| T05 | `T05_TAMPER_DETECTION` | Modified receipt fails is_valid() and all verify checks |
| T06 | `T06_FOUR_PILLAR_LOCK` | Lock key is 64-char hex; all four pillars present |
| T07 | `T07_LOCK_DETERMINISM` | Same inputs produce same lock key |
| T08 | `T08_HOLOGRAPHIC_GENERATION` | Generated sequence: `len() == length`; flux > 0; anchored |
| T09 | `T09_GENERATION_DETERMINISM` | Identical (prompt, wind) → identical generated text |
| T10 | `T10_GENERATION_DIVERSITY` | Different solar winds produce distinct sequences |
| T11 | `T11_GROUNDING_NUMERIC` | Numeric claim near K_EGS fractional part is grounded |
| T12 | `T12_GROUNDING_STRING` | Arbitrary string claim is correctly rejected |
| T13 | `T13_FULL_STACK_PIPELINE` | Write → generate → verify → ground: four layers confirmed |
| T14 | `T14_MULTI_AGENT_CONCURRENT` | Three parallel agent instances all succeed |
| T15 | `T15_AUDIT_TRAIL` | All accumulated receipts pass `is_valid()` |

### 11.5 Running All Tests — CI Integration

**GitHub Actions workflow** (`.github/workflows/egs-tests.yml`) runs all three suites on every push to `main`:

```yaml
- name: "[Suite 1] Five-Pillar FDTD"
  run: python egs_gateway_hifi_test.py --resolution 12 --until 50

- name: "[Suite 2] EGS OS Kernel"
  run: python egs_os_test.py --resolution 10 --until 35

- name: "[Suite 3] HHAAIOS + EGS GenAI"
  run: python hhaaios_test.py --resolution 10 --until 40
```

JSON artefacts are uploaded with 90-day retention for downstream verification.

---

## Chapter 12: Layer-C Integrity System

### 12.1 Overview

Every object in the EGS Gateway that produces a side effect carries a **Layer-C SHA-256 fingerprint**. This is the integrity backbone of the system — no value leaves without a verifiable hash.

### 12.2 Hash Computation

All Layer-C hashes are computed as:

```python
payload = json.dumps(<canonical_dict>, sort_keys=True, default=str).encode()
layer_c = hashlib.sha256(payload).hexdigest()[:16]
```

The first 16 hex characters (64 bits) are used. The full SHA-256 is computed — only the display is truncated.

### 12.3 Where Layer-C Hashes Are Generated

| Location | When Generated | What Is Hashed |
|---|---|---|
| `SyscallResult.__post_init__` | Every syscall completion | `{syscall_int, pid, retval, data}` |
| `MoonPage.write()` | Every page write | `{addr, val}` |
| `SolarReceipt.__post_init__` | Every HHAAIOS write | `{address, data_hash, solar_wind, phase_bias, crab_tick, k_egs, epoch}` |
| `TokenStep.layer_c` | Every generation token | `{step, context_key, fractal_val, token_id}` |
| `PillarResult.hash_` | Every FDTD pillar run | `{pillar, measured}` |

### 12.4 Offline Verification

Any `SolarReceipt` can be verified without re-running the simulation:

```python
import hashlib, json

def verify_receipt_offline(receipt_dict: dict) -> bool:
    """Recompute layer_c from receipt fields and compare."""
    payload = json.dumps({
        "address":    receipt_dict["address"],
        "data_hash":  receipt_dict["data_hash"],
        "solar_wind": receipt_dict["solar_wind"],
        "phase_bias": round(receipt_dict["phase_bias"], 8),
        "crab_tick":  receipt_dict["crab_tick"],
        "k_egs":      round(receipt_dict["k_egs"], 10),
        "epoch":      receipt_dict["epoch"],
    }, sort_keys=True).encode()
    expected_layer_c = hashlib.sha256(payload).hexdigest()[:16]
    return expected_layer_c == receipt_dict["layer_c"]
```

### 12.5 Honesty Boundary

Layer-C hashes are **run-instance deterministic**, not universally constant. The FDTD flux values depend on:

- NumPy version (FMA instruction fusion, sum order)
- Platform (x86-64 vs ARM, FP mode)
- FDTD resolution and until parameters

Two runs with identical parameters on the same machine will produce identical hashes. Runs on different machines may differ at the last 1–2 significant digits of flux. The hash will differ, but the PASS/FAIL verdict (based on finite-and-positive flux, correct InterferenceVerdict, etc.) will be identical.

---

## Chapter 13: Error Reference

### 13.1 Kernel Errors

All kernel errors are returned via `SyscallResult.ok = False` and `SyscallResult.data["error"]`. The kernel never raises exceptions in normal operation.

| Error String | Syscall | Cause | Resolution |
|---|---|---|---|
| `"kernel not booted"` | Any | `syscall()` called before `boot()` | Call `kernel.boot()` first |
| `"no such pid"` | All process ops | PID not in `_processes` | Verify PID exists via `ps()` |
| `"process table full"` | `FORK` | 64 processes already running | `exit()` zombie processes |
| `"out of Moon pages"` | `FORK`, `MALLOC` | All 101 pages allocated | `free()` unused pages |
| `"bad address"` | `READ`, `WRITE` | Address < 0 or ≥ 101 | Check `moon_page` field of PCB |
| `"page owned by another process"` | `WRITE` | Attempted write to another process's page | Write only to owned pages |
| `"cannot free page"` | `FREE` | Address out of range | Valid range is 0–100 |
| `"unknown syscall"` | `syscall()` | Invalid `SYS` value | Use `SYS` enum |

### 13.2 HHAAIOS Errors

| Exception | Method | Cause | Resolution |
|---|---|---|---|
| `RuntimeError("Boot the EGSKernel before calling init_agents()")` | `init_agents()` | Kernel not booted | Boot kernel first |
| `RuntimeError("Writer fork failed: ...")` | `init_agents()` | Process table full or no pages | Reduce active processes |
| `RuntimeError("SYS_WRITE failed: ...")` | `write()` | Kernel write error | Check kernel state via `ps()` |
| `RuntimeError("Agents not initialised...")` | Any method | `init_agents()` not called | Call `init_agents()` after boot |

### 13.3 Gateway Filter Errors

| Exception | Function | Cause | Resolution |
|---|---|---|---|
| `ValueError("solar_wind_speed_km_s must be positive")` | `gateway_filter()` | `solar_wind <= 0` | Use positive solar wind value |
| `ValueError("length must be >= 1")` | `burn_master_fractal()` | `length < 1` | Use length ≥ 1 |
| `ValueError("master_pattern must be non-empty")` | `predict_next_...()` | Empty sequence | Use master from `burn_master_fractal()` |
| `ValueError("index out of range...")` | `predict_next_...()` | Index ≥ len(master) | Check index bounds |

---

## Chapter 14: Troubleshooting

### 14.1 Installation Issues

**Problem:** `ModuleNotFoundError: No module named 'numpy'`

```powershell
python -m pip install numpy
```

**Problem:** `python` not found / Microsoft Store redirect

```powershell
# Install Python 3.12 via winget
winget install Python.Python.3.12
# Then use the full path or restart the terminal to pick up the new PATH
```

**Problem:** `UnicodeEncodeError: 'charmap' codec can't encode character`

This occurs on Windows when the console code page does not support Unicode symbols (✓, ✗, ✅). Fix:

```powershell
$env:PYTHONIOENCODING = "utf-8"
chcp 65001
python -X utf8 egs_os_test.py
```

### 14.2 FDTD Issues

**Problem:** Flux is always 0 or NaN

- Check that `resolution` ≥ 8 (coarser grids cannot resolve the source)
- Check that `until` ≥ 30 (source must propagate through the slab)
- Check that the source frequency (1.0) and slab geometry (half-width 1.5 units) are compatible

**Problem:** FDTD runs are very slow

- Reduce `resolution` (halving resolution ≈ 4× speedup in 2D)
- Reduce `until` — most flux stabilises by t = 40
- Default for OS tests is `resolution=10, until=35` — adequate for all syscall verdicts

**Problem:** Test P2 fails with "scale invariance broken"

- This indicates `EGS_FRACTAL_NOMINAL` is set to an incorrect value
- The correct value is `PHI × (1030.0 / 656.28) ≈ 2.5436`
- Verify the constant definition in `egs_gateway_hifi_test.py` line ~74

### 14.3 OS Kernel Issues

**Problem:** `T04_MALLOC_FREE` fails — `alloc_ok=False, address=-1`

- All Moon pages are owned by kernel — this is the boot-ownership bug
- Ensure `egs_os.py boot()` uses `write_value_only()` approach (current version)
- Do **not** call `page.write(val, KERNEL_PID)` in boot; this claims all pages

**Problem:** `T11_EXIT` fails — `KeyError: -1`

- A process has `moon_page = -1`, meaning `_alloc_page()` returned −1 during fork
- Root cause: the flare `_sys_flare()` re-claimed all pages with `KERNEL_PID`
- Ensure `_sys_flare()` uses `write_value_only()` not `page.write(val, KERNEL_PID)`

**Problem:** `T14_MULTI_PROCESS` fails — `workers_ran=False`

- `n_ticks` is too small; earlier tests accumulate READY processes
- Use `n_ticks ≥ 15` in T14 to ensure new workers are reached in the scheduler queue

### 14.4 HHAAIOS Issues

**Problem:** Receipt fails verification after deserialization

- Float serialization precision: `phase_bias` and `k_egs` must be rounded to the same precision as `_compute_layer_c()`
- Use `to_dict()` / `json.dumps()` round-trip rather than manual field extraction

**Problem:** Generation output differs between runs

- Verify that `solar_wind` and `prompt` are identical between runs
- The kernel tick counter (`_tick`) does **not** affect generation — only solar wind and prompt affect output
- Check that `kernel._master` is identical (boot from the same seed)

---

## Appendix A — Complete Constant Quick Reference

### A.1 `egs_gateway` Module

| Symbol | Value | Unit | Description |
|---|---|---|---|
| `LAMBDA_READER_NM` | `1030.0` | nm | Nd:glass write laser |
| `LAMBDA_H_ALPHA_NM` | `656.28` | nm | Hydrogen Balmer H-alpha optical anchor |
| `REFERENCE_SOLAR_WIND_KM_S` | `400.0` | km/s | Phase normalisation reference |
| `DEFAULT_SOLAR_WIND_KM_S` | `551.7` | km/s | Nominal live solar wind (Seed) |
| `PHI` | `1.6180339887…` | — | Golden ratio |
| `K_EGS` | `2.5436062…` | — | EGS Fractal Constant |
| `EGS_FRACTAL_CONSTANT` | `2.5436062…` | — | Alias for `K_EGS` |

### A.2 `egs_os` Module

| Symbol | Value | Unit | Description |
|---|---|---|---|
| `N_MOON_PAGES` | `101` | pages | Holographic memory pages |
| `CRAB_HZ` | `29.94` | Hz | Crab pulsar clock |
| `CRAB_TICK_S` | `≈0.03340` | s | One Crab tick duration |
| `OS_SEED` | `14409` | — | AR14409 boot seed |
| `OS_MASTER_LEN` | `101` | values | Fractal master length |
| `MAX_PROCESSES` | `64` | PIDs | Maximum concurrent processes |
| `KERNEL_PID` | `0` | PID | Reserved kernel PID |
| `INIT_PID` | `1` | PID | Reserved init PID |

### A.3 `egs_genai` Module

| Symbol | Value | Description |
|---|---|---|
| `VOCAB` | `list[str]` len=40 | `A-Z`, `0-9`, `space`, `.`, `-`, `:` |
| `VOCAB_SIZE` | `40` | Number of generatable characters |

### A.4 Derived Constants

| Symbol | Formula | Value | Description |
|---|---|---|---|
| λ_HI | c / 1420.405751 MHz | 21.106 cm | H I 21 cm rest wavelength |
| φ_pid(n) | n × 2π / 101 | varies | Phase slot for PID n |
| v_ref | 400.0 km/s | — | Solar wind reference |
| r_logistic | 3.2 + (K_EGS mod 1.0) | ≈3.7436 | Logistic map rate (chaotic-stable) |

---

## Appendix B — Syscall Quick Reference

| # | SYS | Signature | retval | Notes |
|---|---|---|---|---|
| 0 | `READ` | `read(pid, address=-1)` | `value × lock_strength` | H-line bus read |
| 1 | `WRITE` | `write(pid, value=0.0, address=-1)` | address written | SHA-256 receipt |
| 2 | `FORK` | `fork(pid, name="")` | child_pid | Allocates Moon page |
| 3 | `EXEC` | `exec(pid)` | FDTD flux | Runs silica_fdtd |
| 4 | `EXIT` | `exit(pid, exit_code=0)` | exit_code | page freed; ZOMBIE |
| 5 | `PS` | `ps()` | n_procs | Process table snapshot |
| 6 | `MALLOC` | `malloc(pid)` | address or -1 | Allocate free page |
| 7 | `FREE` | `free(pid, address)` | 0 or -1 | Release page |
| 8 | `CLOCK` | `clock()` | tick_count | Advances tick by 1 |
| 9 | `FLARE` | `flare(sunspot_index=0.0)` | new_epoch | 180° phase flip |
| 10 | `REBOOT` | `syscall(SYS.REBOOT, 0, solar_wind=...)` | master_len | Re-burns master |

---

## Appendix C — File Inventory

```
Microsoft-Silica-EGS-Gateway-Simulation/
│
├── Core Physics
│   ├── egs_gateway.py              Physical constants, gateway_filter,
│   │                               holographic_gate, burn_master_fractal,
│   │                               predict_next_solar_hydrogen_state
│   ├── meep_gateway.py             FDTD backend selector and run wrapper
│   └── silica_fdtd/
│       ├── __init__.py             Meep-compatible public API
│       └── _core.py               2D TM Yee FDTD engine (pure Python/NumPy)
│
├── Operating System
│   ├── egs_os.py                   EGSKernel: 11 syscalls, PCB, MoonPage,
│   │                               SyscallResult, SYS, ProcessState
│   └── egs_os_test.py              Suite 2: 14 OS operation tests
│
├── Layer 3 API and Generative AI
│   ├── hhaaios.py                  HHAAIOSAgent, SolarReceipt, FourPillarLock
│   ├── egs_genai.py                EGSHolographicLM, GenerationResult, TokenStep
│   └── hhaaios_test.py             Suite 3: 15 HHAAIOS + GenAI tests
│
├── Test Suites
│   ├── egs_gateway_hifi_test.py    Suite 1: five-pillar FDTD test
│   └── testing_suite.py           Unit tests for gateway logic
│
├── Documentation
│   ├── EGS_GATEWAY_PAPER.md        Full peer-review ready whitepaper
│   ├── EGS_SYSTEM_PROGRAMMER_GUIDE.md  This document
│   ├── README.md                   Project overview and quick start
│   └── egs_architecture_canvas.html  Interactive architecture canvas (HTML)
│
├── CI / Environment
│   ├── .github/
│   │   └── workflows/
│   │       └── egs-tests.yml      GitHub Actions: runs all 3 suites on push
│   ├── environment.yml             Conda env for optional MIT Meep backend
│   ├── .gitignore                  Excludes __pycache__, *.pyc, JSON results
│   └── Seed                       Original EGS Gateway specification (20 lines)
```

---

## Appendix D — Glossary

| Term | Definition |
|---|---|
| **AR14409** | Solar active region 14409; the seed value used for the EGS boot master fractal |
| **Bragg reconstruction** | Recovery of holographic data from a subset of interference facets; EGS uses 4-of-5 |
| **Crab pulsar** | Neutron star remnant of SN 1054; rotates at ~29.94 Hz; used as the EGS OS clock |
| **DFT monitor** | Discrete Fourier transform flux monitor; integrates Poynting vector over a surface |
| **FDTD** | Finite-difference time-domain; numerical method for solving Maxwell's equations on a grid |
| **Four-Pillar Lock** | Authentication key derived from K_EGS, solar phase bias, Crab tick, and AR14409 master hash |
| **Gateway Key** | Synonym for K_EGS, the EGS Fractal Constant |
| **H I hyperfine** | 21 cm hydrogen line at 1420.405751 MHz; universal spectral anchor |
| **H-line bus** | Conceptual data bus addressed by the H I rest frequency; implemented as Moon page I/O |
| **Holographic gate** | FDTD interference logic: constructive = True, destructive = False |
| **InterferenceVerdict** | Enum: CONSTRUCTIVE_AR14409 (True), DESTRUCTIVE_H_PHASE_FLIP (False), MIXED |
| **K_EGS** | The EGS Fractal Constant = φ × (λ_laser / λ_H-alpha) ≈ 2.5436… |
| **Layer 0** | The Cosmos — physical constants that drive the entire stack |
| **Layer 1** | Silica Voxel Processor — `silica_fdtd` FDTD engine |
| **Layer 2** | EGS OS Kernel — `egs_os.py` |
| **Layer 3** | HHAAIOS API — `hhaaios.py`, `egs_genai.py` |
| **Layer 4** | LLM / External AI — any system calling into Layer 3 |
| **Layer-C hash** | SHA-256[:16] fingerprint carried by every syscall result and write receipt |
| **Lock strength** | `|cos(phase_bias_rad)|` — measures H-line phase coupling quality; 1.0 = perfect lock |
| **Moon page** | One slot in the 101-element holographic memory map; analogous to a physical memory page |
| **N_MOON_PAGES** | 101 — the count of Jupiter's moons used as the storage array cardinality |
| **NSPFRNP** | Natural Systems Protocol Fractal Recursive Nested Protocol — the operational philosophy |
| **PCB** | Process Control Block — OS data structure describing one process |
| **Phase bias** | Phase offset injected into the FDTD source proportional to solar wind speed |
| **PML** | Perfectly matched layer — FDTD absorbing boundary that eliminates reflections |
| **SolarReceipt** | Cryptographic proof of a write anchored to 7 physical observables |
| **SOL-0** | The Sun-server compute plane; implemented as the EGS OS scheduler |
| **Sovereign Lattice** | The four-layer stack operating as an integrated, self-sovereign computing system |
| **TM polarisation** | Transverse-magnetic — field configuration used in the 2D FDTD; Ez is the primary field |
| **Voxel** | A volumetric pixel in a fused-silica medium; birefringent nanograting written by a laser pulse |
| **Yee grid** | Staggered finite-difference grid for FDTD; E and H fields offset by half a cell in space and time |
| **Zombie** | Process state after `SYS_EXIT`; PCB retained for audit but Moon page freed |

---

## Document Revision History

| Revision | Date | Author | Changes |
|---|---|---|---|
| 1.0.0 | April 2026 | EGS Gateway Team | Initial release. Complete API reference for all four layers. Verified against live Python 3.12.10 execution (34/34 tests PASS, 31.77 s). |

---

**NSPFRNP · Seed:Edge · EGS Fractal Constant · BBHE · SING 9 → ∞⁹**

_End of EGS Gateway System Programmer's Guide_
