# Wiring — Lolin S2 Mini irrigation node

This is the authoritative reference. [`schematic.pdf`](schematic.pdf) is the same information drawn
as a circuit; [`wiring.svg`](wiring.svg) is the same information drawn as a picture. If the three
ever disagree, believe this table — and run
[`check_wiring.py`](check_wiring.py), which compares it against both `platformio.ini` and the
schematic and exits non-zero if they have drifted.

**Read [README.md](README.md) before building anything.** It explains why the parts are what they
are, and three of the choices here are safety-relevant rather than merely tidy.

## Controller pins

Every row is fixed by `[env:s2_mini]` in [`platformio.ini`](../../../platformio.ini). The `Key`
column is what `check_wiring.py` matches on — don't rename it.

| Key | GPIO | S2 Mini pin | Direction | Connects to |
|---|---|---|---|---|
| valve1 | GPIO10 | 14 | out, active HIGH | R4 (100R) → Q1 gate |
| valve2 | GPIO13 | 15 | out, active HIGH | R5 (100R) → Q2 gate |
| valve3 | GPIO14 | 16 | out, active HIGH | R6 (100R) → Q3 gate |
| pump | GPIO38 | 23 | out, active HIGH | R7 (100R) → Q4 gate |
| load | GPIO40 | 24 | out, active HIGH | R8 (100R) → Q5 gate |
| tank | GPIO6 | 12 | analog in | junction of R3 (820R) and the float sender |
| rs485_rx | GPIO16 | 27 | UART in | RS485 module **RXD** |
| rs485_tx | GPIO18 | 28 | UART out | RS485 module **TXD** |
| battery | GPIO8 | 13 | analog in | junction of R1 (220k) and R2 (39k) |

Plus the supply and ground pins:

| S2 Mini pin | Name | Connects to |
|---|---|---|
| 25 | VBUS | D2 cathode (5 V from the buck, through the diode) |
| 8 | 3V3 | R3, RS485 module VCC, C6 — this pin is an **output** from the module's own regulator |
| 18, 26 | GND | common ground |

All 19 remaining GPIOs are unused and left unconnected.

## Power

| From | To | Notes |
|---|---|---|
| 12 V battery + | J1-1 | via the installation's own isolator if it has one |
| 12 V battery − | J1-2 | GND |
| J1-1 | F1 | 3 A fuse |
| F1 | D1 anode | 1N5819, series reverse-polarity protection |
| D1 cathode | **+12 V rail** | ~11.6 V after the diode drop |
| +12 V rail | U2 IN+ | buck module in |
| U2 OUT+ | D2 anode | **set the buck to 5.2 V** — see README |
| D2 cathode | S2 Mini VBUS (pin 25) | ~4.9 V |
| +12 V rail | C1 (100uF) | bulk, near the drivers |
| U2 OUT+ | C2 (10uF) | |
| VBUS rail | C3 (100nF) | |
| 3V3 | C6 (100nF) | |

## Each output channel, five times

Identical for valve 1–3, pump and load. `n` is the channel. This is what is inside each block on
page 1 of the schematic; it is drawn once on `driver_valve.kicad_sch` (valves) and
`driver_switch.kicad_sch` (pump and load).

| From | To |
|---|---|
| GPIO (table above) | gate resistor 100R |
| gate resistor | Q*n* gate **and** 100k pull-down to GND |
| Q*n* source | GND |
| Q*n* drain | terminal J-2, and flyback diode anode |
| flyback diode cathode | +12 V rail |
| terminal J-1 | +12 V rail |
| terminal J-1 / J-2 | the 12 V device (+ / −) |

The 100k pull-down is not optional — see README, "Failure modes".

## RS485 bus

| From | To |
|---|---|
| 3V3 | module VCC |
| GND | module GND |
| module RXD | GPIO16 |
| module TXD | GPIO18 |
| module A | J8-3 → every probe's A |
| module B | J8-4 → every probe's B |
| +12 V rail | J8-1 → every probe's V+ |
| GND | J8-2 → every probe's GND |

120R termination goes at the **far end** of the bus, across A and B at the last probe — not at the
module. Fit one only.

Field cable: shielded twisted pair, one pair for A/B and one for 12 V/GND, shield earthed at the
controller end only.

## Tank sender

| From | To |
|---|---|
| 3V3 | R3 (820R) |
| R3 | GPIO6, C5 (100nF) to GND, and J7-1 |
| J7-2 | GND |
| J7-1 / J7-2 | the float sender |

## Commissioning order

1. Fit the battery divider **before** first power-on, or comment `SENSOR_BATTERY_PIN` back out.
   A floating GPIO8 can read as a flat battery and put the board to sleep.
2. Set the buck to 5.2 V **off-load, before** connecting the S2 Mini.
3. Power up on 12 V with no probes and no valves. Check the portal appears.
4. Connect soil probes **one at a time, in sector order**, waiting a few read cycles between each.
   Addresses are auto-provisioned from 2 upwards and every probe ships as address 1, so two
   unprovisioned probes on the bus at once cannot be told apart.
5. Calibrate the tank: Tare with it empty, then enter `100` with it full.
6. Only then connect the valves.
