/* The irrigation sequencer as this application uses it: a tank and a battery interlock, and one
 * of three pump rules.
 *
 * Composes its own blockers, so the sketch only has to wire them:
 *   tankBlocker   "irrigation-tank"   do not start below tankstart, abort at tankempty
 *   powerBlocker  "irrigation-power"  wire from the battery Control_Hysteresis
 *   solarBlocker  "irrigation-solar"  pump mode 3 only - see below
 *
 * The ids are fixed, so there is one of these per node. The sectors are NOT composed here - the
 * sketch adds them, because which sector watches which probe is wiring, not irrigation policy.
 *
 * ---------------------------------------------------------------------------------------------
 * Pump modes
 *
 * Set CONTROL_IRRIGATION_PUMP_MODE. Hard-coded for now; if these prove useful they become
 * classes rather than a #define.
 *   1 (default) pump runs while any valve is open and nothing says stop
 *               - the tank feeds the sectors, the pump pressurises them
 *   2           pump runs while the tank is NOT full - i.e. it fills a header tank
 *   3           as 2, but only while `solar` says there is input power to spare
 *
 * In mode 3 the solar blocker gates the PUMP, not the sectors, so it is not added with
 * addBlocker(): the sectors are fed from the header tank by gravity, and input power has no
 * bearing on whether they can run.
 */

#ifndef CONTROL_IRRIGATION_EXAMPLE_H
#define CONTROL_IRRIGATION_EXAMPLE_H

#include "control_irrigation.h"

#ifndef CONTROL_IRRIGATION_PUMP_MODE
  #define CONTROL_IRRIGATION_PUMP_MODE 1
#endif

class Control_Irrigation_Example : public Control_Irrigation {
  public:
    Control_Irrigation_Example(const char* const id, const char* const name);
    Control_Blocker_Tank*  tankBlocker;
    Control_Blocker_Power* powerBlocker;
    #if CONTROL_IRRIGATION_PUMP_MODE == 3
      Control_Blocker_Solar* solarBlocker;
    #endif
  protected:
    void setPump() override;
};

#endif // CONTROL_IRRIGATION_EXAMPLE_H
