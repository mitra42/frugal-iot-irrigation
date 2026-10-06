/* The status display - three pages, based on OSPIT's display.lua (differences in
 * OSPIT_COMPARISON.md).
 *
 * The pages are three Control_Oled subclasses in a Control_Carousel, so they can also be selected
 * by hand (a button, or publishing to carousel/select) rather than only cycling.
 *
 *   Page 1  Control_Oled_IrrigationPower    battery
 *   Page 2  Control_Oled_IrrigationSoil     the sector moistures and the tank level
 *   Page 3  Control_Oled_IrrigationNet      IP, WiFi, MQTT
 *
 * A missing reading prints "--", for a sector with no probe and for a tank with no sender.
 *
 * The display is the I2C SSD1306 on pins 21/22. It does NOT conflict with the RS485 probes; only
 * the SSD1327 SPI panel does, because that needs pins 16/17.
 */

#ifndef CONTROL_OLED_IRRIGATION_H
#define CONTROL_OLED_IRRIGATION_H

#include "_settings.h"

#ifdef ACTUATOR_OLED_WANT

#include "control/oled.h"
#include "control/carousel.h"

/* Page 1 - the power system: how full the battery is, and what the charger is doing.
 *
 * On a board with no charge control the panel and state lines simply read "--", so the page is
 * still worth having; nothing here is conditional.
 */
class Control_Oled_IrrigationPower : public Control_Oled {
  public:
    INfloat* battery;
    INfloat* soc;    // Percent, from Control_SoC
    INfloat* panel;  // Panel volts in mV, or nothing on a board with no panel sensor
    INtext*  mpptstate; // Control_MPPT's state word - "tracking", "too hot" and so on
    Control_Oled_IrrigationPower();
    void act() override;
};

// Page 2 - what the irrigation actually runs on: one line per sector, plus the tank.
class Control_Oled_IrrigationSoil : public Control_Oled {
  public:
    // Three, matching the three sectors. A node with a different number wants a different page -
    // this is an example, and the point is that it is short enough to edit.
    INfloat* moisture1;
    INfloat* moisture2;
    INfloat* moisture3;
    INfloat* tank;
    INuint16* active; // Which sector is watering right now, 0 for none
    Control_Oled_IrrigationSoil();
    void act() override;
};

// Page 3 - connectivity, as display.lua's third page
class Control_Oled_IrrigationNet : public Control_Oled {
  public:
    Control_Oled_IrrigationNet();
    void act() override;
};

/* Build all three, add them to frugal_iot.controls and to a carousel, and return the carousel.
 *
 * Only the selected page is `enabled`, which is what stops three controls fighting over one
 * screen - Control_Carousel::act() flips that as the selection moves.
 */
Control_Carousel* ospitDisplay();

#endif // ACTUATOR_OLED_WANT
#endif // CONTROL_OLED_IRRIGATION_H
