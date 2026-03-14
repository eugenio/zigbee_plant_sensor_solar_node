// =============================================================
// Zigbee Plant Sensor Solar Node — Enclosure
// IP65 outdoor enclosure for 60x48mm PCB
// FDM 3D printable (PETG/ASA recommended)
// =============================================================

// --- Part selector ---
// 0 = assembly view
// 1 = base only
// 2 = lid only
// 3 = solar bracket only
// 4 = ground stake only
// 5 = print layout (all parts flat)
part = 0;

/* [Manufacturing] */
$fn = 48;
tol = 0.2;           // FDM tolerance for mating surfaces
wall = 2.5;          // wall thickness
corner_r = 3;        // outer corner radius

/* [PCB] */
pcb_w = 60;          // PCB width (X)
pcb_l = 48;          // PCB length (Y)
pcb_t = 1.6;         // PCB thickness
pcb_clearance = 0.5; // gap between PCB edge and inner wall

// Mounting holes (relative to PCB bottom-left = 0,0)
mh_dx1 = 3.5;
mh_dy1 = 3.5;
mh_dx2 = 56.5;
mh_dy2 = 44.5;
mh_dia = 3.2;        // M3 through-hole
standoff_od = 6;      // standoff outer diameter
standoff_h = 10;      // height from base floor to PCB bottom

/* [Antenna] */
antenna_overhang = 4;     // ESP32-C6 antenna beyond PCB top edge
antenna_keepout_w = 14;   // width of thin-wall zone
antenna_center_x = 30;    // ESP32 center X on PCB
antenna_wall_t = 0.8;     // thin wall for RF transparency

/* [Components] */
max_comp_h = 6.5;    // tallest component above PCB (JST PH)

// USB-C (left wall)
usbc_y = 14;          // Y center on PCB
usbc_cut_w = 10;      // cutout width
usbc_cut_h = 4;       // cutout height

// Buttons (left wall)
sw1_y = 26;           // Boot button Y on PCB
sw2_y = 36;           // Reset button Y on PCB
btn_hole_dia = 3;     // button access hole diameter

// Qwiic connectors (right wall)
qwiic1_y = 13.5;      // CN4 Y on PCB
qwiic2_y = 34;        // CN5 Y on PCB
qwiic_cut_w = 8;      // cutout width
qwiic_cut_h = 5;      // cutout height

// Light sensor (VEML7700) window in lid
light_sensor_x = 13.92; // X on PCB
light_sensor_y = 3;     // Y on PCB
light_window_dia = 6;   // window diameter
light_window_t = 0.4;   // thin wall thickness

/* [Battery] */
batt_w = 48;
batt_l = 30;
batt_t = 8;
batt_pad = 1;         // padding around battery

/* [Cable Glands] */
gland_dia = 12.5;     // PG7 cable gland (12.5mm hole)
// Cable gland positions on bottom (Y-max) wall, X relative to PCB
gland_x1 = 15;        // solar cable
gland_x2 = 30;        // sensor cable 1
gland_x3 = 45;        // sensor cable 2

/* [Lid] */
lid_overlap = 4;      // lid plug depth into base
lid_wall = 1.5;       // lid plug wall thickness
gasket_w = 2.2;       // O-ring groove width (for 2mm cord)
gasket_d = 1.5;       // O-ring groove depth
screw_dia = 3.2;      // M3 screw through-hole
screw_cs_dia = 6;     // countersink diameter
screw_cs_depth = 1.8; // countersink depth
insert_dia = 4.2;     // M3 brass heat-set insert hole
insert_depth = 5;     // insert hole depth

/* [Solar Bracket] */
panel_w = 110;        // solar panel width
panel_l = 70;         // solar panel length
panel_t = 3;          // panel thickness
bracket_arm_w = 12;   // bracket arm width
bracket_arm_t = 3;    // bracket arm thickness
bracket_arm_l = 40;   // arm length from hinge to cradle
hinge_dia = 5;        // hinge boss diameter
hinge_pin_dia = 3.2;  // M3 hinge pin hole
hinge_spacing = 50;   // distance between hinge bosses
hinge_boss_h = 8;     // hinge boss height on lid

/* [Stake] */
stake_socket_dia = 12;
stake_socket_depth = 15;
stake_length = 150;
stake_tip_dia = 4;
stake_cross_t = 3;    // cruciform arm thickness

// =============================================================
// DERIVED DIMENSIONS
// =============================================================

// Internal cavity
cavity_w = pcb_w + 2 * pcb_clearance;
cavity_l = pcb_l + antenna_overhang + 2 * pcb_clearance;
cavity_h = standoff_h + pcb_t + max_comp_h + 0.5;

