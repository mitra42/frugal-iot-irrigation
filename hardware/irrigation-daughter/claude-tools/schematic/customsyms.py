"""Custom symbols for the project library 'irrigation'."""
from sexp import Str

def _eff(size=1.27, hide=False, justify=None):
    e = ['effects', ['font', ['size', size, size]]]
    if justify: e.append(['justify'] + justify.split())
    if hide: e.append(['hide', 'yes'])
    return e

def _prop(name, val, x=0, y=0, hide=False):
    p = ['property', Str(name), Str(val), ['at', round(x, 4), round(y, 4), 0], ['show_name', 'no'], ['do_not_autoplace', 'no']]
    if hide: p.append(['hide', 'yes'])
    p.append(_eff())
    return p

def _pin(num, name, typ, x, y, a, length=2.54, hide=False):
    p = ['pin', typ, 'line', ['at', round(x, 4), round(y, 4), a], ['length', length]]
    if hide: p.append(['hide', 'yes'])
    p += [['name', Str(name), _eff()], ['number', Str(num), _eff()]]
    return p

def _sym(name, props, body, pins, pin_offset=1.016):
    return (['symbol', Str(name), ['pin_names', ['offset', pin_offset]],
             ['exclude_from_sim', 'no'], ['in_bom', 'yes'], ['on_board', 'yes'], ['in_pos_files', 'yes'],
             ['duplicate_pin_numbers_are_jumpers', 'no']] + props +
            [['symbol', Str(name.split(':')[-1] + '_0_1'), body],
             ['symbol', Str(name.split(':')[-1] + '_1_1')] + pins])

def _rect(x1, y1, x2, y2):
    return ['rectangle', ['start', round(x1, 4), round(y1, 4)], ['end', round(x2, 4), round(y2, 4)],
            ['stroke', ['width', 0.254], ['type', 'default']], ['fill', ['type', 'background']]]

# Module: one footprint, either ESP32-C6-MINI-1U or ESP32-C3-MINI-1U fitted.
# Pin map by pad: C6 from KiCad stock symbol (agrees with Espressif datasheet),
# C3 from Espressif ESP32-C3-MINI-1 datasheet v2.2 table 3-1; both re-checked 2026-10-14
# (C6 against ESP32-C6-MINI-1 datasheet v1.5 table 3-1). Copies in ../../datasheets/.
LEFT = [  # (pad, name, type)
    ('8', 'EN', 'input'),
    ('12', 'IO0', 'bidirectional'),
    ('13', 'IO1', 'bidirectional'),
    ('5', 'IO2', 'bidirectional'),
    ('6', 'IO3', 'bidirectional'),
    ('22', 'IO8', 'bidirectional'),
    ('23', 'IO9', 'bidirectional'),
    ('16', 'IO7[C6]/IO10[C3]', 'bidirectional'),
    ('19', 'IO14[C6]/IO5[C3]', 'bidirectional'),
    ('20', 'IO15[C6]/IO6[C3]', 'bidirectional'),
    ('30', 'RXD0', 'bidirectional'),
    ('31', 'TXD0', 'bidirectional'),
]
RIGHT = [
    ('17', 'USB_D-[C6]/NC[C3]', 'bidirectional'),
    ('18', 'USB_D+[C6]/IO4[C3]', 'bidirectional'),
    ('26', 'IO20[C6]/USB_D-[C3]', 'bidirectional'),
    ('27', 'IO21[C6]/USB_D+[C3]', 'bidirectional'),
    ('9', 'IO4[C6]/NC[C3]', 'bidirectional'),
    ('10', 'IO5[C6]/NC[C3]', 'bidirectional'),
    ('15', 'IO6[C6]/NC[C3]', 'bidirectional'),
    ('24', 'IO18[C6]/NC[C3]', 'bidirectional'),
    ('25', 'IO19[C6]/NC[C3]', 'bidirectional'),
    ('28', 'IO22[C6]/NC[C3]', 'bidirectional'),
    ('29', 'IO23[C6]/NC[C3]', 'bidirectional'),
    ('21', 'NC[C6]/IO7[C3]', 'bidirectional'),
    ('4', 'NC', 'no_connect'),
    ('7', 'NC', 'no_connect'),
    ('32', 'NC', 'no_connect'),
    ('33', 'NC', 'no_connect'),
    ('34', 'NC', 'no_connect'),
    ('35', 'NC', 'no_connect'),
]
GND_PADS = ['1', '2', '11', '14'] + [str(i) for i in range(36, 54)]

def module_symbol(libname='irrigation'):
    W = 22.86; X = W + 2.54
    nrows = max(len(LEFT), len(RIGHT))
    top = 2.54 * (nrows // 2 + 1); bot = top - 2.54 * (nrows + 1)
    pins = []
    for i, (n, nm, t) in enumerate(LEFT):
        pins.append(_pin(n, nm, t, -X, top - 2.54 * (i + 1), 0))
    for i, (n, nm, t) in enumerate(RIGHT):
        pins.append(_pin(n, nm, t, X, top - 2.54 * (i + 1), 180))
    pins.append(_pin('3', '3V3', 'power_in', 0, top + 5.08, 270))
    for k, n in enumerate(GND_PADS):
        pins.append(_pin(n, 'GND', 'power_in' if k == 0 else 'passive', 0, bot - 2.54, 90, hide=k > 0))
    name = f'{libname}:ESP32-C3-C6-MINI-1U'
    props = [_prop('Reference', 'U', 0, top + 7.62), _prop('Value', 'ESP32-C3-C6-MINI-1U', 0, bot - 5.08),
             _prop('Footprint', 'irrigation:ESP32-C3-C6-MINI-1U', 0, 0, True),
             _prop('Datasheet', 'https://documentation.espressif.com/esp32-c6-mini-1_mini-1u_datasheet_en.pdf', 0, 0, True),
             _prop('Description', 'ESP32-C6-MINI-1U or ESP32-C3-MINI-1U on a shared footprint. [C6]/[C3] mark module-specific pad functions', 0, 0, True)]
    return _sym(name, props, _rect(-W, top + 2.54, W, bot), pins), (top, bot, X)

def fs8205_symbol(libname='irrigation'):
    pins = [_pin('4', 'G1', 'input', -10.16, -2.54, 0), _pin('2', 'S1', 'passive', -10.16, 2.54, 0),
            _pin('3', 'S1', 'passive', -10.16, 2.54, 0, hide=True),
            _pin('5', 'G2', 'input', 10.16, -2.54, 180), _pin('6', 'S2', 'passive', 10.16, 2.54, 180),
            _pin('7', 'S2', 'passive', 10.16, 2.54, 180, hide=True),
            _pin('1', 'D', 'passive', 0, 7.62, 270), _pin('8', 'D', 'passive', 0, 7.62, 270, hide=True)]
    name = f'{libname}:FS8205A'
    props = [_prop('Reference', 'Q', 0, 8.89), _prop('Value', 'FS8205A', 0, -7.62),
             _prop('Footprint', 'Package_SO:TSSOP-8_4.4x3mm_P0.65mm', 0, 0, True),
             _prop('Datasheet', '~', 0, 0, True),
             _prop('Description', 'Dual N-MOSFET, common drain, for 1-cell Li-ion protection (with DW01A)', 0, 0, True)]
    return _sym(name, props, _rect(-7.62, 5.08, 7.62, -5.08), pins)
