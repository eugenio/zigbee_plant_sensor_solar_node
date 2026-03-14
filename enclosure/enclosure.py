"""
Zigbee Plant Sensor Solar Node — Enclosure (build123d)
IP65 outdoor enclosure for 60x48mm PCB
FDM 3D printable (PETG/ASA recommended)
"""
from build123d import *

# === PARAMETERS ===
tol = 0.2           # FDM tolerance for mating surfaces
wall = 2.5          # wall thickness
corner_r = 3        # outer corner radius

# PCB
pcb_w = 60          # PCB width (X)
pcb_l = 48          # PCB length (Y)
pcb_t = 1.6         # PCB thickness
pcb_clearance = 0.5 # gap between PCB edge and inner wall

# Mounting holes (relative to PCB bottom-left = 0,0)
mh_positions = [(3.5, 3.5), (56.5, 3.5), (3.5, 44.5), (56.5, 44.5)]
mh_dia = 3.2        # M3 through-hole
standoff_od = 6     # standoff outer diameter
standoff_h = 10     # height from base floor to PCB bottom

# Antenna
antenna_overhang = 4     # ESP32-C6 antenna beyond PCB top edge
antenna_keepout_w = 14   # width of thin-wall zone
antenna_center_x = 30    # ESP32 center X on PCB
antenna_wall_t = 0.8     # thin wall for RF transparency

# Components
max_comp_h = 6.5    # tallest component above PCB (JST PH)

# USB-C (left wall)
usbc_y = 14         # Y center on PCB
usbc_cut_w = 10     # cutout width
usbc_cut_h = 4      # cutout height

# Buttons (left wall)
sw1_y = 26          # Boot button Y on PCB
sw2_y = 36          # Reset button Y on PCB
btn_hole_dia = 3    # button access hole diameter

# Qwiic connectors (right wall)
qwiic1_y = 13.5     # CN4 Y on PCB
qwiic2_y = 34       # CN5 Y on PCB
qwiic_cut_w = 8     # cutout width
qwiic_cut_h = 5     # cutout height

# Cable glands PG7 (Y-max wall)
gland_dia = 5.5     # M5 cable gland hole
gland_positions_x = [15, 30, 45]  # X positions on PCB

# Battery
batt_w = 50         # 1000mAh LiPo (LP503449)
batt_l = 34
batt_t = 5.5

# Lid
lid_overlap = 4     # lid plug depth into base
lid_wall = 1.5      # lid plug wall thickness
gasket_w = 2.2      # O-ring groove width (for 2mm cord)
gasket_d = 1.5      # O-ring groove depth
screw_dia = 3.2     # M3 screw through-hole
screw_cs_dia = 6    # countersink diameter
screw_cs_depth = 1.8
insert_dia = 4.2    # M3 brass heat-set insert hole
insert_depth = 5    # insert hole depth

# Light sensor (VEML7700) window in lid
light_sensor_x = 13.92
light_sensor_y = 3
light_window_dia = 6
light_window_t = 0.4

# Hinge
hinge_dia = 5
hinge_pin_dia = 3.2
hinge_spacing = 50
hinge_boss_h = 8

# Ball joint sockets (X+ wall)
socket_margin = 12       # distance from Y wall edges

# === DERIVED DIMENSIONS ===
cavity_w = pcb_w + 2 * pcb_clearance
yplus_extra = 5          # extra space beyond PCB on Y+ side
cavity_l = pcb_l + antenna_overhang + 2 * pcb_clearance + yplus_extra
extra_top = 10           # extra headroom above components
cavity_h = standoff_h + pcb_t + max_comp_h + 0.5 + extra_top

outer_w = cavity_w + 2 * wall
outer_l = cavity_l + 2 * wall
base_h = wall + cavity_h

pcb_ox = wall + pcb_clearance
pcb_oy = wall + pcb_clearance + antenna_overhang
pcb_oz = wall + standoff_h


