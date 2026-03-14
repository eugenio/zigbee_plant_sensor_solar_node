"""
Prepare KiCad PCB files for Quilter AI upload.

Strips traces, vias, zones, and filled zone data from the .kicad_pcb file.
Moves non-fixed components outside the board outline.
Optionally shrinks the board outline to encourage Quilter to minimize area.

Edge-mounted / mechanically-constrained components (connectors, switches)
are kept in place. All other components are moved to a staging area
to the right of the board outline.

Usage:
    python prepare_for_quilter.py [--board-width W] [--board-height H] [--move-all]
                                  [--layers N] [--output-dir DIR]

    Without args: keeps original 60x48mm outline, connectors stay fixed, 4-layer.
    With --board-width/--board-height: resizes to WxH mm.
    With --move-all: moves ALL components outside (let Quilter place everything).
    With --layers: set copper layer count (2, 4, or 6).
    With --output-dir: override output directory name.
"""

import re
import shutil
import argparse
from pathlib import Path

# --- Configuration ---

PROJECT_DIR = Path(__file__).parent / "layouts" / "default"
DEFAULT_OUTPUT_DIR = Path(__file__).parent / "quilter_upload"

# Components that must stay at their current position (edge-mounted connectors, buttons)
FIXED_REFS = {
    "USBC1",  # USB-C connector (left edge)
    "CN1",    # JST PH battery (bottom edge)
    "CN3",    # JST PH solar panel (bottom edge)
    "CN4",    # Qwiic connector - soil (right edge)
    "CN5",    # Qwiic connector - EC (right edge)
    "SW1",    # Boot button (left edge)
    "SW2",    # Reset button (left edge)
    "U5",     # ESP32-C6 (antenna overhangs top edge)
    "H1",     # Mounting hole top-left
    "H2",     # Mounting hole top-right
    "H3",     # Mounting hole bottom-left
    "H4",     # Mounting hole bottom-right
}

# Original board outline coordinates
ORIG_LEFT = 100.0
ORIG_TOP = 78.0
ORIG_RIGHT = 160.0
ORIG_BOTTOM = 126.0
ORIG_WIDTH = ORIG_RIGHT - ORIG_LEFT    # 60mm
ORIG_HEIGHT = ORIG_BOTTOM - ORIG_TOP   # 48mm


def parse_args():
    parser = argparse.ArgumentParser(description="Prepare KiCad files for Quilter AI")
    parser.add_argument("--board-width", type=float, default=None,
                        help="Target board width in mm (default: keep original 60mm)")
    parser.add_argument("--board-height", type=float, default=None,
                        help="Target board height in mm (default: keep original 48mm)")
    parser.add_argument("--move-all", action="store_true",
                        help="Move ALL components outside (let Quilter place everything)")
    parser.add_argument("--layers", type=int, default=4, choices=[2, 4, 6],
                        help="Number of copper layers (default: 4)")
    parser.add_argument("--output-dir", type=str, default=None,
                        help="Output directory (default: quilter_upload)")
    return parser.parse_args()