// Outer dimensions
outer_w = cavity_w + 2 * wall;
outer_l = cavity_l + 2 * wall;
base_h = wall + cavity_h;

// PCB origin inside cavity (offset from inner wall)
pcb_ox = wall + pcb_clearance;
pcb_oy = wall + pcb_clearance + antenna_overhang; // antenna space at Y-min
pcb_oz = wall + standoff_h;

// Screw positions (same as mounting holes, relative to enclosure origin)
screw_positions = [
    [pcb_ox + mh_dx1, pcb_oy + mh_dy1],
    [pcb_ox + mh_dx2, pcb_oy + mh_dy1],
    [pcb_ox + mh_dx1, pcb_oy + mh_dy2],
    [pcb_ox + mh_dx2, pcb_oy + mh_dy2],
];

// =============================================================
// HELPER MODULES
// =============================================================

module rounded_box(w, l, h, r) {
    hull() {
        for (x = [r, w - r], y = [r, l - r])
            translate([x, y, 0])
                cylinder(h = h, r = r);
    }
}

module rounded_box_shell(w, l, h, wall_t, r) {
    difference() {
        rounded_box(w, l, h, r);
        translate([wall_t, wall_t, wall_t])
            rounded_box(w - 2*wall_t, l - 2*wall_t, h, max(r - wall_t, 0.5));
    }
}

module standoff(h, od, id) {
    difference() {
        cylinder(h = h, d = od);
        translate([0, 0, -0.1])
            cylinder(h = h + 0.2, d = id);
    }
}

// Countersunk screw hole (from top)
module countersunk_hole(through_d, cs_d, cs_depth, total_h) {
    union() {
        // Through hole
        translate([0, 0, -0.1])
            cylinder(h = total_h + 0.2, d = through_d);
        // Countersink
        translate([0, 0, total_h - cs_depth])
            cylinder(h = cs_depth + 0.1, d1 = through_d, d2 = cs_d);
    }
}

// =============================================================
// BASE
// =============================================================

module base() {
    difference() {
        union() {
            // Main box shell (open top)
            rounded_box_shell(outer_w, outer_l, base_h, wall, corner_r);

            // Lid seating rim (inner lip at top of base)
            translate([0, 0, base_h - 0.01])
                difference() {
                    rounded_box(outer_w, outer_l, 1.5, corner_r);
                    translate([wall + lid_wall + tol, wall + lid_wall + tol, -0.1])
                        rounded_box(
                            outer_w - 2*(wall + lid_wall + tol),
                            outer_l - 2*(wall + lid_wall + tol),
                            1.7,
                            max(corner_r - wall - lid_wall - tol, 0.5)
                        );
                }

            // PCB standoffs (4x M3)
            for (pos = screw_positions)
                translate([pos[0], pos[1], wall])
                    standoff(standoff_h, standoff_od, mh_dia);

            // Heat-set insert bosses (extend standoffs upward for insert)
            for (pos = screw_positions)
                translate([pos[0], pos[1], wall + standoff_h + pcb_t])
                    cylinder(h = insert_depth + 2, d = standoff_od);

            // Stake mount boss (external, bottom face)
            translate([outer_w/2, outer_l/2, 0])
                rotate([180, 0, 0])
                    cylinder(h = 5, d = stake_socket_dia + 2*wall);
        }

        // --- CUTOUTS ---

        // Heat-set insert holes (into standoff bosses above PCB)
        for (pos = screw_positions)
            translate([pos[0], pos[1], wall + standoff_h + pcb_t - 0.1])
                cylinder(h = insert_depth + 3, d = insert_dia);

        // USB-C port (left wall, X=0 face)
        translate([
            -0.1,
            pcb_oy + usbc_y - usbc_cut_w/2,
            pcb_oz + pcb_t
        ])
            cube([wall + 0.2, usbc_cut_w, usbc_cut_h]);

        // Button access holes (left wall)
        for (by = [sw1_y, sw2_y])
            translate([
                -0.1,
                pcb_oy + by,
                pcb_oz + pcb_t + 0.75
            ])
                rotate([0, 90, 0])
                    cylinder(h = wall + 0.2, d = btn_hole_dia);

        // Qwiic connector slots (right wall)
        for (qy = [qwiic1_y, qwiic2_y])
            translate([
                outer_w - wall - 0.1,
                pcb_oy + qy - qwiic_cut_w/2,
                pcb_oz
            ])
                cube([wall + 0.2, qwiic_cut_w, qwiic_cut_h]);

        // Cable gland holes (bottom wall, Y-max face)
        for (gx = [gland_x1, gland_x2, gland_x3])
            translate([
                pcb_ox + gx,
                outer_l - wall - 0.1,
                wall + gland_dia/2 + 2
            ])
                rotate([-90, 0, 0])
                    cylinder(h = wall + 0.2, d = gland_dia);

        // Stake socket hole (bottom face, center)
        translate([outer_w/2, outer_l/2, -5.1])
            cylinder(h = wall + stake_socket_depth + 5, d = stake_socket_dia + tol);

        // Antenna thin wall section (top wall, Y-min face)
        // Cut the wall from 2.5mm down to antenna_wall_t
        translate([
            pcb_ox + antenna_center_x - antenna_keepout_w/2,
            antenna_wall_t,
            pcb_oz - 2
        ])
            cube([
                antenna_keepout_w,
                wall - antenna_wall_t + 0.1,
                base_h - pcb_oz + 4
            ]);

        // Battery compartment clearance (visual guide, not structural)
        // Battery sits on base floor between standoffs
    }

