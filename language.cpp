#include "language.h"

IrrigationTexts* irrigationT;
IrrigationTexts* irrigationTT[LANGUAGE_COUNT];

void setupIrrigationLanguage() {
  static IrrigationTexts english {
    F("Moisture"), F("Target"), F("Enable"), F("Valve"),
    F("Start hour"), F("Start minute"), F("Max minutes per sector"),
    F("Enabled"), F("Tank level"), F("Tank level to start"),
    F("Tank level to stop"), F("Power ok"), F("Input power"), F("Pump"),
    F("Active sector"), F("Battery"), F("Panel"), F("Battery type"),
    F("Charge"), F("Charging"), F("DAC step"), F("Automatic"),
    F("Charge end"), F("Temperature coefficient"), F("Hot battery"),
    F("Battery temp"), F("Heatsink temp"), F("Panel target"),
    F("Open circuit"), F("DAC volts"), F("State"), F("Capacity Ah"),
    F("Average load A"), F("Panel watts"), F("Irrigation active"),
    F("Health"), F("Storage ratio"), F("Advice"), F("Charger"),
    F("Sector"), F("Tank"), F("IP"), F("WiFi"), F("RSSI"), F("MQTT"),
    F("Heap"), F("no-ip"), F("disconnected"), F("on"), F("off")
  };
  irrigationTT[Language_EN] = &english;

  #if defined(LANGUAGE_FR) || defined(LANGUAGE_ALL)
    static IrrigationTexts french {
      F("Humidite"), F("Cible"), F("Activer"), F("Vanne"),
      F("Heure de debut"), F("Minute de debut"), F("Minutes max par secteur"),
      F("Active"), F("Niveau du reservoir"), F("Niveau pour demarrer"),
      F("Niveau pour arreter"), F("Alimentation OK"), F("Puissance d entree"), F("Pompe"),
      F("Secteur actif"), F("Batterie"), F("Panneau"), F("Type de batterie"),
      F("Charge"), F("En charge"), F("Etape DAC"), F("Automatique"),
      F("Fin de charge"), F("Coefficient de temperature"), F("Batterie chaude"),
      F("Temperature batterie"), F("Temperature dissipateur"), F("Cible panneau"),
      F("Circuit ouvert"), F("Tension DAC"), F("Etat"), F("Capacite Ah"),
      F("Courant moyen A"), F("Puissance panneau"), F("Irrigation active"),
      F("Etat de sante"), F("Ratio de stockage"), F("Conseil"), F("Chargeur"),
      F("Secteur"), F("Reservoir"), F("IP"), F("WiFi"), F("RSSI"), F("MQTT"),
      F("Memoire"), F("pas d IP"), F("deconnecte"), F("active"), F("desactive")
    };
    irrigationTT[Language_FR] = &french;
  #endif

  #if defined(LANGUAGE_SP) || defined(LANGUAGE_ALL)
    static IrrigationTexts spanish {
      F("Humedad"), F("Objetivo"), F("Activar"), F("Valvula"),
      F("Hora de inicio"), F("Minuto de inicio"), F("Minutos max por sector"),
      F("Activado"), F("Nivel del tanque"), F("Nivel para iniciar"),
      F("Nivel para detener"), F("Alimentacion OK"), F("Potencia de entrada"), F("Bomba"),
      F("Sector activo"), F("Bateria"), F("Panel"), F("Tipo de bateria"),
      F("Carga"), F("Cargando"), F("Paso DAC"), F("Automatico"),
      F("Fin de carga"), F("Coeficiente de temperatura"), F("Bateria caliente"),
      F("Temperatura de bateria"), F("Temperatura del disipador"), F("Objetivo del panel"),
      F("Circuito abierto"), F("Voltios DAC"), F("Estado"), F("Capacidad Ah"),
      F("Carga media A"), F("Vatios del panel"), F("Riego activo"),
      F("Salud"), F("Relacion de almacenamiento"), F("Consejo"), F("Cargador"),
      F("Sector"), F("Tanque"), F("IP"), F("WiFi"), F("RSSI"), F("MQTT"),
      F("Memoria"), F("sin IP"), F("desconectado"), F("activado"), F("desactivado")
    };
    irrigationTT[Language_SP] = &spanish;
  #endif

  #if defined(LANGUAGE_DE) || defined(LANGUAGE_ALL)
    static IrrigationTexts german {
      F("Feuchtigkeit"), F("Ziel"), F("Aktivieren"), F("Ventil"),
      F("Startstunde"), F("Startminute"), F("Max Minuten pro Sektor"),
      F("Aktiviert"), F("Tankstand"), F("Startniveau"),
      F("Stoppniveau"), F("Strom OK"), F("Eingangsleistung"), F("Pumpe"),
      F("Aktiver Sektor"), F("Batterie"), F("Panel"), F("Batterietyp"),
      F("Ladung"), F("Laden"), F("DAC-Schritt"), F("Automatisch"),
      F("Ladeende"), F("Temperaturkoeffizient"), F("Heisse Batterie"),
      F("Batterietemperatur"), F("Kuehlkoerpertemperatur"), F("Panelziel"),
      F("Leerlaufspannung"), F("DAC-Spannung"), F("Status"), F("Kapazitaet Ah"),
      F("Durchschnittslast A"), F("Panelleistung"), F("Bewässerung aktiv"),
      F("Zustand"), F("Speicherverhaeltnis"), F("Hinweis"), F("Ladegeraet"),
      F("Sektor"), F("Tank"), F("IP"), F("WLAN"), F("RSSI"), F("MQTT"),
      F("Heap"), F("keine IP"), F("getrennt"), F("ein"), F("aus")
    };
    irrigationTT[Language_DE] = &german;
  #endif

  #if defined(LANGUAGE_NL) || defined(LANGUAGE_ALL)
    static IrrigationTexts dutch {
      F("Vochtigheid"), F("Doel"), F("Inschakelen"), F("Klep"),
      F("Startuur"), F("Startminuut"), F("Max minuten per sector"),
      F("Ingeschakeld"), F("Tankniveau"), F("Startniveau"),
      F("Stopniveau"), F("Stroom OK"), F("Ingangsvermogen"), F("Pomp"),
      F("Actieve sector"), F("Accu"), F("Paneel"), F("Accutype"),
      F("Lading"), F("Laden"), F("DAC-stap"), F("Automatisch"),
      F("Einde laden"), F("Temperatuurcoefficient"), F("Warme accu"),
      F("Accutemperatuur"), F("Koellichaamtemperatuur"), F("Paneeldoel"),
      F("Open circuit"), F("DAC-spanning"), F("Status"), F("Capaciteit Ah"),
      F("Gemiddelde belasting A"), F("Paneelvermogen"), F("Irrigatie actief"),
      F("Gezondheid"), F("Opslagverhouding"), F("Advies"), F("Lader"),
      F("Sector"), F("Tank"), F("IP"), F("WiFi"), F("RSSI"), F("MQTT"),
      F("Heap"), F("geen IP"), F("verbinding verbroken"), F("aan"), F("uit")
    };
    irrigationTT[Language_NL] = &dutch;
  #endif

  #if defined(LANGUAGE_ID) || defined(LANGUAGE_ALL)
    static IrrigationTexts indonesian {
      F("Kelembapan"), F("Target"), F("Aktifkan"), F("Katup"),
      F("Jam mulai"), F("Menit mulai"), F("Menit maksimum per sektor"),
      F("Diaktifkan"), F("Tingkat tangki"), F("Tingkat untuk mulai"),
      F("Tingkat untuk berhenti"), F("Daya OK"), F("Daya masuk"), F("Pompa"),
      F("Sektor aktif"), F("Baterai"), F("Panel"), F("Jenis baterai"),
      F("Pengisian"), F("Sedang mengisi"), F("Langkah DAC"), F("Otomatis"),
      F("Akhir pengisian"), F("Koefisien suhu"), F("Baterai panas"),
      F("Suhu baterai"), F("Suhu heatsink"), F("Target panel"),
      F("Sirkuit terbuka"), F("Volt DAC"), F("Status"), F("Kapasitas Ah"),
      F("Beban rata-rata A"), F("Daya panel"), F("Irigasi aktif"),
      F("Kesehatan"), F("Rasio penyimpanan"), F("Saran"), F("Pengisi daya"),
      F("Sektor"), F("Tangki"), F("IP"), F("WiFi"), F("RSSI"), F("MQTT"),
      F("Heap"), F("tanpa IP"), F("terputus"), F("aktif"), F("mati")
    };
    irrigationTT[Language_ID] = &indonesian;
  #endif

  #if defined(LANGUAGE_HI) || defined(LANGUAGE_ALL)
    static IrrigationTexts hindi {
      F("नमी"), F("लक्ष्य"), F("सक्षम करें"), F("वाल्व"),
      F("प्रारंभ घंटा"), F("प्रारंभ मिनट"), F("प्रति सेक्टर अधिकतम मिनट"),
      F("सक्षम"), F("टैंक स्तर"), F("प्रारंभ स्तर"),
      F("रोकने का स्तर"), F("पावर ठीक है"), F("इनपुट पावर"), F("पंप"),
      F("सक्रिय सेक्टर"), F("बैटरी"), F("पैनल"), F("बैटरी प्रकार"),
      F("चार्ज"), F("चार्ज हो रहा है"), F("DAC चरण"), F("स्वचालित"),
      F("चार्ज समाप्त"), F("तापमान गुणांक"), F("गर्म बैटरी"),
      F("बैटरी तापमान"), F("हीटसिंक तापमान"), F("पैनल लक्ष्य"),
      F("ओपन सर्किट"), F("DAC वोल्ट"), F("स्थिति"), F("क्षमता Ah"),
      F("औसत लोड A"), F("पैनल वाट"), F("सिंचाई सक्रिय"),
      F("स्वास्थ्य"), F("भंडारण अनुपात"), F("सलाह"), F("चार्जर"),
      F("सेक्टर"), F("टैंक"), F("IP"), F("वाई-फ़ाई"), F("RSSI"), F("MQTT"),
      F("हीप"), F("IP नहीं"), F("डिस्कनेक्टेड"), F("चालू"), F("बंद")
    };
    irrigationTT[Language_HI] = &hindi;
  #endif

  irrigationT = irrigationTT[Language_EN];
}

