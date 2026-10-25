"""KiCad python, one job: (1) delete dangling tracks named by DRC (matched by net + an endpoint at the reported
position), (2) rescue GND pads named in DRC unconnected_items: short F.Cu link to an existing GND via/THT pad,
else a new via. All geometry checked against other-net copper."""
import pcbnew, json, math, re
PCB = '../../esp32_io_board/esp32_io_board.kicad_pcb'
b = pcbnew.LoadBoard(PCB); mm = pcbnew.FromMM; V = pcbnew.VECTOR2I
drc = json.load(open('out/drc.json'))
dang = []
for v in drc['violations']:
    if v['type'] == 'track_dangling':
        it = v['items'][0]; d = it['description']
        net = re.search(r'\[(.*?)\]', d).group(1); lay = re.search(r'on (\w\.Cu)', d).group(1)
        ln = float(re.search(r'length ([\d.]+) mm', d).group(1))
        dang.append([net, lay, ln, mm(it['pos']['x']), mm(it['pos']['y']), False])
want = set()
for v in drc['unconnected_items']:
    for it in v['items']:
        m = re.match(r'(?:PTH )?[Pp]ad (\S+) \[GND\] of (\S+)', it['description'])
        if m: want.add((m.group(2), m.group(1)))
kill = []; other = []; gtargets = []; padinfo = {}
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        if t.GetNetname() == 'GND': gtargets.append((t.GetPosition().x, t.GetPosition().y))
        else: other.append(('c', t.GetPosition().x, t.GetPosition().y, t.GetWidth() / 2, None))
        continue
    n = t.GetNetname(); s, e = t.GetStart(), t.GetEnd()
    hit = None
    for dg in dang:
        dn, dl, dlen, x, y, used = dg
        if used or n != dn or b.GetLayerName(t.GetLayer()) != dl or abs(t.GetLength() / 1e6 - dlen) > 0.002: continue
        if math.hypot(s.x - x, s.y - y) < mm(0.06) or math.hypot(e.x - x, e.y - y) < mm(0.06): hit = dg; break
    if hit: hit[5] = True; kill.append(t); continue
    if n != 'GND': other.append(('s', s.x, s.y, t.GetWidth() / 2, (e.x, e.y), t.GetLayer()))
for f in b.GetFootprints():
    for p in f.Pads():
        bb = p.GetBoundingBox(); key = (f.GetReference(), p.GetNumber())
        if p.GetNetname() == 'GND':
            if p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH or key not in want: gtargets.append((p.GetPosition().x, p.GetPosition().y))
            if key in want: padinfo[key] = (p.GetPosition().x, p.GetPosition().y, max(bb.GetWidth(), bb.GetHeight()) / 2)
        else: other.append(('b', bb.GetX(), bb.GetY(), 0, (bb.GetRight(), bb.GetBottom())))
CLR = mm(0.2)
def ok_point(x, y, r):
    for o in other:
        k = o[0]
        if k == 'c' and math.hypot(x - o[1], y - o[2]) < o[3] + r + CLR: return False
        if k == 'b' and o[1] - r - CLR <= x <= o[4][0] + r + CLR and o[2] - r - CLR <= y <= o[4][1] + r + CLR: return False
        if k == 's':
            a, c, w, e = o[1], o[2], o[3], o[4]; dx, dy = e[0] - a, e[1] - c; L2 = dx * dx + dy * dy
            u = 0 if L2 == 0 else max(0, min(1, ((x - a) * dx + (y - c) * dy) / L2))
            if math.hypot(a + u * dx - x, c + u * dy - y) < w + r + CLR: return False
    return True
def ok_seg(x0, y0, x1, y1, hw, start_skip):
    n = max(2, int(math.hypot(x1 - x0, y1 - y0) / mm(0.05)))
    for i in range(n + 1):
        t = i / n; x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        if math.hypot(x - x0, y - y0) < start_skip: continue
        if not ok_point(x, y, hw): return False
    return True
adds = []
for key, (px, py, pr) in padinfo.items():
    done = False
    for gx, gy in [g for g in sorted(gtargets, key=lambda g: math.hypot(g[0] - px, g[1] - py)) if math.hypot(g[0] - px, g[1] - py) > mm(0.05)][:12]:
        if math.hypot(gx - px, gy - py) > mm(4): break
        if ok_seg(px, py, gx, gy, mm(0.15), pr):
            adds.append(('t', px, py, gx, gy)); done = True; break
    if done: continue
    for d in [pr + mm(0.6) + mm(0.1) * i for i in range(35)]:
        for k in range(32):
            a = k * math.pi / 16; vx, vy = px + d * math.cos(a), py + d * math.sin(a)
            if ok_point(vx, vy, mm(0.3)) and ok_seg(px, py, vx, vy, mm(0.15), pr):
                adds.append(('v', px, py, vx, vy)); done = True; break
        if done: break
    if not done: print('could not rescue', key)
killed = [(t.GetNetname(), round(t.GetLength() / 1e6, 2)) for t in kill]
for t in kill: b.Remove(t)
gnd = b.FindNet('GND')
for kind, x0, y0, x1, y1 in adds:
    tr = pcbnew.PCB_TRACK(b); tr.SetStart(V(int(x0), int(y0))); tr.SetEnd(V(int(x1), int(y1)))
    tr.SetWidth(mm(0.3)); tr.SetLayer(pcbnew.F_Cu); tr.SetNet(gnd); b.Add(tr)
    if kind == 'v':
        v = pcbnew.PCB_VIA(b); v.SetPosition(V(int(x1), int(y1))); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3))
        v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(gnd); b.Add(v)
print({'dangling_removed': len(kill), 'killed': killed, 'rescues': [(a[0]) for a in adds], 'pads': list(padinfo)})
pcbnew.SaveBoard(PCB, b)
