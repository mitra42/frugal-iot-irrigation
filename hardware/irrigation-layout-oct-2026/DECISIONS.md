# Frugal-IoT Irrigation V0.1 — decision log

Key choices, why they were made, and what would reopen them. Newest at the bottom of each
section. Status: **Decided** (go ahead), **Proposed** (default unless changed), **Open**.

Status (15 Oct 2026): schematic, layout and JLCPCB fabrication files complete; out for review.
Status (21 Nov 2026, branch `uln2803`): relays replaced by eight MOSFET valve outputs (D67–D78) and the board
re-laid out at 100 × 62 mm (D79–D86); routed, DRC clean, JLCPCB files regenerated; for review, not ordered.

Paths in older entries: `tools/` is now `claude-tools/schematic/`, `layout/` is now `claude-tools/layout/`,
`SCHEMATIC-for-review.pdf` → `SCHEMATIC.pdf`, `ROUTED-for-review.pdf` → `PCB-LAYOUT.pdf`,
`BOM-for-review.csv` → `BOM.csv`, `COST-ESTIMATE-10.txt` → `COST-ESTIMATE.txt`. The original request is
`claude-tools/notes/original-handoff-from-chat.md`; working checkpoints were removed (the Claude project keeps a copy).

## Carried over from the 14 Oct Chat session (see claude-tools/notes/original-handoff-from-chat.md)

| # | Decision | Status | Why / revisit if |
|---|---|---|---|
| D1 | New board, 2 layers, PCBA at JLCPCB, SMD allowed; relays and screw terminals through-hole | Decided | |
| D2 | Bare ESP32 module, u.FL antenna, native USB for flashing (no USB-UART bridge) | Decided | See D14 for module vs bare chip |
| D3 | Single LiPo cell, 18650 max; power topology copied from LOLIN C3 Pico (charger never carries load; P-FET + Schottky load sharing) | Decided | |
| D4 | 12 V external input (max 15 V) → 5 V buck, diode-ORed with USB 5 V; TVS + reverse-polarity protection | Decided | |
| D5 | 4 relays, COM/NO/NC brought out, contacts isolated from board rails, 12 V DC loads only; advertise 5 A/channel at 1 oz copper | Decided | 10 A would need 2 oz copper |
| D6 | 12 V input sensed on an ADC (470k/100k); battery sensed (1M/1M + 100 nF) | Decided | |
| D7 | Two switched rails 3V3-SW and 5V-SW, P-FET high-side, both driven by one GPIO; 5V-SW only works with external power | Decided | |
| D8 | RS485: 3.3 V, auto-direction, not isolated | Decided | |
| D9 | I2C on sensor connector + separate 4-pin OLED header | Decided | |
| D10 | 2.54 mm screw terminals for sensors (each peripheral with own GND); 5.08 mm for power and relay contacts | Decided | |

## 14 Oct 2026 (Cowork session)

