#!/usr/bin/env python3
"""Place components on the PCB according to the placement strategy.

Board: 60x48mm, edge cuts at (100,78) to (160,126).
Floor plan:
  Top-left: MPPT (Block A) — U3/SPV1040T + L1 inductor + passives
  Top-center: LDO (Block C) — U6/HT7833 + bulk cap
  Top-right: ESP32-C6 (Block D) — U5 module, antenna faces right edge
  Left edge: Solar/Battery connectors, Battery Protection (Block B)
  Bottom-left: Sensors (Block E) — SHT40, VEML7700
  Bottom-center: Fuel Gauge (Block F) — MAX17048
  Bottom-right: Qwiic (Block G), USB-C, buttons
"""

import re
import shutil
import sys
from pathlib import Path

PCB_FILE = Path("layouts/default/default.kicad_pcb")

# Target placements: reference -> (x, y, rotation_degrees)
# Board: (100,78) to (160,126) = 60x48mm
PLACEMENTS = {
    # === Mounting Holes (3mm inset from edges) ===
    "H1": (103, 81, 0),
    "H2": (157, 81, 0),
    "H3": (103, 123, 0),
    "H4": (157, 123, 0),

    # === Block D — ESP32-C6 MCU (Priority 1, top-right) ===
    # 90° rotation: antenna (top end at 0°) faces right toward board edge
    # Module body ~(143,84) to (157,100) with antenna keepout x>155
    "U5": (150, 92, 90),
    # Decoupling caps within 2mm of P3V3 pin (left side of module)
    "C12": (142, 87, 0),      # c_dec_1 10µF
    "C13": (142, 89, 0),      # c_dec_2 100nF
    "R16": (142, 91, 0),      # r_en 10k
    "C14": (142, 93, 90),     # c_en 1µF
    "R17": (142, 95, 0),      # r_boot 10k
    # Buttons — accessible from board edge area
    "SW1": (137, 103, 0),     # BOOT button (5.1x5.1mm)
    "SW2": (137, 110, 0),     # RESET button (5.1x5.1mm)

    # === USB-C area (right edge, bottom) ===
    "USBC1": (157, 115, -90),  # USB-C connector at right board edge
    "R18": (153, 110, 0),      # CC1 5.1k
    "R19": (153, 112, 0),      # CC2 5.1k
    "D2": (149, 115, 0),       # SRV05-4 USB ESD protection

    # === Block A — Solar MPPT Charger (Priority 2, top-left) ===
    # SPV1040T + inductor switching loop must be tight
    "U3": (112, 90, 0),       # SPV1040T TSSOP-8
    "L1": (106, 86, 0),       # XAL6060 inductor (6.6x6.4mm), <3mm from LX
    "C6": (106, 93, 90),      # Cin 10µF 0603, near VIN
    "C8": (117, 86, 90),      # Cout 10µF 0603, near VOUT
    "C7": (119, 86, 90),      # Cout2 4.7µF 0603, near VOUT
    "R11": (117, 89, 0),      # Rs 10mΩ R1206 current sense
    "R10": (115, 93, 0),      # Voltage divider near VCTRL
    "R5": (117, 93, 0),       # Voltage divider near VCTRL
    "R7": (108, 91, 0),       # Rf1 near IC
    "R9": (112, 94, 0),       # Rf2 near IC
    "C5": (108, 93, 0),       # Cinsns
    "C9": (115, 91, 0),       # Coutsns
    "C4": (114, 87, 0),       # Cf
    "R6": (110, 94, 0),       # R3 near IC
    "D1": (106, 97, 0),       # SRV05-4 solar ESD
    "D3": (111, 97, 0),       # Schottky reverse polarity diode

    # === Connectors (left board edge) ===
    "CN3": (103, 100, 90),    # Solar JST PH 2-pin, left edge
    "CN1": (103, 107, 90),    # Battery/Load JST PH 2-pin, left edge

    # === Block B — Battery Protection (between connectors and MPPT output) ===
    "U2": (113, 104, 0),      # XB3306D SOT-23-3
    "C3": (115, 103, 0),      # C_bpc 100nF bypass
    "R8": (115, 106, 0),      # R_bpc 100Ω

    # === Block C — LDO Power (top-center, between MPPT and ESP32) ===
    "U6": (128, 86, 0),       # HT7833 SOT-23-5
    "C15": (125, 84, 0),      # c_in 1µF near VIN
    "C16": (131, 84, 0),      # c_out 1µF near VOUT
    "R2": (131, 89, 0),       # c_bulk 100µF 0805 (misnamed ref, critical for TX)

    # === Block E — Sensors (bottom-left, away from heat) ===
    "U4": (109, 117, 0),      # SHT40 DFN-4, thermal isolation
    "LED1": (117, 117, 0),    # VEML7700 light sensor, near edge
    "C10": (109, 120, 0),     # SHT40 decoupling 100nF
    "C11": (117, 120, 0),     # VEML7700 decoupling 100nF

    # === Block F — Fuel Gauge (bottom-center) ===
    "U1": (130, 115, 180),    # MAX17048 TDFN-8
    "C1": (128, 113, 0),      # Bypass cap 1µF
    "C2": (133, 113, -90),    # Battery cap 1µF
    "R1": (128, 117, 0),      # Pulldown 10k
    "R4": (133, 117, 0),      # Alert pullup 10k
    "Q1": (130, 119, 0),      # q_pulldown (R0402 footprint)

    # === Block G — Qwiic Connectors (bottom-right area) ===
    "CN4": (145, 116, -90),   # Qwiic 1 BM04B-SRSS-TB
    "CN5": (145, 122, -90),   # Qwiic 2 BM04B-SRSS-TB

    # === Block H — Load Switch (near Block A/B) ===
    "Q2": (120, 101, 0),      # SI2301CDS MPPT gate switch SOT-23-3

    # === Block I — I2C Pull-ups (central, near MCU on I2C trunk) ===
    "R13": (137, 99, 0),      # SDA pullup 2.2k
    "R15": (137, 101, 0),     # SCL pullup 2.2k
}


