# Frugal-IoT Irrigation

Solar-powered irrigation for small farms: a set of sectors is watered one at a time, once a day,
each until its soil reaches a target moisture or a time limit runs out — with tank-level and
battery interlocks that stop the whole run.

It is a port of the irrigation half of [OSPIT](https://github.com/mitra42/ospit) (NodeMCU Lua on
the FF-ESP32-OpenMPPT solar charge controller) onto the
[Frugal-IoT](https://github.com/mitra42/frugal-iot) library, which brings WiFi setup from a phone,
MQTT, a web dashboard, graphing, and over-the-air updates.

## What it does today

- **Up to N irrigation sectors**, run strictly in order, one valve open at a time.
- **Soil moisture per sector** from RS485/Modbus probes sharing one bus.
- A sector whose probe is **not reporting is skipped**, and its valve is never opened — watering
  with no feedback is worse than not watering.
- **Tank level** from a float sender, with two thresholds: one to begin a run, a lower one to
  abort it. "No tank sensor fitted" is kept distinct from "tank empty".
- **Battery interlock** — irrigation stops below a configurable voltage and resumes above a higher
  one.
- Optional **pump** (driven with the valves) and **load output** (switched by the battery
  interlock) on separate pins.
- Optional **OLED**: battery, then the sector moistures and tank, then IP/WiFi/MQTT.

- **Solar charge control** — two-stage MPPT tracking with temperature compensation, a hard
  thermal cut-out, and battery-type profiles.
- **Battery reporting** — state of charge and a health estimate, both derived rather than measured
  and clearly labelled as such.

**None of the charge control has run on real hardware yet**, so it ships switched off:
`mppt/automatic` defaults to false and is turned on once, after the checks in
[TESTING.md](TESTING.md).

## Hardware

Two boards are supported out of the box. See `platformio.ini` for the full pin list.

| Board | Notes |
|---|---|
| **FF-ESP32-OpenMPPT** | the solar charge controller OSPIT runs on. Pin assignments are OSPIT's own |
| **Lolin S2 Mini** | the same application on a plain dev board, no charge hardware |

You will also need: 12 V valves and a driver for them, one Modbus soil probe per sector, an RS485
transceiver, and optionally a tank float sender and a pump.

## Building

### PlatformIO (recommended)

```bash
pio run --environment ff_openmppt          # compile
pio run --target upload -e ff_openmppt     # flash
pio run --target uploadfs -e ff_openmppt   # upload data/ (WiFi passwords etc)
```

The Frugal-IoT library is fetched automatically from the `ospit-p1` branch, so a fresh clone needs
nothing set up. If you are changing the library at the same time, see "Building against a local
library" in [CLAUDE.md](CLAUDE.md).

### Arduino IDE

1. Install **Frugal-IoT** from Library Manager (or clone it into your `libraries/` folder).
2. Install the ESP32 board support package.
3. Open `frugal-iot-irrigation.ino` — the whole repository folder is the sketch folder.
4. Under **Tools > Board**, pick the board you have. `platform.h` supplies the right pins for it;
   if your board has no section there, compiling stops with a message telling you so.

`platform.h` is generated from `platformio.ini`. If you change pins there, re-run
`scripts/generate_platform_h.bash`, or the two toolchains will disagree.

## First run

1. Flash, then power up. The device makes its own WiFi network — connect a phone to it.
2. A setup page opens (or browse to `192.168.4.1`). Give it your WiFi name and password.
3. **Irrigation starts switched off.** Something that opens water valves unattended should not
   begin doing so just because it was flashed. Turn it on in the **Irrigation** section, and set
   the start time while you are there.

`TESTING.md` walks through commissioning a real board step by step, including calibrating the tank
and the battery. `HARDWARE-QUESTIONS.md` is a list of things we need someone with the hardware to
look at.

Because not everyone has sun, a multimeter and a fortnight, `docs/` holds three ready-made plans —
[bench](docs/plan-bench.md), [sunny half-day](docs/plan-sunny-session.md),
[days of running](docs/plan-long-run.md) — each a short ordered list of which Parts of `TESTING.md`
to do. Question 9 of `HARDWARE-QUESTIONS.md` picks one. [docs/sleep-test.md](docs/sleep-test.md) is
the one test that needs its own build, on the `sleep-test` branch.

## Licence

Same as Frugal-IoT. The OSPIT algorithms this is derived from are GPL-2.0-or-later,
Copyright (C) 2026 Corinna 'Elektra' Aichele.