| # | Decision | Status | Why / revisit if |
|---|---|---|---|
| D11 | Charger: **TP4056 chip** (SOP-8), not TP4054 | Decided | Has TEMP pin for a cell thermistor — matters outdoors |
| D12 | Charge current: solder jumper selecting **250 mA (default) / 500 mA** | Decided | Cell size unknown; revisit once cell is chosen |
| D13 | Relays: **SRD-12VDC-SL-C**, 12 V coils via ULN2003; 5.08 mm terminals | Decided | Check contact rating vs 5 A target when picking LCSC part |
| D14 | Module choice **left open: ESP32-C3-MINI-1U or ESP32-C6-MINI-1U on one footprint**. Essential functions must work on either; buttons and spare GPIOs go on C6-only pads | Decided | C6 costs ~$2–3 more per board; drop C3 support if it costs too much complexity |
| D15 | The two modules are **not fully pin-compatible**: USB is on pads 17/18 (C6) vs 26/27 (C3); only ~11 pads are GPIO on both. Each USB pad pair reaches the USB lines through its own pair of 0 Ω links (see D19) | Decided | Verify against both datasheets again before layout |
| D16 | Relays driven via **TCA9534PWR I2C expander** (pins default to inputs at reset; the ULN2003's internal input resistors then hold the relays off) rather than direct GPIOs. Frees shared pads so essentials fit both modules with a BOOT button on IO9 | Decided | Adds ~$0.90 at 10 boards (feeder fee + part) — cheaper than forcing C6. Relays now depend on I2C working |
| D17 | Use a **module, not the bare ESP32 chip** | Decided | Module brings crystal, flash, RF matching, shield and RF certification. Revisit only at volume (1000s) |

## 14 Oct 2026 — schematic build (Cowork session, continued)

| # | Decision | Status | Why / revisit if |
|---|---|---|---|
| D18 | **GPIO map** (module pad → function). Shared pads, work on both modules: 5 IO2 RS485_TX (10k pull-up = C3 strap), 6 IO3 VBAT_SENSE, 12 IO0 RS485_RX, 13 IO1 V12_SENSE, 16 I2C_SDA, 19 I2C_SCL, 20 RAIL_EN (100k pull-down), 22 IO8 STATUS_LED (10k pull-up, strap), 23 IO9 BOOT button, 30/31 UART0 to DNP debug header. C6-only: 24 BTN1, 25 BTN2, 15 GPIO_A (ADC on C6), 28 GPIO_B. Unused: 9, 10, 29, 21 | Decided | C3 pad map comes from the Espressif datasheet as read by a web summariser — **re-check against the C3-MINI-1 datasheet table 3-1 before layout**. C6 map matches KiCad's stock symbol — **Verified 14 Oct 2026 pad-by-pad against ESP32-C3-MINI-1 datasheet v2.2 and ESP32-C6-MINI-1 v1.5, table 3-1 (copies in datasheets/). C6 GPIO15 (pad 20, RAIL_EN) is a JTAG-source strap, ignored with default eFuses** |
| D19 | USB select: 0 Ω links R3/R4 (C6) fitted, R5/R6 (C3) DNP. BOM defaults to **C6-MINI-1U-H4** | Proposed | Swap links + module to build a C3 board |
| D20 | ~~I2C bus isolation with two BSS138s~~ — **superseded by D34** | Superseded | Lets relays stay controlled while sensor power is off, without back-powering sensors through their I2C pins |
| D21 | **RS485: SP3485 (3.3 V) with direction taken from TX** (DI tied low, TX drives DE/RE through a 2N7002; 680 Ω bias, 120 Ω termination on a solder jumper, SM712 TVS). Transceiver, bias and pull-ups all on 3V3_SW | Proposed | Uses basic parts, but "1" bits are driven only by the bias resistors: fine for Modbus at 9600 baud, marginal with two terminations. **THVD1406** (true auto-direction) is the better part — not used yet because its pinout could not be confirmed this session |
| D22 | RS485 terminal: 5V_SW, A, B, GND | Proposed | Change to 12 V if the sensors need it |
| D23 | 12 V sense divider **560k/100k** (2.27 V at 15 V) rather than 470k/100k | Proposed | Keeps within the C3 ADC's ~2.5 V range at 11 dB |
| D24 | Relay pinout from KiCad symbol: pin 1 COM, 3 NO, 4 NC, 2/5 coil (confirmed by KiCad's Form A/B variants). Terminal order NO-COM-NC. One red LED per relay coil | Decided | |
| D25 | 5 V buck **AP63205WU** (fixed 5 V, 3.8–32 V in), 6.8 µH, 2×22 µF out | Decided | Inductor and caps from memory of the datasheet — **verify against AP63205 datasheet** — **Superseded by D46 (datasheet says 4.7 µH)** |
| D26 | 12 V input: SS34 series diode (reverse polarity) then SMAJ15A TVS. Relay coils and buck both fed from the protected +12V | Proposed | |
| D27 | TP4056 TEMP: solder jumper to GND by default (NTC disabled); NTC header + divider resistor DNP until a cell/NTC is chosen | Proposed | |
| D28 | LiPo connector JST-PH 2-pin, pin 1 = +, pin 2 = − | Decided | JST-PH cell polarity is not standardised — check against the cells you will buy — **Superseded by D47** |
| D29 | Passives 0603; buttons 6×6 mm SMD (footprint placeholder) | Proposed | |
| D30 | TCA9534 P4–P7 to a DNP 6-pin header; INT not connected | Superseded by D75 | Firmware should drive unused P4–P7 low if the header is not fitted |

## 14 Oct 2026 — schematic redraw

| # | Decision | Status | Why / revisit if |
|---|---|---|---|
| D31 | Schematics are drawn conventionally (wires, rails top / ground bottom, left→right flow, titled blocks combined on one sheet) using the **kicad-schematic-layout** skill (Diode663, MIT) with its netlist / ERC / text checks | Decided | Mitra's standing requirement; label-per-pin sheets are unacceptable |
| D32 | Net renames for KiCad conventions (see SCHEMATIC-checkpoint.md); FS8205A drain pins marked no-connect (internal common drain) | Decided | |
| D33 | The +3V3_SW rail keeps only 1 µF + 100 nF (lint asks for ≥10 µF bulk) to limit inrush when the P-FET switches on and dips +3V3 | Proposed | Revisit with the actual sensor load; a soft-start RC on the gate would allow more bulk |

## 14 Oct 2026 — review round 1 (Mitra)

| # | Decision | Status | Why / revisit if |
|---|---|---|---|
| D34 | **No I2C isolation FETs.** One pull-up pair (R32/R33) on +3V3_SW. Firmware switches +3V3_SW on before any I2C traffic, including relay changes; the TCA9534 stays on always-on 3V3 and holds its outputs while the bus is down | Decided | Mitra: the MCU pins go to input when the rail goes off, so Q7/Q8 add nothing. Removes 2 FETs + 2 resistors |
| D35 | **SW2 = BOOT and BTN1** on IO9 (hold during reset for download mode, ordinary button afterwards). Separate BTN1 removed; pad 24 now spare | Decided | As agreed in the handoff; also makes BTN1 work on a C3 |
| D36 | FS8205A drawn as a 2-unit part, two N-MOSFET symbols back to back (drains common) | Decided | Conventional symbols, not a box |
| D37 | References renumbered after removing parts (R27 onwards, SW3/SW4, Q7) | Decided | Pre-layout, so no PCB impact |
| D38 | **Keep both 2N7002s** (Q4, Q6): one RAIL_EN switches +3V3_SW and +5V_SW together, high = on, R21 holds both off at reset | Decided | Q4 is technically avoidable (GPIO can drive the 3V3 P-FET directly) but would need a second, opposite-polarity enable for 5 V. Mitra chose the simpler firmware |

## 14 Oct 2026 — part numbers checked on JLCPCB + cost estimate

Stock and prices read from JLCPCB's parts API on 14 Oct 2026 (`tools/jlc_query.py`, `tools/jlc_dump.sh`); fees from jlcpcb.com/help/article/pcb-assembly-price (updated 9 Sep 2026). Estimate: `tools/cost_estimate.py` → `COST-ESTIMATE-10.txt`.

| # | Decision | Status | Why / revisit if |
|---|---|---|---|
| D39 | **FS8205A is SOT-23-6, C908265 (Fuxinsemi)**, not TSSOP-8 (pre-order only at JLCPCB). Pinout per datasheet (`datasheets/FS8205A_C908265.pdf`): 1 S1, 2 D, 3 S2, 4 G2, 5 D, 6 G1. Symbol unit A = G6/S1/D2, unit B = G4/S3/D5 | Decided | C2830320 (another FS8205A in SOT-23-6) is $0.02 cheaper; not used because its datasheet pinout wasn't checked |
| D40 | Every fitted part now has a stocked LCSC number (see BOM-for-review.csv). Changes: green LED → KT-0603G C12624 (superseded by D44); 22 µF → **C12891** (Basic, 1206 25 V); SM712 → **PSM712 C32677** (Basic); inductor **SWPA5040S6R8MT C36411**, footprint L_Sunlord_SWPA5040S; buttons **TS-1187A C318884** (Basic), footprint SW_Push_1P1T_XKB_TS-1187A; 5.08 terminals **KF128** (C474952/C474953); 2.54 terminals **XY308** (C557685/C915913); OLED header PZ254V C492403 | Decided | |
| D41 | Keep the **560k** sense resistor (C23203): it is a *preferred* Extended part, so no feeder fee. Supersedes the 1M/200k idea | Decided | |
| D42 | 5.08 terminals keep the Phoenix MKDS footprint for now (same pitch as KF128) | Proposed — **Superseded by D79** (valve board) | Swap to a KF128-specific footprint at layout if outline/hole size differs |
| D43 | Estimate, JLCPCB Economic PCBA, 10 boards: **≈ $231 ($23/board)** excl. shipping/tax and with a guessed $5 bare PCB. Biggest items: parts $127 (module $39), 18 Extended feeder fees $55, X-ray of the module $16, manual THT soldering $12 | Proposed | Options to cut it: hand-solder the THT parts yourself (−7 feeder fees, −$12 labour ≈ −$34); red instead of green LEDs (−$3) |

## 14 Oct 2026 — review round 2 (Mitra) + pre-layout checks

| # | Decision | Status | Why / revisit if |
|---|---|---|---|
| D44 | Green LEDs (D6 STDBY, D8 STATUS) → **KT-0805G C2297, Basic, 0805**. TVS D3 → **SMAJ15A C19077535, Preferred Extended** (no fee). Saves 2 × $3.07 | Decided | JLCPCB has no Basic 0603 green or any Basic blue; Basic non-red are white 0603 (C2290), green/yellow/white 0805. Green on 3V3 through 1k is ~0.5 mA — dim but visible; lower R26 if wanted |
| D45 | **No Basic/preferred alternatives worth taking for U1, U2, U4, U5, U7** (searched JLCPCB Basic + Preferred library 14 Oct). Basic bucks (XL1509, TPS5430) are 150–500 kHz with mA quiescent and big inductors; Basic LDOs are XC6206 (200 mA — too little for WiFi peaks) or AMS1117 (1.1 V dropout, mA quiescent — bad on a LiPo). No Basic ESD array, battery protector or I/O expander exists. U3 TP4056 is Preferred (no fee) | Decided | U1 USBLC6 could be dropped (−$5) at some ESD risk on the USB port |
| D46 | AP63205 per datasheet Table 3 (DS41326 Rev 3-2): **L = 4.7 µH** (Sunlord SWPA5040S4R7NT C305174, 3 A, 30 mΩ), C_in 10 µF, C_out 2 × 22 µF, C_bst 100 nF. FB tied to output (fixed 5 V), EN to VIN | Decided | |
| D47 | **LiPo J4: pin 1 = cell −, pin 2 = cell +.** Believed to match Adafruit/SparkFun board-side headers (not confirmed from their drawings); silkscreen must show + and − | Decided | No standard exists — check each cell before connecting |
| D48 | Cost-estimate columns explained in the file itself (Type Basic / PrefExt / Ext, Fee, buy = per-board × N + JLCPCB attrition, or JLCPCB minimum if larger) | Decided | |

## 14 Oct 2026 — layout start

| # | Decision | Status | Why / revisit if |
|---|---|---|---|
| D49 | **Board 100 × 80 mm, 2 layers, 4 × M3 corner holes** (Mitra). Relays + their 5.08 mm terminals along the bottom long edge; 12V IN, RS485, I2C, GPIO_A/B terminals and the OLED header along the top; USB-C on the right edge, LiPo on the left; module top-right with its U.FL facing the right edge | Decided — **Superseded by D80** (valve board) | Within JLCPCB's 100 × 100 price break |
| D50 | Each relay channel: terminal NO-COM-NC directly in front of its relay; relay turned so COM sits straight above the terminal's middle pin and NO/NC face the terminal. Net class **Relay: 2.0 mm track, 0.6 mm clearance** (~4–5 A on 1 oz copper) | Proposed — **Superseded by D82** (valve board) | Revisit when load current is known — 2 oz copper or mask-opened traces for more |
| D51 | Module footprint is a project footprint **irrigation:ESP32-C3-C6-MINI-1U** (stock pads, 13.2 × 12.5 body, no PCB-antenna keep-out). Land pattern checked identical in both datasheets (fig. 11-2) | Decided | Stock RF_Module:ESP32-C6-MINI-1 reserves a 43 × 32 mm antenna keep-out the -1U doesn't need |
| D52 | TP4056 footprint without built-in 0.2 mm thermal vias (below JLCPCB's 0.3 mm standard); 0.3 mm vias to be added under its pad when routing | Decided | |
| D53 | Net classes: Default 0.25 mm / 0.2 mm; Power 0.6 mm / 0.2 mm (rails, GND, buck switch node); USB 0.3 mm | Proposed | |
| D54 | Cost estimate now shows 10 (Economic), 100 (Economic, panelised) and 100 (Standard) side by side; bare PCB excluded until size known. **≈ $219 for 10 ($21.94/board), ≈ $1,222 for 100 ($12.22/board)** + bare PCB | Decided | |

## 14 Oct 2026 — routing

| # | Decision | Status | Why / revisit if |
|---|---|---|---|
| D55 | **GND kept out of the autorouter.** 69 fan-out vias (short 0.4 mm stub per SMD GND pad), 15 vias in exposed pads (module EP per Espressif's land pattern, TP4056 EP, 0.3 mm drill), GND pours both layers, ~200 grid stitching vias + island-targeted vias | Decided | Same method as Frugal IoT v0.1 |
| D56 | Net classes revised after a pad-escape check: **PowerFine 0.3 mm** (+3V3, +3V3_SW, +5V_SW, VBUS — ~1 A), **USB 0.25 mm / 0.15 mm**; Power 0.6 mm (12 V, 5 V, VBAT, buck), Relay 2.0 mm / 0.6 mm | Decided | 0.4–0.6 mm could not enter the USB-C (0.5 mm pitch) or TCA9534 (0.65 mm) pads |
| D57 | Routing by **Freerouting 2.1.0** driven pass-by-pass from `layout/route/Route.java` | Decided | 2.1.0 CLI ignores max-passes/timeout and writes nothing until 100 %; 2.5.0 needs Java 25 |
| D58 | Relay contacts routed on the bottom layer, 2 mm, COM straight down to the terminal's middle pin | Decided — **Superseded by D82** (valve board) | 12 V loads, 4–5 A (Mitra) |
| D59 | Thermal reliefs: minimum 1 resolved spoke (6 pads have one spoke) | Decided | Electrically fine; geometry around fine-pitch pads leaves no room for two |
| D60 | 9 silkscreen-edge notes accepted: J1 (USB-C) and J4 (JST) outlines overhang the board edge by design; fab clips silk at the edge | Decided | |
| D61 | Board title **"Frugal-IoT Irrigation V0.1"** on top silkscreen, 2 mm, vertical beside K4 (Mitra; "V0,1" read as V0.1) | Decided — **Superseded by D80** (valve board) | |
| D62 | JLCPCB files in `fabrication/`: gerbers.zip (9 layers + PTH/NPTH drill), BOM_JLCPCB.csv, CPL_JLCPCB.csv (105 parts); Gerbers checked independently in gerbv | Decided | Check rotations in JLCPCB's preview before ordering |
| D63 | **Bare PCB quoted by JLCPCB** from the real gerbers (15 Oct 2026): detected 2-layer 100 × 80 mm; 10 pcs A$7.18 ≈ US$5.00, 100 pcs A$100.31 ≈ US$69.90 (JLCPCB's displayed 1.435 AUD/USD). DHL to Australia A$30.47 / A$70.86 (bare boards). Totals now **≈ $224 for 10 ($22.44/board), ≈ $1,291 for 100 ($12.91/board)** excl. shipping | Decided — **Superseded by D86** (valve board) | Not ordered; assembly quote needs a JLCPCB login |
| D64 | Folder tidied for review (15 Oct 2026): README.md board description added; all scripts gathered under `claude-tools/`; interim outputs, backups and one-off scripts removed; cost estimate shows 10 and 100 (Economic) only; schematic title block now "Frugal-IoT Irrigation" rev 0.1 | Decided | |
| D65 | **Proposed: XB5353A** (C80628, single-chip Li-ion protection with integrated MOSFETs) to replace DW01A + FS8205A — saves one Extended part (~$3/order) and a part on the board | Approved — apply with the reviewers' changes | Datasheet checked 15 Oct 2026: 3 A discharge over-current (cell load < 1 A), 4.30 / 2.4 V, 54 mΩ; pins VT/GND/VDD/VM/VM. Same part as Frugal-IoT V0.2 (its D19) |
| D66 | **Possible next revision: ESP32-C3-WROOM-02U** instead of MINI-1U to avoid JLCPCB's X-ray fee on leadless parts ($1.64/board @10, $0.49 @100). ESP32-C6-WROOM-1U (would restore BTN2 and GPIO_B) is a catalogued part but out of stock at JLCPCB (Oct 2026). Different footprints and pinouts — not a drop-in swap; needs re-placement and re-routing | Deferred | Left for now pending reviewers' comments (Mitra) |

## 20 Nov 2026 — branch `uln2803`: relays replaced by valve drivers (Phase 1: schematic + cost)

D67, D68, D70 and D71 record the ULN2803A version tried first; **superseded on 21 Nov by D73 (one
AO3400A MOSFET per valve)**. They are kept because D70 is the reason for the switch.

Phase 1 changed the schematic, BOM and cost estimate only; the PCB was re-laid out to match in Phase 2 (D79–D86).
Figures below are from the UTC ULN2803 datasheet (`datasheets/ULN2803_UTC_C33924.pdf`), the part chosen.

| # | Decision | Status | Why / revisit if |
|---|---|---|---|
| D67 | **K1–K4 (SRD-12VDC relays), U9 ULN2003A and the 3-way relay terminals replaced by U9 ULN2803A (C33924, UTC ULN2803G-S18-R, SOP-18 300 mil) and four 2-way terminals J12–J15 (V+, OUT)**. Valves are 12 V DC solenoids switched on the low side. Terminals reuse KF128-5.08-2P (C474952, same as 12 V IN) so they add no feeder fee. LED + 4.7k per valve kept, now across the valve | Superseded by D73 | No ULN2803 is a JLCPCB Basic part (checked 20 Nov 2026): every one carries the $3.07 Extended fee. C33924 chosen for stock (12 k) and a usable datasheet. **Footprint is KiCad's SOIC-18W 7.5 × 11.6 mm — check against UTC's SOP-18 drawing before layout** (the datasheet has no package drawing) |
| D68 | **Two channels per valve, paired in hardware**: each TCA9534 output (P0–P3) drives two inputs, and the two outputs are tied, so 8 channels make 4 valves. P4–P7 stay on the DNP header | Superseded by D73 | Paired at the inputs, not in firmware, so a firmware bug cannot switch on half a pair and overload it. Halving the current per channel helps twice: VCE(sat) falls (1.3 → 1.1 V typ going from 350 to 200 mA), and the 3.2 V drive from the TCA9534 is inside the spec (VIN(ON) ≤ 2.4 V at 200 mA, ≤ 3.0 V at 300 mA; nothing is specified above 300 mA). The alternative, 8 independent valves at ≤ 0.15 A each, needs only the paired wiring removed |
| D69 | **Flyback: COM (pin 10) to the same +12V net as the valves' V+ terminal pins, after D2** (reverse-polarity diode). C22 (10 µF 25 V, Basic) on +12V at the driver | Decided | The clamp diodes only work if COM is on the supply the coil is returning to. Loop at turn-off: coil → OUT → clamp diode → COM → +12V → V+ terminal → coil, all on the board. If V+ were taken from before D2, the loop would have to pass backwards through D2 and the coil energy would instead pump up +12V until the SMAJ15A clamps. If a valve is wired to any OTHER supply, its clamp is lost and the Darlington avalanches at turn-off (the datasheet: "the input and output parasitic diodes cannot be used as clamp diodes"). Surges coming in on the valve wires are clamped onto +12V by the same diodes and absorbed by D3 (SMAJ15A) |
| D70 | **Rating: 12 V DC valves up to ~0.35 A each, one valve on at a time.** Not pumps, not latching (pulse) valves, not 24 V AC irrigation valves | Superseded by D73 | The limit is the SOP-18 package, not the channels: 0.625 W at 25 °C on a 30 × 30 mm copper area, derating to 0 at 150 °C (≈ 0.45 W at 60 °C). Paired at 0.35 A: VCE(sat) ≈ 1.05 V typ / 1.25 V max → 0.37 / 0.44 W, OK to ~60 °C. At 0.5 A: 1.15 / 1.4 V → 0.58 / 0.70 W, over the rating even at 25 °C. Datasheet duty-cycle chart agrees: two channels on continuously, 200 mA each at 25 °C. The valve also sees ~1.1 V less than with a relay; on a 12 V battery that can put it below a 12 V valve's −10 % rating. Firmware already opens one valve at a time; opening several by hand from the portal could overheat U9. **Options if valves draw more:** (a) DIP-18 ULN2803 (C75528, 1.47 W, hand-soldered, ~+$0.40/board); (b) four logic-level N-MOSFETs (AO3400A C20917, Basic) each with an SS34 flyback diode (Basic, already on the board) and a 100k gate pull-down — ~0.03 V drop, several amps, so pumps work too, no new feeder fee, within ±$0.15/board of the ULN2803. (b) is the better circuit; the ULN2803A was kept because it was the brief |
| D71 | **Cost, JLCPCB prices fetched 20 Nov 2026: $19.80/board at 10, $11.24 at 100** (was $22.03 / $12.63 for the relay design at the same prices). Saving $2.23 and $1.39 per board: relays −$1.00, 3-way terminals → 2-way, 24 fewer hand-soldered joints, one fewer Extended part, partly offset by U9 ($0.31 and Extended vs $0.15 Basic) | Superseded by D73 | Bare PCB still the 100 × 80 mm quote: a smaller board in Phase 2 is the next saving |
| D72 | `run_draw.sh`, `run_draw_bg.sh`, `run_kicad.sh` locate their files relative to themselves; they still pointed at the folder's location before it moved into this repo. The layout scripts still do, and are for Phase 2 | Decided | |

## 21 Nov 2026 — valve drivers: discrete MOSFETs instead of the ULN2803A (Mitra)

| # | Decision | Status | Why / revisit if |
|---|---|---|---|
| D73 | **Each valve: AO3400A (C20917, Basic) low-side, gate straight from TCA9534 P0–P3, 100k gate pull-down, SS34 (C8678, Basic) flyback diode across the valve, red LED + 4.7k across the valve, 2-way terminal (V+, OUT).** U9 ULN2803A removed; Q8–Q11, R39/41/43/45 (100k), D10/12/14/16 (SS34) added. Every new part is Basic, and SS34 and 100k were already on the board, so no new part numbers | Decided | Replaces the ULN2803A, whose SOP-18 package limited a valve to ~0.35 A and dropped ~1.1 V (D70). AO3400A: 30 V, 48 mΩ max at VGS 2.5 V (the TCA9534 gives ~3.2 V), so ~0.04 V and ~0.05 W at 1 A, and **~2 A per valve with all four on** — pumps and brass valves are back in range. The pull-downs replace the ULN's internal input resistors in holding valves off while the expander pins are inputs (reset, boot). Flyback per D69: diode cathode on the same +12V as the V+ pin, after D2. VDS 30 V is above the SMAJ15A's ~24 V clamp. **Total current from 12 V IN is limited by D2 (SS34, 3 A, ~1 W at 2 A)** — revisit D2 if a pump plus valves exceed ~2.5 A. Phase 2: give the VALVEn nets and the source-to-GND path a wide net class |
| D74 | **Cost, JLCPCB prices fetched 21 Nov 2026: $19.69/board at 10, $11.29 at 100** (relay design at the same prices: $22.04 / $12.63; the ULN2803A version was $19.80 / $11.24 on 20 Nov). 14 Extended part numbers (relay design: 16) | Decided | Bare PCB still the 100 × 80 mm quote; a smaller board in Phase 2 is the next saving |
| D75 | **Eight valve channels, one per TCA9534 pin (P0–P7)**, all fitted by default. Any of channels 5–8 can be left unfitted (its AO3400A, 100k, SS34, LED, 4.7k and terminal) with no other change: the TCA9534 pin is then simply unused. The DNP expander header J10 is removed (all eight pins used). **References renumbered**: RS485 terminal J11 → J10; valve terminals J11–J18; Q8–Q15; pull-downs R39–R53 odd; LED resistors R40–R54 even; SS34 D10–D24 even; LEDs D11–D25 odd. `platformio.ini` comments updated to match (comments only, `platform.h` regenerated) | Decided (Mitra) | Each channel is ~$0.29/board at 10 and ~$0.21 at 100 (D76) and adds no feeder fee, so channels were cheaper than any other way of adding outputs. The 3 A total through D2 is unchanged — more valves, not more simultaneous current. Phase 2: room for eight 5.08 mm 2-way terminals along an edge (~81 mm) is the layout constraint |
| D76 | **Cost with eight channels, JLCPCB prices fetched 21 Nov 2026: $20.86/board at 10, $12.11 at 100** (four channels: $19.69 / $11.29; four-relay design: $22.04 / $12.63) | Decided | Bare PCB still the 100 × 80 mm quote |
| D77 | **12 V input: F1 resettable fuse SMD1812P300TF/16 (C702820; 3 A hold, 5 A trip in ~4 s, 16 V, 40 mΩ) ahead of D2, and D2 SS34 → SS54 (C22452, Basic, 5 A, same SMA footprint).** Order: J2 → F1 → D2 → D3 (TVS) → +12V. Correction: earlier entries (D69, D73, D75) said "D1" for the 12 V input diode; it is **D2** (D1 is the USB diode) — fixed in place | Decided (Mitra) | The fuse is short-circuit protection for eight field cables fed from a battery that can supply hundreds of amps — **not** a current budget: it holds 3 A, trips only above 5 A, and its hold current falls in a hot enclosure. Limiting how many valves are on at once is firmware's job. It must be rated ≥ 16 V: most 1812 PTCs at JLCPCB are 6–8 V and cannot reliably interrupt 12 V. Ahead of the TVS so a TVS conducting for long trips it. No Basic PTC exists, so F1 adds one $3.07 feeder fee. SS54 because all valve current passes D2: at 3 A an SS34 is at its rating. Per-valve fuses not fitted — revisit if AO3400As die from shorted outputs in the field. An inline fuse at the battery is still needed to protect the cable to the board |
| D78 | **Cost with F1 and SS54, JLCPCB prices fetched 21 Nov 2026: $21.44/board at 10, $12.32 at 100** (+$0.58 / +$0.21 over D76; four-relay design $22.04 / $12.63). 15 Extended part numbers | Decided | Bare PCB still the 100 × 80 mm quote |

## 21 Nov 2026 — Phase 2: layout of the valve board

| # | Decision | Status | Why / revisit if |
|---|---|---|---|
| D79 | **Valve and 12 V terminals use a project footprint `irrigation:TerminalBlock_KF128-5.08-2P`** (from KiCad's Phoenix MKDS-1,5-2-5.08, generated by `claude-tools/layout/mkfp_kf128.py`): drill 1.4 mm (was 1.3), courtyard exactly the 10.16 mm body width, silk 0.1 mm inside the body edge. The eight valve terminals are **butted** at 10.16 mm pitch into one 81.3 mm row. Datasheet in `datasheets/KF128-5.08-2P_C474952.pdf` | Decided | Resolves D42. The KF128 drawing gives the body as P × 5.08 mm and a 1.40 +0.10/−0 mm hole; the blocks are made to butt. With the MKDS courtyard (11.17 mm wide) eight in a row are either eight courtyard overlaps or 90 mm long, which does not fit between the bottom corner holes. The drawing does not make clear which face the pins are 5.4 mm from, so the courtyard depth (±5.45 mm) covers both |
| D80 | **Board 100 × 62 mm** (was 100 × 80), 2 layers, 4 × M3 corner holes as D49. Valve terminals along the bottom long edge; **J2 (12 V in) moved to the left edge** just above the valve row; RS485, I2C, GPIO_A/B terminals and the OLED header along the top edge; module top-right with its U.FL at the right edge; USB-C right edge, LiPo left edge as before. Board title **"Frugal-IoT Irrigation V0.2"** (top silk, beside J9) | Decided — title open (Mitra) | 62 mm is the smallest height at which every block still packs inside its own region; at 60 mm the charger needs its region grown and line crossings rise from ~160 to ~210 — a harder board to route for ~$0.04 per board. J2 moved because the 3 A path should not cross the board: on the left edge the loop J2 → F1 → D2 → valves → GND is a few cm. "V0.2" because it is a different board from V0.1 with the same purpose; the schematic title block still says rev 0.1 |
| D81 | **Each valve channel is a column straight above its terminal**, identical in all eight: SS34 across the terminal (cathode over pin 1, anode over pin 2); 4.7k and LED in the next row, LED cathode on the VALVE line; AO3400A turned 270° so its drain points down at that line, source top-left, gate top-right; 100k gate pull-down above the FET, one end over the gate, the other over the source. TCA9534 centred above the row, P0–P3 facing channels 1–4 and P4–P7 facing 5–8. Placed by rule in `place.py`, not by the packer | Decided | Puts each 2 A path in a straight line and the flyback loop (valve → terminal → SS34) at a few mm. Leaving channels 5–8 unfitted (D75) leaves four empty columns, nothing else |
| D82 | **The high-current copper is drawn by rule, before autorouting** (`valve_route.py`), and fixed for the router: J2.1 → F1 → D2 2 mm on top; D2 cathode → three 0.8/0.4 mm vias between channels 1 and 2 → **2 mm +12V bus on the bottom layer** 3 mm above the terminal pins, with a 2 mm stub to every pin 1; per channel a **1 mm VALVE line** from the FET drain straight down through the LED cathode and SS34 anode to pin 2, +12V 1 mm from pin 1 to the SS34 cathode, the FET source 1 mm to two 0.8/0.4 mm GND vias. C22 sits on the feed vias. J2.2 has a solid (not thermal-relief) connection to both GND pours. Net class Valve (1 mm, 0.3 mm clearance) for 12V_IN, D2's anode and the eight VALVE nets; +12V stays Power (0.6 mm) so the router can reach the buck's 0.95 mm-pitch pins for its small branches | Decided | Replaces D50/D58 (relay contacts, 2 mm). 3 A total on 2 mm and 2 A per valve on 1 mm of 1 oz outer copper is ~10 °C rise. The autorouter cannot give these widths near fine-pitch pads and would not make eight channels alike. Ground return is the two pours. Revisit (2 oz copper, wider bus) if valves draw more than ~2 A each or several run at once near the 3 A limit |
| D83 | **Routing: Freerouting 2.1.0 run locally on Java 25**, in rounds of 25 passes with each result merged back as the next start (`route/loop_local.sh`, `route/merge.py` from frugal-iot-hw-lora, changed to skip the fixed wires). Two pipeline fixes found on the way: (1) Freerouting's .ses keeps fixed wires but **drops fixed vias**, and KiCad's SES import replaces all copper, so `copper_snap.py` saves the pre-route copper and restores what the import lost (all 100 pre-route vias, otherwise); (2) +5V, VBAT and the cell-protection path moved from Power (0.6 mm) to PowerFine for the router: at 0.6 mm it could not get between the TP4056 / FS8205A / AP2112 pins. Round 8 left one connection (U2 SW → L1); drawn by hand with V12_SENSE moved out of its way and re-routed alone. C5 and L1 are hand-placed per the AP63205 datasheet layout after the packer twice put C5's SW pad on the far side | Decided | Freerouting's own "incomplete" count is not reliable (it said 102 when 29 were open); every result was checked by importing it and running KiCad DRC (`real_unrouted.sh`). `place.py` now fails if any two courtyards overlap, hand-placed anchors included (C5 first landed on U2) |
| D84 | **Checks (21 Nov 2026): DRC 0 errors; 9 silkscreen-edge notes accepted as D60 (J1 USB-C and J4 JST overhang the edge by design); 0 unconnected; schematic parity 0.** GND: pours both layers, 87 grid stitching vias plus island vias; J2.2 solid. JLCPCB files regenerated: 138 placed parts, BOM and CPL agree. PCB-LAYOUT.pdf: 3D top and bottom, top and bottom copper | Decided | Not yet checked in JLCPCB's assembly preview (rotations) — see fabrication/README.md |
| D85 | **Layout scripts now locate their files relative to themselves** (as D72 did for the schematic scripts); new: `mkfp_kf128.py`, `valve_route.py`, `preroute.sh`, `copper_snap.py`, `real_unrouted.sh`, `look.sh`, `route/loop_local.sh`, `route/merge.py`. `preview.py` needs matplotlib, which this Mac does not have; `look.sh` renders the board from KiCad instead | Decided | |
| D86 | **Cost, JLCPCB prices fetched 21 Nov 2026: $21.47/board at 10, $12.20 at 100** (D78: $21.44 / $12.32 on the 100 × 80 mm quote). The bare PCB is **estimated, not re-quoted**: at 10 the prototype price is the same for any board within 100 × 100; at 100 the board line of the 15 Oct quote is scaled by area (62/80), $56.47 instead of $69.90 | Decided | The size saving is ~$0.13 per board at 100 and nothing at 10 — the layout's gain is in the copper, not the price. Re-quote from `fabrication/gerbers.zip` before ordering |
