# %%
# Open this file in VS Code, then click "Run Cell" (requires Jupyter extension)
# Make sure OCP CAD Viewer is open: Ctrl+Shift+P -> "OCP CAD Viewer: Open Viewer"

from build123d import *
from ocp_vscode import show
from ocp_vscode.comms import set_port

set_port(3939)

# %% Load and display enclosure with PCB assembly

base = import_step("enclosure_base.step")
lid = import_step("enclosure_lid.step")
pcb = import_step("pcb_quilter.step")

# KiCad board center in STEP coords: (130, -102)
# Enclosure PCB center: (0, -0.5), Z on standoffs: 12.5
pcb_positioned = Pos(-130, 101.5, 12.5) * pcb

# Position lid above base
lid_up = Pos(0, 0, 24) * lid

show(base, pcb_positioned, lid_up,
     names=["Base", "PCB Assembly", "Lid"],
     colors=["dimgray", "green", "silver"],
     alphas=[0.7, 1.0, 0.5])
