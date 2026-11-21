"""Circuit definition for the generic ESP32 I/O board (schematic phase).
Each part: dict(prefix, lib, value, fp, nets{pin:net}, dnp, lcsc, mpn, block, rot)
net 'NC' => no-connect marker. Power nets drawn with power symbols: GND, +3V3, +12V.
"""
P = []
def part(prefix, lib, value, fp, nets, block, dnp=False, lcsc='', mpn='', rot=None, note=''):
    P.append(dict(prefix=prefix, lib=lib, value=value, fp=fp, nets=nets, block=block,
                  dnp=dnp, lcsc=lcsc, mpn=mpn, rot=rot, note=note))
def GAP(prefix):
    """A reference number that belonged to a removed part. References are numbered in this file's order, so
    removing a part would renumber everything after it - including the valve channels that place.py and
    valve_route.py name, and the unnamed nets KiCad names after them (Net-(D10-A)). Kept as a gap instead."""
    P.append(dict(prefix=prefix, gap=True))

R06 = 'Resistor_SMD:R_0603_1608Metric'; C06 = 'Capacitor_SMD:C_0603_1608Metric'
C12 = 'Capacitor_SMD:C_1206_3216Metric'; LED06 = 'LED_SMD:LED_0603_1608Metric'; LED08 = 'LED_SMD:LED_0805_2012Metric'
SMA = 'Diode_SMD:D_SMA'; SOT23 = 'Package_TO_SOT_SMD:SOT-23'
TB508 = 'irrigation:TerminalBlock_KF128-5.08-2P'   # project footprint, KF128 drawing (D79); was Phoenix MKDS-1,5-2-5.08
TB254 = 'TerminalBlock:TerminalBlock_Xinya_XY308-2.54-{n}P_1x0{n}_P2.54mm_Horizontal'
HDR = 'Connector_PinHeader_2.54mm:PinHeader_1x0{n}_P2.54mm_Vertical'
BTN = 'Button_Switch_SMD:SW_Push_1P1T_XKB_TS-1187A'
SJ = 'Jumper:SolderJumper-2_P1.3mm_Open_RoundedPad1.0x1.5mm'
SJB = 'Jumper:SolderJumper-2_P1.3mm_Bridged_RoundedPad1.0x1.5mm'

RES = {'10k': 'C25804', '100k': 'C25803', '1k': 'C21190', '4.7k': 'C23162', '5.1k': 'C23186',
       '1M': 'C22935', '120R': 'C22787', '100R': 'C22775', '0R': 'C21189', '560k': 'C23203', '680R': 'C23228'}
CAP = {'100nF': 'C14663', '1uF': 'C15849', '10uF': 'C19702'}

def R(v, a, b, blk, dnp=False, note=''):
    part('R', 'Device:R', v, R06, {'1': a, '2': b}, blk, dnp, RES.get(v, ''), note=note)
def C(v, a, b, blk, fp=C06, lcsc=None, dnp=False):
    part('C', 'Device:C', v, fp, {'1': a, '2': b}, blk, dnp, CAP.get(v, '') if lcsc is None else lcsc)
def LED(col, anode, cathode, blk):  # both JLCPCB Basic: red KT-0603R, green KT-0805G (no Basic 0603 green)
    part('D', 'Device:LED', col, {'RED': LED06, 'GREEN': LED08}[col], {'2': anode, '1': cathode}, blk, rot=180,
         lcsc={'RED': 'C2286', 'GREEN': 'C2297'}[col], mpn={'RED': 'KT-0603R', 'GREEN': 'KT-0805G'}[col])
def SCH(anode, cathode, blk, typ='SS34'):  # SMA Schottky: SS34 (3 A) or SS54 (5 A), both Basic
    part('D', 'Device:D_Schottky', typ, SMA, {'2': anode, '1': cathode}, blk,
         lcsc={'SS34': 'C8678', 'SS54': 'C22452'}[typ], mpn=typ, rot=180)
def PFET(g, s, d, blk):
    part('Q', 'Transistor_FET:AO3401A', 'AO3401A', SOT23, {'1': g, '2': s, '3': d}, blk, lcsc='C15127')
def NFET(g, s, d, blk, typ='2N7002'):
    part('Q', f'Transistor_FET:{typ}', typ, SOT23, {'1': g, '2': s, '3': d}, blk,
         lcsc={'2N7002': 'C8545', 'BSS138': 'C78284', 'AO3400A': 'C20917'}[typ])
