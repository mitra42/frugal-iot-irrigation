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
 * What it does NOT yet have, and what that means:
 *
 *   - No temperature compensation of the charge-end voltage. Lead-acid wants roughly -30 mV/degC
 *     from 25 degC; charging a hot battery to a cold battery's voltage overcharges it. Until P5.4
 *     the charge-end voltage is fixed, so set it for the warmest conditions the battery will see
 *     rather than the coldest.
 *   - No fine regulation. This is a bang-bang controller: it charges at the tracked point until
 *     the battery reaches the limit, then stops. A regulated charger instead eases off as it
 *     approaches. The practical effect is that the battery will oscillate slowly around the
 *     charge-end voltage rather than settling on it. Not harmful, not ideal, and it is P5.4.
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
 *   CONTROL_MPPT_RESUME_MV     (200)   how far below the limit the battery must fall to restart
 *   CONTROL_MPPT_VOC_MARGIN_MV (500)   Voc must beat the battery by this to be worth charging from
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
#ifndef CONTROL_MPPT_RESUME_MV
  #define CONTROL_MPPT_RESUME_MV 200
#endif
#ifndef CONTROL_MPPT_VOC_MARGIN_MV
  #define CONTROL_MPPT_VOC_MARGIN_MV 500
#endif

/* Charge-end voltages in millivolts, by battery chemistry - OSPIT's battery_profile_defaults().
 *
 * Selecting a profile WRITES chargeend, rather than chargeend being read through the profile. So
 * "Custom" needs no special case: it is simply what you have after editing the value, and it
 * persists like any other setting. OSPIT carries an is_custom_profile flag and a parallel set of
 * variables to achieve the same thing.
 *
 * These are the charge-end figures only. The temperature coefficient and the hot-battery cap from
 * the same table arrive with the temperature compensation in P5.4; a setting that nothing reads
 * is worse than no setting.
 */
enum Control_MPPT_Profile { MPPT_AGM = 0, MPPT_GEL = 1, MPPT_FLOODED = 2, MPPT_LIFEPO4 = 3 };

class Control_MPPT : public Control {
  public:
    Control_MPPT(const char* const id, const char* const name);
    INuint16* step;       // DAC step. Written by the algorithm when automatic, by a person when not
    INbool*   automatic;  // OFF by default - see "Safety" above
    INuint16* profile;    // Battery chemistry; selecting one writes chargeend
    INfloat*  chargeend;  // Stop charging at this battery voltage, mV
    INfloat*  panel;      // Wire from panel/panel, mV
    INfloat*  battery;    // Wire from battery/battery, mV
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
    enum Phase { TRACKING, SWEEPING };
    Phase phase = TRACKING;
    uint32_t phase_since = 0;  // sleepSafeSecs() when the current phase began
    uint32_t last_sweep = 0;   // sleepSafeSecs() of the last completed sweep; 0 = never
    bool     full = false;     // Latched at the charge-end voltage, cleared RESUME_MV below it
    uint16_t profile_applied = 0; // Which profile's charge-end voltage is currently loaded
    bool     configured = false;  // False while setup() is replaying stored settings - see act()
    void act() override;
    void dispatch(System_Message &msg) override;
    void applyStep(uint16_t s);      // Clamp, publish vmpp and dacvolts
    void setState(const char* s);
    uint16_t safeStep() const;       // Highest step - least current. See the top of this file
    uint16_t maxStep() const;
    float vmppForStep(uint16_t s) const;
    float voltsForStep(uint16_t s) const;
    uint16_t stepForVmpp(float v) const;
    float chargeEndFor(uint16_t p) const;
};

#endif // OSPIT_MPPT_DAC_PIN
#endif // CONTROL_MPPT_H
