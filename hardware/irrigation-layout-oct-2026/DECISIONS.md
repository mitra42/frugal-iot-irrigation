# Frugal-IoT Irrigation V0.1 — decision log

Key choices, why they were made, and what would reopen them. Newest at the bottom of each
section. Status: **Decided** (go ahead), **Proposed** (default unless changed), **Open**.

Status (15 Oct 2026): schematic, layout and JLCPCB fabrication files complete; out for review.

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
| D30 | TCA9534 P4–P7 to a DNP 6-pin header; INT not connected | Proposed | Firmware should drive unused P4–P7 low if the header is not fitted |

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
| D42 | 5.08 terminals keep the Phoenix MKDS footprint for now (same pitch as KF128) | Proposed | Swap to a KF128-specific footprint at layout if outline/hole size differs |
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
| D49 | **Board 100 × 80 mm, 2 layers, 4 × M3 corner holes** (Mitra). Relays + their 5.08 mm terminals along the bottom long edge; 12V IN, RS485, I2C, GPIO_A/B terminals and the OLED header along the top; USB-C on the right edge, LiPo on the left; module top-right with its U.FL facing the right edge | Decided | Within JLCPCB's 100 × 100 price break |
| D50 | Each relay channel: terminal NO-COM-NC directly in front of its relay; relay turned so COM sits straight above the terminal's middle pin and NO/NC face the terminal. Net class **Relay: 2.0 mm track, 0.6 mm clearance** (~4–5 A on 1 oz copper) | Proposed | Revisit when load current is known — 2 oz copper or mask-opened traces for more |
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
| D58 | Relay contacts routed on the bottom layer, 2 mm, COM straight down to the terminal's middle pin | Decided | 12 V loads, 4–5 A (Mitra) |
| D59 | Thermal reliefs: minimum 1 resolved spoke (6 pads have one spoke) | Decided | Electrically fine; geometry around fine-pitch pads leaves no room for two |
| D60 | 9 silkscreen-edge notes accepted: J1 (USB-C) and J4 (JST) outlines overhang the board edge by design; fab clips silk at the edge | Decided | |
| D61 | Board title **"Frugal-IoT Irrigation V0.1"** on top silkscreen, 2 mm, vertical beside K4 (Mitra; "V0,1" read as V0.1) | Decided | |
| D62 | JLCPCB files in `fabrication/`: gerbers.zip (9 layers + PTH/NPTH drill), BOM_JLCPCB.csv, CPL_JLCPCB.csv (105 parts); Gerbers checked independently in gerbv | Decided | Check rotations in JLCPCB's preview before ordering |
| D63 | **Bare PCB quoted by JLCPCB** from the real gerbers (15 Oct 2026): detected 2-layer 100 × 80 mm; 10 pcs A$7.18 ≈ US$5.00, 100 pcs A$100.31 ≈ US$69.90 (JLCPCB's displayed 1.435 AUD/USD). DHL to Australia A$30.47 / A$70.86 (bare boards). Totals now **≈ $224 for 10 ($22.44/board), ≈ $1,291 for 100 ($12.91/board)** excl. shipping | Decided | Not ordered; assembly quote needs a JLCPCB login |
| D64 | Folder tidied for review (15 Oct 2026): README.md board description added; all scripts gathered under `claude-tools/`; interim outputs, backups and one-off scripts removed; cost estimate shows 10 and 100 (Economic) only; schematic title block now "Frugal-IoT Irrigation" rev 0.1 | Decided | |
| D65 | **Proposed: XB5353A** (C80628, single-chip Li-ion protection with integrated MOSFETs) to replace DW01A + FS8205A — saves one Extended part (~$3/order) and a part on the board | Approved — apply with the reviewers' changes | Datasheet checked 15 Oct 2026: 3 A discharge over-current (cell load < 1 A), 4.30 / 2.4 V, 54 mΩ; pins VT/GND/VDD/VM/VM. Same part as Frugal-IoT V0.2 (its D19) |
| D66 | **Possible next revision: ESP32-C3-WROOM-02U** instead of MINI-1U to avoid JLCPCB's X-ray fee on leadless parts ($1.64/board @10, $0.49 @100). ESP32-C6-WROOM-1U (would restore BTN2 and GPIO_B) is a catalogued part but out of stock at JLCPCB (Oct 2026). Different footprints and pinouts — not a drop-in swap; needs re-placement and re-routing | Deferred | Left for now pending reviewers' comments (Mitra) |
