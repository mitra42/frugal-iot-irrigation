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
- Full re-layout: `pipeline.sh [--sch] 80` (fpmeasure → place → build_pcb → netclasses → DRC);
  `preview.py` draws the placement by block. Placement anchors and block regions are in `place.py`;
  `blocks.json` maps refs to schematic blocks.
- Routing: `prep_route.py` (GND fan-out + exposed-pad vias, DSN) → `dsn_prep.py` → `route/dsn_classes.py`
  → `route/escape.py` (pad-escape check) → Freerouting 2.1.0 via `route/Route.java` (Java 21; download
  freerouting-2.1.0.jar from github.com/freerouting/freerouting releases) → `route/check_ses.py`
  → `post_route.sh` (import, pours, stitching, island vias, stub removal, GND rescue, refdes placement, DRC).
- One-offs: `mkfp_module.py` (project footprint for the -1U module), `addtext.py` (board title),
  `netclasses.py` (net classes and rules into the .kicad_pro).

## notes/
`original-handoff-from-chat.md` — the original request from the 14 Oct chat session.
