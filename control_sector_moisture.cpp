/* See control_sector_moisture.h */

#include "control_sector_moisture.h"
#include "language.h"
#include "Frugal-IoT.h"
#include <cmath> // for NAN

Control_Sector_Moisture::Control_Sector_Moisture(const char* const id, const char* const name)
: Control_Sector(id, name),
  // Starts as "no reading", so a sector whose moisture input is never wired is skipped rather
  // than watered on the strength of a default of zero.
  moisture(new INfloat(id, "moisture", String(irrigationT->Moisture), NAN, 1,
    IO_DEFAULTS(sector_moisture), true)),
  target(new INfloat(id, "target", String(irrigationT->Target), 80, 1, IO_DEFAULTS(sector_target), true))
{
  // At the front, so the portal still shows the reading and target above enable, as it did
  // before the base class was split out.
  inputs.insert(inputs.begin(), {moisture, target});
}

bool Control_Sector_Moisture::start() {
  bool started = false;
  // isValid() false means the probe published "nan" - no reading at all. Skip without touching
  // the valve; see "Skipping a sector" in control_irrigation.h.
  if (available() && (moisture->floatValue() < target->floatValue())) {
    started = Control_Sector::start();
  }
  return started;
}

bool Control_Sector_Moisture::step() {
  bool keepGoing;
  if (!moisture->isValid()) {
    /* The reading disappeared part way through watering.
     *
     * Keep the valve open and let the maximum-duration timer end the sector, rather than closing
     * up immediately. A probe that misses a poll or two on a shared RS485 bus is a great deal more
     * common than a probe that has really gone, and stopping on every dropped reading would
     * under-water the sector every time. The timeout still bounds how much water this can cost.
     *
     * TODO revisit once there is field experience. The alternative - stop and advance - is safer
     * if probes turn out to fail outright more often than they glitch, and this is the one line
     * to change. Note start() takes the opposite view for the same condition, on purpose: opening
     * a valve with no feedback at all is a worse bet than continuing one already open.
     */
    keepGoing = true;
  } else {
    keepGoing = moisture->floatValue() < target->floatValue();
  }
  return keepGoing;
}
