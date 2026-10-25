"""Blocks 5-6: ESP32 module with its support circuits; sensor ports."""
import dbase as B
from dbase import tag as dbtag, pwr_pin, side, put, put_pin, pin, port, drop, term, hang, rise, series, diode_r, at

LEFT = [('8', 'EN'), ('12', 'RS485_RX'), ('13', 'V12_SENSE'), ('5', 'RS485_TX'), ('6', 'VBAT_SENSE'),
        ('22', 'STATUS_LED'), ('23', 'BOOT'), ('16', 'I2C_SDA'), ('19', 'I2C_SCL'), ('20', 'RAIL_EN'),
        ('30', 'RXD0'), ('31', 'TXD0')]
RIGHT = [('17', 'USB_C6_D_N'), ('18', 'USB_C6_D_P'), ('26', 'USB_C3_D_N'), ('27', 'USB_C3_D_P'),
         ('15', 'GPIO_A'), ('25', 'BTN2'), ('28', 'GPIO_B')]

def pullup_sw(rref, swref, net, x, y):
    """+3V3 -> R -> node(label) -> switch -> GND, drawn as one vertical column."""
    n = (x, y)
    rise(rref, n, '+3V3', bottom_pin='2')
    put_pin(swref, '1', at(n, 0, 2.54), rot=270)
    assert pin(swref, '2')[1] > n[1]
    S = B.S
    S.wire(n, pin(swref, '1'))
    term(swref, '2', 'GND')
    S.wire(n, at(n, -5.08)); S.label(net, n[0] - 5.08, n[1], angle=180)

def module(x, y):
    S = B.S
    with S.block("ESP32-C6 / C3 MODULE"):
        put('U6', x, y)
        for p, net in LEFT: term('U6', p, net, 5.08)
        for p, net in RIGHT: term('U6', p, net, 5.08)
        S.nc('U6', '9', '10', '24', '29', '21', '4', '7', '32', '33', '34', '35')
        v = pin('U6', '3')
        m = at(v, 0, -10.16); t = at(v, 0, -12.7)
        S.wire(v, m, t); port('+3V3', *t)
        S.wire(m, at(m, 10.16), at(m, 17.78))
        hang('C17', at(m, 10.16), 'GND'); hang('C18', at(m, 17.78), 'GND')
        term('U6', '1', 'GND')
        # support circuits, left of the module
        sx = x - 109.22
        # reset: pull-up + RC + button
        n = (sx, y - 25.4)
        rise('R22', n, '+3V3', bottom_pin='2')
        S.wire(n, at(n, 7.62)); hang('C19', at(n, 7.62), 'GND')
        put_pin('SW1', '1', at(n, 0, 2.54), rot=270); S.wire(n, pin('SW1', '1')); term('SW1', '2', 'GND')
        S.wire(n, at(n, -5.08)); S.label('EN', n[0] - 5.08, n[1], angle=180)
        # BOOT / BTN1 on IO9: hold during reset = download mode; afterwards an ordinary user button
        pullup_sw('R23', 'SW2', 'BOOT', sx, y + 2.54)
        # status LED on IO8 (strap: R25 keeps it high at reset)
        n = (sx + 20.32, y + 2.54)
        rise('R25', n, '+3V3', bottom_pin='2')
        a = at(n, 10.16, -20.32)
        S.wire(a, at(a, 0, -2.54)); port('+3V3', a[0], a[1] - 2.54)
        put_pin('R26', '1', a); r2 = pin('R26', '2')
        put_pin('D8', '2', at(r2, 0, 2.54), rot=90)
        assert pin('D8', '1')[1] > r2[1]
        S.wire(r2, pin('D8', '2'))
        kk = pin('D8', '1')
        S.wire(kk, (kk[0], n[1]), n)
        S.wire(n, at(n, 0, 5.08)); S.label('STATUS_LED', n[0], n[1] + 5.08, angle=270)
        # RS485_TX pull-up (also holds the C3's GPIO2 strap high)
        n = (sx + 45.72, y + 2.54)
        rise('R24', n, '+3V3', bottom_pin='2')
        S.wire(n, at(n, 0, 5.08)); S.label('RS485_TX', n[0], n[1] + 5.08, angle=270)
        # user buttons (C6-only pads)
        pullup_sw('R27', 'SW3', 'BTN2', sx, y + 30.48)
        # UART0 debug header (DNP)
        put('J5', sx + 35.56, y + 33.02, mirror='y')
        term('J5', '1', 'TXD0', 2.54); term('J5', '2', 'RXD0', 2.54); pwr_pin('J5', '3', 'GND')
        S.note("Pads marked [C6]/[C3] differ between the two modules (D15, D18).\n"
               "Everything essential uses pads that work on both; BTN2 and GPIO_A/B work\n"
               "only with a C6. SW2 is BOOT and BTN1 (IO9 strap). IO8/IO9 must be high at reset.\n"
               "C17/C18 close to module pin 3.",
               x - 109.22, y + 48.26, 1.0)