def find_footprint_ranges(content: str) -> dict[str, tuple[int, int, int]]:
    """Find the byte ranges of each footprint block and the position line offset.

    Returns dict of ref -> (block_start, block_end, at_line_start).
    """
    results = {}
    # Match top-level footprint blocks
    fp_starts = [m.start() for m in re.finditer(r'^\t\(footprint ', content, re.MULTILINE)]

    for fp_start in fp_starts:
        # Find the (at X Y [rot]) line — it's the first (at ...) after (footprint
        at_match = re.search(
            r'\n(\t\t\(at\s+[\d.\-]+\s+[\d.\-]+(?:\s+[\d.\-]+)?\))',
            content[fp_start:fp_start + 500],
        )
        if not at_match:
            continue

        # Find the reference property
        ref_match = re.search(
            r'\(property\s+"Reference"\s+"([^"]+)"',
            content[fp_start:fp_start + 1000],
        )
        if not ref_match:
            continue

        ref = ref_match.group(1)
        at_abs_start = fp_start + at_match.start(1)
        at_abs_end = fp_start + at_match.end(1)
        results[ref] = (at_abs_start, at_abs_end)

    return results


def format_at(x: float, y: float, rot: float) -> str:
    """Format an (at ...) S-expression."""
    # Format numbers: use int if whole, else float
    def fmt(v):
        return str(int(v)) if v == int(v) else str(v)

    if rot == 0:
        return f"\t\t(at {fmt(x)} {fmt(y)})"
    else:
        return f"\t\t(at {fmt(x)} {fmt(y)} {fmt(rot)})"


def main():
    if not PCB_FILE.exists():
        print(f"ERROR: PCB file not found: {PCB_FILE}")
        sys.exit(1)

    # Backup
    backup = PCB_FILE.with_suffix(".kicad_pcb.bak")
    shutil.copy2(PCB_FILE, backup)
    print(f"Backup saved to {backup}")

    content = PCB_FILE.read_text()
    ranges = find_footprint_ranges(content)

    print(f"\nFound {len(ranges)} footprints with references in PCB")
    print(f"Placement targets: {len(PLACEMENTS)} components\n")

    # Check which targets are missing from PCB
    missing = set(PLACEMENTS.keys()) - set(ranges.keys())
    if missing:
        print(f"WARNING: These refs are in placement plan but not in PCB: {sorted(missing)}")

    extra = set(ranges.keys()) - set(PLACEMENTS.keys())
    if extra:
        print(f"NOTE: These refs are in PCB but not in placement plan: {sorted(extra)}")

    # Apply placements — process from end to start to preserve offsets
    edits = []
    for ref, (x, y, rot) in PLACEMENTS.items():
        if ref not in ranges:
            continue
        start, end = ranges[ref]
        new_at = format_at(x, y, rot)
        edits.append((start, end, new_at, ref))

    # Sort by position descending so replacements don't shift offsets
    edits.sort(key=lambda e: e[0], reverse=True)

    for start, end, new_at, ref in edits:
        old_at = content[start:end]
        content = content[:start] + new_at + content[end:]
        print(f"  {ref:>6}: {old_at.strip()} -> {new_at.strip()}")

    PCB_FILE.write_text(content)
    print(f"\nPlaced {len(edits)} components. PCB saved to {PCB_FILE}")
    print("Open in KiCad to verify placement and adjust as needed.")


if __name__ == "__main__":
    main()
