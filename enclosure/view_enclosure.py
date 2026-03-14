# %%
# Open this file in VS Code, then click "Run Cell" (requires Jupyter extension)
# Make sure OCP CAD Viewer is open: Ctrl+Shift+P -> "OCP CAD Viewer: Open Viewer"

import math
from build123d import *
from ocp_vscode import show
from ocp_vscode.comms import set_port

set_port(3940)

# %% Load and display enclosure with PCB assembly

# --- Enclosure dimensions (must match enclosure.py) ---
wall = 2.5
outer_w = 66      # X
outer_l = 63      # Y
base_h = 31.1     # Z (wall + cavity_h)
pcb_oy = 7.2      # wall + pcb_clearance + antenna_overhang
qwiic1_y = 13.5
qwiic2_y = 34

# --- Global rotation: -90° Z so USB-C faces Y+ ---
rot = Rot(0, 0, -90)

# --- Base & Lid ---
base = import_step("enclosure_base.step")
lid = import_step("enclosure_lid.step")
pcb = import_step("pcb_quilter.step")

# KiCad board center in STEP coords: (130, -102)
# Enclosure PCB center: (0, -0.5), Z on standoffs: 12.5
pcb_positioned = Pos(-130, 101.5, 12.5) * pcb

# Position lid above base
lid_up = Pos(0, 0, 24) * lid

# --- Cable gland models (simple cylinder + hex nut representation) ---
gland_body_od = 9.5
gland_body_len = 12
gland_nut_af = 13       # across flats
gland_nut_h = 3
gland_thread_od = 5.5
gland_thread_len = 5

def make_gland():
    """Simple M5 cable gland model: body + hex nut."""
    with BuildPart() as g:
        # Threaded section
        Cylinder(gland_thread_od / 2, gland_thread_len)
        # Body
        with BuildPart(Plane.XY.offset(gland_thread_len)):
            Cylinder(gland_body_od / 2, gland_body_len)
        # Hex nut at base
        with BuildPart(Plane.XY.offset(-gland_nut_h)):
            with BuildSketch():
                RegularPolygon(gland_nut_af / 2, 6)
            extrude(amount=gland_nut_h)
    return g.part

gland = make_gland()

# Solar gland (Y+ wall) - same positioning as enclosure.py
gland_cx = outer_w / 4 - 33.2
gland_cz = wall + base_h / 2
# Gland axis along Y, body outside, nut inside
solar_gland = Pos(gland_cx, outer_l / 2 - wall + gland_thread_len - 2.5, gland_cz) * Rot(90, 0, 0) * gland

# Soil sensor gland (X+ wall, between Qwiic connectors)
soil_cy = -outer_l / 2 + pcb_oy + (qwiic1_y + qwiic2_y) / 2
soil_cz = wall + base_h / 2 + 3
# Gland axis along X, body outside, nut inside - rotated 180° per user request
soil_gland = Pos(outer_w / 2 - wall + gland_thread_len - 2.5, soil_cy, soil_cz) * Rot(0, 90, 0) * gland

# --- Battery (1000mAh LiPo) ---
batt_w, batt_l, batt_t = 50, 34, 5.5
batt_cx = 0  # centered
batt_cy = -outer_l / 2 + pcb_oy + 48 / 2  # centered under PCB
batt_cz = wall + batt_t / 2
with BuildPart() as batt_part:
    with BuildPart(Pos(batt_cx, batt_cy, batt_cz)):
        Box(batt_w, batt_l, batt_t)
battery = batt_part.part

# --- Ball joints (Printables 666758 - actual 18mm models) ---
ball_stl = import_stl("Ball-18mm.stl")
nut_stl = import_stl("Nut-18mm.stl")
socket_stl = import_stl("Socket-18mm.stl")

# Socket: Z from -12 to -2, axis along Z, opening at Z=-2
# We need the socket axis along X, opening pointing outward (+X)
# Ball: ball at top (Z+), stem at bottom (Y-)
# Nut: flat hex nut, axis along Z

# Position on X+ wall at two extreme Y positions
margin = 12  # distance from Y wall edges
j1_cy = -outer_l / 2 + margin
j2_cy = outer_l / 2 - margin
joint_x = outer_w / 2  # flush with outer wall

# Socket: Rot(0,90,0) → closed end at X = pos_x - 12, opening at pos_x - 2
# Closed end must touch enclosure outer wall (X = outer_w/2 = joint_x)
# So: pos_x - 12 = joint_x → pos_x = joint_x + 12
socket_rot = Rot(0, 90, 0)
socket_z_mid = wall + base_h / 2  # mid-height of enclosure
socket_x = joint_x + 12  # closed end flush with outer wall

socket1 = Pos(socket_x, j1_cy, socket_z_mid) * socket_rot * socket_stl
socket2 = Pos(socket_x, j2_cy, socket_z_mid) * socket_rot * socket_stl

