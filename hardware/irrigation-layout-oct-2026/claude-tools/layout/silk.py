"""KiCad python: reposition reference designators (0.8 mm / 0.12 mm) clear of pads, silk graphics, the board
edge and each other; largest footprints first. Refs that find no spot within 7 mm are moved to F.Fab (hidden
from silkscreen) and listed."""
import pcbnew, math, json
PCB = '../../esp32_io_board/esp32_io_board.kicad_pcb'
b = pcbnew.LoadBoard(PCB); mm = pcbnew.FromMM; V = pcbnew.VECTOR2I
e = b.GetBoardEdgesBoundingBox(); EX0, EY0, EX1, EY1 = e.GetX() + mm(0.3), e.GetY() + mm(0.3), e.GetRight() - mm(0.3), e.GetBottom() - mm(0.3)
M = mm(0.15)
padbox = []; silkpts = []
fps = list(b.GetFootprints())
for f in fps:
    for p in f.Pads():
        if p.IsOnLayer(pcbnew.F_Cu):
            bb = p.GetBoundingBox(); padbox.append((bb.GetX() - M, bb.GetY() - M, bb.GetRight() + M, bb.GetBottom() + M))
    for g in f.GraphicalItems():
        if g.GetLayer() != pcbnew.F_SilkS or g.GetClass() in ('PCB_FIELD', 'PCB_TEXT'): continue
        bb = g.GetBoundingBox()
        if g.GetClass() == 'PCB_SHAPE' and g.GetShape() == pcbnew.SHAPE_T_SEGMENT:
            s, t = g.GetStart(), g.GetEnd(); n = max(1, int(math.hypot(t.x - s.x, t.y - s.y) / mm(0.2)))
            silkpts += [(s.x + (t.x - s.x) * i / n, s.y + (t.y - s.y) * i / n) for i in range(n + 1)]
        else:
            # arcs/circles/polys/rects: sample bbox perimeter + centre (coarse)
            x0, y0, x1, y1 = bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom()
            n = max(1, int(max(x1 - x0, y1 - y0) / mm(0.2)))
            for i in range(n + 1):
                f_ = i / n
                silkpts += [(x0 + (x1 - x0) * f_, y0), (x0 + (x1 - x0) * f_, y1), (x0, y0 + (y1 - y0) * f_), (x1, y0 + (y1 - y0) * f_)]
placed = []
def ok(bb):
    x0, y0, x1, y1 = bb
    if x0 < EX0 or y0 < EY0 or x1 > EX1 or y1 > EY1: return False
    for a in padbox:
        if x0 < a[2] and a[0] < x1 and y0 < a[3] and a[1] < y1: return False
    for a in placed:
        if x0 < a[2] + M and a[0] < x1 + M and y0 < a[3] + M and a[1] < y1 + M: return False
    for px, py in silkpts:
        if x0 - M <= px <= x1 + M and y0 - M <= py <= y1 + M: return False
    return True
def area(f):
    bb = f.GetBoundingBox(False, False); return bb.GetWidth() * bb.GetHeight()
moved = 0; fab = []
for f in sorted(fps, key=area, reverse=True):
    r = f.Reference()
    if not r.IsVisible() or r.GetLayer() != pcbnew.F_SilkS: continue
    r.SetTextSize(V(mm(0.8), mm(0.8))); r.SetTextThickness(mm(0.12)); r.SetKeepUpright(True)
    c = f.GetPosition(); fb = f.GetBoundingBox(False, False)
    rad0 = 0; found = None
    for ring in range(0, 70):
        rad = ring * mm(0.1)
        n = max(1, int(2 * math.pi * rad / mm(0.4))) if rad else 1
        for k in range(n):
            a = 2 * math.pi * k / n
            for ang in (0, 90):
                x, y = c.x + rad * math.cos(a), c.y + rad * math.sin(a)
                r.SetTextAngleDegrees(ang); r.SetPosition(V(int(x), int(y)))
                bb = r.GetBoundingBox()
                box = (bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom())
                if ok(box): found = box; break
            if found: break
        if found: break
    if found: placed.append(found); moved += 1
    else:
        r.SetLayer(pcbnew.F_Fab); r.SetPosition(c); fab.append(f.GetReference())
json.dump(dict(placed=moved, to_fab=fab), open('out/silk.json', 'w'))
print('placed', moved, 'moved to F.Fab', fab)
pcbnew.SaveBoard(PCB, b)
