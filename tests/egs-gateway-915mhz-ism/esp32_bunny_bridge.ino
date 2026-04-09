/*
 * esp32_bunny_bridge.ino
 * EGS Gateway — ESP32 LoRa Bunny Bridge
 * ───────────────────────────────────────────────────────────────────────────
 * Hardware: ESP32 DevKit + HopeRF RFM95W or Semtech SX1276 LoRa module
 *           (Part-15 certified — FCC ID varies by module vendor)
 *
 * Function:
 *   1. Receives EGS voxel packets from the Python bridge via USB Serial
 *   2. Transmits them at 915 MHz via LoRa to The Things Network (TTN)
 *   3. Forwards TTN downlinks back to the Python bridge via Serial
 *   4. Optionally bridges Bluetooth (BLE) for mobile-originated transmissions
 *
 * Pin wiring (SX1276 / RFM95W → ESP32):
 *   NSS  → GPIO 18    SCK  → GPIO 5
 *   MOSI → GPIO 23    MISO → GPIO 19
 *   RST  → GPIO 14    DIO0 → GPIO 26
 *
 * Serial (UV-K5 K-plug optional bridge):
 *   TX   → GPIO 17    RX   → GPIO 16   (Serial2, 9600 baud)
 *
 * Dependencies (Arduino Library Manager):
 *   MCCI LoRaWAN LMIC library  (mcci-catena/arduino-lmic)
 *   ArduinoBLE                 (for BLE mobile bridge)
 *
 * COMPLIANCE NOTE:
 *   This sketch never exceeds +14 dBm EIRP.
 *   TTN fair-use policy: ≤ 30 s uplink air-time / day.
 *   All transmissions operate under FCC Part 15.247 via the certified module.
 */

#include <lmic.h>
#include <hal/hal.h>
#include <SPI.h>
#include <ArduinoBLE.h>

// ── TTN OTAA credentials ─────────────────────────────────────────────────────
// Replace with your TTN application credentials
// APPEUI / DEVEUI are LSB first, APPKEY is MSB first
static const u1_t PROGMEM APPEUI[8]  = { 0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00 };
static const u1_t PROGMEM DEVEUI[8]  = { 0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00 };
static const u1_t PROGMEM APPKEY[16] = {
  0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00,
  0x00,0x00,0x00,0x00,0x00,0x00,0x00,0x00
};

void os_getArtEui (u1_t* buf) { memcpy_P(buf, APPEUI, 8); }
void os_getDevEui (u1_t* buf) { memcpy_P(buf, DEVEUI, 8); }
void os_getDevKey (u1_t* buf) { memcpy_P(buf, APPKEY, 16); }

// ── LMIC pin map (ESP32 + RFM95W) ────────────────────────────────────────────
const lmic_pinmap lmic_pins = {
  .nss  = 18,
  .rxtx = LMIC_UNUSED_PIN,
  .rst  = 14,
  .dio  = {26, 33, 32},
};

// ── EGS constants (mirrored from Python layer) ────────────────────────────────
const float  K_EGS    = 2.5436f;
const float  IM_E     = 0.0032f;
const double FC_HZ    = 915.000e6;
const double FS_HZ    = FC_HZ * IM_E;   // 2 928 000 Hz
const double VW_HZ    = FS_HZ * IM_E;   // 9 369.6 Hz

// ── State ─────────────────────────────────────────────────────────────────────
static uint8_t txBuf[51];     // max SF12 payload
static uint8_t txLen = 0;
static bool    txPending = false;
static bool    joined    = false;

// Serial2 → UV-K5 K-plug (optional)
HardwareSerial K5Serial(2);

// BLE service for mobile bridge
BLEService     egsService("180A");
BLECharacteristic txChar("2A57", BLEWrite | BLEWriteWithoutResponse, 51);
BLECharacteristic rxChar("2A58", BLERead  | BLENotify,              51);

// ── Helpers ───────────────────────────────────────────────────────────────────
void egs_log(const char* tag, const char* msg) {
  Serial.print("["); Serial.print(tag); Serial.print("] ");
  Serial.println(msg);
}

// Build a minimal EGS packet header on the ESP32 side
// (Full voxel encoding is done in Python; this is just the LoRa envelope)
uint8_t egs_build_packet(const uint8_t* data, uint8_t len, float sfi) {
  if (len > 48) len = 48;
  txBuf[0] = 0xE9;                             // EGS version byte
  txBuf[1] = len;
  txBuf[2] = (uint8_t)(sfi * 10 / 256);        // SFI high byte
  txBuf[3] = (uint8_t)((uint16_t)(sfi * 10) & 0xFF);
  memcpy(&txBuf[4], data, len);
  return 4 + len;
}

