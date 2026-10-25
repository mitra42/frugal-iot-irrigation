"""Blocks 1-2: USB-C input; 12 V input + 5 V buck."""
import dbase as B
from dbase import tag as dbtag, pwr_pin, put, put_pin, pin, port, drop, term, hang, rise, series, diode_r, at

def usb(x, y):
    S = B.S
    with S.block("USB-C INPUT"):
        put('J1', x, y)
        vb = pin('J1', 'A4')
        n1 = at(vb, 7.62)
        S.wire(vb, n1)
        nf = at(n1, 0, -2.54)
        S.wire(n1, nf, at(nf, 0, -2.54)); port('VBUS', *at(nf, 0, -2.54))
        S.wire(nf, at(nf, -5.08)); S.power('PWR_FLAG', nf[0] - 5.08, nf[1])
        a = at(n1, 5.08)
        S.wire(n1, a)
        k = diode_r('D1', a)
        e = at(k, 7.62)
        S.wire(k, e)
        drop('+5V', e, 2.54)
        S.wire(e, at(e, 5.08)); S.power('PWR_FLAG', e[0] + 5.08, e[1])
        term('J1', 'SH', 'GND')
        ga = pin('J1', 'A1'); gq = at(ga, 0, 2.54); S.wire(ga, gq, at(gq, 0, 2.54)); port('GND', *at(gq, 0, 2.54))
        S.wire(gq, at(gq, 7.62)); S.power('PWR_FLAG', gq[0] + 7.62, gq[1])
        S.nc('J1', 'A8', 'B8')
        # CC pull-downs: label each CC, resistors stand to the right
        term('J1', 'A5', 'CC1', 2.54)
        term('J1', 'B5', 'CC2', 2.54)
        # flip pairs: join, then D- straight to ESD pin 1 row, D+ jogs up one row to pin 3
        pa, pb = pin('J1', 'A7'), pin('J1', 'B7')           # D-
        xj = pa[0] + 2.54
        S.wire(pa, (xj, pa[1])); S.wire(pb, (xj, pb[1])); S.wire((xj, pa[1]), (xj, pb[1]))
        qa, qb = pin('J1', 'A6'), pin('J1', 'B6')           # D+
        S.wire(qa, (xj, qa[1])); S.wire(qb, (xj, qb[1])); S.wire((xj, qa[1]), (xj, qb[1]))
        ux = xj + 22.86
        put_pin('U1', '1', (ux, pb[1]))                    # I/O1 = D- on the B7 row
        S.wire((xj, pb[1]), (xj + 12.7, pb[1]), pin('U1', '1'))
        S.label('USB_D_N', xj + 12.7, pb[1], angle=90)
        S.wire((xj, qa[1]), (xj + 12.7, qa[1]), pin('U1', '3'))   # D+ on the A6 row
        S.label('USB_D_P', xj + 12.7, qa[1], angle=270)
        term('U1', '5', 'VBUS')
        term('U1', '2', 'GND')
        # through-pins continue to the module-select links
        o6, o4 = pin('U1', '6'), pin('U1', '4')
        lx = o6[0] + 15.24
        S.wire(o6, (lx, o6[1])); S.wire(o4, (lx + 12.7, o4[1]))
        # CC resistors
        cx = n1[0] + 30.48
        for ref, net in (('R1', 'CC1'), ('R2', 'CC2')):
            top = (cx, vb[1] - 15.24)
            S.wire(top, at(top, 0, -2.54)); S.label(net, top[0], top[1] - 2.54, angle=90)
            hang(ref, top, 'GND')
            cx += 10.16
        # module-select 0R links: D- pair from o6 row, D+ pair from o4 row
        # D-: node at lx, R3 (C6) on the row, R5 (C3) one branch below
        r3e = series('R3', (lx + 25.4, o6[1]))
        S.wire((lx, o6[1]), (lx + 25.4, o6[1]))
        term('R3', '2', 'USB_C6_D_N', 2.54)
        S.wire((lx, o6[1]), (lx, o6[1] - 10.16), (lx + 25.4, o6[1] - 10.16))
        dbtag('USB_D_N', (lx, o6[1] - 10.16), up=True, length=2.54)
        series('R5', (lx + 25.4, o6[1] - 10.16)); term('R5', '2', 'USB_C3_D_N', 2.54)
        # D+: node further right, R4 on the row, R6 branch below
        dx = lx + 12.7
        S.wire((dx, o4[1]), (dx, o4[1] + 10.16), (lx + 25.4, o4[1] + 10.16))
        dbtag('USB_D_P', (dx, o4[1] + 20.32), up=False, length=2.54)
        series('R4', (lx + 25.4, o4[1] + 10.16)); term('R4', '2', 'USB_C6_D_P', 2.54)
        S.wire((dx, o4[1] + 10.16), (dx, o4[1] + 20.32), (lx + 25.4, o4[1] + 20.32))
        series('R6', (lx + 25.4, o4[1] + 20.32)); term('R6', '2', 'USB_C3_D_P', 2.54)
        S.note("CC1/CC2: 5.1k each to GND (USB-C sink, 5 V only).\n"
               "Fit R3/R4 for an ESP32-C6 module, R5/R6 (DNP) for a C3 module:\n"
               "the two modules have USB on different pads (DECISIONS D15/D19).",
               x - 5.08, y + 33.02, 1.0)

