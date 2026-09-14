#!/bin/bash
# Regenerate platform.h from platformio.ini.
#
# platform.h is what makes this sketch work in the Arduino IDE, which has no idea what a build
# flag or an environment is: the script turns each [env:...] section's -D flags into #defines
# wrapped in #ifdef ARDUINO_<BOARD>. The ESP32 core puts the sketch directory on the include path,
# so the library's _settings.h picks the file up automatically.
#
# Run this after ANY change to platformio.ini. PlatformIO does not use platform.h, so forgetting
# leaves the two toolchains disagreeing - and only the Arduino one is wrong.
#
# The generator lives in the library, so find the library first: a developer's symlink at
# lib/Frugal-IoT, otherwise whatever PlatformIO downloaded into .pio/libdeps.
set -e
cd "$(dirname "$0")/.."

for candidate in lib/Frugal-IoT .pio/libdeps/*/Frugal-IoT; do
  if [ -f "$candidate/scripts/generate_platform_h.py" ]; then
    echo "Using the generator from $candidate"
    exec "$candidate/scripts/generate_platform_h.py"
  fi
done

echo "Could not find Frugal-IoT." >&2
echo "Either run 'pio run' once so PlatformIO downloads it, or symlink your working copy:" >&2
echo "  ln -s ../../frugal-iot-demo/lib/Frugal-IoT lib/Frugal-IoT" >&2
exit 1
