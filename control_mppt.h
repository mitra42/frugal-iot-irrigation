/* Control_MPPT - solar charge control for the FF-ESP32-OpenMPPT board.
 *
 * Finds the voltage at which the solar panel gives the most power, holds it there, and stops when
 * the battery is full. Ported from OSPIT's mp2.lua.
 *
 * ---------------------------------------------------------------------------------------------
 * What the DAC does, and which way round it is
 *
 * The board takes an analog voltage from the ESP32's DAC and uses it as the voltage the solar
 * panel should be held at. A panel produces most power at a particular voltage, below its
 * open-circuit voltage; holding it there is the whole job of an MPPT charger.
 *
 * The number is an INVERSE THROTTLE, which is easy to get backwards:
 *
 *     LOW  step -> low target voltage  -> the panel is pulled down hard -> MORE current
 *     HIGH step -> high target voltage -> the panel is left near open circuit -> LESS current
 *
 * So the SAFE value - the one that charges least, and the one to fall back on whenever a reading
 * is missing or a limit is reached - is the HIGHEST step, not zero.
 *
 * ---------------------------------------------------------------------------------------------
 * How a maximum power point is found: "fractional Voc"
 *
 * Measuring the true maximum power point needs a current sensor, which this board does not have.
 * The standard substitute exploits a property of silicon panels: the maximum-power voltage is a
 * fairly constant fraction of the open-circuit voltage, around 0.8, largely independent of how
 * bright it is. So:
 *
 *   1. Stop drawing current - write the highest step. The panel rises to its open circuit voltage.
 *   2. Wait for it to settle, then measure. That is Voc.
 *   3. Ask for Voc / CONTROL_MPPT_VOC_RATIO (1.24, i.e. 0.806 x Voc) and hold that until the next
 *      sweep.
 *
 * The cost is that charging stops during the sweep. OSPIT sweeps every 15 seconds, which is
 * affordable there because its sweep takes about a second. Ours cannot: the panel voltage arrives
 * through the normal sensor path, once per wake cycle, so a sweep costs a whole cycle of not
 * charging. Sweeping every cycle would halve the harvest. Instead CONTROL_MPPT_SWEEP_S (default
 * 300) sets how often, and one lost cycle in five minutes is a fraction of a percent. Voc moves
 * with panel temperature over tens of minutes, not seconds, so this loses very little tracking
 * accuracy.
 *
 * ---------------------------------------------------------------------------------------------
 * The sweep is spread across two wake cycles, not blocking
 *
 * Cycle N     : write the highest step, note the time, enter SWEEPING.
 * Cycle N+1   : the sensors have since read the panel with no load on it, so `panel` now holds
 *               Voc. Compute the setpoint, write it, go back to TRACKING.
 *
 * This works because System_Frugal runs the sensors group before the controls group, so by the
 * time this control's periodically() runs, the panel reading is from this cycle. It is also why
 * the control reads the panel through a wired IN rather than reaching into the sensor: nothing
 * has to block, and nothing has to know which pin the panel is on.
 *
 * ---------------------------------------------------------------------------------------------
 * Safety - what this will and will not do
 *
 * Every path that is not a deliberate decision to charge ends at the safe step:
 *
 *   no reading from the panel or the battery   -> safe. A charger acting on a missing reading is
 *                                                 the failure that damages batteries.
 *   battery at or above the charge-end voltage -> safe, until it falls CONTROL_MPPT_RESUME_MV
 *                                                 below it again. This is the charge limit.
 *   panel below the battery, or Voc barely above it -> dark. See CONTROL_MPPT_IDLE_STEP.
 *   automatic switched off                     -> whatever step a person last asked for.
 *
 * ---------------------------------------------------------------------------------------------
 * Two stages: bulk, then absorption
 *
 * TRACKING is the bulk stage - take whatever the panel will give, at the maximum power point.
 * That is right until the battery approaches the voltage it should be charged to; past that,
 * pushing more current in overcharges it. So once the battery rises CONTROL_MPPT_ENTER_MV above
 * the target the controller switches to REGULATING, where it stops chasing maximum power and
 * instead nudges the step up or down to HOLD the battery at the target. It returns to bulk when
 * the battery has fallen CONTROL_MPPT_EXIT_MV below the target - a wide gap, because a load
 * switching on should not be mistaken for the battery discharging.
 *
 * The regulator is proportional and slew-limited rather than the single step OSPIT moves:
 *
 *     delta = error / CONTROL_MPPT_REGULATE_MV_PER_STEP, clamped to CONTROL_MPPT_MAX_SLEW
 *
 * because OSPIT regulates every 600 ms against a reading it takes itself, while this runs once a
 * wake cycle against the battery sensor's reading - roughly ten seconds. One step per cycle would
 * take most of an hour to cross the range. If field testing shows it oscillating, lower the gain
 * or the slew; if it is sluggish, raise them. Both are build flags.
 *
 * CONTROL_MPPT_OVERSHOOT_MV is the backstop that makes the slow loop safe: past that much above
 * the target the controller stops arguing and goes straight to the safe step. Whatever the gain
 * is doing, the battery cannot be held far above its charge voltage.
 *
 * ---------------------------------------------------------------------------------------------
 * Temperature
 *
 * Two corrections, both of which LOWER the voltage the battery is charged to:
 *
 *   Battery temperature. Lead-acid wants about -30 mV per degree above 25 C (per cell-string; the
 *   figure is per profile). A hot battery charged to a cold battery's voltage gases and loses
 *   water. Above CONTROL_MPPT's hot limit the target is clamped to the profile's hot-battery
 *   voltage outright rather than extrapolating.
 *
 *   Heatsink temperature. If the board's own heatsink is too hot, back off. OSPIT subtracts
 *   heatsink_derate_step_mv from the target on EVERY cycle the heatsink is over its threshold,
 *   and restores the lot when it falls below the lower one.
 *
 *   That looks unbounded, and an earlier version of this file "fixed" it with a cap. The cap was
 *   wrong and is worth explaining, because the mistake is easy to repeat. Lowering the target does
 *   NOTHING while the battery is below it - in bulk the target is not used for current control at
 *   all, only to decide when to start regulating. The derate begins to bite only once the target
 *   has fallen BELOW the battery's actual voltage. So with AGM's 14.1V and a 1V cap, the target
 *   stops at 13.1V; a discharged battery under charge sitting at 13.0V is still below that, so the
 *   board is still in bulk, still at full current, still heating - and the protection has hit its
 *   limit without ever engaging. The cap defeated the case it was meant to handle.
 *
 *   Unbounded is correct, and it is not a runaway. Once the target drops below the battery
 *   voltage, CONTROL_MPPT_OVERSHOOT_MV sends the step to safe, current stops, the board cools, and
 *   below the restore threshold the whole derate is dropped at once. It is an integral controller
 *   with a reset. If the board is hot for a reason unrelated to charging - high ambient, blocked
 *   airflow - then walking down until charging stops altogether is the right answer, not a
 *   failure. CONTROL_MPPT_TARGET_MIN_MV exists only to stop the arithmetic reaching values that
 *   mean nothing; it sits below any usable battery, so it never limits the protection.
 *
 * With no battery temperature sensor wired, no compensation is applied and `target` simply equals
 * `chargeend` - so set chargeend for the warmest conditions the battery will see. The published
 * `target` always says what is actually being aimed at.
 *
 * AUTOMATIC IS OFF BY DEFAULT. Nothing here has run on real hardware. It stays off until someone
 * has worked through TESTING.md and is satisfied the readings are right. Turning it on is one
 * switch, and the setting is remembered.
 *
 * ---------------------------------------------------------------------------------------------
 * The step-to-volts mapping, which is a guess until someone measures it
 *
 * OSPIT maps its panel-voltage range onto the DAC as
 *     dac = (Vmpp - Vmpp_min) / ((Vmpp_max - Vmpp_min) / 285)
 * Note 285, not 255: on OSPIT's own numbers the top tenth of the range is unreachable. That may be
 * a deliberate correction for a transfer function that is not quite linear, or a mistake - we
 * cannot tell from the code, so it is CONTROL_MPPT_DAC_SPAN here and Part H of TESTING.md is the
 * measurement that settles it.
 *
 * `step` stays an input and `vmpp` an OUTPUT for the same reason: a person setting this by hand
 * sets a step, which is unambiguous, and the node reports the voltage it BELIEVES that asks for.
 *
 * Build flags:
 *   OSPIT_MPPT_DAC_PIN         REQUIRED, or none of this is compiled
 *   CONTROL_MPPT_VMPP_MIN  }   the panel-voltage range this board's hardware can ask for.
 *   CONTROL_MPPT_VMPP_MAX  }   Give BOTH or NEITHER - see the #error below.
 *   CONTROL_MPPT_BOARD_FF_1_0 / _1_1   a known board revision instead of the two above. With none
 *                              of these set, FF v1.2 is used - the most recent, so a new board
 *                              needs no flags at all.
 *   CONTROL_MPPT_DAC_SPAN      (285)   see above
 *   CONTROL_MPPT_VOC_RATIO     (1.24)  Voc divided by this is the maximum-power voltage
 *   CONTROL_MPPT_SWEEP_S       (300)   seconds between open-circuit measurements
 *   CONTROL_MPPT_SETTLE_S      (2)     shortest gap between unloading the panel and believing it
 *   CONTROL_MPPT_IDLE_STEP     (29)    what to write when the panel is dark
 *   CONTROL_MPPT_VOC_MARGIN_MV (500)   Voc must beat the battery by this to be worth charging from
 *   CONTROL_MPPT_ENTER_MV      (50)    above target -> leave bulk, start regulating
 *   CONTROL_MPPT_EXIT_MV       (300)   below target -> back to bulk tracking
 *   CONTROL_MPPT_DEADBAND_MV   (30)    no correction while the error is smaller than this
 *   CONTROL_MPPT_REGULATE_MV_PER_STEP (50) battery error one DAC step is assumed to correct.
 *                              A GUESS - the first thing to tune if regulation misbehaves.
 *   CONTROL_MPPT_MAX_SLEW      (8)     most steps to move in one cycle
 *   CONTROL_MPPT_OVERSHOOT_MV  (300)   past this above target, go straight to the safe step
 *   CONTROL_MPPT_HOT_LIMIT_C   (42)    battery above this uses the profile's hot-battery voltage
 *   CONTROL_MPPT_DERATE_START_C   (60) heatsink above this starts backing the target off
 *   CONTROL_MPPT_DERATE_RESTORE_C (58) and below this restores it
 *   CONTROL_MPPT_DERATE_STEP_MV   (100) by this much per cycle, for as long as it is too hot
 *   CONTROL_MPPT_TARGET_MIN_MV  (10000) floor on the target, below any usable battery
 */

