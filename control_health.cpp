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
  active(new INuint16(id, "active", "Irrigation active", 0,
    DEFAULT_batteryhealth_active_min, DEFAULT_batteryhealth_active_max,
    DEFAULT_batteryhealth_active_min, DEFAULT_batteryhealth_active_max, DEFAULT_batteryhealth_active_color, true)),
  health(new OUTfloat(id, "health", "Health", NAN, 0,
    DEFAULT_batteryhealth_health_min, DEFAULT_batteryhealth_health_max, DEFAULT_batteryhealth_health_color, false)),
  state(new OUTtext(id, "state", "State", "waiting", DEFAULT_batteryhealth_state_color, false))
{
  inputs.push_back(soc);
  inputs.push_back(capacity);
  inputs.push_back(load);
  inputs.push_back(active);
  outputs.push_back(health);
  outputs.push_back(state);
}

void Control_Health::setState(const char* s) {
  state->set(String(s));
}

void Control_Health::periodically() {
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
