"""Blocks 7-8: RS485; valve drivers."""
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
    with S.block("VALVE DRIVERS (ULN2803A, TWO CHANNELS PER VALVE)"):
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
        # ULN2803A: Pk drives the pair I(2k+1), I(2k+2). P0 runs straight across to I1; each later Pk
        # drops to its pair's row in its own column, further left each time, so no two wires cross.
        p0 = pin('U7', '4')
        put_pin('U9', '1', at(p0, 38.1))
        tx = pin('U9', '1')[0] - 2.54                       # tie column, just left of the inputs
        for k, tp in enumerate(('4', '5', '6', '7')):
            a, b = pin('U9', str(2 * k + 1)), pin('U9', str(2 * k + 2))
            src = pin('U7', tp)
            if k == 0:
                S.wire(src, (tx, a[1]), a)
            else:
                cx = tx - 5.08 * (k + 1)
                S.wire(src, (cx, src[1]), (cx, a[1]), (tx, a[1]), a)
            S.wire((tx, a[1]), (tx, b[1]), b)
        # outputs: O1/O2 -> VALVE1 ... O7/O8 -> VALVE4, tied just right of the pins
        ox = pin('U9', '18')[0] + 2.54
        for k, (pa, pb) in enumerate((('18', '17'), ('16', '15'), ('14', '13'), ('12', '11'))):
            a, b = pin('U9', pa), pin('U9', pb)
            S.wire(b, (ox, b[1]), (ox, a[1]))
            S.wire(a, (ox, a[1]), (ox + 5.08, a[1])); S.label(f'VALVE{k+1}', ox + 5.08, a[1])
        term('U9', '9', 'GND')
        # COM: up to +12V, with the local bulk cap hung off the same wire
        c = pin('U9', '10')
        n1 = at(c, 12.7); n2 = at(n1, 0, -7.62)
        S.wire(c, n1, n2); port('+12V', *n2)
        S.wire(at(n1, 0, -2.54), at(n1, 7.62, -2.54))
        hang('C22', at(n1, 7.62, -2.54), 'GND')
        # expander spare header (DNP)
        put('J10', x + 5.08, y + 30.48, mirror='y')
        for p, net in (('1', 'EXP_IO4'), ('2', 'EXP_IO5'), ('3', 'EXP_IO6'), ('4', 'EXP_IO7')):
            term('J10', p, net, 2.54)
        pwr_pin('J10', '6', 'GND', 2.54, 2.54); term('J10', '5', '+3V3', 2.54)
        # four identical valve channels: V+ / OUT terminal, LED across the valve
        for i in range(4):
            r, d, j = f'R{39+i}', f'D{10+i}', f'J{12+i}'
            jx, jy = x + 129.54 + 33.02 * i, y + 7.62
            put(j, jx, jy)
            pwr_pin(j, '1', '+12V', 5.08, 5.08)
            p2 = pin(j, '2')
            n = at(p2, -15.24)
            S.wire(p2, n, at(n, -7.62)); S.label(f'VALVE{i+1}', n[0] - 7.62, n[1], angle=180)
            a = at(n, 0, -2.54)
            S.wire(n, a)
            put_pin(d, '1', a, rot=90)
            assert pin(d, '2')[1] < a[1], (d, 'LED not pointing down')
            top = at(pin(d, '2'), 0, -2.54)
            S.wire(pin(d, '2'), top)
            rise(r, top, '+12V')
        S.note("TCA9534 pins start as inputs: the ULN2803A's internal input resistors then hold every\n"
               "valve off until firmware drives P0-P3 (D16). Address 0x20 (A0-A2 low). P0-P3 high = valve on.\n"
               "Each output drives two Darlingtons in parallel (D68). Valves: 12 V DC, up to ~0.35 A, one at a\n"
               "time - the SOP-18 package limits this, not the channels (D70). Not for pumps or latching valves.\n"
               "FLYBACK (D69): COM must be on the same +12V as the valves' V+ pins, after D1. A valve wired to\n"
               "any other supply loses its clamp and the Darlington avalanches at turn-off.",
               x - 5.08, y + 48.26, 1.0)
