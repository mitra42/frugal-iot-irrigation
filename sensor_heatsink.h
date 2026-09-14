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
 * OSPIT computes the same line differently, from raw ADC counts scaled by a hand-calibrated
 * reference voltage and a 6 dB attenuator setting:
 *
 *     V = ((raw / 4095) * (Vref * 0.002)) / 1.06
 *     T = -50 + ((1.273 - V) / 0.0048)
 *
 * which is temperature = 215.2 - 0.2083 x millivolts, i.e. 913 mV at 25 C and 4.8 mV per degree -
 * the defaults below. We do not copy their arithmetic because we do not read raw counts:
 * analogReadMilliVolts() applies the chip's factory calibration and already accounts for the
 * attenuator, so Vref, the 0.002 and the 1.06 have no equivalent here. See the note on linearity
 * in the library's sensor/voltage.h.
 *
 * ---------------------------------------------------------------------------------------------
 * Calibrating it
 *
 * The two constants are build flags because they are the sort of thing that differs between
 * boards and is easy to measure. With the board cold and at a known room temperature, read
 * <id>/<id> and compare: if it is out by a constant number of degrees, adjust
 * OSPIT_HEATSINK_MV_AT_25C by 4.8 mV for each degree of error. The slope is a property of silicon
 * and is unlikely to need changing.
 *
 * Build flags:
 *   OSPIT_HEATSINK_PIN            REQUIRED, or this class is not compiled at all
 *   OSPIT_HEATSINK_MV_AT_25C      (913)  sensor voltage at 25 C
 *   OSPIT_HEATSINK_MV_PER_C       (4.8)  how far it falls per degree - positive number, the sign
 *                                        is handled below
 *   OSPIT_HEATSINK_MV_DISCONNECTED (2500) at or above this, assume no sensor is connected
 */

#ifndef SENSOR_HEATSINK_H
#define SENSOR_HEATSINK_H

#ifdef OSPIT_HEATSINK_PIN

#include "sensor/analog.h"

#ifndef OSPIT_HEATSINK_MV_AT_25C
  #define OSPIT_HEATSINK_MV_AT_25C 913
#endif
#ifndef OSPIT_HEATSINK_MV_PER_C
  #define OSPIT_HEATSINK_MV_PER_C 4.8
#endif
#ifndef OSPIT_HEATSINK_MV_DISCONNECTED
  // 2500 mV would be about -305 C, so nothing real can reach it. An input with nothing connected
  // floats up towards the supply rail; OSPIT treats the same condition as "sensor missing, or
  // connected the wrong way round".
  #define OSPIT_HEATSINK_MV_DISCONNECTED 2500
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

#endif // OSPIT_HEATSINK_PIN
#endif // SENSOR_HEATSINK_H
