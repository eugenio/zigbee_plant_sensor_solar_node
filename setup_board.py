"""
Set up 4-layer board with:
- Board outline 60x48mm
- ESP32-C6 placed with antenna overhanging short edge (top)
- USB-C on long edge (left)
- Connectors placed and locked with silkscreen labels
- Mounting holes in 4 corners
- Placement regions (Rule Areas) for Quilter
- All fixed components locked
"""
import pcbnew

PCB_PATH = r"C:\Users\eugen\elettronica\zigbee_xiao_esp32c6\zigbee_plant_sensor_solar_node\layouts\default\default.kicad_pcb"

board = pcbnew.LoadBoard(PCB_PATH)

# ============================================================
# Board dimensions
# ============================================================
BOARD_W = 60.0
BOARD_H = 48.0
OX = 100.0  # left edge
OY = 78.0   # top edge
# Derived edges
RIGHT = OX + BOARD_W   # 160
BOTTOM = OY + BOARD_H  # 126

# ============================================================
# Clean up: edge cuts, tracks, zones, silkscreen texts
# ============================================================
to_remove = []
for dwg in board.GetDrawings():
    layer = dwg.GetLayer()
    if layer == pcbnew.Edge_Cuts:
        to_remove.append(dwg)
    elif layer in (pcbnew.F_SilkS, pcbnew.B_SilkS) and dwg.GetClass() == "PCB_TEXT":
        to_remove.append(dwg)
for dwg in to_remove:
    board.RemoveNative(dwg)

for t in list(board.GetTracks()):
    board.RemoveNative(t)
for z in list(board.Zones()):
    board.RemoveNative(z)

# ============================================================
# 4-layer stackup
# ============================================================
board.SetCopperLayerCount(4)

# ============================================================
# Board outline
# ============================================================
corners = [
    (OX, OY), (RIGHT, OY),
    (RIGHT, BOTTOM), (OX, BOTTOM),
]
for i in range(4):
    seg = pcbnew.PCB_SHAPE(board)
    seg.SetShape(pcbnew.SHAPE_T_SEGMENT)
    seg.SetLayer(pcbnew.Edge_Cuts)
    seg.SetWidth(pcbnew.FromMM(0.15))
    x1, y1 = corners[i]
    x2, y2 = corners[(i + 1) % 4]
    seg.SetStart(pcbnew.VECTOR2I(pcbnew.FromMM(x1), pcbnew.FromMM(y1)))
    seg.SetEnd(pcbnew.VECTOR2I(pcbnew.FromMM(x2), pcbnew.FromMM(y2)))
    board.Add(seg)

# ============================================================
# Helper functions
# ============================================================
def find_fp(ref):
    for fp in board.GetFootprints():
        if fp.GetReference() == ref:
            return fp
    print(f"WARNING: {ref} not found!")
    return None

def place(ref, x_mm, y_mm, angle_deg=0, layer="F.Cu"):
    fp = find_fp(ref)
    if fp is None:
        return
    fp.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))
    fp.SetOrientationDegrees(angle_deg)
    if layer == "B.Cu" and fp.GetLayer() != pcbnew.B_Cu:
        fp.Flip(fp.GetPosition(), False)
    elif layer == "F.Cu" and fp.GetLayer() != pcbnew.F_Cu:
        fp.Flip(fp.GetPosition(), False)

def lock(ref):
    fp = find_fp(ref)
    if fp:
        fp.SetLocked(True)

def add_silkscreen_label(text, x_mm, y_mm, size_mm=0.8, thickness_mm=0.15, layer=pcbnew.F_SilkS):
    """Add a text label on the silkscreen layer."""
    t = pcbnew.PCB_TEXT(board)
    t.SetText(text)
    t.SetPosition(pcbnew.VECTOR2I(pcbnew.FromMM(x_mm), pcbnew.FromMM(y_mm)))
    t.SetLayer(layer)
    t.SetTextSize(pcbnew.VECTOR2I(pcbnew.FromMM(size_mm), pcbnew.FromMM(size_mm)))
    t.SetTextThickness(pcbnew.FromMM(thickness_mm))
    t.SetHorizJustify(pcbnew.GR_TEXT_H_ALIGN_CENTER)
    board.Add(t)

def add_rule_area(name, x1, y1, x2, y2, layer=pcbnew.F_Cu):
    """Add a Rule Area (keepout with nothing kept out = placement region for Quilter)."""
    zone = pcbnew.ZONE(board)
    zone.SetIsRuleArea(True)
    zone.SetDoNotAllowTracks(False)
    zone.SetDoNotAllowVias(False)
    zone.SetDoNotAllowPads(False)
    zone.SetDoNotAllowCopperPour(False)
    zone.SetDoNotAllowFootprints(False)
    zone.SetLayer(layer)
    zone.SetZoneName(name)
    zone.SetLocked(True)

    outline = zone.Outline()
    outline.NewOutline()
    outline.Append(pcbnew.FromMM(x1), pcbnew.FromMM(y1))
    outline.Append(pcbnew.FromMM(x2), pcbnew.FromMM(y1))
    outline.Append(pcbnew.FromMM(x2), pcbnew.FromMM(y2))
    outline.Append(pcbnew.FromMM(x1), pcbnew.FromMM(y2))

    board.Add(zone)
    print(f"  Rule area '{name}': ({x1},{y1})-({x2},{y2})")

# ============================================================
# PLACEMENT
# ============================================================

