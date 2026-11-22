# Frugal-IoT Irrigation V0.2 — JLCPCB order files (21 Nov 2026, for review — not yet ordered)

Board: 100 × 62 mm, 2 layers, 1.6 mm FR-4, 1 oz copper, 4 × M3 holes. Min track 0.25 mm (0.15 mm absolute
minimum in rules), min clearance 0.15 mm (USB pair) / 0.2 mm elsewhere, min drill 0.3 mm — all JLCPCB standard.
Valve copper is 1–2 mm on 1 oz; ask for 2 oz only if the valves draw more than D82 assumes.

| File | Upload where |
|---|---|
| `gerbers.zip` | PCB order — "Add gerber file" |
| `BOM_JLCPCB.csv` | PCB Assembly — BOM (columns: Comment, Designator, Footprint, LCSC Part #) |
| `CPL_JLCPCB.csv` | PCB Assembly — CPL / pick-and-place (Designator, Mid X, Mid Y, Layer, Rotation) |

135 placed parts, all with LCSC numbers; the nine test pads TP1–TP9 are bare copper, not parts (D89); DNP parts (J3, J5, R5, R6, R11, R28–R31) and the three solder jumpers
are excluded from both files. To leave valve channels 5–8 off (D75), delete their rows (Q12–Q15, R47–R54,
D18–D25, J15–J18) from both files.

**Before paying, check part rotations in JLCPCB's assembly preview.** KiCad and JLCPCB disagree on the zero
rotation of some packages (commonly SOT-23, SOIC/TSSOP, the USB-C, the SS34/SS54 diodes and the terminals); the preview shows
each part on its footprint — fix any that are turned, or tick JLCPCB's "Confirm parts placement" option
(about $0.45) so their engineer checks it. The ESP32 module (U6) uses project footprint
irrigation:ESP32-C3-C6-MINI-1U; check its pin-1 dot matches pad 1. **U4 (XB5353A, C80628)**: on the LoRa board,
which was ordered with this part, JLCPCB's model needed 180° where its other SOT-23-5 needed −90°, so expect U4
to need turning by a different amount from U5 (RT9080, TSOT-23-5).

Assembly options to choose: Economic, top side only; through-hole parts (J2, J4, J6–J10, J11–J18) are
hand-soldered by JLCPCB (manual-assembly fee) — or untick them and solder yourself (D43). The eight valve
terminals butt against each other in one row (KF128 blocks are made to, D79).

## How to order from JLCPCB, step by step

You need a JLCPCB account and the three files above. Do not trust the prices in this repository: the quote you
see on screen is the one that counts, and JLCPCB's fees change (they are listed at
https://jlcpcb.com/help/article/pcb-assembly-price).

1. **Log in first**, then go to https://cart.jlcpcb.com/quote. If you upload while logged out the board size
   may not fill in.
2. **Add gerber file**: upload `gerbers.zip` (not the individual files). Check the board size shown matches the
   one at the top of this README. Choose the quantity, 2 layers, 1.6 mm, and leave the other options at their
   defaults unless you know why you are changing them.
3. **Turn on PCB Assembly.** Choose **Economic**, **top side only** (Standard costs far more for a simple board
   because of its higher setup fee). If Economic is greyed out, the usual cause is the surface finish: Economic
   needs **HASL (lead-free is fine) or ENIG**, not the default OSP. Change the finish in the PCB options above.
4. **Decide about conformal coating, per order, because it can change step 3.** It is the same
   gerbers, BOM and CPL either way. Leave it off for development boards (they are easier to modify and rework
   uncoated); use it for boards going into the field. JLCPCB's coating service is **only available on Standard
   PCBA orders**, so asking for it means changing step 3 to Standard and paying that setup fee. Their terms,
   at https://jlcpcb.com/help/article/conformal-coating-spray-service, include: you must attach images of the
   areas to coat or keep clear (with no images the whole board is coated), keep-out areas should be at least
   17 × 17 mm, and coverage is not guaranteed. Connectors, screw terminals, headers, sockets and any antenna
   connector must not be coated, so mark those. If in doubt, order uncoated and coat it yourself after testing.
5. **Upload the BOM and CPL**, then press *Process BOM & CPL*.
6. **Check the parts list.** Every line should be matched to its LCSC number and have enough stock.
   - Anything marked *Extended* costs a one-off feeder fee per different part number, so ten identical
     terminals cost one fee, not ten.
   - A part with low or no stock stops the order: pick the substitute JLCPCB suggests only if you have checked
     its datasheet, and tell the maintainer.
   - Parts you do not want fitted must be removed from both CSV files before uploading (see the paragraph above
     for this board). Unticking them on the website also works but is easier to get wrong.
7. **Check every part's placement in the assembly preview.** This is where mistakes get caught. JLCPCB's part
   models are drawn at different zero angles from KiCad's, so some parts show turned or shifted. For each part
   type compare the preview with `PCB-LAYOUT.pdf`, using the pink dot, which marks pin 1:
   - **Transistors, ICs and modules:** pin 1 must match the layout.
   - **Diodes** (the stripe is the cathode) and **LEDs** (check which side the cathode is on).
   - **Terminal blocks and headers:** every block must sit over its own pads, not offset by a pin or two, and
     the wire entry must face the board edge.
   - Click a part's row in the list on the right to zoom the viewer to it; at the default zoom the small parts
     are unreadable. Switch to 2D to compare against the pads.
   - Fix a turned part with the rotate control in the preview, and write down what you changed (part,
     degrees). Whoever maintains the repository should put those corrections into `jlc_files.py` so the next
     order is right first time.
   - If anything is still doubtful, tick **Confirm parts placement** (a small fee). JLCPCB staff then show you
     their placement and wait for your OK before building. For a first order, tick it anyway, and also tick
     **Do not confirm automatically**, otherwise they may build after a timeout without your OK.
8. **Through-hole parts** are soldered by hand by JLCPCB for a small per-joint fee, or you can untick them and
   solder them yourself.
9. **Get the quote, pick shipping, pay.** Check the totals against `COST-ESTIMATE.txt` (treat it as a ceiling:
   the 22 Nov 2026 irrigation daughter board came in well under its estimate, partly from a new-customer PCB
   discount), allowing for shipping, tax and import duty (not included there). If the total is much higher
   than expected, stop and find out why before paying; the usual causes are extra Extended parts or a part
   added by mistake.
10. **Afterwards**, add the order number and any part-rotation corrections to `DECISIONS.md`, and commit them.

Regenerate: `claude-tools/layout/fab.sh` on the Mac (DRC + Gerbers + drill + placement + BOM), then
`python3 claude-tools/layout/jlc_files.py`.
