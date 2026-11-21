"""The daughter board's three blocks: host connector + OLED; 12 V input; expander + valve drivers.
The input and valve blocks are the irrigation board's (its dblk1.v12 without the buck, its dblk4.relays)."""
import dbase as B
from dbase import tag as dbtag, pwr_pin, put, put_pin, pin, port, drop, term, hang, rise, series, diode_r, at, side

def host(x, y):
    S = B.S
    with S.block("TO THE HOST BOARD (SENSOR / LORA J2) & OLED"):
        put('J1', x, y, mirror='y')   # pin 1 (V12) at the top, GND (pin 5) at the bottom so its symbol hangs clear
        term('J1', '1', 'V12_SENSE', 12.7)
        p2 = pin('J1', '2'); a2 = at(p2, 33.02); S.wire(p2, a2, at(a2, 0, -12.7)); port('+3V3_SW', *at(a2, 0, -12.7))
        S.wire(a2, at(a2, 7.62)); S.power('PWR_FLAG', a2[0] + 7.62, a2[1])
        term('J1', '3', 'I2C_SCL', 12.7); term('J1', '4', 'I2C_SDA', 12.7)
        pwr_pin('J1', '5', 'GND', 5.08, 2.54)
        # OLED header, drawn upside down so SDA/SCL sit on top like the bus; power below
        put('J3', x + 96.52, y + 2.54, rot=180)
        term('J3', '4', 'I2C_SDA', 5.08); term('J3', '3', 'I2C_SCL', 5.08)
        pwr_pin('J3', '1', 'GND', 2.54, 2.54)
        p2 = pin('J3', '2'); a2 = at(p2, side('J3', '2') * 10.16); S.wire(p2, a2, at(a2, 0, 7.62)); port('+3V3_SW', *at(a2, 0, 7.62), up=False)
        S.note("J1 -> host J2 by a 5-wire cable: GND, SDA, SCL, 3V3_SW to host J2.1-4, V12 to host J2.9\n"
               "(SENS2, analog; the host's 100 nF filter is fitted). On the board J1 reads in that order (D2, D4).\n"
               "No I2C pull-ups here: the host's 4.7k on 3V3_SW are the bus's only ones.\n"
               "Everything on this board's logic side is powered from the host's 3V3_SW (D3).",
               x - 5.08, y + 22.86, 1.0)

def v12(x, y):
    S = B.S
    with S.block("12 V INPUT & PROTECTION, 12 V SENSE"):
        put('J2', x, y, mirror='y')
        p1 = pin('J2', '1')
        pwr_pin('J2', '2', 'GND')
        a = at(p1, 7.62)
        S.wire(p1, at(p1, 2.54), a)
        dbtag('12V_IN', at(p1, 2.54), up=True, length=5.08)
        f = series('F1', a)
        a2 = at(f, 5.08); S.wire(f, a2)
        dbtag('12V_FUSED', a2, up=True, length=5.08)
        k = diode_r('D1', a2)
        n = at(k, 5.08)
        S.wire(k, n)
        drop('+12V', n, 2.54)
        ry = k[1]
        xs = [n[0] + 7.62, n[0] + 33.02, n[0] + 45.72]
        S.wire(n, *[(xx, ry) for xx in xs])
        put_pin('D2', '1', (xs[0], ry), rot=270)          # TVS, cathode up
        assert pin('D2', '2')[1] > ry
        term('D2', '2', 'GND')
        hang('C1', (xs[1], ry), 'GND')
        m = hang('R1', (xs[2], ry))
        hang('R2', m, 'GND')
        S.wire(m, at(m, 10.16)); S.label('V12_SENSE', m[0] + 10.16, m[1])
        # ERC: 12 V and GND enter the board at J2
        S.wire(n, at(n, 0, 5.08)); S.power('PWR_FLAG', n[0], n[1] + 5.08, rot=180)
        gp = (x - 5.08, y + 15.24)
        S.wire(gp, at(gp, 0, -2.54)); S.power('PWR_FLAG', gp[0], gp[1] - 2.54); port('GND', *gp)
        S.note("F1 (3 A hold, 16 V) trips on a shorted cable; D1 (SS54, 5 A) blocks reverse polarity;\n"
               "D2 (SMAJ15A) clamps surges. 15 V max. As the irrigation board (its D77).\n"
               "V12_SENSE = 12 V x 100k/660k: 2.27 V at 15 V. ~18 uA from the battery, always (D4).",
               x - 5.08, y + 30.48, 1.0)