# ---- Mounting holes: 4 corners, 3.5mm inset from edges ----
MH_INSET = 3.5
place("H1", OX + MH_INSET,        OY + MH_INSET,        0)  # top-left
place("H2", RIGHT - MH_INSET,     OY + MH_INSET,        0)  # top-right
place("H3", OX + MH_INSET,        BOTTOM - MH_INSET,    0)  # bottom-left
place("H4", RIGHT - MH_INSET,     BOTTOM - MH_INSET,    0)  # bottom-right
for h in ["H1", "H2", "H3", "H4"]:
    lock(h)

# ---- ESP32-C6: antenna overhangs TOP short edge ----
# Module is 16.6x13.2mm. Rotated 0deg: length along Y, width along X.
# Antenna is at the top of the module (~3-4mm).
# Place so antenna region sticks out past OY (top edge).
# Module center at Y = OY + 7 means top of module at OY - 1.3 (overhangs ~1.3mm)
ESP_X = OX + 30  # centered horizontally
ESP_Y = OY + 7   # antenna overhangs top edge
place("U5", ESP_X, ESP_Y, 0)
lock("U5")

# ---- USB-C: left long edge, flipped horizontally (facing left) ----
# Connector ~8.9x10.6mm. Rotated -90deg (270) to face left edge.
USB_X = OX + 5    # near left edge
USB_Y = OY + 14   # below ESP32, accessible
place("USBC1", USB_X, USB_Y, 270)
lock("USBC1")

# ---- Boot & Reset buttons: left edge, spaced apart from USB-C ----
place("SW1", OX + 5,  OY + 26, 0)   # BOOT - well below USB
place("SW2", OX + 5,  OY + 38, 0)   # RESET - further down, 12mm gap
lock("SW1")
lock("SW2")

# ---- Power connectors: bottom edge (solar + battery) ----
# CN3 = Solar panel input, CN1 = Battery
place("CN3", OX + 15, BOTTOM - 4, 180)  # SOLAR - bottom left
place("CN1", OX + 30, BOTTOM - 4, 180)  # BATTERY - bottom center
lock("CN3")
lock("CN1")

# ---- Qwiic connectors: right edge ----
# EC above SOIL, closer to top-right mounting hole
place("CN5", RIGHT - 4, OY + 10, 270)  # QWIIC EC - right side, near top
place("CN4", RIGHT - 4, OY + 20, 270)  # QWIIC SOIL - right side, below EC
lock("CN5")
lock("CN4")

# ---- Lock all components already inside the board ----
print("\nLocking components inside board area...")
for fp in board.GetFootprints():
    pos = fp.GetPosition()
    x, y = pcbnew.ToMM(pos.x), pcbnew.ToMM(pos.y)
    # Allow small margin for antenna overhang
    if OX - 5 <= x <= RIGHT + 5 and OY - 5 <= y <= BOTTOM + 5:
        if not fp.IsLocked():
            fp.SetLocked(True)
            print(f"  Locked {fp.GetReference()} at ({x:.1f},{y:.1f})")

# ============================================================
# Silkscreen labels for connectors
# ============================================================
# All labels placed within board frame (OX..RIGHT, OY..BOTTOM)
add_silkscreen_label("USB",      OX + 10,   USB_Y,       0.7)  # right of USB connector
add_silkscreen_label("BOOT",     OX + 10,   OY + 26,     0.6)  # right of boot button
add_silkscreen_label("RESET",    OX + 10,   OY + 38,     0.6)  # right of reset button
add_silkscreen_label("SOLAR",    OX + 15,   BOTTOM - 8,  0.7)  # above solar connector
add_silkscreen_label("BATT",     OX + 30,   BOTTOM - 8,  0.7)  # above battery connector
add_silkscreen_label("EC",       RIGHT - 9, OY + 10,     0.6)  # left of EC connector
add_silkscreen_label("SOIL",     RIGHT - 9, OY + 20,     0.6)  # left of soil connector

# ============================================================
# Placement regions (Rule Areas for Quilter)
# ============================================================
print("\nAdding placement regions...")

# 1. MCU zone: ESP32 + decoupling + EN/boot circuit
#    Upper-left quadrant, around ESP32
add_rule_area("MCU", OX + 10, OY + 1, OX + 45, OY + 20)

# 2. LDO zone: HT7833 + caps
#    Upper-right area
add_rule_area("LDO", OX + 45, OY + 1, RIGHT - 5, OY + 20)

# 3. MPPT/Power zone: SPV1040T + inductor + battery protection + caps
#    Lower-left quadrant
add_rule_area("MPPT_POWER", OX + 10, OY + 20, OX + 40, BOTTOM - 8)

# 4. Sensor zone: SHT40 + VEML7700 + MAX17048 + I2C pull-ups
#    Lower-right area
add_rule_area("SENSORS", OX + 40, OY + 20, RIGHT - 8, BOTTOM - 8)

# ============================================================
# Save
# ============================================================
board.Save(PCB_PATH)
print(f"\nBoard setup complete:")
print(f"  4-layer, {BOARD_W}x{BOARD_H}mm")
print(f"  ESP32-C6 antenna overhangs top edge")
print(f"  USB-C on left edge")
print(f"  Solar/Batt/Load on bottom edge")
print(f"  Qwiic connectors on right edge")
print(f"  Mounting holes in 4 corners")
print(f"  4 placement regions defined for Quilter")
