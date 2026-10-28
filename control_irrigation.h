/* Sequenced, time-of-day irrigation - the base classes.
 *
 * Note, influenced by OSPIT - and for some parts there is a one:one relationship
 * the differences are in OSPIT_COMPARISOM.md along with some bugs/weaknesses found.
 *
 * Three families of class, each a base here and subclasses elsewhere for particular rules:
 *   Control_Sector      one irrigation sector - a valve, and the rule for when it wants water.
 *                       The base waters until the per-sector maximum time runs out;
 *                       Control_Sector_Moisture stops at a target soil moisture.
 *   Control_Blocker     something that can stop irrigation - tank, battery, solar.
 *                       See control_blocker.h.
 *   Control_Irrigation  the sequencer - owns the clock, the master switch, the pump, a list of
 *                       blockers, and a list of sectors which it runs ONE AT A TIME, in order.
 *                       Control_Irrigation_Example composes a particular set of blockers and the
 *                       pump rule.
 *
 * So an installation with, say, one sector on a moisture probe and another on a timer, is two
 * different sector classes added to the same sequencer.
 *
 * What it does:
 *   - once a day, at a configured local hour:minute, start a cycle, if every blocker agrees
 *   - take each sector in turn; open its valve until either the sector says it is done or the
 *     per-sector maximum time runs out; then close it and move to the next
 *   - skip a sector that is not available (e.g. its probe reads "nan") without touching its valve
 *   - abort the whole cycle if any blocker says stop
 *   - when the last sector is done, arm for the same time tomorrow
 *
 * ---------------------------------------------------------------------------------------------
 * A single, sleep-safe timer controls either when the next cycle starts,
 * or the maximum time the current sector's valve should stay open.
 *
 * The start is an absolute epoch from System_Time::getNextDaytime(), armed once per cycle rather
 * than recomputed every pass - an epoch for the right wall-clock time is already right across a
 * daylight-saving change. A small clock correction through System_Time::set() shifts it by the
 * same few seconds; a large one would move the start, which is accepted as unlikely.
 *
 * No RTC_DATA_ATTR state of our own (other than the timer) is needed. `i` is reset to "idle" in setup(), which runs on
 * every boot including a deep-sleep wake.
 * okToSleep() prevents sleeping mid-cycle.
 *
 * ---------------------------------------------------------------------------------------------
 * Skipping a sector
 *
 * A sector that is not available() is skipped and its valve is never driven, because driving a
 * valve you have no feedback from is worse than not watering. For Control_Sector_Moisture that
 * is a probe publishing "nan". (In OSPIT the skip was also how pin 12 was chosen between valve 3
 * and USB.)
 */

#ifndef CONTROL_IRRIGATION_H
#define CONTROL_IRRIGATION_H

#include "control/control.h"
#include "control_blocker.h"
#include <vector>
#include <ctime>

/* How late after hour:minute a run may still begin, in seconds - see inStartWindow().
 *
 * Normally a run starts within one wake cycle of the slot, so this only matters for a late wake
 * from sleep, or a clock that was set a little after the slot. An hour is generous for both,
 * while a node powered up in the afternoon still waits for tomorrow.
 */
#ifndef CONTROL_IRRIGATION_START_WINDOW_S
  #define CONTROL_IRRIGATION_START_WINDOW_S 3600
#endif

/* One irrigation sector: a valve, and when it is this sector's turn.
 *
 * The base has no sensor, so it always wants water and runs until the sequencer's maximum time.
 * Subclasses override start() and step() to decide for themselves, calling the base start() to
 * actually open the valve.
 *
 * Registered in frugal_iot.controls (so receives dispatch etc) AND held in Control_Irrigation::sectors
 */
class Control_Sector : public Control {
  public:
    Control_Sector(const char* const id, const char* const name);
    INbool*  enable;  // Set by Control_Irrigation: when it is this sector's turn.; UX controllable to immediately cancel and close valve.
    OUTbool* valve;   // Wire to an Actuator_Digital, e.g. setPath("valve1/on")

    /* False when this sector has no feedback to work from, so must be neither opened nor closed
     * - see "Skipping a sector". Always true in the base, which has no feedback to lose.
     */
    virtual bool available() { return true; }
    /* Begin watering this sector, if it should be watered at all.
     *
     * The base opens the valve whenever enable is set. False - and the valve untouched - means
     * this sector does not want water; true means the valve has been opened and the caller should
     * arm the maximum-duration timer.
     */
    virtual bool start();
    /* True while this sector should keep watering. Called once per cycle by the sequencer, which
     * stops the sector when this returns false OR the maximum time expires. The base always says
     * keep going, so it is the timer that ends it.
     */
    virtual bool step() { return true; }
    void stop(); // Close the valve and drop enable. Safe to call when not running.
    /* Push "closed" onto the valve whether or not this control believes it is already closed.
     *
     * stop() goes through OUTbool::set(), which only sends on a change - so a valve opened by
     * hand from the portal, which never touched this OUT, would be left open. See closeAll().
     */
    void forceOff();
  protected:
    void act() override;
};

