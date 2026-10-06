# How this differs from OSPIT

This application started as a port of
[OSPIT](https://www.apc.org/en/news/meet-ospit-sustainable-energy-and-irrigation-solution-community-networks),
the NodeMCU-Lua firmware for the FF-ESP32-OpenMPPT board, and parts of it are still close ports.
This file collects what changed and why, and what looks wrong in OSPIT, so that the comments in
the code can stay short. The code says *what* it does; this says how it differs from what OSPIT
did.

OSPIT sources referred to below are from a translated repo that may be out of date. This file only covers what affects this application.

OSPIT's main files, for reference:

| OSPIT file | What it does | Here |
|---|---|---|
| `irrigation.lua` | the sequencer and the tank gauge | `control_irrigation.*`, `sensor_tank.*` |
| `mp2.lua` | MPPT, charge limit, state of charge, battery health, low-voltage disconnect, USB disconnect | `control_mppt.*`, `control_soc.*`, `control_health.*`, the `Control_Hysteresis` interlocks in the `.ino` |
| `display.lua` | three status pages | `control_oled_irrigation.*` |
| `is.lua` | timers, GPIO setup | the library's `System_Power` and `Actuator_Digital` |
| `owids.lua` / `owread.lua` | DS18B20 probes | the library's `Sensor_DS18B20` |
| `config_default.lua` | defaults | `platformio.ini` and the schema defaults |

---

## 1. Hardware and pins

The `ff_openmppt` pin assignments in `platformio.ini` are OSPIT's own, read out of its Lua:

| Pin | Use | Where OSPIT says so |
|---|---|---|
| 26, 27, 12 | valves 1-3 | `irrigation.lua`: `local valves = {26, 27, 12, 14}` |
| 14 | pump or load | `irrigation.lua` drives it with the valve when `pump_is_load` is false; `mp2.lua` also uses it as the low-voltage load disconnect, and `control.lua` exposes it as "Load power output". Three jobs, one pin. |
| 16 / 17 | RS485 rx / tx | `modbr.lua`: `uart.setup(2, ..., {tx = 17, rx = 16})` |
| 32 | tank gauge | `irrigation.lua`: `ADCmeasure(4, 2)`, i.e. ADC1 channel 4 |
| 33 | battery | `mp2.lua` `Voutmeasure()`: ADC1 channel 5, 1k/15k divider, ratio 0.0625, so a factor of 16 |
| 34 | panel | `mp2.lua` `Vinmeasure()`: 1k/27k divider, ratio 0.035714, so a factor of 28 |
| 21 / 22 | OLED I2C | `init.lua` loads `SSD1306.lua` |

What changed:

- **Three valves, not four.** OSPIT's list has a fourth valve on pin 14, the same pin as the
  pump/load. Here pin 14 is a pump or a load and never a valve.
- **Pin 14: pump or load, chosen at build time.** OSPIT has one output with a runtime flag,
  `pump_is_load`. Here there are two independent optional pins, `IRRIGATION_PUMP_PIN` and
  `IRRIGATION_LOAD_PIN`. `IRRIGATION_PUMP_PIN` is the same as `pump_is_load = false`, and
  `IRRIGATION_LOAD_PIN` is the same as `pump_is_load = true`. On the FF board they cannot both be
  pin 14, so `platformio.ini` sets one and comments out the other. OSPIT's default is the load
  role. The pump role is used here because it exercises the irrigation path.
- **Pin 12: valve 3 or USB supply, chosen at build time.** OSPIT decides at runtime: if probe 3
  does not answer (`shumidity3 == -127`), `irrigation.lua` skips sector 3 and `mp2.lua` uses the
  pin for USB load control. Here you define either `IRRIGATION_VALVE3_PIN` or
  `IRRIGATION_USB_PIN`. The skip itself is kept for another reason, see
  [Skipping a sector](#skipping-a-sector).
- **The display is the I2C SSD1306, not the SSD1327 SPI panel.** The SSD1327 needs pins 16 and 17
  for dc and rst, and the RS485 probes use those pins. OSPIT makes the same choice: `init.lua`
  loads `SSD1306.lua` and leaves the SSD1327 line commented out.
- **GPIO32 may not be the tank.** `mp2.lua`'s header comment calls GPIO32 a temperature sense
  input, but `irrigation.lua` reads it as the tank. Question 7 in `HARDWARE-QUESTIONS.md` asks
  someone with the board to check.
- **The battery divider.** At 12.6 V, OSPIT's 1k/15k divider puts only 0.79 V on the pin, about a
  quarter of the ADC's range. If you are building new hardware, 3k3/15k (a factor of 5.546) gives
  noticeably better resolution.

---

## 2. Irrigation sequencer (`irrigation.lua` → `Control_Irrigation`)

What is the same: once a day, take each sector in turn, open its valve until the soil reaches its
target or a maximum time runs out, then move on. Stop if the tank runs dry or the battery
interlock opens.

Future versions will add functionality here, for example so that a sector might run twice a day or be temperature dependent. 

| OSPIT | Here | Notes |
|---|---|---|
| `i_hr` | `irrigation/hour` | default 3 in both |
| — | `irrigation/minute` | OSPIT starts on the hour |
| `i_vlv_opn` | `irrigation/maxminutes` | |
| `i_nbld` | `irrigation/enabled` | off by default in both |
| `i_lvl1..4` | `sectorN/target` | |
| `low_voltage_disconnect_state` | `irrigation/power` | see [Battery interlocks](#battery-interlocks) |
| `i_tanksens` | — | here, a missing tank sensor is detected rather than configured |
| — | `irrigation/active` | which sector is running; OSPIT has no equivalent |

### Skipping a sector

OSPIT skips a sector whose probe reads `-127` without touching its valve. In OSPIT this is how the
board is configured (see pin 12 above). Here a sector exists because you constructed one, so that
reason is gone. The skip stays because driving a valve with no feedback is worse than not
watering.

The same rule applies when closing. OSPIT's reset branch closes only valves whose probe is not
`-127`, so that it does not switch off the USB charger on pin 12. `closeAll()` does the same, so
a sector with no reading is never driven either way.

### Closing everything at the end of a run

OSPIT's reset branch writes 0 to every valve at the end of a sequence, whoever opened it.
`closeAll()` does the same. Without it, a valve opened by hand from the portal would never close,
because `OUTbool::set()` only sends on a change.

### Interlocks abort the whole sequence

This matches OSPIT's "Irrigation Emergency Stop": an interlock that opens part way through
abandons the cycle, not just the current sector.

**One difference:** OSPIT's emergency stop clears the active valve but leaves `irrigation_done`
false, so its 6-second loop starts again for the rest of the scheduled hour. Here, a cycle that is
blocked at the scheduled moment (a tank still refilling at 03:00, a momentary battery dip) is
written off until the next day. There is a TODO in `Control_Irrigation::periodically()` to add a
retry window if that matters in practice.

### Battery interlocks

OSPIT gates irrigation on `low_voltage_disconnect_state`, the same flag that disconnects the load,
so both switch at 11.9/12.3 V. Here every consumer has its own `Control_Hysteresis`, and the
thresholds set the order things are shed as the battery falls:

| Consumer | Off / on | Why this order |
|---|---|---|
| USB supply | 12.8 / 13.4 V | least important |
| Irrigation | 12.4 / 12.8 V | a pump is the heaviest intermittent load, and watering can wait a day |
| Load (router) | 11.9 / 12.3 V | last, because losing communications means losing the ability to find out what went wrong |

Setting `IRRIGATION_LVD_IRRIGATION_MV=12100` in `platformio.ini` goes back to OSPIT's behaviour.

### Low-voltage deep sleep

OSPIT's `low_voltage_sleep_enabled` defaults to true: below 11.9 V the node deep sleeps for five
minutes at a time. The library supports this (`SYSTEM_POWER_LOW_MV` / `SYSTEM_POWER_LOW_MS`), but
it is **not enabled here yet**. We do not know what the board's outputs do while the ESP32 is
asleep:

- A GPIO is released in deep sleep unless it is explicitly held, and `is.lua` configures pin 14
  (the load switch) with `PULL_UP`. If that pull-up turns the router back on during a sleep meant
  to save power, sleeping makes things worse.
- If the DAC on pin 25 stops charging during sleep, the battery cannot recover during the very
  sleep meant to let it.

For scale: the ESP32 draws well under a watt, so it is not what flattens an 18 Ah battery. The
load is, and the load interlock already sheds that at 11.9 V. `docs/sleep-test.md` describes the
measurement that would settle it.

---

## 3. Tank gauge (`irrigation.lua` → `Sensor_Tank`)

**OSPIT's tank gauge does not measure a level. It only reports whether the sender is connected.**

The hardware, from the comment in `irrigation.lua`: a float sender that reads 170 Ω full and 0 Ω
empty, with an 820 Ω series resistor to 3v3. So:

| State | Pin voltage | 12-bit counts at 11 dB |
|---|---|---|
| full, 170 Ω | 0.567 V | about 703 |
| empty, 0 Ω | 0 V | 0 |
| sender disconnected | pulled to 3v3 | about 4095 |

OSPIT's live code is:

```lua
local tankgaugeadc = ADCmeasure(4, 2)
if tankgaugeadc > 4000 then tankgauge = 0 end
if tankgaugeadc < 3000 then tankgauge = 1 end
```

This cannot tell a full tank from an empty one, because every connected reading is below 3000. It
reports an open circuit as 0, i.e. as an empty tank. Because the sequencer then tests
`tankgauge <= 0 and i_tanksens == true`, a node with `i_tanksens` on and its sender unplugged
refuses to irrigate, and looks exactly like a node whose tank is dry. A genuinely empty tank does
not stop irrigation at all. Between 3000 and 4000, `tankgauge` keeps its previous value.

An earlier version that computed a percentage is still in the file, commented out. It never ran,
and it read a different ADC channel (`ADCmeasure(0, 40)`) from the one it configured.

Here the two states are kept apart:

- no sender fitted, or a broken cable → `validate()` fails → `nan` → the tank does not block
  irrigation
- a real level → 0-100 %, and a genuine low level does stop irrigation

The default calibration (0 and 703 counts) is calculated from the resistances in OSPIT's comment
and has never been measured. Use the portal's Tare and Calibrate. The disconnect threshold of 3000
is the bottom of OSPIT's 3000-4000 dead band.

---

## 4. Display (`display.lua` → `control_oled_irrigation`)

OSPIT shows three pages and moves to the next one each time the display timer fires. Here the
three pages are `Control_Oled` subclasses in a `Control_Carousel`, so they can also be selected by
hand.

- **Page 1 (power):** OSPIT's page is mostly MPPT: open-circuit voltage, tracking voltage, charge
  state and battery temperature. Ours shows battery volts, state of charge, panel volts and the
  charger's state word.
- **Page 2 (soil):** a sector with no reading prints `--` where OSPIT prints `-127`. The tank
  prints `--` when no sender is fitted, which OSPIT cannot distinguish from empty. A `*` marks the
  sector that is watering; OSPIT has no equivalent.
- **Page 3 (network):** follows `display.lua`.

---

## 5. Solar charge control (`mp2.lua` → `Control_MPPT`)

The method is OSPIT's: **fractional Voc**. Unload the panel, measure the open-circuit voltage, and
ask for `Voc / 1.24` (about 0.8 × Voc). The DAC is an inverse throttle in both: a higher step
means less current.

### How often it sweeps

OSPIT re-runs `mp2.lua` every 15 s (`is.lua`), and its sweep takes about a second. Ours cannot: the
panel voltage only arrives through the sensor path, once per wake cycle, so a sweep costs a whole
cycle of not charging. Sweeping every cycle would halve the harvest. `CONTROL_MPPT_SWEEP_S`
defaults to 300 s instead. Voc moves with panel temperature over tens of minutes, so this costs
very little tracking accuracy.

### Regulation near full charge

OSPIT's `Voutctrl()` runs every 600 ms against a reading it takes itself, and moves the DAC by one
step outside a ±30 mV band. Ours runs once per wake cycle (about 10 s) against the battery
sensor's reading. At one step per cycle it would take most of an hour to cross the range, so it is
proportional and slew-limited: `error / CONTROL_MPPT_REGULATE_MV_PER_STEP`, clamped to
`CONTROL_MPPT_MAX_SLEW`. `CONTROL_MPPT_OVERSHOOT_MV` is the backstop that makes the slow loop safe.

### The DAC mapping: 285, not 255

OSPIT maps panel voltage onto the DAC as

```lua
dac1value = (v_mpp_estimate - Vmpp_min) / ((Vmpp_max - Vmpp_min) / 285)
```

The DAC is 8-bit, so dividing by 285 means the top tenth of the range is unreachable. This may be
a deliberate correction for a transfer function that is not quite linear, or it may be a mistake;
the code does not say. It is `CONTROL_MPPT_DAC_SPAN` here, and Part H of `TESTING.md` is the
measurement that would settle it. The per-revision Vmpp ranges (FF v1.0, v1.1, v1.2) are also
OSPIT's.

### When the panel is dark

OSPIT writes step 29 when the panel is dark, and we do not know why. It is a low step, so it asks
for maximum current. That is harmless in the dark, and it means charging starts as soon as the sun
returns rather than at the next sweep. That is the only explanation we can see.
`CONTROL_MPPT_IDLE_STEP` keeps the value.

OSPIT zeroes its panel readings when `V_oc < V_out + 0.2`. Here the same test uses
`CONTROL_MPPT_VOC_MARGIN_MV`, 500 mV by default.

### Heatsink protection

OSPIT has one mechanism: above `heatsink_derate_start_c` (60 °C), it lowers the charge target by
100 mV on each run, and it restores the target below 58 °C.

Here 60 °C is a **hard cut**: charging stops on that cycle and stays stopped until the board has
cooled to 53 °C. OSPIT's progressive back-off is kept but starts lower, at 55 °C.

The progressive back-off cannot be the only mechanism. Lowering the target does nothing while the
battery is below it, because in bulk the target only decides when to start regulating. So the
back-off only takes effect once the target has been walked down below the battery's actual
voltage, and every step above that is dead travel. Measured, at a 10 s cycle and 100 mV per step:
with the battery near full it cuts in after about 30 s, but with a discharged battery at 12.4 V it
takes about 180 s. The discharged battery draws the most current and makes the most heat, so the
response was slowest exactly when it was needed most.

(An earlier version of our port also capped the total back-off. The cap stopped the target above a
discharged battery's voltage, so the protection never took effect at all.)

The restore point is 53 °C rather than 58 °C so that, after a hard cut, charging does not cycle on
and off around the limit.

### Battery profiles

The charge-end voltages, temperature coefficients and hot-battery voltages per chemistry are
OSPIT's `battery_profile_defaults()`. So is the 42 °C hot-battery limit (`batt_charge_limit_temp_c`).

OSPIT has an `is_custom_profile` flag and a parallel set of `batt_*` variables for a custom
profile. Here, selecting a profile *writes* `chargeend`, `tempcoeff` and `hotcharge`, and editing
one of them afterwards keeps the edit. That is all "Custom" means here, so it needs no flag.

---

## 6. Heatsink temperature from diodes (`Sensor_Heatsink`)

OSPIT computes the temperature from raw ADC counts, a hand-calibrated reference voltage and the
6 dB attenuator setting:

```
V = ((raw / 4095) * (Vref * 0.002)) / 1.06
T = -50 + ((1.273 - V) / 0.0048)
```

This works out as `T = 215.2 - 0.2083 × mV`, i.e. 913 mV at 25 °C and 4.8 mV per degree. Those
are the defaults here. We do not copy the arithmetic because we read
`analogReadMilliVolts()`, which applies the chip's factory calibration and already allows for the
attenuator, so `Vref`, the 0.002 and the 1.06 have no equivalent.

OSPIT treats a reading near the supply rail as "sensor missing, or connected the wrong way round".
`SENSOR_HEATSINK_MV_DISCONNECTED` (2500 mV) is the same test.

---

## 7. State of charge (`mp2.lua` → `Control_SoC`)

`mp2.lua` has eight overlapping heuristics with hand-tuned constants. Most of them try to estimate
the state of charge **while charging**, without a current sensor, by reasoning about the ratio of
open-circuit to tracking voltage, whether the voltage is still rising, and so on. That cannot
really be done: without the current, the charging voltage describes the charger, not the battery.

They are deliberately not ported. What is ported is the part that works:

- a standard resting-voltage table per chemistry, interpolated
- the estimate is **frozen** while the panel is above the battery, rather than following the
  charger up
- slew-limited, so a pump starting does not move it

Here it is **reporting only**, published read-only. In OSPIT `charge_state` also feeds the system
status. `Control_MPPT` measures its own thresholds and never reads it.

---

## 8. Battery health (`mp2.lua` → `Control_Health`)

The method is OSPIT's, and it is a reasonable one for a system with no current sensor. Over a
six-hour window at night:

```
health % = (6 h × av_pwr) / ((SoC at 22:00 - SoC at 04:00) / 100 × ah_batt) × 100
```

| OSPIT | Here |
|---|---|
| `ah_batt` | `batteryhealth/capacity` |
| `av_pwr` | `batteryhealth/load` |
| `pv_watt` | `batteryhealth/panelwatts` |
| `critical_storage_charge_ratio` (5.0) | `CONTROL_HEALTH_MIN_RATIO` |
| the "Healthy" / "Battery level low" / "Energy storage capacity too small" status | `batteryhealth/advice` |

### A flaw in OSPIT's version, fixed here

OSPIT measures from 22:00 to 04:00 and irrigates at 03:00 (`i_hr = 3`). On any night the
irrigation runs, the pump's draw falls inside the measurement window but is not included in
`av_pwr`. The battery then looks much more worn than it is, and only on nights it waters, so the
figure jumps around for no visible reason.

Here the window is discarded if `irrigation/active` is non-zero at any point during it.

### Other differences

- Nothing is reported until a complete, uninterrupted window has passed. OSPIT starts from a
  default of 100.
- A window in which the estimate did not fall is reported as "voided", not as 100 %.
- Here, the storage-ratio advice uses the rated capacity until there is a measured health figure,
  so it is available from the first day.

---

## 9. Not ported

These were left out on purpose, not overlooked:

- The eight state-of-charge heuristics (see [§7](#7-state-of-charge-mp2lua--control_soc)).
- Low-voltage deep sleep is available but not enabled (see
  [§2](#low-voltage-deep-sleep)).
- The runtime overloading of pins 12 and 14 (see [§1](#1-hardware-and-pins)).
- Everything in OSPIT that the library already does a different way: the web server, FTP, telnet,
  the Lua shell, OTA, MQTT, configuration storage and the router scripts.
