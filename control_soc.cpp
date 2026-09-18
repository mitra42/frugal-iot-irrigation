/* See control_soc.h - why this is a table rather than OSPIT's eight branches, and why the estimate
 * is frozen while charging.
 */

#include "control_soc.h"
#include "language.h"
#include "Frugal-IoT.h"
#include <cmath>

/* Resting voltage against state of charge, in millivolts, highest first.
 *
 * Lead-acid is the standard 12V table; AGM, GEL and flooded are close enough to each other at this
 * resolution that one table serves all three. LiFePO4 is a different shape entirely - note how
 * little voltage separates 20% from 90%, which is exactly why a voltage estimate is weak for it.
 */
struct SoCPoint { float mv; float pc; };

static const SoCPoint SOC_LEAD[] = {
  { 12700, 100 }, { 12580, 90 }, { 12460, 80 }, { 12360, 70 }, { 12280, 60 },
  { 12200,  50 }, { 12060, 40 }, { 11900, 30 }, { 11750, 20 }, { 11580, 10 }, { 11400, 0 },
};
static const SoCPoint SOC_LIFEPO4[] = {
  { 13400, 100 }, { 13300, 90 }, { 13250, 80 }, { 13220, 70 }, { 13200, 60 },
  { 13180,  50 }, { 13150, 40 }, { 13100, 30 }, { 13000, 20 }, { 12900, 10 }, { 12000, 0 },
};
#define SOC_POINTS ((uint8_t)(sizeof(SOC_LEAD) / sizeof(SOC_LEAD[0])))

Control_SoC::Control_SoC(const char* const id, const char* const name)
: Control(id, name, std::vector<IN*>{}, std::vector<OUT*>{}),
  battery(new INfloat(id, "battery", String(irrigationT->Battery), NAN, 0,
    DEFAULT_soc_battery_min, DEFAULT_soc_battery_max,
    DEFAULT_soc_battery_min, DEFAULT_soc_battery_max, DEFAULT_soc_battery_color, true)),
  // NAN means no panel is wired, which is read as "this node never charges" rather than as a panel
  // sitting at zero volts - the latter would look like darkness and freeze nothing
  panel(new INfloat(id, "panel", String(irrigationT->Panel), NAN, 0,
    DEFAULT_soc_panel_min, DEFAULT_soc_panel_max,
    DEFAULT_soc_panel_min, DEFAULT_soc_panel_max, DEFAULT_soc_panel_color, true)),
  profile(new INuint16(id, "profile", String(irrigationT->BatteryType), BATTERY_AGM,
    DEFAULT_soc_profile_min, DEFAULT_soc_profile_max,
    DEFAULT_soc_profile_min, DEFAULT_soc_profile_max, DEFAULT_soc_profile_color, false)),
  soc(new OUTfloat(id, "soc", String(irrigationT->Charge), NAN, 0,
    DEFAULT_soc_soc_min, DEFAULT_soc_soc_max, DEFAULT_soc_soc_color, false)),
  charging(new OUTbool(id, "charging", String(irrigationT->Charging), false, DEFAULT_soc_charging_color, false))
{
  inputs.push_back(battery);
  inputs.push_back(panel);
  inputs.push_back(profile);
  outputs.push_back(soc);
  outputs.push_back(charging);
}

/* Linear interpolation between the two table entries the voltage falls between.
 *
 * The table is ordered highest voltage first, so walking down it and stopping at the first entry
 * the reading is above finds the upper bracket. Off either end clamps rather than extrapolating -
 * a battery at 13.5V resting is not 140% charged, it is a battery that has just come off charge.
 */
float Control_SoC::socForVoltage(float mv, uint16_t chem) const {
  const SoCPoint* t = (chem == BATTERY_LIFEPO4) ? SOC_LIFEPO4 : SOC_LEAD;
  float pc;
  if (mv >= t[0].mv) {
    pc = t[0].pc;
  } else if (mv <= t[SOC_POINTS - 1].mv) {
    pc = t[SOC_POINTS - 1].pc;
  } else {
    pc = t[SOC_POINTS - 1].pc; // Not reachable; keeps the compiler happy about the loop below
    for (uint8_t i = 1; i < SOC_POINTS; i++) {
      if (mv >= t[i].mv) {
        const float span_mv = t[i - 1].mv - t[i].mv;
        const float span_pc = t[i - 1].pc - t[i].pc;
        pc = t[i].pc + ((mv - t[i].mv) / span_mv) * span_pc;
        break;
      }
    }
  }
  return pc;
}

void Control_SoC::setup() {
  Control::setup();
  soc->setInvalid(); // "No estimate yet" until a reading arrives, rather than a confident zero
}

void Control_SoC::periodically() {
  if (!battery->isValid()) {
    soc->setInvalid();
    published = NAN;
  } else {
    /* Charging if there is a panel and it is above the battery. With no panel wired this is always
     * false, which is right for a node with no solar - its battery only ever discharges.
     */
    const bool chg = panel->isValid() && (panel->floatValue() > battery->floatValue());
    charging->set(chg);
    if (!chg) {
      const float want = socForVoltage(battery->floatValue(), profile->value);
      if (std::isnan(published)) {
        published = want; // First reading: adopt it rather than crawling up from nothing
      } else {
        // Slew limit. A pump starting drops the terminal voltage for a few seconds; without this
        // the estimate would lurch down and then back, which looks like the battery misbehaving.
        const float slew = (float)CONTROL_SOC_SLEW_PC;
        if (want > published + slew) {
          published += slew;
        } else if (want < published - slew) {
          published -= slew;
        } else {
          published = want;
        }
      }
      soc->set(published);
    } // else frozen - see the header. The last figure stands, and `charging` says why.
  }
}
