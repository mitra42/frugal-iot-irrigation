# Frugal-IoT Irrigation Daughter V0.1

> **Status (21 Nov 2026): schematic, layout and JLCPCB files done, DRC clean — for review, not yet ordered or
> built.** Decisions D1–D12 in DECISIONS.md.

An add-on that gives a Frugal-IoT **sensor board** (frugal-iot-hw-sensor V0.2) or **LoRa board**
(frugal-iot-hw-lora V0.3) eight 12 V DC valve outputs and an OLED. It is the valve-driver half of the irrigation
board (`../irrigation-layout-oct-2026`) on its own: the host does WiFi/LoRa, charging and sensors; this board
switches valves when the host tells it to over I2C.

## How it fits together

```
 solar panel ─► MPPT charge controller ─► 12 V battery
                   │ USB 5 V                 │ 12 V
                   ▼                         ▼
             host board (sensor/LoRa)    this board, J2 (12V IN)
               J2 ◄── 5-wire cable ──► J1        J4–J11 ─► eight 12 V valves
```

- **Power:** the host from the controller's USB port (so no 5 V buck is needed); the valves from the 12 V
  battery into J2 — 3 A resettable fuse, reverse-polarity diode, 15 V TVS, as the irrigation board.
- **J1 → host J2**, a 5-way screw terminal reading GND, SDA, SCL, 3V3, V12 from left to right (names printed
  beside it): the first four to host J2 pins 1–4, V12 (the battery voltage through a 560k/100k divider) to host
  J2 pin 9 (SENS2), so the host can stop watering on a flat battery. Wiring diagrams are in the firmware's
  README.md at the top of this repository.
- **Logic** (a TCA9534 I2C expander at 0x20, and the OLED) runs from the host's switched 3.3 V sensor rail. When
  the host turns that rail off, every valve turns off.
- **Valves:** eight channels, each a logic-level MOSFET switching the valve's low side, a flyback diode, and a red
  LED that shows when it is on. 12 V DC solenoid valves, ~2 A each, ~3 A in total. Not latching valves, not
  24 V AC valves. Channels 5–8 can be left unfitted.
- **I2C pull-ups:** R19/R20, 4.7k to 3V3, fitted - an S2 Mini host has none of its own. With a sensor or LoRa
  host they sit in parallel with the host's, which is fine (D12).
- **OLED:** J3, a 4-pin header for a 128×64 SSD1306 module (GND, VCC, SCL, SDA), on the same I2C bus.
- **Not here:** RS485 soil probes stay on the host's RS485 terminal; how to power them (most need 5–30 V) is
  open until there is experimental evidence (D1).

Board: 100 × 42 mm, 2 layers, 4 × M3 corner holes; valve terminals along the bottom edge, 12 V on the left, host
and OLED connectors on the top.

## Cost (JLCPCB, Nov 2026)

About **$8.21 per board for 10, $4.46 for 100**, assembled, before shipping. With a sensor board, $19.72 / $11.62
— slightly under the all-in-one irrigation board ($21.04 / $12.07). The bare PCB is estimated, not yet quoted.
Breakdown in COST-ESTIMATE.txt; comparison in DECISIONS D7.

## Points for reviewers

1. The MPPT controller's USB ground must be the battery negative (D9) — check before wiring.
2. Firmware: the irrigation app needs a build for each host board (D10).
3. One I2C address (0x20): two add-ons on one host would need address jumpers (D3).
4. Before ordering: follow *How to order from JLCPCB* in `fabrication/README.md`, including checking part rotations in the assembly preview.

## What's in this folder

| | |
|---|---|
| `SCHEMATIC.pdf` | Schematic, one sheet |
| `PCB-LAYOUT.pdf` | 3D views and both copper layers |
| `BOM.csv` | Bill of materials with LCSC (JLCPCB) part numbers |
| `COST-ESTIMATE.txt` | JLCPCB cost for 10 and 100 boards |
| `DECISIONS.md` | Design decisions and why (D1–D12) |
| `fabrication/` | Files to order from JLCPCB — see its README |
| `daughter/` | KiCad 10 project |
| `claude-tools/` | Scripts Claude uses to regenerate the design — reviewers can ignore |
