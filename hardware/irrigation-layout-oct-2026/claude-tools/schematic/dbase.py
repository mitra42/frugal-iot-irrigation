"""Shared helpers for draw.py (schlib-based readable schematic)."""
import os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import circuit

RAIL = {'GND': 'GND', '+3V3': '+3V3', '+5V': '+5V', '+12V': '+12V', 'VBUS': 'VBUS',
        'VSYS': 'irrigation:VSYS', 'VBAT': 'irrigation:VBAT',
        '+3V3_SW': 'irrigation:+3V3_SW', '+5V_SW': 'irrigation:+5V_SW'}

# ---- spec, from circuit.py (the single source of truth) ----
PARTS, NETS, NO_CONNECT = {}, {}, []
_cnt = {}
for p in circuit.P:
    _cnt[p['prefix']] = _cnt.get(p['prefix'], 0) + 1
    ref = f"{p['prefix']}{_cnt[p['prefix']]}"
    props = {'Footprint': p['fp'], 'MPN': p['mpn'] or p['value']}
    if p['lcsc']: props['LCSC'] = p['lcsc']
    if p['note']: props['Note'] = p['note']
    PARTS[ref] = dict(lib=p['lib'], value=p['value'], props=props, dnp=p['dnp'])
    for pin, net in p['nets'].items():
        if net == 'NC': NO_CONNECT.append((ref, pin))
        else: NETS.setdefault(net, []).append((ref, pin))

S = None   # current sheet, set by draw.py
G = 2.54
def snap(v, g=1.27): return round(round(v / g) * g, 4)
def at(p, dx=0, dy=0): return (round(p[0] + dx, 4), round(p[1] + dy, 4))

def put(ref, x, y, rot=0, mirror=None, unit=1):
    P = PARTS[ref]
    S.place(ref, P['lib'], P['value'], snap(x, 2.54), snap(y, 2.54), rot, mirror, unit=unit, props=P['props'], dnp=P['dnp'])
    return ref

def put_pin(ref, pin, where, rot=0, mirror=None, unit=1):
    """Place ref so that its pin lands exactly on `where`."""
    put(ref, 0, 0, rot, mirror, unit)
    px, py = S.pin(ref, pin, unit) if unit != 1 else S.pin(ref, pin)
    sym = S._sym(ref, unit)[0] if unit != 1 else S._sym(ref)[0]
    sym['x'], sym['y'] = round(where[0] - px, 4), round(where[1] - py, 4)
    S._pin_pts = S._fields = S._items = None
    return ref

def pin(ref, k): return S.pin(ref, k)

def port(net, x, y, up=True):
    kind = RAIL[net]
    if net == 'GND': S.power(kind, x, y)
    else: S.power(kind, x, y, rot=0 if up else 180)
    return (x, y)

def drop(net, p, length=2.54, up=True):
    """Short vertical wire from p ending in a rail symbol (or label)."""
    e = at(p, 0, -length if up else length)
    S.wire(p, e)
    if net in RAIL: port(net, *e, up=up)
    else: S.label(net, e[0], e[1], angle=90 if up else 270)
    return e

def term(ref, k, net, length=2.54):
    """Stub out of a pin ending in a rail port or a net label."""
    if net in RAIL: return S.stub(ref, k, length, power=RAIL[net])
    return S.stub(ref, k, length, label=net)

def hang(ref, node, bottom=None, top_pin='1', bottom_pin=None):
    """Vertical 2-pin part hanging below `node` (top_pin on node)."""
    put_pin(ref, top_pin, node, rot=0)
    bp = bottom_pin or ('2' if top_pin == '1' else '1')
    assert abs(S.pin(ref, bp)[0] - node[0]) < 1e-6 and S.pin(ref, bp)[1] > node[1], (ref, 'not vertical-down')
    if bottom: term(ref, bp, bottom)
    return S.pin(ref, bp)

def rise(ref, node, top=None, bottom_pin='2'):
    """Vertical 2-pin part standing above `node` (bottom_pin on node)."""
    put_pin(ref, bottom_pin, node, rot=0)
    tp = '1' if bottom_pin == '2' else '2'
    assert S.pin(ref, tp)[1] < node[1], (ref, 'not vertical-up')
    if top: term(ref, tp, top)
    return S.pin(ref, tp)

def series(ref, start, first='1', rot=None):
    """Horizontal 2-pin part with pin `first` on `start`, extending right."""
    if rot is None: rot = 90 if first == '1' else 270
    put_pin(ref, first, start, rot=rot)
    other = '2' if first == '1' else '1'
    e = S.pin(ref, other)
    assert abs(e[1] - start[1]) < 1e-6 and e[0] > start[0], (ref, 'not horizontal-right', rot, e, start)
    return e

def diode_r(ref, start):
    """Diode/LED pointing right: anode (pin 2) on start, cathode (pin 1) to the right."""
    return series(ref, start, first='2', rot=180)

def tag(net, p, up=True, length=2.54):
    """Label a net with a short vertical branch off a wire vertex p (never mid-wire)."""
    e = at(p, 0, -length if up else length)
    S.wire(p, e)
    S.label(net, e[0], e[1], angle=90 if up else 270)
    return e

def side(ref, k):
    sym = S._sym(ref)[0]
    return -1 if S.pin(ref, k)[0] < sym['x'] else 1

def pwr_pin(ref, k, net, out=2.54, rise_=2.54):
    """Connector power pin: short horizontal stub, then up to a rail port
    (or down to GND), so the port stands upright instead of lying sideways."""
    p = S.pin(ref, k)
    a = at(p, side(ref, k) * out)
    e = at(a, 0, rise_ if net == 'GND' else -rise_)
    S.wire(p, a, e)
    port(net, *e)
    return e
