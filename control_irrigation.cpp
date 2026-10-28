/* See control_irrigation.h for what this does, how the single timer serves both halves of the
 * job, and why a sector with no reading is skipped rather than watered.
 */

#include "control_irrigation.h"
#include "language.h"
#include "Frugal-IoT.h"

// ================= Control_Sector =================================================

Control_Sector::Control_Sector(const char* const id, const char* const name)
: Control(id, name, std::vector<IN*>{}, std::vector<OUT*>{}),
  enable(new INbool(id, "enable", String(irrigationT->Enable), false, DEFAULT_sector_enable_color, false)),
  valve(new OUTbool(id, "valve", String(irrigationT->Valve), false, DEFAULT_sector_valve_color, true))
{
  inputs.push_back(enable);
  outputs.push_back(valve);
}

/* Inputs changed.
 *
 * `enable` is the interlock: dropping it closes the valve at once, whoever dropped it - the
 * sequencer moving on, or a person clearing it from the portal. Raising it does NOT open the
 * valve; only start() does, so the sequencer stays in charge of when watering begins.
 *
 * Nothing here reacts to the sector being satisfied (e.g. `moisture` reaching `target` in
 * Control_Sector_Moisture). That is deliberate - the decision to stop belongs to the sequencer,
 * which also has to arm the next sector, and having two places able to close the valve would make
 * "why did it stop?" much harder to answer. Subclasses report it through step() instead.
 */
void Control_Sector::act() {
  if (!enable->value && valve->value) {
    valve->set(false);
  }
}

bool Control_Sector::start() {
  bool started = false;
  if (enable->value) {
    valve->set(true);
    started = true;
  }
  return started;
}

void Control_Sector::stop() {
  valve->set(false);
  enable->set(false);
}

void Control_Sector::forceOff() {
  valve->set(false);   // Sends only if this control had it open ...
  valve->sendWired();  // ... so push it regardless, in case something else did - see closeAll()
  enable->set(false);
}

// ================= Control_Irrigation =============================================

Control_Irrigation::Control_Irrigation(const char* const id, const char* const name)
: Control(id, name, std::vector<IN*>{}, std::vector<OUT*>{}),
  // One slot, claimed once, for the lifetime of the device - see CLAUDE.md "Using a sleep-safe
  // timer in a component". It carries the per-sector maximum while a cycle runs and the next
  // start time while idle.
  t(frugal_iot.powercontroller->timer_next()),
  i(0), // Replaced by setup() with sectors.size(), i.e. idle, once the sectors are known
  hour(new INuint16(id, "hour", String(irrigationT->StartHour), 3, IO_DEFAULTS(irrigation_hour), false)),
  minute(new INuint16(id, "minute", String(irrigationT->StartMinute), 0,
    IO_DEFAULTS(irrigation_minute), false)),
  maxminutes(new INfloat(id, "maxminutes", String(irrigationT->MaxMinutesPerSector), 5, 1,
    IO_DEFAULTS(irrigation_maxminutes), false)),
  // Defaults to OFF. Something that opens water valves unattended should not start doing so merely
  // because it was flashed - see the note in frugal-iot-irrigation.ino on turning it on.
  enabled(new INbool(id, "enabled", String(irrigationT->Enabled), false, DEFAULT_irrigation_enabled_color, false)),
  pump(new OUTbool(id, "pump", String(irrigationT->Pump), false, DEFAULT_irrigation_pump_color, true)),
  active(new OUTuint16(id, "active", String(irrigationT->ActiveSector), 0,
    IO_DEFAULTS(irrigation_active), false))
{
  inputs.push_back(hour);
  inputs.push_back(minute);
  inputs.push_back(maxminutes);
  inputs.push_back(enabled);
  outputs.push_back(pump);
  outputs.push_back(active);
}

void Control_Irrigation::registerSector(Control_Sector* s) {
  sectors.push_back(s);
  // Also a control in its own right, so it gets dispatch(), discover() and a captive-portal
  // section like anything else. Same arrangement as Control_Carousel's children - see gps.ino.
  frugal_iot.controls->add(s);
}

void Control_Irrigation::registerBlocker(Control_Blocker* b) {
  blockers.push_back(b);
  b->owner = this;
  frugal_iot.controls->add(b);
}

void Control_Irrigation::setup() {
  // Idle. This runs on every boot, a deep-sleep wake included, so a cycle interrupted by a sleep
  // is abandoned rather than resumed from stale state - and every valve has just been driven low
  // by Actuator_Digital::setup(). See the header for why that is the outcome we want.
  i = (int8_t)sectors.size();
  Control::setup();
}

bool Control_Irrigation::okToSleep(unsigned long ms, uint16_t how) {
  return !running();
}

// Deliberately loops rather than returning early - see CLAUDE.md "Coding preferences".
bool Control_Irrigation::blocked() {
  bool stop = !enabled->value;
  for (Control_Blocker* b : blockers) {
    if (b->stopIrrigation()) {
      stop = true;
    }
  }
  return stop;
}

bool Control_Irrigation::canStart() {
  bool ok = !blocked();
  for (Control_Blocker* b : blockers) {
    if (!b->okToIrrigate()) {
      ok = false;
    }
  }
  return ok;
}

