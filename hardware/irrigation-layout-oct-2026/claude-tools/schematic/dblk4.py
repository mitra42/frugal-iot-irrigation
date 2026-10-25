"""Blocks 7-8: RS485; relay driver and relays."""
import dbase as B
from dbase import tag as dbtag, pwr_pin, put, put_pin, pin, port, drop, term, hang, rise, series, diode_r, at

def rs485(x, y):
    S = B.S
    with S.block("RS485 (DIRECTION FROM TX)"):
        put('U8', x, y)
        v = pin('U8', '8')
        m = at(v, 0, -10.16); t = at(v, 0, -12.7)
        S.wire(v, m, t); port('+3V3_SW', *t)
        S.wire(m, at(m, -17.78)); hang('C21', at(m, -17.78), 'GND')
        term('U8', '5', 'GND')
        term('U8', '1', 'RS485_RX', 5.08)
        re_, de = pin('U8', '2'), pin('U8', '3')
        jx = re_[0] - 2.54
        S.wire(re_, (jx, re_[1])); S.wire(de, (jx, de[1])); S.wire((jx, re_[1]), (jx, de[1]))
        S.wire((jx, de[1]), (jx - 5.08, de[1])); S.label('RS485_DIR', jx - 5.08, de[1], angle=180)
        term('U8', '4', 'GND', 2.54)
        # bus: A straight to J11 pin 2, B jogs up one row to pin 3
        a, b = pin('U8', '6'), pin('U8', '7')
        jxx = a[0] + 38.1
        put_pin('J11', '2', (jxx, a[1]))
        p3 = pin('J11', '3')
        S.wire(a, at(a, 10.16), at(a, 22.86), pin('J11', '2'))
        dbtag('RS485_A', at(a, 22.86), up=True, length=7.62)
        bx = b[0] + 27.94
        S.wire(b, at(b, 10.16), at(b, 20.32), (bx, b[1]), (bx, p3[1]), p3)
        dbtag('RS485_B', at(b, 20.32), up=False, length=7.62)
        rise('R36', at(a, 10.16), '+3V3_SW', bottom_pin='2')
        hang('R37', at(b, 10.16), 'GND')
        pwr_pin('J11', '1', '+5V_SW', 5.08, 5.08); pwr_pin('J11', '4', 'GND', 5.08, 2.54)
        # termination (solder jumper) and TVS, hung off labels below the bus
        n = (a[0] + 2.54, b[1] + 12.7)
        S.wire(at(n, -5.08), n); S.label('RS485_A', n[0] - 5.08, n[1], angle=180)
        e = series('R38', n)
        e2 = series('JP3', at(e, 2.54), first='1', rot=0); S.wire(e, at(e, 2.54))
        S.wire(e2, at(e2, 5.08)); S.label('RS485_B', e2[0] + 5.08, e2[1])
        n = (a[0] + 7.62, b[1] + 22.86)
        put_pin('D9', '1', n)
        S.wire(at(n, -5.08), n); S.label('RS485_A', n[0] - 5.08, n[1], angle=180)
        term('D9', '2', 'RS485_B', 5.08); term('D9', '3', 'GND', 2.54)
        # direction: TX low -> Q9 off -> DE high -> driver sends 0; TX high -> receive, bias gives 1
        qx, qy = x - 38.1, y + 7.62
        n = (qx, qy)
        rise('R34', n, '+3V3_SW', bottom_pin='2')
        S.wire(n, at(n, 7.62)); S.label('RS485_DIR', n[0] + 7.62, n[1])
        put_pin('Q7', '3', at(n, 0, 2.54)); S.wire(n, pin('Q7', '3'))
        term('Q7', '2', 'GND'); term('Q7', '1', 'RS485_TX', 5.08)
        n = (qx, qy - 20.32)
        rise('R35', n, '+3V3_SW', bottom_pin='2')
        S.wire(n, at(n, 7.62)); S.label('RS485_RX', n[0] + 7.62, n[1])
        S.note("DI is tied low: the driver only ever sends 0, gated by TX through Q9.\n"
               "A 1 (and idle) is held by the 680R bias pair. Fine for Modbus at 9600 baud;\n"
               "marginal with termination at both cable ends (D21). Bridge JP3 at a bus end.\n"
               "Transceiver, bias and pull-ups are on +3V3_SW, so RS485 is off with the rail.",
               x - 38.1, y + 38.1, 1.0)

