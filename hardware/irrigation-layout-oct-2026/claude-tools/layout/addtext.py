"""KiCad python: place a board title on F.SilkS at the largest size (2.0 -> 1.0 mm) that fits clear of pads,
silk graphics, other silk text and the edge. Prints where it went."""
import pcbnew, math, sys
TEXT = sys.argv[1] if len(sys.argv) > 1 else 'Frugal-IoT Irrigation V0.1'
PCB = '../../esp32_io_board/esp32_io_board.kicad_pcb'
b = pcbnew.LoadBoard(PCB); mm = pcbnew.FromMM; V = pcbnew.VECTOR2I
e = b.GetBoardEdgesBoundingBox(); EX0, EY0, EX1, EY1 = e.GetX() + mm(1), e.GetY() + mm(1), e.GetRight() - mm(1), e.GetBottom() - mm(1)
M = mm(0.3)
boxes = []
for f in b.GetFootprints():
    for p in f.Pads():
        if p.IsOnLayer(pcbnew.F_Cu): bb = p.GetBoundingBox(); boxes.append((bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom()))
    for it in list(f.GraphicalItems()) + [f.Reference()]:
        if it.GetLayer() == pcbnew.F_SilkS and (it.GetClass() != 'PCB_FIELD' or it.IsVisible()):
            bb = it.GetBoundingBox(); boxes.append((bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom()))
    if f.GetReference().startswith('H'):   # mounting holes: keep text off the screw head area
        c = f.GetPosition(); boxes.append((c.x - mm(3.5), c.y - mm(3.5), c.x + mm(3.5), c.y + mm(3.5)))
t = pcbnew.PCB_TEXT(b); t.SetText(TEXT); t.SetLayer(pcbnew.F_SilkS)
best = None
for h in (2.0, 1.8, 1.6, 1.5, 1.4, 1.2, 1.0):
    t.SetTextSize(V(mm(h), mm(h))); t.SetTextThickness(mm(max(0.15, h * 0.15)))
    for ang in (0, 90):
        t.SetTextAngleDegrees(ang)
        y = EY0
        while y < EY1 and not best:
            x = EX0
            while x < EX1:
                t.SetPosition(V(int(x), int(y))); bb = t.GetBoundingBox()
                r = (bb.GetX(), bb.GetY(), bb.GetRight(), bb.GetBottom())
                if r[0] >= EX0 and r[1] >= EY0 and r[2] <= EX1 and r[3] <= EY1 and \
                   all(r[2] + M <= q[0] or q[2] + M <= r[0] or r[3] + M <= q[1] or q[3] + M <= r[1] for q in boxes):
                    best = (h, ang, x, y); break
                x += mm(0.5)
            y += mm(0.5)
        if best: break
    if best: break
if not best: sys.exit('no space found')
h, ang, x, y = best
t.SetTextSize(V(mm(h), mm(h))); t.SetTextThickness(mm(max(0.15, h * 0.15))); t.SetTextAngleDegrees(ang); t.SetPosition(V(int(x), int(y)))
b.Add(t); pcbnew.SaveBoard(PCB, b)
print(f'placed "{TEXT}" {h} mm, angle {ang}, centre ({x/1e6-50:.1f}, {y/1e6-50:.1f}) mm')