def read_pcb(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def write_pcb(path: Path, content: str):
    path.write_text(content, encoding="utf-8")


def find_matching_paren(text: str, start: int) -> int:
    """Find the closing parenthesis matching the opening one at `start`."""
    depth = 0
    i = start
    while i < len(text):
        if text[i] == "(":
            depth += 1
        elif text[i] == ")":
            depth -= 1
            if depth == 0:
                return i
        i += 1
    return -1


def remove_segments_vias(content: str) -> str:
    """Remove all (segment ...) and (via ...) top-level entries."""
    # These are tab-indented at top level
    content = re.sub(r"\n\t\(segment\b[^)]*(?:\([^)]*\))*[^)]*\)", "", content)
    content = re.sub(r"\n\t\(via\b[^)]*(?:\([^)]*\))*[^)]*\)", "", content)
    return content


def remove_zones(content: str) -> str:
    """Remove all (zone ...) blocks (multi-line, nested parens)."""
    result = []
    i = 0
    while i < len(content):
        # Look for top-level zone definitions
        match = re.match(r"\n\t\(zone\b", content[i:])
        if match:
            # Find the opening paren of (zone
            zone_start = i + match.start() + 1  # skip the \n
            # But we want to also skip the \n before it
            paren_start = content.index("(zone", zone_start - 5)
            end = find_matching_paren(content, paren_start)
            if end > 0:
                # Skip this zone block entirely (including leading \n\t)
                i = end + 1
                continue
        result.append(content[i])
        i += 1
    return "".join(result)


def remove_filled_zones(content: str) -> str:
    """Remove any (filled_polygon ...) blocks that might exist."""
    content = re.sub(
        r"\n\t\t\(filled_polygon\b.*?\n\t\t\)",
        "",
        content,
        flags=re.DOTALL,
    )
    return content


def extract_footprints(content: str) -> list[dict]:
    """Extract footprint info: reference, position, start/end indices."""
    footprints = []
    pattern = re.compile(r"\n\t\(footprint ")
    for m in pattern.finditer(content):
        start = m.start() + 1  # skip leading \n
        fp_paren_start = content.index("(footprint", start)
        end = find_matching_paren(content, fp_paren_start)
        if end < 0:
            continue

        block = content[fp_paren_start : end + 1]

        # Extract reference
        ref_match = re.search(r'\(property "Reference" "([^"]*)"', block)
        ref = ref_match.group(1) if ref_match else "UNKNOWN"

        # Extract position
        at_match = re.search(r"\(at ([\d.-]+) ([\d.-]+)(?:\s+([\d.-]+))?\)", block)
        if at_match:
            x, y = float(at_match.group(1)), float(at_match.group(2))
            rot = at_match.group(3)
        else:
            x, y, rot = 0, 0, None

        footprints.append({
            "ref": ref,
            "x": x,
            "y": y,
            "rot": rot,
            "start": fp_paren_start,
            "end": end,
            "block": block,
        })

    return footprints


def move_component(block: str, new_x: float, new_y: float) -> str:
    """Move a footprint block to new coordinates, preserving rotation."""
    def replace_at(m):
        rot = m.group(3)
        if rot:
            return f"(at {new_x} {new_y} {rot})"
        return f"(at {new_x} {new_y})"

    # Only replace the first (at ...) which is the footprint position
    return re.sub(
        r"\(at ([\d.-]+) ([\d.-]+)(?:\s+([\d.-]+))?\)",
        replace_at,
        block,
        count=1,
    )


def update_board_outline(content: str, new_width: float, new_height: float,
                         orig_left: float, orig_top: float) -> str:
    """Replace the Edge.Cuts rectangle with a new size, anchored at top-left."""
    new_right = orig_left + new_width
    new_bottom = orig_top + new_height

    # Remove existing Edge.Cuts lines
    content = re.sub(
        r"\n\t\(gr_line\n\t\t\(start [\d.]+ [\d.]+\)\n\t\t\(end [\d.]+ [\d.]+\)"
        r"\n\t\t\(stroke\n\t\t\t\(width [\d.]+\)\n\t\t\t\(type \w+\)\n\t\t\)"
        r'\n\t\t\(layer "Edge\.Cuts"\)'
        r"\n\t\t\(uuid \"[^\"]+\"\)\n\t\)",
        "",
        content,
    )

    # Insert new Edge.Cuts rectangle before (zone or (group or (embedded_fonts
    outline = f"""
\t(gr_line
\t\t(start {orig_left} {orig_top})
\t\t(end {new_right} {orig_top})
\t\t(stroke
\t\t\t(width 0.15)
\t\t\t(type default)
\t\t)
\t\t(layer "Edge.Cuts")
\t\t(uuid "e0000001-0000-0000-0000-000000000001")
\t)
\t(gr_line
\t\t(start {new_right} {orig_top})
\t\t(end {new_right} {new_bottom})
\t\t(stroke
\t\t\t(width 0.15)
\t\t\t(type default)
\t\t)
\t\t(layer "Edge.Cuts")
\t\t(uuid "e0000002-0000-0000-0000-000000000002")
\t)
\t(gr_line
\t\t(start {new_right} {new_bottom})
\t\t(end {orig_left} {new_bottom})
\t\t(stroke
\t\t\t(width 0.15)
\t\t\t(type default)
\t\t)
\t\t(layer "Edge.Cuts")
\t\t(uuid "e0000003-0000-0000-0000-000000000003")
\t)
\t(gr_line
\t\t(start {orig_left} {new_bottom})
\t\t(end {orig_left} {orig_top})
\t\t(stroke
\t\t\t(width 0.15)
\t\t\t(type default)
\t\t)
\t\t(layer "Edge.Cuts")
\t\t(uuid "e0000004-0000-0000-0000-000000000004")
\t)"""

    # Find insertion point: before first (zone, (group, or (embedded_fonts
    for marker in ["\n\t(zone", "\n\t(group", "\n\t(embedded_fonts"]:
        idx = content.find(marker)
        if idx >= 0:
            content = content[:idx] + outline + content[idx:]
            break

    return content


def _make_dielectric(name: str, dtype: str, thickness: float) -> str:
    return (
        f'\t\t\t(layer "{name}"\n'
        f'\t\t\t\t(type "{dtype}")\n'
        f'\t\t\t\t(thickness {thickness})\n'
        '\t\t\t\t(material "FR4")\n'
        '\t\t\t\t(epsilon_r 4.5)\n'
        '\t\t\t\t(loss_tangent 0.02)\n'
        '\t\t\t)'
    )


def _make_copper(name: str, thickness: float = 0.035) -> str:
    return (
        f'\t\t\t(layer "{name}"\n'
        '\t\t\t\t(type "copper")\n'
        f'\t\t\t\t(thickness {thickness})\n'
        '\t\t\t)'
    )


def _build_stackup_layers(num_layers: int) -> str:
    """Build the inner stackup layers (between F.Cu and B.Cu)."""
    if num_layers == 2:
        return _make_dielectric("dielectric 1", "core", 1.51)
    elif num_layers == 4:
        # F.Cu / prepreg / In1.Cu / core / In2.Cu / prepreg / B.Cu
        return "\n".join([
            _make_dielectric("dielectric 1", "prepreg", 0.2),
            _make_copper("In1.Cu"),
            _make_dielectric("dielectric 2", "core", 1.065),
            _make_copper("In2.Cu"),
            _make_dielectric("dielectric 3", "prepreg", 0.2),
        ])
    elif num_layers == 6:
        # F.Cu / prepreg / In1.Cu / prepreg / In2.Cu / core / In3.Cu / prepreg / In4.Cu / prepreg / B.Cu
        return "\n".join([
            _make_dielectric("dielectric 1", "prepreg", 0.13),
            _make_copper("In1.Cu"),
            _make_dielectric("dielectric 2", "prepreg", 0.13),
            _make_copper("In2.Cu"),
            _make_dielectric("dielectric 3", "core", 0.8),
            _make_copper("In3.Cu"),
            _make_dielectric("dielectric 4", "prepreg", 0.13),
            _make_copper("In4.Cu"),
            _make_dielectric("dielectric 5", "prepreg", 0.13),
        ])
    else:
        raise ValueError(f"Unsupported layer count: {num_layers}")


def update_stackup(content: str, num_layers: int) -> str:
    """Replace the stackup between F.Cu and B.Cu with the correct layer count."""
    # Match everything between F.Cu copper layer and B.Cu copper layer in stackup
    pattern = re.compile(
        r'(\t\t\t\(layer "F\.Cu"\n\t\t\t\t\(type "copper"\)\n\t\t\t\t\(thickness [\d.]+\)\n\t\t\t\)\n)'
        r'(.*?)'
        r'(\t\t\t\(layer "B\.Cu")',
        re.DOTALL,
    )
    m = pattern.search(content)
    if not m:
        print("  WARNING: Could not find F.Cu/B.Cu stackup markers")
        return content

    new_inner = _build_stackup_layers(num_layers)
    content = content[:m.end(1)] + new_inner + "\n" + content[m.start(3):]

    # Update the layer table at the top to include/exclude inner layers
    # First remove any existing inner layer definitions
    content = re.sub(r'\n\t\t\(\d+ "In\d+\.Cu" signal\)', '', content)

    # Add inner layer definitions after B.Cu line in layer table
    if num_layers >= 4:
        inner_layer_defs = ""
        layer_numbers = {4: [(4, "In1.Cu"), (6, "In2.Cu")],
                         6: [(2, "In1.Cu"), (4, "In2.Cu"), (6, "In3.Cu"), (8, "In4.Cu")]}
        for num, name in layer_numbers[num_layers]:
            inner_layer_defs += f'\n\t\t({num} "{name}" signal)'

        # Insert after F.Cu line
        fcu_pattern = r'(\t\t\(0 "F\.Cu" signal\))'
        content = re.sub(fcu_pattern, r'\1' + inner_layer_defs, content)

    print(f"  Updated stackup to {num_layers}-layer")
    return content


def main():
    args = parse_args()

    board_width = args.board_width or ORIG_WIDTH
    board_height = args.board_height or ORIG_HEIGHT
    num_layers = args.layers
    OUTPUT_DIR = Path(__file__).parent / args.output_dir if args.output_dir else DEFAULT_OUTPUT_DIR

    print(f"=== Quilter Upload Preparation ===")
    print(f"Target board size: {board_width} x {board_height} mm")
    print(f"Copper layers: {num_layers}")
    print()

    # Create output directory
    OUTPUT_DIR.mkdir(exist_ok=True)

    # Copy project files
    for ext in [".kicad_pro", ".kicad_sch", ".kicad_pcb", ".kicad_prl"]:
        src = PROJECT_DIR / f"default{ext}"
        if src.exists():
            shutil.copy2(src, OUTPUT_DIR / f"default{ext}")
            print(f"  Copied {src.name}")

    # Copy fp-lib-table if present
    fp_lib = PROJECT_DIR / "fp-lib-table"
    if fp_lib.exists():
        shutil.copy2(fp_lib, OUTPUT_DIR / "fp-lib-table")
        print("  Copied fp-lib-table")

    print()

    # Process the PCB file
    pcb_path = OUTPUT_DIR / "default.kicad_pcb"
    content = read_pcb(pcb_path)
    original_len = len(content)

    # Step 1: Remove segments (traces) and vias
    print("Step 1: Removing traces and vias...")
    content = remove_segments_vias(content)
    print(f"  Removed {original_len - len(content)} chars of trace/via data")

    # Step 2: Remove zones (copper pours)
    print("Step 2: Removing copper zones...")
    before = len(content)
    content = remove_zones(content)
    content = remove_filled_zones(content)
    print(f"  Removed {before - len(content)} chars of zone data")

    # Step 3: Update stackup
    print(f"Step 3: Updating stackup for {num_layers}-layer board...")
    content = update_stackup(content, num_layers)

    # Step 4: Update board outline if resizing
    if args.board_width or args.board_height:
        print(f"Step 4: Resizing board outline to {board_width} x {board_height} mm...")
        content = update_board_outline(content, board_width, board_height,
                                       ORIG_LEFT, ORIG_TOP)
    else:
        print("Step 4: Keeping original board outline (60 x 48 mm)")

    # Step 5: Move non-fixed components outside the board
    print("Step 5: Moving non-fixed components outside board outline...")
    footprints = extract_footprints(content)

    # Staging area: to the right of the board, spaced vertically
    staging_x = ORIG_LEFT + board_width + 20  # 20mm to the right of the board
    staging_y_start = ORIG_TOP
    staging_y_step = 5  # 5mm spacing between components

    move_all = args.move_all
    moved_count = 0
    fixed_count = 0

    # Process footprints in reverse order (to preserve string indices)
    for i, fp in enumerate(sorted(footprints, key=lambda f: f["start"], reverse=True)):
        ref = fp["ref"]
        if not move_all and ref in FIXED_REFS:
            fixed_count += 1
            print(f"    FIXED:  {ref:8s} at ({fp['x']:.1f}, {fp['y']:.1f})")
            continue

        # Move to staging area
        new_y = staging_y_start + moved_count * staging_y_step
        new_block = move_component(fp["block"], staging_x, new_y)
        content = content[:fp["start"]] + new_block + content[fp["end"] + 1:]
        moved_count += 1

    print(f"\n  Fixed components (stay in place): {fixed_count}")
    print(f"  Moved components (Quilter will place): {moved_count}")
    print(f"  Total components: {len(footprints)}")

    # Step 6: Clean up any remaining filled polygon data
    print("\nStep 6: Final cleanup...")
    # Remove any stray filled_polygon blocks
    content = re.sub(r"\n\t\(filled_polygon\b.*?\n\t\)", "", content, flags=re.DOTALL)

    # Write output
    write_pcb(pcb_path, content)

    # Summary
    print(f"\n=== Done! ===")
    print(f"Output directory: {OUTPUT_DIR}")
    print(f"Files ready for Quilter upload:")
    for f in sorted(OUTPUT_DIR.iterdir()):
        size_kb = f.stat().st_size / 1024
        print(f"  {f.name:30s} ({size_kb:.1f} KB)")
    print()
    print("Next steps:")
    print("  1. Go to https://app.quilter.ai and sign up (free tier)")
    print("  2. Upload all files from the quilter_upload/ directory")
    print("  3. In Constraints Manager, verify:")
    print("     - 4-layer stackup")
    print("     - GND plane on In1.Cu")
    print("     - Net classes and clearances")
    print("  4. Submit the job and wait for results")
    print("  5. Download the routed KiCad files")
    print()
    print("Tip: To let Quilter minimize board size, use:")
    print("  python prepare_for_quilter.py --board-width 45 --board-height 35 --move-all")
    print("  --move-all lets Quilter place connectors too for optimal layout.")


if __name__ == "__main__":
    main()
