#ifndef IRRIGATION_LANGUAGE_H
#define IRRIGATION_LANGUAGE_H

#include <Arduino.h>
#include "system/language.h"

struct IrrigationTexts {
  const __FlashStringHelper
      *Moisture,
      *Target,
      *Enable,
      *Valve,
      *StartHour,
      *StartMinute,
      *MaxMinutesPerSector,
      *Enabled,
      *TankLevel,
      *TankLevelToStart,
      *TankLevelToStop,
      *PowerOk,
      *InputPower,
      *Pump,
      *ActiveSector,
      *Battery,
      *Panel,
      *BatteryType,
      *Charge,
      *Charging,
      *DacStep,
      *Automatic,
      *ChargeEnd,
      *TemperatureCoefficient,
      *HotBattery,
      *BatteryTemperature,
      *HeatsinkTemperature,
      *PanelTarget,
      *OpenCircuit,
      *DacVolts,
      *State,
      *Capacity,
      *AverageLoad,
      *PanelWatts,
      *IrrigationActive,
      *Health,
      *StorageRatio,
      *Advice,
      *Charger,
      *Sector,
      *Tank,
      *Ip,
      *Wifi,
      *Rssi,
      *Mqtt,
      *Heap,
      *NoIp,
      *Disconnected,
      *On,
      *Off;
};

extern IrrigationTexts* irrigationT;
extern IrrigationTexts* irrigationTT[LANGUAGE_COUNT];

void setupIrrigationLanguage();
void syncIrrigationLanguage(const String& languageCode);

#endif