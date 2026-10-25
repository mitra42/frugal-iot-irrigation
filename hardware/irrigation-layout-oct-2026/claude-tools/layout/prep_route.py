"""KiCad python, one job: GND fan-out vias for SMD GND pads + thermal vias in exposed pads, then export DSN.
Reads/writes ../esp32_io_board/esp32_io_board.kicad_pcb; writes out/board.dsn and out/prep.json."""
import json, math, pcbnew
PCB = '../../esp32_io_board/esp32_io_board.kicad_pcb'
b = pcbnew.LoadBoard(PCB)
mm = pcbnew.FromMM; tomm = lambda v: v / 1e6
gnd = b.FindNet('GND')
# ---- collect everything first (SWIG landmine: no reads after mutation) ----
edge = b.GetBoardEdgesBoundingBox(); EX0, EY0, EX1, EY1 = tomm(edge.GetX()), tomm(edge.GetY()), tomm(edge.GetRight()), tomm(edge.GetBottom())
obst = []        # (x0,y0,x1,y1) of non-GND copper pads (both layers matter for vias)
gpads = []       # SMD GND pads: (ref, num, x, y, w, h, fx, fy, nGNDinFP)
ep = []          # exposed pads to fill with vias: (ref, num, x, y, w, h)
for f in b.GetFootprints():
    fc = f.GetPosition(); fx, fy = tomm(fc.x), tomm(fc.y)
    ref = f.GetReference()
    gl = [p for p in f.Pads() if p.GetNetname() == 'GND' and p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD]
    for p in f.Pads():
        bb = p.GetBoundingBox(); box = (tomm(bb.GetX()), tomm(bb.GetY()), tomm(bb.GetRight()), tomm(bb.GetBottom()))
        if p.GetNetname() != 'GND':
            obst.append(box)
        elif p.GetAttribute() == pcbnew.PAD_ATTRIB_SMD:
            pc = p.GetPosition()
            w, h = box[2] - box[0], box[3] - box[1]
            if (ref == 'U6' and p.GetNumber() == '49') or (ref == 'U3' and p.GetNumber() == '9'):
                ep.append((ref, p.GetNumber(), tomm(pc.x), tomm(pc.y), w, h))
            else:
                gpads.append((ref, p.GetNumber(), tomm(pc.x), tomm(pc.y), w, h, fx, fy, len(gl)))
VIA_D, VIA_DR, CLR, TRK = 0.6, 0.3, 0.2, 0.4
vias = []; tracks = []; skipped = []
def near_box(x, y, box, m):
    return box[0] - m <= x <= box[2] + m and box[1] - m <= y <= box[3] + m
def ok_via(x, y):
    if not (EX0 + 0.8 <= x <= EX1 - 0.8 and EY0 + 0.8 <= y <= EY1 - 0.8): return False
    if any(near_box(x, y, o, VIA_D / 2 + CLR) for o in obst): return False
    return all(math.hypot(x - vx, y - vy) >= VIA_D + 0.25 for vx, vy in vias)
def ok_seg(x0, y0, x1, y1):
    n = max(2, int(math.hypot(x1 - x0, y1 - y0) / 0.05))
    for i in range(n + 1):
        t = i / n; x, y = x0 + (x1 - x0) * t, y0 + (y1 - y0) * t
        if any(near_box(x, y, o, TRK / 2 + CLR) for o in obst): return False
    return True
# thin out big GND groups (module perimeter): the top pour ties neighbouring pads together
done_per_fp = {}
for ref, num, x, y, w, h, fx, fy, ng in sorted(gpads, key=lambda g: (g[0], int(g[1]) if g[1].isdigit() else 0)):
    k = done_per_fp.get(ref, 0); done_per_fp[ref] = k + 1
    if ng > 4 and k % 3: continue
    dx, dy = x - fx, y - fy; L = math.hypot(dx, dy)
    base = math.atan2(dy, dx) if L > 1e-3 else -math.pi / 2
    start = max(w, h) / 2 + 0.5
    found = None
    for d in [start + 0.2 * i for i in range(10)]:
        for da in (0, 30, -30, 60, -60, 90, -90, 135, -135, 180):
            a = base + math.radians(da); vx, vy = x + d * math.cos(a), y + d * math.sin(a)
            if ok_via(vx, vy) and ok_seg(x + (w / 2) * math.cos(a) * 0.5, y + (h / 2) * math.sin(a) * 0.5, vx, vy):
                found = (vx, vy); break
        if found: break
    if found: vias.append(found); tracks.append((x, y, *found))
    else: skipped.append(f'{ref}.{num}')
# thermal vias inside exposed pads
epv = []
for ref, num, x, y, w, h in ep:
    if ref == 'U3':   # SOIC-8 EP 2.41 x 3.3: 2 x 3 grid
        pts = [(x + sx, y + sy) for sx in (-0.6, 0.6) for sy in (-1.0, 0.0, 1.0)]
    else:             # module EP square: one via at its centre
        pts = [(x, y)]
    epv += pts
# module EP squares: 9 pads all named 49 -> one via each in the corner + centre squares
# ---- mutate ----
def add_via(x, y, dia=VIA_D, drill=VIA_DR):
    v = pcbnew.PCB_VIA(b); v.SetPosition(pcbnew.VECTOR2I(mm(x), mm(y))); v.SetWidth(mm(dia)); v.SetDrill(mm(drill))
    v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(gnd); b.Add(v)
for x, y in vias: add_via(x, y)
for x, y in epv: add_via(x, y)
for x0, y0, x1, y1 in tracks:
    t = pcbnew.PCB_TRACK(b); t.SetStart(pcbnew.VECTOR2I(mm(x0), mm(y0))); t.SetEnd(pcbnew.VECTOR2I(mm(x1), mm(y1)))
    t.SetWidth(mm(TRK)); t.SetLayer(pcbnew.F_Cu); t.SetNet(gnd); b.Add(t)
json.dump(dict(fanout=len(vias), ep_vias=len(epv), skipped=skipped), open('out/prep.json', 'w'), indent=1)
pcbnew.SaveBoard(PCB, b)
ok = pcbnew.ExportSpecctraDSN(b, 'out/board.dsn')
print('fanout vias', len(vias), 'EP vias', len(epv), 'skipped', skipped, 'dsn', ok)
