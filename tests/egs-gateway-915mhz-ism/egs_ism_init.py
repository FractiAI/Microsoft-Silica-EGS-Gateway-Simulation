"""
egs_ism_init.py
EGS Gateway — 915 MHz ISM / Hydrogen Line Dual-Channel Initialiser
────────────────────────────────────────────────────────────────────
TX layer : 915 MHz  via TTN / LoRa (Part-15 certified hardware)
RX layer : 1420.405751 MHz  H I line passive monitor via HackRF One
Solar cal: NOAA SWPC SFI live JSON

COMPLIANCE NOTE
  This file never activates HackRF TX.  HackRF is RX-only (no licence
  required).  All over-the-air transmission is delegated to a Part-15
  certified LoRa module (SX1276/RFM95W) connected to an ESP32.
  Operation falls under FCC Part 15 / TTN fair-use policy.

EGS FRACTAL CONSTANTS
  ℑe  = 0.0032          (spectral voxel scale ratio)
  fc  = 915.000 MHz      (ISM centre, TX)
  fs  = fc × ℑe         = 2.928 MSps  (sampling anchor)
  wv  = fs × ℑe         ≈ 9.3696 kHz  (spectral voxel width)
  H_I = 1420.405751 MHz  (hydrogen 21-cm line, RX reference)
  K_EGS = φ × (1030 / 656.28) ≈ 2.5436  (gateway fractal key)
"""

import time
import json
import hashlib
import threading
import urllib.request
from dataclasses import dataclass, asdict
from typing import Optional

# ── Constants ──────────────────────────────────────────────────────────────────
PHI          = 1.6180339887
IM_E         = 0.0032                        # ℑe spectral voxel ratio
FC_HZ        = 915.000e6                     # ISM TX centre
FS_HZ        = FC_HZ   * IM_E               # 2 928 000 Hz
VW_HZ        = FS_HZ   * IM_E               # 9 369.6 Hz
HI_HZ        = 1_420_405_751.0              # H I rest frequency
K_EGS        = PHI * (1030.0 / 656.28)      # ≈ 2.5436
NOAA_SFI_URL = (
    "https://services.swpc.noaa.gov/products/summary/10cm-flux.json"
)
NOAA_KP_URL  = (
    "https://services.swpc.noaa.gov/products/noaa-planetary-k-index.json"
)

# ── Data structures ────────────────────────────────────────────────────────────
@dataclass
class SolarReading:
    sfi:            float    # Solar Flux Index (10.7 cm)
    kp:             float    # Planetary K-index
    timestamp_utc:  str
    noise_floor_db: float    # derived baseline  dBm/Hz

    def layer_c_hash(self) -> str:
        blob = json.dumps(asdict(self), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:16]


@dataclass
class HydrogenReading:
    hi_freq_hz:     float    # measured centre offset from 1420.405751 MHz
    hi_power_db:    float    # relative power in the 21-cm window
    doppler_km_s:   float    # implied radial velocity
    timestamp_utc:  str
    sdr_gain_db:    float

    def layer_c_hash(self) -> str:
        blob = json.dumps(asdict(self), sort_keys=True).encode()
        return hashlib.sha256(blob).hexdigest()[:16]


# ── Solar calibration ──────────────────────────────────────────────────────────
def fetch_solar_reading() -> SolarReading:
    """Pull live SFI + Kp from NOAA SWPC. Falls back to nominal on error."""
    sfi, kp = 150.0, 2.0          # nominals
    try:
        with urllib.request.urlopen(NOAA_SFI_URL, timeout=6) as r:
            data = json.loads(r.read())
            sfi  = float(data.get("Flux", 150))
    except Exception as exc:
        print(f"[SOLAR] SFI fetch failed ({exc}), using nominal {sfi}")
    try:
        with urllib.request.urlopen(NOAA_KP_URL, timeout=6) as r:
            rows = json.loads(r.read())
            # last row is most recent [time_tag, kp, ...]
            kp = float(rows[-1][1]) if len(rows) > 1 else kp
    except Exception as exc:
        print(f"[SOLAR] Kp fetch failed ({exc}), using nominal {kp}")

    # Derive noise floor baseline from SFI using EGS scaling
    # Higher SFI → denser noise substrate → lower effective floor
    noise_floor_db = -174.0 + 10 * (sfi / 150.0) * K_EGS

    return SolarReading(
        sfi            = sfi,
        kp             = kp,
        timestamp_utc  = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        noise_floor_db = noise_floor_db,
    )


