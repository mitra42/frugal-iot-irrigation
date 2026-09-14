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
static const Control_MPPT_Chemistry MPPT_PROFILES[] = {
  //  name        charge@25C   mV/degC   hot-battery
  { "AGM",         14100,        30,       13100 },
  { "GEL",         14100,        24,       13100 },
  { "Flooded",     14400,        30,       13300 },
  { "LiFePO4",     14200,         0,       13600 }, // Lithium does not want the compensation
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
  tempcoeff(new INfloat(id, "tempcoeff", "Temp coefficient", MPPT_PROFILES[MPPT_AGM].tempcoeff_mv_per_c, 0,
    DEFAULT_mppt_tempcoeff_min, DEFAULT_mppt_tempcoeff_max,
    DEFAULT_mppt_tempcoeff_min, DEFAULT_mppt_tempcoeff_max, DEFAULT_mppt_tempcoeff_color, false)),
  hotcharge(new INfloat(id, "hotcharge", "Hot battery", MPPT_PROFILES[MPPT_AGM].hotcharge_mv, 0,
    DEFAULT_mppt_hotcharge_min, DEFAULT_mppt_hotcharge_max,
    DEFAULT_mppt_hotcharge_min, DEFAULT_mppt_hotcharge_max, DEFAULT_mppt_hotcharge_color, false)),
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
  /* NAN, so an unwired temperature simply means "no correction" rather than "0 degrees", which
   * would subtract 25 x the coefficient and undercharge the battery by most of a volt.
   */
  batttemp(new INfloat(id, "batttemp", "Battery temp", NAN, 1,
    DEFAULT_mppt_batttemp_min, DEFAULT_mppt_batttemp_max,
    DEFAULT_mppt_batttemp_min, DEFAULT_mppt_batttemp_max, DEFAULT_mppt_batttemp_color, true)),
  heatsink(new INfloat(id, "heatsink", "Heatsink temp", NAN, 1,
    DEFAULT_mppt_heatsink_min, DEFAULT_mppt_heatsink_max,
    DEFAULT_mppt_heatsink_min, DEFAULT_mppt_heatsink_max, DEFAULT_mppt_heatsink_color, true)),
  target(new OUTfloat(id, "target", "Target", NAN, 0,
    DEFAULT_mppt_target_min, DEFAULT_mppt_target_max, DEFAULT_mppt_target_color, false)),
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
  inputs.push_back(tempcoeff);
  inputs.push_back(hotcharge);
  inputs.push_back(panel);
  inputs.push_back(battery);
  inputs.push_back(batttemp);
  inputs.push_back(heatsink);
  outputs.push_back(target);
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
    const Control_MPPT_Chemistry& c =
      MPPT_PROFILES[(profile_applied < MPPT_PROFILE_COUNT) ? profile_applied : MPPT_AGM];
    chargeend->set(c.chargeend_mv);
    tempcoeff->set(c.tempcoeff_mv_per_c);
    hotcharge->set(c.hotcharge_mv);
  }
}

void Control_MPPT::setup() {
  Control::setup();                 // Replays stored settings - may restore a profile AND a chargeend
  profile_applied = profile->value; // Adopt what we ended up with, without rewriting chargeend
  configured = true;
  applyStep(safeStep());            // Least current until the first sweep says otherwise
  setState(automatic->value ? "starting" : "manual");
}

// ---- temperature ----------------------------------------------------------------------

/* Back the charge voltage off while the board's own heatsink is too hot.
 *
 * OSPIT subtracts its step on EVERY cycle the heatsink is over the threshold and restores the
 * whole lot when it falls below the lower one. We keep that shape - responding to "still too hot"
 * rather than assuming how much one step buys - but bound the total, which OSPIT does not: a board
 * that stays hot would otherwise walk its charge voltage down without limit.
 *
 * With no heatsink sensor wired there is nothing to protect against and no derating is applied.
 */
void Control_MPPT::updateDerate() {
  if (heatsink->isValid()) {
    const float t = heatsink->floatValue();
    if (t > (float)CONTROL_MPPT_DERATE_START_C) {
      derate_mv += (float)CONTROL_MPPT_DERATE_STEP_MV;
      if (derate_mv > (float)CONTROL_MPPT_DERATE_MAX_MV) {
        derate_mv = (float)CONTROL_MPPT_DERATE_MAX_MV;
      }
    } else if (t < (float)CONTROL_MPPT_DERATE_RESTORE_C) {
      derate_mv = 0; // Restored in one go, as OSPIT does - the hysteresis is what stops it chattering
    }
  }
}