def v12(x, y):
    S = B.S
    with S.block("12 V INPUT, PROTECTION & 5 V BUCK"):
        put('J2', x, y, mirror='y')
        p1 = pin('J2', '1')
        pwr_pin('J2', '2', 'GND')
        a = at(p1, 7.62)
        S.wire(p1, at(p1, 2.54), a)
        dbtag('12V_IN', at(p1, 2.54), up=True, length=5.08)
        k = diode_r('D2', a)
        n = at(k, 5.08)
        S.wire(k, n)
        drop('+12V', n, 2.54)
        # rail runs right along k's row
        ry = k[1]
        nodes = {}
        xs = [n[0] + 7.62, n[0] + 27.94, n[0] + 50.8, n[0] + 73.66]
        S.wire(n, *[(xx, ry) for xx in xs])
        # TVS (cathode up)
        put_pin('D3', '1', (xs[0], ry), rot=270)
        assert pin('D3', '2')[1] > ry
        term('D3', '2', 'GND')
        # input caps
        hang('C2', (xs[1], ry), 'GND'); hang('C3', (xs[2], ry), 'GND'); hang('C4', (xs[3], ry), 'GND')
        # buck
        ux = xs[3] + 22.86
        put_pin('U2', '3', (ux, ry))
        S.wire((xs[3], ry), pin('U2', '3'))
        # 12 V sense divider, drawn on its own below the input
        sp = (x + 15.24, y + 27.94)
        S.wire(sp, at(sp, 0, -2.54)); port('+12V', sp[0], sp[1] - 2.54)
        m = hang('R7', sp)
        hang('R8', m, 'GND')
        c = at(m, 10.16)
        S.wire(m, c, at(c, 10.16)); hang('C1', c, 'GND')
        S.label('V12_SENSE', c[0] + 10.16, c[1])
        en = pin('U2', '2')
        S.wire(en, (ux - 5.08, en[1]), (ux - 5.08, ry))
        term('U2', '4', 'GND')
        sw = pin('U2', '5')
        swn = at(sw, 2.54)
        S.wire(sw, swn)
        S.wire(swn, at(swn, 5.08), at(swn, 10.16))
        o = series('L1', at(swn, 10.16))
        c5n = at(swn, 5.08)
        put_pin('C5', '2', at(c5n, 0, -2.54))
        S.wire(c5n, at(c5n, 0, -2.54))
        term('C5', '1', 'BUCK_BST')
        term('U2', '6', 'BUCK_BST', 2.54)
        fb = pin('U2', '1')
        S.wire(fb, (o[0], fb[1]), o)
        # output rail
        ox = [o[0] + 10.16, o[0] + 22.86, o[0] + 33.02]
        S.wire(o, *[(xx, o[1]) for xx in ox])
        dbtag('5V_BUCK', o, up=True, length=5.08)
        hang('C6', (ox[0], o[1]), 'GND'); hang('C7', (ox[1], o[1]), 'GND')
        kk = diode_r('D4', (ox[2], o[1]))
        e = at(kk, 5.08); S.wire(kk, e); drop('+5V', e, 2.54)
        # ERC: 12 V and GND enter the board at J2
        S.wire(n, at(n, 0, 5.08)); S.power('PWR_FLAG', n[0], n[1] + 5.08, rot=180)
        S.note("D2 blocks reverse polarity; D3 (SMAJ15A) clamps surges. 15 V max input.\n"
               "V12_SENSE = 12 V x 100k/660k: 2.27 V at 15 V, inside the ADC range (D23).\n"
               "AP63205: fixed 5 V out. L1/C6/C7 to be checked against the datasheet (D25).",
               x - 5.08, y + 30.48, 1.0)
