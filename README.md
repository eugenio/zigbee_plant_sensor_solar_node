# Zigbee Plant Sensor Solar Node

Solar-powered environmental monitoring node for outdoor plant care. Measures temperature, humidity, light, soil moisture, and battery state via Zigbee 802.15.4 — integrates with Home Assistant, Zigbee2MQTT, and ZHA.

## Motivation

Commercial plant sensors are either battery-hungry, lack solar charging, or miss key measurements. This node combines an MPPT solar charger with deep-sleep Zigbee to achieve indefinite outdoor operation while reporting six sensor channels.

## Hardware Overview

| Block              | Component          | Function                                |
| ------------------ | ------------------ | --------------------------------------- |
| MCU                | ESP32-C6-MINI-1-N4 | Zigbee 802.15.4 / WiFi / BLE, 4MB flash |
| MPPT Charger       | SPV1040T           | Autonomous solar boost charger, 5W max  |
| LDO                | HT7833             | 3.3V 500mA, 4uA quiescent              |
| Battery Protection | XB3306D            | Overcharge / overdischarge / overcurrent |
| Temp/Humidity      | SHT40              | +/-0.2 degC, +/-1.8% RH (onboard)      |
| Ambient Light      | VEML7700           | 0.0036 - 120k lux                      |
| Fuel Gauge         | MAX17048           | Li-Po SOC estimation, low-battery alert |
| External Temp      | ADS1115 + NTC 10k  | 0.1 degC resolution, metal-tip probe   |
| Expansion          | 2x Qwiic I2C      | Soil moisture, EC sensor                |

**Board**: 60 x 48 mm, 4-layer, 1.6mm FR4

## Quick Start

```bash
# 1. Install atopile
pip install atopile

# 2. Clone and build
git clone <repo-url> && cd zigbee_plant_sensor_solar_node
ato build

# 3. Open PCB in KiCad
kicad layouts/default/default.kicad_pcb
```

## Project Structure

```text
.
├── main.ato                    # Top-level schematic (App module)
├── micromppt.ato               # MPPT solar charger (SPV1040T)
├── ldo.ato                     # 3.3V LDO (HT7833)
├── loadswitch.ato              # P-FET high-side load switch (SI2301CDS)
├── ntc_adc.ato                 # External NTC thermistor (ADS1115)
├── xiao_esp32c6.ato            # ESP32-C6 MCU driver
├── ato.yaml                    # Atopile project config + dependencies
├── pixi.toml                   # Pixi environment config
├── parts/                      # Component packages (32 parts, 4 files each)
│   ├── Texas_Instruments_ADS1115IRUGR/   # .ato + .kicad_mod + .kicad_sym + .step
│   ├── STMicroelectronics_SPV1040T/
│   ├── Espressif_Systems_ESP32_C6_MINI_1_N4/
│   └── ...                     # Resistors, caps, connectors, ICs
├── layouts/default/            # KiCad PCB layout (60x48mm, 4-layer)
│   ├── default.kicad_pcb
│   ├── default.kicad_sch
│   └── default.kicad_pro
├── docs/
│   ├── pcb_placement_strategy.md
│   ├── power_budget.md
│   ├── uml/architecture.puml  # System block diagram
│   └── adr/ADR-001-external-ntc-thermistor.md
└── scripts/
    └── place_components.py     # Automated PCB placement

176 tracked files. Atopile dependencies (sensirion-sht40, vishay-veml7700,
maxim-max17048, sparkfun-qwiic) are gitignored and reinstalled by `ato build`.
```

## Power Budget

| Mode               | Current    | Duration       | Notes                      |
| ------------------ | ---------- | -------------- | -------------------------- |
| Deep Sleep         | ~82 uA     | 99% of time    | Fuel gauge + LDO quiescent |
| Active (sense + TX)| ~120 mA    | ~500 ms        | Zigbee transmit burst      |
| Solar input        | 200-400 mA | Daylight hours | 5V / 1W panel via MPPT     |

See [docs/power_budget.md](docs/power_budget.md) for detailed analysis.

## Architecture

See [docs/uml/architecture.puml](docs/uml/architecture.puml) for the system block diagram.

## License

MIT