def BUTTON(a, b, blk, val):
    part('SW', 'Switch:SW_Push', val, BTN, {'1': a, '2': b}, blk, lcsc='C318884', mpn='TS-1187A-B-A-B')

# ---------------- USB-C input ----------------
B = 'usb'
part('J', 'Connector:USB_C_Receptacle_USB2.0_16P', 'USB-C', 'Connector_USB:USB_C_Receptacle_HRO_TYPE-C-31-M-12',
     {'A1': 'GND', 'B1': 'GND', 'A12': 'GND', 'B12': 'GND', 'A4': 'VBUS', 'A9': 'VBUS', 'B4': 'VBUS', 'B9': 'VBUS',
      'A5': 'CC1', 'B5': 'CC2', 'A6': 'USB_D_P', 'B6': 'USB_D_P', 'A7': 'USB_D_N', 'B7': 'USB_D_N',
      'A8': 'NC', 'B8': 'NC', 'SH': 'GND'}, B, lcsc='C165948', mpn='TYPE-C-31-M-12')
R('5.1k', 'CC1', 'GND', B); R('5.1k', 'CC2', 'GND', B)
part('U', 'Power_Protection:USBLC6-2SC6', 'USBLC6-2SC6', 'Package_TO_SOT_SMD:SOT-23-6',
     {'1': 'USB_D_N', '6': 'USB_D_N', '3': 'USB_D_P', '4': 'USB_D_P', '2': 'GND', '5': 'VBUS'}, B, lcsc='C7519')
SCH('VBUS', '+5V', B)
R('0R', 'USB_D_N', 'USB_C6_D_N', B, note='Fit for C6 module')
R('0R', 'USB_D_P', 'USB_C6_D_P', B, note='Fit for C6 module')
R('0R', 'USB_D_N', 'USB_C3_D_N', B, dnp=True, note='Fit for C3 module')
R('0R', 'USB_D_P', 'USB_C3_D_P', B, dnp=True, note='Fit for C3 module')

# ---------------- 12 V input + buck ----------------
B = 'v12'
part('J', 'Connector:Screw_Terminal_01x02', '12V IN', TB508.format(n=2), {'1': '12V_IN', '2': 'GND'}, B, lcsc='C474952', mpn='KF128-5.08-2P')
# Resettable fuse, then reverse-polarity diode (D77). The fuse is for a shorted field cable fed from a battery,
# not a current budget: 3 A hold, 5 A trip, ~4 s. It MUST be rated >= 16 V - most 1812 PTCs at JLCPCB are
# 6-8 V and cannot reliably interrupt 12 V. Ahead of the TVS, so a TVS conducting for long trips it.
part('F', 'Device:Polyfuse', '3A 16V', 'Fuse:Fuse_1812_4532Metric', {'1': '12V_IN', '2': '12V_FUSED'}, B,
     lcsc='C702820', mpn='SMD1812P300TF/16')
SCH('12V_FUSED', '+12V', B, typ='SS54')   # 5 A: all valve current passes through it (D77)
part('D', 'Diode:SMAJ15A', 'SMAJ15A', SMA, {'1': '+12V', '2': 'GND'}, B, lcsc='C19077535', mpn='SMAJ15A')
R('560k', '+12V', 'V12_SENSE', B); R('100k', 'V12_SENSE', 'GND', B); C('100nF', 'V12_SENSE', 'GND', B)
part('U', 'Regulator_Switching:AP63205WU', 'AP63205WU', 'Package_TO_SOT_SMD:TSOT-23-6',
     {'3': '+12V', '2': '+12V', '4': 'GND', '5': 'BUCK_SW', '6': 'BUCK_BST', '1': '5V_BUCK'}, B, lcsc='C2071056', mpn='AP63205WU-7')
C('10uF 25V', '+12V', 'GND', B, fp=C12, lcsc='C13585'); C('10uF 25V', '+12V', 'GND', B, fp=C12, lcsc='C13585')
C('100nF', '+12V', 'GND', B)
C('100nF', 'BUCK_BST', 'BUCK_SW', B)
part('L', 'Device:L', '4.7uH', 'Inductor_SMD:L_Sunlord_SWPA5040S', {'1': 'BUCK_SW', '2': '5V_BUCK'}, B, lcsc='C305174', mpn='SWPA5040S4R7NT')
C('22uF', '5V_BUCK', 'GND', B, fp=C12, lcsc='C12891'); C('22uF', '5V_BUCK', 'GND', B, fp=C12, lcsc='C12891')
SCH('5V_BUCK', '+5V', B)

