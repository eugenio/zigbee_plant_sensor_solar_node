"""Generate a KiCad 9 schematic (.kicad_sch) for the Zigbee Plant Sensor Solar Node."""

import uuid
import os
from dataclasses import dataclass, field
from typing import Optional

OUTPUT_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "layouts", "default", "default.kicad_sch",
)

# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------

def uid() -> str:
    return str(uuid.uuid4())


def sexp_str(s: str) -> str:
    """Escape a string for S-expression."""
    return f'"{s}"'


GRID = 2.54  # mm


def snap(v: float) -> float:
    """Snap to 2.54 mm grid."""
    return round(round(v / GRID) * GRID, 4)


# ---------------------------------------------------------------------------
# data model helpers
# ---------------------------------------------------------------------------

@dataclass
class Pin:
    number: str
    name: str
    etype: str = "passive"  # passive, input, output, bidirectional, power_in, power_out, unspecified
    x: float = 0
    y: float = 0
    angle: float = 0  # 0=right, 90=up, 180=left, 270=down
    length: float = 2.54


@dataclass
class SymbolDef:
    lib_id: str  # e.g. "Device:R"
    name: str    # symbol name inside lib
    pins: list   # list[Pin]
    width: float = 5.08  # body rect half-width
    height: float = 5.08  # body rect half-height
    reference_prefix: str = "U"
    show_pin_names: bool = True
    show_pin_numbers: bool = True


@dataclass
class PlacedSymbol:
    reference: str
    lib_id: str
    x: float
    y: float
    angle: float = 0
    mirror: str = ""
    properties: dict = field(default_factory=dict)
    unit: int = 1


@dataclass
class Wire:
    x1: float
    y1: float
    x2: float
    y2: float


@dataclass
class NetLabel:
    text: str
    x: float
    y: float
    angle: float = 0


@dataclass
class PowerSymbol:
    """GND or +3V3 power port (flag)."""
    name: str
    reference: str
    x: float
    y: float
    angle: float = 0


@dataclass
class Junction:
    x: float
    y: float


# ---------------------------------------------------------------------------
# Symbol library definitions
# ---------------------------------------------------------------------------

def _make_rect_symbol(lib_id: str, name: str, prefix: str,
                      left_pins: list, right_pins: list,
                      pin_length: float = 2.54,
                      body_w: float = 10.16,
                      show_pin_names: bool = True) -> str:
    """Build an S-expression lib_symbol block for a rectangular IC.

    left_pins / right_pins: list of (number:str, name:str, etype:str)
    Pin spacing is 2.54 mm between pins, centered vertically.
    """
    n_left = len(left_pins)
    n_right = len(right_pins)
    n_max = max(n_left, n_right, 1)
    body_h = max(n_max * GRID, 2 * GRID)  # half-heights will be body_h/2
    half_w = body_w / 2
    half_h = body_h / 2

    lines = []
    lines.append(f'    (symbol {sexp_str(lib_id)}')
    lines.append(f'      (pin_names (offset 1.016){"" if show_pin_names else " hide"})')
    lines.append(f'      (exclude_from_sim no)')
    lines.append(f'      (in_bom yes)')
    lines.append(f'      (on_board yes)')

    # sub-symbol _0_1: body rectangle
    lines.append(f'      (symbol {sexp_str(name + "_0_1")}')
    lines.append(f'        (rectangle (start {-half_w} {-half_h}) (end {half_w} {half_h})')
    lines.append(f'          (stroke (width 0.254) (type default))')
    lines.append(f'          (fill (type background))')
    lines.append(f'        )')
    lines.append(f'      )')

    # sub-symbol _1_1: pins
    lines.append(f'      (symbol {sexp_str(name + "_1_1")}')

    # left pins (facing right => angle 0)
    for i, (pnum, pname, petype) in enumerate(left_pins):
        py = -half_h + GRID + i * GRID if n_left > 1 else 0
        px = -half_w - pin_length
        lines.append(
            f'        (pin {petype} line (at {px} {py} 0) (length {pin_length})'
            f' (name {sexp_str(pname)}) (number {sexp_str(pnum)}))'
        )

    # right pins (facing left => angle 180)
    for i, (pnum, pname, petype) in enumerate(right_pins):
        py = -half_h + GRID + i * GRID if n_right > 1 else 0
        px = half_w + pin_length
        lines.append(
            f'        (pin {petype} line (at {px} {py} 180) (length {pin_length})'
            f' (name {sexp_str(pname)}) (number {sexp_str(pnum)}))'
        )

    lines.append(f'      )')

    # property templates (Reference, Value, Footprint, Datasheet)
    ref_id = uid()
    val_id = uid()
    lines.append(f'      (property "Reference" {sexp_str(prefix)}')
    lines.append(f'        (at 0 {half_h + 2.54} 0) (effects (font (size 1.27 1.27))))')
    lines.append(f'      (property "Value" {sexp_str(name)}')
    lines.append(f'        (at 0 {-(half_h + 2.54)} 0) (effects (font (size 1.27 1.27))))')
    lines.append(f'      (property "Footprint" ""')
    lines.append(f'        (at 0 0 0) (effects (font (size 1.27 1.27)) hide))')
    lines.append(f'      (property "Datasheet" ""')
    lines.append(f'        (at 0 0 0) (effects (font (size 1.27 1.27)) hide))')

    lines.append(f'    )')
    return "\n".join(lines)


def _make_2pin_symbol(lib_id: str, name: str, prefix: str,
                      pin1_name: str = "1", pin2_name: str = "2",
                      body_type: str = "rect") -> str:
    """2-pin passive symbol (resistor/capacitor/inductor/fuse/diode)."""
    # simple vertical rectangle body, pin 1 top, pin 2 bottom
    half_h = 2.54
    half_w = 1.27

    lines = []
    lines.append(f'    (symbol {sexp_str(lib_id)}')
    lines.append(f'      (pin_names (offset 0) hide)')
    lines.append(f'      (exclude_from_sim no)')
    lines.append(f'      (in_bom yes)')
    lines.append(f'      (on_board yes)')

    lines.append(f'      (symbol {sexp_str(name + "_0_1")}')
    lines.append(f'        (rectangle (start {-half_w} {-half_h}) (end {half_w} {half_h})')
    lines.append(f'          (stroke (width 0.254) (type default))')
    lines.append(f'          (fill (type background))')
    lines.append(f'        )')
    lines.append(f'      )')

    lines.append(f'      (symbol {sexp_str(name + "_1_1")}')
    # pin 1 at top (facing down = 270)
    lines.append(
        f'        (pin passive line (at 0 {half_h + 2.54} 270) (length 2.54)'
        f' (name {sexp_str(pin1_name)}) (number "1"))'
    )
    # pin 2 at bottom (facing up = 90)
    lines.append(
        f'        (pin passive line (at 0 {-(half_h + 2.54)} 90) (length 2.54)'
        f' (name {sexp_str(pin2_name)}) (number "2"))'
    )
    lines.append(f'      )')

    lines.append(f'      (property "Reference" {sexp_str(prefix)}')
    lines.append(f'        (at 2.54 0 0) (effects (font (size 1.27 1.27)) (justify left)))')
    lines.append(f'      (property "Value" {sexp_str(name)}')
    lines.append(f'        (at 2.54 -2.54 0) (effects (font (size 1.27 1.27)) (justify left)))')
    lines.append(f'      (property "Footprint" ""')
    lines.append(f'        (at 0 0 0) (effects (font (size 1.27 1.27)) hide))')
    lines.append(f'      (property "Datasheet" ""')
    lines.append(f'        (at 0 0 0) (effects (font (size 1.27 1.27)) hide))')

    lines.append(f'    )')
    return "\n".join(lines)


def _make_power_symbol(lib_id: str, name: str, is_gnd: bool = True) -> str:
    """Power port symbol (GND or supply rail)."""
    lines = []
    lines.append(f'    (symbol {sexp_str(lib_id)}')
    lines.append(f'      (power)')
    lines.append(f'      (pin_names (offset 0) hide)')
    lines.append(f'      (exclude_from_sim no)')
    lines.append(f'      (in_bom yes)')
    lines.append(f'      (on_board yes)')

    lines.append(f'      (symbol {sexp_str(name + "_0_1")}')
    if is_gnd:
        # GND triangle
        lines.append(f'        (polyline (pts (xy 0 0) (xy 0 -1.27) (xy -1.27 -1.27)'
                     f' (xy 0 -2.54) (xy 1.27 -1.27) (xy 0 -1.27))')
        lines.append(f'          (stroke (width 0) (type default))')
        lines.append(f'          (fill (type outline))')
        lines.append(f'        )')
    else:
        # bar on top
        lines.append(f'        (polyline (pts (xy -1.27 1.27) (xy 1.27 1.27))')
        lines.append(f'          (stroke (width 0.254) (type default))')
        lines.append(f'          (fill (type none))')
        lines.append(f'        )')
        lines.append(f'        (polyline (pts (xy 0 0) (xy 0 1.27))')
        lines.append(f'          (stroke (width 0) (type default))')
        lines.append(f'          (fill (type none))')
        lines.append(f'        )')
    lines.append(f'      )')

    lines.append(f'      (symbol {sexp_str(name + "_1_1")}')
    pin_etype = "power_in"
    if is_gnd:
        lines.append(
            f'        (pin {pin_etype} line (at 0 0 0) (length 0)'
            f' (name {sexp_str(name)}) (number "1"))'
        )
    else:
        lines.append(
            f'        (pin {pin_etype} line (at 0 0 0) (length 0)'
            f' (name {sexp_str(name)}) (number "1"))'
        )
    lines.append(f'      )')

    lines.append(f'      (property "Reference" "#PWR"')
    lines.append(f'        (at 0 {-5.08 if is_gnd else 5.08} 0) (effects (font (size 1.27 1.27)) hide))')
    lines.append(f'      (property "Value" {sexp_str(name)}')
    lines.append(f'        (at 0 {-3.81 if is_gnd else 2.54} 0) (effects (font (size 1.27 1.27))))')
    lines.append(f'      (property "Footprint" ""')
    lines.append(f'        (at 0 0 0) (effects (font (size 1.27 1.27)) hide))')
    lines.append(f'      (property "Datasheet" ""')
    lines.append(f'        (at 0 0 0) (effects (font (size 1.27 1.27)) hide))')

    lines.append(f'    )')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Build all library symbols needed