def ports(x, y):
    S = B.S
    with S.block("SENSOR PORTS: I2C, OLED, GPIO"):
        # I2C bus to the sensor terminal; pull-ups on +3V3_SW (the only pull-ups on the bus)
        sda = (x, y); scl = (x, y + 17.78)
        S.label('I2C_SDA', sda[0], sda[1], angle=180); S.label('I2C_SCL', scl[0], scl[1], angle=180)
        put_pin('J8', '2', at(sda, 45.72))
        S.wire(sda, at(sda, 12.7), pin('J8', '2'))
        rise('R32', at(sda, 12.7), '+3V3_SW', bottom_pin='2')
        p3 = pin('J8', '3')
        S.wire(scl, at(scl, 12.7), (p3[0] - 15.24, scl[1]), (p3[0] - 15.24, p3[1]), p3)
        rise('R33', at(scl, 12.7), '+3V3_SW', bottom_pin='2')
        pwr_pin('J8', '1', '+3V3_SW', 5.08, 5.08); pwr_pin('J8', '4', 'GND', 5.08, 2.54)
        # OLED header
        # OLED header, drawn upside down so SDA/SCL sit on top like the bus; power below
        put('J9', sda[0] + 45.72, sda[1] + 33.02, rot=180)
        term('J9', '4', 'I2C_SDA', 5.08); term('J9', '3', 'I2C_SCL', 5.08)
        pwr_pin('J9', '1', 'GND', 2.54, 2.54)
        p2 = pin('J9', '2'); a2 = at(p2, side('J9', '2') * 10.16); S.wire(p2, a2, at(a2, 0, 7.62)); port('+3V3_SW', *at(a2, 0, 7.62), up=False)

        # GPIO terminals with optional pull-up / pull-down (DNP)
        for k, (net, ru, rd, j) in enumerate((('GPIO_A', 'R28', 'R29', 'J6'), ('GPIO_B', 'R30', 'R31', 'J7'))):
            gx, gy = x - 15.24 + 30.48 * k, y + 55.88
            n = (gx, gy)
            S.wire(at(n, -5.08), n); S.label(net, n[0] - 5.08, n[1], angle=180)
            rise(ru, n, '+3V3_SW', bottom_pin='2')
            hang(rd, n, 'GND')
            put_pin(j, '1', at(n, 10.16))
            S.wire(n, pin(j, '1')); pwr_pin(j, '2', 'GND', 2.54, 2.54)
        S.note("Pull-ups are on +3V3_SW, so nothing back-powers sensors when the rail is off.\n"
               "Firmware must switch +3V3_SW on before ANY I2C traffic, including relay changes:\n"
               "the TCA9534 (on always-on 3V3) holds its outputs meanwhile (D20). OLED shares the bus.",
               x - 15.24, y + 71.12, 1.0)