    // Battery retainer walls (two low walls to cradle LiPo)
    // Positioned at base floor, centered under PCB
    batt_cx = pcb_ox + pcb_w/2;
    batt_cy = pcb_oy + pcb_l/2;
    translate([batt_cx - batt_w/2 - 1.5, batt_cy - batt_l/2, wall])
        cube([1.5, batt_l, batt_t + 1]);
    translate([batt_cx + batt_w/2, batt_cy - batt_l/2, wall])
        cube([1.5, batt_l, batt_t + 1]);
}

// =============================================================
// LID
// =============================================================

module lid() {
    lid_total_h = wall + lid_overlap;

    difference() {
        union() {
            // Top plate
            rounded_box(outer_w, outer_l, wall, corner_r);

            // Inner plug walls (drop into base)
            translate([wall + tol/2, wall + tol/2, -lid_overlap])
                difference() {
                    rounded_box(
                        outer_w - 2*wall - tol,
                        outer_l - 2*wall - tol,
                        lid_overlap,
                        max(corner_r - wall, 0.5)
                    );
                    translate([lid_wall, lid_wall, -0.1])
                        rounded_box(
                            outer_w - 2*wall - tol - 2*lid_wall,
                            outer_l - 2*wall - tol - 2*lid_wall,
                            lid_overlap + 0.2,
                            max(corner_r - wall - lid_wall, 0.5)
                        );
                }

            // Hinge mount bosses on top surface
            for (side = [-1, 1])
                translate([
                    outer_w/2 + side * hinge_spacing/2,
                    corner_r + 2,
                    wall
                ])
                    cylinder(h = hinge_boss_h, d = hinge_dia + 2*wall);
        }

        // --- CUTOUTS ---

        // Gasket groove (around outer face of plug walls)
        translate([0, 0, -lid_overlap + lid_overlap/2 - gasket_w/2])
            difference() {
                translate([wall + tol/2 - gasket_d, wall + tol/2 - gasket_d, 0])
                    rounded_box(
                        outer_w - 2*wall - tol + 2*gasket_d,
                        outer_l - 2*wall - tol + 2*gasket_d,
                        gasket_w,
                        max(corner_r - wall + gasket_d, 0.5)
                    );
                translate([wall + tol/2, wall + tol/2, -0.1])
                    rounded_box(
                        outer_w - 2*wall - tol,
                        outer_l - 2*wall - tol,
                        gasket_w + 0.2,
                        max(corner_r - wall, 0.5)
                    );
            }

        // Screw holes (countersunk from top, M3)
        for (pos = screw_positions)
            translate([pos[0], pos[1], -lid_overlap - 0.1])
                cylinder(h = lid_total_h + 0.2, d = screw_dia);
        // Countersinks
        for (pos = screw_positions)
            translate([pos[0], pos[1], wall - screw_cs_depth])
                cylinder(h = screw_cs_depth + 0.1, d1 = screw_dia, d2 = screw_cs_dia);

        // Light sensor window (VEML7700)
        // Thin out the lid above the sensor to light_window_t
        translate([
            pcb_ox + light_sensor_x,
            pcb_oy + light_sensor_y,
            light_window_t
        ])
            cylinder(h = wall, d = light_window_dia);

        // Hinge pin holes
        for (side = [-1, 1])
            translate([
                outer_w/2 + side * hinge_spacing/2,
                corner_r + 2,
                wall - 0.1
            ])
                cylinder(h = hinge_boss_h + 0.2, d = hinge_pin_dia);
    }
}

// =============================================================
// SOLAR BRACKET
// =============================================================

module solar_bracket() {
    cradle_lip = 1.5;
    cradle_wall = 2;

