# Frugal-IoT Irrigation V0.1 — JLCPCB order files (15 Oct 2026)

Board: 100 × 80 mm, 2 layers, 1.6 mm FR-4, 1 oz copper, 4 × M3 holes. Min track 0.25 mm (0.15 mm absolute
minimum in rules), min clearance 0.15 mm (USB pair) / 0.2 mm elsewhere, min drill 0.3 mm — all JLCPCB standard.

| File | Upload where |
|---|---|
| `gerbers.zip` | PCB order — "Add gerber file" |
| `BOM_JLCPCB.csv` | PCB Assembly — BOM (columns: Comment, Designator, Footprint, LCSC Part #) |
| `CPL_JLCPCB.csv` | PCB Assembly — CPL / pick-and-place (Designator, Mid X, Mid Y, Layer, Rotation) |

105 placed parts, 50 part numbers, all with LCSC numbers; DNP parts (J3, J5, J10, R5, R6, R11, R28–R31) and the
three solder jumpers are excluded from both files.

**Before paying, check part rotations in JLCPCB's assembly preview.** KiCad and JLCPCB disagree on the zero
rotation of some packages (commonly SOT-23, SOIC/TSSOP, the USB-C and the relays/terminals); the preview shows
each part on its footprint — fix any that are turned, or tick JLCPCB's "Confirm parts placement" option
(about $0.45) so their engineer checks it. The ESP32 module (U6) uses project footprint
irrigation:ESP32-C3-C6-MINI-1U; check its pin-1 dot matches pad 1.

Assembly options to choose: Economic, top side only; through-hole parts (K1–K4, J2, J4, J6–J9, J11–J15) are
hand-soldered by JLCPCB (manual-assembly fee) — or untick them and solder yourself (saves ~$34 per 10, D43).

Regenerate: `claude-tools/layout/fab.sh` on the Mac (DRC + Gerbers + drill + placement + BOM), then
`python3 claude-tools/layout/jlc_files.py`.
