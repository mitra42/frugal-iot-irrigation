/* See control_irrigation_example.h */

#include "control_irrigation_example.h"
#include "Frugal-IoT.h"

Control_Irrigation_Example::Control_Irrigation_Example(const char* const id, const char* const name)
: Control_Irrigation(id, name),
  tankBlocker(addBlocker(new Control_Blocker_Tank("irrigation-tank", "Irrigation tank"))),
  powerBlocker(addBlocker(new Control_Blocker_Power("irrigation-power", "Irrigation power")))
{
  #if CONTROL_IRRIGATION_PUMP_MODE == 3
    // Not addBlocker() - see "Pump modes" in the header. Still owned, so a change re-runs setPump().
    solarBlocker = new Control_Blocker_Solar("irrigation-solar", "Irrigation solar");
    solarBlocker->owner = this;
    frugal_iot.controls->add(solarBlocker);
  #endif
}

void Control_Irrigation_Example::setPump() {
  #if CONTROL_IRRIGATION_PUMP_MODE == 1
    Control_Irrigation::setPump();
  #elif CONTROL_IRRIGATION_PUMP_MODE == 2
    // Pump fills a header tank - run whenever it is below the "enough to start" level. Never run
    // when no tank sensor is fitted: with no level to work from, running a pump is the unsafe guess.
    pump->set(tankBlocker->needsFilling());
  #elif CONTROL_IRRIGATION_PUMP_MODE == 3
    // As mode 2, but only while there is input power to spare, e.g. wired from a hysteresis
    // control on the solar input voltage.
    pump->set(tankBlocker->needsFilling() && solarBlocker->okToIrrigate());
  #else
    #error CONTROL_IRRIGATION_PUMP_MODE must be 1, 2 or 3 - see control_irrigation_example.h
  #endif
}
