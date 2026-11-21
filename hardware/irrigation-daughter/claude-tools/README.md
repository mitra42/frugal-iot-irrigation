# claude-tools — how Claude regenerates and changes this design

Reviewers can ignore this folder. Copied from `../irrigation-layout-oct-2026/claude-tools/` and cut down; the
method is the same, and so are most scripts. Everything runs on Mitra's Mac with KiCad 10's bundled Python
(`/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3`).
`out/` folders are scratch (gitignored).

## Schematic — `schematic/`
Generated: edit `circuit.py` (parts, values, LCSC numbers, nets) and `dblk.py` (where the three blocks are drawn),
never the .kicad_sch by hand. References are numbered in `circuit.py`'s order.
1. `buildlib.py` — project symbol library (only the +3V3_SW rail symbol).
2. `run_draw.sh` → `draw.py` — writes the sheet, verifies netlist = spec, ERC, text collisions
   (`out/draw.log` must end `VERIFY OK`). `crops.sh` renders each block for a look.
3. `run_kicad.sh` — netlist, ERC, `../../SCHEMATIC.pdf`, `../../BOM.csv`.
4. Costs: `jlc_dump.sh` (live JLCPCB prices) then `python3 cost_estimate.py > ../../COST-ESTIMATE.txt`.

## PCB — `layout/`
Full layout, in order (each step also rebuilds the board from scratch, so it discards routing):
1. `pipeline.sh [--sch] 42` — fpmeasure → `place.py 42` (anchors: the irrigation board's valve band, J2/F1/D1,
   J1, J3, U1; fails on a courtyard overlap or a part on a mounting hole) → build_pcb → netclasses → DRC.
   `look.sh` renders the board to `out/look.png`.
2. `preroute.sh` — build_pcb, net classes, `valve_route.py` (the 1–2 mm valve and +12V copper),
   `prep_route.py` (GND fan-out, DSN), `copper_snap.py save`, `dsn_prep.py`, `route/dsn_classes.py`.
3. `cd out && ../route/loop_local.sh board_r.dsn r 3 25` — Freerouting from `~/tools/freerouting/`.
4. `real_unrouted.sh out/r_N.ses` — import, restore the fixed copper, DRC, list what is open (Freerouting's own
   count is not reliable). Two rounds left nothing open.
5. `post_route.sh --no-import` — pours, stitching, islands, stubs, reference placement, DRC. Then
   `pinlabels.py` (connector pin names) and `addtext.py "Frugal-IoT Irrigation Daughter V0.1"`.
6. `fab.sh` → `python3 jlc_files.py` (`../../fabrication/`), `renders.sh` (views for `PCB-LAYOUT.pdf`, joined
   with macOS's `Combine PDF Pages.action/Contents/MacOS/join`).

For a small change after a schematic edit, KiCad's "Update PCB from Schematic" and re-routing by hand is less
work than step 1.
