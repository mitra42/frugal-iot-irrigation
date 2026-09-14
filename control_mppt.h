/* Control_MPPT - solar charge control for the FF-ESP32-OpenMPPT board.
 *
 * AT THIS STAGE IT DOES NOT TRACK ANYTHING. All it does is let a person set the charge controller
 * by hand and see what happens, which is step P5.2 of the plan. The tracking algorithm (an
 * open-circuit-voltage sweep, then a regulation loop against a temperature-compensated charge-end
 * voltage) is P5.3 and P5.4, and is deliberately not written until the manual version has been
 * driven on real hardware - a charge controller working from an unverified reading damages
 * batteries, and nobody involved has the board yet.
 *
 * ---------------------------------------------------------------------------------------------
 * What the DAC does, and which way round it is
 *
 * The board takes an analog voltage from the ESP32's DAC and uses it as the voltage the solar
 * panel should be held at - the "maximum power point" setpoint. A panel produces most power at a
 * particular voltage, below its open-circuit voltage; holding it there is the whole job of an MPPT
 * charger.
 *
 * The number is therefore an INVERSE THROTTLE, which is easy to get backwards:
 *
 *     LOW  step -> low target voltage  -> the panel is pulled down hard -> MORE current
 *     HIGH step -> high target voltage -> the panel is left near open circuit -> LESS current
 *
 * So the SAFE value - the one that charges least, and the one to fall back on when anything is
 * unknown or a reading is missing - is the HIGHEST step, not zero. CONTROL_MPPT_SAFE_STEP is
 * written at startup and is what a later fault path should return to.
 *
 * ---------------------------------------------------------------------------------------------
 * The step-to-volts mapping, which is a guess until someone measures it
 *
 * OSPIT maps its configured panel-voltage range onto the DAC like this:
 *
 *     dac = (Vmpp - Vmpp_min) / ((Vmpp_max - Vmpp_min) / 285)
 *
 * Note 285, not 255. The DAC only reaches 255, so on OSPIT's own numbers the top tenth of the
 * range is unreachable. That may be a deliberate correction for a transfer function that is not
 * quite linear, or it may be a mistake - we cannot tell from the code. It is CONTROL_MPPT_DAC_SPAN
 * here so it can be changed without hunting for it.
 *
 * This is why `step` is an input and `vmpp` is an OUTPUT. The tester sets a step, which is
 * unambiguous, and the board reports what panel voltage we PREDICT that step asks for. Comparing
 * that prediction against a meter - see Part H of TESTING.md - is what turns the mapping from a
 * guess into a measurement. If we asked the tester to set a voltage instead, a wrong mapping would
 * quietly corrupt the very table meant to reveal it.
 *
 * Build flags:
 *   OSPIT_MPPT_DAC_PIN         REQUIRED, or none of this is compiled
 *   CONTROL_MPPT_VMPP_MIN  }   the panel-voltage range this board's hardware can ask for.
 *   CONTROL_MPPT_VMPP_MAX  }   Give BOTH or NEITHER - see the #error below.
 *   CONTROL_MPPT_BOARD_FF_1_0 / _1_1   pick a known board revision instead of the two above.
 *                              With none of these set, the FF v1.2 figures are used - the most
 *                              recent board, so a new one needs no flags at all.
 *   CONTROL_MPPT_DAC_SPAN      (285)  see above
 *   CONTROL_MPPT_SAFE_STEP     (highest step) what to write when nothing else is known
 */

#ifndef CONTROL_MPPT_H
#define CONTROL_MPPT_H

#ifdef OSPIT_MPPT_DAC_PIN

#include "control/control.h"

/* Defining one of the pair and not the other would silently mix your value with a default, and
 * the result would look plausible. In the preprocessor defined() is 1 or 0, so this compares them.
 */
#if defined(CONTROL_MPPT_VMPP_MIN) != defined(CONTROL_MPPT_VMPP_MAX)
  #error Define both CONTROL_MPPT_VMPP_MIN and CONTROL_MPPT_VMPP_MAX, or neither
#endif

#if !defined(CONTROL_MPPT_VMPP_MIN)
  #if defined(CONTROL_MPPT_BOARD_FF_1_0)
    // Cannot track a panel below 14.45V, which a hot 36-cell panel can fall to
    #define CONTROL_MPPT_VMPP_MIN 14.45
    #define CONTROL_MPPT_VMPP_MAX 23.80
  #elif defined(CONTROL_MPPT_BOARD_FF_1_1)
    // Reaches highest, so it suits a 60-cell / 24V-nominal panel
    #define CONTROL_MPPT_VMPP_MIN 13.25
    #define CONTROL_MPPT_VMPP_MAX 27.20
  #else
    // FF-ESP32-OpenMPPT v1.2 - the most recent, and the compromise between the two above
    #define CONTROL_MPPT_VMPP_MIN 12.86
    #define CONTROL_MPPT_VMPP_MAX 25.15
  #endif
#endif

#ifndef CONTROL_MPPT_DAC_SPAN
  #define CONTROL_MPPT_DAC_SPAN 285
#endif

class Control_MPPT : public Control {
  public:
    Control_MPPT(const char* const id, const char* const name);
    /* The DAC step, 0 to steps-1. Set by hand for now.
     *
     * TODO when the tracking algorithm arrives it will write this itself, and will need an
     * auto/manual input beside it so a person can still take over. Not added yet because there is
     * nothing to take over FROM, and an input that does nothing is worse than no input.
     */
    INuint16* step;
    OUTfloat* vmpp;     // The panel voltage we PREDICT that step asks for - a guess, see above
    OUTfloat* dacvolts; // Wire to an Actuator_Analog's set path; volts at the DAC pin
    void setup() override;
  protected:
    void act() override;
    // Highest step, i.e. least charge current. See "which way round it is" above.
    uint16_t safeStep() const;
    float vmppForStep(uint16_t s) const;
    float voltsForStep(uint16_t s) const;
    uint16_t maxStep() const;
};

#endif // OSPIT_MPPT_DAC_PIN
#endif // CONTROL_MPPT_H
