"""Circuit definition for the Frugal-IoT irrigation daughter board (source of truth for parts and nets).
An add-on for the Frugal-IoT sensor board (frugal-iot-hw-sensor V0.2) or LoRa board (frugal-iot-hw-lora V0.3):
the valve drivers of the irrigation board (../../irrigation-layout-oct-2026, D73-D77 there) on their own, driven
over I2C from the host's J2. Decisions are Dn in ../../DECISIONS.md; Ixx refers to the irrigation board's log.
Each part: dict(prefix, lib, value, fp, nets{pin:net}, dnp, lcsc, mpn, block, rot)
net 'NC' => no-connect marker. References are numbered in this file's order.
"""
P = []
def part(prefix, lib, value, fp, nets, block, dnp=False, lcsc='', mpn='', rot=None, note=''):
    P.append(dict(prefix=prefix, lib=lib, value=value, fp=fp, nets=nets, block=block,
                  dnp=dnp, lcsc=lcsc, mpn=mpn, rot=rot, note=note))

R06 = 'Resistor_SMD:R_0603_1608Metric'; C06 = 'Capacitor_SMD:C_0603_1608Metric'
C12 = 'Capacitor_SMD:C_1206_3216Metric'; LED06 = 'LED_SMD:LED_0603_1608Metric'
SMA = 'Diode_SMD:D_SMA'; SOT23 = 'Package_TO_SOT_SMD:SOT-23'
TB508 = 'irrigation:TerminalBlock_KF128-5.08-2P'   # the irrigation board's KF128 footprint (its D79)
TB254 = 'TerminalBlock:TerminalBlock_Xinya_XY308-2.54-{n}P_1x0{n}_P2.54mm_Horizontal'
HDR = 'Connector_PinHeader_2.54mm:PinHeader_1x0{n}_P2.54mm_Vertical'

RES = {'100k': 'C25803', '4.7k': 'C23162', '560k': 'C23203'}
CAP = {'100nF': 'C14663'}

def R(v, a, b, blk, dnp=False, note=''):
    part('R', 'Device:R', v, R06, {'1': a, '2': b}, blk, dnp, RES.get(v, ''), note=note)
def C(v, a, b, blk, fp=C06, lcsc=None, dnp=False):
    part('C', 'Device:C', v, fp, {'1': a, '2': b}, blk, dnp, CAP.get(v, '') if lcsc is None else lcsc)
def LED(col, anode, cathode, blk):  # JLCPCB Basic red KT-0603R
    part('D', 'Device:LED', col, LED06, {'2': anode, '1': cathode}, blk, rot=180, lcsc='C2286', mpn='KT-0603R')
def SCH(anode, cathode, blk, typ='SS34'):  # SMA Schottky: SS34 (3 A) or SS54 (5 A), both Basic
    part('D', 'Device:D_Schottky', typ, SMA, {'2': anode, '1': cathode}, blk,
         lcsc={'SS34': 'C8678', 'SS54': 'C22452'}[typ], mpn=typ, rot=180)
def NFET(g, s, d, blk):
    part('Q', 'Transistor_FET:AO3400A', 'AO3400A', SOT23, {'1': g, '2': s, '3': d}, blk, lcsc='C20917')

# ---------------- Host connector + OLED ----------------
B = 'host'
# J1 to the host's J2 by a short cable (D2). Read left to right as it sits on the board's top edge it is GND, SDA,
# SCL, 3V3_SW, V12 - the host's J2 pins 1, 2, 3, 4, 9 read top to bottom - so with the two boards side by side a
# cable runs straight without twisting. That puts GND on the terminal's pin 5 and V12 on pin 1: the footprint faces
# the edge, which makes its pin 1 the rightmost. V12_SENSE goes to host J2.9 (SENS2, analog, 100 nF fitted there).
# XY308, the part the hosts use, so it rides on their volume. No I2C pull-ups here: the host has 4.7k on 3V3_SW.
part('J', 'Connector:Screw_Terminal_01x05', 'HOST', TB254.format(n=5),
     {'5': 'GND', '4': 'I2C_SDA', '3': 'I2C_SCL', '2': '+3V3_SW', '1': 'V12_SENSE'}, B, lcsc='C915914', mpn='XY308-2.54-5P')
