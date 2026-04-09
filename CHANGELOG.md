# Changelog

All notable changes to this project are documented here.
Format: [Keep a Changelog](https://keepachangelog.com/en/1.0.0/)

## [Unreleased]

### Added
- External NTC thermistor circuit: ADS1115 16-bit ADC + 10k 0.1% reference resistor + JST PH 2-pin probe connector for high-precision ambient temperature measurement (0.1 degC resolution, -30 to +100 degC)
- PCB component placement for 60x48mm 4-layer board following functional block strategy
- Automated placement script (`scripts/place_components.py`)
- PCB placement strategy document (`docs/pcb_placement_strategy.md`)
- P-FET high-side load switch module (`loadswitch.ato`) using SI2301CDS

### Changed
- ESP32-C6 module rotated 90 deg with antenna facing right board edge for optimal RF performance
- MPPT switching loop components placed within 3mm for minimal loop area

## [0.3.0] - 2026-03-14

### Added
- OpenSCAD parametric enclosure for 60x48mm PCB
- STEP exports for mechanical integration
- PCB preview renders
- Quilter autorouter candidate configurations

## [0.2.0] - 2026-03-01

### Added
- build123d enclosure design for 60x48mm PCB form factor

## [0.1.0] - 2026-02-25

### Added
- Complete schematic: ESP32-C6-MINI-1, SPV1040T MPPT charger, HT7833 LDO, SHT40, VEML7700, MAX17048 fuel gauge
- USB-C connector with ESD protection and CC resistors
- Boot and reset buttons
- Qwiic I2C expansion connectors (2x)
- Battery protection circuit (XB3306D)
- 4-layer PCB layout with initial routing
- KiCad project and schematic generation scripts

## [0.0.1] - 2026-02-24

### Added
- Initial project scaffold with atopile configuration
