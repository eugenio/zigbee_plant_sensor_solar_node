# PCB Placement Strategy — Zigbee Plant Sensor Solar Node

## Board Parameters
- **PCB file**: `layouts/default/default.kicad_pcb`
- **Current size**: 245.5 x 137.5 mm (oversized — target ~60x48mm per enclosure)
- **Layers**: 4 (2-signal + 2-ground/power recommended)
- **Footprints**: 60 total, 235 pads, 0 tracks (unrouted)
- **Stack**: 1.6mm FR4

## Functional Blocks (placement groups)

### Block A — Solar MPPT Charger (SPV1040T)
**Components**: SPV1040T IC, L1 (XAL6060 inductor), Cin (10µF), Cout1 (4.7µF), Cout2 (10µF), R1/R2 (voltage divider 1%), R3, Rf1, Rf2, Rs (10mΩ sense), Cinsns, Coutsns, Cf, SRV05-4 (ESD), D_rpv (reverse polarity Schottky)
**Connectors**: J_solar (JST PH 2-pin), J_battery (JST PH 2-pin)
**Placement rules**:
- Keep inductor L1 within 3mm of SPV1040T LX pin
- Cin close to VIN, Cout1/Cout2 close to VOUT
- Rs (current sense) between IC VOUT and battery output — short, wide traces
- Voltage divider R1/R2 near VCTRL pin — keep traces short (high impedance)
- Solar connector at board edge
- Battery connector at board edge (same side or adjacent)
- Group entire MPPT section in one corner

### Block B — Battery Protection (XB3306D)
**Components**: XB3306D IC, C_bpc (100nF), R_bpc (100Ω)
**Placement**: Adjacent to battery connector, between MPPT output and battery JST

### Block C — LDO Power (HT7833)
**Components**: HT7833 IC, c_in (1µF), c_out (1µF), c_bulk (100µF 0805)
**Placement rules**:
- Between battery rail (Block A output) and 3.3V rail (Block D input)
- c_bulk (100µF) as close to VOUT as possible — critical for TX transient
- c_in close to VIN pin
- Keep short, wide power traces from battery to LDO to MCU

### Block D — ESP32-C6 MCU
**Components**: ESP32-C6-MINI-1-N4 module, c_dec_1 (10µF), c_dec_2 (100nF), r_en (10k), c_en (1µF), r_boot (10k), btn_boot, btn_reset, USB-C connector, r_cc1/r_cc2 (5.1k), USB ESD (SRV05-4)
**Placement rules**:
- **CRITICAL: Antenna keepout** — 3.5mm clearance from module edge (antenna end) on ALL copper layers. No traces, pours, or vias in this zone.
- Antenna must point toward board edge or overhang — never toward ground plane
- Place module so antenna faces AWAY from MPPT switching noise
- Decoupling caps c_dec_1 and c_dec_2 within 2mm of P3V3 pin
- USB-C connector at board edge, close to IO12/IO13 pads
- Boot/reset buttons accessible from board edge
- Keep I2C lines (IO6/IO7) routed toward sensor area

### Block E — Sensors (on switched power rail)
**Components**: SHT40 (DFN-4), VEML7700 (LED-SMD-4P), decoupling caps (2x 100nF)
**Placement rules**:
- SHT40: Away from heat sources (LDO, MPPT, MCU). Ideally near board edge with thermal isolation slot
- VEML7700: Near board edge with unobstructed view (light sensor — no tall components nearby)
- Both on same I2C bus — minimize trace length to MCU IO6/IO7

### Block F — Fuel Gauge (always on, main 3.3V)
**Components**: MAX17048 (TDFN-8), bypass_cap (1µF), battery_cap (1µF), q_pulldown (10k), alert_pullup (10k)
**Placement**: Near battery connection (senses CELL voltage) and close to MCU (I2C + ALERT to GPIO2)

### Block G — Qwiic Connectors
**Components**: 2x BM04B-SRSS-TB (4-pin SMD)
**Placement**: Board edge, accessible for cable connection. Same side preferred.

### Block H — Load Switches (2x SI2301CDS P-FET)
**Components per switch**: SI2301CDS (SOT-23), r_gate_pu (100k), r_gate (10k)
- **MPPT gate**: Between battery rail and MPPT power input. Near Block A.
- **Sensor gate**: Between 3.3V rail and sensor power rail. Near Block E.

### Block I — I2C Pull-ups
**Components**: r_sda_pu (2.2k), r_scl_pu (2.2k)
**Placement**: Central location near MCU, on the I2C bus trunk before it fans out to sensors/Qwiic

