# Power Budget — Zigbee Plant Sensor Solar Node

## Component Power Consumption

| Component | Function | V_supply | Active Current | Sleep Current |
|---|---|---|---|---|
| ESP32-C6-MINI-1-N4 | MCU + Zigbee | 3.3V | 120 mA (TX @ 0 dBm), 73 mA (RX), 19 mA (CPU only) | 7 uA (deep sleep) |
| SHT40 | Temp/Humidity | 1.08-3.6V | 150 uA | 0.08 uA |
| VEML7700 | Light Sensor | 2.5-3.6V | 45 uA | 0.5 uA |
| MAX17048 | Fuel Gauge | 2.5-4.5V | 23 uA | 4 uA |
| SPV1040T | MPPT Charger | 0.3-5.5V | N/A | 60 uA (quiescent) |
| HT7833 | 3.3V LDO | 3.6-8V in | pass-through | 7 uA |
| XB3306D | Battery Protection | 2.5-6.0V | pass-through | 3 uA |

## Operating Parameters

- Readings every 5 minutes (288/day)
- Active duration per reading: ~500 ms (200 ms sensor read + 300 ms Zigbee TX/ACK)
- Battery: 3.7V nominal LiPo

## Active Current Budget (per 500 ms reading)

| Phase | Duration | ESP32-C6 | Sensors | Other | Subtotal |
|---|---|---|---|---|---|
| Sensor read (CPU, no RF) | 200 ms | 19 mA | ~0.2 mA | ~0.03 mA | ~19.2 mA |
| Zigbee TX + RX ACK | 300 ms | 120 mA | — | ~0.03 mA | ~120 mA |
| **Weighted average** | **500 ms** | | | | **~80 mA** |

With 1.2x safety margin: **~96 mA average per active period**

## Sleep Current Budget

| Component | Current |
|---|---|
| ESP32-C6 (deep sleep) | 7.0 uA |
| SHT40 (idle) | 0.08 uA |
| VEML7700 (shutdown) | 0.5 uA |
| MAX17048 (hibernate) | 4.0 uA |
| SPV1040T (quiescent) | 60.0 uA |
| HT7833 (quiescent) | 7.0 uA |
| XB3306D (standby) | 3.0 uA |
| **Total** | **81.6 uA** |

Note: SPV1040T dominates sleep budget at 73% of total.

## Daily Energy Budget

### At 3.3V rail

| Mode | Current | Time/day | Energy |
|---|---|---|---|
| Active | 96 mA | 144 s (0.04 h) | 3.84 mAh / 12.67 mWh |
| Sleep | 81.6 uA | 23.96 h | 1.96 mAh / 6.45 mWh |
| **Subtotal** | | | **5.80 mAh / 19.12 mWh** |

### At battery level

- HT7833 LDO efficiency: Vout/Vin = 3.3V/3.7V = 89.2%
- SPV1040T quiescent (direct from battery): 60 uA x 24h x 3.7V = 5.33 mWh/day
- XB3306D (direct from battery): 3 uA x 24h x 3.7V = 0.27 mWh/day

| Item | Energy/day |
|---|---|
| 3.3V rail (through LDO) | 21.43 mWh |
| SPV1040T quiescent | 5.33 mWh |
| XB3306D standby | 0.27 mWh |
| **Total from battery** | **~27 mWh/day** |

**With safety margin: ~30 mWh/day**

## Battery Autonomy (no solar)

| Battery | Capacity | Realistic Days (x0.7 derating) |
|---|---|---|
| 500 mAh | 1.85 Wh | ~43 days |
| 1000 mAh | 3.7 Wh | ~86 days |
| 2000 mAh | 7.4 Wh | ~173 days |

## Solar Panel Sizing

Efficiency chain:
- SPV1040 charger: ~90%
- Battery charge/discharge: ~90%
- Panel derating (angle, clouds, aging): ~70%
- **Combined: 56.7%**

Required solar input: 30 mWh / 0.567 = **52.9 mWh/day**

| Panel | Rated Power | Peak Sun Hours Needed |
|---|---|---|
| 0.5W (60x60mm) | 500 mW | 6.3 min |
| 1W (110x70mm) | 1000 mW | 3.2 min |
| 2W (110x136mm) | 2000 mW | 1.6 min |

## Selected Configuration

- **Solar panel**: ~2W, **4-cell** (Vmpp ~2.0-2.2V, Impp ~0.9-1.0A)
  - CRITICAL: SPV1040T is a boost-only converter (Vin < Vout required).
    A 5V panel (Voc ~6.5V) exceeds Vin_max=5.5V and prevents MPPT tracking.
    Must use a low-voltage panel where Vmpp < Vbat (4.2V).
  - Alternative: replace SPV1040T with buck-boost MPPT (e.g., SPV1050, CN3791)
    if a 5V+ panel is preferred.
- **Battery**: 1000 mAh LiPo (3.7V nominal)
- **Battery autonomy**: ~86 days without sun (with MPPT gate: ~120+ days)
- **Solar sufficiency**: needs <2 minutes of direct sun per day

## Design Improvements (rev 2)

- **R1/R2 tolerance**: Changed from 10% to 1% — prevents overcharge (4.53V risk)
- **LDO bulk cap**: Added 100µF output cap — absorbs 120mA Zigbee TX transient
- **I2C pull-ups**: Centralized single 2.2k pair — was 6x10k stacked (3.3k effective)
- **Solar reverse protection**: Added Schottky diode on Vpv input
- **USB ESD**: Added SRV05-4 TVS on USB D+/D-
- **MPPT power gate**: P-FET load switch (SI2301CDS) on GPIO0 — saves 60µA at night
- **Sensor power gate**: P-FET load switch on GPIO1 — cuts external sensor power during sleep
- **Battery UVLO**: MAX17048 ALERT wired to GPIO2 — wakes MCU for low-battery shutdown
- **RF keepout**: Documented 3.5mm antenna clearance zone requirement

## ESP32-C6 802.15.4 TX Power Levels

| TX Power | Current |
|---|---|
| +19 dBm | 305 mA |
| +12 dBm | 190 mA |
| 0 dBm | 120 mA |
| -16 dBm | 86 mA |

Default assumption: 0 dBm (good indoor/outdoor range, reasonable power).
