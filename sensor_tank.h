/* Sensor_Tank - water tank level, in percent, from a resistive float sender.
 *
 * ---------------------------------------------------------------------------------------------
 * The circuit
 *
 * A float sender is a variable resistor whose resistance follows the float. Wire it as the lower
 * half of a voltage divider, with a fixed resistor from 3v3 to the ADC pin and the sender from the
 * pin to ground:
 *
 *     3v3 ---[ R fixed ]---+--- ADC pin
 *                          |
 *                     [ R sender ]
 *                          |
 *                         GND
 *
 * The pin then sits at 3.3 x Rsender / (Rsender + Rfixed), so the raw ADC reading rises and falls
 * with the level. Senders come in both directions (low resistance at empty or at full), and either
 * works: calibration just maps whatever the two ends read onto 0% and 100%.
 *
 * Choose Rfixed so that "full" reads well below the top of the ADC range. That leaves a gap at the
 * top for the next case.
 *
 * ---------------------------------------------------------------------------------------------
 * "No sender" is not "empty tank"
 *
 * With the sender unplugged or its cable broken, nothing pulls the pin down, so the fixed resistor
 * pulls it up to 3v3, near the top of the range. No connected sender can read that high. So:
 *
 *   raw >= SENSOR_TANK_RAW_DISCONNECTED -> validate() fails -> publishes "nan"
 *   otherwise                           -> a level, 0..100 %
 *
 * Control_Irrigation relies on the difference: "nan" means there is no tank sensor, which must not
 * block irrigation, while a genuine low level must stop it. Anything using this sensor should make
 * the same distinction.
 *
 * ---------------------------------------------------------------------------------------------
 * Converting to percent
 *
 * Sensor_Analog computes (raw - offset) x scale. Here offset is the empty reading and scale is
 * 100 / (full - empty), so the empty reading becomes 0% and the full one 100%. The result is
 * clamped to 0..100, so a sender slightly out of calibration reads 100% rather than 103%.
 *
 * ---------------------------------------------------------------------------------------------
 * Calibrating it
 *
 * From the captive portal, which is easiest and is persisted: with the tank empty press Tare, then
 * with it full enter 100. See captiveLines() below.
 *
 * Or at build time, with the raw counts measured at both ends:
 *   SENSOR_TANK_RAW_EMPTY         (0)     counts with the tank empty
 *   SENSOR_TANK_RAW_FULL          (703)   counts with the tank full
 *   SENSOR_TANK_RAW_DISCONNECTED  (3000)  at or above this, the sender is assumed missing
 *
 * The defaults are calculated, not measured, for a 0 ohm (empty) to 170 ohm (full) sender with an
 * 820 ohm fixed resistor: full is 0.567 V, about 703 counts of a 12-bit ADC at 11 dB attenuation.
 * That is the sender OSPIT uses; its own code only detects whether the sender is present, not the
 * level - see OSPIT_COMPARISON.md.
 *
 * Published as <id>/<id>, e.g. "tank/tank", per Sensor_Float's one-output convention.
 */

#ifndef SENSOR_TANK_H
#define SENSOR_TANK_H

#include "sensor/analog.h"

#ifndef SENSOR_TANK_RAW_EMPTY
  #define SENSOR_TANK_RAW_EMPTY 0
#endif
#ifndef SENSOR_TANK_RAW_FULL
  #define SENSOR_TANK_RAW_FULL 703
#endif
#ifndef SENSOR_TANK_RAW_DISCONNECTED
  #define SENSOR_TANK_RAW_DISCONNECTED 3000
#endif

class Sensor_Tank : public Sensor_Analog {
  public:
    Sensor_Tank(const char* const id, const char* const name, uint8_t pin, bool retain,
                int raw_empty = SENSOR_TANK_RAW_EMPTY,
                int raw_full = SENSOR_TANK_RAW_FULL,
                int raw_disconnected = SENSOR_TANK_RAW_DISCONNECTED);
  protected:
    int raw_disconnected;
    bool validate(int v) override;
    float convert(int v) override;
    /* Two-point calibration from the portal, the same mechanism Sensor_Soil offers.
     *
     * Sensor_Analog already has it all: writing 0 to <id>/output tares (the current raw reading
     * becomes 0%), writing any other number calibrates (scale is set so the current reading means
     * that number), and both offset and scale are persisted. The constructor's raw_empty/raw_full
     * are only the starting point.
     */
    void captiveLines(AsyncResponseStream* response) override;
};

#endif // SENSOR_TANK_H
