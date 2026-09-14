/* See control_mppt.h - how fractional-Voc tracking works, why the sweep spans two wake cycles,
 * and why the SAFE step is the highest one rather than zero.
 */

#include "control_mppt.h"

#ifdef OSPIT_MPPT_DAC_PIN

#include "Frugal-IoT.h"
#include "actuator/analog.h" // for ACTUATOR_ANALOG_STEPS and ACTUATOR_ANALOG_VREF
#include "misc.h"            // for changed()
#include <cmath>

// Charge-end voltage in mV per chemistry - OSPIT's battery_profile_defaults(). See the note on
// the enum in control_mppt.h for why there is no "Custom" entry.
static const struct { const char* name; float chargeend_mv; } MPPT_PROFILES[] = {
  { "AGM",     14100 },
  { "GEL",     14100 },
  { "Flooded", 14400 },
  { "LiFePO4", 14200 },
};
#define MPPT_PROFILE_COUNT ((uint16_t)(sizeof(MPPT_PROFILES) / sizeof(MPPT_PROFILES[0])))

Control_MPPT::Control_MPPT(const char* const id, const char* const name)
: Control(id, name, std::vector<IN*>{}, std::vector<OUT*>{}),
  step(new INuint16(id, "step", "DAC step", 0,
    DEFAULT_mppt_step_min, DEFAULT_mppt_step_max,
    DEFAULT_mppt_step_min, DEFAULT_mppt_step_max, DEFAULT_mppt_step_color, false)),
  // OFF until someone has been through TESTING.md - see "Safety" in the header
  automatic(new INbool(id, "automatic", "Automatic", false, DEFAULT_mppt_automatic_color, false)),
  profile(new INuint16(id, "profile", "Battery type", MPPT_AGM,
    DEFAULT_mppt_profile_min, DEFAULT_mppt_profile_max,
    DEFAULT_mppt_profile_min, DEFAULT_mppt_profile_max, DEFAULT_mppt_profile_color, false)),
  chargeend(new INfloat(id, "chargeend", "Charge end", MPPT_PROFILES[MPPT_AGM].chargeend_mv, 0,
    DEFAULT_mppt_chargeend_min, DEFAULT_mppt_chargeend_max,
    DEFAULT_mppt_chargeend_min, DEFAULT_mppt_chargeend_max, DEFAULT_mppt_chargeend_color, false)),
  /* NAN, so a node with nothing wired to these reads as "no reading" and stays safe - rather than
   * believing the panel and the battery are both sitting at zero volts, which would look like a
   * flat battery in the dark and is exactly the state we least want to guess about.
   */
  panel(new INfloat(id, "panel", "Panel", NAN, 0,
    DEFAULT_mppt_panel_min, DEFAULT_mppt_panel_max,
    DEFAULT_mppt_panel_min, DEFAULT_mppt_panel_max, DEFAULT_mppt_panel_color, true)),
  battery(new INfloat(id, "battery", "Battery", NAN, 0,
    DEFAULT_mppt_battery_min, DEFAULT_mppt_battery_max,
    DEFAULT_mppt_battery_min, DEFAULT_mppt_battery_max, DEFAULT_mppt_battery_color, true)),
  vmpp(new OUTfloat(id, "vmpp", "Panel target", NAN, 2,
    DEFAULT_mppt_vmpp_min, DEFAULT_mppt_vmpp_max, DEFAULT_mppt_vmpp_color, false)),
  voc(new OUTfloat(id, "voc", "Open circuit", NAN, 0,
    DEFAULT_mppt_voc_min, DEFAULT_mppt_voc_max, DEFAULT_mppt_voc_color, false)),
  dacvolts(new OUTfloat(id, "dacvolts", "DAC volts", 0, 3,
    DEFAULT_mppt_dacvolts_min, DEFAULT_mppt_dacvolts_max, DEFAULT_mppt_dacvolts_color, true)),
  state(new OUTtext(id, "state", "State", "starting", DEFAULT_mppt_state_color, false))
{
  inputs.push_back(step);
  inputs.push_back(automatic);
  inputs.push_back(profile);
  inputs.push_back(chargeend);
  inputs.push_back(panel);
  inputs.push_back(battery);
  outputs.push_back(vmpp);
  outputs.push_back(voc);
  outputs.push_back(dacvolts);
  outputs.push_back(state);
}

