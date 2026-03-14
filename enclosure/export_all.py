"""
Export all enclosure parts as STEP files for Fusion 360.
Ball/Nut/Socket scaled to 90% (-10%).
Each part is exported both standalone and in assembled position.
"""
import math
import os
from build123d import *

os.chdir(os.path.dirname(os.path.abspath(__file__)))

SCALE = 0.9  # -10% for ball joint components

# === ENCLOSURE DIMENSIONS (from enclosure.py) ===
wall = 2.5
outer_w = 66
outer_l = 63
base_h = 31.1
pcb_oy = 7.2
qwiic1_y = 13.5
qwiic2_y = 34

# === BALL JOINT POSITIONS ===
margin = 12
j1_cy = -outer_l / 2 + margin
j2_cy = outer_l / 2 - margin
joint_x = outer_w / 2
socket_z_mid = wall + base_h / 2

# === 1. ENCLOSURE BASE & LID (already built) ===
print("Loading enclosure base and lid...")
base = import_step("enclosure_base.step")
lid = import_step("enclosure_lid.step")

# === 2. CABLE GLANDS ===
print("Building cable glands...")
gland_body_od = 9.5
gland_body_len = 12
gland_nut_af = 13
gland_nut_h = 3
gland_thread_od = 5.5
gland_thread_len = 5

with BuildPart() as gland_bp:
    Cylinder(gland_thread_od / 2, gland_thread_len)
    with BuildPart(Plane.XY.offset(gland_thread_len)):
        Cylinder(gland_body_od / 2, gland_body_len)
    with BuildPart(Plane.XY.offset(-gland_nut_h)):
        with BuildSketch():
            RegularPolygon(gland_nut_af / 2, 6)
        extrude(amount=gland_nut_h)
gland = gland_bp.part

gland_cx = outer_w / 4 - 33.2
gland_cz = wall + base_h / 2
solar_gland = Pos(gland_cx, outer_l / 2 - wall + gland_thread_len - 2.5, gland_cz) * Rot(90, 0, 0) * gland

soil_cy = -outer_l / 2 + pcb_oy + (qwiic1_y + qwiic2_y) / 2
soil_cz = wall + base_h / 2 + 3
soil_gland = Pos(outer_w / 2 - wall + gland_thread_len - 2.5, soil_cy, soil_cz) * Rot(0, 90, 0) * gland

# === 3. BATTERY ===
print("Building battery...")
batt_w, batt_l, batt_t = 50, 34, 5.5
batt_cx = 0
batt_cy = -outer_l / 2 + pcb_oy + 48 / 2
batt_cz = wall + batt_t / 2
with BuildPart() as batt_bp:
    with BuildPart(Pos(batt_cx, batt_cy, batt_cz)):
        Box(batt_w, batt_l, batt_t)
battery = batt_bp.part

# === 4. BALL JOINT COMPONENTS (scaled 90%) ===
print(f"Loading ball joint STLs and scaling to {SCALE*100:.0f}%...")
ball_stl = import_stl("Ball-18mm.stl")
nut_stl = import_stl("Nut-18mm.stl")
socket_stl = import_stl("Socket-18mm.stl")

# Scale each component around its own center
ball_scaled = ball_stl.scale(SCALE)
nut_scaled = nut_stl.scale(SCALE)
socket_scaled = socket_stl.scale(SCALE)

# Socket: closed end flush with outer wall
socket_rot = Rot(0, 90, 0)
socket_x = joint_x + 12 * SCALE  # adjust for scaled depth
socket1 = Pos(socket_x, j1_cy, socket_z_mid) * socket_rot * socket_scaled
socket2 = Pos(socket_x, j2_cy, socket_z_mid) * socket_rot * socket_scaled

# Nut
nut_rot = Rot(0, 90, 0)
nut1 = Pos(joint_x + 3, j1_cy, socket_z_mid) * nut_rot * nut_scaled
nut2 = Pos(joint_x + 3, j2_cy, socket_z_mid) * nut_rot * nut_scaled

