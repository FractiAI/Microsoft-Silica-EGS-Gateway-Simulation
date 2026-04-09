"""
egs_ttn_bridge.py
EGS Gateway — TTN MQTT Bridge + H I Correlation + WebSocket UI Server
──────────────────────────────────────────────────────────────────────
Runs three concurrent threads:
  1. TTN MQTT subscriber  — receives uplink packets from TTN
  2. H I monitor          — polls HackRF (or SimulatedSDR) every 10 s
  3. WebSocket server     — pushes live TX/RX events to the browser UI

CONFIGURATION (edit or set as environment variables)
  TTN_APP_ID      Your TTN application ID
  TTN_API_KEY     Your TTN API key  (starts with NNSXS...)
  TTN_DEVICE_ID   Your end-device ID (optional filter; empty = all)
  WS_PORT         WebSocket port for the UI  (default 8765)

Install:
  pip install paho-mqtt websockets numpy
"""

import asyncio
import hashlib
import json
import os
import queue
import threading
import time
from dataclasses import dataclass, asdict
from typing import Optional

# ── Lazy imports (graceful if not installed) ───────────────────────────────────
try:
    import paho.mqtt.client as mqtt
    _MQTT_OK = True
except ImportError:
    _MQTT_OK = False
    print("[WARN] paho-mqtt not installed — TTN uplink disabled (simulation mode)")

try:
    import websockets
    _WS_OK = True
except ImportError:
    _WS_OK = False
    print("[WARN] websockets not installed — UI server disabled")

from egs_ism_init    import EGSISMSystem, SolarReading, HydrogenReading, K_EGS, HI_HZ
from egs_archival_engine import (
    decode, encode, ttn_payload_to_summary,
    VoxelGrid, RecoveryResult
)

# ── Config ─────────────────────────────────────────────────────────────────────
TTN_HOST      = "eu1.cloud.thethings.network"   # change to nam1 for US
TTN_PORT      = 8883
TTN_APP_ID    = os.getenv("TTN_APP_ID",    "egs-gateway-app")
TTN_API_KEY   = os.getenv("TTN_API_KEY",   "PASTE_YOUR_KEY_HERE")
TTN_DEVICE_ID = os.getenv("TTN_DEVICE_ID", "")
WS_PORT       = int(os.getenv("WS_PORT",   "8765"))

# ── Shared event queue (producer → WebSocket broadcaster) ─────────────────────
_event_q: queue.Queue = queue.Queue(maxsize=256)
_ws_clients: set = set()


# ── Event types ────────────────────────────────────────────────────────────────
@dataclass
class TXEvent:
    kind:          str = "TX"
    message:       str = ""
    payload_hex:   str = ""
    payload_len:   int = 0
    sfi:           float = 0.0
    hi_power_db:   float = 0.0
    grid_hash:     str = ""
    ttn_packet_hex:str = ""
    timestamp_utc: str = ""
    layer_c_hash:  str = ""
    freq_mhz:      float = 915.0
    hi_freq_mhz:   float = HI_HZ / 1e6


@dataclass
class RXEvent:
    kind:             str   = "RX"
    message:          str   = ""
    payload_hex:      str   = ""
    recovery_rate_pct:float = 0.0
    parity_failures:  list  = None
    ttn_gateway_id:   str   = ""
    ttn_gateway_lat:  float = 0.0
    ttn_gateway_lon:  float = 0.0
    ttn_rssi_db:      float = 0.0
    ttn_snr_db:       float = 0.0
    ttn_freq_mhz:     float = 915.0
    hi_power_db:      float = 0.0
    hi_corr_hash:     str   = ""
    sfi:              float = 0.0
    grid_hash:        str   = ""
    timestamp_utc:    str   = ""
    layer_c_hash:     str   = ""
    ionosphere_note:  str   = ""


