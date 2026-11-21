# Frugal-IoT Irrigation V0.2 — JLCPCB order files (21 Nov 2026, for review — not yet ordered)

Board: 100 × 62 mm, 2 layers, 1.6 mm FR-4, 1 oz copper, 4 × M3 holes. Min track 0.25 mm (0.15 mm absolute
minimum in rules), min clearance 0.15 mm (USB pair) / 0.2 mm elsewhere, min drill 0.3 mm — all JLCPCB standard.
Valve copper is 1–2 mm on 1 oz; ask for 2 oz only if the valves draw more than D82 assumes.

| File | Upload where |
|---|---|
| `gerbers.zip` | PCB order — "Add gerber file" |
| `BOM_JLCPCB.csv` | PCB Assembly — BOM (columns: Comment, Designator, Footprint, LCSC Part #) |
| `CPL_JLCPCB.csv` | PCB Assembly — CPL / pick-and-place (Designator, Mid X, Mid Y, Layer, Rotation) |

138 placed parts, all with LCSC numbers; DNP parts (J3, J5, R5, R6, R11, R28–R31) and the three solder jumpers
are excluded from both files. To leave valve channels 5–8 off (D75), delete their rows (Q12–Q15, R47–R54,
D18–D25, J15–J18) from both files.

**Before paying, check part rotations in JLCPCB's assembly preview.** KiCad and JLCPCB disagree on the zero
rotation of some packages (commonly SOT-23, SOIC/TSSOP, the USB-C, the SS34/SS54 diodes and the terminals); the preview shows
each part on its footprint — fix any that are turned, or tick JLCPCB's "Confirm parts placement" option
(about $0.45) so their engineer checks it. The ESP32 module (U6) uses project footprint
irrigation:ESP32-C3-C6-MINI-1U; check its pin-1 dot matches pad 1.

Assembly options to choose: Economic, top side only; through-hole parts (J2, J4, J6–J10, J11–J18) are
hand-soldered by JLCPCB (manual-assembly fee) — or untick them and solder yourself (D43). The eight valve
terminals butt against each other in one row (KF128 blocks are made to, D79).

Regenerate: `claude-tools/layout/fab.sh` on the Mac (DRC + Gerbers + drill + placement + BOM), then
`python3 claude-tools/layout/jlc_files.py`.
