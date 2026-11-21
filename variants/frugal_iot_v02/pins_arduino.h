// Frugal-IoT sensor board V0.2 - ESP32-C3-WROOM-02U module (frugal-iot-hw-sensor DECISIONS D3).
// COPIED from frugal-iot-hw-sensor/firmware/variants/frugal_iot_v02/ - change it there, then copy it here.
// Based on arduino-esp32 variants/esp32c3. Differences: LED_BUILTIN is a plain LED on GPIO8,
// active LOW (to +3V3 through 1k) - not the DevKit's RGB LED; SDA/SCL are this board's I2C pins.
#ifndef Pins_Arduino_h
#define Pins_Arduino_h

#include <stdint.h>
#include "soc/soc_caps.h"

static const uint8_t LED_BUILTIN = 8;   // D4 green, active LOW (esp32-c3-devkitm-1 => library inverts it)
#define BUILTIN_LED LED_BUILTIN         // backward compatibility
#define LED_BUILTIN LED_BUILTIN         // allow testing #ifdef LED_BUILTIN

static const uint8_t TX = 21;           // UART0 -> RS485 DI (U5), or J3 pin 3 with JP3 re-bridged
static const uint8_t RX = 20;           // UART0 <- RS485 RO (U5), or J3 pin 2 with JP2 re-bridged

static const uint8_t SDA = 6;           // J2 pin 2; pull-ups on 3V3_SW
static const uint8_t SCL = 7;           // J2 pin 3

// SPI is not used on this board; generic C3 defaults kept so libraries that expect them compile.
static const uint8_t SS = 7;
static const uint8_t MOSI = 6;
static const uint8_t MISO = 5;
static const uint8_t SCK = 4;

static const uint8_t A0 = 0;            // SENS1, J2 pin 6
static const uint8_t A1 = 1;            // SENS2, J2 pin 9
static const uint8_t A2 = 2;            // GPIO2, J13 pin 6 (strap: must be high at reset)
static const uint8_t A3 = 3;            // VBAT_SENSE (cell / 2)
static const uint8_t A4 = 4;            // GPIO4, J13 pin 9
static const uint8_t A5 = 5;            // nRAIL_EN - not an analog input on this board

#endif /* Pins_Arduino_h */
