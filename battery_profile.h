/* What a battery chemistry wants - shared by the charge controller and the charge estimate.
 *
 * Its own file because it belongs to neither. Control_MPPT needs the charging voltages and
 * Control_SoC needs to know whether to use the lead-acid or the lithium voltage curve, and a board
 * can have the second without the first - a node with a battery but no solar panel still wants to
 * report how full it is. Keeping this inside control_mppt.h, behind OSPIT_MPPT_DAC_PIN, made
 * Control_SoC fail to compile on exactly that board.
 */

#ifndef BATTERY_PROFILE_H
#define BATTERY_PROFILE_H

/* Numbering is deliberately stable and the values are published as an integer, so a stored
 * setting keeps its meaning across firmware versions. Add new chemistries at the END.
 */
enum Battery_Profile { BATTERY_AGM = 0, BATTERY_GEL = 1, BATTERY_FLOODED = 2, BATTERY_LIFEPO4 = 3 };

// One row of the charging table - see BATTERY_PROFILES in control_mppt.cpp
struct Battery_Chemistry {
  const char* name;
  float chargeend_mv;      // At 25 C
  float tempcoeff_mv_per_c;
  float hotcharge_mv;      // Once the battery is over CONTROL_MPPT_HOT_LIMIT_C
};

#endif // BATTERY_PROFILE_H
