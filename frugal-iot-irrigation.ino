/*
 *  Frugal IoT example - Irrigation controller
 *
 *  An irrigation controller, with optional MPPT power control. 
 *  
 *  Significant parts of this are inspired by 
 *  [OSPIT](https://www.apc.org/en/news/meet-ospit-sustainable-energy-and-irrigation-solution-community-networks)
 *  - the solar-powered irrigation controller built on the FF-ESP32-OpenMPPT board. 
 *  
 *  It currently waters a set of sectors one at a time, once a day, 
 *  each until its soil reaches a target moisture or a time limit runs out,
 *  with tank-level and battery interlocks that stop the whole run.
 * 
 *  That functionality is likely to change to meet varying needs of people using it, for example
 *  to allow multiple times a day, or per-sector variations. 
 * 
 *  Feedback on what functionality is needed is very welcome. 
 *
 *  To enable it to run on the OSPIT hardware, which is based on the Freifunk 
 *  [FF-ESP32-OpenMPPT](https://media.ccc.de/v/camp2023-57058-resilient_solar_energy_autonomous_infrastructure_with_freifunk_openmppt_controllers)
 *  board designed by Elektra Wagenrad, we've added MPPT. 
 *  In part based on some out of date code we found for it, but heavily modified. 
 * 
 *  What is here, and what is not:
 *    - irrigation, soil probes, tank gauge, valves, pump          YES
 *    - MPPT solar charge control                                  YES
 *
 *  Two boards are supported, see platformio.ini: `ff_openmppt` (the OSPIT version of the Freifunk board)
 *  and `s2_mini` (the same application on a plain dev board with no charge-controller hardware). 
 * 
 *  Adding other ESP32 boards should be as simple as copying their platformio.ini from one of the 
 *  examples in [frugal-iot](https;//github.com/mitra42/frugal-iot)
 *
 *  Ww anticipate the `s2_mini` will also evolve into a distributed version using sensors and valves
 *  connected by WiFi or LoRa.
 *
 *  ============================================================================================
 *  NOTE IRRIGATION IS OFF BY DEFAULT.
 *
 *  `irrigation/enabled` starts false - a device that opens water valves
 *  unattended should not begin doing so merely because it was flashed. 
 *  
 *  Turn it on once, from the captive portal or by publishing to `set/<device>/irrigation/enabled` = 1; 
 *
 *  Worth setting at the same time, all persisted the same way:
 *    irrigation/hour, irrigation/minute   when the daily run starts, local time (default 03:00)
 *    irrigation/maxminutes                longest any one valve may stay open (default 5)
 *    sectorN/target                       moisture % at which sector N is satisfied (default 80)
 * 
 *  All these settings are persisted in onboard LittleFS, and can also be flashed with platformio.ini 
 * 
 *  ============================================================================================
 */

#include "Frugal-IoT.h"
#include "control_irrigation.h"
#include "sensor_tank.h"
#include "control_oled_irrigation.h"
#include "sensor_heatsink.h"
#include "control_mppt.h"
#include "control_soc.h"
#include "control_health.h"
#include "language.h"

// Change the parameters here to match your ...
// organization, project, device name, description
System_Frugal frugal_iot(SYSTEM_FRUGAL_ORG, SYSTEM_FRUGAL_PROJECT, "irrigation", "Irrigation Controller");

