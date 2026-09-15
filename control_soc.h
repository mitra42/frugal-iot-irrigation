/* Control_SoC - how full is the battery, estimated from its voltage.
 *
 * REPORTING ONLY. Nothing controls anything from this, and `soc` is published read-only and
 * unwireable to keep it that way. A voltage-based estimate is good enough to look at and to graph;
 * it is not good enough to decide when to stop charging, which is what Control_MPPT's own
 * measured thresholds are for.
 *
 * ---------------------------------------------------------------------------------------------
 * Why this is a simple table where OSPIT has eight branches
 *
 * mp2.lua carries eight overlapping heuristics with hand-tuned constants, most of them attempts to
 * guess the state of charge WHILE CHARGING without a current sensor - reasoning about the ratio of
 * open-circuit to tracking voltage, whether the voltage is still rising, and so on. That is the
 * part that cannot really be done: without knowing the current, charging voltage tells you about
 * the charger, not about the battery.
 *
 * So this does the part that does work. A resting lead-acid battery has a genuinely useful
 * voltage-to-charge relationship, and the table below is the standard one. The rest is handled by
 * not pretending:
 *
 *   - while the panel is above the battery, the battery is being charged and its terminal voltage
 *     is elevated. The estimate is FROZEN rather than tracking it up. `charging` says when.
 *   - the published figure is slew-limited, so a pump starting does not move it. It takes several
 *     minutes to travel any distance, which is about right for something that physically changes
 *     over hours.
 *
 * The honest summary, which belongs in front of anyone reading the number: it is most accurate
 * after a quiet night, least accurate in the middle of a sunny day, and a battery whose capacity
 * has faded will read optimistically at every voltage. That last one is what Control_Health is for.
 *
 * ---------------------------------------------------------------------------------------------
 * Lithium
 *
 * LiFePO4's voltage curve is nearly flat between 20% and 90% - about 0.3V across the whole middle
 * of the range, against 1.0V for lead-acid - so a voltage estimate is much weaker, and small
 * calibration errors turn into large percentage errors. The table is still the best available
 * without a current sensor, and it is marked in the UX by the reading simply moving very little.
 * If a lithium installation needs a real figure, the answer is a shunt - Sensor_INA219 already
 * exists - not a better table.
 *
 * Build flags:
 *   CONTROL_SOC_SLEW_PC  (0.05)  most the published figure may move in one cycle, in percent
 */

#ifndef CONTROL_SOC_H
#define CONTROL_SOC_H

#include "control/control.h"
#include "battery_profile.h"

#ifndef CONTROL_SOC_SLEW_PC
  // 0.05%/cycle at a 10s cycle is 18%/hour - slow enough to ignore a pump, fast enough to follow
  // a battery that is genuinely emptying
  #define CONTROL_SOC_SLEW_PC 0.05
#endif

class Control_SoC : public Control {
  public:
    Control_SoC(const char* const id, const char* const name);
    INfloat*  battery;  // Wire from battery/battery, mV
    INfloat*  panel;    // Wire from panel/panel, mV. Unwired means "assume never charging"
    INuint16* profile;  // Battery chemistry, same numbering as Control_MPPT's
    OUTfloat* soc;      // Percent. Read-only on purpose - see the top of this file
    OUTbool*  charging; // True while the panel is above the battery, i.e. while soc is frozen
    void setup() override;
    void periodically() override;
  protected:
    float published = NAN; // The slew-limited figure; NAN until the first reading
    // Percent for this voltage, by linear interpolation of the chemistry's table
    float socForVoltage(float mv, uint16_t chem) const;
};

#endif // CONTROL_SOC_H
