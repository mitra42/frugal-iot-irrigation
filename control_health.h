/* Control_Health - how much of its rated capacity the battery still has.
 *
 * REPORTING ONLY, like Control_SoC, and for the same reason: it is an inference from two numbers
 * measured six hours apart, not a measurement.
 *
 * ---------------------------------------------------------------------------------------------
 * The idea
 *
 * Overnight the system draws a known, fairly steady current and nothing charges it. So over a
 * six-hour window we know roughly how many amp-hours came OUT:
 *
 *     expected Ah = 6 hours x the node's average current draw
 *
 * And the state-of-charge estimate says what fraction of the battery that emptied, which - if the
 * battery still had its rated capacity - would be:
 *
 *     implied Ah = (SoC at 22:00 - SoC at 04:00) / 100 x rated Ah
 *
 * If the battery is healthy those agree. If it has faded, the same amp-hours empty a larger
 * fraction of it, the implied figure is bigger, and the ratio falls:
 *
 *     health % = expected / implied x 100
 *
 * This is OSPIT's method, and it is a decent one for a system with no current sensor. Its accuracy
 * rests entirely on `load` being right - see below.
 *
 * ---------------------------------------------------------------------------------------------
 * A flaw in OSPIT's version, which is fixed here
 *
 * OSPIT runs its health test from 22:00 to 04:00 and its irrigation at 03:00. So on any night the
 * irrigation actually runs, the pump's draw lands INSIDE the measurement window and is not in
 * `av_pwr` - which makes the battery look far more worn than it is, and does so only on the nights
 * it waters, so the figure jumps around for no visible reason.
 *
 * Here the measurement is abandoned if irrigation runs at any point during the window. Wire
 * `active` to irrigation/active and it looks after itself; leave it unwired on a node with no
 * irrigation and every night counts. The same applies to anything else heavy and intermittent: if
 * you add one, it needs to invalidate the window too.
 *
 * ---------------------------------------------------------------------------------------------
 * What it is worth
 *
 * A trend over weeks, not a reading. It inherits every weakness of the voltage-based SoC it is
 * built on - most of which cancel, because the same table is used at both ends of the window, but
 * not all - and `load` is a number somebody typed in rather than something measured. A figure that
 * falls steadily over months means something. A figure that is 78 rather than 84 does not.
 *
 * It reports nothing at all until a complete, uninterrupted window has passed, rather than
 * publishing a confident number derived from half a night.
 *
 * Build flags:
 *   CONTROL_HEALTH_START_HOUR  (22)  local hour the window opens
 *   CONTROL_HEALTH_END_HOUR     (4)  and closes. Six hours later, overnight, nothing charging
 */

#ifndef CONTROL_HEALTH_H
#define CONTROL_HEALTH_H

#include "control/control.h"
#include <ctime>

#ifndef CONTROL_HEALTH_START_HOUR
  #define CONTROL_HEALTH_START_HOUR 22
#endif
#ifndef CONTROL_HEALTH_END_HOUR
  #define CONTROL_HEALTH_END_HOUR 4
#endif

class Control_Health : public Control {
  public:
    Control_Health(const char* const id, const char* const name);
    INfloat*  soc;      // Wire from soc/soc, percent
    INfloat*  capacity; // Rated capacity when new, Ah - OSPIT's ah_batt
    INfloat*  load;     // Average current the system draws overnight, A - OSPIT's av_pwr
    INuint16* active;   // Wire from irrigation/active. Non-zero at any point voids the window
    OUTfloat* health;   // Percent of rated capacity. Invalid until a whole clean window has passed
    OUTtext*  state;    // waiting / measuring / voided / measured - why there is or is not a figure
    void periodically() override;
  protected:
    bool  measuring = false;
    bool  voided = false;     // Irrigation ran during this window, so it does not count
    float soc_at_start = NAN;
    int   last_hour = -1;     // So the window opens on the TRANSITION into the hour, not all hour
    void setState(const char* s);
};

#endif // CONTROL_HEALTH_H