/* The voltage actually being aimed at: the configured charge-end voltage, corrected downwards for
 * a warm battery and for a hot heatsink. Never corrected upwards - both corrections only ever
 * reduce it, so a failed sensor cannot cause overcharging.
 */
float Control_MPPT::computeTarget() {
  float t = chargeend->floatValue();
  if (batttemp->isValid()) {
    const float bt = batttemp->floatValue();
    if (bt > (float)CONTROL_MPPT_HOT_LIMIT_C) {
      // Past the limit, clamp outright rather than extrapolating a coefficient beyond its range
      t = hotcharge->floatValue();
    } else {
      // Positive coefficient, subtracted: hotter battery, lower voltage. Below 25 C this raises
      // the target, which is correct and is what the chemistry wants.
      t -= (bt - 25.0f) * tempcoeff->floatValue();
    }
  } // else no sensor: no correction, and `target` will simply equal `chargeend`
  t -= derate_mv;
  if (t > chargeend->floatValue()) {
    // Only a cold battery can get here, and only by the coefficient. Allowed - but never let the
    // two corrections between them produce something ABOVE what the profile asked for by more
    // than the cold-battery term, which is what this guards against if a coefficient is mis-set.
    const float ceiling = chargeend->floatValue() + (25.0f * tempcoeff->floatValue());
    if (t > ceiling) {
      t = ceiling;
    }
  }
  return t;
}

// ---- regulation -----------------------------------------------------------------------

/* Nudge the step so the battery sits at the target.
 *
 * Proportional and slew-limited rather than OSPIT's single step, because this runs once a wake
 * cycle (~10s) against the battery sensor's reading, where OSPIT runs every 600ms against a
 * reading it takes itself. One step per cycle would take most of an hour to cross the range.
 *
 * Raising the step asks for a higher panel voltage and so draws LESS current - see the header. So
 * a battery ABOVE the target needs a HIGHER step.
 */
void Control_MPPT::regulate(float vb, float tgt) {
  const float err = vb - tgt;
  int32_t s = (int32_t)step->value;
  if (std::fabs(err) > (float)CONTROL_MPPT_DEADBAND_MV) {
    int32_t delta = (int32_t)(err / (float)CONTROL_MPPT_REGULATE_MV_PER_STEP);
    if (delta == 0) {
      delta = (err > 0) ? 1 : -1; // Outside the deadband, always move at least one step
    }
    if (delta > (int32_t)CONTROL_MPPT_MAX_SLEW) {
      delta = (int32_t)CONTROL_MPPT_MAX_SLEW;
    } else if (delta < -(int32_t)CONTROL_MPPT_MAX_SLEW) {
      delta = -(int32_t)CONTROL_MPPT_MAX_SLEW;
    }
    s += delta;
    if (s < 0) {
      s = 0;
    } else if (s > (int32_t)maxStep()) {
      s = (int32_t)maxStep();
    }
    applyStep((uint16_t)s);
  } // else inside the deadband - leave it alone, which is what stops it hunting
}

// ---- the algorithm --------------------------------------------------------------------

void Control_MPPT::periodically() {
  const uint32_t now = frugal_iot.powercontroller->sleepSafeSecs();
  updateDerate();
  const float tgt = computeTarget();
  target->set(tgt);

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

    if (vb > (tgt + (float)CONTROL_MPPT_OVERSHOOT_MV)) {
      /* Well past the target. Stop arguing about gains and go straight to the safe step.
       *
       * This is what makes a once-a-cycle regulator safe: whatever CONTROL_MPPT_REGULATE_MV_PER_STEP
       * is doing, and however badly it is guessed, the battery cannot be held far above its charge
       * voltage. Stays in REGULATING so it resumes fine control once back in range.
       */
      applyStep(safeStep());
      setState("overshoot");
      phase = REGULATING;
    } else if (vp < vb) {
      // The panel is below the battery, so nothing flows into it whatever we ask for
      applyStep(CONTROL_MPPT_IDLE_STEP);
      voc->setInvalid();
      setState("dark");
      phase = TRACKING;
    } else if (phase == REGULATING) {
      if (vb < (tgt - (float)CONTROL_MPPT_EXIT_MV)) {
        /* The battery has fallen well below the target - a load came on, or the sun went in.
         * Back to taking whatever the panel will give. The gap is deliberately wide so a load
         * switching on is not mistaken for the battery needing bulk charge again.
         */
        phase = TRACKING;
        setState("tracking");
      } else {
        regulate(vb, tgt);
        setState("regulating");
      }
    } else if (vb > (tgt + (float)CONTROL_MPPT_ENTER_MV)) {
      // Bulk charging has brought the battery up to its voltage; hold it there instead
      phase = REGULATING;
      regulate(vb, tgt);
      setState("regulating");
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