void Control_Irrigation::closeAll() {
  for (Control_Sector* s : sectors) {
    if (s->available()) {
      s->forceOff();
    }
  }
}

void Control_Irrigation::startNext() {
  while (++i < (int8_t)sectors.size()) {
    if (blocked()) {
      // An interlock opened part way through the sequence. Abandon the whole cycle, not just this
      // sector.
      i = (int8_t)sectors.size();
    } else {
      sectors[i]->enable->set(true);
      if (sectors[i]->start()) {
        frugal_iot.powercontroller->timer_set(t, (uint32_t)(maxminutes->floatValue() * 60.0f));
        break;
      }
      sectors[i]->enable->set(false); // Did not start - do not leave it looking armed
    }
  }
}

void Control_Irrigation::armNext() {
  // 0 with no clock - or no System_Time at all - which reads as expired, so periodically() looks
  // again on every pass until the clock is set, and inStartWindow() keeps that from being a run.
  const time_t next = frugal_iot.time
    ? frugal_iot.time->getNextDaytime((uint8_t)hour->value, (uint8_t)minute->value)
    : 0;
  frugal_iot.powercontroller->timer_set_to(t, (uint32_t)next);
}

// Wall-clock arithmetic rather than epochs, so it needs no "yesterday's slot" calculation.
bool Control_Irrigation::inStartWindow() {
  bool inWindow = false;
  if (frugal_iot.time && frugal_iot.time->isTimeSet()) {
    const time_t now = frugal_iot.time->now();
    struct tm lt;
    localtime_r(&now, &lt);
    int32_t since = ((int32_t)lt.tm_hour * 3600 + lt.tm_min * 60 + lt.tm_sec)
      - ((int32_t)hour->value * 3600 + (int32_t)minute->value * 60);
    if (since < 0) {
      since += 86400; // The slot is later today, so the most recent one was yesterday's
    }
    inWindow = since < CONTROL_IRRIGATION_START_WINDOW_S;
  }
  return inWindow;
}

void Control_Irrigation::setPump() {
  pump->set(running() && !blocked());
}

/* An input changed - ours, or a blocker's, which calls this through Control_Blocker::owner.
 *
 * Acting here as well as in periodically() is what makes the interlocks quick: a battery that has
 * just dropped below its threshold closes the valve now rather than up to one wake-cycle later.
 * The abort path is the same one startNext() takes, so there is only one behaviour to reason about.
 */
void Control_Irrigation::act() {
  System_Power* p = frugal_iot.powercontroller;
  if (running() && blocked()) {
    sectors[i]->stop();
    i = (int8_t)sectors.size();
    closeAll(); // An interlock aborting a run closes everything, not just the sector that was open
    active->set(0);
    armNext(); // Otherwise the timer still holds this sector's maximum, which is not a start time
  } else if (!running() && !p->timer_expired(t)) {
    /* Idle and armed: recompute, which is how a change to hour or minute takes effect.
     *
     * Not when the timer has expired. That is periodically()'s to deal with, and re-arming here
     * would throw a start away: a deep-sleep wake AT the start time replays the persisted inputs
     * through dispatch() before the first periodically(), and so does any tank or battery reading
     * that happens to arrive in the few seconds between the start time and the next pass.
     */
    armNext();
  }
  setPump();
}

/* The timer is re-armed only when it has done its job - a cycle ending, or an idle expiry that did
 * not start one - and on an input change (see act()). Not on every pass: a time computed just
 * before the start would already be tomorrow's, and the run would never happen.
 */
void Control_Irrigation::periodically() {
  System_Power* p = frugal_iot.powercontroller;
  bool cycleEnded = false;
  bool rearm = false;
  if (running()) {
    // Three ways a sector's turn ends: its time ran out, an interlock opened, or the soil reached
    // target. stop() closes the valve in all three; startNext() then finds the next sector that
    // will actually run, or leaves us idle.
    if (p->timer_expired(t) || blocked() || !sectors[i]->step()) {
      sectors[i]->stop();
      startNext();
      cycleEnded = !running();
    }
  } else if (p->timer_expired(t)) {
    /* Expired is "time to look", not "time to run" - see inStartWindow() in the header for the
     * other reasons a timer can be expired.
     *
     * TODO this writes off the whole day if an interlock happens to be open at the scheduled
     * moment - a tank still refilling at 03:00, or a momentary battery dip - because what is
     * armed next is tomorrow. OSPIT retries for the rest of the hour (see OSPIT_COMPARISON.md);
     * worth adding if that matters in practice.
     */
    if (inStartWindow() && canStart()) {
      i = -1; // startNext() pre-increments, so this starts the search at sector 0
      startNext();
      cycleEnded = !running(); // A cycle was due and attempted, but no sector wanted water
    } else {
      rearm = true;
    }
  }
  if (cycleEnded) {
    // Once per cycle, not once per pass - so this is a handful of messages a day, not a stream
    closeAll();
    rearm = true;
  }
  if (rearm) {
    armNext();
  }
  active->set(running() ? (uint16_t)(i + 1) : 0);
  setPump();
}
