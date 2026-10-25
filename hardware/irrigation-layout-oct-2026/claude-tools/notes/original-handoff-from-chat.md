# Generic ESP32 I/O board — handoff brief (14 Oct 2026)

**Status:** design basis agreed in a Chat session. **No KiCad files exist yet.** That session
could not reach KiCad (the Mac osascript connector hung), so everything below is decisions,
not work done. Pick up here in a session that has KiCad 10 / `kicad-cli` / `pcbnew` on the Mac.

**This phase:** schematic only. ERC clean, BOM with LCSC part numbers for JLCPCB PCBA, then
stop for review (PDF + BOM CSV, as in the Frugal IoT v0.1 flow). No layout yet.
Use a **new project folder**, separate from `frugal-layout`. This board is **not** bound by the
Frugal IoT through-hole-only rule: it is PCBA'd by JLCPCB, so SMD is fine. Relays and screw
terminals stay through-hole.

## Decisions stated by Mitra
- Clean sheet, new board. 2 layers assumed. No size target yet.
- MCU: ESP32-C-series, bare module on the board (not a socketed dev board). u.FL antenna.
- Native USB for flashing (no bridge chip). Also 12 V external supply option.
- Cell: single LiPo, 4.2 V. Capacity unknown, 18650 is the maximum. Wants long cell life.
- No TP4056 *module*; power circuit based on the **LOLIN C3 Pico** (see below).
- 12 V comes from an external battery with its own charge controller. When present it charges
  the cell via a 12 V → 5 V buck. Solar is assumed to arrive as 5 V via USB. Max 12 V input 15 V.
- 4 relays on board, **COM/NO/NC brought out for each** (12 terminals). They switch external
  loads, **not** the board's own rail, possibly ground-side. Board carries no load current.
  Contacts isolated from board rails. Fuse on the contact path not needed (externals fused).
- Current limit: Mitra wants "close to edge, decent conductors" and to be told the limit.
  IPC-2221 at 1 oz outer, 10 C rise: 3 A ~ 1.4 mm, 5 A ~ 2.8 mm, 10 A ~ 7 mm trace.
  Advertise **5 A per channel** at 1 oz with wide pours; 10 A needs 2 oz. Check the chosen
  relay and terminal ratings. 12 V DC only, not mains.
- Relay coils: pick what suits. Proposal: **12 V coils** (SRD-12VDC type) via ULN2003.
- Overnight scenario: external 12 V sags while the cell keeps the device alive; firmware stops
  switching 12 V loads; power returns in the morning. So **sense the 12 V input** as well as
  the cell: 470k/100k divider to an ADC pin (about 2.6 V at 15 V in).
- Two switched rails, **3V3-SW and 5V-SW**. 5V-SW need only work when external power is
  present (not on battery alone, so no boost converter).
- RS485: **3.3 V transceiver**, automatic direction, not isolated.
- I2C bus on the sensor connector. **OLED on its own 4-pin I2C header** (same bus).
- Two user buttons plus on-board reset (not brought to a connector). Native USB makes the boot
  button mostly unnecessary: one user button may double as BOOT (GPIO9 strap), hold while reset.
  If GPIOs run short, drop to one or zero buttons.
- 2 extra GPIOs, each with pull-up and/or pull-down placeholder footprints.
- Usual decoupling.
- **Connectors:** 2.54 mm screw terminals for sensor wiring, each peripheral with its own
  ground, e.g. (3V3-SW, SDA, SCL, GND), (A, GND), (B, GND). **Separate wider-pitch (5.08 mm)
  connector for real power** (12 V in, relay terminals).
- Mitra can accept the optional rail-switch merge: **one GPIO** driving both rail switches
  (see GPIO budget).

## Proposed (confirm or change)
- **Module: ESP32-C6-MINI-1U** (u.FL built into the module). Pad-compatible with the
  C3-MINI footprint (53 pads), so one footprint takes either. C6-MINI-1 has 22 usable GPIOs;
  the C3 module has about 15 (unverified). Check both datasheets before assigning pins.
- **Power path (copy of the Pico topology, but with 5V_IN from USB or the 12 V buck, diode-ORed):**
  charger IC from 5V_IN to VBAT; a P-FET whose gate is tied to 5V_IN (with 100k pull-down)
  connects VBAT to the LDO input only when 5V_IN is absent; a Schottky feeds 5V_IN to the LDO
  input otherwise. The charger only charges and never carries the load.
