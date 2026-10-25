"""Blocks 3-4: charger + protection; system power."""
import dbase as B
from dbase import tag as dbtag, pwr_pin, put, put_pin, pin, port, drop, term, hang, rise, series, diode_r, at

def charger(x, y):
    S = B.S
    with S.block("LI-ION CHARGER & CELL PROTECTION"):
        put('U3', x, y)
        v = pin('U3', '4')
        mid = at(v, 0, -5.08); topp = at(v, 0, -7.62)
        S.wire(v, mid, topp); port('+5V', *topp)
        c8 = at(mid, -20.32)
        S.wire(mid, c8); hang('C8', c8, 'GND')
        ce = pin('U3', '8'); S.wire(ce, at(ce, -5.08), at(ce, -5.08, -5.08)); port('+5V', *at(ce, -5.08, -5.08))  # CE tied high
        term('U3', '7', 'nCHRG', 5.08); term('U3', '6', 'nSTDBY', 5.08)
        g3, g9 = pin('U3', '3'), pin('U3', '9')
        S.wire(g9, at(g9, 0, 2.54), at(g3, 0, 2.54)); S.wire(g3, at(g3, 0, 2.54), at(g3, 0, 5.08)); port('GND', *at(g3, 0, 5.08))
        # BAT -> VBAT rail, raised above the IC so its cap clears TEMP/PROG
        b = pin('U3', '5')
        ry = b[1] - 10.16
        b1 = at(b, 7.62)
        S.wire(b, b1, (b1[0], ry))
        r = [b1[0] + 7.62, b1[0] + 15.24, b1[0] + 30.48]
        S.wire((b1[0], ry), *[(xx, ry) for xx in r])
        hang('C9', (r[0], ry), 'GND')
        drop('VBAT', (r[1], ry), 2.54)
        # J4 polarity (D28): pin 1 = cell -, pin 2 = cell +
        put_pin('J4', '2', (r[2] + 5.08, ry), mirror='y')
        S.wire((r[2], ry), pin('J4', '2'))
        term('J4', '1', 'CELL_NEG', 2.54)
        # TEMP: jumper to GND (NTC disabled) -- placed beyond the PROG resistors
        t = pin('U3', '1')
        tj = (t[0] + 40.64, t[1])
        S.wire(t, at(t, 35.56), tj)
        dbtag('CHG_TEMP', at(t, 35.56), up=False, length=5.08)
        e = series('JP2', tj, first='1', rot=0)
        term('JP2', '2', 'GND')
        # PROG: 4.7k fixed, second 4.7k via JP1 for 500 mA
        p = pin('U3', '2')
        p1 = at(p, 7.62); p2 = at(p, 25.4)
        S.wire(p, p1, p2)
        hang('R9', p1, 'GND')
        m = hang('R10', p2)
        put_pin('JP1', '1', m, rot=270)
        assert pin('JP1', '2')[1] > m[1]
        term('JP1', '2', 'GND')
        # LED indicators (open-drain outputs, lit from +5V)
        for k, (rr, dd, net) in enumerate((('R12', 'D5', 'nCHRG'), ('R13', 'D6', 'nSTDBY'))):
            s0 = (x - 45.72, y + 22.86 + 10.16 * k)
            term_pt = at(s0, -2.54)
            S.wire(term_pt, s0); port('+5V', *term_pt)
            e = series(rr, s0)
            kk = diode_r(dd, e)
            S.wire(kk, at(kk, 2.54)); S.label(net, kk[0] + 2.54, kk[1])
        # optional NTC (DNP): divider top resistor and 2-pin header
        s1 = (x - 45.72, y + 45.72)
        rise('R11', s1, '+5V', bottom_pin='2')
        put_pin('J3', '1', at(s1, 15.24), mirror='y')
        S.wire(s1, at(s1, 7.62), pin('J3', '1'))
        dbtag('CHG_TEMP', at(s1, 7.62), up=False, length=5.08)
        pwr_pin('J3', '2', 'GND')
        # ---- protection: DW01A + FS8205A in the cell's negative lead ----
        px, py = x + 10.16, y + 50.8
        put('U4', px, py)
        vc = pin('U4', '5')
        n = at(vc, -5.08)
        S.wire(vc, n)
        series('R14', at(n, -17.78)); S.wire(pin('R14', '2'), at(n, -5.08), n)
        S.wire(at(n, -5.08), at(n, -5.08, -5.08)); S.power('PWR_FLAG', n[0] - 5.08, n[1] - 5.08)
        term('R14', '1', 'VBAT')
        cb = hang('C10', n)
        g = pin('U4', '6')
        jn = (g[0] - 2.54, cb[1] + 2.54)
        S.wire(g, at(g, -2.54), jn); S.wire(cb, (cb[0], jn[1]), jn)
        S.wire((cb[0], jn[1]), (cb[0] - 5.08, jn[1])); S.label('CELL_NEG', cb[0] - 5.08, jn[1], angle=180)
        S.wire(jn, at(jn, 0, 5.08)); S.power('PWR_FLAG', jn[0], jn[1] + 5.08, rot=180)
        cs = pin('U4', '2')
        e = series('R15', at(cs, 2.54)); S.wire(cs, at(cs, 2.54)); term('R15', '2', 'GND')
        S.nc('U4', '4')
        # FS8205A: two N-MOSFETs back to back, drains common. A switches discharge (OD),
        # B switches charge (OC); the cell's negative lead runs S1 -> D -> D -> S2 -> GND.
        od, oc = pin('U4', '1'), pin('U4', '3')
        ym = od[1] + 5.08
        fy = ym + 10.16
        put('Q1', px - 10.16, fy, rot=270, unit=1)
        put('Q1', px + 10.16, fy, rot=270, mirror='y', unit=2)
        ga, gb = pin('Q1', '6'), pin('Q1', '4')
        assert abs(ga[0] - (px - 10.16)) < 1e-6 and ga[1] < fy, ga
        S.wire(od, (od[0], ym), (ga[0], ym), ga)
        S.wire(oc, (oc[0], ym), (gb[0], ym), gb)
        da, db = pin('Q1', '2'), pin('Q1', '5')
        S.wire(da, db)
        sa, sb = pin('Q1', '1'), pin('Q1', '3')
        S.wire(sa, at(sa, -5.08)); S.label('CELL_NEG', sa[0] - 5.08, sa[1], angle=180)
        e = at(sb, 5.08); S.wire(sb, e, at(e, 0, 2.54)); port('GND', *at(e, 0, 2.54))
        S.note("PROG: I = 1200 / R. 4.7k = 255 mA; bridge JP1 (2.35k) = 510 mA (D12).\n"
               "TEMP: JP2 bridged disables the NTC input. For a cell NTC, cut JP2 and fit\n"
               "R11 + J3 with values from the TP4056 datasheet (D27).\n"
               "J4 (JST-PH): pin 1 = cell -, pin 2 = cell +. JST-PH polarity is not standardised:\n"
               "check each cell before connecting (D28).\n"
               "Protection (DW01A + FS8205A) sits in the cell's negative lead: board GND is the pack's P-.",
               x - 45.72, y - 27.94, 1.0)
    return

