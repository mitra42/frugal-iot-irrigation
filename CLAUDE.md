# Frugal-IoT Irrigation — notes for working on this repo

This is an **application**, not a library. It was `examples/ospit` inside the Frugal-IoT library
until it was split out, so that someone working on irrigation is not also looking at every sensor
driver in the world.

Read [the library's CLAUDE.md](lib/Frugal-IoT/CLAUDE.md) first — the IO/wiring model, sleep-safe
timers, invalid-reading propagation and the schema pipeline all live there and are assumed here.

## Coding preferences

- **No mid-function early returns** — wrap the remaining body in an `if` instead. Early returns
  are easy to miss.
- Comments explain *why*, and especially why the obvious alternative was rejected. Several
  decisions here look arbitrary until you know what OSPIT did and what went wrong with it.

## Layout, and why it is flat

Everything is at the top level, next to `frugal-iot-irrigation.ino`. That is not untidiness — it
is the only layout that builds in **both** toolchains:

- **Arduino IDE** needs a `.ino` whose name matches the folder, and compiles it together with the
  `.cpp`/`.h` files beside it. It ignores every subdirectory except `src/`, so `lib/`, `data/`,
  `scripts/` and `.pio/` are invisible to it.
- **PlatformIO** is told `src_dir = .` and compiles the same set.

`platform.h` is generated from `platformio.ini` by `scripts/generate_platform_h.bash` and is how
the Arduino IDE learns the pins, since it has no concept of a build environment. **Re-run it after
any change to `platformio.ini`** — PlatformIO does not read `platform.h`, so forgetting leaves the
two toolchains disagreeing, and only the Arduino one is wrong.

`defaults.h` is NOT here. It belongs to the library and ships with it; the `DEFAULT_*` macros this
application uses come from the schema in `frugal-iot-server` via
`frugal-iot-logger/scripts/generate-defaults.js`.

## The library

`platformio.ini` depends on the library's `ospit-p1` branch from GitHub, so a fresh clone builds
with nothing set up. That is the committed default because the person most likely to hit it first
is a tester, not us.

### Building against a local library

A symlink at `lib/Frugal-IoT` alone is NOT enough - PlatformIO uses the declared `lib_deps` copy
in preference. Two steps:

```bash
ln -s ../../frugal-iot-demo/lib/Frugal-IoT lib/Frugal-IoT
printf '[common]\nlib_deps =\n' > platformio-local.ini
```

`platformio-local.ini` is picked up by `extra_configs` in `platformio.ini` and is gitignored;
PlatformIO ignores the line when the file is absent, so nobody else is affected. Blanking
`common.lib_deps` removes the git dependency and leaves the symlink as the only copy. Transitive
dependencies still resolve from the library's own `library.json` - which is why this works where
`lib_deps = symlink://...` does not.

Check which one you actually built against: the dependency list at the start of a build shows
`Frugal-IoT @ 0.1.6` for the symlink and `Frugal-IoT @ 0.1.6+sha.xxxxxxx` for the git copy.

Beware `src_dir = .`: without the `build_src_filter` line in `platformio.ini`, PlatformIO would
compile everything under `lib/` as project source, including the library's own examples and their
downloaded dependencies. It fails in a very confusing way.

Use the symlink when a change needs both repos. **A change that is generally useful belongs in the
library, not here** — ask which branch it should go on rather than growing a private copy. The
split so far: `Control_Irrigation`, `Control_Sector`, `Sensor_Tank` and the OLED pages are here
because they are expected to be re-coded for the next application; `Sensor_SoilModbus`,
`System_RS485`, `Actuator_Analog` and the `IN`/`OUT` setters are in the library because they are
not.

## What is here

| File | What |
|---|---|
| `frugal-iot-irrigation.ino` | wiring: which sensors, which actuators, what is connected to what |
| `control_irrigation.{h,cpp}` | `Control_Irrigation` (the sequencer) and `Control_Sector` |
| `sensor_tank.{h,cpp}` | resistive float sender as a percentage |
| `control_oled_ospit.{h,cpp}` | three display pages in a carousel |
| `sensor_heatsink.{h,cpp}` | heatsink temperature from a diode pair, if the board has one |
| `control_mppt.{h,cpp}` | solar charge control - fractional-Voc tracking; the board-revision Vmpp cascade lives here |
| `platformio.ini` | the pin map for each board, and every build flag |
| `TESTING.md` | commissioning a real board, written for someone who is not a developer |
| `HARDWARE-QUESTIONS.md` | things only someone holding the board can answer |

## Things that are the way they are on purpose

- **A sector with no reading is skipped and its valve is never driven.** In OSPIT this was the
  board's configuration mechanism — its third output was a valve or a USB supply depending on
  whether probe 3 answered. Here a sector exists because you constructed one, but the skip stays.
- **One sleep-safe timer does two jobs** — the current sector's maximum open time while a run is
  going, the absolute start of the next run while idle. They are never both needed, and the timer
  array is in `RTC_DATA_ATTR`, so the schedule survives deep sleep with no state of our own.
- **`closeAll()` runs once per cycle**, pushing every valve closed whether or not this control
  believes it opened it. Without it a valve opened by hand from the portal would never be closed,
  because `OUTbool::set()` only sends on a change.
- **Modbus slave ids start at 2.** Address 1 is the factory default every probe ships with and has
  to keep meaning "not yet provisioned".
- **The MPPT DAC is an inverse throttle** — a HIGHER step asks for a higher panel voltage, leaves
  the panel nearer open circuit, and so charges LESS. The safe fallback is therefore the top of the
  range, not zero, and every path in `Control_MPPT` that is not a deliberate decision to charge
  ends there. Getting this backwards means charging hardest when something has gone wrong.
- **`mppt/automatic` is off by default.** None of the charge control has run on hardware. It stays
  off until someone has been through `TESTING.md`; the setting is persisted, so it is turned on
  once.

## Testing without hardware

`pio run` for both environments is the compile check. Beyond that, the logic that is worth testing
is pure: the schedule arithmetic and the sequencer state machine have been host-tested by copying
them into a small C++ program with the library types stubbed out. That found two real bugs, and is
much faster than reasoning about it. Do that again rather than trusting a reading of the code.

Verify what actually linked with `nm` on the ELF rather than trusting a zero exit code — a
conditional compile that silently did nothing looks exactly like success.