def relays(x, y):
    S = B.S
    with S.block("I2C EXPANDER & VALVE DRIVERS (LOW-SIDE MOSFET PER VALVE)"):
        put('U1', x, y)
        v = pin('U1', '16')
        m = at(v, 0, -12.7); t = at(v, 0, -15.24)
        S.wire(v, m, t); port('+3V3_SW', *t)
        S.wire(m, at(m, -10.16)); hang('C2', at(m, -10.16), 'GND')
        term('U1', '8', 'GND')
        term('U1', '14', 'I2C_SCL', 5.08); term('U1', '15', 'I2C_SDA', 5.08)
        S.nc('U1', '13')
        for p in ('1', '2', '3'): term('U1', p, 'GND', 2.54)
        for k, tp in enumerate(('4', '5', '6', '7', '9', '10', '11', '12')):
            term('U1', tp, f'REL{k+1}', 5.08)
        def ref(prefix, net, pinno):
            return next(r for r, p in B.NETS[net] if r[:len(prefix)] == prefix and r[len(prefix)].isdigit() and p == pinno)
        for i in range(8):   # two rows of four identical channels
            v = f'VALVE{i+1}'
            q = ref('Q', v, '3'); df = ref('D', v, '2'); led = ref('D', v, '1')
            rl = ref('R', f'LED_V{i+1}', '2'); rg = ref('R', f'REL{i+1}', '1'); j = ref('J', v, '2')
            jx, jy = x + 114.3 + 60.96 * (i % 4), y + 7.62 + 55.88 * (i // 4)
            put(j, jx, jy)
            pwr_pin(j, '1', '+12V', 5.08, 5.08)
            p2 = pin(j, '2')
            nd = at(p2, -10.16); nl = at(nd, -15.24); nq = at(nl, -15.24)
            S.wire(p2, nd, nl, nq)
            a = at(nd, 0, -2.54); S.wire(nd, a)
            put_pin(df, '2', a, rot=270)
            assert pin(df, '1')[1] < a[1], (df, 'diode not pointing up')
            drop('+12V', pin(df, '1'))
            a = at(nl, 0, -2.54); S.wire(nl, a)
            put_pin(led, '1', a, rot=90)
            top = at(pin(led, '2'), 0, -2.54)
            S.wire(pin(led, '2'), top)
            rise(rl, top, '+12V')
            put_pin(q, '3', at(nq, 0, 2.54)); S.wire(nq, pin(q, '3'))
            term(q, '2', 'GND')
            g = pin(q, '1'); gn = at(g, -5.08); gl = at(gn, -7.62)
            S.wire(g, gn, gl); S.label(f'REL{i+1}', gl[0], gl[1], angle=180)
            hang(rg, gn, 'GND')
        S.note("TCA9534 at 0x20 (A0-A2 low), on the host's 3V3_SW: with the host's sensor rail off it is unpowered\n"
               "and the 100k pull-downs hold every valve off, as they do while its pins are inputs (D3).\n"
               "P0-P7 high = valve 1-8 on. Valves 5-8 may be left unfitted.\n"
               "Valves: 12 V DC, low-side switched, up to ~2 A each; ~3 A in total, set by F1.\n"
               "Not for latching valves or 24 V AC valves.\n"
               "FLYBACK: each diode returns to the same +12V as its valve's V+ pin, after D1.",
               x - 5.08, y + 124.46, 1.0)
