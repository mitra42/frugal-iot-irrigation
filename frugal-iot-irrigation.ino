/*
 *  Frugal IoT example - OSPIT irrigation
 *
 *  A port of the irrigation half of OSPIT (https://github.com/mitra42/ospit) - the solar-powered
 *  irrigation controller built on the FF-ESP32-OpenMPPT board. It waters a set of sectors one at
 *  a time, once a day, each until its soil reaches a target moisture or a time limit runs out,
 *  with tank-level and battery interlocks that stop the whole run.
 *
 *  What is here, and what is not:
 *    - irrigation, soil probes, tank gauge, valves, pump          YES
 *    - MPPT solar charge control                                  NO - that is a later phase.
 *      This build leaves the FF board's charge hardware entirely alone and uses the board as a
 *      plain ESP32. On the FF board, the existing charge controller is simply not driven.
 *
 *  Two boards, see platformio.ini: `ff_openmppt` (the real OSPIT hardware) and `s2_mini` (the
 *  same application on a plain dev board with no charge-controller hardware).
 *
 *  ============================================================================================
 *  IRRIGATION IS OFF BY DEFAULT.
 *
 *  `irrigation/enabled` starts false, as OSPIT's i_nbld does - a device that opens water valves
 *  unattended should not begin doing so merely because it was flashed. Turn it on once, from the
 *  captive portal or by publishing to `set/<device>/irrigation/enabled` = 1; the setting is
 *  written to LittleFS and survives reboots and deep sleep.
 *
 *  Worth setting at the same time, all persisted the same way:
 *    irrigation/hour, irrigation/minute   when the daily run starts, local time (default 03:00)
 *    irrigation/maxminutes                longest any one valve may stay open (default 5)
 *    sectorN/target                       moisture % at which sector N is satisfied (default 80)
 *  ============================================================================================
 */

#include "Frugal-IoT.h"
#include "control_irrigation.h"
#include "sensor_tank.h"
#include "control_oled_ospit.h"
#include "sensor_heatsink.h"
#include "control_mppt.h"
#include "control_soc.h"
#include "control_health.h"
#include "language.h"

// Change the parameters here to match your ...
// organization, project, device name, description
System_Frugal frugal_iot(SYSTEM_FRUGAL_ORG, SYSTEM_FRUGAL_PROJECT, "ospit", "OSPIT Irrigation");

