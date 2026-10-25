// Frugal-IoT Irrigation V0.1 - ESP32-C6-MINI-1U module (DECISIONS D18).
// Based on arduino-esp32 variants/esp32c6. Differences: LED_BUILTIN is a plain LED on GPIO8,
// active LOW (to +3V3 through 1k) - not the DevKit's RGB LED; SDA/SCL are this board's I2C pins.
#ifndef Pins_Arduino_h
#define Pins_Arduino_h

#include <stdint.h>
#include "soc/soc_caps.h"

static const uint8_t LED_BUILTIN = 8;   // D8 green, active LOW - build with -D ACTUATOR_LEDBUILTIN_INVERT
#define BUILTIN_LED LED_BUILTIN         // backward compatibility
#define LED_BUILTIN LED_BUILTIN         // allow testing #ifdef LED_BUILTIN

static const uint8_t TX = 16;           // UART0, unfitted debug header J5
static const uint8_t RX = 17;

static const uint8_t SDA = 7;           // pad 16; pull-ups on 3V3_SW
static const uint8_t SCL = 14;          // pad 19

// SPI is not used on this board; generic C6 defaults kept so libraries that expect them compile.
static const uint8_t SS = 18;
static const uint8_t MOSI = 19;         // also BTN2
static const uint8_t MISO = 20;
static const uint8_t SCK = 21;

static const uint8_t A0 = 0;            // RS485 RX
static const uint8_t A1 = 1;            // V12_SENSE (12 V in x 100k/660k)
static const uint8_t A2 = 2;            // RS485 TX
static const uint8_t A3 = 3;            // VBAT_SENSE (cell / 2)
static const uint8_t A4 = 4;
static const uint8_t A5 = 5;
static const uint8_t A6 = 6;            // GPIO_A terminal

// LP I2C pins are fixed on ESP32-C6
#define WIRE1_PIN_DEFINED
static const uint8_t SDA1 = 6;
static const uint8_t SCL1 = 7;

#endif /* Pins_Arduino_h */
