/* See control_mppt.h - manual control only at this stage, and note that the DAC is an inverse
 * throttle so the SAFE value is the highest step, not zero.
 */

#include "control_mppt.h"

#ifdef OSPIT_MPPT_DAC_PIN

#include "Frugal-IoT.h"
#include "actuator/analog.h" // for ACTUATOR_ANALOG_STEPS and ACTUATOR_ANALOG_VREF

Control_MPPT::Control_MPPT(const char* const id, const char* const name)
: Control(id, name, std::vector<IN*>{}, std::vector<OUT*>{}),
  // Starts at the safe end. The constructor cannot call maxStep() before the base is built, so
  // the initial value is set in setup() instead - this is only a placeholder.
  step(new INuint16(id, "step", "DAC step", 0,
    DEFAULT_mppt_step_min, DEFAULT_mppt_step_max,
    DEFAULT_mppt_step_min, DEFAULT_mppt_step_max, DEFAULT_mppt_step_color, false)),
  vmpp(new OUTfloat(id, "vmpp", "Panel target", NAN, 2,
    DEFAULT_mppt_vmpp_min, DEFAULT_mppt_vmpp_max, DEFAULT_mppt_vmpp_color, false)),
  dacvolts(new OUTfloat(id, "dacvolts", "DAC volts", 0, 3,
    DEFAULT_mppt_dacvolts_min, DEFAULT_mppt_dacvolts_max, DEFAULT_mppt_dacvolts_color, true))
{
  inputs.push_back(step);
  outputs.push_back(vmpp);
  outputs.push_back(dacvolts);
}

// One less than the number of levels the hardware has - ACTUATOR_ANALOG_STEPS is 256 on a real
// DAC, or 2^bits on a board driving this through PWM instead.
uint16_t Control_MPPT::maxStep() const {
  return (uint16_t)(ACTUATOR_ANALOG_STEPS - 1);
}

#ifndef CONTROL_MPPT_SAFE_STEP
  #define CONTROL_MPPT_SAFE_STEP maxStep()
#endif

uint16_t Control_MPPT::safeStep() const {
  return CONTROL_MPPT_SAFE_STEP;
}

/* The panel voltage this step asks the hardware for.
 *
 * Divided by CONTROL_MPPT_DAC_SPAN, which is 285 rather than 255 - OSPIT's number, and the reason
 * the top of the range is unreachable. See the header; this is a prediction to be checked against
 * a meter, not a measurement.
 */
float Control_MPPT::vmppForStep(uint16_t s) const {
  return (float)CONTROL_MPPT_VMPP_MIN
       + ((float)s * ((float)CONTROL_MPPT_VMPP_MAX - (float)CONTROL_MPPT_VMPP_MIN)
          / (float)CONTROL_MPPT_DAC_SPAN);
}

// Actuator_Analog is driven in volts, not steps, so convert - and do it the same way it does, so
// asking for step N really writes step N rather than N-1 through a rounding difference.
float Control_MPPT::voltsForStep(uint16_t s) const {
  return ((float)ACTUATOR_ANALOG_VREF * (float)s) / (float)maxStep();
}

void Control_MPPT::setup() {
  // Least charge current until someone asks for more. Done here rather than in the constructor
  // because it has to survive readConfigFromFS() replaying a stored step - which it should, since
  // a step someone deliberately saved is a better starting point than our fallback.
  step->value = safeStep();
  Control::setup();
  act(); // Push the initial value out, whether it came from the filesystem or from safeStep()
}

void Control_MPPT::act() {
  uint16_t s = step->value;
  if (s > maxStep()) {
    s = maxStep(); // Clamp towards LESS current, which is the safe direction
  }
  vmpp->set(vmppForStep(s));
  dacvolts->set(voltsForStep(s));
}

#endif // OSPIT_MPPT_DAC_PIN