# ---------------- Charger + cell protection ----------------
B = 'chg'
part('U', 'Battery_Management:TP4056-42-ESOP8', 'TP4056', 'Package_SO:SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm',
     {'1': 'CHG_TEMP', '2': 'CHG_PROG', '3': 'GND', '4': '+5V', '5': 'VBAT', '6': 'nSTDBY', '7': 'nCHRG',
      '8': '+5V', '9': 'GND'}, B, lcsc='C16581')
C('10uF', '+5V', 'GND', B); C('10uF', 'VBAT', 'GND', B)
R('4.7k', 'CHG_PROG', 'GND', B, note='~250 mA')
R('4.7k', 'CHG_PROG', 'CHG_PROG2', B, note='with JP: ~500 mA')
part('JP', 'Jumper:SolderJumper_2_Open', '500mA', SJ, {'1': 'CHG_PROG2', '2': 'GND'}, B)
part('JP', 'Jumper:SolderJumper_2_Bridged', 'NO_NTC', SJB, {'1': 'CHG_TEMP', '2': 'GND'}, B)
R('10k', '+5V', 'CHG_TEMP', B, dnp=True, note='NTC divider, value per cell NTC')
part('J', 'Connector:Conn_01x02_Pin', 'NTC', HDR.format(n=2), {'1': 'CHG_TEMP', '2': 'GND'}, B, dnp=True)
R('1k', '+5V', 'LED_CHRG', B); LED('RED', 'LED_CHRG', 'nCHRG', B)
R('1k', '+5V', 'LED_STDBY', B); LED('GREEN', 'LED_STDBY', 'nSTDBY', B)
part('J', 'Connector:Conn_01x02_Pin', 'LiPo', 'Connector_JST:JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal',
     {'2': 'VBAT', '1': 'CELL_NEG'}, B, lcsc='C157932', mpn='S2B-PH-K-S')
# XB5353A (D65, D87): one-chip protection with its MOSFETs inside, as frugal-iot-hw-lora. Replaced DW01A + FS8205A
# (+ R14 100R, R15 1k): one Extended part instead of two, two fewer parts. Pins per datasheet (C80628): 1 VT (test,
# open), 2 GND = cell -, 3 VDD = cell +, 4/5 VM = pack - = board GND. 4.30 / 2.4 V, 3 A discharge over-current.
part('U', 'irrigation:XB5353A', 'XB5353A', 'Package_TO_SOT_SMD:SOT-23-5',
     {'1': 'NC', '2': 'CELL_NEG', '3': 'VBAT', '4': 'GND', '5': 'GND'}, B, lcsc='C80628', mpn='XB5353A')
GAP('R')                                   # R14 was the DW01A's 100R supply resistor
C('100nF', 'VBAT', 'CELL_NEG', B)          # C10, at the XB5353A's VDD
GAP('R')                                   # R15 was the DW01A's 1k current-sense resistor
GAP('Q')                                   # Q1 was the FS8205A

# ---------------- System power ----------------
B = 'pwr'
SCH('+5V', 'VSYS', B)
PFET('+5V', 'VSYS', 'VBAT', B)
R('100k', '+5V', 'GND', B)
C('10uF', 'VSYS', 'GND', B)
# RT9080-33GJ5 (D88), as frugal-iot-hw-lora's L18: 2 uA quiescent (AP2112K: 55 uA), 600 mA, same pins
# (1 VIN, 2 GND, 3 EN, 4 NC, 5 VOUT). KiCad has no RT9080 symbol; the XC6220B331MR's is the same pinout.
part('U', 'Regulator_Linear:XC6220B331MR', 'RT9080-33GJ5', 'Package_TO_SOT_SMD:TSOT-23-5',
     {'1': 'VSYS', '3': 'VSYS', '2': 'GND', '4': 'NC', '5': '+3V3'}, B, lcsc='C841192', mpn='RT9080-33GJ5')