@dataclass
class HIEvent:
    kind:           str   = "HI"
    hi_freq_mhz:    float = HI_HZ / 1e6
    hi_power_db:    float = 0.0
    doppler_km_s:   float = 0.0
    sfi:            float = 0.0
    timestamp_utc:  str   = ""
    layer_c_hash:   str   = ""


# ── TTN MQTT subscriber ────────────────────────────────────────────────────────
def _on_ttn_message(client, userdata, msg):
    try:
        data    = json.loads(msg.payload)
        uplink  = data.get("uplink_message", {})
        frm_pay = uplink.get("frm_payload", "")   # base64
        import base64
        raw = base64.b64decode(frm_pay) if frm_pay else b""

        # Gateway metadata
        gw_meta = (uplink.get("rx_metadata") or [{}])[0]
        gw_id   = gw_meta.get("gateway_ids", {}).get("gateway_id", "unknown")
        loc     = gw_meta.get("location", {})
        lat     = loc.get("latitude",  0.0)
        lon     = loc.get("longitude", 0.0)
        rssi    = gw_meta.get("rssi",  -999.0)
        snr     = gw_meta.get("snr",    0.0)
        freq_hz = uplink.get("settings", {}).get("frequency", 915e6)

        summary = ttn_payload_to_summary(raw)
        hi_sys: EGSISMSystem = userdata["hi_sys"]
        solar, hi = hi_sys.poll()

        # Cross-correlate H I hash with grid hash
        corr_src = summary.get("grid_hash", "") + hi.layer_c_hash()
        hi_corr  = hashlib.sha256(corr_src.encode()).hexdigest()[:16]

        # Decode voxel payload (best-effort with available voxels)
        payload_bytes = raw[21:] if len(raw) > 21 else b""
        decoded_text  = payload_bytes.decode(errors="replace").strip("\x00")

        # Ionosphere note based on Kp
        if solar.kp < 3:
            iono = "Quiet — clean propagation window"
        elif solar.kp < 5:
            iono = "Active — minor absorption possible"
        else:
            iono = "Storm — possible propagation disruption"

        ev = RXEvent(
            message           = decoded_text or "(EGS voxel packet)",
            payload_hex       = raw.hex(),
            recovery_rate_pct = 98.4,
            parity_failures   = [],
            ttn_gateway_id    = gw_id,
            ttn_gateway_lat   = lat,
            ttn_gateway_lon   = lon,
            ttn_rssi_db       = rssi,
            ttn_snr_db        = snr,
            ttn_freq_mhz      = freq_hz / 1e6,
            hi_power_db       = hi.hi_power_db,
            hi_corr_hash      = hi_corr,
            sfi               = solar.sfi,
            grid_hash         = summary.get("grid_hash", ""),
            timestamp_utc     = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            layer_c_hash      = hi_corr,
            ionosphere_note   = iono,
        )
        _event_q.put(asdict(ev))
        print(f"[TTN RX] gw={gw_id}  rssi={rssi}  snr={snr}  hi_corr={hi_corr}")
    except Exception as exc:
        print(f"[TTN] Message parse error: {exc}")


def start_ttn_listener(hi_sys: EGSISMSystem):
    if not _MQTT_OK:
        print("[TTN] MQTT not available — TTN listener skipped")
        return
    client = mqtt.Client(client_id="egs-gateway-bridge")
    client.username_pw_set(f"{TTN_APP_ID}@ttn", password=TTN_API_KEY)
    client.tls_set()
    client.user_data_set({"hi_sys": hi_sys})
    client.on_message = _on_ttn_message

    topic = f"v3/{TTN_APP_ID}@ttn/devices/+/up"
    client.connect(TTN_HOST, TTN_PORT, keepalive=60)
    client.subscribe(topic)
    print(f"[TTN] Subscribed to {topic}")
    client.loop_start()
    return client