// ---- the step / voltage mapping -------------------------------------------------------

uint16_t Control_MPPT::maxStep() const {
  return (uint16_t)(ACTUATOR_ANALOG_STEPS - 1); // 255 on a real DAC, 2^bits-1 through PWM
}

uint16_t Control_MPPT::safeStep() const {
  return maxStep(); // Highest step = panel near open circuit = least current. See the header.
}

float Control_MPPT::vmppForStep(uint16_t s) const {
  // Divided by CONTROL_MPPT_DAC_SPAN (285, not 255) - OSPIT's number, and the reason the top of
  // the range is unreachable. A prediction to be checked against a meter, not a measurement.
  return (float)CONTROL_MPPT_VMPP_MIN
       + ((float)s * ((float)CONTROL_MPPT_VMPP_MAX - (float)CONTROL_MPPT_VMPP_MIN)
          / (float)CONTROL_MPPT_DAC_SPAN);
}

uint16_t Control_MPPT::stepForVmpp(float v) const {
  const float span = ((float)CONTROL_MPPT_VMPP_MAX - (float)CONTROL_MPPT_VMPP_MIN);
  const float raw = (v - (float)CONTROL_MPPT_VMPP_MIN) * (float)CONTROL_MPPT_DAC_SPAN / span;
  uint16_t s;
  if (raw <= 0.0f) {
    /* Wanting a lower voltage than the hardware can ask for - a panel that is cold, small, or
     * partly shaded. Ask for the lowest it has rather than giving up: charging at a non-optimal
     * point is better than not charging at all.
     */
    s = 0;
  } else if (raw >= (float)maxStep()) {
    s = maxStep();
  } else {
    s = (uint16_t)(raw + 0.5f);
  }
  return s;
}

float Control_MPPT::voltsForStep(uint16_t s) const {
  // The same arithmetic Actuator_Analog uses, in reverse, so asking for step N writes step N
  return ((float)ACTUATOR_ANALOG_VREF * (float)s) / (float)maxStep();
}

float Control_MPPT::chargeEndFor(uint16_t p) const {
  return MPPT_PROFILES[(p < MPPT_PROFILE_COUNT) ? p : MPPT_AGM].chargeend_mv;
}

// ---- output ---------------------------------------------------------------------------

void Control_MPPT::applyStep(uint16_t s) {
  if (s > maxStep()) {
    s = maxStep(); // Clamp towards LESS current, which is the safe direction
  }
  step->set(s); // An IN rather than private state, so it stays visible and a person can override
  vmpp->set(vmppForStep(s));
  dacvolts->set(voltsForStep(s));
}

void Control_MPPT::setState(const char* s) {
  state->set(String(s));
}

// ---- configuration --------------------------------------------------------------------

/* Someone touching `step` means they want manual control.
 *
 * Only a message reaches here - the algorithm writes the step through INuint16::set(), which does
 * not go through dispatch() - so this cleanly distinguishes "a person asked" from "we decided".
 * Without it, setting a step by hand while automatic was on would be silently undone on the next
 * cycle, which looks like the board ignoring you.
 */
void Control_MPPT::dispatch(System_Message &msg) {
  const bool manualStep = msg.isSet() && (msg.module() == id) && msg.leaf().startsWith("step");
  Control::dispatch(msg);
  if (manualStep && automatic->value) {
    automatic->set(false);
    Serial.println(F("mppt: step set by hand, automatic switched off"));
  }
}