# Ball
ball_rot = Rot(0, -90, 90)
ball_x = joint_x + 10
ball_stem_extent = 12.4 * SCALE  # scaled stem length
ball1 = Pos(ball_x, j1_cy, socket_z_mid) * ball_rot * ball_scaled
ball2 = Pos(ball_x, j2_cy, socket_z_mid) * ball_rot * ball_scaled

# === 5. SOIL SENSOR STAKES ===
print("Building stakes...")
stake_cyl_len = 30
cross_arm_h = 7
cross_tip_angle = 5
cross_const_len = 50
cross_taper_len = 150
core_r = 1.5
stake_cyl_r = cross_arm_h
arm_half_w = cross_arm_h * math.tan(math.radians(cross_tip_angle))

def _cross_sketch():
    h = cross_arm_h
    hw = arm_half_w
    Circle(core_r)
    Polygon((-hw, 0), (hw, 0), (0, h), align=None)
    Polygon((-hw, 0), (hw, 0), (0, -h), align=None)
    Polygon((0, -hw), (0, hw), (h, 0), align=None)
    Polygon((0, -hw), (0, hw), (-h, 0), align=None)

taper_start = stake_cyl_len + cross_const_len

with BuildPart() as tapered_bp:
    with BuildSketch(Plane.YZ.offset(taper_start)):
        _cross_sketch()
    extrude(amount=cross_taper_len)
    with Locations([(taper_start + cross_taper_len / 2, 0, 0)]):
        Cone(cross_arm_h, 0.01, cross_taper_len,
             rotation=(0, 90, 0), mode=Mode.INTERSECT)

with BuildPart() as stake_bp:
    with BuildSketch(Plane.YZ):
        Circle(stake_cyl_r)
    extrude(amount=stake_cyl_len)
    with BuildSketch(Plane.YZ.offset(stake_cyl_len)):
        _cross_sketch()
    extrude(amount=cross_const_len)
    add(tapered_bp.part)
stake = stake_bp.part

stake_start_x = ball_x + ball_stem_extent
stake1 = Pos(stake_start_x, j1_cy, socket_z_mid) * stake
stake2 = Pos(stake_start_x, j2_cy, socket_z_mid) * stake

# === EXPORT ===
out_dir = "export_step"
os.makedirs(out_dir, exist_ok=True)

# Standalone parts (at origin, for 3D printing)
print("\nExporting standalone parts...")
export_step(base, f"{out_dir}/base.step")
export_step(lid, f"{out_dir}/lid.step")
export_step(gland, f"{out_dir}/gland_m5.step")
export_step(battery, f"{out_dir}/battery_1000mah.step")
export_step(stake, f"{out_dir}/stake.step")

# Scaled ball joint parts (at origin)
export_step(ball_scaled, f"{out_dir}/ball_18mm_90pct.step")
export_step(nut_scaled, f"{out_dir}/nut_18mm_90pct.step")
export_step(socket_scaled, f"{out_dir}/socket_18mm_90pct.step")

# Assembled parts (in final position)
print("Exporting assembled parts...")
parts = {
    "base": base,
    "lid": Pos(0, 0, 24) * lid,
    "solar_gland": solar_gland,
    "soil_gland": soil_gland,
    "battery": battery,
    "socket_1": socket1,
    "socket_2": socket2,
    "nut_1": nut1,
    "nut_2": nut2,
    "ball_1": ball1,
    "ball_2": ball2,
    "stake_1": stake1,
    "stake_2": stake2,
}

for name, part in parts.items():
    export_step(part, f"{out_dir}/asm_{name}.step")

# Full assembly as single compound
assembly = Compound(list(parts.values()))
export_step(assembly, f"{out_dir}/full_assembly.step")

print(f"\nDone! Exported {len(parts) + 6} STEP files to {out_dir}/")
print(f"Ball joint components scaled to {SCALE*100:.0f}%")
print(f"\nFiles:")
for f in sorted(os.listdir(out_dir)):
    size = os.path.getsize(f"{out_dir}/{f}") / 1024
    print(f"  {f:40s} {size:7.1f} KB")