- LDO: bigger than the Pico's ME6211 (500 mA, marginal with Wi-Fi + 3V3-SW loads). Options:
  AP2112K-3.3 (600 mA, ~55 uA Iq) or XC6220B331 (1 A, ~8 uA Iq, pricier).
- Battery sense: 1 Mohm / 1 Mohm divider plus 100 nF into **GPIO3** (the Pico uses 100k/100k,
  which draws ~21 uA continuously).
- Battery protection (DW01-type + dual MOSFET) so unprotected cells are safe.
- Charge-current selection by a solder jumper between two PROG resistors (about 250 mA and
  500 mA) since the cell size is unknown.
- 12 V input: TVS and reverse-polarity protection ahead of the buck.
- Rail switches: P-FET high-side. One small N-FET per rail pulls the P-FET gate low, driven by
  one GPIO (high = on, pull-down default off), 3V3-SW gate pull-up to 3V3, 5V-SW gate pull-up
  to 5V. I2C pull-ups on 3V3-SW.

## Open questions
1. **Charger:** TP4054 (SOT-23-5, as on the Pico, **no NTC pin**) or TP4056 chip (SOP-8,
   **has a TEMP pin** for a cell thermistor)? Recommendation: TP4056 chip for outdoor cell
   life; the rest of the circuit is the same.
2. Cell capacity (affects the charge-current default).
3. Relay terminal pitch and part (5.08 mm assumed); confirm part ratings.

## GPIO budget (C6, 22 usable)
I2C 2, UART 2, relays 4, buttons 2, rail switches 1, battery sense 1, 12 V sense 1, spare 2
= **15**, plus the USB pair. Fits the C6 with headroom. A C3 module (about 15) would only fit
with zero buttons and no spares, or with an I2C expander for the relays. Not recommended.

## Reference: LOLIN C3 Pico power section (from Mitra's screenshot of the official schematic)
- U4 TP4054: VCC from VBUS, BAT to VBAT, PROG 2k to GND, CHRG pin to red LED via 5.1k from
  VBUS (solder jumper JP2). PH2.0 battery connector on VBAT.
- Battery sense: R7/R10 100k/100k from VBAT, 100 nF C9, jumper JP1 to IO3.
- Q1 CJ2301 P-FET: gate to VBUS with R8 100k to GND, one terminal on VBAT, the other on VIN.
  D1 1N5819W Schottky from VBUS to VIN. C17 10 uF on VIN.
- U2 ME6211C33 LDO: VIN, CE tied to VIN, VOUT to +3V3 with C18 10 uF and C2 100 nF.

## Rough cost notes (LCSC listings and forum reports, 14 Oct 2026; verify in JLC's own tool)
- C3-MINI-1-N4 about $1.29 at qty 1 (4,679 in stock on the listing seen).
- C6-MINI-1U-H4 about $4.43 at qty 1, falling to about $3.19 at 1,300+; the listing seen
  showed 0 stock, so **check JLC parts-library stock first**.
- JLC fee structure from forum posts: ~$7-8 SMT setup incl. stencil, ~$3 per unique extended
  part, a separate through-hole assembly setup (~$3.50) with higher per-board THT cost.
  Prefer basic parts where it does not hurt the design.

## Lessons from the Frugal IoT v0.1 sessions (in the project files)
- Register custom footprints and symbols in a **project library** (`fp-lib-table`,
  `sym-lib-table` using `${KIPRJMOD}`) before syncing schematic to PCB.
- Run DRC with **`--schematic-parity`**; without the flag the parity result is empty, not
  passed.
- If Freerouting is used later, its own completion report is unreliable; verify with an
  independent connectivity check and KiCad DRC.
- Snapshot the project before changes, keep it closed in the GUI while scripts run, and stop at
  a checkpoint (schematic PDF + BOM CSV) before doing the next phase.
- Preferred review artefacts: `SCHEMATIC-for-review.pdf` and `BOM-for-review.csv`.

## Suggested first prompt for the new session
"Read generic-esp32-board-handoff.md and the Frugal IoT v0.1 project files, create a new KiCad
project folder, and build the schematic for the generic ESP32 board. Stop at ERC clean with a
review PDF and BOM CSV. Ask me the open questions first."