### Block J — External NTC Thermistor (ADS1115)
**Components**: ADS1115IRUGR (X2QFN-10), R_ref (10k 0.1% 0402), C_dec (100nF 0402), CN_ntc (JST PH 2-pin)
**Placement rules**:
- ADS1115 near fuel gauge (Block F) — both on I2C bus, both always-on
- R_ref within 3mm of ADS1115 AIN0 pin (short high-impedance trace)
- C_dec within 2mm of ADS1115 VDD pin
- CN_ntc at board edge — NTC probe cable exits enclosure, only metal tip protrudes
- Keep analog input traces away from MPPT switching noise and I2C clock lines
- Guard AIN0 trace with GND on adjacent layers

### Block K — Mounting Holes
**Components**: 4x MountingHole_3.2_M3
**Placement**: 4 corners of the board, inset ~3mm from edges

## Recommended Floor Plan (60x48mm target)

```
┌─────────────────────────────────────────────────────────┐
│ [MH]                                             [MH]  │
│                                                         │
│  ┌─────────┐  ┌──────────┐  ┌───────────────────────┐  │
│  │ MPPT    │  │ LDO      │  │ ESP32-C6-MINI-1       │  │
│  │ Block A │  │ Block C  │  │ Block D               │  │
│  │         │  │ +100µF   │  │                       │  │
│  │ L1  IC  │  │          │  │         ┌─────────┐   │  │
│  │         │  │          │  │         │ ANTENNA │   │  │
│  └─────────┘  └──────────┘  │         │ KEEPOUT │   │  │
│  [J_solar]                   │         └─────────┘   │  │
│  [J_batt] [BPC]             └───────────────────────┘  │
│                                                         │
│  ┌───────┐ ┌───────┐  [I2C PU]  ┌────┐ ┌────┐         │
│  │SHT40  │ │VEML   │            │Qwc1│ │Qwc2│  [USB-C]│
│  │Block E│ │7700   │  [Fuel     └────┘ └────┘         │
│  └───────┘ └───────┘   Gauge]    Block G               │
│  [CN_ntc]   [ADS1115]  Block F                         │
│              Block J                                    │
│ [MH]                                             [MH]  │
└─────────────────────────────────────────────────────────┘

Power flow: Solar → MPPT → Battery → LDO → 3.3V → MCU/Sensors
Signal flow: Sensors → I2C bus → MCU → Zigbee antenna (RF out)
```

## Placement Priority Order

1. **ESP32-C6 module** — largest component, antenna determines board edge orientation
2. **MPPT IC + inductor** — high-current switching, needs tight layout
3. **LDO + bulk cap** — power path between MPPT and MCU
4. **Connectors** (solar, battery, USB-C, Qwiic) — board edges
5. **Sensors** (SHT40, VEML7700) — thermal/optical considerations
6. **Fuel gauge** (MAX17048) — near battery + MCU
7. **Load switches** — in power path, near their respective blocks
8. **NTC ADC** (ADS1115) — near fuel gauge, NTC connector at board edge
9. **Passives** — close to their parent ICs
10. **Mounting holes** — 4 corners

## Critical Layout Rules

1. **Antenna keepout**: 3.5mm clearance, no copper on any layer
2. **MPPT switching loop**: Minimize area of L1→LX→VOUT→Cout→GND loop
3. **Current sense**: Rs (10mΩ) Kelvin connection — separate sense and power traces
4. **Ground plane**: Continuous on layer 2, split only if necessary between analog/digital
5. **Thermal relief**: SHT40 needs thermal isolation from hot components
6. **High-impedance traces**: R1/R2 voltage divider, MPPT sense lines — guard with ground
7. **Power traces**: Battery and 3.3V rails minimum 0.5mm width, 1mm preferred
8. **NTC analog trace**: AIN0 from R_ref/NTC junction to ADS1115 — short, guarded with GND, away from MPPT/I2C clock

## GPIO Quick Reference

| GPIO | Function | Direction | Connected To |
|------|----------|-----------|-------------|
| IO0  | MPPT gate | Output (active low) | SI2301CDS gate → MPPT power |
| IO1  | Sensor gate | Output (active low) | SI2301CDS gate → sensor rail |
| IO2  | Battery alert | Input (active low) | MAX17048 nALRT |
| IO6  | I2C SDA | Bidirectional | All sensors + Qwiic |
| IO7  | I2C SCL | Output | All sensors + Qwiic |
| IO9  | Boot select | Input (pulled high) | Boot button to GND |
| IO12 | USB D- | Bidirectional | USB-C connector |
| IO13 | USB D+ | Bidirectional | USB-C connector |
| IO16 | UART TX | Output | Debug header (optional) |
| IO17 | UART RX | Input | Debug header (optional) |

## How to Execute

After restarting Claude Code (to load the kicad-pcb MCP server):

```
Use the pcb-placement-specialist agent to place components according to
this strategy document. The KiCad MCP tools are configured as "kicad-pcb"
and expose: list_pcb_footprints, get_pcb_statistics, setup_pcb_layout,
analyze_pcb_nets, run_drc, export_gerber.

PCB file: layouts/default/default.kicad_pcb
Strategy: docs/pcb_placement_strategy.md
```
