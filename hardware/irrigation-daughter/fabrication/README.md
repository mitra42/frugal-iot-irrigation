# Frugal-IoT Irrigation Daughter V0.1 — JLCPCB order files (21 Nov 2026, for review — not yet ordered)

Board: 100 × 42 mm, 2 layers, 1.6 mm FR-4, 1 oz copper, 4 × M3 corner holes. Min track 0.25 mm, min clearance
0.2 mm, min drill 0.3 mm — all JLCPCB standard. Valve copper is 1–2 mm on 1 oz, as the irrigation board.

| File | Upload where |
|---|---|
| `gerbers.zip` | PCB order — "Add gerber file" |
| `BOM_JLCPCB.csv` | PCB Assembly — BOM (columns: Comment, Designator, Footprint, LCSC Part #) |
| `CPL_JLCPCB.csv` | PCB Assembly — CPL / pick-and-place (Designator, Mid X, Mid Y, Layer, Rotation) |

61 placed parts, all with LCSC numbers. To leave valve channels 5–8 off, delete their rows (Q5–Q8, R11–R18,
D11–D18, J8–J11) from both files. R19/R20 are the 4.7k I2C pull-ups (DECISIONS D12): fitted, because an S2 Mini
host has none; to leave them off for a sensor or LoRa host, delete them likewise - no need, though, as both fitted
is fine.

**Before paying, check part rotations in JLCPCB's assembly preview.** KiCad and JLCPCB disagree on the zero
rotation of some packages (commonly SOT-23, TSSOP, the SMA diodes and the terminals); fix any that are turned,
or tick "Confirm parts placement" (about $0.45).

Through-hole parts (J1, J2, J3, J4–J11) are hand-soldered by JLCPCB (manual-assembly fee) — or untick them and
solder yourself. The eight valve terminals butt against each other in one row (KF128 blocks are made to).

Regenerate: `claude-tools/layout/fab.sh` on the Mac, then `python3 claude-tools/layout/jlc_files.py`.
