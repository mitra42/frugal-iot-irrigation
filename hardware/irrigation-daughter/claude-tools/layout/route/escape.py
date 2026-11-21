import dsnparse, math, sys
from shapely.geometry import LineString
from shapely.strtree import STRtree
pads, pin2net, cls = dsnparse.load(sys.argv[1] if len(sys.argv) > 1 else 'board_r.dsn')
def netof(ref, num): return pin2net.get(f'{ref}-{num}')
geoms = [g for _, _, _, g in pads]; tree = STRtree(geoms)
def clsof(n): return cls.get(n, ('kicad_default', 0.25, 0.2))
bad = []
seen = set()
for i, (ref, num, layer, g) in enumerate(pads):
    n = netof(ref, num)
    if not n or n == 'GND' or (ref, num, layer) in seen: continue
    seen.add((ref, num, layer))
    cname, w, clr = clsof(n); c = g.centroid
    ok = 0
    for k in range(16):
        a = math.radians(22.5 * k)
        seg = LineString([(c.x, c.y), (c.x + 1.5 * math.cos(a), c.y + 1.5 * math.sin(a))]).buffer(w / 2, 8)
        hit = False
        for j in tree.query(seg.buffer(1.0)):
            r2, n2, l2, g2 = pads[j]
            if l2 != layer or (r2 == ref and n2 == num): continue
            nn = netof(r2, n2)
            if nn == n: continue
            if seg.distance(g2) < max(clr, clsof(nn)[2] if nn else 0.2) - 1e-4: hit = True; break
        if not hit: ok += 1
    if ok == 0: bad.append((f'{ref}.{num}', layer, n, cname, w))
print(len(bad), 'pad/layer combos with no escape at class width:')
for x in bad: print('  ', x)