#ifndef CONTROL_MPPT_H
#define CONTROL_MPPT_H

#ifdef OSPIT_MPPT_DAC_PIN

#include "control/control.h"

/* Defining one of the pair and not the other would silently mix your value with a default, and
 * the result would look plausible. In the preprocessor defined() is 1 or 0, so this compares them.
 */
#if defined(CONTROL_MPPT_VMPP_MIN) != defined(CONTROL_MPPT_VMPP_MAX)
  #error Define both CONTROL_MPPT_VMPP_MIN and CONTROL_MPPT_VMPP_MAX, or neither
#endif

#if !defined(CONTROL_MPPT_VMPP_MIN)
  #if defined(CONTROL_MPPT_BOARD_FF_1_0)
    // Cannot track a panel below 14.45V, which a hot 36-cell panel can fall to
    #define CONTROL_MPPT_VMPP_MIN 14.45
    #define CONTROL_MPPT_VMPP_MAX 23.80
  #elif defined(CONTROL_MPPT_BOARD_FF_1_1)
    // Reaches highest, so it suits a 60-cell / 24V-nominal panel
    #define CONTROL_MPPT_VMPP_MIN 13.25
    #define CONTROL_MPPT_VMPP_MAX 27.20
  #else
    // FF-ESP32-OpenMPPT v1.2 - the most recent, and the compromise between the two above
    #define CONTROL_MPPT_VMPP_MIN 12.86
    #define CONTROL_MPPT_VMPP_MAX 25.15
  #endif