# ---------------- 12 V input ----------------
B = 'v12'
# As the irrigation board (I77): resettable fuse, then reverse-polarity Schottky, then TVS. The fuse is for a
# shorted field cable fed from a battery, not a current budget; it MUST be rated >= 16 V.
part('J', 'Connector:Screw_Terminal_01x02', '12V IN', TB508, {'1': '12V_IN', '2': 'GND'}, B, lcsc='C474952', mpn='KF128-5.08-2P')
part('F', 'Device:Polyfuse', '3A 16V', 'Fuse:Fuse_1812_4532Metric', {'1': '12V_IN', '2': '12V_FUSED'}, B,
     lcsc='C702820', mpn='SMD1812P300TF/16')
SCH('12V_FUSED', '+12V', B, typ='SS54')   # 5 A: all valve current passes through it
part('D', 'Diode:SMAJ15A', 'SMAJ15A', SMA, {'1': '+12V', '2': 'GND'}, B, lcsc='C19077535', mpn='SMAJ15A')
C('10uF 25V', '+12V', 'GND', B, fp=C12, lcsc='C13585')   # bulk at the valves: inrush and the flyback loops
# 12 V battery reading for the host's low-voltage interlock (D4): 2.27 V at 15 V. The filter cap is the host's.
R('560k', '+12V', 'V12_SENSE', B); R('100k', 'V12_SENSE', 'GND', B)

# ---------------- OLED ----------------
B = 'oled'
# The irrigation board's J9 pinout (SSD1306 128x64 modules: GND, VCC, SCL, SDA). On this board rather than the
# host because the host's I2C is on its screw terminal, which the cable to here already uses.
part('J', 'Connector:Conn_01x04_Pin', 'OLED', HDR.format(n=4), {'1': 'GND', '2': '+3V3_SW', '3': 'I2C_SCL', '4': 'I2C_SDA'},
     B, lcsc='C492403', mpn='PZ254V-11-04P')

# ---------------- Expander + valve drivers ----------------
B = 'rly'
# TCA9534 at 0x20 (A0-A2 low), powered from the host's 3V3_SW (D3): with the host's sensor rail off it is
# unpowered, its pins go high-impedance, and the 100k pull-downs turn every valve off - the safe direction.
part('U', 'Interface_Expansion:TCA9534', 'TCA9534PWR', 'Package_SO:TSSOP-16_4.4x5mm_P0.65mm',
     {'1': 'GND', '2': 'GND', '3': 'GND', '4': 'REL1', '5': 'REL2', '6': 'REL3', '7': 'REL4', '8': 'GND',
      '9': 'REL5', '10': 'REL6', '11': 'REL7', '12': 'REL8', '13': 'NC', '14': 'I2C_SCL', '15': 'I2C_SDA',
      '16': '+3V3_SW'}, B, lcsc='C783615', mpn='TCA9534PWR')
C('100nF', '+3V3_SW', 'GND', B)
# Each valve as the irrigation board (I73): AO3400A low-side, gate from a TCA9534 pin, 100k pull-down, SS34
# flyback across the valve (cathode on the same +12V as the V+ pin, after D1), red LED + 4.7k across the valve.
for i in range(1, 9):
    NFET(f'REL{i}', 'GND', f'VALVE{i}', B)
    R('100k', f'REL{i}', 'GND', B, note='valve off at reset')
    SCH(f'VALVE{i}', '+12V', B)
    R('4.7k', '+12V', f'LED_V{i}', B); LED('RED', f'LED_V{i}', f'VALVE{i}', B)
    part('J', 'Connector:Screw_Terminal_01x02', f'Valve {i}', TB508, {'1': '+12V', '2': f'VALVE{i}'}, B,
         lcsc='C474952', mpn='KF128-5.08-2P')
