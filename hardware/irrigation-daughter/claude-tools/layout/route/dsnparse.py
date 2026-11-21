"""Minimal Specctra DSN reader: pads (as shapely geometries in mm), nets, classes."""
import re, math
from shapely.geometry import Point, Polygon, LineString, box
from shapely import affinity
def tokenize(s):
    return re.findall(r'\(|\)|"[^"]*"|[^\s()]+', s)
def parse(tokens):
    stack = [[]]
    for t in tokens:
        if t == '(': stack.append([])
        elif t == ')': x = stack.pop(); stack[-1].append(x)
        else: stack[-1].append(t.strip('"'))
    return stack[0][0]
def find(node, key):
    return [c for c in node if isinstance(c, list) and c and c[0] == key]
def load(path):
    T = parse(tokenize(open(path).read()))
    res = float(find(T, 'resolution')[0][2]) if find(T, 'resolution') else 1.0
    u = 1000.0  # DSN coordinates are um (see skill: 1 unit = 1 um)
    lib = find(T, 'library')[0]
    stacks = {}
    for ps in find(lib, 'padstack'):
        shp = {}
        for s in find(ps, 'shape'):
            g = s[1]; kind, layer = g[0], g[1]
            if kind == 'circle':
                d = float(g[2]) / u; cx = float(g[3]) / u if len(g) > 3 else 0; cy = float(g[4]) / u if len(g) > 4 else 0
                geo = Point(cx, -cy).buffer(d / 2, 16)
            elif kind == 'rect':
                x0, y0, x1, y1 = [float(v) / u for v in g[2:6]]; geo = box(min(x0, x1), -max(y0, y1), max(x0, x1), -min(y0, y1))
            elif kind == 'polygon':
                v = [float(x) / u for x in g[3:]]; geo = Polygon([(v[i], -v[i + 1]) for i in range(0, len(v) - 1, 2)])
                if float(g[2]) > 0: geo = geo.buffer(float(g[2]) / u / 2)
            elif kind == 'path':
                w = float(g[2]) / u; v = [float(x) / u for x in g[3:]]
                pts = [(v[i], -v[i + 1]) for i in range(0, len(v) - 1, 2)]
                geo = (LineString(pts) if len(pts) > 1 else Point(pts[0])).buffer(w / 2, 16)
            else: continue
            shp[layer] = geo
        stacks[ps[1]] = shp
    images = {}
    for im in find(lib, 'image'):
        pins = []
        for p in find(im, 'pin'):
            rest = p[1:]; rot = 0
            if isinstance(rest[1], list) and rest[1][0] == 'rotate': rot = float(rest[1][1]); rest = [rest[0]] + rest[2:]
            stack, num, x, y = rest[0], rest[1], float(rest[2]) / u, -float(rest[3]) / u
            pins.append((num, stack, x, y, rot))
        images[im[1]] = pins
    pads = []   # (ref, num, layer, geometry)
    for comp in find(find(T, 'placement')[0], 'component'):
        img = comp[1]
        for pl in find(comp, 'place'):
            ref, x, y, side, rot = pl[1], float(pl[2]) / u, -float(pl[3]) / u, pl[4], float(pl[5])
            for num, stack, px, py, prot in images[img]:
                for layer, geo in stacks[stack].items():
                    g = affinity.rotate(geo, -prot, origin=(0, 0))
                    g = affinity.translate(g, px, py)
                    if side == 'back': g = affinity.scale(g, -1, 1, origin=(0, 0))
                    g = affinity.rotate(g, -rot, origin=(0, 0))
                    g = affinity.translate(g, x, y)
                    pads.append((ref, num, layer, g))
    net = find(T, 'network')[0]
    pin2net = {}
    for n in find(net, 'net'):
        for pinsnode in find(n, 'pins'):
            for p in pinsnode[1:]: pin2net[p] = n[1]
    cls = {}
    for c in find(net, 'class'):
        names = [x for x in c[2:] if not isinstance(x, list)]
        rule = find(find(c, 'rule')[0], 'width')[0][1] if find(c, 'rule') else '250'
        clr = find(find(c, 'rule')[0], 'clearance')
        for nm in names: cls[nm] = (c[1], float(rule) / u, float(clr[0][1]) / u if clr else 0.2)
    return pads, pin2net, cls
