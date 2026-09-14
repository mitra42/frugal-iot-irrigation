/* See sensor_heatsink.h for the diode curve, why the slope is negative, and how to calibrate it */

#include "sensor_heatsink.h"

#ifdef OSPIT_HEATSINK_PIN

#include "Frugal-IoT.h"

// offset and scale are left at 0 and 1: convert() is overridden outright, because a line with a
// negative slope through a point at 25 C is clearer written as that than as an offset and a scale.
Sensor_Heatsink::Sensor_Heatsink(const char* const id, const char* const name, uint8_t pin, bool retain)
: Sensor_Analog(id, name, pin, 1,
                DEFAULT_heatsink_heatsink_min, DEFAULT_heatsink_heatsink_max,
                0, 1.0f, DEFAULT_heatsink_heatsink_color, retain)
{
  output->unit = "C";
}

int Sensor_Heatsink::readInt() {
  // Millivolts with the factory calibration applied, NOT Sensor_Analog's raw analogRead()
  return analogReadMilliVolts(pin);
}

bool Sensor_Heatsink::validate(int mV) {
  return mV < OSPIT_HEATSINK_MV_DISCONNECTED; // false publishes "nan" - no sensor, rather than -305C
}

float Sensor_Heatsink::convert(int mV) {
  // Falls as it warms, so the reading is subtracted from the 25 C point, not added to it
  return 25.0f + ((float)(OSPIT_HEATSINK_MV_AT_25C - mV) / (float)OSPIT_HEATSINK_MV_PER_C);
}

#endif // OSPIT_HEATSINK_PIN
