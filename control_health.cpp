/* See control_health.h - the method, and the flaw in OSPIT's version that this fixes. */

#include "control_health.h"
#include "Frugal-IoT.h"
#include <cmath>

Control_Health::Control_Health(const char* const id, const char* const name)
: Control(id, name, std::vector<IN*>{}, std::vector<OUT*>{}),
  soc(new INfloat(id, "soc", "Charge", NAN, 0,
    DEFAULT_batteryhealth_soc_min, DEFAULT_batteryhealth_soc_max,
    DEFAULT_batteryhealth_soc_min, DEFAULT_batteryhealth_soc_max, DEFAULT_batteryhealth_soc_color, true)),
  capacity(new INfloat(id, "capacity", "Capacity Ah", 18, 1,
    DEFAULT_batteryhealth_capacity_min, DEFAULT_batteryhealth_capacity_max,
    DEFAULT_batteryhealth_capacity_min, DEFAULT_batteryhealth_capacity_max, DEFAULT_batteryhealth_capacity_color, false)),
  load(new INfloat(id, "load", "Average load A", 1, 2,
    DEFAULT_batteryhealth_load_min, DEFAULT_batteryhealth_load_max,
    DEFAULT_batteryhealth_load_min, DEFAULT_batteryhealth_load_max, DEFAULT_batteryhealth_load_color, false)),
  panelwatts(new INfloat(id, "panelwatts", "Panel watts", 0, 0,
    DEFAULT_batteryhealth_panelwatts_min, DEFAULT_batteryhealth_panelwatts_max,
    DEFAULT_batteryhealth_panelwatts_min, DEFAULT_batteryhealth_panelwatts_max,
    DEFAULT_batteryhealth_panelwatts_color, false)),
  active(new INuint16(id, "active", "Irrigation active", 0,
    DEFAULT_batteryhealth_active_min, DEFAULT_batteryhealth_active_max,
    DEFAULT_batteryhealth_active_min, DEFAULT_batteryhealth_active_max, DEFAULT_batteryhealth_active_color, true)),
  health(new OUTfloat(id, "health", "Health", NAN, 0,
    DEFAULT_batteryhealth_health_min, DEFAULT_batteryhealth_health_max, DEFAULT_batteryhealth_health_color, false)),
  state(new OUTtext(id, "state", "State", "waiting", DEFAULT_batteryhealth_state_color, false)),
  storageratio(new OUTfloat(id, "storageratio", "Storage ratio", NAN, 1,
    DEFAULT_batteryhealth_storageratio_min, DEFAULT_batteryhealth_storageratio_max,
    DEFAULT_batteryhealth_storageratio_color, false)),
  advice(new OUTtext(id, "advice", "Advice", "", DEFAULT_batteryhealth_advice_color, false))
{
  inputs.push_back(soc);
  inputs.push_back(capacity);
  inputs.push_back(load);
  inputs.push_back(panelwatts);
  inputs.push_back(active);
  outputs.push_back(health);
  outputs.push_back(state);
  outputs.push_back(storageratio);
  outputs.push_back(advice);
}

/* Is the battery big enough for the panel? See the header.
 *
 * Independent of the overnight measurement, so it runs every cycle and is useful from the first
 * day - before any health figure exists it uses the rated capacity, which is the right assumption
 * for a new battery and a conservative one for an old.
 */
void Control_Health::updateAdvice() {
  const float watts = panelwatts->floatValue();
  if (!panelwatts->isValid() || (watts <= 0.0f) || (capacity->floatValue() <= 0.0f)) {
    storageratio->setInvalid(); // Nobody has said how big the panel is, so there is nothing to say
    advice->set(String(""));
  } else {
    // OUT has setInvalid() but no isValid() - that test only exists on IN - so check the NAN
    const float measured = health->floatValue();
    const float fraction = std::isnan(measured) ? 1.0f : (measured / 100.0f);
    const float usable_ah = capacity->floatValue() * fraction;
    const float panel_a = watts / (float)CONTROL_HEALTH_PANEL_V;
    const float ratio = usable_ah / panel_a;
    storageratio->set(ratio);
    if (ratio <= (float)CONTROL_HEALTH_MIN_RATIO) {
      // Charged too hard for its size - either it always was, or it has worn down to it
      advice->set(String(F("battery small")));
    } else if (soc->isValid() && (soc->floatValue() < (float)CONTROL_HEALTH_LOW_PC)) {
      // Big enough, but living at a low state of charge, which wears a lead-acid battery too
      advice->set(String(F("battery low")));
    } else {
      advice->set(String(F("ok")));
    }
  }
}

void Control_Health::setState(const char* s) {
  state->set(String(s));
}

void Control_Health::periodically() {
  updateAdvice(); // Every cycle - it does not depend on the overnight window
  if (!frugal_iot.time || !frugal_iot.time->isTimeSet()) {
    setState("waiting"); // The whole method is anchored to the time of day
  } else {
    const time_t now = frugal_iot.time->now();
    struct tm lt;
    localtime_r(&now, &lt);

    /* Anything heavy and intermittent during the window makes the result meaningless, because its
     * draw is not in `load`. This is the bug in OSPIT: it waters at 03:00 and measures 22:00-04:00,
     * so every night it irrigates, the battery looks far more worn than it is.
     */
    if (measuring && (active->value != 0)) {
      voided = true;
    }

    // On the TRANSITION into the hour, not throughout it - otherwise the start would be re-taken
    // every cycle for an hour and the window would be five hours, not six.
    if (lt.tm_hour != last_hour) {
      if (lt.tm_hour == CONTROL_HEALTH_START_HOUR) {
        if (soc->isValid()) {
          soc_at_start = soc->floatValue();
          measuring = true;
          voided = (active->value != 0); // Already watering as the window opens
          setState("measuring");
        } else {
          setState("waiting"); // No charge estimate yet, so nothing to measure against
        }
      } else if ((lt.tm_hour == CONTROL_HEALTH_END_HOUR) && measuring) {
        measuring = false;
        if (voided) {
          setState("voided");
        } else if (!soc->isValid()) {
          setState("voided"); // Lost the estimate part way through
        } else {
          const float dropped = soc_at_start - soc->floatValue();
          // Hours in the window, allowing for it crossing midnight
          const int hours = ((CONTROL_HEALTH_END_HOUR - CONTROL_HEALTH_START_HOUR) + 24) % 24;
          const float expected_ah = (float)hours * load->floatValue();
          const float implied_ah = (dropped / 100.0f) * capacity->floatValue();
          if ((dropped <= 0.0f) || (implied_ah <= 0.0f) || (expected_ah <= 0.0f)) {
            /* The charge estimate did not fall. Either something charged the battery overnight,
             * or the load is too small to register against a table with 10% steps. Not a health
             * figure of 100 - a health figure of "we learned nothing", which is what invalid means.
             */
            setState("voided");
          } else {
            float pc = (expected_ah / implied_ah) * 100.0f;
            if (pc > 100.0f) {
              pc = 100.0f; // A battery cannot be better than new; a higher number means the inputs
            }             // are wrong, and reporting 130% would just look broken
            health->set(pc);
            setState("measured");
          }
        }
      }
      last_hour = lt.tm_hour;
    }
  }
}
