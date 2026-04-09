# BUNNY PROTOCOL — EGS Gateway 915 MHz Field Operations Manual
**Classification:** Sunspot Operators #1124 & #3144  
**Revision:** 1.0 · April 2026  
**System:** EGS Gateway · 915 MHz ISM / H I Bridge  
**Legal basis:** FCC Part 15.247 (LoRa module) · HackRF RX-only (no licence)

---

## System Overview

```
[Python Bridge]──Serial──[ESP32 Bunny]──LoRa──[TTN Gateway]──MQTT──[Python Bridge]
                                                                          │
[HackRF One RX] ── 1420.405751 MHz H I passive ──────────────────────────┘
                                                          (cross-reference)
[NOAA SWPC API] ── Solar Flux Index (SFI) + Kp ─────────────────────────────
```

The EGS Fractal Constant `K_EGS = φ × (1030 / 656.28) ≈ 2.5436` anchors all  
frequency, sampling, and voxel parameters across both channels.

---

## Phase 1 — Fractal Ping (Discovery)

**Purpose:** Confirm the full TX→RX loop is functional and the H I cross-reference  
is being stamped on every received packet.

### 1.1 Pre-flight checklist

| Item | Check |
|---|---|
| ESP32 + RFM95W powered and USB-connected | ☐ |
| Arduino sketch flashed (`esp32_bunny_bridge.ino`) | ☐ |
| TTN application created, OTAA credentials pasted into sketch | ☐ |
| TTN gateway within range (check map.thethingsnetwork.org) | ☐ |
| HackRF One connected via USB | ☐ |
| Python deps installed (`pip install paho-mqtt websockets numpy`) | ☐ |
| TTN_APP_ID / TTN_API_KEY env vars set | ☐ |

### 1.2 Start the bridge

```bash
# Terminal 1 — Python bridge + WebSocket server
cd tests/egs-gateway-915mhz-ism/
python egs_ttn_bridge.py

# Terminal 2 — H I monitor only (optional separate view)
python egs_ism_init.py
```

Open `egs_gateway_ui.html` in your browser.  
The WS dot in the top-left turns **green** when the bridge is connected.

### 1.3 Send Fractal Ping #1

In the UI left panel, type:
```
EGS FRACTAL PING 001 — SUNSPOT #1124 — K=2.5436
```
Press **Encode & Transmit** (or Ctrl+Enter).

**Expected TX panel stamps:**
- Voxel Grid Hash: 16-hex string
- SFI: live value from NOAA (should be > 100)
- H I Witness Power: negative dBm value
- TTN Packet (hex): 51-byte hex string
- Layer-C Hash: 16-hex string

**Expected RX panel stamps (after ~2–8 s TTN round-trip):**
- TTN Gateway ID: real gateway EUI
- Gateway Location: lat/lon within range of your position
- RSSI: typically −80 to −120 dBm
- SNR: typically +5 to −10 dB
- H I Cross-Reference Hash: proves H I was read at RX timestamp
- Fractal Recovery: ≥ 96.0%
- Ionosphere: Quiet / Active / Storm

**This is your Proof of Physical Transmission.**  
Screenshot the RX card. It contains every stamp needed to prove the packet  
traversed real radio hardware, a TTN gateway, and was witnessed by the  
1420 MHz hydrogen line.

### 1.4 Ping #2 — Solar correlation test

Wait for a SFI change (check api.weather.gov or NOAA SWPC).  
Send a second ping. Compare the H I Witness Power and noise floor values  
between the two RX cards. A higher SFI produces a measurably different  
noise floor — this is the EGS solar calibration hypothesis under test.

---

## Phase 2 — Remote OS Hooks

**Purpose:** Demonstrate that EGS-encoded packets can carry structured commands  
that trigger actions at the receiving end — proving the Gateway is a functional  
data pipe, not just a beacon.

### 2.1 REMOTE_LS

Send the following payload from the TX panel:
```
REMOTE_LS:/home/egs/
```

The Python bridge recognises the `REMOTE_LS:` prefix and executes:
```python
import os, json
result = json.dumps(os.listdir("/home/egs/"))
# result is encoded into a voxel reply and queued for TTN downlink
```