class Control_Irrigation : public Control {
  public:
    Control_Irrigation(const char* const id, const char* const name);
    std::vector<Control_Sector*> sectors;
    std::vector<Control_Blocker*> blockers;
    /* Add a sector to this sequencer AND to frugal_iot.controls.
     *
     * Sectors run in the order they are added. Returns its argument, with its own type, so the
     * sketch can construct, add and wire in one go:
     *   Control_Sector_Moisture* s1 = irr->addSector(new Control_Sector_Moisture("sector1", "Sector 1"));
     * A template only so that the return type is the caller's subclass, not Control_Sector.
     */
    template<class S> S* addSector(S* s) { registerSector(s); return s; }
    // As addSector(), for a blocker - and makes this its owner, so it re-runs act() on a change.
    template<class B> B* addBlocker(B* b) { registerBlocker(b); return b; }

    INuint16* hour;       // Local hour to start
    INuint16* minute;     // Local minute to start
    INfloat*  maxminutes; // Longest any one valve may stay open
    INbool*   enabled;    // Master switch
    OUTbool*  pump;       // Wire to the pump/load Actuator_Digital
    OUTuint16* active;    // Sector currently running, 1-based; 0 when idle

    /* Refuses any sleep while a cycle is running - System_Power asks every module before sleeping
     * (System_Base::okToSleep), and asks again on the next loop() after a refusal.
     *
     * Whatever kind of sleep: a deep sleep would abandon the cycle (see the note on `i` above), and
     * any sleep would leave a valve open with nothing watching the tank, the power interlock, the
     * watchdog or MQTT. Between cycles any sleep is fine - a start that falls due during a sleep
     * just happens on waking, as the timer lives in RTC memory.
     * TODO may consider holding GPIO with RTC when asleep, which would allow a cycle to span a
     * sleep rather than having to prevent one.
     */
    bool okToSleep(unsigned long ms, uint16_t how) override;

    void setup() override;
    void periodically() override;
    void act() override; // Public so a Control_Blocker can call it through its owner
  protected:
    uint8_t t;  // Sleep-safe timer slot - see "The main loop" above. Claimed in the constructor.
    int8_t  i;  // Sector being watered; >= sectors.size() means idle. Set to idle in setup().
    bool running() { return i < (int8_t)sectors.size(); }
    void registerSector(Control_Sector* s);   // The work of addSector(), out of line
    void registerBlocker(Control_Blocker* b); // The work of addBlocker(), out of line
    /* True when a running cycle must stop right now: master switch off, or any blocker says stop.
     * Checked every cycle AND before each sector, so it aborts the sequence rather than merely the
     * current sector.
     */
    bool blocked();
    // True when a new cycle may begin: not blocked(), and every blocker is ok to start.
    bool canStart();
    void startNext();   // Advance i to the next sector that will run; leaves it idle if none will
    /* Close every sector's valve at the end of a cycle, whoever opened it.
     *
     * Manual control is allowed to fight the sequencer and win for a while - but when the run
     * that would have closed a valve reaches its end, it closes. That needs forceOff() rather
     * than stop(), and it needs to reach sectors the run skipped, neither of which falls out of
     * the per-sector path.
     *
     * Sectors that are not available() are left alone: we promised never to drive a valve we have
     * no feedback from, and that promise holds for closing as well as opening.
     * TODO manual override needs application-specific thought - "the schedule wins eventually"
     * is one answer, "manual latches until someone clears it" is another.
     */
    void closeAll();
    // Arm the timer for the next hour:minute - see periodically() for when, and why not more often
    void armNext();
    /* True when the clock is set and the most recent hour:minute was less than
     * CONTROL_IRRIGATION_START_WINDOW_S ago.
     *
     * An expired timer is NOT enough on its own to start a run, because it expires for reasons
     * that are not a scheduled start: a slot that has never been armed reads 0, so it is already
     * expired after a cold boot (RTC memory cleared) and stays so until the clock is set; and an
     * NTP step clamps a timer that looks too far ahead to "now" (System_Power::timers_clampFuture).
     * Starting on either would water at power-up. So the timer says WHEN to look, and this says
     * whether it is time.
     */
    bool inStartWindow();
    /* Drive the pump. The base runs it while a sector is watering and nothing says stop - the tank
     * feeds the sectors and the pump pressurises them. Override for a pump that does something
     * else, e.g. fills a header tank - see Control_Irrigation_Example.
     */
    virtual void setPump();
};

#endif // CONTROL_IRRIGATION_H