C('10uF', '+3V3', 'GND', B); C('100nF', '+3V3', 'GND', B)
R('1M', 'VBAT', 'VBAT_SENSE', B); R('1M', 'VBAT_SENSE', 'GND', B); C('100nF', 'VBAT_SENSE', 'GND', B)
PFET('G_3V3SW', '+3V3', '+3V3_SW', B); R('100k', '+3V3', 'G_3V3SW', B); NFET('RAIL_EN', 'GND', 'G_3V3SW', B)
C('1uF', '+3V3_SW', 'GND', B)
PFET('G_5VSW', '+5V', '+5V_SW', B); R('100k', '+5V', 'G_5VSW', B); NFET('RAIL_EN', 'GND', 'G_5VSW', B)
C('10uF', '+5V_SW', 'GND', B)
R('100k', 'RAIL_EN', 'GND', B, note='rails off at reset')
# Test points on every supply rail (D89), as frugal-iot-hw-lora's L20: bare 1.5 mm pads, no LCSC part, so not in
# the JLCPCB BOM or pick-and-place. The value is the rail, which the silkscreen shows instead of the reference.
TP_RAILS = ('+12V', '+5V', 'VBUS', 'VBAT', 'VSYS', '+3V3', '+3V3_SW', '+5V_SW', 'GND')
for net in TP_RAILS:
    part('TP', 'Connector:TestPoint', net, 'TestPoint:TestPoint_Pad_D1.5mm', {'1': net}, B)

# ---------------- MCU ----------------
B = 'mcu'
part('U', 'irrigation:ESP32-C3-C6-MINI-1U', 'ESP32-C6-MINI-1U-H4 (alt C3-MINI-1U)', 'irrigation:ESP32-C3-C6-MINI-1U',
     {'3': '+3V3', **{n: 'GND' for n in ['1', '2', '11', '14'] + [str(i) for i in range(36, 54)]},
      '8': 'EN', '12': 'RS485_RX', '13': 'V12_SENSE', '5': 'RS485_TX', '6': 'VBAT_SENSE',
      '22': 'STATUS_LED', '23': 'BOOT', '16': 'I2C_SDA', '19': 'I2C_SCL', '20': 'RAIL_EN',
      '30': 'RXD0', '31': 'TXD0',
      '17': 'USB_C6_D_N', '18': 'USB_C6_D_P', '26': 'USB_C3_D_N', '27': 'USB_C3_D_P',
      '9': 'NC', '10': 'NC', '15': 'GPIO_A', '24': 'NC', '25': 'BTN2', '28': 'GPIO_B', '29': 'NC', '21': 'NC',
      '4': 'NC', '7': 'NC', '32': 'NC', '33': 'NC', '34': 'NC', '35': 'NC'}, B, lcsc='C20627095', mpn='ESP32-C6-MINI-1U-H4')
C('10uF', '+3V3', 'GND', B); C('100nF', '+3V3', 'GND', B)
R('10k', '+3V3', 'EN', B); C('1uF', 'EN', 'GND', B); BUTTON('EN', 'GND', B, 'RESET')
R('10k', '+3V3', 'BOOT', B); BUTTON('BOOT', 'GND', B, 'BOOT / BTN1')
R('10k', '+3V3', 'RS485_TX', B, note='also C3 GPIO2 strap high')
R('10k', '+3V3', 'STATUS_LED', B, note='GPIO8 strap high')
R('1k', '+3V3', 'LED_STAT', B); LED('GREEN', 'LED_STAT', 'STATUS_LED', B)
part('J', 'Connector:Conn_01x03_Pin', 'UART0 debug', HDR.format(n=3), {'1': 'TXD0', '2': 'RXD0', '3': 'GND'}, B, dnp=True)

# ---------------- User I/O (C6-only pads) ----------------
B = 'uio'
R('10k', '+3V3', 'BTN2', B); BUTTON('BTN2', 'GND', B, 'BTN2 (C6)')
for g in ('GPIO_A', 'GPIO_B'):
    R('10k', '+3V3_SW', g, B, dnp=True, note='pull-up option'); R('10k', g, 'GND', B, dnp=True, note='pull-down option')
    part('J', 'Connector:Screw_Terminal_01x02', g + ' (C6)', TB254.format(n=2), {'1': g, '2': 'GND'}, B, lcsc='C557685', mpn='XY308-2.54-2P')

# ---------------- I2C, expander, sensor ports ----------------
B = 'i2c'
R('4.7k', '+3V3_SW', 'I2C_SDA', B); R('4.7k', '+3V3_SW', 'I2C_SCL', B)
part('J', 'Connector:Screw_Terminal_01x04', 'I2C sensor', TB254.format(n=4),
     {'1': '+3V3_SW', '2': 'I2C_SDA', '3': 'I2C_SCL', '4': 'GND'}, B, lcsc='C915913', mpn='XY308-2.54-4P')