def syspwr(x, y):
    S = B.S
    with S.block("SYSTEM POWER: LOAD SHARING, 3.3 V LDO, SWITCHED RAILS"):
        a = (x, y)
        drop('+5V', a, 2.54)
        k = diode_r('D7', at(a, 5.08)); S.wire(a, at(a, 5.08))
        ry = k[1]
        xs = [k[0] + 7.62, k[0] + 20.32, k[0] + 27.94]
        S.wire(k, *[(xx, ry) for xx in xs])
        # load-sharing P-FET below the rail: S up to VSYS, D down to VBAT, gate = +5V
        put_pin('Q2', '2', (xs[0], ry + 2.54), mirror='x')
        S.wire((xs[0], ry), pin('Q2', '2'))
        term('Q2', '3', 'VBAT', 2.54)
        gp = pin('Q2', '1')
        gn = (a[0], gp[1])
        S.wire(a, gn, gp)
        hang('R16', gn, 'GND')
        hang('C11', (xs[1], ry), 'GND')
        S.wire((xs[1], ry), at((xs[1], ry), 0, -2.54)); S.power('PWR_FLAG', xs[1], ry - 2.54)
        # LDO
        put_pin('U5', '1', (xs[2] + 7.62, ry))
        S.wire((xs[2], ry), pin('U5', '1'))
        en = pin('U5', '3')
        S.wire(en, (en[0] - 2.54, en[1]), (en[0] - 2.54, ry))
        term('U5', '2', 'GND'); S.nc('U5', '4')
        vo = pin('U5', '5')
        o = [vo[0] + 5.08, vo[0] + 12.7, vo[0] + 17.78]
        S.wire(vo, *[(xx, vo[1]) for xx in o])
        hang('C12', (o[0], vo[1]), 'GND'); hang('C13', (o[1], vo[1]), 'GND')
        drop('+3V3', (o[2], vo[1]), 2.54)
        # battery sense divider
        bx, by = o[2] + 15.24, ry - 5.08
        S.wire((bx, by), at((bx, by), 0, -2.54)); port('VBAT', bx, by - 2.54)
        m = hang('R17', (bx, by))
        hang('R18', m, 'GND')
        c = at(m, 7.62); S.wire(m, c); hang('C14', c, 'GND')
        S.wire(c, at(c, 5.08)); S.label('VBAT_SENSE', c[0] + 5.08, c[1])
        # switched rails, one P-FET each, gates pulled low together by RAIL_EN
        for i, (qp, rp, qn, cc, src, out) in enumerate((('Q3', 'R19', 'Q4', 'C15', '+3V3', '+3V3_SW'),
                                                       ('Q5', 'R20', 'Q6', 'C16', '+5V', '+5V_SW'))):
            sx, sy = x + 20.32 + 50.8 * i, y + 38.1
            put(qp, sx, sy, mirror='x')
            assert pin(qp, '2')[1] < pin(qp, '3')[1]
            term(qp, '2', src, 2.54)
            d = pin(qp, '3')
            d1 = at(d, 0, 2.54); d2 = at(d1, 10.16)
            S.wire(d, d1, at(d1, 5.08), d2)
            hang(cc, at(d1, 5.08), 'GND')
            drop(out, d2, 2.54)
            S.wire(d2, at(d2, 7.62)); S.power('PWR_FLAG', d2[0] + 7.62, d2[1])
            g = pin(qp, '1')
            gn = at(g, -5.08)
            S.wire(g, gn)
            rise(rp, gn, src, bottom_pin='2')
            put_pin(qn, '3', at(gn, 0, 5.08))
            S.wire(gn, pin(qn, '3'))
            term(qn, '2', 'GND')
            gq = pin(qn, '1')
            if i == 0:
                r = at(gq, -5.08)
                S.wire(gq, r); hang('R21', r, 'GND')
                S.wire(r, at(r, -2.54)); S.label('RAIL_EN', r[0] - 2.54, r[1], angle=180)
            else:
                term(qn, '1', 'RAIL_EN', 5.08)
        S.note("D7 + Q2: with 5 V present VSYS comes through D7 and Q2 is off;\n"
               "without it Q2 turns on and the cell feeds VSYS. The charger never carries the load.\n"
               "VBAT_SENSE = VBAT / 2 (1M/1M, ~2 uA). RAIL_EN low (default, R21) = both rails off.\n"
               "+5V_SW only exists while USB or 12 V is present (no boost from the cell).",
               x - 5.08, y + 66.04, 1.0)
