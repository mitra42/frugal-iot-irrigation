/* Heatsink temperature from a pair of forward-biased diodes on an ADC pin.
 *
 * The FF-OpenMPPT board measures how hot its own heatsink is, so that the charge voltage can be
 * reduced before anything is damaged. There appear to be two ways it does this depending on the
 * board, and this class is one of them:
 *
 *   - a DS18B20 on the 1-Wire bus (use Sensor_DS18B20 with id "pcbtemp"), or
 *   - two 1N4148 diodes in series, fed through 39k, read as an analog voltage - this class.
 *
 * We do not know which is fitted on any given board, so both are compiled only when their pin is
 * defined. See question 4 in HARDWARE-QUESTIONS.md. It is possible for both to be present.
 *
 * ---------------------------------------------------------------------------------------------
 * How the number is arrived at
 *
 * A silicon diode's forward voltage falls as it gets hotter, by roughly 2 mV per degree. Two in
 * series double that, so the reading moves about 4.8 mV per degree and - this is the part that
 * surprises people - it moves DOWNWARDS as the heatsink warms up. Hence a negative slope.
 *
 * So the conversion is a straight line through one known point:
 *
 *     temperature = 25 + (mV_at_25C - mV) / mV_per_C
 *
 * The defaults below are OSPIT's line, re-expressed in calibrated millivolts rather than raw counts
 * (see OSPIT_COMPARISON.md) - analogReadMilliVolts() already accounts for the attenuator. See the
 * note on linearity in the library's sensor/voltage.h.
 *
 * ---------------------------------------------------------------------------------------------
 * Calibrating it
 *
 * The two constants are build flags because they are the sort of thing that differs between
 * boards and is easy to measure. With the board cold and at a known room temperature, read
 * <id>/<id> and compare: if it is out by a constant number of degrees, adjust
 * SENSOR_HEATSINK_MV_AT_25C by 4.8 mV for each degree of error. The slope is a property of silicon
 * and is unlikely to need changing.
 *
 * Build flags:
 *   SENSOR_HEATSINK_PIN            REQUIRED, or this class is not compiled at all
 *   SENSOR_HEATSINK_MV_AT_25C      (913)  sensor voltage at 25 C
 *   SENSOR_HEATSINK_MV_PER_C       (4.8)  how far it falls per degree - positive number, the sign
 *                                        is handled below
 *   SENSOR_HEATSINK_MV_DISCONNECTED (2500) at or above this, assume no sensor is connected
 */

#ifndef SENSOR_HEATSINK_H
#define SENSOR_HEATSINK_H

#ifdef SENSOR_HEATSINK_PIN

#include "sensor/analog.h"

#ifndef SENSOR_HEATSINK_MV_AT_25C
  #define SENSOR_HEATSINK_MV_AT_25C 913
#endif
#ifndef SENSOR_HEATSINK_MV_PER_C
  #define SENSOR_HEATSINK_MV_PER_C 4.8
#endif
#ifndef SENSOR_HEATSINK_MV_DISCONNECTED
  // 2500 mV would be about -305 C, so nothing real can reach it. An input with nothing connected
  // (or connected the wrong way round) floats up towards the supply rail.
  #define SENSOR_HEATSINK_MV_DISCONNECTED 2500
#endif

class Sensor_Heatsink : public Sensor_Analog {
  public:
    Sensor_Heatsink(const char* const id, const char* const name, uint8_t pin, bool retain);
  protected:
    // Calibrated millivolts, not raw counts - see the note above
    int readInt() override;
    bool validate(int mV) override;
    float convert(int mV) override;
};

#endif // SENSOR_HEATSINK_PIN
#endif // SENSOR_HEATSINK_H
