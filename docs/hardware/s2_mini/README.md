# Lolin S2 Mini irrigation node — reference hardware

A worked design for the hardware the **`s2_mini`** build needs around it. 

Feel free to modify to your own needs, but check the reasoning below for our design choices so
you can intentionally disagree with them. 

Note - as of September 2026 - none of this has been built on hardware and tested. 

| File | What |
|---|---|
| [`wiring.md`](wiring.md) | **the connection table — the authoritative reference** |
| [`wiring.svg`](wiring.svg) | the same thing as a picture, for assembly |
| [`schematic.pdf`](schematic.pdf) | the circuit, with the values and the reasoning on the sheet |
| [`bom.md`](bom.md) | what to buy, with AliExpress search terms |
| [`bom.csv`](bom.csv) | generated from the schematic |
| [`check_wiring.py`](check_wiring.py) | checks `platformio.ini`, `wiring.md` and the schematic still agree |
| `s2_mini_irrigation.kicad_sch` | the root sheet - a line diagram |
| `driver_valve.kicad_sch` / `driver_switch.kicad_sch` | one output channel, drawn once each |

There is **deliberately no PCB**. This is point-to-point wiring between off-the-shelf modules.

## What the firmware fixes, and what it leaves open

Constraints from code i.e. changing them requires code changes, not just configuration.

- **Outputs are active HIGH.** `Actuator_Digital::act()` is a bare
  `digitalWrite(pin, input->value ? HIGH : LOW)` with no invert flag anywhere in the class. Most
  cheap opto-isolated relay boards are active **LOW**; one of those would open every valve when
  the firmware closed it.
- **The RS485 transceiver must switch direction itself.** `[env:s2_mini]` defines neither
  `SYSTEM_RS485_DE_PIN` nor `SYSTEM_RS485_RE_PIN`, so `System_RS485::txEnable()` short-circuits and
  never drives anything. A plain MAX485 breakout with a DE/RE jumper receives but never transmits.
- **The tank sender divider is 820 Ω to 3V3**, with the sender to ground — `sensor_tank.h` hard-codes
  the raw counts that implies.
- **The battery divider ratio must match `SENSOR_BATTERY_VOLTAGE_DIVIDER`.

## Design decisions

These are our decisions - vary them at will. 

### 12 V in, and nothing about solar

Scope stops at a 12 V input. Charging, panels and MPPT are the FF-ESP32-OpenMPPT board's business
and are not modelled here.

**Reverse polarity: series Schottky, not a P-FET.** A 1N5819 in the positive lead costs ~0.4 V, so
the rail runs at ~11.6 V. A 12 V solenoid operates perfectly well there, which makes the
simplicity worth more than the drop. Use a P-channel MOSFET ideal-diode which would drop ~20 mV instead, if you plan to run this from a nearly-flat battery where every volt counts.

**The 3 A fuse protects the battery, not the board.** Worst case draw is about 0.9 A — one valve
(the sequencer only ever opens one), the S2, and three probes. The fuse is there because a shorted
valve cable across a lead-acid bank is a fire risk and nothing else in the design limits that
current.

### 5 V, and the USB problem

**12 V → 5 V with a buck module, then a series Schottky into VBUS.**

The S2 Mini ties its VBUS pin straight to USB 5 V, so the moment anyone plugs in USB to flash the
board, two supplies meet on one node. The diode plus a deliberate undervolt resolves it: set the
buck to **5.2 V**, and after D2 the rail is ~4.9 V — just *below* USB. When USB is present it wins
and nothing is pushed back into the host port; when USB is absent the buck powers the board. D2
also stops USB back-feeding the buck's output.

**Do not set the buck above ~5.3 V.** Above that, the diode-dropped rail exceeds USB 5 V and the
buck will drive current into the host port through D2 — the exact failure the diode was added to
prevent.

**Why not 12 V → 3.3 V and skip the diode?** Because an LDO cannot do it: at the S2's ~300 mA WiFi
peak, (12 − 3.3) × 0.3 = **2.6 W**, which needs a TO-220 and a heatsink. So 3.3 V would still have
to be a buck, and feeding the 3V3 pin directly then back-drives the module's own regulator and
removes the only thing standing between a drifting trimpot and the ESP32. One 20-cent diode is the
cheaper trade.

### Output drivers: discrete MOSFETs, no relays

Five identical low-side channels: 100 Ω gate series resistor, 100 k gate pull-down, IRLZ44N,
1N5819 flyback across the load.

**Why not relay modules?** They are easy to buy, but they are usually active LOW (see above), they
draw coil current continuously while a valve is open, and they wear out. A logic-level MOSFET is
cheaper, silent, and its natural polarity is the one the firmware already uses.

**Why IRLZ44N?** Availability, not merit. It is logic-level (V<sub>GS(th)</sub> 1.0–2.0 V), it is
comfortably in saturation at a 3.3 V gate for a 0.5 A solenoid, and being rated 55 V / 47 A — wildly
more than needed — is exactly why it is cheap and stocked everywhere. An AO3400 is the SMD
equivalent; an IRLB8721 is slightly better and slightly harder to find.

**Pump and load are 12 V DC, and mains is out of scope.** If the pump or the router is
mains-powered, drive an external Sonoff from the frugal-iot server rather than putting mains on
this board. Nothing here is rated for it, and mixing mains with low voltage raises the safety bar a
long way past what a drawing like this can carry responsibly. That decision is also what removed
two relays, two coil currents and a pile of clearance requirements from the design.