# ---------------------------------------------------------------------------

def build_lib_symbols() -> str:
    syms = []

    # ---- Power symbols ----
    syms.append(_make_power_symbol("power:GND", "GND", is_gnd=True))
    syms.append(_make_power_symbol("power:+3V3", "+3V3", is_gnd=False))
    syms.append(_make_power_symbol("power:Vbatr", "Vbatr", is_gnd=False))
    syms.append(_make_power_symbol("power:Vpvr", "Vpvr", is_gnd=False))

    # ---- 2-pin passives ----
    syms.append(_make_2pin_symbol("Device:R", "R", "R"))
    syms.append(_make_2pin_symbol("Device:C", "C", "C"))
    syms.append(_make_2pin_symbol("Device:L", "L", "L"))
    syms.append(_make_2pin_symbol("Device:Fuse", "Fuse", "F"))
    syms.append(_make_2pin_symbol("Device:D", "D", "D", pin1_name="K", pin2_name="A"))

    # ---- Switch (2-pin) ----
    syms.append(_make_2pin_symbol("Switch:SW_Push", "SW_Push", "SW", pin1_name="A", pin2_name="B"))

    # ---- Connectors ----
    # 2-pin JST
    syms.append(_make_rect_symbol(
        "Connector_Generic:Conn_01x02", "Conn_01x02", "CN",
        left_pins=[("1", "1", "passive"), ("2", "2", "passive")],
        right_pins=[],
        body_w=5.08,
    ))

    # 4-pin Qwiic
    syms.append(_make_rect_symbol(
        "Connector_Generic:Conn_01x04", "Conn_01x04", "CN",
        left_pins=[("1", "GND", "passive"), ("2", "VCC", "passive"),
                   ("3", "SDA", "passive"), ("4", "SCL", "passive")],
        right_pins=[],
        body_w=5.08,
    ))

    # USB-C simplified
    syms.append(_make_rect_symbol(
        "Connector:USB_C", "USB_C", "USBC",
        left_pins=[
            ("A4B9", "VBUS", "power_in"),
            ("A1B12", "GND", "passive"),
            ("A5", "CC1", "bidirectional"),
            ("B5", "CC2", "bidirectional"),
            ("A6", "D-", "bidirectional"),
            ("A7", "D+", "bidirectional"),
            ("1", "SHIELD", "passive"),
        ],
        right_pins=[],
        body_w=7.62,
    ))

    # ---- ICs ----
    # U1 MAX17048 fuel gauge
    syms.append(_make_rect_symbol(
        "custom:MAX17048", "MAX17048", "U",
        left_pins=[
            ("3", "VDD", "power_in"),
            ("2", "CELL", "input"),
            ("1", "GND1", "power_in"),
            ("4", "GND2", "power_in"),
            ("9", "EPAD", "passive"),
        ],
        right_pins=[
            ("5", "~{ALRT}", "output"),
            ("6", "QSTRT", "input"),
            ("7", "SCL", "bidirectional"),
            ("8", "SDA", "bidirectional"),
        ],
        body_w=12.7,
    ))

    # U2 XB3306D battery protection
    syms.append(_make_rect_symbol(
        "custom:XB3306D", "XB3306D", "U",
        left_pins=[
            ("1", "GND", "power_in"),
            ("2", "IN", "input"),
        ],
        right_pins=[
            ("3", "OUT", "output"),
        ],
        body_w=10.16,
    ))

    # U3 SPV1040T MPPT
    syms.append(_make_rect_symbol(
        "custom:SPV1040T", "SPV1040T", "U",
        left_pins=[
            ("1", "VIN_SNS+", "input"),
            ("8", "VIN_SNS-", "input"),
            ("2", "GND", "power_in"),
            ("3", "LX", "output"),
        ],
        right_pins=[
            ("4", "VOUT", "power_out"),
            ("5", "VOUT_SNS", "input"),
            ("7", "MPPT+", "input"),
            ("6", "MPPT-", "input"),
        ],
        body_w=15.24,
    ))

    # U4 SHT40
    syms.append(_make_rect_symbol(
        "custom:SHT40", "SHT40", "U",
        left_pins=[
            ("3", "VDD", "power_in"),
            ("4", "GND", "power_in"),
            ("5", "EPAD", "passive"),
        ],
        right_pins=[
            ("1", "SDA", "bidirectional"),
            ("2", "SCL", "bidirectional"),
        ],
        body_w=10.16,
    ))

    # U5 ESP32-C6-MINI simplified
    syms.append(_make_rect_symbol(
        "custom:ESP32_C6_MINI", "ESP32_C6_MINI", "U",
        left_pins=[
            ("3", "3V3", "power_in"),
            ("1", "GND", "power_in"),
            ("8", "EN", "input"),
            ("23", "GPIO9", "bidirectional"),
        ],
        right_pins=[
            ("15", "SDA", "bidirectional"),
            ("16", "SCL", "bidirectional"),
            ("17", "USB_D+", "bidirectional"),
            ("18", "USB_D-", "bidirectional"),
        ],
        body_w=17.78,
    ))

    # U6 HT7833 LDO
    syms.append(_make_rect_symbol(
        "custom:HT7833", "HT7833", "U",
        left_pins=[
            ("1", "VIN", "power_in"),
            ("2", "GND", "power_in"),
        ],
        right_pins=[
            ("5", "VOUT", "power_out"),
        ],
        body_w=10.16,
    ))

    # LED1 VEML7700
    syms.append(_make_rect_symbol(
        "custom:VEML7700", "VEML7700", "LED",
        left_pins=[
            ("2", "VDD", "power_in"),
            ("3", "GND", "power_in"),
        ],
        right_pins=[
            ("1", "SCL", "bidirectional"),
            ("4", "SDA", "bidirectional"),
        ],
        body_w=10.16,
    ))

    # D1 SRV05-4 (6-pin ESD)
    syms.append(_make_rect_symbol(
        "custom:SRV05_4", "SRV05_4", "D",
        left_pins=[
            ("1", "GND1", "passive"),
            ("2", "GND2", "passive"),
            ("3", "GND3", "passive"),
        ],
        right_pins=[
            ("4", "VCC1", "passive"),
            ("5", "VCC2", "passive"),
            ("6", "VCC3", "passive"),
        ],
        body_w=10.16,
    ))

    return "  (lib_symbols\n" + "\n".join(syms) + "\n  )"


# ---------------------------------------------------------------------------
# Placed symbol S-expression
# ---------------------------------------------------------------------------

def _emit_placed_symbol(ref: str, lib_id: str, x: float, y: float,
                        value: str = "", angle: float = 0,
                        mirror: str = "", extra_props: dict = None) -> str:
    """Emit a placed symbol instance."""
    s_uuid = uid()
    pin_uuid_map = uid()

    angle_str = f"{angle}"

    lines = []
    lines.append(f'  (symbol (lib_id {sexp_str(lib_id)}) (at {x} {y} {angle_str})'
                 f' {"(mirror y)" if mirror == "y" else ""}'
                 f' (unit 1) (exclude_from_sim no) (in_bom yes) (on_board yes)'
                 f' (dnp no)')
    lines.append(f'    (uuid {uid()})')

    # Determine reference prefix for y-offset
    ref_y = y - 5.08
    val_y = y + 5.08

    lines.append(f'    (property "Reference" {sexp_str(ref)}'
                 f' (at {x} {ref_y} 0) (effects (font (size 1.27 1.27))))')
    lines.append(f'    (property "Value" {sexp_str(value if value else lib_id.split(":")[-1])}'
                 f' (at {x} {val_y} 0) (effects (font (size 1.27 1.27))))')
    lines.append(f'    (property "Footprint" ""'
                 f' (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))')
    lines.append(f'    (property "Datasheet" ""'
                 f' (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))')

    if extra_props:
        for k, v in extra_props.items():
            lines.append(f'    (property {sexp_str(k)} {sexp_str(v)}'
                         f' (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))')

    # pin instances - we don't know the pin map, but KiCad doesn't strictly require
    # pin UUIDs in the placed symbol for opening; it derives them.
    lines.append(f'    (instances (project "" (path "/"'
                 f' (reference {sexp_str(ref)}) (unit 1))))')

    lines.append(f'  )')
    return "\n".join(lines)