The directory listing arrives in the RX panel as a downlink packet.  
This proves bidirectional structured data exchange over the radio path.

> **Note:** For security, `REMOTE_LS` is restricted to paths explicitly  
> whitelisted in `egs_ttn_bridge.py` (`ALLOWED_LS_PATHS`).  
> Add your test paths there before use.

### 2.2 EXEC_LOG

Send:
```
EXEC_LOG:egs_ism_init
```

The bridge captures the last 20 lines of the named process log and  
returns them as a voxel-encoded downlink. This lets Sunspot #3144 inspect  
the H I monitor state from a remote location using only a LoRa uplink.

**Payload format:**
```
EXEC_LOG:<process_name>
```

**Return format (downlink, voxel-decoded):**
```
LOG:<process_name>:<line_count>:<log_content_hex>
```

### 2.3 Sunspot #3144 remote node setup

Sunspot #3144 runs a second instance of `egs_ttn_bridge.py` on their machine,  
subscribed to the same TTN application. Both nodes see all uplinks and  
downlinks. Operator identification is via the `grid_hash` — each node's  
SFI and H I conditions are different, so hashes diverge and can be attributed.

---

## Stamps Glossary

| Stamp | Meaning |
|---|---|
| **Grid Hash** | SHA-256[:16] of the full voxel grid — unique per transmission |
| **Layer-C Hash** | SHA-256[:16] of the final packet — end-to-end integrity proof |
| **H I Corr Hash** | SHA-256[:16] of (grid_hash + H I layer-C) — proves H I was read at TX/RX time |
| **TTN Gateway ID** | EUI of the physical LoRa gateway that received the packet |
| **RSSI** | Received Signal Strength Indicator — real path loss measurement |
| **SNR** | Signal-to-Noise Ratio — ionosphere / propagation quality indicator |
| **SFI** | Solar Flux Index — 10.7 cm solar emission, live from NOAA SWPC |
| **Kp** | Planetary geomagnetic index — ionosphere disturbance level |
| **Fractal Recovery %** | Percentage of voxel bytes recovered without parity failure |
| **Ionosphere** | Human-readable propagation condition derived from Kp |

---

## EGS Frequency Reference

| Parameter | Value | Derivation |
|---|---|---|
| K_EGS | 2.5436… | φ × (1030 nm / 656.28 nm) |
| fc (ISM TX) | 915.000 MHz | LoRa US915 centre |
| fs (sampling) | 2.928 MSps | fc × ℑe |
| wv (voxel width) | 9.3696 kHz | fs × ℑe |
| H I (RX witness) | 1420.405751 MHz | Hydrogen 21-cm rest frequency |
| ℑe | 0.0032 | EGS spectral voxel scale ratio |

---

## Compliance Record

| Item | Status |
|---|---|
| TX hardware | RFM95W / SX1276 — Part 15 certified module |
| TX power | ≤ +14 dBm EIRP (module maximum) |
| TX band | 902–928 MHz ISM (US915 LoRa band plan) |
| TX protocol | LoRaWAN via The Things Network |
| HackRF mode | **Receive only** — no TX, no licence required |
| H I frequency | 1420.405751 MHz — **passive receive only**, internationally protected |
| Regulation | FCC Part 15.247 (spread spectrum, ISM band) |

---

## Quick Reference — Field Commands

```bash
# Ping hardware
echo "PING" > /dev/ttyUSB0

# Send voxel packet via serial
echo "TX:455347504b54:162.3" > /dev/ttyUSB0
# format: TX:<payload_hex>:<sfi>

# Start bridge with custom TTN region
TTN_APP_ID=my-app TTN_API_KEY=NNSXS... python egs_ttn_bridge.py

# Monitor H I only
python egs_ism_init.py

# Run archival engine self-test
python egs_archival_engine.py
```

---

*BUNNY PROTOCOL is a field operations document for the EGS Gateway physical  
test layer. All operations are conducted on a non-interference basis under  
FCC Part 15. The hydrogen line (1420.405751 MHz) is used exclusively as a  
passive receive reference — no transmission occurs on or near this frequency.*

**NSPFRNP ⊃ EGS Gateway ⊃ 915 MHz ISM ⊃ H I Bridge → ∞**