### Failure modes — a dead controller must not leave water running

Three independent layers, two of which constrain purchase decisions.

1. **Normally-closed solenoids only.** If 12 V disappears, an NC valve shuts mechanically, with no
   circuit involved. This is the layer that actually satisfies the requirement.
   **Latching valves must not be used** — they hold their last state, and the firmware could not
   drive one anyway: it holds a level for a duration, where a latching valve needs an H-bridge and
   two pins per valve.
2. **The 100 k gate pull-downs.** Covers the case of 12 V present, controller dead, resetting, or still booting.
   The pull-down holds the gate due while the ESP32 GPIOs are floating before `setup()` runs and during a brownout,
3. **The battery interlock**, at 12.6 V ± 0.2 (`OSPIT_LVD_IRRIGATION_MV`). This covers the slow
   case — a sagging battery that can still hold a solenoid open but can no longer run the system.

None of the five outputs is a strapping pin (those are GPIO0, GPIO45 and GPIO46 on the S2), so
nothing here affects boot mode.

### Battery sense

**220 k / 39 k, ratio 6.641, with 100 nF at the pin.** 15 V puts 2.26 V on the pin, inside the S2
ADC's 0–2500 mV linear range at the default attenuation; 12.6 V puts 1.90 V. The values are high
because a 12 V bank moves slowly, so 49 µA of standing drain is worth more than the extra
resolution.

**The capacitor is required, not optional.** Source impedance is 220k∥39k = 33 kΩ, well above the
ADC's ~10 kΩ preference. 100 nF gives τ = 3.3 ms against a 10 s sample interval, so the reading is
fully settled.

If, for software testing, you fit no divider and run on USB, comment `SENSOR_BATTERY_PIN` back out as 
a floating pin looks similar to brownout causing a hard shutdown.

### RS485 and the probes

**One 120 Ω termination, at the far end of the bus.** Not on this board — at the last probe.

**Bias resistors are drawn but marked DNP**, because most auto-direction modules already fit bias
and termination and a second set makes things worse. If yours does not, the arithmetic matters:
fail-safe bias has to hold the idle bus above 200 mV differential, and with 120 Ω at *both* ends
(60 Ω effective) a 680 Ω pair gives only 3.3 × 60/1420 = **139 mV**, which is not enough. With one
termination, 680 Ω gives 268 mV and is right. Terminate both ends and you need 470 Ω.

**Probes run from the 12 V rail**, since SEN0600-class probes accept 5–30 V. No separate supply.

**Connect them one at a time, in sector order.** `SENSOR_SOILMODBUS_AUTOPROVISION` writes an
address to whichever probe answers the factory address, and every probe ships as address 1 — so two
unprovisioned probes on the bus at once cannot be told apart.

### Grounding

Star point at the 12 V input negative terminal. Solenoid return currents must not share a conductor
with the ground path back to the S2: a 0.5 A pulse down a shared return puts tens of millivolts
under the battery and tank readings. Run a separate wire from each driver's source to the star
point rather than daisy-chaining them.

## Deep sleep concerns

**This board does not sleep, and should not.** `frugal_iot.configure_power(Power_Loop, 10000, 10000)`
keeps it awake on a 10-second cycle. That is the right call here: the ESP32 draws well under a watt
against valves and pumps that draw orders of magnitude more, so sleeping saves nothing that
matters, and a deep sleep mid-run would abandon the run — `Control_Irrigation` returns to idle in
`setup()`.

Recorded here because the findings would otherwise be scattered, and because anyone who tries to
add sleep later will hit all of them:

- **GPIO38 and GPIO40 are not RTC pads on the S2.** They float on wake, and
  `Actuator_Digital::setup()` prints a warning saying so. On this board that means the pump and
  load outputs, and the gate pull-downs are what make it safe.
- **`Actuator::preserveDuringSleep` exists to hold pins through a sleep, and the low-voltage path
  deliberately does not use it.** `System_Power::checkLevel()` goes to deep sleep as fast as it
  can, without `prepare()`, because the point is to get there before the rail collapses. The cost
  is that pins are released — and that is the *correct* trade here, because holding them would hold
  a valve **open** on a flat battery.
- **`System_Modbus` loses its `connected` flag**, so the first read after each wake costs a 2 s
  ModbusMaster timeout per absent probe.
- **The tank and battery readings are taken fresh on each wake** and need no state, so those are
  the parts that would survive sleep unchanged.

## Known-unmeasured

- Nothing in this design has been built. The values are arithmetic and datasheet figures.
- The tank sender's 0 Ω / 170 Ω / 820 Ω figures come from a comment in OSPIT's `irrigation.lua` and
  were never measured. Calibrate rather than trusting them.
- Solenoid current is assumed ~0.5 A. Check yours before trusting the 3 A fuse.

## Regenerating

The schematic and the wiring diagram are generated, not hand-drawn, so that the pin assignments
cannot drift from `platformio.ini`. The generator scripts live outside the repo; the
committed artefacts are the schematic, the exports and `wiring.md`. To verify they still agree:

```bash
python3 docs/hardware/s2_mini/check_wiring.py
```

It compares `platformio.ini`, the table in `wiring.md` and the schematic's own netlist, and exits
non-zero if any of the three disagree.

ERC is clean, and the netlist was diffed pin-by-pin against the intended connection list.