#endif

#ifndef CONTROL_MPPT_DAC_SPAN
  #define CONTROL_MPPT_DAC_SPAN 285
#endif
#ifndef CONTROL_MPPT_VOC_RATIO
  #define CONTROL_MPPT_VOC_RATIO 1.24
#endif
#ifndef CONTROL_MPPT_SWEEP_S
  #define CONTROL_MPPT_SWEEP_S 300
#endif
#ifndef CONTROL_MPPT_SETTLE_S
  #define CONTROL_MPPT_SETTLE_S 2
#endif
#ifndef CONTROL_MPPT_IDLE_STEP
  /* What to write when the panel is dark.
   *
   * 29 is OSPIT's value and we do not know why it chose it. It is a LOW step, i.e. it asks for
   * maximum current - harmless in the dark because there is none to be had, and it means charging
   * begins the moment the sun returns rather than waiting for the next sweep. That is the only
   * explanation we can see; if it turns out to matter, this is the flag to change.
   */
  #define CONTROL_MPPT_IDLE_STEP 29
#endif
#ifndef CONTROL_MPPT_VOC_MARGIN_MV
  #define CONTROL_MPPT_VOC_MARGIN_MV 500
#endif
#ifndef CONTROL_MPPT_ENTER_MV
  #define CONTROL_MPPT_ENTER_MV 50
