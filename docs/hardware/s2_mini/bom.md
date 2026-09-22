# Bill of materials — S2 Mini irrigation node

Prices are indicative AliExpress (Sept 2026), seach terms provided.

[`bom.csv`](bom.csv) is machine-generated version without sourcing.

## Read these three lines before ordering

1. **Valves must be NORMALLY CLOSED and must not be latching.** This is a safety requirement, not
   a preference — see "Failure modes" in [README.md](README.md). A latching valve cannot be driven
   by this firmware at all.
2. **The RS485 module must have hardware automatic flow control.** The firmware defines no DE/RE
   pin. Search for those exact words; a plain MAX485 breakout with a DE/RE jumper will receive but
   never transmit.
3. **Do not substitute an opto-isolated relay board** for the MOSFET drivers unless you check its
   polarity. The firmware is active HIGH and no invert flag exists; most of those boards are
   active LOW.

## Controller

| Qty | Part | Designators | ~Each | Search for |
|---:|---|---|---:|---|
| 1 | Lolin / Wemos S2 Mini (ESP32-S2, 4 MB flash, 2 MB PSRAM) | U1 | $5.00 | `Lolin S2 Mini ESP32-S2` |
| 1 | DC-DC buck module, adjustable, 3 A | U2 | $0.65 | `MP1584EN mini buck converter adjustable` |
| 1 | TTL↔RS485 module, **hardware automatic flow control**, 3.3/5 V | U3 | $0.40 | `TTL to RS485 automatic flow control 3.3V 5V` |
| 5 | Logic-level N-MOSFET, TO-220 | Q1–Q5 | $0.35 | `IRLZ44N` |
| 7 | Schottky diode, 1 A 40 V | D1–D7 | $0.05 | `1N5819` |
| 1 | Blade fuse holder + 3 A fuse | F1 | $0.50 | `inline blade fuse holder 12V` |
| 5 | 100 Ω resistor, ¼ W | R4–R8 | | `1/4W metal film resistor kit` |
| 5 | 100 kΩ resistor, ¼ W | R9–R13 | | (from the same kit) |
| 1 | 220 kΩ, 1 % | R1 | | (from the same kit) |
| 1 | 39 kΩ, 1 % | R2 | | (from the same kit) |
| 1 | 820 Ω | R3 | | (from the same kit) |
| 1 | 120 Ω — bus termination, fit at the **last probe** | R14 | | (from the same kit) |
| 2 | 680 Ω — fail-safe bias, **usually not needed** | R15, R16 | | (from the same kit) |
| 1 | 100 µF 25 V electrolytic | C1 | $0.05 | `100uF 25V electrolytic capacitor` |
| 1 | 10 µF electrolytic | C2 | $0.03 | (from a capacitor kit) |
| 4 | 100 nF ceramic | C3–C6 | $0.02 | (from a capacitor kit) |
| 7 | 2-way screw terminal, 5 mm pitch | J1, J7, J9–J13 | $0.10 | `KF301 2P screw terminal 5mm` |
| 1 | 4-way screw terminal, 5 mm pitch | J8 | $0.15 | `KF301 4P screw terminal 5mm` |
| 1 | Prototype board, ~7 × 9 cm | — | $0.50 | `double sided prototype PCB 7x9` |

**Controller subtotal: roughly $9**, assuming you already own resistor and capacitor kits — which
is the usual case, and why they are priced as kits rather than per part.

R15 and R16 are marked DNP on the schematic. Buy them (they cost nothing in a kit) but fit them
only after checking whether your RS485 module already has bias resistors.

## Per sector

| Qty | Part | ~Each | Search for |
|---:|---|---|---:|---|
| 1 | RS485 / Modbus-RTU soil moisture + temperature probe, IP68, 5–30 V | $16.00 | `RS485 Modbus soil moisture temperature sensor IP68` |
| 1 | **Normally-closed** 12 V DC solenoid valve, ½" or ¾" | $5–9 | `12V DC normally closed solenoid valve 1/2 irrigation` |

Three sectors as drawn: about **$65**. The probes dominate the cost of the whole node.

The reference probe is the DFRobot SEN0600; the generic equivalents on AliExpress use the same
register map (function 0x03, moisture then temperature) and are a third of the price. Anything
that answers Modbus RTU with those two registers will work.

## Optional

| Qty | Part | ~Each | Search for |
|---:|---|---|---:|---|
| 1 | Resistive float level sender, 0–170 Ω | $5–12 | `resistive water tank level sender 0-190 ohm` |
| 1 | 12 V pump, or a Sonoff for a mains one | — | `Sonoff basic R2` |
| — | Shielded twisted pair, 2 pair, 24 AWG | per m | `2 pair shielded twisted pair cable 24AWG` |

Senders are commonly sold as 0–190 Ω for fuel tanks, which works — the exact resistance does not
matter because the firmware is calibrated by Tare/Calibrate from the portal, not by the nominal
value. `SENSOR_TANK_RAW_FULL` can also be set in `platformio.ini` if you would rather not calibrate
by hand.

## Not needed, deliberately

- **No relay board.** Discrete MOSFETs are cheaper, silent, draw no holding current and match the
  firmware's polarity. See README.
- **No RS485 termination at the controller.** One 120 Ω at the far end of the bus only.
- **No separate probe supply.** The probes take 5–30 V and run from the 12 V rail.
- **No charge controller, panel or MPPT hardware.** Out of scope for this drawing; that is what
  the FF-ESP32-OpenMPPT build is for.
- **Nothing mains-rated.** A mains pump or router goes behind an external Sonoff.
