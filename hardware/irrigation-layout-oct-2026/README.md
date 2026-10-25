# Frugal-IoT Irrigation V0.1

An ESP32 I/O board for irrigation and similar field control: four 12 V relays, RS485 (Modbus), I2C sensors,
two spare GPIOs, and power from 12 V, USB or a single LiPo cell. Designed Oct 2026 for assembly by JLCPCB.
This folder is for review: comments and suggested changes welcome — see "Points for reviewers" below.

## The board

- 100 × 80 mm, 2 layers, 1.6 mm FR-4, 4 × M3 corner holes.
- Relays and their screw terminals along one long edge; field connectors (12 V in, RS485, I2C, GPIOs, OLED)
  along the other; USB-C on the right short edge, LiPo connector on the left.
- Surface-mount parts on the top side, assembled by JLCPCB; relays and terminals are through-hole
  (JLCPCB hand-solders them, or you can).

## Power

- Powered from **12 V** (screw terminal, up to 15 V), **5 V USB-C**, or a **local single LiPo cell** (optional,
  JST-PH, 18650 at most).
- 12 V input: reverse-polarity protection (Schottky), 15 V TVS, then a 5 V buck (AP63205). USB 5 V and the
  buck output are diode-ORed onto the 5 V rail, so either or both can be connected.
- The 5 V rail charges the cell (TP4056; 250 mA, or 500 mA with a solder jumper). The cell has its own
  protection (DW01A + FS8205A: over-charge, over-discharge, over-current/short).
- Load sharing: when 5 V is present it powers the board and the charger only charges; when 5 V goes away a
  P-FET switches the cell in. Either source then feeds a 3.3 V LDO (AP2112K, 600 mA) for the module.
- Two switched rails turned on together by one GPIO: **3V3_SW** (sensors, I2C, RS485) and **5V_SW** (RS485
  sensor supply). Both off at reset. 5V_SW only exists when 12 V or USB is present, not on battery alone.
- Monitoring: the 12 V input and the cell voltage are each read on an ADC pin.
- The relay coils run from 12 V, so **relays work only when 12 V is connected**.

## Processor

- ESP32-C6-MINI-1U module (default) or ESP32-C3-MINI-1U on the same footprint — both have a **U.FL antenna
  socket** (an external antenna is needed). Two pairs of 0 Ω links select which module's USB pins are used.
- Native USB on USB-C for programming and serial (no USB-UART chip); USB ESD protection.
- Buttons: RESET, BOOT/BTN1 (hold at reset for download mode, a normal button afterwards), BTN2 (C6 only).
- Status LED (green); charger LEDs (charging red, charged green).
- Unfitted headers for UART0 debug, a cell thermistor, and the I/O expander's spare pins.

## Outputs and interfaces

- **4 relays** (SRD-12VDC-SL-C), contacts NO/COM/NC on 5.08 mm screw terminals, isolated from the board rails.
  Rated for 12 V DC loads up to about 4–5 A per channel with this copper. Driven through an I2C I/O expander
  (TCA9534) and a ULN2003, so the relays stay off through reset and boot. A red LED per relay shows it is on.
- **RS485** (Modbus): 3.3 V transceiver, not isolated, transmit/receive switched automatically from the TX
  line; bias resistors, 120 Ω termination on a solder jumper, surge protection. Terminal: 5V_SW, A, B, GND.
- **I2C**: 4-way 2.54 mm terminal (3V3_SW, SDA, SCL, GND) plus a 4-pin OLED header (GND, 3V3_SW, SCL, SDA).
- **2 GPIOs** (GPIO_A — ADC capable — and GPIO_B, C6 only) on 2-way 2.54 mm terminals with GND, with
  unfitted pull-up/pull-down positions.

## Firmware notes

- Turn on RAIL_EN before any I2C traffic (relay changes included) or RS485; the expander itself is always
  powered and keeps the relays as set while the rail is off.
- Relay outputs: TCA9534 P0–P3 high = relay on. P4–P7 go to an unfitted header — drive them low if unused.
- GPIO map (module pad → use) is in DECISIONS.md, D18.

## Points for reviewers

Items that are deliberately "proposed" rather than final — opinions especially welcome:

1. RS485 direction from TX (D21): fine for Modbus at 9600 baud, marginal with long cables and two
   terminations; a true auto-direction transceiver (THVD1406) is the alternative.
2. RS485 terminal supplies 5V_SW — should it be 12 V for your sensors? (D22)
3. Cell thermistor (TEMP) disabled by default (D27); charge current 250/500 mA (D12).
4. LiPo connector: pin 1 = −, pin 2 = + (D47). JST-PH polarity is not standard — check your cells.
5. Relay contact copper ~4–5 A per channel (D50).
6. The 5.08 mm terminals use the Phoenix MKDS footprint for KF128 parts of the same pitch (D42).
7. Small bulk capacitance on 3V3_SW to limit inrush (D33).
8. Before ordering: check part rotations in JLCPCB's assembly preview (see fabrication/README.md).

## Cost (JLCPCB, Oct 2026)

About **$22 per board for 10**, **$13 per board for 100**, assembled, before shipping. Breakdown in
COST-ESTIMATE.txt; the ESP32 module is the largest single item.

## What's in this folder

| | |
|---|---|
| `README.md` | This description |
| `SCHEMATIC.pdf` | Full schematic, one sheet |
| `PCB-LAYOUT.pdf` | 3D views and both copper layers |
| `BOM.csv` | Bill of materials with LCSC (JLCPCB) part numbers |
| `COST-ESTIMATE.txt` | JLCPCB cost for 10 and 100 boards |
| `DECISIONS.md` | Every design decision, why, and what would reopen it (D1–D64) |
| `esp32_io_board/` | KiCad 10 project (schematic, PCB, project libraries) |
| `fabrication/` | Files to order from JLCPCB — see its README |
| `firmware/` | PlatformIO env for frugal-iot-irrigation + board variant (pins_arduino.h) |
| `datasheets/` | Datasheets checked during design |
| `claude-tools/` | Scripts Claude uses to regenerate and change the design — reviewers can ignore |

To suggest a change: mark up the PDFs, edit in KiCad, or describe it; the schematic is generated from
`claude-tools/schematic/circuit.py`, so changes made by Claude go there rather than into the .kicad_sch.
