# claude-tools — how Claude regenerates and changes this design

Reviewers can ignore this folder. Everything runs on Mitra's Mac with KiCad 10's bundled Python
(`/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3`).
Long steps run detached and drop a `out/<name>.done` sentinel. `out/` folders are scratch — safe to delete.
Method and lessons: the kicad skill (`../../kicad-skill/SKILL.md`).

## Schematic — `schematic/`
The schematic is **generated**: edit `circuit.py` (parts, values, LCSC numbers, nets) and the block layout in
`dblk1–4.py`, never the .kicad_sch by hand.
1. `buildlib.py` — project symbol library (module, FS8205A, rail symbols).
2. `run_draw_bg.sh` → `draw.py` — writes the sheet, then verifies netlist = spec, ERC and text collisions
   (`out/draw.log` must end `VERIFY OK`).
3. `run_kicad.sh` — netlist, ERC, `../../SCHEMATIC.pdf`, `../../BOM.csv`.
4. Costs: `jlc_dump.sh` (live JLCPCB prices) then `python3 cost_estimate.py > ../../COST-ESTIMATE.txt`.
   `jlc_query.py` / `jlc_basic.py` look up parts and Basic/preferred alternatives.

## PCB — `layout/`
**Small changes after a schematic edit: use KiCad's "Update PCB from Schematic" in the GUI, re-route the
affected nets, then run `fab.sh`.** The scripts below rebuild the board from scratch and would discard all
routing — use them only for a full re-layout.
- Fabrication (safe, read-only on the board): `fab.sh` (DRC with schematic parity, Gerbers, drill, placement,
  BOM, render; raw outputs go to `out/fab/`, which is scratch) → `python3 jlc_files.py` (JLCPCB BOM/CPL +
  gerbers.zip in `../../fabrication/`).
  `renders.sh` makes the 3D/copper views used for `PCB-LAYOUT.pdf`.
- Full re-layout (valve board, D79–D86):
  1. `pipeline.sh [--sch] 62` — fpmeasure → `place.py 62` → build_pcb → netclasses → DRC. `place.py` holds the
     anchors (valve columns, J2/F1/D2, buck, module, terminals) and fails on any courtyard overlap; `look.sh`
     renders the board to `out/look.png` (`preview.py` needs matplotlib).
  2. `preroute.sh` — build_pcb, net classes, `valve_route.py` (the 1–2 mm valve and +12V copper, D82),
     `prep_route.py` (GND fan-out, DSN), `copper_snap.py save`, `dsn_prep.py`, `route/dsn_classes.py`.
  3. Routing, local: `route/loop_local.sh out/board_r.dsn r 8 25` (needs `~/tools/freerouting/freerouting-2.1.0.jar`; `FR=<dir>` overrides; compiles `Route.java` itself)
     (Java 21+). Rounds restart from the last result (`route/merge.py`).
  4. `real_unrouted.sh <x.ses>` — import, restore the fixed copper the .ses drops, DRC, list what is still open.
     Freerouting's own count is not reliable; use this. Leaves the imported board in place.
  5. `post_route.sh --no-import` — pours, stitching, island vias, stub removal, refdes placement, DRC. Then
     `addtext.py "Frugal-IoT Irrigation V0.2"`, `fab.sh`, `jlc_files.py`, `renders.sh`.
- Changing a routed board without re-laying it out (power parts, D87–D90): `patch_power.py` (swap and remove
  parts, place test pads, delete the copper that no longer fits) → `route_patch.sh prep` (snapshot the copper, DSN
  without the pours via `nozone_dsn.py`) → `cd out && ../route/loop_local.sh board_r.dsn p 4 25` →
  `route_patch.sh import out/p_N.ses` (import, restore the snapshot, pour, DRC). `gnd_via.py` adds a GND via to a
  pad left in a cut-off pocket of pour; `islands2.py` finds those.
- One-offs: `mkfp_module.py` (project footprint for the -1U module), `mkfp_kf128.py` (KF128 terminal footprint,
  D79), `netclasses.py` (net classes and rules into the .kicad_pro).

## notes/
`original-handoff-from-chat.md` — the original request from the 14 Oct chat session.