def relays(x, y):
    S = B.S
    with S.block("RELAY DRIVER & RELAYS"):
        put('U7', x, y)
        v = pin('U7', '16')
        m = at(v, 0, -12.7); t = at(v, 0, -15.24)
        S.wire(v, m, t); port('+3V3', *t)
        S.wire(m, at(m, -10.16)); hang('C20', at(m, -10.16), 'GND')
        term('U7', '8', 'GND')
        term('U7', '14', 'I2C_SCL', 5.08); term('U7', '15', 'I2C_SDA', 5.08)
        S.nc('U7', '13')
        for p in ('1', '2', '3'): term('U7', p, 'GND', 2.54)
        for p, net in (('9', 'EXP_IO4'), ('10', 'EXP_IO5'), ('11', 'EXP_IO6'), ('12', 'EXP_IO7')):
            term('U7', p, net, 2.54)
        # ULN2003: I1..I4 in line with P0..P3
        p0 = pin('U7', '4')
        put_pin('U9', '1', at(p0, 33.02))
        for a, b in (('4', '1'), ('5', '2'), ('6', '3'), ('7', '4')):
            S.wire(pin('U7', a), pin('U9', b))
        for p in ('5', '6', '7'): term('U9', p, 'GND', 2.54)
        term('U9', '8', 'GND'); term('U9', '9', '+12V', 2.54)
        for p, net in (('16', 'COIL1'), ('15', 'COIL2'), ('14', 'COIL3'), ('13', 'COIL4')):
            term('U9', p, net, 5.08)
        S.nc('U9', '12', '11', '10')
        # expander spare header (DNP)
        put('J10', x + 5.08, y + 30.48, mirror='y')
        for p, net in (('1', 'EXP_IO4'), ('2', 'EXP_IO5'), ('3', 'EXP_IO6'), ('4', 'EXP_IO7')):
            term('J10', p, net, 2.54)
        pwr_pin('J10', '6', 'GND', 2.54, 2.54); pwr_pin('J10', '5', '+3V3', 7.62, 0.0) if False else term('J10', '5', '+3V3', 2.54)
        # four identical relay channels
        for i in range(4):
            k, r, d, j = f'K{i+1}', f'R{39+i}', f'D{10+i}', f'J{12+i}'
            kx, ky = x + 104.14 + 45.72 * i, y
            put(k, kx, ky)
            c5, c2 = pin(k, '5'), pin(k, '2')            # coil: top = COILn, bottom = +12V
            ct = at(c5, 0, -2.54); cb = at(c2, 0, 2.54)
            S.wire(c5, ct); S.wire(c2, cb)
            # LED + resistor across the coil, on its left
            lx = ct[0] - 10.16
            S.wire(cb, (lx, cb[1]))
            put_pin(r, '1', (lx, cb[1] - 2.54), rot=180)
            S.wire((lx, cb[1]), pin(r, '1'))
            put_pin(d, '2', at(pin(r, '2'), 0, -2.54), rot=270)
            S.wire(pin(r, '2'), pin(d, '2'))
            kp = pin(d, '1')
            S.wire(kp, ct) if abs(kp[1] - ct[1]) < 1e-6 else S.wire(kp, (lx, ct[1]), ct)
            S.wire(ct, at(ct, 0, -2.54)); S.label(f'COIL{i+1}', ct[0], ct[1] - 2.54, angle=90)
            S.wire(cb, at(cb, 0, 2.54)); port('+12V', cb[0], cb[1] + 2.54, up=False)
            for p, net in (('1', f'K{i+1}_COM'), ('3', f'K{i+1}_NO'), ('4', f'K{i+1}_NC')):
                term(k, p, net, 2.54 if p != '4' else 5.08)
            put(j, kx + 25.4, ky)
            for p, net in (('1', f'K{i+1}_NO'), ('2', f'K{i+1}_COM'), ('3', f'K{i+1}_NC')):
                term(j, p, net, 2.54)
        S.note("TCA9534 pins start as inputs: the ULN2003's internal input resistors then hold\n"
               "every relay off until firmware drives P0-P3 (D16). Address 0x20 (A0-A2 low).\n"
               "Contacts are isolated from the board: wire loads to COM/NO/NC (D5, D24).\n"
               "Contact copper for 5 A per channel at 1 oz; 12 V DC loads only.",
               x - 5.08, y + 48.26, 1.0)