/* Selecting a battery type loads its charge-end voltage.
 *
 * Only when the PROFILE is what changed, which is what profile_applied tracks. Editing chargeend
 * afterwards therefore sticks - and that is all "Custom" means here, so unlike OSPIT there is no
 * separate mode, no is_custom_profile flag, and no parallel set of variables.
 *
 * `configured` keeps this quiet during setup(): readConfigFromFS() replays stored settings through
 * dispatch(), which calls act(), and the order the files come back in is not defined. Without the
 * guard, a stored profile arriving before a stored chargeend would overwrite the value someone
 * had deliberately customised.
 */
void Control_MPPT::act() {
  if (configured && (profile->value != profile_applied)) {
    profile_applied = profile->value;
    chargeend->set(chargeEndFor(profile_applied));
  }
}

void Control_MPPT::setup() {
  Control::setup();                 // Replays stored settings - may restore a profile AND a chargeend
  profile_applied = profile->value; // Adopt what we ended up with, without rewriting chargeend
  configured = true;
  applyStep(safeStep());            // Least current until the first sweep says otherwise
  setState(automatic->value ? "starting" : "manual");
}

// ---- the algorithm --------------------------------------------------------------------

void Control_MPPT::periodically() {
  const uint32_t now = frugal_iot.powercontroller->sleepSafeSecs();

  if (!automatic->value) {
    setState("manual"); // A person owns `step`; do not touch it
  } else if (!panel->isValid() || !battery->isValid()) {
    /* No reading. This is the case that damages batteries when it is got wrong, so it is tested
     * before anything else, and it goes to the safe step rather than holding the last one - a
     * held step is a decision made from information we no longer have.
     */
    applyStep(safeStep());
    setState("no reading");
    phase = TRACKING;
  } else {
    const float vp = panel->floatValue();
    const float vb = battery->floatValue();

    // Charge limit, latched with hysteresis so it does not chatter at the threshold
    if (vb >= chargeend->floatValue()) {
      full = true;
    } else if (vb < (chargeend->floatValue() - (float)CONTROL_MPPT_RESUME_MV)) {
      full = false;
    }

    if (full) {
      applyStep(safeStep());
      setState("full");
      phase = TRACKING;
    } else if (vp < vb) {
      // The panel is below the battery, so nothing flows into it whatever we ask for
      applyStep(CONTROL_MPPT_IDLE_STEP);
      voc->setInvalid();
      setState("dark");
      phase = TRACKING;
    } else if (phase == SWEEPING) {
      if ((now - phase_since) >= (uint32_t)CONTROL_MPPT_SETTLE_S) {
        /* The panel has been unloaded since the previous cycle, so this reading IS the
         * open-circuit voltage: the sensors group runs before the controls group, so `panel`
         * already holds a value measured this cycle.
         */
        if (vp < (vb + (float)CONTROL_MPPT_VOC_MARGIN_MV)) {
          // Open circuit barely above the battery - there is no useful power here. OSPIT makes
          // the same test and zeroes its panel readings when it fails.
          voc->setInvalid();
          applyStep(CONTROL_MPPT_IDLE_STEP);
          setState("dark");
        } else {
          voc->set(vp);
          // In volts: the Vmpp range is in volts, while the sensors report millivolts
          const float target_v = (vp / 1000.0f) / (float)CONTROL_MPPT_VOC_RATIO;
          applyStep(stepForVmpp(target_v));
          setState("tracking");
        }
        last_sweep = now;
        phase = TRACKING;
      } // else still settling - leave the panel unloaded and look again next cycle
    } else if ((last_sweep == 0) || ((now - last_sweep) >= (uint32_t)CONTROL_MPPT_SWEEP_S)) {
      // Time to re-measure. Unload the panel now; the reading is taken next cycle.
      applyStep(safeStep());
      setState("sweeping");
      phase = SWEEPING;
      phase_since = now;
    } // else holding the tracked step - nothing to do
  }
}

#endif // OSPIT_MPPT_DAC_PIN