void setup() {
  setupIrrigationLanguage();

  /* Battery sensor has to come before pre_setup, all others should come after.
   *
   * 10000..15000 mV rather than the 3000..5000 default: this is a 12V lead-acid bank, not a
   * single lithium cell, so every gauge in the UX would otherwise sit pegged at maximum. The
   * divider is set per board in platformio.ini - on the FF board it is OSPIT's own 1k/15k,
   * i.e. the 0.0625 ratio in mp2.lua's Voutmeasure(), so a factor of 16.
   */
  #ifdef SENSOR_BATTERY_PIN
    frugal_iot.configure_battery(SENSOR_BATTERY_PIN, SENSOR_BATTERY_VOLTAGE_DIVIDER, 10000, 15000);
  #endif

  /* Awake all the time, on a 10 second cycle.
   *
   * Deliberately NOT a sleeping mode. Valve timing has the resolution of one wake cycle, and more
   * importantly a deep sleep in the middle of a run would abandon the run - Control_Irrigation
   * returns to idle in setup(). Control_Irrigation::allowSleep() is the hook a sleep manager will
   * use to avoid exactly that; nothing calls it yet.
   */
  frugal_iot.configure_power(Power_Loop, 10000, 10000);

  frugal_iot.pre_setup();
  syncIrrigationLanguage(frugal_iot.captive->language_code);

  // Override MQTT host, username and password if you have an "organization" other than "dev"
  frugal_iot.configure_mqtt("frugaliot.naturalinnovation.org", "dev", "public");

  // Add local wifis here, or see instructions in the wiki for adding via the /data
  //frugal_iot.wifi->addWiFi(F("mywifissid"),F("mywifipassword"));

  /* ---- Actuators: the valves, and optionally a pump and a load switch ------------------
   *
   * OSPIT has ONE output (pin 14) with two possible roles, chosen by its `pump_is_load` flag: a
   * pump the irrigation sequence drives with each valve, or a load output the low-voltage
   * disconnect opens. Here they are two independent optional pins, so a board can have either,
   * both, or neither:
   *
   *   OSPIT_PUMP_PIN  driven by Control_Irrigation whenever irrigation is running
   *                   (equivalent to OSPIT's pump_is_load = false)
   *   OSPIT_LOAD_PIN  switched off by the battery interlock below
   *                   (equivalent to OSPIT's pump_is_load = true, minus MPPT)
   *
   * On the FF board these cannot BOTH be pin 14, which is why platformio.ini defines one of them
   * there and says what the other choice would look like.
   */
  frugal_iot.actuators->add(new Actuator_Digital("valve1", "Valve 1", OSPIT_VALVE1_PIN, DEFAULT_valve_on_color));
  frugal_iot.actuators->add(new Actuator_Digital("valve2", "Valve 2", OSPIT_VALVE2_PIN, DEFAULT_valve_on_color));
  frugal_iot.actuators->add(new Actuator_Digital("valve3", "Valve 3", OSPIT_VALVE3_PIN, DEFAULT_valve_on_color));
  #ifdef OSPIT_PUMP_PIN
    frugal_iot.actuators->add(new Actuator_Digital("pump", "Pump", OSPIT_PUMP_PIN, DEFAULT_pump_on_color));
  #endif
  #ifdef OSPIT_LOAD_PIN
    frugal_iot.actuators->add(new Actuator_Digital("load", "Load", OSPIT_LOAD_PIN, DEFAULT_load_on_color));
  #endif
  #ifdef OSPIT_USB_PIN
    // A second switched output, for a USB supply. On the FF board this is the SAME PIN as valve 3
    // - OSPIT decides which it is by whether a probe answers on sector 3. Here you choose by
    // defining one or the other, and platformio.ini says so beside both.
    frugal_iot.actuators->add(new Actuator_Digital("usb", "USB", OSPIT_USB_PIN, DEFAULT_usb_on_color));
  #endif

  // ---- Sensors -------------------------------------------------------------------------
  // One RS485 bus, one probe per sector, slave ids 1..3. A probe that does not answer publishes
  // "nan", which is what makes Control_Irrigation skip that sector - the same job OSPIT's -127
  // does, but without doubling as the switch that turns an output into a USB socket.
  /* One RS485 bus, one probe per sector. A probe that does not answer publishes "nan", which is
   * what makes Control_Irrigation skip that sector - the same job OSPIT's -127 does, but without
   * doubling as the switch that turns an output into a USB socket.
   *
   * Slave ids start at 2, NOT 1. Address 1 is the factory default every probe ships with, and
   * SENSOR_SOILMODBUS_AUTOPROVISION needs it to keep meaning "not yet provisioned" - see
   * sensor/soilmodbus.h. With that flag set, commissioning is: plug in sector 2's probe, wait a
   * few cycles, plug in sector 3's, and so on IN ORDER.
   */
  System_RS485* rs485 = new System_RS485(&OSPIT_RS485_UART);
  frugal_iot.sensors->add(new Sensor_SoilModbus("soil1", "Sector 1 probe", 2, rs485, true));
  frugal_iot.sensors->add(new Sensor_SoilModbus("soil2", "Sector 2 probe", 3, rs485, true));
  frugal_iot.sensors->add(new Sensor_SoilModbus("soil3", "Sector 3 probe", 4, rs485, true));

  // Resistive float sender in the tank. Publishes "nan" if no sender is fitted, which is NOT
  // treated as an empty tank - see sensor_tank.h.
  #ifdef OSPIT_TANK_PIN
    frugal_iot.sensors->add(new Sensor_Tank("tank", "Water tank", OSPIT_TANK_PIN, true));
  #endif

  /* ---- Charge controller instrumentation (P5.1) -------------------------------------------
   *
   * MEASUREMENT ONLY - the charge control below is what acts on these. The point of the split is
   * it separately is that every one of these numbers can be checked against a multimeter before
   * any code acts on it, and a charge controller working from a wrong reading damages a battery.
   *
   * Each is behind its own #define, so a board can be instrumented one piece at a time as the
   * questions in HARDWARE-QUESTIONS.md get answered.
   */
  #ifdef OSPIT_PANEL_PIN
    /* Solar panel voltage.
     *
     * Sensor_Voltage rather than a class of its own - it is the same job as the battery reading
     * with a different divider. The diode offset is in millivolts AT THE PIN, so the drop at the
     * panel is divided down: 300 mV through a 28:1 divider is about 11. Negative because the
     * panel is HIGHER than the pin suggests. Set OSPIT_PANEL_DIODE_MV to 0 if D6 has been replaced
     * by a wire on your board - see question 2 in HARDWARE-QUESTIONS.md.
     */
    frugal_iot.sensors->add(new Sensor_Voltage("panel", "Solar Panel", OSPIT_PANEL_PIN,
      OSPIT_PANEL_DIVIDER, DEFAULT_panel_panel_min, DEFAULT_panel_panel_max,
      -(OSPIT_PANEL_DIODE_MV / OSPIT_PANEL_DIVIDER), DEFAULT_panel_panel_color, true));
  #endif

  #ifdef OSPIT_HEATSINK_PIN
    // The diode-pair heatsink sensor. Most boards seem to use a DS18B20 for this instead, in which
    // case leave OSPIT_HEATSINK_PIN undefined and the class is not compiled at all.
    frugal_iot.sensors->add(new Sensor_Heatsink("heatsink", "Heatsink", OSPIT_HEATSINK_PIN, true));
  #endif

  #ifdef OSPIT_ONEWIRE_PIN
    /* Up to three DS18B20 temperature probes on one shared wire.
     *
     * They are told apart by the unique id burned into each probe, not by position, so which is
     * which survives unplugging them - see "1-Wire" in the library's CLAUDE.md. With exactly one
     * probe on the bus it binds itself; with several, bind them from the captive portal, and the
     * choice is remembered.
     *
     * This is OSPIT's owids.lua/owread.lua arrangement, which maps the same three ids to
     * airtemp, battery_temperature and heatsink_temperature.
     */
    frugal_iot.sensors->add(new Sensor_DS18B20("airtemp", "Air Temperature", OSPIT_ONEWIRE_PIN, true));
    frugal_iot.sensors->add(new Sensor_DS18B20("batttemp", "Battery Temperature", OSPIT_ONEWIRE_PIN, true));
    frugal_iot.sensors->add(new Sensor_DS18B20("pcbtemp", "Board Temperature", OSPIT_ONEWIRE_PIN, true));
  #endif

  /* ---- Battery interlocks ----------------------------------------------------------------
   *
   * One Control_Hysteresis per thing that should give up when the battery gets low, each entirely
   * independent of the others and each behind its own #define. A board defines as many or as few
   * as it has pins for, and none of them knows about any other.
   *
   * The thresholds are what sets the ORDER things are shed in as the battery falls, and that is
   * the interesting decision:
   *
   *   USB supply      12.8 / 13.4   given up first - the least important consumer
   *   Irrigation      12.4 / 12.8   next: a pump is a big draw, and the watering can wait a day
   *   Load (router)   11.9 / 12.3   last, because losing communications means losing the ability
   *                                 to find out what went wrong
   *
   * OSPIT gates irrigation on the same low_voltage_disconnect_state as the load, i.e. both at
   * 11.9/12.3. Setting OSPIT_LVD_IRRIGATION_MV to 12100 gives that behaviour back. Shedding the
   * pump first is the deliberate difference: it is the heaviest intermittent load on the system.
   *
   * Each is written as a limit with a dead band rather than as a pair of thresholds, because that
   * is what Control_Hysteresis takes: 12.1V +/- 0.2 IS 11.9 off, 12.3 on.
   */
  #ifdef OSPIT_LOAD_PIN
    Control_Hysteresis* chload = new Control_Hysteresis("controlhysteresis-load", "Load interlock",
      OSPIT_LVD_LOAD_MV, 0, 10000, 15000, OSPIT_LVD_LOAD_HYST_MV);
    frugal_iot.controls->add(chload);
    chload->inputs[0]->wireTo(frugal_iot.messages->path("battery/battery"));
    chload->outputs[0]->wireTo(frugal_iot.messages->setPath("load/on"));
  #endif

  #ifdef OSPIT_USB_PIN
    Control_Hysteresis* chusb = new Control_Hysteresis("controlhysteresis-usb", "USB interlock",
      OSPIT_LVD_USB_MV, 0, 10000, 15000, OSPIT_LVD_USB_HYST_MV);
    frugal_iot.controls->add(chusb);
    chusb->inputs[0]->wireTo(frugal_iot.messages->path("battery/battery"));
    chusb->outputs[0]->wireTo(frugal_iot.messages->setPath("usb/on"));
  #endif

  // Not conditional: irrigation is the point of this node, so it always has an interlock of its
  // own rather than borrowing the state of an output that may not exist.
  Control_Hysteresis* chirr = new Control_Hysteresis("controlhysteresis-irrig", "Irrigation interlock",
    OSPIT_LVD_IRRIGATION_MV, 0, 10000, 15000, OSPIT_LVD_IRRIGATION_HYST_MV);
  frugal_iot.controls->add(chirr);
  chirr->inputs[0]->wireTo(frugal_iot.messages->path("battery/battery"));


  // ---- Irrigation ------------------------------------------------------------------------
  Control_Irrigation* irr = new Control_Irrigation("irrigation", "Irrigation");
  frugal_iot.controls->add(irr);
  #ifdef OSPIT_TANK_PIN
    irr->tank->wireTo(frugal_iot.messages->path("tank/tank"));
  #endif
  #ifdef OSPIT_PUMP_PIN
    irr->pump->wireTo(frugal_iot.messages->setPath("pump/on"));
  #endif
  chirr->outputs[0]->wireTo(frugal_iot.messages->setPath("irrigation/power"));

  // Sectors run in the order they are added. addSector() registers each one as a control in its
  // own right, so each gets its own portal section, MQTT topics and discovery.
  Control_Sector* s1 = irr->addSector("sector1", "Sector 1");
  s1->moisture->wireTo(frugal_iot.messages->path("soil1/humidity"));
  s1->valve->wireTo(frugal_iot.messages->setPath("valve1/on"));

  Control_Sector* s2 = irr->addSector("sector2", "Sector 2");
  s2->moisture->wireTo(frugal_iot.messages->path("soil2/humidity"));
  s2->valve->wireTo(frugal_iot.messages->setPath("valve2/on"));

  Control_Sector* s3 = irr->addSector("sector3", "Sector 3");
  s3->moisture->wireTo(frugal_iot.messages->path("soil3/humidity"));
  s3->valve->wireTo(frugal_iot.messages->setPath("valve3/on"));

  #ifdef OSPIT_MPPT_DAC_PIN
    /* ---- Solar charge control ---------------------------------------------------------------
     *
     * The DAC tells the board's charge circuit what voltage to hold the solar panel at.
     * Control_MPPT finds the best voltage by briefly unloading the panel, measuring its
     * open-circuit voltage and then asking for about 80% of it - see control_mppt.h.
     *
     * AUTOMATIC IS OFF BY DEFAULT, so out of the box a person sets `mppt/step` by hand and watches
     * what happens - that is Part H of TESTING.md. Switch `mppt/automatic` on once the readings
     * have been checked against a meter. Either way it starts at the step that charges LEAST,
     * because the DAC is an inverse throttle and the safe fallback is the top of the range.
     */
    frugal_iot.actuators->add(new Actuator_Analog("analog", "Charge DAC", OSPIT_MPPT_DAC_PIN));
    Control_MPPT* mppt = new Control_MPPT("mppt", "Charge Control");
    frugal_iot.controls->add(mppt);
    mppt->dacvolts->wireTo(frugal_iot.messages->setPath("analog/volts"));
    #ifdef OSPIT_PANEL_PIN
      mppt->panel->wireTo(frugal_iot.messages->path("panel/panel"));
    #endif
    mppt->battery->wireTo(frugal_iot.messages->path("battery/battery"));
    #ifdef OSPIT_ONEWIRE_PIN
      mppt->batttemp->wireTo(frugal_iot.messages->path("batttemp/batttemp"));
      /* The heatsink reading comes from whichever sensor this board actually has: a DS18B20
       * on the 1-Wire bus, or the diode pair on an ADC pin. Both write the same meaning, and
       * only one is ever compiled - see question 4 in HARDWARE-QUESTIONS.md.
       */
      #ifndef OSPIT_HEATSINK_PIN
        mppt->heatsink->wireTo(frugal_iot.messages->path("pcbtemp/pcbtemp"));
      #endif
    #endif
    #ifdef OSPIT_HEATSINK_PIN
      mppt->heatsink->wireTo(frugal_iot.messages->path("heatsink/heatsink"));
    #endif
  #endif

  /* ---- Reporting: how full the battery is, and how well it is holding up -------------------
   *
   * Both are REPORTING ONLY. Nothing is controlled from either, and both publish read-only - a
   * voltage-derived estimate is fine to look at and useless to charge from, which is why
   * Control_MPPT does its own measuring rather than reading these.
   *
   * State of charge freezes while the panel is above the battery, because a battery on charge
   * reads high and tracking that would just report the charger. Battery health compares the
   * overnight fall in that estimate against the load you tell it about, and refuses to report at
   * all if irrigation ran during the window - which is the flaw in OSPIT's version, since it
   * waters at 03:00 inside its own 22:00-04:00 measurement.
   */
  Control_SoC* soc = new Control_SoC("soc", "State of Charge");
  frugal_iot.controls->add(soc);
  soc->battery->wireTo(frugal_iot.messages->path("battery/battery"));
  #ifdef OSPIT_PANEL_PIN
    soc->panel->wireTo(frugal_iot.messages->path("panel/panel"));
  #endif

  Control_Health* bh = new Control_Health("batteryhealth", "Battery Health");
  frugal_iot.controls->add(bh);
  bh->soc->wireTo(frugal_iot.messages->path("soc/soc"));
  bh->active->wireTo(frugal_iot.messages->path("irrigation/active"));

  /* ---- Display ---------------------------------------------------------------------------
   *
   * Three pages in a carousel, ported from OSPIT's display.lua. It advances on its own; wire a
   * button to carousel/select/cycle, or publish to it, to step through by hand.
   */
  #ifdef ACTUATOR_OLED_WANT
    Control_Carousel* display = ospitDisplay();
    (void)display; // Nothing else to wire to it here - a button would go to carousel/select/cycle
    Control_Oled_OspitPower* powerPage = (Control_Oled_OspitPower*)display->controls[0];
    powerPage->battery->wireTo(frugal_iot.messages->path("battery/battery"));
    powerPage->soc->wireTo(frugal_iot.messages->path("soc/soc"));
    #ifdef OSPIT_PANEL_PIN
      powerPage->panel->wireTo(frugal_iot.messages->path("panel/panel"));
    #endif
    #ifdef OSPIT_MPPT_DAC_PIN
      powerPage->mpptstate->wireTo(frugal_iot.messages->path("mppt/state"));
    #endif
    Control_Oled_OspitSoil* soilPage = (Control_Oled_OspitSoil*)display->controls[1];
    soilPage->moisture1->wireTo(frugal_iot.messages->path("soil1/humidity"));
    soilPage->moisture2->wireTo(frugal_iot.messages->path("soil2/humidity"));
    soilPage->moisture3->wireTo(frugal_iot.messages->path("soil3/humidity"));
    #ifdef OSPIT_TANK_PIN
      soilPage->tank->wireTo(frugal_iot.messages->path("tank/tank"));
    #endif
    soilPage->active->wireTo(frugal_iot.messages->path("irrigation/active"));
  #endif
  // Want NTP time (or set from browser)
  frugal_iot.system->add(frugal_iot.time = new System_Time());
  // Dont change below here - should be after setup the actuators, controls and sensors
  frugal_iot.setup(); // Has to be after setup sensors and actuators and controls and system
  Serial.println(F("FrugalIoT Starting Loop"));
}

void loop() {
  frugal_iot.loop(); // Should be running watchdog.loop which will call esp_task_wdt_reset()
  syncIrrigationLanguage(frugal_iot.captive->language_code);
}
