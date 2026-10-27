/* Blockers - things that can stop a Control_Irrigation from running.
 *
 * A blocker is a control in its own right (so it has its own inputs, topics and portal section)
 * which Control_Irrigation asks two questions:
 *
 *   okToIrrigate()    may a run START now? Asked once, when a run falls due.
 *   stopIrrigation()  must a running run ABORT now? Asked every cycle, before each sector, and
 *                     whenever any blocker's inputs change.
 *
 * They are two questions rather than one because they usually want different thresholds - the
 * tank is the obvious case: do not bother starting below 25%, but do not abort a run already going
 * until it falls to 5%. Without that gap a tank hovering at one level starts and aborts all day.
 *
 * An unwired blocker never blocks. Wiring one in can only ever stop irrigation, never enable it,
 * which is the right way round for anything that opens water valves unattended.
 *
 * Ids: the blockers composed by Control_Irrigation_Example are "irrigation-tank" etc. The client
 * resolves those to the "irrigation" schema by prefix (see CLAUDE.md "Module ids and schema keys"),
 * and the leaves keep their old names, so no schema change was needed to split them out.
 */

#ifndef CONTROL_BLOCKER_H
#define CONTROL_BLOCKER_H

#include "control/control.h"

class Control_Blocker : public Control {
  public:
    Control_Blocker(const char* const id, const char* const name);
    virtual bool okToIrrigate() { return true; }
    virtual bool stopIrrigation() { return false; }
    /* The control to re-evaluate when this blocker's inputs change. Set by
     * Control_Irrigation::addBlocker().
     *
     * Without it a battery that has just dropped below its threshold would only close the valve
     * on the sequencer's next periodically(), up to one wake-cycle later - the inputs belong to
     * this control now, so the sequencer's own act() no longer sees them change.
     */
    Control* owner = nullptr;
  protected:
    void act() override;
};

/* Tank level, from Sensor_Tank.
 *
 * "nan" means no tank sensor is fitted, and is deliberately NOT treated as an empty tank - see
 * sensor_tank.h. So with no sensor this neither blocks nor aborts.
 */
class Control_Blocker_Tank : public Control_Blocker {
  public:
    Control_Blocker_Tank(const char* const id, const char* const name);
    INfloat* tank;       // Level in %, wire from e.g. tank/tank
    INfloat* tankstart;  // Do not BEGIN a run below this level
    INfloat* tankempty;  // ABORT a running run at or below this level
    bool okToIrrigate() override;
    bool stopIrrigation() override;
    bool fitted() { return tank->isValid(); }
    // Below the start level - for a pump that fills a header tank. Never true with no sensor.
    bool needsFilling();
};

/* Electrically safe to run - typically wired from a Control_Hysteresis on the battery voltage.
 * Defaults true, so a node with nothing wired to it still irrigates.
 */
class Control_Blocker_Power : public Control_Blocker {
  public:
    Control_Blocker_Power(const char* const id, const char* const name);
    INbool* power;
    bool okToIrrigate() override { return power->value; }
    bool stopIrrigation() override { return !power->value; }
};

/* Input power available - e.g. wired from a Control_Hysteresis on the panel voltage.
 *
 * Only refuses a START. A cloud passing over mid-run is not a reason to abandon the sectors still
 * to go; a battery that is genuinely too low is Control_Blocker_Power's job.
 */
class Control_Blocker_Solar : public Control_Blocker {
  public:
    Control_Blocker_Solar(const char* const id, const char* const name);
    INbool* solar;
    bool okToIrrigate() override { return solar->value; }
};

#endif // CONTROL_BLOCKER_H
