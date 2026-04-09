# ADR-001: External NTC Thermistor with ADS1115 ADC

## Status

Accepted

## Context

The onboard SHT40 temperature sensor is mounted on the PCB inside a solar-exposed enclosure. During sunny conditions, the PCB heats up significantly (measured 15-20 degC above ambient), making the onboard reading unreliable for true ambient temperature. The node needs accurate outdoor temperature for plant care decisions.

Requirements:
- Range: -30 to +100 degC
- Resolution: 0.1 degC
- Only the metal sensing tip protrudes from the enclosure
- Short cable (10-30 cm)
- Low cost, simple integration

## Decision

Use an external 10k NTC thermistor probe with a dedicated ADS1115 16-bit delta-sigma ADC for readout. The NTC connects via a JST PH 2-pin connector. A precision 10k 0.1% reference resistor (YAGEO RT0402BRD0710KL, 25ppm/degC) forms a voltage divider read by the ADS1115.

The ADS1115 is on the always-on 3.3V rail (not the switched sensor rail) with I2C address 0x48.

Firmware will use Steinhart-Hart 3-point calibration to achieve +/-0.1 degC absolute accuracy from a standard +/-1% NTC probe.

## Consequences

### Positive
- True ambient temperature independent of enclosure heating
- 0.02 degC ADC resolution (16-bit) far exceeds the 0.1 degC target
- ADS1115 shares existing I2C bus — no additional GPIOs needed
- NTC probe is cheap (~1-3 EUR) and mechanically simple

### Negative
- Adds 4 components to BOM: ADS1115 (1.92 EUR), precision resistor, decoupling cap, JST connector
- Requires firmware Steinhart-Hart calibration per probe
- NTC nonlinearity requires lookup table or polynomial for accuracy across full range

### Neutral
- ADS1115 has 4 analog inputs — 3 are unused and available for future sensors
- I2C bus now has 5 devices (SHT40, VEML7700, MAX17048, ADS1115, + Qwiic) — well within bus capacity

## Alternatives Considered

| Alternative | Why Rejected |
|---|---|
| ESP32-C6 internal ADC (12-bit) | INL +/-5 LSB gives +/-0.6 degC — insufficient for 0.1 degC target |
| External digital probe (DS18B20, 1-Wire) | Requires additional GPIO + 1-Wire protocol; 0.5 degC accuracy without calibration |
| External SHT40 on cable (I2C) | I2C not reliable over cables >10cm without bus extender; address conflict with onboard SHT40 |
| Pt1000 RTD | More linear and accurate but requires excitation current source or Wheatstone bridge — more complex circuit for marginal benefit over calibrated NTC |

## References

- ADS1115 datasheet: Texas Instruments SBAS444
- NTC Steinhart-Hart calibration: Steinhart & Hart, 1968, "Calibration curves for thermistors"
- YAGEO RT0402BRD0710KL: 10k 0.1% thin film, 25ppm/degC

---
*ADRs are immutable once Accepted. To revise, create a new ADR with status "Supersedes ADR-001".*