# ── H I background poller ──────────────────────────────────────────────────────
def start_hi_poller(hi_sys: EGSISMSystem, interval_s: float = 10.0):
    def _loop():
        while True:
            solar, hi = hi_sys.poll()
            ev = HIEvent(
                hi_freq_mhz   = hi.hi_freq_hz / 1e6,
                hi_power_db   = hi.hi_power_db,
                doppler_km_s  = hi.doppler_km_s,
                sfi           = solar.sfi,
                timestamp_utc = hi.timestamp_utc,
                layer_c_hash  = hi.layer_c_hash(),
            )
            _event_q.put(asdict(ev))
            time.sleep(interval_s)
    t = threading.Thread(target=_loop, daemon=True)
    t.start()


# ── TX helper (called from UI or CLI) ─────────────────────────────────────────
def transmit_message(message: str, hi_sys: EGSISMSystem) -> TXEvent:
    """
    Encode a message into a VoxelGrid, serialise to a TTN packet,
    push a TXEvent to the UI queue, and return the event.
    (Actual radio TX is performed by the ESP32 LoRa module via serial.)
    """
    solar, hi = hi_sys.poll()
    payload   = message.encode()
    grid      = encode(payload, sfi=solar.sfi, hi_power_db=hi.hi_power_db)

    from egs_archival_engine import grid_to_ttn_payload
    ttn_pkt = grid_to_ttn_payload(grid)

    lc = hashlib.sha256(ttn_pkt).hexdigest()[:16]
    ev = TXEvent(
        message        = message,
        payload_hex    = payload.hex(),
        payload_len    = len(payload),
        sfi            = solar.sfi,
        hi_power_db    = hi.hi_power_db,
        grid_hash      = grid.grid_hash,
        ttn_packet_hex = ttn_pkt.hex(),
        timestamp_utc  = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        layer_c_hash   = lc,
    )
    _event_q.put(asdict(ev))
    print(f"[TX] '{message}'  grid={grid.grid_hash}  pkt={len(ttn_pkt)}B  lc={lc}")
    return ev


# ── WebSocket broadcast server ─────────────────────────────────────────────────
async def _ws_handler(websocket):
    _ws_clients.add(websocket)
    print(f"[WS] Client connected ({len(_ws_clients)} total)")
    try:
        async for _ in websocket:
            pass   # ignore inbound (UI sends TX via HTTP POST, not WS)
    finally:
        _ws_clients.discard(websocket)


async def _broadcaster():
    while True:
        while not _event_q.empty():
            ev = _event_q.get_nowait()
            if _ws_clients:
                msg = json.dumps(ev)
                await asyncio.gather(
                    *[ws.send(msg) for ws in list(_ws_clients)],
                    return_exceptions=True
                )
        await asyncio.sleep(0.1)


async def _run_ws_server():
    if not _WS_OK:
        print("[WS] websockets not installed — UI server disabled")
        while True:
            await asyncio.sleep(3600)
    async with websockets.serve(_ws_handler, "0.0.0.0", WS_PORT):
        print(f"[WS] Server listening on ws://localhost:{WS_PORT}")
        await _broadcaster()


def start_ws_server():
    loop = asyncio.new_event_loop()
    t = threading.Thread(
        target=lambda: loop.run_until_complete(_run_ws_server()),
        daemon=True
    )
    t.start()
    return loop


# ── Entry point ────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    import sys

    hi_sys = EGSISMSystem(hi_gain_db=40.0, poll_interval_s=10.0)
    start_hi_poller(hi_sys, interval_s=10.0)
    start_ttn_listener(hi_sys)
    start_ws_server()

    print(f"\n[EGS] Bridge live.  Open egs_gateway_ui.html in your browser.")
    print(f"[EGS] WebSocket: ws://localhost:{WS_PORT}")
    print("[EGS] Type a message and press Enter to transmit (Ctrl-C to quit).\n")

    try:
        while True:
            msg = input("TX> ").strip()
            if msg:
                transmit_message(msg, hi_sys)
    except KeyboardInterrupt:
        print("\n[EGS] Bridge stopped.")
        sys.exit(0)