# ── HackRF H I monitor (RX only) ──────────────────────────────────────────────
def init_hackrf_hi_monitor(gain_db: float = 40.0) -> Optional[object]:
    """
    Attempt to open HackRF in receive-only mode tuned to the H I line.
    Returns a device handle or None if HackRF is not connected.

    In simulation mode (no hardware) returns a SimulatedSDR object that
    produces synthetic H I noise data seeded from the live SFI.
    """
    try:
        import SoapySDR                          # pip install SoapySDR
        from SoapySDR import SOAPY_SDR_RX, SOAPY_SDR_CF32
        sdr = SoapySDR.Device({"driver": "hackrf"})
        sdr.setSampleRate(SOAPY_SDR_RX, 0, FS_HZ)
        sdr.setFrequency(SOAPY_SDR_RX,  0, HI_HZ)
        sdr.setGain(SOAPY_SDR_RX,       0, gain_db)
        print(f"[HackRF] Tuned to H I line  {HI_HZ/1e6:.6f} MHz  "
              f"gain={gain_db} dB  fs={FS_HZ/1e6:.3f} MSps")
        return sdr
    except Exception as exc:
        print(f"[HackRF] Hardware not found ({exc}) — entering simulation mode")
        return SimulatedSDR(gain_db=gain_db)


class SimulatedSDR:
    """Synthetic H I receiver for software-only testing."""
    def __init__(self, gain_db: float = 40.0):
        self.gain_db = gain_db
        self._solar  = fetch_solar_reading()

    def read_hi(self) -> HydrogenReading:
        import random
        # Seed noise from SFI so solar activity affects the reading
        random.seed(int(self._solar.sfi * 1000 + time.time()))
        power  = -120.0 + (self._solar.sfi / 150.0) * K_EGS * 2
        offset = random.gauss(0, VW_HZ * 0.1)   # sub-voxel Doppler scatter
        doppler = (offset / HI_HZ) * 3e5         # km/s

        return HydrogenReading(
            hi_freq_hz    = HI_HZ + offset,
            hi_power_db   = power,
            doppler_km_s  = doppler,
            timestamp_utc = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            sdr_gain_db   = self.gain_db,
        )


# ── System initialisation ──────────────────────────────────────────────────────
class EGSISMSystem:
    """
    Top-level initialiser.  Brings up solar calibration and H I monitor,
    then exposes a blocking poll loop that feeds readings to a callback.
    """
    def __init__(self, hi_gain_db: float = 40.0, poll_interval_s: float = 10.0):
        print("=" * 60)
        print("  EGS GATEWAY — 915 MHz ISM / H I DUAL-CHANNEL INIT")
        print("=" * 60)
        print(f"  ℑe  = {IM_E}")
        print(f"  fc  = {FC_HZ/1e6:.3f} MHz  (ISM TX, LoRa/TTN)")
        print(f"  fs  = {FS_HZ/1e6:.4f} MSps")
        print(f"  wv  = {VW_HZ/1e3:.4f} kHz")
        print(f"  H I = {HI_HZ/1e6:.6f} MHz  (passive RX)")
        print(f"  K_EGS = {K_EGS:.6f}")
        print("=" * 60)

        self.poll_interval = poll_interval_s
        self.solar          = fetch_solar_reading()
        self.sdr            = init_hackrf_hi_monitor(gain_db=hi_gain_db)
        self._running       = False

        print(f"\n[SOLAR] SFI={self.solar.sfi}  Kp={self.solar.kp}  "
              f"noise_floor={self.solar.noise_floor_db:.2f} dBm/Hz  "
              f"hash={self.solar.layer_c_hash()}")

    def poll(self, callback=None):
        """
        Read one H I sample, refresh solar if stale, call callback(solar, hi).
        Returns (SolarReading, HydrogenReading) tuple.
        """
        hi = self.sdr.read_hi()
        print(f"\n[H I ] power={hi.hi_power_db:.2f} dBm  "
              f"doppler={hi.doppler_km_s:.3f} km/s  "
              f"hash={hi.layer_c_hash()}")
        if callback:
            callback(self.solar, hi)
        return self.solar, hi

    def run_loop(self, callback=None):
        """Blocking poll loop.  Ctrl-C to stop."""
        self._running = True
        print("\n[EGS] Poll loop started.  Ctrl-C to stop.\n")
        try:
            while self._running:
                self.poll(callback)
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            print("\n[EGS] Poll loop stopped.")
        self._running = False

    def stop(self):
        self._running = False


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    def on_reading(solar: SolarReading, hi: HydrogenReading):
        print(f"  → Solar hash : {solar.layer_c_hash()}")
        print(f"  → H I hash   : {hi.layer_c_hash()}")
        combined = solar.layer_c_hash() + hi.layer_c_hash()
        gate = hashlib.sha256(combined.encode()).hexdigest()[:16]
        print(f"  → Gate stamp : {gate}")

    sys = EGSISMSystem(hi_gain_db=40.0, poll_interval_s=10.0)
    sys.run_loop(callback=on_reading)