// ── LMIC callbacks ────────────────────────────────────────────────────────────
void onEvent(ev_t ev) {
  switch(ev) {
    case EV_JOINING:
      egs_log("TTN", "Joining...");
      break;

    case EV_JOINED:
      joined = true;
      egs_log("TTN", "Joined — OTAA complete");
      // Set DR to SF9 for 915 MHz US915 sub-band 2
      LMIC_setDrTxpow(DR_SF9, 14);
      LMIC_setAdrMode(0);
      break;

    case EV_TXCOMPLETE:
      egs_log("TTN", "TX complete");
      txPending = false;
      // Check for downlink
      if (LMIC.dataLen > 0) {
        Serial.print("[TTN] Downlink ");
        Serial.print(LMIC.dataLen);
        Serial.print(" bytes: ");
        for (int i = 0; i < LMIC.dataLen; i++) {
          Serial.print(LMIC.frame[LMIC.dataBeg + i], HEX);
          Serial.print(" ");
        }
        Serial.println();
        // Forward to UV-K5 K-plug
        K5Serial.write(&LMIC.frame[LMIC.dataBeg], LMIC.dataLen);
        // Forward to BLE
        rxChar.writeValue(&LMIC.frame[LMIC.dataBeg], LMIC.dataLen);
      }
      break;

    case EV_JOIN_FAILED:
      egs_log("TTN", "Join failed");
      break;

    case EV_TXERR:
      egs_log("TTN", "TX error");
      txPending = false;
      break;

    default:
      break;
  }
}

// ── Queue a LoRa uplink ───────────────────────────────────────────────────────
bool egs_transmit(const uint8_t* data, uint8_t len, float sfi = 150.0f) {
  if (!joined || txPending) {
    egs_log("TX", "Not ready (not joined or TX in progress)");
    return false;
  }
  uint8_t pktLen = egs_build_packet(data, len, sfi);
  if (LMIC_setTxData2(1, txBuf, pktLen, 0) == 0) {
    txPending = true;
    char buf[64];
    snprintf(buf, sizeof(buf), "%u bytes queued at 915 MHz", pktLen);
    egs_log("TX", buf);
    return true;
  }
  egs_log("TX", "LMIC queue failed");
  return false;
}

// ── Parse serial command from Python bridge ───────────────────────────────────
// Protocol: each line is a JSON-like token:
//   TX:<hex_payload>:<sfi_float>\n   → transmit voxel packet
//   PING\n                           → respond PONG\n
void processSerialCommand(String cmd) {
  cmd.trim();
  if (cmd == "PING") {
    Serial.println("PONG:EGS-BUNNY-BRIDGE-v1.0");
    return;
  }
  if (cmd.startsWith("TX:")) {
    // Parse TX:<hexdata>:<sfi>
    int sep1 = cmd.indexOf(':', 3);
    String hexData = cmd.substring(3, sep1 > 3 ? sep1 : cmd.length());
    float sfi = 150.0f;
    if (sep1 > 3) sfi = cmd.substring(sep1 + 1).toFloat();

    uint8_t buf[48];
    uint8_t len = 0;
    for (int i = 0; i + 1 < (int)hexData.length() && len < 48; i += 2) {
      buf[len++] = strtol(hexData.substring(i, i+2).c_str(), nullptr, 16);
    }
    bool ok = egs_transmit(buf, len, sfi);
    Serial.println(ok ? "TX:OK" : "TX:ERR");
  }
}

// ── BLE write handler ─────────────────────────────────────────────────────────
void onTxCharWrite(BLEDevice central, BLECharacteristic characteristic) {
  uint8_t buf[51];
  int len = characteristic.readValue(buf, sizeof(buf));
  egs_transmit(buf, len);
}

// ── setup ─────────────────────────────────────────────────────────────────────
void setup() {
  Serial.begin(115200);
  delay(300);

  egs_log("EGS", "Bunny Bridge starting");
  egs_log("EGS", "K_EGS=" + String(K_EGS, 4) +
                  "  fc=" + String(FC_HZ / 1e6, 3) + " MHz" +
                  "  Im_e=" + String(IM_E, 4));

  // UV-K5 K-plug UART
  K5Serial.begin(9600, SERIAL_8N1, 16, 17);
  egs_log("K5", "Serial2 ready on GPIO16/17 at 9600 baud");

  // BLE
  if (!BLE.begin()) {
    egs_log("BLE", "Init failed — continuing without BLE");
  } else {
    BLE.setLocalName("EGS-Bunny");
    BLE.setAdvertisedService(egsService);
    egsService.addCharacteristic(txChar);
    egsService.addCharacteristic(rxChar);
    BLE.addService(egsService);
    txChar.setEventHandler(BLEWritten, onTxCharWrite);
    BLE.advertise();
    egs_log("BLE", "Advertising as EGS-Bunny");
  }

  // LMIC
  os_init();
  LMIC_reset();
  // US915 sub-band 2 (channels 8-15 + 65) — standard for TTN US
  LMIC_selectSubBand(1);
  LMIC_startJoining();
  egs_log("LMIC", "OTAA join initiated");
}

// ── loop ──────────────────────────────────────────────────────────────────────
void loop() {
  os_runloop_once();
  BLE.poll();

  // Serial command from Python bridge
  if (Serial.available()) {
    String cmd = Serial.readStringUntil('\n');
    processSerialCommand(cmd);
  }

  // UV-K5 passthrough to Serial monitor
  if (K5Serial.available()) {
    Serial.print("[K5] ");
    while (K5Serial.available()) Serial.write(K5Serial.read());
    Serial.println();
  }
}