    // Hinge knuckles (two, matching lid boss spacing)
    for (side = [-1, 1]) {
        translate([side * hinge_spacing/2, 0, 0]) {
            difference() {
                cylinder(h = bracket_arm_w, d = hinge_dia + 2*bracket_arm_t);
                translate([0, 0, -0.1])
                    cylinder(h = bracket_arm_w + 0.2, d = hinge_pin_dia + tol);
            }

            // Arm extending from hinge to cradle
            translate([0, 0, 0])
                hull() {
                    cylinder(h = bracket_arm_t, d = hinge_dia + 2*bracket_arm_t);
                    translate([0, bracket_arm_l, 0])
                        cube([bracket_arm_w, 0.1, bracket_arm_t], center = true);
                }
        }
    }

    // Panel cradle (rectangular frame)
    translate([0, bracket_arm_l, 0]) {
        difference() {
            // Outer frame
            translate([-panel_w/2, 0, 0])
                cube([panel_w, panel_l, cradle_wall]);
            // Inner cutout (panel sits here)
            translate([-panel_w/2 + cradle_lip, cradle_lip, -0.1])
                cube([panel_w - 2*cradle_lip, panel_l - 2*cradle_lip, cradle_wall + 0.2]);
        }
        // Cradle lip walls (hold panel in place)
        difference() {
            translate([-panel_w/2, 0, cradle_wall])
                cube([panel_w, panel_l, panel_t + 0.5]);
            translate([-panel_w/2 + cradle_lip, cradle_lip, cradle_wall - 0.1])
                cube([panel_w - 2*cradle_lip, panel_l - 2*cradle_lip, panel_t + 1]);
        }
    }
}

// =============================================================
// GROUND STAKE
// =============================================================

module stake() {
    plug_h = stake_socket_depth - 1;
    plug_dia = stake_socket_dia - tol;

    // Plug (inserts into base socket)
    difference() {
        cylinder(h = plug_h, d = plug_dia);
        // Flat for anti-rotation
        translate([plug_dia/2 - 1, -plug_dia, -0.1])
            cube([plug_dia, plug_dia * 2, plug_h + 0.2]);
    }

    // Stake body (cruciform cross-section, tapered)
    translate([0, 0, -stake_length]) {
        // Cruciform taper
        hull() {
            // Top (full width)
            translate([0, 0, stake_length])
                intersection() {
                    cylinder(h = 0.1, d = plug_dia);
                    union() {
                        cube([plug_dia, stake_cross_t, 0.1], center = true);
                        cube([stake_cross_t, plug_dia, 0.1], center = true);
                    }
                }
            // Tip (point)
            cylinder(h = 0.1, d = stake_tip_dia);
        }
    }
}

// =============================================================
// GHOST PCB (for assembly visualization)
// =============================================================

module ghost_pcb() {
    color("green", 0.4)
        translate([pcb_ox, pcb_oy, pcb_oz])
            cube([pcb_w, pcb_l, pcb_t]);

    // Antenna overhang indicator
    color("red", 0.3)
        translate([
            pcb_ox + antenna_center_x - antenna_keepout_w/2,
            pcb_oy - antenna_overhang,
            pcb_oz
        ])
            cube([antenna_keepout_w, antenna_overhang, 3]);
}

module ghost_battery() {
    batt_cx = pcb_ox + pcb_w/2;
    batt_cy = pcb_oy + pcb_l/2;
    color("blue", 0.3)
        translate([batt_cx - batt_w/2, batt_cy - batt_l/2, wall + batt_pad])
            cube([batt_w, batt_l, batt_t]);
}

// =============================================================
// ASSEMBLY & PART SELECTOR
// =============================================================

module assembly() {
    color("DimGray") base();

    color("Silver", 0.8)
        translate([0, 0, base_h + 1.5])
            lid();

    // Solar bracket at 45 degrees
    translate([outer_w/2, corner_r + 2, base_h + 1.5 + wall + hinge_boss_h/2])
        rotate([45, 0, 0])
            color("Orange") solar_bracket();

    // Ground stake
    translate([outer_w/2, outer_l/2, -5])
        rotate([180, 0, 0])
            color("SaddleBrown") stake();

    ghost_pcb();
    ghost_battery();
}

module print_layout() {
    // Base
    base();

    // Lid (flipped for printing)
    translate([outer_w + 15, 0, wall])
        rotate([180, 0, 0])
            lid();

    // Solar bracket (flat)
    translate([0, outer_l + 15, 0])
        solar_bracket();

    // Stake (on side)
    translate([outer_w + 60, outer_l + 15, 0])
        rotate([0, 0, 90])
            stake();
}

if (part == 0) assembly();
else if (part == 1) base();
else if (part == 2) lid();
else if (part == 3) solar_bracket();
else if (part == 4) stake();
else if (part == 5) print_layout();
