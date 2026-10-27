/* See control_blocker.h for the two questions a blocker answers, and why they are separate. */

#include "control_blocker.h"
#include "language.h"
#include "Frugal-IoT.h"
#include <cmath> // for NAN

// ================= Control_Blocker ================================================

Control_Blocker::Control_Blocker(const char* const id, const char* const name)
: Control(id, name, std::vector<IN*>{}, std::vector<OUT*>{})
{
}

void Control_Blocker::act() {
  if (owner) {
    owner->act();
  }
}

// ================= Control_Blocker_Tank ===========================================

Control_Blocker_Tank::Control_Blocker_Tank(const char* const id, const char* const name)
: Control_Blocker(id, name),
  tank(new INfloat(id, "tank", String(irrigationT->TankLevel), NAN, 1, IO_DEFAULTS(irrigation_tank), true)),
  tankstart(new INfloat(id, "tankstart", String(irrigationT->TankLevelToStart), 25, 1,
    IO_DEFAULTS(irrigation_tankstart), false)),
  tankempty(new INfloat(id, "tankempty", String(irrigationT->TankLevelToStop), 5, 1,
    IO_DEFAULTS(irrigation_tankempty), false))
{
  inputs.push_back(tank);
  inputs.push_back(tankstart);
  inputs.push_back(tankempty);
}

// No tank sensor fitted ("nan") never blocks - see sensor_tank.h.
bool Control_Blocker_Tank::okToIrrigate() {
  return !fitted() || (tank->floatValue() >= tankstart->floatValue());
}

bool Control_Blocker_Tank::stopIrrigation() {
  return fitted() && (tank->floatValue() <= tankempty->floatValue());
}

bool Control_Blocker_Tank::needsFilling() {
  return fitted() && (tank->floatValue() < tankstart->floatValue());
}

// ================= Control_Blocker_Power ==========================================

Control_Blocker_Power::Control_Blocker_Power(const char* const id, const char* const name)
: Control_Blocker(id, name),
  power(new INbool(id, "power", String(irrigationT->PowerOk), true, DEFAULT_irrigation_power_color, true))
{
  inputs.push_back(power);
}

// ================= Control_Blocker_Solar ==========================================

Control_Blocker_Solar::Control_Blocker_Solar(const char* const id, const char* const name)
: Control_Blocker(id, name),
  solar(new INbool(id, "solar", String(irrigationT->InputPower), true, DEFAULT_irrigation_solar_color, true))
{
  inputs.push_back(solar);
}
