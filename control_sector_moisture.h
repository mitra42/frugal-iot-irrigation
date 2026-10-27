/* A sector watered until its soil reaches a target moisture.
 *
 * The OSPIT rule, and the one this application started with. See control_irrigation.h for the
 * sequencer that runs it, and for "Skipping a sector", which is what available() implements here.
 */

#ifndef CONTROL_SECTOR_MOISTURE_H
#define CONTROL_SECTOR_MOISTURE_H

#include "control_irrigation.h"

class Control_Sector_Moisture : public Control_Sector {
  public:
    Control_Sector_Moisture(const char* const id, const char* const name);
    INfloat* moisture; // Wire to a soil probe, e.g. soil1/humidity. "nan" here means "skip me"
    INfloat* target;   // Stop watering at this moisture

    bool available() override { return moisture->isValid(); }
    // Opens the valve only with a reading, and only when the soil is below target.
    bool start() override;
    bool step() override;
};

#endif // CONTROL_SECTOR_MOISTURE_H
