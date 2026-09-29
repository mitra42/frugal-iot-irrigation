#!/bin/bash
# Regenerate platform.h from platformio.ini.
#
# platform.h is what makes this sketch work in the Arduino IDE, which has no idea what a build
# flag or an environment is: the script turns each [env:...] section's -D flags into #defines
# wrapped in #ifdef ARDUINO_<BOARD>. The ESP32 core puts the sketch directory on the include path,
# so the library's _settings.h picks the file up automatically.
#
# Run this after ANY change to platformio.ini. PlatformIO does not use platform.h, so forgetting
# leaves the two toolchains disagreeing - and only the Arduino one is wrong. scripts/release.zsh
# runs it too.
#
# The generator is a copy of the library's scripts/generate_platform_h.py, kept identical so the
# two can be copied either way. --esp32 because every board here is an ESP32, so there is no
# ESP8266 globals file to write; --no-readme because README.md is written by hand.
set -e
cd "$(dirname "$0")/.."
exec python3 scripts/generate_platform_h.py --esp32 --no-readme