void syncIrrigationLanguage(const String& code) {
  if (code.length() > 0) {
    if (code == "EN") {
      irrigationT = irrigationTT[Language_EN];
    }
    #if defined(LANGUAGE_FR) || defined(LANGUAGE_ALL)
      else if (code == "FR") {
        irrigationT = irrigationTT[Language_FR];
      }
    #endif
    #if defined(LANGUAGE_SP) || defined(LANGUAGE_ALL)
      else if (code == "SP") {
        irrigationT = irrigationTT[Language_SP];
      }
    #endif
    #if defined(LANGUAGE_DE) || defined(LANGUAGE_ALL)
      else if (code == "DE") {
        irrigationT = irrigationTT[Language_DE];
      }
    #endif
    #if defined(LANGUAGE_NL) || defined(LANGUAGE_ALL)
      else if (code == "NL") {
        irrigationT = irrigationTT[Language_NL];
      }
    #endif
    #if defined(LANGUAGE_ID) || defined(LANGUAGE_ALL)
      else if (code == "ID") {
        irrigationT = irrigationTT[Language_ID];
      }
    #endif
    #if defined(LANGUAGE_HI) || defined(LANGUAGE_ALL)
      else if (code == "HI") {
        irrigationT = irrigationTT[Language_HI];
      }
    #endif
  }
}