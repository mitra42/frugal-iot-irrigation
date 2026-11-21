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
 *  The boards supported are in platformio.ini, and listed with wiring in README.md: the OSPIT version of
 *  the Freifunk board, a plain S2 Mini dev board (on its own, or driving the irrigation daughter board),
 *  the Frugal-IoT Irrigation V0.2 board, and the Frugal-IoT sensor board driving the daughter board.
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
#include "control_irrigation_example.h"
#include "control_sector_moisture.h"
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

/* ---- How many sectors ---------------------------------------------------------------------
 *
 * Sectors 1-3 always exist. Sectors 4-7 each exist if the board defines a valve for them -
 * IRRIGATION_VALVE4_BIT (an expander pin) or IRRIGATION_VALVE4_PIN (a GPIO), and so on - so a board
 * with eight driver channels can run seven sectors and the pump just by uncommenting lines in
 * platformio.ini. Each extra sector gets its own soil probe at the next Modbus slave id.
 * The OLED's soil page still shows sectors 1-3 only.
 */
#if defined(IRRIGATION_VALVE4_BIT) || defined(IRRIGATION_VALVE4_PIN)
  #define IRRIGATION_SECTOR4
#endif
#if defined(IRRIGATION_VALVE5_BIT) || defined(IRRIGATION_VALVE5_PIN)
  #define IRRIGATION_SECTOR5
#endif
#if defined(IRRIGATION_VALVE6_BIT) || defined(IRRIGATION_VALVE6_PIN)
  #define IRRIGATION_SECTOR6
#endif
#if defined(IRRIGATION_VALVE7_BIT) || defined(IRRIGATION_VALVE7_PIN)
  #define IRRIGATION_SECTOR7
#endif

/* A valve is a pin of a TCA9534 I2C expander (IRRIGATION_RELAY_TCA9534_ADDRESS, then IRRIGATION_VALVEn_BIT
 * for which pin of it), as on the Irrigation V0.2 board and the daughter board, or a GPIO
 * (IRRIGATION_VALVEn_PIN). Either way the same actuator with the same id, so nothing that wires to it -
 * the sectors, MQTT - can tell which. N is a literal 1-7.
 */
#ifdef IRRIGATION_RELAY_TCA9534_ADDRESS
  // IRRIGATION_RELAY_INVERT for a relay board that switches on when its pin is LOW
  #ifndef IRRIGATION_RELAY_INVERT
    #define IRRIGATION_RELAY_INVERT false
  #endif
  #define IRRIGATION_VALVE(id, name, N) new Actuator_Digital_Expander(id, name, IRRIGATION_RELAY_TCA9534_ADDRESS, \
    IRRIGATION_VALVE##N##_BIT, DEFAULT_valve_on_color, IRRIGATION_RELAY_INVERT)
#else
  #define IRRIGATION_VALVE(id, name, N) new Actuator_Digital(id, name, IRRIGATION_VALVE##N##_PIN, DEFAULT_valve_on_color)
#endif

/* One sector beyond the first three: its probe, at Modbus slave id `slave`, and the sector, wired to the
 * probe and to its valve. Sectors run in the order they are added.
 */