#endif
#ifndef CONTROL_MPPT_EXIT_MV
  #define CONTROL_MPPT_EXIT_MV 300
#endif
#ifndef CONTROL_MPPT_DEADBAND_MV
  #define CONTROL_MPPT_DEADBAND_MV 30
#endif
#ifndef CONTROL_MPPT_REGULATE_MV_PER_STEP
  /* How much battery error one DAC step is assumed to correct.
   *
   * A GUESS. The real figure depends on the panel, the battery's internal resistance and the state
   * of charge, and it is not constant. Too large and regulation is sluggish; too small and it
   * oscillates. CONTROL_MPPT_MAX_SLEW and CONTROL_MPPT_OVERSHOOT_MV bound what a bad guess can do.
   */
  #define CONTROL_MPPT_REGULATE_MV_PER_STEP 50
#endif
#ifndef CONTROL_MPPT_MAX_SLEW
  /* Most steps to move in one cycle.
   *
   * Note this does NOT bind at the default settings: ENTER_MV, EXIT_MV and OVERSHOOT_MV between
   * them hold the error regulation ever sees to +/-300 mV, and 300/50 is 6, under this limit. It
   * is here for a re-tuned system - lowering REGULATE_MV_PER_STEP after field testing is exactly
   * what would make a single correction large enough to matter.
   */
  #define CONTROL_MPPT_MAX_SLEW 8
#endif
#ifndef CONTROL_MPPT_OVERSHOOT_MV
  #define CONTROL_MPPT_OVERSHOOT_MV 300
#endif
#ifndef CONTROL_MPPT_HOT_LIMIT_C
  #define CONTROL_MPPT_HOT_LIMIT_C 42
#endif
#ifndef CONTROL_MPPT_DERATE_START_C
  #define CONTROL_MPPT_DERATE_START_C 60
#endif
#ifndef CONTROL_MPPT_DERATE_RESTORE_C
  #define CONTROL_MPPT_DERATE_RESTORE_C 58
#endif
#ifndef CONTROL_MPPT_DERATE_STEP_MV
  #define CONTROL_MPPT_DERATE_STEP_MV 100
#endif
#ifndef CONTROL_MPPT_TARGET_MIN_MV
  /* A floor on the TARGET, not a cap on the derating - see "Temperature" above for why that
   * distinction matters. 10V is below any usable 12V battery, so this never stops the heatsink
   * protection from doing its job; it only keeps the arithmetic somewhere meaningful.
   */
  #define CONTROL_MPPT_TARGET_MIN_MV 10000
