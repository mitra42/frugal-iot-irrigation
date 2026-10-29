# Frugal-IoT Irrigation

This project is intended to provide solar-powered irrigation for small farms. A set of sectors is watered one at a time, once a day. 

The default version waters each sector until its soil reaches a target moisture or a time limit runs out, but it can be 
subclased for more complex per-sector requirements. 

There are tank-level and battery interlocks that stop the whole run, and this also can be customized. 

It is built on top of Frugal-IoT and both the irrigation and MPPT components draw part of their
inspiration from [OSPIT](https://www.apc.org/en/news/meet-ospit-sustainable-energy-and-irrigation-solution-community-networks)
(Lua on the FF-ESP32-OpenMPPT solar charge controller)
- [OSPIT_COMPARISON.md](OSPIT_COMPARISON.md) describes what is different and why.

This release should work in four hardware environments.

* The "FF-ESP32-OpenMPPT solar charge controller" in which case it will run MPPT 
* Our custom board in `hardware` with onboard relays and RS485. 
* A simple off the shelf dev board with hardwired sensors, just edit board definitions in 
  platformio.ini and `wiring` in frugal-iot-irrigation.ino
* A distributed sensor environment, just change the `wiring` in frugal-iot-irrigation.ino 
  to point at the distributed sensors

[Frugal-IoT](https://github.com/mitra42/frugal-iot) brings: WiFi setup from a phone; MQTT; web and phone dashboards; graphing and over-the-air updates.  

Any of the other features of Frugal-IoT can be easily added to your sketch including, off-internet operation, remote sensors, LoRa, or a wide range of other sensors for example for weather. 

## What it does today

- **Up to N irrigation sectors**, run strictly in order, one valve open at a time.
- **Soil moisture per sector** from RS485/Modbus probes sharing one bus, or from simple
  analog capacitive soil sensors.
- Anomaly handling - for instance, a sector whose probe is **not reporting is skipped**
- **Tank level** from a float sender, with two thresholds: one to begin a run, a lower one to
  abort it. "No tank sensor fitted" is kept distinct from "tank empty".
- **Battery interlock** - irrigation stops below a configurable voltage and resumes above a higher
  one.
- Optional **pump** (driven with the valves) and **load output** (e.g. for a router) (switched by the
  battery interlock) on separate pins.
- Optional **OLED**: Displays battery; sector moistures; tank and communicationss status.
- **Solar charge control** - two-stage MPPT tracking with temperature compensation, a hard
  thermal cut-out, and battery-type profiles.
- **Battery reporting** - state of charge and a health estimate inferred from voltage drop.

## Status

**None of the charge control has run on real hardware yet**, so it ships switched off. 

Run the checks in [TESTING.md](TESTING.md) and then turn on `mppt/automatic`

`HARDWARE-QUESTIONS.md` is a list of things we need someone with the OSPIT hardware to
look at and confirm.

## Hardware

Three boards are supported out of the box. See `platformio.ini` for the full pin list.

| Board | Notes |
|---|---|
| **FF-ESP32-OpenMPPT** | the solar charge controller OSPIT runs on. Pin assignments are OSPIT's own |
| **Frugal IoT Irrigation v0.1** | a custom board with Relays, RS485 and battery charging |
| **Lolin S2 Mini** | the same application on a plain dev board, no charging hardware.|
| other | Setting up support for most other boards is trivial, look in the [Frugal-IoT/examples/all](https://github.com/mitra42/frugal-iot/blob/main/examples/all/platformio.ini) for example configuration for many popular boards or [add a new issue](https://github.com/mitra42/frugal-iot-irrigation/issues/new) in this repo.

The `FF-ESP32-OpenMPTT` board has the needed functionality, but is going to be a significantly more expensive solution than the `Frugal IoT Irrigation v0.1` paired, if neccessary, with an off-the-shelf MPPT controller.

You will also need: 12 V valves and a driver for them, one Modbus soil probe per sector, an RS485
transceiver, and optionally a tank float sender and a pump.

The hardware in `hardware` is available as a full set of Gerber and fabrication files, they are designed for use at SLCPCB but could be adapted to any manufacturer (and we would
be happy to add files for other manufacturers). Note this hardware has (as of Oct 2026) yet to be built and tested. 

## Building

### PlatformIO (recommended)

```bash
pio run --environment ff_openmppt          # compile
pio run --target upload -e ff_openmppt     # flash
pio run --target uploadfs -e ff_openmppt   # upload data/ (WiFi passwords etc)
```

The Frugal-IoT library is fetched automatically, so a fresh clone needs nothing set up. 
If you are changing the library at the same time, 
see "Building against a local library" in [CLAUDE.md](CLAUDE.md).

### Arduino IDE

1. Install **Frugal-IoT** from Library Manager (or clone it into your `libraries/` folder).
2. Install the ESP32 board support package.
3. Open `frugal-iot-irrigation.ino` - the whole repository folder is the sketch folder.
4. Under **Tools > Board**, pick the board you have. `platform.h` supplies the right pins for it;
   if your board has no section there, compiling stops with a message telling you so.

`platform.h` is generated from `platformio.ini`. If you change pins there, re-run
`scripts/generate_platform_h.bash`, or the two toolchains will disagree.

## First run

1. Flash, then power up. The device makes its own WiFi network - connect a phone to it.
2. A setup page opens (or browse to `192.168.4.1`). Give it your WiFi name and password.
3. **Irrigation starts switched off.** Turn it on in the **Irrigation** section, and set
   the start time while you are there.

`TESTING.md` walks through commissioning a real board step by step, including calibrating the tank
and the battery. `HARDWARE-QUESTIONS.md` is a list of things we need someone with the OSPIT hardware to look at.

Because not everyone has sun, a multimeter and a fortnight, `docs/` holds three ready-made plans —
[bench](docs/plan-bench.md), [sunny half-day](docs/plan-sunny-session.md),
[days of running](docs/plan-long-run.md) — each a short ordered list of which Parts of `TESTING.md`
to do. Question 9 of `HARDWARE-QUESTIONS.md` picks one. [docs/sleep-test.md](docs/sleep-test.md) is
the one test that needs its own build, on the `sleep-test` branch.

## Licence

Same as Frugal-IoT. The OSPIT algorithms parts of this are derived from are GPL-2.0-or-later,
Copyright (C) 2026 Corinna 'Elektra' Aichele.