#if defined(IRRIGATION_SECTOR4) || defined(IRRIGATION_SECTOR5) || defined(IRRIGATION_SECTOR6) || defined(IRRIGATION_SECTOR7)
static void addExtraSector(Control_Irrigation_Example* irr, System_RS485* rs485, Actuator_Digital* valve,
    const char* soilId, const char* soilName, uint8_t slave, const char* sectorId, const char* sectorName) {
  Sensor_SoilModbus* soil = new Sensor_SoilModbus(soilId, soilName, slave, rs485, true);
  frugal_iot.sensors->add(soil);
  Control_Sector_Moisture* s = irr->addSector(new Control_Sector_Moisture(sectorId, sectorName));
  s->moisture->wireFrom(soil->humidity);
  s->valve->wireTo(valve);
}
#endif

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
   *
   * The valves and pump are either on GPIOs (IRRIGATION_VALVE1_PIN...) or on the pins of a TCA9534
   * I2C expander (IRRIGATION_RELAY_TCA9534_ADDRESS, then IRRIGATION_VALVE1_BIT...) - see
   * IRRIGATION_VALVE() at the top.
   */
  Actuator_Digital *valve1, *valve2, *valve3; // Kept so the sectors below can be wired to them
  Actuator_Digital* pump = nullptr;            // Stays nullptr on a board with no pump
  frugal_iot.actuators->add(valve1 = IRRIGATION_VALVE("valve1", "Valve 1", 1));
  frugal_iot.actuators->add(valve2 = IRRIGATION_VALVE("valve2", "Valve 2", 2));
  frugal_iot.actuators->add(valve3 = IRRIGATION_VALVE("valve3", "Valve 3", 3));
  #ifdef IRRIGATION_SECTOR4
    Actuator_Digital* valve4; frugal_iot.actuators->add(valve4 = IRRIGATION_VALVE("valve4", "Valve 4", 4));
  #endif
  #ifdef IRRIGATION_SECTOR5
    Actuator_Digital* valve5; frugal_iot.actuators->add(valve5 = IRRIGATION_VALVE("valve5", "Valve 5", 5));
  #endif
  #ifdef IRRIGATION_SECTOR6
    Actuator_Digital* valve6; frugal_iot.actuators->add(valve6 = IRRIGATION_VALVE("valve6", "Valve 6", 6));
  #endif
  #ifdef IRRIGATION_SECTOR7
    Actuator_Digital* valve7; frugal_iot.actuators->add(valve7 = IRRIGATION_VALVE("valve7", "Valve 7", 7));
  #endif
  #ifdef IRRIGATION_PUMP_BIT
    frugal_iot.actuators->add(pump = new Actuator_Digital_Expander("pump", "Pump", IRRIGATION_RELAY_TCA9534_ADDRESS, IRRIGATION_PUMP_BIT, DEFAULT_pump_on_color, IRRIGATION_RELAY_INVERT));
  #endif
  #ifdef IRRIGATION_PUMP_PIN
    frugal_iot.actuators->add(pump = new Actuator_Digital("pump", "Pump", IRRIGATION_PUMP_PIN, DEFAULT_pump_on_color));
  #endif
  #ifdef IRRIGATION_LOAD_PIN
    Actuator_Digital* load = new Actuator_Digital("load", "Load", IRRIGATION_LOAD_PIN, DEFAULT_load_on_color);
    frugal_iot.actuators->add(load);
  #endif
  #ifdef IRRIGATION_USB_PIN
    // A second switched output, for a USB supply. On the FF board this is the SAME PIN as valve 3,
    // so define one or the other.
    Actuator_Digital* usb = new Actuator_Digital("usb", "USB", IRRIGATION_USB_PIN, DEFAULT_usb_on_color);
    frugal_iot.actuators->add(usb);
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
  Sensor_SoilModbus* soil1 = new Sensor_SoilModbus("soil1", "Sector 1 probe", 2, rs485, true);
  frugal_iot.sensors->add(soil1);
  Sensor_SoilModbus* soil2 = new Sensor_SoilModbus("soil2", "Sector 2 probe", 3, rs485, true);
  frugal_iot.sensors->add(soil2);
  Sensor_SoilModbus* soil3 = new Sensor_SoilModbus("soil3", "Sector 3 probe", 4, rs485, true);
  frugal_iot.sensors->add(soil3);

  // Resistive float sender in the tank. Publishes "nan" if no sender is fitted, which is NOT
  // treated as an empty tank - see sensor_tank.h.
  // TO-DO implement alternative ultrasonic sensor
  #ifdef SENSOR_TANK_PIN
    Sensor_Tank* tank = new Sensor_Tank("tank", "Water tank", SENSOR_TANK_PIN, true);
    frugal_iot.sensors->add(tank);
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
    Sensor_Voltage* panel = new Sensor_Voltage("panel", "Solar Panel", MPPT_PANEL_PIN,
      MPPT_PANEL_DIVIDER, DEFAULT_panel_panel_min, DEFAULT_panel_panel_max,
      -(MPPT_PANEL_DIODE_MV / MPPT_PANEL_DIVIDER), DEFAULT_panel_panel_color, true);
    frugal_iot.sensors->add(panel);
  #endif

  #ifdef SENSOR_HEATSINK_PIN
    // The diode-pair heatsink sensor. Most boards seem to use a DS18B20 for this instead, in which
    // case leave SENSOR_HEATSINK_PIN undefined and the class is not compiled at all.
    Sensor_Heatsink* heatsink = new Sensor_Heatsink("heatsink", "Heatsink", SENSOR_HEATSINK_PIN, true);
    frugal_iot.sensors->add(heatsink);
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
    Sensor_DS18B20* batttemp = new Sensor_DS18B20("batttemp", "Battery Temperature", MPPT_ONEWIRE_PIN, true);
    frugal_iot.sensors->add(batttemp);
    Sensor_DS18B20* pcbtemp = new Sensor_DS18B20("pcbtemp", "Board Temperature", MPPT_ONEWIRE_PIN, true);
    frugal_iot.sensors->add(pcbtemp);
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
    chload->wireFrom(frugal_iot.battery)->wireTo(load); // battery "now" -> "out" -> load "on"
  #endif

  #ifdef IRRIGATION_USB_PIN
    Control_Hysteresis* chusb = new Control_Hysteresis("controlhysteresis-usb", "USB interlock",
      IRRIGATION_LVD_USB_MV, 0, 10000, 15000, IRRIGATION_LVD_USB_HYST_MV);
    frugal_iot.controls->add(chusb);
    chusb->wireFrom(frugal_iot.battery)->wireTo(usb);
  #endif

  // Not conditional: irrigation is the point of this node, so it always has an interlock of its
  // own rather than borrowing the state of an output that may not exist.
  Control_Hysteresis* chirr = new Control_Hysteresis("controlhysteresis-irrig", "Irrigation interlock",
    IRRIGATION_LVD_IRRIGATION_MV, 0, 10000, 15000, IRRIGATION_LVD_IRRIGATION_HYST_MV);
  frugal_iot.controls->add(chirr);
  chirr->wireFrom(frugal_iot.battery);


  // ---- Irrigation ------------------------------------------------------------------------
  // Composes its own blockers - irrigation-tank and irrigation-power - which are wired here.
  Control_Irrigation_Example* irr = new Control_Irrigation_Example("irrigation", "Irrigation");
  frugal_iot.controls->add(irr);
  #ifdef SENSOR_TANK_PIN
    irr->tankBlocker->tank->wireFrom(tank);
  #endif
  #if defined(IRRIGATION_PUMP_PIN) || defined(IRRIGATION_PUMP_BIT)
    irr->pump->wireTo(pump);
  #endif
  chirr->wireTo(irr->powerBlocker->power);

  /* Sectors run in the order they are added. addSector() registers each one as a control in its
   * own right, so each gets its own portal section, MQTT topics and discovery. Each can be a
   * different Control_Sector subclass - these are all moisture-driven, as OSPIT's were.
   */
  Control_Sector_Moisture* s1 = irr->addSector(new Control_Sector_Moisture("sector1", "Sector 1"));
  s1->moisture->wireFrom(soil1->humidity);
  s1->valve->wireTo(valve1);

  Control_Sector_Moisture* s2 = irr->addSector(new Control_Sector_Moisture("sector2", "Sector 2"));
  s2->moisture->wireFrom(soil2->humidity);
  s2->valve->wireTo(valve2);

  Control_Sector_Moisture* s3 = irr->addSector(new Control_Sector_Moisture("sector3", "Sector 3"));
  s3->moisture->wireFrom(soil3->humidity);
  s3->valve->wireTo(valve3);

  // Sectors 4-7, where the board defines a valve for them (see the top): probes at slave ids 5-8
  #ifdef IRRIGATION_SECTOR4
    addExtraSector(irr, rs485, valve4, "soil4", "Sector 4 probe", 5, "sector4", "Sector 4");
  #endif
  #ifdef IRRIGATION_SECTOR5
    addExtraSector(irr, rs485, valve5, "soil5", "Sector 5 probe", 6, "sector5", "Sector 5");
  #endif
  #ifdef IRRIGATION_SECTOR6
    addExtraSector(irr, rs485, valve6, "soil6", "Sector 6 probe", 7, "sector6", "Sector 6");
  #endif
  #ifdef IRRIGATION_SECTOR7
    addExtraSector(irr, rs485, valve7, "soil7", "Sector 7 probe", 8, "sector7", "Sector 7");
  #endif

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
    Actuator_Analog* dac = new Actuator_Analog("analog", "Charge DAC", MPPT_DAC_PIN);
    frugal_iot.actuators->add(dac);
    Control_MPPT* mppt = new Control_MPPT("mppt", "Charge Control");
    frugal_iot.controls->add(mppt);
    mppt->dacvolts->wireTo(dac);
    #ifdef MPPT_PANEL_PIN
      mppt->panel->wireFrom(panel);
    #endif
    mppt->battery->wireFrom(frugal_iot.battery);
    #ifdef MPPT_ONEWIRE_PIN
      mppt->batttemp->wireFrom(batttemp);
      /* The heatsink reading comes from whichever sensor this board actually has: a DS18B20
       * on the 1-Wire bus, or the diode pair on an ADC pin. Both write the same meaning, and
       * only one is ever compiled - see question 4 in HARDWARE-QUESTIONS.md.
       */
      #ifndef SENSOR_HEATSINK_PIN
        mppt->heatsink->wireFrom(pcbtemp);
      #endif
    #endif
    #ifdef SENSOR_HEATSINK_PIN
      mppt->heatsink->wireFrom(heatsink);
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
  soc->battery->wireFrom(frugal_iot.battery);
  #ifdef MPPT_PANEL_PIN
    soc->panel->wireFrom(panel);
  #endif

  Control_Health* bh = new Control_Health("batteryhealth", "Battery Health");
  frugal_iot.controls->add(bh);
  bh->soc->wireFrom(soc->soc);
  bh->active->wireFrom(irr->active);

  /* ---- Display ---------------------------------------------------------------------------
   *
   * Three pages in a carousel, based on OSPIT's display.lua. It advances on its own; wire a
   * button to carousel/select/cycle, or publish to it, to step through by hand.
   */
  #ifdef ACTUATOR_OLED_WANT
    Control_Carousel* display = ospitDisplay();
    (void)display; // Nothing else to wire to it here - a button would go to carousel/select/cycle
    Control_Oled_IrrigationPower* powerPage = (Control_Oled_IrrigationPower*)display->controls[0];
    powerPage->battery->wireFrom(frugal_iot.battery);
    powerPage->soc->wireFrom(soc->soc);
    #ifdef MPPT_PANEL_PIN
      powerPage->panel->wireFrom(panel);
    #endif
    #ifdef MPPT_DAC_PIN
      powerPage->mpptstate->wireFrom(mppt->state);
    #endif
    Control_Oled_IrrigationSoil* soilPage = (Control_Oled_IrrigationSoil*)display->controls[1];
    soilPage->moisture1->wireFrom(soil1->humidity);
    soilPage->moisture2->wireFrom(soil2->humidity);
    soilPage->moisture3->wireFrom(soil3->humidity);
    #ifdef SENSOR_TANK_PIN
      soilPage->tank->wireFrom(tank);
    #endif
    soilPage->active->wireFrom(irr->active);
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