def _emit_power_flag(ref: str, lib_id: str, x: float, y: float,
                     value: str = "", angle: float = 0) -> str:
    """Emit a power flag (GND / +3V3 / Vbatr / Vpvr)."""
    lines = []
    lines.append(f'  (symbol (lib_id {sexp_str(lib_id)}) (at {x} {y} {angle})'
                 f' (unit 1) (exclude_from_sim no) (in_bom no) (on_board yes)'
                 f' (dnp no)')
    lines.append(f'    (uuid {uid()})')
    lines.append(f'    (property "Reference" {sexp_str(ref)}'
                 f' (at {x} {y - 2.54} 0) (effects (font (size 1.27 1.27)) hide))')
    lines.append(f'    (property "Value" {sexp_str(value if value else lib_id.split(":")[-1])}'
                 f' (at {x} {y + 2.54} 0) (effects (font (size 1.27 1.27))))')
    lines.append(f'    (property "Footprint" ""'
                 f' (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))')
    lines.append(f'    (property "Datasheet" ""'
                 f' (at {x} {y} 0) (effects (font (size 1.27 1.27)) hide))')
    lines.append(f'    (instances (project "" (path "/"'
                 f' (reference {sexp_str(ref)}) (unit 1))))')
    lines.append(f'  )')
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# Wire / Label / Junction helpers
# ---------------------------------------------------------------------------

def _emit_wire(x1, y1, x2, y2) -> str:
    return (f'  (wire (pts (xy {x1} {y1}) (xy {x2} {y2}))\n'
            f'    (stroke (width 0) (type default))\n'
            f'    (uuid {uid()}))')


def _emit_label(text, x, y, angle=0) -> str:
    return (f'  (label {sexp_str(text)} (at {x} {y} {angle})'
            f' (effects (font (size 1.27 1.27)))\n'
            f'    (uuid {uid()}))')


def _emit_junction(x, y) -> str:
    return (f'  (junction (at {x} {y}) (diameter 0) (color 0 0 0 0)\n'
            f'    (uuid {uid()}))')


def _emit_no_connect(x, y) -> str:
    return f'  (no_connect (at {x} {y}) (uuid {uid()}))'


# ---------------------------------------------------------------------------
# Main schematic assembly
# ---------------------------------------------------------------------------