part('J', 'Connector:Conn_01x04_Pin', 'OLED', HDR.format(n=4), {'1': 'GND', '2': '+3V3_SW', '3': 'I2C_SCL', '4': 'I2C_SDA'}, B, lcsc='C492403', mpn='PZ254V-11-04P')
part('U', 'Interface_Expansion:TCA9534', 'TCA9534PWR', 'Package_SO:TSSOP-16_4.4x5mm_P0.65mm',
     {'1': 'GND', '2': 'GND', '3': 'GND', '4': 'REL1', '5': 'REL2', '6': 'REL3', '7': 'REL4', '8': 'GND',
      '9': 'REL5', '10': 'REL6', '11': 'REL7', '12': 'REL8', '13': 'NC', '14': 'I2C_SCL', '15': 'I2C_SDA',
      '16': '+3V3'}, B, lcsc='C783615', mpn='TCA9534PWR')
C('100nF', '+3V3', 'GND', B)
# No spare header: all eight expander pins drive valves (D75)

# ---------------- RS485 ----------------
B = 'rs485'
part('U', 'Interface_UART:SP3485EN', 'SP3485EN', 'Package_SO:SOIC-8_3.9x4.9mm_P1.27mm',
     {'1': 'RS485_RX', '2': 'RS485_DIR', '3': 'RS485_DIR', '4': 'GND', '5': 'GND', '6': 'RS485_A', '7': 'RS485_B',
      '8': '+3V3_SW'}, B, lcsc='C8963', mpn='SP3485EN-L/TR')
C('100nF', '+3V3_SW', 'GND', B)
NFET('RS485_TX', 'GND', 'RS485_DIR', B)
R('10k', '+3V3_SW', 'RS485_DIR', B)
R('10k', '+3V3_SW', 'RS485_RX', B)
R('680R', '+3V3_SW', 'RS485_A', B, note='bias'); R('680R', 'RS485_B', 'GND', B, note='bias')
R('120R', 'RS485_A', 'RS485_TERM', B); part('JP', 'Jumper:SolderJumper_2_Open', 'TERM', SJ, {'1': 'RS485_TERM', '2': 'RS485_B'}, B)
part('D', 'Diode:SM712_SOT23', 'PSM712', SOT23, {'1': 'RS485_A', '2': 'RS485_B', '3': 'GND'}, B, lcsc='C32677', mpn='PSM712-LF-T7')
part('J', 'Connector:Screw_Terminal_01x04', 'RS485', TB254.format(n=4),
     {'1': '+5V_SW', '2': 'RS485_A', '3': 'RS485_B', '4': 'GND'}, B, lcsc='C915913', mpn='XY308-2.54-4P')

# ---------------- Valve drivers (one AO3400A per valve, eight valves) ----------------
# Replaces the four relays (D73). Each valve: low-side logic-level N-MOSFET driven straight from a TCA9534
# pin, 100k gate pull-down, SS34 Schottky across the valve, LED across the valve. All Basic parts.
# Why not the ULN2803A tried first (D67-D70): its SOP-18 package limits a valve to ~0.35 A and drops ~1.1 V;
# the AO3400A drops ~0.04 V at 1 A (48 mOhm max at VGS 2.5 V, and the TCA9534 gives ~3.2 V).
# The pull-down holds each valve off while the TCA9534 pins are inputs (reset, boot, before firmware runs):
# the ULN's internal resistors did that job before; a bare MOSFET gate would float.
# Flyback diode cathode on +12V, the SAME node as the valve's V+ terminal pin, after D2: the turn-off loop
# (coil -> diode -> +12V -> V+ pin -> coil) stays on the board and never needs current back through D2 (D69).
B = 'rly'
for i in range(1, 9):   # 8 valves, one per TCA9534 pin (D75); any of 5-8 can be left unfitted
    NFET(f'REL{i}', 'GND', f'VALVE{i}', B, typ='AO3400A')
    R('100k', f'REL{i}', 'GND', B, note='valve off at reset')
    SCH(f'VALVE{i}', '+12V', B)
    R('4.7k', '+12V', f'LED_V{i}', B); LED('RED', f'LED_V{i}', f'VALVE{i}', B)
    part('J', 'Connector:Screw_Terminal_01x02', f'Valve {i}', TB508.format(n=2),
         {'1': '+12V', '2': f'VALVE{i}'}, B, lcsc='C474952', mpn='KF128-5.08-2P')
# Local bulk on +12V at the valve terminals: valve inrush and the flyback loops are here, not at the buck
C('10uF 25V', '+12V', 'GND', B, fp=C12, lcsc='C13585')