#endif

/* Charge-end voltages in millivolts, by battery chemistry - OSPIT's battery_profile_defaults().
 *
 * Selecting a profile WRITES chargeend, rather than chargeend being read through the profile. So
 * "Custom" needs no special case: it is simply what you have after editing the value, and it
 * persists like any other setting. OSPIT carries an is_custom_profile flag and a parallel set of
 * variables to achieve the same thing.
 *
 * Each row carries the charge-end voltage, the temperature coefficient and the hot-battery cap,
 * and selecting a profile writes all three.
 */
enum Control_MPPT_Profile { MPPT_AGM = 0, MPPT_GEL = 1, MPPT_FLOODED = 2, MPPT_LIFEPO4 = 3 };

// One row of the profile table - see MPPT_PROFILES in control_mppt.cpp
struct Control_MPPT_Chemistry {
  const char* name;
  float chargeend_mv;      // At 25 C
  float tempcoeff_mv_per_c;
  float hotcharge_mv;      // Once the battery is over CONTROL_MPPT_HOT_LIMIT_C
};

class Control_MPPT : public Control {
  public:
    Control_MPPT(const char* const id, const char* const name);
    INuint16* step;       // DAC step. Written by the algorithm when automatic, by a person when not
    INbool*   automatic;  // OFF by default - see "Safety" above
    INuint16* profile;    // Battery chemistry; selecting one writes chargeend
    INfloat*  chargeend;  // Charge to this battery voltage at 25 C, mV
    INfloat*  tempcoeff;  // mV to subtract per degree above 25 C; 0 for chemistries that do not care
    INfloat*  hotcharge;  // Voltage to use instead once the battery is over the hot limit, mV
    INfloat*  panel;      // Wire from panel/panel, mV
    INfloat*  battery;    // Wire from battery/battery, mV
    INfloat*  batttemp;   // Wire from a battery-mounted probe, C. Unwired means no compensation
    INfloat*  heatsink;   // Wire from the board's own temperature, C. Unwired means no derating
    OUTfloat* target;     // The voltage actually being aimed at now, after both corrections, mV
    OUTfloat* vmpp;       // Panel voltage we PREDICT the current step asks for - a guess
    OUTfloat* voc;        // Open-circuit voltage from the last sweep, mV
    OUTfloat* dacvolts;   // Wire to an Actuator_Analog's set path; volts at the DAC pin
    OUTtext*  state;      // What it is doing, in words - the first thing to look at
    void setup() override;
    void periodically() override;
  protected:
    /* Where the sweep has got to. Not persisted and not in RTC memory: after any restart the right
     * thing is to sweep again, and the safe step is the right thing to hold until we have.
     */
    enum Phase { TRACKING, SWEEPING, REGULATING };
    Phase phase = TRACKING;
    uint32_t phase_since = 0;  // sleepSafeSecs() when the current phase began
    uint32_t last_sweep = 0;   // sleepSafeSecs() of the last completed sweep; 0 = never
    float    derate_mv = 0;    // Accumulated heatsink derating, bounded by DERATE_MAX_MV
    uint16_t profile_applied = 0; // Which profile's voltages are currently loaded
    bool     configured = false;  // False while setup() is replaying stored settings - see act()
    void act() override;
    void dispatch(System_Message &msg) override;
    void applyStep(uint16_t s);      // Clamp, publish vmpp and dacvolts
    void setState(const char* s);
    void updateDerate();             // Heatsink protection - see "Temperature" above
    float computeTarget();           // chargeend, corrected for battery and heatsink temperature
    void regulate(float vb, float tgt); // Proportional, slew-limited nudge towards the target
    uint16_t safeStep() const;       // Highest step - least current. See the top of this file
    uint16_t maxStep() const;
    float vmppForStep(uint16_t s) const;
    float voltsForStep(uint16_t s) const;
    uint16_t stepForVmpp(float v) const;
};

#endif // OSPIT_MPPT_DAC_PIN
#endif // CONTROL_MPPT_H