# Nut on inside of wall (shifted same amount)
nut_rot = Rot(0, 90, 0)
nut1 = Pos(joint_x + 3, j1_cy, socket_z_mid) * nut_rot * nut_stl
nut2 = Pos(joint_x + 3, j2_cy, socket_z_mid) * nut_rot * nut_stl

# Ball in socket, stem coaxial with stake cylinder
# Rot(0, -90, 90): stem(-Y)→+X, sphere(Z+)→-Y, stem axis at Z=0
ball_rot = Rot(0, -90, 90)
ball_x = joint_x + 10          # ball center inside socket cavity
ball_stem_extent = 12.4         # stem tip distance from ball center after rotation
ball1 = Pos(ball_x, j1_cy, socket_z_mid) * ball_rot * ball_stl
ball2 = Pos(ball_x, j2_cy, socket_z_mid) * ball_rot * ball_stl

# --- Soil sensor stakes (extend from ball stems) ---
stake_cyl_len = 30          # cylinder extension length
cross_arm_h = 7             # arm height from center to tip
cross_tip_angle = 5         # external angle at arm tip (degrees)
cross_const_len = 50        # constant cross section length
cross_taper_len = 150       # tapered section to point
core_r = 1.5                # center core radius for printability

# Cylinder radius matches cross arm height
stake_cyl_r = cross_arm_h

# Arm half-width at base: each side at 5° from arm centerline
arm_half_w = cross_arm_h * math.tan(math.radians(cross_tip_angle))

# Taper angle: shrink cross_arm_h to 0 over cross_taper_len
taper_angle = math.degrees(math.atan(cross_arm_h / cross_taper_len))

def _cross_sketch():
    """Draw cross profile in current BuildSketch context."""
    h = cross_arm_h
    hw = arm_half_w
    Circle(core_r)
    Polygon((-hw, 0), (hw, 0), (0, h), align=None)    # +Z arm
    Polygon((-hw, 0), (hw, 0), (0, -h), align=None)   # -Z arm
    Polygon((0, -hw), (0, hw), (h, 0), align=None)     # +Y arm
    Polygon((0, -hw), (0, hw), (-h, 0), align=None)    # -Y arm

def make_stake():
    """Soil sensor stake: 30mm cylinder + 50mm cross + 150mm taper to point."""
    taper_start = stake_cyl_len + cross_const_len

    # Build tapered section: cross extrusion intersected with cone
    with BuildPart() as tapered:
        with BuildSketch(Plane.YZ.offset(taper_start)):
            _cross_sketch()
        extrude(amount=cross_taper_len)
        # Cone: big end (r=arm_h) at taper_start, point at tip
        with Locations([(taper_start + cross_taper_len / 2, 0, 0)]):
            Cone(cross_arm_h, 0.01, cross_taper_len,
                 rotation=(0, 90, 0), mode=Mode.INTERSECT)

    # Build main stake and fuse tapered section
    with BuildPart() as stake:
        # 1. Cylinder (r = cross_arm_h = 7mm, 30mm long)
        with BuildSketch(Plane.YZ):
            Circle(stake_cyl_r)
        extrude(amount=stake_cyl_len)
        # 2. Constant cross section (50mm)
        with BuildSketch(Plane.YZ.offset(stake_cyl_len)):
            _cross_sketch()
        extrude(amount=cross_const_len)
        # 3. Add tapered section
        add(tapered.part)
    return stake.part

stake = make_stake()

# Position stakes flush with ball stem end
stake_start_x = ball_x + ball_stem_extent  # cylinder starts where stem ends
stake1 = Pos(stake_start_x, j1_cy, socket_z_mid) * stake
stake2 = Pos(stake_start_x, j2_cy, socket_z_mid) * stake

# %% Apply rotation and show everything

objects = [base, pcb_positioned, lid_up,
           solar_gland, soil_gland, battery,
           socket1, socket2, nut1, nut2, ball1, ball2,
           stake1, stake2]
names = ["Base", "PCB Assembly", "Lid",
         "Gland Solar P.", "Gland Soil sens.", "Battery 1000mAh",
         "Socket 1", "Socket 2", "Nut 1", "Nut 2", "Ball 1", "Ball 2",
         "Stake 1", "Stake 2"]
colors = ["dimgray", "green", "silver",
          "gold", "gold", "royalblue",
          "darkslategray", "darkslategray", "gray", "gray", "orange", "orange",
          "saddlebrown", "saddlebrown"]
alphas = [0.7, 1.0, 0.5,
          1.0, 1.0, 0.8,
          0.9, 0.9, 0.8, 0.8, 1.0, 1.0,
          1.0, 1.0]

# Apply -90° Z rotation to all objects
rotated = [rot * obj for obj in objects]

show(*rotated, names=names, colors=colors, alphas=alphas)
