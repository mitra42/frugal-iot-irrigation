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
        put_pin('J10', '2', (jxx, a[1]))
        p3 = pin('J10', '3')
        S.wire(a, at(a, 10.16), at(a, 22.86), pin('J10', '2'))
        dbtag('RS485_A', at(a, 22.86), up=True, length=7.62)
        bx = b[0] + 27.94
        S.wire(b, at(b, 10.16), at(b, 20.32), (bx, b[1]), (bx, p3[1]), p3)
        dbtag('RS485_B', at(b, 20.32), up=False, length=7.62)
        rise('R36', at(a, 10.16), '+3V3_SW', bottom_pin='2')
        hang('R37', at(b, 10.16), 'GND')
        pwr_pin('J10', '1', '+5V_SW', 5.08, 5.08); pwr_pin('J10', '4', 'GND', 5.08, 2.54)
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
    with S.block("VALVE DRIVERS (LOW-SIDE MOSFET PER VALVE)"):
        put('U7', x, y)
        v = pin('U7', '16')
        m = at(v, 0, -12.7); t = at(v, 0, -15.24)
        S.wire(v, m, t); port('+3V3', *t)
        S.wire(m, at(m, -10.16)); hang('C20', at(m, -10.16), 'GND')
        term('U7', '8', 'GND')
        term('U7', '14', 'I2C_SCL', 5.08); term('U7', '15', 'I2C_SDA', 5.08)
        S.nc('U7', '13')
        for p in ('1', '2', '3'): term('U7', p, 'GND', 2.54)
        for k, tp in enumerate(('4', '5', '6', '7', '9', '10', '11', '12')):
            term('U7', tp, f'REL{k+1}', 5.08)
        # refs come from circuit.py's order, so look them up by what they connect to
        def ref(prefix, net, pinno):
            return next(r for r, p in B.NETS[net] if r[:len(prefix)] == prefix and r[len(prefix)].isdigit() and p == pinno)
        # four identical valve channels: gate pull-down, MOSFET, LED, flyback diode, V+ / OUT terminal
        for i in range(8):   # two rows of four
            v = f'VALVE{i+1}'
            q = ref('Q', v, '3'); df = ref('D', v, '2'); led = ref('D', v, '1')
            rl = ref('R', f'LED_V{i+1}', '2'); rg = ref('R', f'REL{i+1}', '1'); j = ref('J', v, '2')
            jx, jy = x + 114.3 + 60.96 * (i % 4), y + 7.62 + 55.88 * (i // 4)
            put(j, jx, jy)
            pwr_pin(j, '1', '+12V', 5.08, 5.08)
            p2 = pin(j, '2')
            nd = at(p2, -10.16); nl = at(nd, -15.24); nq = at(nl, -15.24)
            S.wire(p2, nd, nl, nq)
            # flyback diode, cathode up to +12V
            a = at(nd, 0, -2.54); S.wire(nd, a)
            put_pin(df, '2', a, rot=270)
            assert pin(df, '1')[1] < a[1], (df, 'diode not pointing up')
            drop('+12V', pin(df, '1'))
            # LED + resistor across the valve
            a = at(nl, 0, -2.54); S.wire(nl, a)
            put_pin(led, '1', a, rot=90)
            top = at(pin(led, '2'), 0, -2.54)
            S.wire(pin(led, '2'), top)
            rise(rl, top, '+12V')
            # MOSFET: drain up to the valve node, source to GND, gate left with its pull-down
            put_pin(q, '3', at(nq, 0, 2.54)); S.wire(nq, pin(q, '3'))
            term(q, '2', 'GND')
            g = pin(q, '1'); gn = at(g, -5.08); gl = at(gn, -7.62)
            S.wire(g, gn, gl); S.label(f'REL{i+1}', gl[0], gl[1], angle=180)
            hang(rg, gn, 'GND')
        # local bulk on +12V near the terminals
        cb = (x + 81.28, y - 5.08)
        drop('+12V', cb); hang('C22', cb, 'GND')
        S.note("TCA9534 pins start as inputs; the 100k pull-downs then hold every valve off until\n"
               "firmware drives them. Address 0x20 (A0-A2 low). P0-P7 high = valve 1-8 on.\n"
               "Valves 5-8 may be left unfitted (FET, pull-down, diode, LED, resistor, terminal) (D75).\n"
               "Valves: 12 V DC, low-side switched, up to ~2 A each (D73); total from 12 V IN ~3 A,\n"
               "set by F1 (D77). Not for latching valves or 24 V AC valves.\n"
               "FLYBACK (D69): each diode returns to the same +12V as its valve's V+ pin, after D2.\n"
               "A valve wired to any other supply loses its clamp.",
               x - 5.08, y + 124.46, 1.0)