def build_schematic() -> str:
    parts = []  # list of string fragments

    # file header
    file_uuid = uid()
    parts.append(f'(kicad_sch')
    parts.append(f'  (version 20231120)')
    parts.append(f'  (generator "python_generate_schematic")')
    parts.append(f'  (generator_version "9.0")')
    parts.append(f'  (uuid {sexp_str(file_uuid)})')
    parts.append(f'  (paper "A3")')

    # lib_symbols
    parts.append(build_lib_symbols())

    # ======================================================================
    # BLOCK 1: Solar Input + MPPT  (left region, x ~ 25..90)
    # ======================================================================
    bx, by = 30, 55  # base position

    # CN3 solar JST
    parts.append(_emit_placed_symbol("CN3", "Connector_Generic:Conn_01x02",
                                     bx, by, "Solar JST"))
    # CN3 pin 1 = Vpvr-hv at (bx - 2.54 - 2.54, by - 1.27) = left side
    cn3_p1_x = bx - 5.08 - 2.54
    cn3_p1_y = by - 1.27
    cn3_p2_x = cn3_p1_x
    cn3_p2_y = by + 1.27

    # wire from CN3 pin1 + label Vpvr
    parts.append(_emit_wire(cn3_p1_x, cn3_p1_y, cn3_p1_x - 5.08, cn3_p1_y))
    parts.append(_emit_label("Vpvr-hv", cn3_p1_x - 5.08, cn3_p1_y, 180))

    # GND on CN3 pin2
    parts.append(_emit_wire(cn3_p2_x, cn3_p2_y, cn3_p2_x - 5.08, cn3_p2_y))
    parts.append(_emit_power_flag("#PWR01", "power:GND", cn3_p2_x - 5.08, cn3_p2_y + 2.54))
    parts.append(_emit_wire(cn3_p2_x - 5.08, cn3_p2_y, cn3_p2_x - 5.08, cn3_p2_y + 2.54))

    # C6 across solar input
    c6x, c6y = bx + 10.16, by
    parts.append(_emit_placed_symbol("C6", "Device:C", c6x, c6y, "C6"))
    parts.append(_emit_wire(c6x, c6y - 5.08, c6x, c6y - 7.62))
    parts.append(_emit_label("Vpvr-hv", c6x, c6y - 7.62, 90))
    parts.append(_emit_wire(c6x, c6y + 5.08, c6x, c6y + 7.62))
    parts.append(_emit_power_flag("#PWR02", "power:GND", c6x, c6y + 7.62))

    # L1 inductor
    l1x, l1y = bx + 22.86, by - 10.16
    parts.append(_emit_placed_symbol("L1", "Device:L", l1x, l1y, "L1"))
    parts.append(_emit_wire(l1x, l1y - 5.08, l1x, l1y - 7.62))
    parts.append(_emit_label("Vpvr-hv", l1x, l1y - 7.62, 90))
    parts.append(_emit_wire(l1x, l1y + 5.08, l1x, l1y + 7.62))
    parts.append(_emit_label("LX", l1x, l1y + 7.62, 270))

    # U3 SPV1040T  center of MPPT block
    u3x, u3y = 65, 85
    parts.append(_emit_placed_symbol("U3", "custom:SPV1040T", u3x, u3y, "SPV1040T"))

    # U3 left pins at x = u3x - 15.24/2 - 2.54 = u3x - 10.16
    u3_lx = u3x - 15.24 / 2 - 2.54
    # U3 right pins at x = u3x + 15.24/2 + 2.54 = u3x + 10.16
    u3_rx = u3x + 15.24 / 2 + 2.54

    # Left side pins of U3: VIN_SNS+(1), VIN_SNS-(8), GND(2), LX(3)
    # They are at y offsets: -3.81, -1.27, 1.27, 3.81 from u3y
    u3_pins_left_y = [u3y - 3*GRID + GRID + i * GRID for i in range(4)]
    # pin 1 VIN_SNS+ -> Cinsns-power-hv
    parts.append(_emit_wire(u3_lx, u3_pins_left_y[0], u3_lx - 5.08, u3_pins_left_y[0]))
    parts.append(_emit_label("Cinsns-power-hv", u3_lx - 5.08, u3_pins_left_y[0], 180))
    # pin 8 VIN_SNS- -> same as pin 1 (both connect to Cinsns-power-hv)
    parts.append(_emit_wire(u3_lx, u3_pins_left_y[1], u3_lx - 5.08, u3_pins_left_y[1]))
    parts.append(_emit_label("Cinsns-power-hv", u3_lx - 5.08, u3_pins_left_y[1], 180))
    # pin 2 GND
    parts.append(_emit_wire(u3_lx, u3_pins_left_y[2], u3_lx - 5.08, u3_pins_left_y[2]))
    parts.append(_emit_power_flag("#PWR03", "power:GND", u3_lx - 5.08, u3_pins_left_y[2] + 2.54))
    parts.append(_emit_wire(u3_lx - 5.08, u3_pins_left_y[2], u3_lx - 5.08, u3_pins_left_y[2] + 2.54))
    # pin 3 LX
    parts.append(_emit_wire(u3_lx, u3_pins_left_y[3], u3_lx - 5.08, u3_pins_left_y[3]))
    parts.append(_emit_label("LX", u3_lx - 5.08, u3_pins_left_y[3], 180))

    # Right side pins of U3: VOUT(4), VOUT_SNS(5), MPPT+(7), MPPT-(6)
    u3_pins_right_y = [u3y - 3*GRID + GRID + i * GRID for i in range(4)]
    # pin 4 VOUT -> Cout1-power-hv
    parts.append(_emit_wire(u3_rx, u3_pins_right_y[0], u3_rx + 5.08, u3_pins_right_y[0]))
    parts.append(_emit_label("Cout1-power-hv", u3_rx + 5.08, u3_pins_right_y[0]))
    # pin 5 VOUT_SNS -> Coutsns-power-hv
    parts.append(_emit_wire(u3_rx, u3_pins_right_y[1], u3_rx + 5.08, u3_pins_right_y[1]))
    parts.append(_emit_label("Coutsns-power-hv", u3_rx + 5.08, u3_pins_right_y[1]))
    # pin 7 MPPT+ -> Cf-power-hv
    parts.append(_emit_wire(u3_rx, u3_pins_right_y[2], u3_rx + 5.08, u3_pins_right_y[2]))
    parts.append(_emit_label("Cf-power-hv", u3_rx + 5.08, u3_pins_right_y[2]))
    # pin 6 MPPT- -> Cf-power-lv
    parts.append(_emit_wire(u3_rx, u3_pins_right_y[3], u3_rx + 5.08, u3_pins_right_y[3]))
    parts.append(_emit_label("Cf-power-lv", u3_rx + 5.08, u3_pins_right_y[3]))

    # R7: Vpvr-hv / Cinsns-power-hv
    r7x, r7y = 45, 65
    parts.append(_emit_placed_symbol("R7", "Device:R", r7x, r7y, "R7"))
    parts.append(_emit_wire(r7x, r7y - 5.08, r7x, r7y - 7.62))
    parts.append(_emit_label("Vpvr-hv", r7x, r7y - 7.62, 90))
    parts.append(_emit_wire(r7x, r7y + 5.08, r7x, r7y + 7.62))
    parts.append(_emit_label("Cinsns-power-hv", r7x, r7y + 7.62, 270))

    # C5: Cinsns-power-hv / lv
    c5x, c5y = 50, 110
    parts.append(_emit_placed_symbol("C5", "Device:C", c5x, c5y, "C5"))
    parts.append(_emit_wire(c5x, c5y - 5.08, c5x, c5y - 7.62))
    parts.append(_emit_label("Cinsns-power-hv", c5x, c5y - 7.62, 90))
    parts.append(_emit_wire(c5x, c5y + 5.08, c5x, c5y + 7.62))
    parts.append(_emit_power_flag("#PWR04", "power:GND", c5x, c5y + 7.62))

    # C4: Cf-power-hv / Cf-power-lv
    c4x, c4y = 85, 110
    parts.append(_emit_placed_symbol("C4", "Device:C", c4x, c4y, "C4"))
    parts.append(_emit_wire(c4x, c4y - 5.08, c4x, c4y - 7.62))
    parts.append(_emit_label("Cf-power-hv", c4x, c4y - 7.62, 90))
    parts.append(_emit_wire(c4x, c4y + 5.08, c4x, c4y + 7.62))
    parts.append(_emit_label("Cf-power-lv", c4x, c4y + 7.62, 270))

    # R9: Cf-power-hv / Cout1-power-hv
    r9x, r9y = 90, 65
    parts.append(_emit_placed_symbol("R9", "Device:R", r9x, r9y, "R9"))
    parts.append(_emit_wire(r9x, r9y - 5.08, r9x, r9y - 7.62))
    parts.append(_emit_label("Cf-power-hv", r9x, r9y - 7.62, 90))
    parts.append(_emit_wire(r9x, r9y + 5.08, r9x, r9y + 7.62))
    parts.append(_emit_label("Cout1-power-hv", r9x, r9y + 7.62, 270))

    # R10: Cf-power-lv / Vbatr-hv
    r10x, r10y = 95, 110
    parts.append(_emit_placed_symbol("R10", "Device:R", r10x, r10y, "R10"))
    parts.append(_emit_wire(r10x, r10y - 5.08, r10x, r10y - 7.62))
    parts.append(_emit_label("Cf-power-lv", r10x, r10y - 7.62, 90))
    parts.append(_emit_wire(r10x, r10y + 5.08, r10x, r10y + 7.62))
    parts.append(_emit_label("Vbatr-hv", r10x, r10y + 7.62, 270))

    # R5: Vbatr-hv / Coutsns-power-hv
    r5x, r5y = 90, 45
    parts.append(_emit_placed_symbol("R5", "Device:R", r5x, r5y, "R5"))
    parts.append(_emit_wire(r5x, r5y - 5.08, r5x, r5y - 7.62))
    parts.append(_emit_label("Vbatr-hv", r5x, r5y - 7.62, 90))
    parts.append(_emit_wire(r5x, r5y + 5.08, r5x, r5y + 7.62))
    parts.append(_emit_label("Coutsns-power-hv", r5x, r5y + 7.62, 270))

    # R6: Coutsns-power-hv / lv
    r6x, r6y = 95, 45
    parts.append(_emit_placed_symbol("R6", "Device:R", r6x, r6y, "R6"))
    parts.append(_emit_wire(r6x, r6y - 5.08, r6x, r6y - 7.62))
    parts.append(_emit_label("Coutsns-power-hv", r6x, r6y - 7.62, 90))
    parts.append(_emit_wire(r6x, r6y + 5.08, r6x, r6y + 7.62))
    parts.append(_emit_power_flag("#PWR05", "power:GND", r6x, r6y + 7.62))

    # R11: Cout1-power-hv / Vbatr-hv
    r11x, r11y = 85, 65
    parts.append(_emit_placed_symbol("R11", "Device:R", r11x, r11y, "R11"))
    parts.append(_emit_wire(r11x, r11y - 5.08, r11x, r11y - 7.62))
    parts.append(_emit_label("Cout1-power-hv", r11x, r11y - 7.62, 90))
    parts.append(_emit_wire(r11x, r11y + 5.08, r11x, r11y + 7.62))
    parts.append(_emit_label("Vbatr-hv", r11x, r11y + 7.62, 270))

    # C7: Cout1-power-hv / lv
    c7x, c7y = 80, 110
    parts.append(_emit_placed_symbol("C7", "Device:C", c7x, c7y, "C7"))
    parts.append(_emit_wire(c7x, c7y - 5.08, c7x, c7y - 7.62))
    parts.append(_emit_label("Cout1-power-hv", c7x, c7y - 7.62, 90))
    parts.append(_emit_wire(c7x, c7y + 5.08, c7x, c7y + 7.62))
    parts.append(_emit_power_flag("#PWR06", "power:GND", c7x, c7y + 7.62))

    # C8: Vbatr-hv / lv
    c8x, c8y = 100, 110
    parts.append(_emit_placed_symbol("C8", "Device:C", c8x, c8y, "C8"))
    parts.append(_emit_wire(c8x, c8y - 5.08, c8x, c8y - 7.62))
    parts.append(_emit_label("Vbatr-hv", c8x, c8y - 7.62, 90))
    parts.append(_emit_wire(c8x, c8y + 5.08, c8x, c8y + 7.62))
    parts.append(_emit_power_flag("#PWR07", "power:GND", c8x, c8y + 7.62))

    # C9: Coutsns-power-hv / lv
    c9x, c9y = 100, 45
    parts.append(_emit_placed_symbol("C9", "Device:C", c9x, c9y, "C9"))
    parts.append(_emit_wire(c9x, c9y - 5.08, c9x, c9y - 7.62))
    parts.append(_emit_label("Coutsns-power-hv", c9x, c9y - 7.62, 90))
    parts.append(_emit_wire(c9x, c9y + 5.08, c9x, c9y + 7.62))
    parts.append(_emit_power_flag("#PWR08", "power:GND", c9x, c9y + 7.62))

    # D1 SRV05-4 ESD protection near MPPT output
    d1x, d1y = 80, 45
    parts.append(_emit_placed_symbol("D1", "custom:SRV05_4", d1x, d1y, "SRV05-4"))
    # D1 left: GND pins
    d1_lx = d1x - 10.16 / 2 - 2.54
    d1_pins_left_y = [d1y - 2*GRID + GRID + i * GRID for i in range(3)]
    for i, py in enumerate(d1_pins_left_y):
        parts.append(_emit_wire(d1_lx, py, d1_lx - 2.54, py))
        parts.append(_emit_wire(d1_lx - 2.54, py, d1_lx - 2.54, py + 2.54 if i < 2 else py))
    parts.append(_emit_power_flag("#PWR09", "power:GND", d1_lx - 2.54, d1_pins_left_y[2] + 2.54))
    parts.append(_emit_wire(d1_lx - 2.54, d1_pins_left_y[2], d1_lx - 2.54, d1_pins_left_y[2] + 2.54))
    # D1 right: Cout1-power-hv
    d1_rx = d1x + 10.16 / 2 + 2.54
    d1_pins_right_y = [d1y - 2*GRID + GRID + i * GRID for i in range(3)]
    for i, py in enumerate(d1_pins_right_y):
        parts.append(_emit_wire(d1_rx, py, d1_rx + 2.54, py))
    parts.append(_emit_wire(d1_rx + 2.54, d1_pins_right_y[0], d1_rx + 2.54, d1_pins_right_y[2]))
    parts.append(_emit_label("Cout1-power-hv", d1_rx + 2.54, d1_pins_right_y[0]))

    # ======================================================================
    # BLOCK 2: Battery Protection  (x ~ 110..145)
    # ======================================================================
    # U2 XB3306D
    u2x, u2y = 120, 150
    parts.append(_emit_placed_symbol("U2", "custom:XB3306D", u2x, u2y, "XB3306D"))
    u2_lx = u2x - 10.16 / 2 - 2.54
    u2_rx = u2x + 10.16 / 2 + 2.54
    # pin 1 GND at top-left
    u2_p1y = u2y - 1 * GRID + GRID
    u2_p2y = u2y
    u2_p3y = u2y - 1 * GRID + GRID
    # left pins: GND(1) at y offset 0 from center - 1.27, IN(2) at center + 1.27
    u2_lpin_ys = [u2y - GRID + GRID, u2y + GRID - GRID]  # 2 left pins
    # Actually: 2 left pins spaced GRID apart
    u2_lpin0_y = u2y - GRID / 2  # pin1 GND
    u2_lpin1_y = u2y + GRID / 2  # pin2 IN
    # Recalculate based on the rect symbol:  n_left=2, half_h = max(2, 2)*GRID/2 = GRID
    # pins at -half_h + GRID + i*GRID = -GRID + GRID + i*GRID = i*GRID
    u2_lpin0_y = u2y  # pin1 GND  (i=0: offset 0)
    u2_lpin1_y = u2y + GRID  # pin2 IN  (i=1: offset GRID)

    parts.append(_emit_wire(u2_lx, u2_lpin0_y, u2_lx - 5.08, u2_lpin0_y))
    parts.append(_emit_power_flag("#PWR010", "power:GND", u2_lx - 5.08, u2_lpin0_y + 2.54))
    parts.append(_emit_wire(u2_lx - 5.08, u2_lpin0_y, u2_lx - 5.08, u2_lpin0_y + 2.54))

    parts.append(_emit_wire(u2_lx, u2_lpin1_y, u2_lx - 5.08, u2_lpin1_y))
    parts.append(_emit_label("C_bpc-power-hv", u2_lx - 5.08, u2_lpin1_y, 180))

    # right pin: OUT(3) -> cathode
    u2_rpin_y = u2y  # single right pin at center
    parts.append(_emit_wire(u2_rx, u2_rpin_y, u2_rx + 5.08, u2_rpin_y))
    parts.append(_emit_label("cathode", u2_rx + 5.08, u2_rpin_y))

    # C3: C_bpc-power-hv / cathode
    c3x, c3y = 120, 170
    parts.append(_emit_placed_symbol("C3", "Device:C", c3x, c3y, "C3"))
    parts.append(_emit_wire(c3x, c3y - 5.08, c3x, c3y - 7.62))
    parts.append(_emit_label("C_bpc-power-hv", c3x, c3y - 7.62, 90))
    parts.append(_emit_wire(c3x, c3y + 5.08, c3x, c3y + 7.62))
    parts.append(_emit_label("cathode", c3x, c3y + 7.62, 270))

    # R8: C_bpc-power-hv / Vbatr-hv
    r8x, r8y = 110, 140
    parts.append(_emit_placed_symbol("R8", "Device:R", r8x, r8y, "R8"))
    parts.append(_emit_wire(r8x, r8y - 5.08, r8x, r8y - 7.62))
    parts.append(_emit_label("C_bpc-power-hv", r8x, r8y - 7.62, 90))
    parts.append(_emit_wire(r8x, r8y + 5.08, r8x, r8y + 7.62))
    parts.append(_emit_label("Vbatr-hv", r8x, r8y + 7.62, 270))

    # D2: cathode / anode
    d2x, d2y = 130, 170
    parts.append(_emit_placed_symbol("D2", "Device:D", d2x, d2y, "D2"))
    parts.append(_emit_wire(d2x, d2y - 5.08, d2x, d2y - 7.62))
    parts.append(_emit_label("cathode", d2x, d2y - 7.62, 90))
    parts.append(_emit_wire(d2x, d2y + 5.08, d2x, d2y + 7.62))
    parts.append(_emit_label("anode", d2x, d2y + 7.62, 270))

    # F1: Vbatr-hv / 1 (net "1")
    f1x, f1y = 140, 170
    parts.append(_emit_placed_symbol("F1", "Device:Fuse", f1x, f1y, "F1"))
    parts.append(_emit_wire(f1x, f1y - 5.08, f1x, f1y - 7.62))
    parts.append(_emit_label("Vbatr-hv", f1x, f1y - 7.62, 90))
    parts.append(_emit_wire(f1x, f1y + 5.08, f1x, f1y + 7.62))
    parts.append(_emit_label("net_1", f1x, f1y + 7.62, 270))

    # CN1 load JST: Vbatr-hv / cathode
    cn1x, cn1y = 145, 150
    parts.append(_emit_placed_symbol("CN1", "Connector_Generic:Conn_01x02", cn1x, cn1y, "Load JST"))
    cn1_lx = cn1x - 5.08 - 2.54
    cn1_p1y = cn1y - 1.27  # pin 1
    cn1_p2y = cn1y + 1.27  # pin 2
    # Recalculate: n_left=2, half_h = GRID. pins at -GRID+GRID+i*GRID = i*GRID
    cn1_p1y = cn1y       # pin 1 at i=0
    cn1_p2y = cn1y + GRID  # pin 2 at i=1
    parts.append(_emit_wire(cn1_lx, cn1_p1y, cn1_lx - 5.08, cn1_p1y))
    parts.append(_emit_label("Vbatr-hv", cn1_lx - 5.08, cn1_p1y, 180))
    parts.append(_emit_wire(cn1_lx, cn1_p2y, cn1_lx - 5.08, cn1_p2y))
    parts.append(_emit_label("cathode", cn1_lx - 5.08, cn1_p2y, 180))

    # CN2 battery JST: net_1 / anode
    cn2x, cn2y = 145, 170
    parts.append(_emit_placed_symbol("CN2", "Connector_Generic:Conn_01x02", cn2x, cn2y, "Battery JST"))
    cn2_lx = cn2x - 5.08 - 2.54
    cn2_p1y = cn2y       # pin 1
    cn2_p2y = cn2y + GRID  # pin 2
    parts.append(_emit_wire(cn2_lx, cn2_p1y, cn2_lx - 5.08, cn2_p1y))
    parts.append(_emit_label("net_1", cn2_lx - 5.08, cn2_p1y, 180))
    parts.append(_emit_wire(cn2_lx, cn2_p2y, cn2_lx - 5.08, cn2_p2y))
    parts.append(_emit_label("anode", cn2_lx - 5.08, cn2_p2y, 180))

    # C1: Vbatr-hv / lv
    c1x, c1y = 110, 170
    parts.append(_emit_placed_symbol("C1", "Device:C", c1x, c1y, "C1"))
    parts.append(_emit_wire(c1x, c1y - 5.08, c1x, c1y - 7.62))
    parts.append(_emit_label("Vbatr-hv", c1x, c1y - 7.62, 90))
    parts.append(_emit_wire(c1x, c1y + 5.08, c1x, c1y + 7.62))
    parts.append(_emit_power_flag("#PWR011", "power:GND", c1x, c1y + 7.62))

    # ======================================================================
    # BLOCK 3: LDO Power  (x ~ 155..200)
    # ======================================================================
    u6x, u6y = 170, 55
    parts.append(_emit_placed_symbol("U6", "custom:HT7833", u6x, u6y, "HT7833"))
    u6_lx = u6x - 10.16 / 2 - 2.54
    u6_rx = u6x + 10.16 / 2 + 2.54
    # left pins: VIN(1) i=0 => y=u6y, GND(2) i=1 => y=u6y+GRID
    u6_vin_y = u6y
    u6_gnd_y = u6y + GRID
    parts.append(_emit_wire(u6_lx, u6_vin_y, u6_lx - 5.08, u6_vin_y))
    parts.append(_emit_label("Vbatr-hv", u6_lx - 5.08, u6_vin_y, 180))
    parts.append(_emit_wire(u6_lx, u6_gnd_y, u6_lx - 5.08, u6_gnd_y))
    parts.append(_emit_power_flag("#PWR012", "power:GND", u6_lx - 5.08, u6_gnd_y + 2.54))
    parts.append(_emit_wire(u6_lx - 5.08, u6_gnd_y, u6_lx - 5.08, u6_gnd_y + 2.54))
    # right pin: VOUT(5) at center y
    u6_vout_y = u6y
    parts.append(_emit_wire(u6_rx, u6_vout_y, u6_rx + 5.08, u6_vout_y))
    parts.append(_emit_label("hv", u6_rx + 5.08, u6_vout_y))

    # C15: Vbatr-hv / lv (input cap)
    c15x, c15y = 157, 70
    parts.append(_emit_placed_symbol("C15", "Device:C", c15x, c15y, "C15"))
    parts.append(_emit_wire(c15x, c15y - 5.08, c15x, c15y - 7.62))
    parts.append(_emit_label("Vbatr-hv", c15x, c15y - 7.62, 90))
    parts.append(_emit_wire(c15x, c15y + 5.08, c15x, c15y + 7.62))
    parts.append(_emit_power_flag("#PWR013", "power:GND", c15x, c15y + 7.62))

    # C16: hv / lv (output cap)
    c16x, c16y = 185, 70
    parts.append(_emit_placed_symbol("C16", "Device:C", c16x, c16y, "C16"))
    parts.append(_emit_wire(c16x, c16y - 5.08, c16x, c16y - 7.62))
    parts.append(_emit_label("hv", c16x, c16y - 7.62, 90))
    parts.append(_emit_wire(c16x, c16y + 5.08, c16x, c16y + 7.62))
    parts.append(_emit_power_flag("#PWR014", "power:GND", c16x, c16y + 7.62))

    # C2: hv / lv (general)
    c2x, c2y = 190, 70
    parts.append(_emit_placed_symbol("C2", "Device:C", c2x, c2y, "C2"))
    parts.append(_emit_wire(c2x, c2y - 5.08, c2x, c2y - 7.62))
    parts.append(_emit_label("hv", c2x, c2y - 7.62, 90))
    parts.append(_emit_wire(c2x, c2y + 5.08, c2x, c2y + 7.62))
    parts.append(_emit_power_flag("#PWR015", "power:GND", c2x, c2y + 7.62))

    # ======================================================================
    # BLOCK 4: ESP32-C6 MCU  (x ~ 200..270)
    # ======================================================================
    u5x, u5y = 230, 130
    parts.append(_emit_placed_symbol("U5", "custom:ESP32_C6_MINI", u5x, u5y, "ESP32-C6-MINI"))
    u5_lx = u5x - 17.78 / 2 - 2.54
    u5_rx = u5x + 17.78 / 2 + 2.54

    # left pins: 3V3(3) i=0, GND(1) i=1, EN(8) i=2, GPIO9(23) i=3
    # n_left=4, half_h=max(4,4)*GRID=4*GRID=10.16
    # pins at y = u5y - 4*GRID + GRID + i*GRID = u5y - 3*GRID + i*GRID
    u5_lpin_ys = [u5y - 3 * GRID + i * GRID for i in range(4)]
    # pin 3 (3V3)
    parts.append(_emit_wire(u5_lx, u5_lpin_ys[0], u5_lx - 5.08, u5_lpin_ys[0]))
    parts.append(_emit_label("hv", u5_lx - 5.08, u5_lpin_ys[0], 180))
    # pin 1 (GND)
    parts.append(_emit_wire(u5_lx, u5_lpin_ys[1], u5_lx - 5.08, u5_lpin_ys[1]))
    parts.append(_emit_power_flag("#PWR016", "power:GND", u5_lx - 5.08, u5_lpin_ys[1] + 2.54))
    parts.append(_emit_wire(u5_lx - 5.08, u5_lpin_ys[1], u5_lx - 5.08, u5_lpin_ys[1] + 2.54))
    # pin 8 (EN)
    parts.append(_emit_wire(u5_lx, u5_lpin_ys[2], u5_lx - 5.08, u5_lpin_ys[2]))
    parts.append(_emit_label("c_en-power-hv", u5_lx - 5.08, u5_lpin_ys[2], 180))
    # pin 23 (GPIO9)
    parts.append(_emit_wire(u5_lx, u5_lpin_ys[3], u5_lx - 5.08, u5_lpin_ys[3]))
    parts.append(_emit_label("A_GPIO9", u5_lx - 5.08, u5_lpin_ys[3], 180))

    # right pins: SDA(15) i=0, SCL(16) i=1, USB_D+(17) i=2, USB_D-(18) i=3
    u5_rpin_ys = [u5y - 3 * GRID + i * GRID for i in range(4)]
    # SDA
    parts.append(_emit_wire(u5_rx, u5_rpin_ys[0], u5_rx + 5.08, u5_rpin_ys[0]))
    parts.append(_emit_label("SDA", u5_rx + 5.08, u5_rpin_ys[0]))
    # SCL
    parts.append(_emit_wire(u5_rx, u5_rpin_ys[1], u5_rx + 5.08, u5_rpin_ys[1]))
    parts.append(_emit_label("SCL", u5_rx + 5.08, u5_rpin_ys[1]))
    # USB_D+
    parts.append(_emit_wire(u5_rx, u5_rpin_ys[2], u5_rx + 5.08, u5_rpin_ys[2]))
    parts.append(_emit_label("USB_Dp", u5_rx + 5.08, u5_rpin_ys[2]))
    # USB_D-
    parts.append(_emit_wire(u5_rx, u5_rpin_ys[3], u5_rx + 5.08, u5_rpin_ys[3]))
    parts.append(_emit_label("USB_Dm", u5_rx + 5.08, u5_rpin_ys[3]))

    # R17: hv / c_en-power-hv (EN pull-up)
    r17x, r17y = 205, 105
    parts.append(_emit_placed_symbol("R17", "Device:R", r17x, r17y, "R17"))
    parts.append(_emit_wire(r17x, r17y - 5.08, r17x, r17y - 7.62))
    parts.append(_emit_label("hv", r17x, r17y - 7.62, 90))
    parts.append(_emit_wire(r17x, r17y + 5.08, r17x, r17y + 7.62))
    parts.append(_emit_label("c_en-power-hv", r17x, r17y + 7.62, 270))

    # C14: c_en-power-hv / lv
    c14x, c14y = 210, 105
    parts.append(_emit_placed_symbol("C14", "Device:C", c14x, c14y, "C14"))
    parts.append(_emit_wire(c14x, c14y - 5.08, c14x, c14y - 7.62))
    parts.append(_emit_label("c_en-power-hv", c14x, c14y - 7.62, 90))
    parts.append(_emit_wire(c14x, c14y + 5.08, c14x, c14y + 7.62))
    parts.append(_emit_power_flag("#PWR017", "power:GND", c14x, c14y + 7.62))

    # R16: hv / A_GPIO9 (BOOT pull-up)
    r16x, r16y = 205, 145
    parts.append(_emit_placed_symbol("R16", "Device:R", r16x, r16y, "R16"))
    parts.append(_emit_wire(r16x, r16y - 5.08, r16x, r16y - 7.62))
    parts.append(_emit_label("hv", r16x, r16y - 7.62, 90))
    parts.append(_emit_wire(r16x, r16y + 5.08, r16x, r16y + 7.62))
    parts.append(_emit_label("A_GPIO9", r16x, r16y + 7.62, 270))

    # C12, C13 decoupling near ESP32
    c12x, c12y = 215, 155
    parts.append(_emit_placed_symbol("C12", "Device:C", c12x, c12y, "C12"))
    parts.append(_emit_wire(c12x, c12y - 5.08, c12x, c12y - 7.62))
    parts.append(_emit_label("hv", c12x, c12y - 7.62, 90))
    parts.append(_emit_wire(c12x, c12y + 5.08, c12x, c12y + 7.62))
    parts.append(_emit_power_flag("#PWR018", "power:GND", c12x, c12y + 7.62))

    c13x, c13y = 220, 155
    parts.append(_emit_placed_symbol("C13", "Device:C", c13x, c13y, "C13"))
    parts.append(_emit_wire(c13x, c13y - 5.08, c13x, c13y - 7.62))
    parts.append(_emit_label("hv", c13x, c13y - 7.62, 90))
    parts.append(_emit_wire(c13x, c13y + 5.08, c13x, c13y + 7.62))
    parts.append(_emit_power_flag("#PWR019", "power:GND", c13x, c13y + 7.62))

    # SW1 boot button: A_GPIO9 / lv
    sw1x, sw1y = 200, 160
    parts.append(_emit_placed_symbol("SW1", "Switch:SW_Push", sw1x, sw1y, "BOOT"))
    parts.append(_emit_wire(sw1x, sw1y - 5.08, sw1x, sw1y - 7.62))
    parts.append(_emit_label("A_GPIO9", sw1x, sw1y - 7.62, 90))
    parts.append(_emit_wire(sw1x, sw1y + 5.08, sw1x, sw1y + 7.62))
    parts.append(_emit_power_flag("#PWR020", "power:GND", sw1x, sw1y + 7.62))

    # SW2 reset button: c_en-power-hv / lv
    sw2x, sw2y = 195, 115
    parts.append(_emit_placed_symbol("SW2", "Switch:SW_Push", sw2x, sw2y, "RESET"))
    parts.append(_emit_wire(sw2x, sw2y - 5.08, sw2x, sw2y - 7.62))
    parts.append(_emit_label("c_en-power-hv", sw2x, sw2y - 7.62, 90))
    parts.append(_emit_wire(sw2x, sw2y + 5.08, sw2x, sw2y + 7.62))
    parts.append(_emit_power_flag("#PWR021", "power:GND", sw2x, sw2y + 7.62))

    # ======================================================================
    # BLOCK 5: USB-C  (x ~ 200..250, y ~ 185..230)
    # ======================================================================
    usbcx, usbcy = 220, 205
    parts.append(_emit_placed_symbol("USBC1", "Connector:USB_C", usbcx, usbcy, "USB-C"))
    usbc_lx = usbcx - 7.62 / 2 - 2.54
    # 7 left pins, half_h = max(7,0)*GRID = 7*GRID
    # pin y offsets: -6*GRID + GRID + i*GRID = (-6+1+i)*GRID = (-5+i)*GRID from center
    # VBUS(A4B9), GND(A1B12), CC1(A5), CC2(B5), D-(A6), D+(A7), SHIELD(1)
    usbc_pin_ys = [usbcy + (-5 + i) * GRID for i in range(7)]

    # VBUS -> label
    parts.append(_emit_wire(usbc_lx, usbc_pin_ys[0], usbc_lx - 7.62, usbc_pin_ys[0]))
    parts.append(_emit_label("power_usb-hv", usbc_lx - 7.62, usbc_pin_ys[0], 180))
    # GND
    parts.append(_emit_wire(usbc_lx, usbc_pin_ys[1], usbc_lx - 7.62, usbc_pin_ys[1]))
    parts.append(_emit_power_flag("#PWR022", "power:GND", usbc_lx - 7.62, usbc_pin_ys[1] + 2.54))
    parts.append(_emit_wire(usbc_lx - 7.62, usbc_pin_ys[1], usbc_lx - 7.62, usbc_pin_ys[1] + 2.54))
    # CC1
    parts.append(_emit_wire(usbc_lx, usbc_pin_ys[2], usbc_lx - 7.62, usbc_pin_ys[2]))
    parts.append(_emit_label("A5_CC1", usbc_lx - 7.62, usbc_pin_ys[2], 180))
    # CC2
    parts.append(_emit_wire(usbc_lx, usbc_pin_ys[3], usbc_lx - 7.62, usbc_pin_ys[3]))
    parts.append(_emit_label("B5_CC2", usbc_lx - 7.62, usbc_pin_ys[3], 180))
    # D-
    parts.append(_emit_wire(usbc_lx, usbc_pin_ys[4], usbc_lx - 7.62, usbc_pin_ys[4]))
    parts.append(_emit_label("USB_Dm", usbc_lx - 7.62, usbc_pin_ys[4], 180))
    # D+
    parts.append(_emit_wire(usbc_lx, usbc_pin_ys[5], usbc_lx - 7.62, usbc_pin_ys[5]))
    parts.append(_emit_label("USB_Dp", usbc_lx - 7.62, usbc_pin_ys[5], 180))
    # SHIELD -> GND
    parts.append(_emit_wire(usbc_lx, usbc_pin_ys[6], usbc_lx - 7.62, usbc_pin_ys[6]))
    parts.append(_emit_power_flag("#PWR023", "power:GND", usbc_lx - 7.62, usbc_pin_ys[6] + 2.54))
    parts.append(_emit_wire(usbc_lx - 7.62, usbc_pin_ys[6], usbc_lx - 7.62, usbc_pin_ys[6] + 2.54))

    # R18: A5_CC1 / lv
    r18x, r18y = 200, 225
    parts.append(_emit_placed_symbol("R18", "Device:R", r18x, r18y, "R18 5.1k"))
    parts.append(_emit_wire(r18x, r18y - 5.08, r18x, r18y - 7.62))
    parts.append(_emit_label("A5_CC1", r18x, r18y - 7.62, 90))
    parts.append(_emit_wire(r18x, r18y + 5.08, r18x, r18y + 7.62))
    parts.append(_emit_power_flag("#PWR024", "power:GND", r18x, r18y + 7.62))

    # R19: B5_CC2 / lv
    r19x, r19y = 205, 225
    parts.append(_emit_placed_symbol("R19", "Device:R", r19x, r19y, "R19 5.1k"))
    parts.append(_emit_wire(r19x, r19y - 5.08, r19x, r19y - 7.62))
    parts.append(_emit_label("B5_CC2", r19x, r19y - 7.62, 90))
    parts.append(_emit_wire(r19x, r19y + 5.08, r19x, r19y + 7.62))
    parts.append(_emit_power_flag("#PWR025", "power:GND", r19x, r19y + 7.62))

    # ======================================================================
    # BLOCK 6: Sensors + I2C  (x ~ 270..380)
    # ======================================================================
    # I2C pull-up resistors
    # R12: SCL / hv
    r12x, r12y = 275, 50
    parts.append(_emit_placed_symbol("R12", "Device:R", r12x, r12y, "R12"))
    parts.append(_emit_wire(r12x, r12y - 5.08, r12x, r12y - 7.62))
    parts.append(_emit_label("hv", r12x, r12y - 7.62, 90))
    parts.append(_emit_wire(r12x, r12y + 5.08, r12x, r12y + 7.62))
    parts.append(_emit_label("SCL", r12x, r12y + 7.62, 270))

    # R13: SDA / hv
    r13x, r13y = 280, 50
    parts.append(_emit_placed_symbol("R13", "Device:R", r13x, r13y, "R13"))
    parts.append(_emit_wire(r13x, r13y - 5.08, r13x, r13y - 7.62))
    parts.append(_emit_label("hv", r13x, r13y - 7.62, 90))
    parts.append(_emit_wire(r13x, r13y + 5.08, r13x, r13y + 7.62))
    parts.append(_emit_label("SDA", r13x, r13y + 7.62, 270))

    # U4 SHT40 temp/humidity
    u4x, u4y = 300, 85
    parts.append(_emit_placed_symbol("U4", "custom:SHT40", u4x, u4y, "SHT40"))
    u4_lx = u4x - 10.16 / 2 - 2.54
    u4_rx = u4x + 10.16 / 2 + 2.54
    # left pins: VDD(3) i=0, GND(4) i=1, EPAD(5) i=2
    # n_left=3, half_h = 3*GRID
    u4_lpin_ys = [u4y - 2 * GRID + i * GRID for i in range(3)]
    parts.append(_emit_wire(u4_lx, u4_lpin_ys[0], u4_lx - 5.08, u4_lpin_ys[0]))
    parts.append(_emit_label("hv", u4_lx - 5.08, u4_lpin_ys[0], 180))
    parts.append(_emit_wire(u4_lx, u4_lpin_ys[1], u4_lx - 5.08, u4_lpin_ys[1]))
    parts.append(_emit_power_flag("#PWR026", "power:GND", u4_lx - 5.08, u4_lpin_ys[1] + 2.54))
    parts.append(_emit_wire(u4_lx - 5.08, u4_lpin_ys[1], u4_lx - 5.08, u4_lpin_ys[1] + 2.54))
    parts.append(_emit_wire(u4_lx, u4_lpin_ys[2], u4_lx - 5.08, u4_lpin_ys[2]))
    parts.append(_emit_power_flag("#PWR027", "power:GND", u4_lx - 5.08, u4_lpin_ys[2] + 2.54))
    parts.append(_emit_wire(u4_lx - 5.08, u4_lpin_ys[2], u4_lx - 5.08, u4_lpin_ys[2] + 2.54))
    # right pins: SDA(1) i=0, SCL(2) i=1
    u4_rpin_ys = [u4y - 1 * GRID + i * GRID for i in range(2)]
    parts.append(_emit_wire(u4_rx, u4_rpin_ys[0], u4_rx + 5.08, u4_rpin_ys[0]))
    parts.append(_emit_label("SDA", u4_rx + 5.08, u4_rpin_ys[0]))
    parts.append(_emit_wire(u4_rx, u4_rpin_ys[1], u4_rx + 5.08, u4_rpin_ys[1]))
    parts.append(_emit_label("SCL", u4_rx + 5.08, u4_rpin_ys[1]))

    # C10: hv / lv (SHT40 decoupling)
    c10x, c10y = 285, 95
    parts.append(_emit_placed_symbol("C10", "Device:C", c10x, c10y, "C10"))
    parts.append(_emit_wire(c10x, c10y - 5.08, c10x, c10y - 7.62))
    parts.append(_emit_label("hv", c10x, c10y - 7.62, 90))
    parts.append(_emit_wire(c10x, c10y + 5.08, c10x, c10y + 7.62))
    parts.append(_emit_power_flag("#PWR028", "power:GND", c10x, c10y + 7.62))

    # LED1 VEML7700 light sensor
    led1x, led1y = 300, 120
    parts.append(_emit_placed_symbol("LED1", "custom:VEML7700", led1x, led1y, "VEML7700"))
    led1_lx = led1x - 10.16 / 2 - 2.54
    led1_rx = led1x + 10.16 / 2 + 2.54
    # left: VDD(2) i=0, GND(3) i=1
    led1_lpin_ys = [led1y - GRID / 2, led1y + GRID / 2]
    # n_left=2, half_h=GRID. pins at y=center+i*GRID = center, center+GRID
    led1_lpin_ys = [led1y, led1y + GRID]
    parts.append(_emit_wire(led1_lx, led1_lpin_ys[0], led1_lx - 5.08, led1_lpin_ys[0]))
    parts.append(_emit_label("hv", led1_lx - 5.08, led1_lpin_ys[0], 180))
    parts.append(_emit_wire(led1_lx, led1_lpin_ys[1], led1_lx - 5.08, led1_lpin_ys[1]))
    parts.append(_emit_power_flag("#PWR029", "power:GND", led1_lx - 5.08, led1_lpin_ys[1] + 2.54))
    parts.append(_emit_wire(led1_lx - 5.08, led1_lpin_ys[1], led1_lx - 5.08, led1_lpin_ys[1] + 2.54))
    # right: SCL(1) i=0, SDA(4) i=1
    led1_rpin_ys = [led1y, led1y + GRID]
    parts.append(_emit_wire(led1_rx, led1_rpin_ys[0], led1_rx + 5.08, led1_rpin_ys[0]))
    parts.append(_emit_label("SCL", led1_rx + 5.08, led1_rpin_ys[0]))
    parts.append(_emit_wire(led1_rx, led1_rpin_ys[1], led1_rx + 5.08, led1_rpin_ys[1]))
    parts.append(_emit_label("SDA", led1_rx + 5.08, led1_rpin_ys[1]))

    # C11: hv / lv (VEML7700 decoupling)
    c11x, c11y = 285, 130
    parts.append(_emit_placed_symbol("C11", "Device:C", c11x, c11y, "C11"))
    parts.append(_emit_wire(c11x, c11y - 5.08, c11x, c11y - 7.62))
    parts.append(_emit_label("hv", c11x, c11y - 7.62, 90))
    parts.append(_emit_wire(c11x, c11y + 5.08, c11x, c11y + 7.62))
    parts.append(_emit_power_flag("#PWR030", "power:GND", c11x, c11y + 7.62))

    # U1 MAX17048 fuel gauge
    u1x, u1y = 340, 85
    parts.append(_emit_placed_symbol("U1", "custom:MAX17048", u1x, u1y, "MAX17048"))
    u1_lx = u1x - 12.7 / 2 - 2.54
    u1_rx = u1x + 12.7 / 2 + 2.54
    # left: VDD(3) i=0, CELL(2) i=1, GND1(1) i=2, GND2(4) i=3, EPAD(9) i=4
    # n_left=5, half_h=5*GRID
    u1_lpin_ys = [u1y - 4 * GRID + i * GRID for i in range(5)]
    parts.append(_emit_wire(u1_lx, u1_lpin_ys[0], u1_lx - 5.08, u1_lpin_ys[0]))
    parts.append(_emit_label("hv", u1_lx - 5.08, u1_lpin_ys[0], 180))
    parts.append(_emit_wire(u1_lx, u1_lpin_ys[1], u1_lx - 5.08, u1_lpin_ys[1]))
    parts.append(_emit_label("Vbatr-hv", u1_lx - 5.08, u1_lpin_ys[1], 180))
    # GND pins
    for idx in [2, 3, 4]:
        parts.append(_emit_wire(u1_lx, u1_lpin_ys[idx], u1_lx - 5.08, u1_lpin_ys[idx]))
    parts.append(_emit_wire(u1_lx - 5.08, u1_lpin_ys[2], u1_lx - 5.08, u1_lpin_ys[4]))
    parts.append(_emit_power_flag(f"#PWR031", "power:GND", u1_lx - 5.08, u1_lpin_ys[4] + 2.54))
    parts.append(_emit_wire(u1_lx - 5.08, u1_lpin_ys[4], u1_lx - 5.08, u1_lpin_ys[4] + 2.54))

    # right: ~ALRT(5) i=0, QSTRT(6) i=1, SCL(7) i=2, SDA(8) i=3
    u1_rpin_ys = [u1y - 3 * GRID + i * GRID for i in range(4)]
    parts.append(_emit_wire(u1_rx, u1_rpin_ys[0], u1_rx + 5.08, u1_rpin_ys[0]))
    parts.append(_emit_label("nALRT", u1_rx + 5.08, u1_rpin_ys[0]))
    parts.append(_emit_wire(u1_rx, u1_rpin_ys[1], u1_rx + 5.08, u1_rpin_ys[1]))
    parts.append(_emit_label("QSTRT", u1_rx + 5.08, u1_rpin_ys[1]))
    parts.append(_emit_wire(u1_rx, u1_rpin_ys[2], u1_rx + 5.08, u1_rpin_ys[2]))
    parts.append(_emit_label("SCL", u1_rx + 5.08, u1_rpin_ys[2]))
    parts.append(_emit_wire(u1_rx, u1_rpin_ys[3], u1_rx + 5.08, u1_rpin_ys[3]))
    parts.append(_emit_label("SDA", u1_rx + 5.08, u1_rpin_ys[3]))

    # R1: nALRT / hv (pull-up)
    r1x, r1y = 365, 65
    parts.append(_emit_placed_symbol("R1", "Device:R", r1x, r1y, "R1"))
    parts.append(_emit_wire(r1x, r1y - 5.08, r1x, r1y - 7.62))
    parts.append(_emit_label("hv", r1x, r1y - 7.62, 90))
    parts.append(_emit_wire(r1x, r1y + 5.08, r1x, r1y + 7.62))
    parts.append(_emit_label("nALRT", r1x, r1y + 7.62, 270))

    # R4: QSTRT / lv
    r4x, r4y = 370, 80
    parts.append(_emit_placed_symbol("R4", "Device:R", r4x, r4y, "R4"))
    parts.append(_emit_wire(r4x, r4y - 5.08, r4x, r4y - 7.62))
    parts.append(_emit_label("QSTRT", r4x, r4y - 7.62, 90))
    parts.append(_emit_wire(r4x, r4y + 5.08, r4x, r4y + 7.62))
    parts.append(_emit_power_flag("#PWR032", "power:GND", r4x, r4y + 7.62))

    # R2: hv / SCL (additional)
    r2x, r2y = 330, 50
    parts.append(_emit_placed_symbol("R2", "Device:R", r2x, r2y, "R2"))
    parts.append(_emit_wire(r2x, r2y - 5.08, r2x, r2y - 7.62))
    parts.append(_emit_label("hv", r2x, r2y - 7.62, 90))
    parts.append(_emit_wire(r2x, r2y + 5.08, r2x, r2y + 7.62))
    parts.append(_emit_label("SCL", r2x, r2y + 7.62, 270))

    # R3: hv / SDA
    r3x, r3y = 335, 50
    parts.append(_emit_placed_symbol("R3", "Device:R", r3x, r3y, "R3"))
    parts.append(_emit_wire(r3x, r3y - 5.08, r3x, r3y - 7.62))
    parts.append(_emit_label("hv", r3x, r3y - 7.62, 90))
    parts.append(_emit_wire(r3x, r3y + 5.08, r3x, r3y + 7.62))
    parts.append(_emit_label("SDA", r3x, r3y + 7.62, 270))

    # R14: hv / SCL
    r14x, r14y = 360, 120
    parts.append(_emit_placed_symbol("R14", "Device:R", r14x, r14y, "R14"))
    parts.append(_emit_wire(r14x, r14y - 5.08, r14x, r14y - 7.62))
    parts.append(_emit_label("hv", r14x, r14y - 7.62, 90))
    parts.append(_emit_wire(r14x, r14y + 5.08, r14x, r14y + 7.62))
    parts.append(_emit_label("SCL", r14x, r14y + 7.62, 270))

    # R15: hv / SDA
    r15x, r15y = 365, 120
    parts.append(_emit_placed_symbol("R15", "Device:R", r15x, r15y, "R15"))
    parts.append(_emit_wire(r15x, r15y - 5.08, r15x, r15y - 7.62))
    parts.append(_emit_label("hv", r15x, r15y - 7.62, 90))
    parts.append(_emit_wire(r15x, r15y + 5.08, r15x, r15y + 7.62))
    parts.append(_emit_label("SDA", r15x, r15y + 7.62, 270))

    # CN4 Qwiic connector
    cn4x, cn4y = 300, 155
    parts.append(_emit_placed_symbol("CN4", "Connector_Generic:Conn_01x04", cn4x, cn4y, "Qwiic1"))
    cn4_lx = cn4x - 5.08 / 2 - 2.54
    # n_left=4, half_h=4*GRID. pins at y = center - 3*GRID + i*GRID
    cn4_pin_ys = [cn4y - 3 * GRID + i * GRID for i in range(4)]
    parts.append(_emit_wire(cn4_lx, cn4_pin_ys[0], cn4_lx - 5.08, cn4_pin_ys[0]))
    parts.append(_emit_power_flag("#PWR033", "power:GND", cn4_lx - 5.08, cn4_pin_ys[0] + 2.54))
    parts.append(_emit_wire(cn4_lx - 5.08, cn4_pin_ys[0], cn4_lx - 5.08, cn4_pin_ys[0] + 2.54))
    parts.append(_emit_wire(cn4_lx, cn4_pin_ys[1], cn4_lx - 5.08, cn4_pin_ys[1]))
    parts.append(_emit_label("hv", cn4_lx - 5.08, cn4_pin_ys[1], 180))
    parts.append(_emit_wire(cn4_lx, cn4_pin_ys[2], cn4_lx - 5.08, cn4_pin_ys[2]))
    parts.append(_emit_label("SDA", cn4_lx - 5.08, cn4_pin_ys[2], 180))
    parts.append(_emit_wire(cn4_lx, cn4_pin_ys[3], cn4_lx - 5.08, cn4_pin_ys[3]))
    parts.append(_emit_label("SCL", cn4_lx - 5.08, cn4_pin_ys[3], 180))

    # CN5 Qwiic connector
    cn5x, cn5y = 340, 155
    parts.append(_emit_placed_symbol("CN5", "Connector_Generic:Conn_01x04", cn5x, cn5y, "Qwiic2"))
    cn5_lx = cn5x - 5.08 / 2 - 2.54
    cn5_pin_ys = [cn5y - 3 * GRID + i * GRID for i in range(4)]
    parts.append(_emit_wire(cn5_lx, cn5_pin_ys[0], cn5_lx - 5.08, cn5_pin_ys[0]))
    parts.append(_emit_power_flag("#PWR034", "power:GND", cn5_lx - 5.08, cn5_pin_ys[0] + 2.54))
    parts.append(_emit_wire(cn5_lx - 5.08, cn5_pin_ys[0], cn5_lx - 5.08, cn5_pin_ys[0] + 2.54))
    parts.append(_emit_wire(cn5_lx, cn5_pin_ys[1], cn5_lx - 5.08, cn5_pin_ys[1]))
    parts.append(_emit_label("hv", cn5_lx - 5.08, cn5_pin_ys[1], 180))
    parts.append(_emit_wire(cn5_lx, cn5_pin_ys[2], cn5_lx - 5.08, cn5_pin_ys[2]))
    parts.append(_emit_label("SDA", cn5_lx - 5.08, cn5_pin_ys[2], 180))
    parts.append(_emit_wire(cn5_lx, cn5_pin_ys[3], cn5_lx - 5.08, cn5_pin_ys[3]))
    parts.append(_emit_label("SCL", cn5_lx - 5.08, cn5_pin_ys[3], 180))

    # ======================================================================
    # Title block / text annotations
    # ======================================================================
    # Add some text annotations for block titles
    block_titles = [
        (55, 30, "SOLAR INPUT + MPPT"),
        (125, 135, "BATTERY PROTECTION"),
        (170, 40, "LDO 3.3V"),
        (230, 100, "ESP32-C6 MCU"),
        (220, 180, "USB-C"),
        (310, 35, "SENSORS + I2C BUS"),
    ]
    for tx, ty, text in block_titles:
        parts.append(
            f'  (text {sexp_str(text)} (at {tx} {ty} 0)'
            f' (effects (font (size 2.54 2.54) bold))\n'
            f'    (uuid {uid()}))'
        )

    # ======================================================================
    # Sheet instances (required)
    # ======================================================================
    parts.append(f'  (sheet_instances (path "/" (page "1")))')

    parts.append(f')')

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    content = build_schematic()
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    size = os.path.getsize(OUTPUT_PATH)
    print(f"Schematic written to: {OUTPUT_PATH}")
    print(f"File size: {size:,} bytes ({size / 1024:.1f} KB)")


if __name__ == "__main__":
    main()