# =============================================================
# BASE
# =============================================================
def make_base():
    with BuildPart() as base:
        # Outer shell
        with BuildSketch():
            RectangleRounded(outer_w, outer_l, corner_r)
        extrude(amount=base_h)

        # Hollow interior
        inner_r = max(corner_r - wall, 0.5)
        with BuildSketch(Plane.XY.offset(wall)):
            RectangleRounded(cavity_w, cavity_l, inner_r)
        extrude(amount=cavity_h + 1, mode=Mode.SUBTRACT)

        # Standoffs + insert bosses
        for mx, my in mh_positions:
            sx = -outer_w / 2 + pcb_ox + mx
            sy = -outer_l / 2 + pcb_oy + my
            # Standoff cylinder
            with BuildSketch(Plane.XY.offset(wall)):
                with Locations([(sx, sy)]):
                    Circle(standoff_od / 2)
            extrude(amount=standoff_h)
            # Heat-set insert hole from bottom of enclosure into standoff
            with BuildSketch(Plane.XY.offset(-0.1)):
                with Locations([(sx, sy)]):
                    Circle(insert_dia / 2)
            extrude(amount=wall + insert_depth + 0.1, mode=Mode.SUBTRACT)

        # Cable gland hole M5 (Y+ wall, X+ side)
        gland_cx = outer_w / 4 - 33.2    # X+ side, shifted
        gland_cz = wall + base_h / 2     # mid-height
        gland_plane = Plane(
            origin=(gland_cx, outer_l / 2 - wall - 0.1, gland_cz),
            z_dir=(0, 1, 0)
        )
        with BuildSketch(gland_plane):
            Circle(gland_dia / 2)
        extrude(amount=wall + 0.2, mode=Mode.SUBTRACT)

        # Cable gland hole M5 (X+ wall, between Qwiic connectors) - Soil sensor
        soil_cy = -outer_l / 2 + pcb_oy + (qwiic1_y + qwiic2_y) / 2
        soil_cz = wall + base_h / 2 + 3
        soil_plane = Plane(
            origin=(outer_w / 2 - wall - 0.1, soil_cy, soil_cz),
            z_dir=(1, 0, 0)
        )
        with BuildSketch(soil_plane):
            Circle(gland_dia / 2)
        extrude(amount=wall + 0.2, mode=Mode.SUBTRACT)

        # Antenna thin wall (Y-min wall)
        ant_cx = -outer_w / 2 + pcb_ox + antenna_center_x
        with BuildSketch(Plane.XZ.offset(-outer_l / 2 + antenna_wall_t)):
            with Locations([(ant_cx, pcb_oz + (base_h - pcb_oz) / 2)]):
                Rectangle(antenna_keepout_w, base_h - pcb_oz + 4)
        extrude(amount=wall - antenna_wall_t + 0.1, mode=Mode.SUBTRACT)

        # Battery retainer walls with snap clips
        batt_cx = -outer_w / 2 + pcb_ox + pcb_w / 2
        batt_cy = -outer_l / 2 + pcb_oy + pcb_l / 2
        clip_wall = 1.5
        clip_lip = 1.0      # overhang lip to hold battery down
        clip_gap = 0.3      # clearance around battery
        for side in [-1, 1]:
            rx = batt_cx + side * (batt_w / 2 + clip_gap + clip_wall / 2)
            # Vertical wall
            with BuildSketch(Plane.XY.offset(wall)):
                with Locations([(rx, batt_cy)]):
                    Rectangle(clip_wall, batt_l)
            extrude(amount=batt_t + 1)
            # Snap lip overhanging battery top
            lip_x = rx - side * (clip_wall / 2 + clip_lip / 2)
            with BuildSketch(Plane.XY.offset(wall + batt_t)):
                with Locations([(lip_x, batt_cy)]):
                    Rectangle(clip_lip, batt_l * 0.4)
            extrude(amount=1)

    return base.part


# =============================================================
# LID
# =============================================================
def make_lid():
    plug_w = outer_w - 2 * wall - tol
    plug_l = outer_l - 2 * wall - tol
    plug_inner_w = plug_w - 2 * lid_wall
    plug_inner_l = plug_l - 2 * lid_wall
    plug_r = max(corner_r - wall, 0.5)
    plug_inner_r = max(corner_r - wall - lid_wall, 0.5)

    with BuildPart() as lid:
        # Top plate
        with BuildSketch():
            RectangleRounded(outer_w, outer_l, corner_r)
        extrude(amount=wall)

        # Inner plug walls (extending downward)
        with BuildSketch():
            RectangleRounded(plug_w, plug_l, plug_r)
        extrude(amount=-lid_overlap)

        # Hollow out the plug
        with BuildSketch():
            RectangleRounded(plug_inner_w, plug_inner_l, plug_inner_r)
        extrude(amount=-lid_overlap - 0.1, mode=Mode.SUBTRACT)

        # Screw holes through lid (M3 countersunk)
        for mx, my in mh_positions:
            sx = -outer_w / 2 + pcb_ox + mx
            sy = -outer_l / 2 + pcb_oy + my
            # Through hole
            with BuildSketch(Plane.XY.offset(-lid_overlap - 0.1)):
                with Locations([(sx, sy)]):
                    Circle(screw_dia / 2)
            extrude(amount=wall + lid_overlap + 0.2, mode=Mode.SUBTRACT)
            # Countersink
            with Locations([(sx, sy, wall - screw_cs_depth)]):
                Cone(screw_dia / 2, screw_cs_dia / 2, screw_cs_depth + 0.1,
                     mode=Mode.SUBTRACT)


    return lid.part


# =============================================================
# MAIN — generate and export
# =============================================================
if __name__ == "__main__":
    base = make_base()
    lid = make_lid()

    export_stl(base, "enclosure_base.stl")
    export_stl(lid, "enclosure_lid.stl")
    export_step(base, "enclosure_base.step")
    export_step(lid, "enclosure_lid.step")
    print("Exported: enclosure_base.stl, enclosure_lid.stl, enclosure_base.step, enclosure_lid.step")