void setup() {
  setupIrrigationLanguage();

  /* Battery sensor has to come before pre_setup, all others should come after.
   * The parameters are display parameters set in platformio.ini typically 10000..15000 mV for Lead Acid
   * For a single cell Lithium it would be 3000..5000 but this application is more likely to use multi-cell variants
   * The divider is set per board in platformio.ini - on the FF board it is OpenMPPT's own 1k/15k
   */
  #ifdef SENSOR_BATTERY_PIN
    frugal_iot.configure_battery(SENSOR_BATTERY_PIN, SENSOR_BATTERY_VOLTAGE_DIVIDER, SENSOR_BATTERY_MIN, SENSOR_BATTERY_MAX);
  #endif

  /* Awake all the time, on a 10 second cycle.
   *
   * Deliberately NOT a sleeping mode. Valve timing has the resolution of one wake cycle, and more
   * importantly a deep sleep in the middle of a run would abandon the run - Control_Irrigation
   * returns to idle in setup(). 
   * 
   * Control_Irrigation::okToSleep() is the hook used to stop a sleep, this is in progress in frugal-iot
   * and once hooked up we'll be able to use Power_Deep
   */
  frugal_iot.configure_power(Power_Loop, 10000, 10000);

  frugal_iot.pre_setup();
  syncIrrigationLanguage(frugal_iot.captive->language_code);

  // Override MQTT host, username and password if you have an "organization" other than "dev"
  frugal_iot.configure_mqtt("frugaliot.naturalinnovation.org", "dev", "public");

  // Add local wifis here, this is rarely used since a device without any wifi's can be setup 
  // via their captive portal, and will remember settings. Or have defaults flashed in /data
  //frugal_iot.wifi->addWiFi(F("mywifissid"),F("mywifipassword"));

  /* ---- Actuators: the valves, and optionally a pump and a load switch ------------------
   *
   * Two independent optional pins, so a board can have either, both, or neither:
   *   IRRIGATION_PUMP_PIN  driven by Control_Irrigation whenever irrigation is running
   *   IRRIGATION_LOAD_PIN  switched off by the battery interlock below
   * On the FF board both would be pin 14, so platformio.ini defines only one - see
   * OSPIT_COMPARISON.md for how OSPIT shares that pin.
   */
  frugal_iot.actuators->add(new Actuator_Digital("valve1", "Valve 1", IRRIGATION_VALVE1_PIN, DEFAULT_valve_on_color));
  frugal_iot.actuators->add(new Actuator_Digital("valve2", "Valve 2", IRRIGATION_VALVE2_PIN, DEFAULT_valve_on_color));
  frugal_iot.actuators->add(new Actuator_Digital("valve3", "Valve 3", IRRIGATION_VALVE3_PIN, DEFAULT_valve_on_color));
  #ifdef IRRIGATION_PUMP_PIN
    frugal_iot.actuators->add(new Actuator_Digital("pump", "Pump", IRRIGATION_PUMP_PIN, DEFAULT_pump_on_color));
  #endif
  #ifdef IRRIGATION_LOAD_PIN
    frugal_iot.actuators->add(new Actuator_Digital("load", "Load", IRRIGATION_LOAD_PIN, DEFAULT_load_on_color));
  #endif
  #ifdef IRRIGATION_USB_PIN
    // A second switched output, for a USB supply. On the FF board this is the SAME PIN as valve 3,
    // so define one or the other.
    frugal_iot.actuators->add(new Actuator_Digital("usb", "USB", IRRIGATION_USB_PIN, DEFAULT_usb_on_color));
  #endif

  // ---- Sensors -------------------------------------------------------------------------
  /* One RS485 bus, one probe per sector. A probe that does not answer publishes "nan", which is
   * what makes Control_Irrigation skip that sector 
   *
   * Slave ids start at 2, NOT 1. Address 1 is the factory default every probe ships with, and
   * SENSOR_SOILMODBUS_AUTOPROVISION needs it to keep meaning "not yet provisioned" - see
   * sensor/soilmodbus.h. With that flag set, commissioning is: plug in sector 2's probe, wait a
   * few cycles, plug in sector 3's, and so on IN ORDER.
   */
  System_RS485* rs485 = new System_RS485(&SYSTEM_RS485_UART);
  frugal_iot.sensors->add(new Sensor_SoilModbus("soil1", "Sector 1 probe", 2, rs485, true));
  frugal_iot.sensors->add(new Sensor_SoilModbus("soil2", "Sector 2 probe", 3, rs485, true));
  frugal_iot.sensors->add(new Sensor_SoilModbus("soil3", "Sector 3 probe", 4, rs485, true));

  // Resistive float sender in the tank. Publishes "nan" if no sender is fitted, which is NOT
  // treated as an empty tank - see sensor_tank.h.
  // TO-DO implement alternative ultrasonic sensor
  #ifdef SENSOR_TANK_PIN
    frugal_iot.sensors->add(new Sensor_Tank("tank", "Water tank", SENSOR_TANK_PIN, true));
  #endif

  /* ---- Charge controller instrumentation (P5.1) -------------------------------------------
   *
   * MEASUREMENT ONLY - the charge control below is what acts on these. 
   * So that each of these numbers can be checked against a multimeter before
   * any code acts on it, as a charge controller working from a wrong reading would damage a battery.
   *
   * Each is behind its own #define, so a board can be instrumented one piece at a time as the
   * questions in HARDWARE-QUESTIONS.md get answered.
   */
  #ifdef MPPT_PANEL_PIN
    /* Solar panel voltage.
     * The diode offset is in millivolts AT THE PIN, so the drop at the
     * panel is divided down: 300 mV through a 28:1 divider is about 11. Negative because the
     * panel is HIGHER than the pin suggests. 
     * On a FF board, set MPPT_PANEL_DIODE_MV to 0 if D6 has been replaced by a wire 
     * - see question 2 in HARDWARE-QUESTIONS.md.
     */
    frugal_iot.sensors->add(new Sensor_Voltage("panel", "Solar Panel", MPPT_PANEL_PIN,
      MPPT_PANEL_DIVIDER, DEFAULT_panel_panel_min, DEFAULT_panel_panel_max,
      -(MPPT_PANEL_DIODE_MV / MPPT_PANEL_DIVIDER), DEFAULT_panel_panel_color, true));
  #endif

  #ifdef SENSOR_HEATSINK_PIN
    // The diode-pair heatsink sensor. Most boards seem to use a DS18B20 for this instead, in which
    // case leave SENSOR_HEATSINK_PIN undefined and the class is not compiled at all.
    frugal_iot.sensors->add(new Sensor_Heatsink("heatsink", "Heatsink", SENSOR_HEATSINK_PIN, true));
  #endif

  #ifdef MPPT_ONEWIRE_PIN
    /* Up to three DS18B20 temperature probes on one shared wire.
     *
     * They are told apart by the unique id burned into each probe, not by position, so which is
     * which survives unplugging them - see "1-Wire" in the library's CLAUDE.md. With exactly one
     * probe on the bus it binds itself; with several, bind them from the captive portal, and the
     * choice is remembered.
     *
     * This is FF's owids.lua/owread.lua arrangement, which maps the same three ids to
     * airtemp, battery_temperature and heatsink_temperature.
     */
    frugal_iot.sensors->add(new Sensor_DS18B20("airtemp", "Air Temperature", MPPT_ONEWIRE_PIN, true));
    frugal_iot.sensors->add(new Sensor_DS18B20("batttemp", "Battery Temperature", MPPT_ONEWIRE_PIN, true));
    frugal_iot.sensors->add(new Sensor_DS18B20("pcbtemp", "Board Temperature", MPPT_ONEWIRE_PIN, true));
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
   * Shedding the pump before the router is deliberate - it is the heaviest intermittent load. OSPIT
   * sheds both at once; see OSPIT_COMPARISON.md.
   *
   * Control_Hysteresis uses a limit with a dead-band so 12.1V +/- 0.2 is 11.9v off, 12.3v on
   */
  #ifdef IRRIGATION_LOAD_PIN
    Control_Hysteresis* chload = new Control_Hysteresis("controlhysteresis-load", "Load interlock",
      IRRIGATION_LVD_LOAD_MV, 0, 10000, 15000, IRRIGATION_LVD_LOAD_HYST_MV);
    frugal_iot.controls->add(chload);
    chload->inputs[0]->wireTo(frugal_iot.messages->path("battery/battery"));
    chload->outputs[0]->wireTo(frugal_iot.messages->setPath("load/on"));
  #endif

  #ifdef IRRIGATION_USB_PIN
    Control_Hysteresis* chusb = new Control_Hysteresis("controlhysteresis-usb", "USB interlock",
      IRRIGATION_LVD_USB_MV, 0, 10000, 15000, IRRIGATION_LVD_USB_HYST_MV);
    frugal_iot.controls->add(chusb);
    chusb->inputs[0]->wireTo(frugal_iot.messages->path("battery/battery"));
    chusb->outputs[0]->wireTo(frugal_iot.messages->setPath("usb/on"));
  #endif

  // Not conditional: irrigation is the point of this node, so it always has an interlock of its
  // own rather than borrowing the state of an output that may not exist.
  Control_Hysteresis* chirr = new Control_Hysteresis("controlhysteresis-irrig", "Irrigation interlock",
    IRRIGATION_LVD_IRRIGATION_MV, 0, 10000, 15000, IRRIGATION_LVD_IRRIGATION_HYST_MV);
  frugal_iot.controls->add(chirr);
  chirr->inputs[0]->wireTo(frugal_iot.messages->path("battery/battery"));


  // ---- Irrigation ------------------------------------------------------------------------
  Control_Irrigation* irr = new Control_Irrigation("irrigation", "Irrigation");
  frugal_iot.controls->add(irr);
  #ifdef SENSOR_TANK_PIN
    irr->tank->wireTo(frugal_iot.messages->path("tank/tank"));
  #endif
  #ifdef IRRIGATION_PUMP_PIN
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

  #ifdef MPPT_DAC_PIN
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
    frugal_iot.actuators->add(new Actuator_Analog("analog", "Charge DAC", MPPT_DAC_PIN));
    Control_MPPT* mppt = new Control_MPPT("mppt", "Charge Control");
    frugal_iot.controls->add(mppt);
    mppt->dacvolts->wireTo(frugal_iot.messages->setPath("analog/volts"));
    #ifdef MPPT_PANEL_PIN
      mppt->panel->wireTo(frugal_iot.messages->path("panel/panel"));
    #endif
    mppt->battery->wireTo(frugal_iot.messages->path("battery/battery"));
    #ifdef MPPT_ONEWIRE_PIN
      mppt->batttemp->wireTo(frugal_iot.messages->path("batttemp/batttemp"));
      /* The heatsink reading comes from whichever sensor this board actually has: a DS18B20
       * on the 1-Wire bus, or the diode pair on an ADC pin. Both write the same meaning, and
       * only one is ever compiled - see question 4 in HARDWARE-QUESTIONS.md.
       */
      #ifndef SENSOR_HEATSINK_PIN
        mppt->heatsink->wireTo(frugal_iot.messages->path("pcbtemp/pcbtemp"));
      #endif
    #endif
    #ifdef SENSOR_HEATSINK_PIN
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
   * all if irrigation ran during the window.
   */
  Control_SoC* soc = new Control_SoC("soc", "State of Charge");
  frugal_iot.controls->add(soc);
  soc->battery->wireTo(frugal_iot.messages->path("battery/battery"));
  #ifdef MPPT_PANEL_PIN
    soc->panel->wireTo(frugal_iot.messages->path("panel/panel"));
  #endif

  Control_Health* bh = new Control_Health("batteryhealth", "Battery Health");
  frugal_iot.controls->add(bh);
  bh->soc->wireTo(frugal_iot.messages->path("soc/soc"));
  bh->active->wireTo(frugal_iot.messages->path("irrigation/active"));

  /* ---- Display ---------------------------------------------------------------------------
   *
   * Three pages in a carousel, based on OSPIT's display.lua. It advances on its own; wire a
   * button to carousel/select/cycle, or publish to it, to step through by hand.
   */
  #ifdef ACTUATOR_OLED_WANT
    Control_Carousel* display = ospitDisplay();
    (void)display; // Nothing else to wire to it here - a button would go to carousel/select/cycle
    Control_Oled_IrrigationPower* powerPage = (Control_Oled_IrrigationPower*)display->controls[0];
    powerPage->battery->wireTo(frugal_iot.messages->path("battery/battery"));
    powerPage->soc->wireTo(frugal_iot.messages->path("soc/soc"));
    #ifdef MPPT_PANEL_PIN
      powerPage->panel->wireTo(frugal_iot.messages->path("panel/panel"));
    #endif
    #ifdef MPPT_DAC_PIN
      powerPage->mpptstate->wireTo(frugal_iot.messages->path("mppt/state"));
    #endif
    Control_Oled_IrrigationSoil* soilPage = (Control_Oled_IrrigationSoil*)display->controls[1];
    soilPage->moisture1->wireTo(frugal_iot.messages->path("soil1/humidity"));
    soilPage->moisture2->wireTo(frugal_iot.messages->path("soil2/humidity"));
    soilPage->moisture3->wireTo(frugal_iot.messages->path("soil3/humidity"));
    #ifdef SENSOR_TANK_PIN
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
