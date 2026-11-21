"""KiCad python, one job: draw the high-current copper by rule, before the autorouter (D82). Run after build_pcb.py.
Freerouting is given these as fixed wiring (dsn_prep.py marks every existing wire and via fixed).
Why by hand: the 2-3 A paths want width the autorouter cannot give them near fine-pitch pads, and they want to be
short and identical in every channel, which is exactly what the column placement in place.py was arranged for.

  input   J2.1 -> F1 -> D1 anode, 2 mm on F.Cu
  feed    D1 cathode -> three vias between channels 1 and 2 -> 2 mm on B.Cu down to the bus; C1 on the vias
  bus     2 mm on B.Cu, 3 mm above the terminal pins, with a 2 mm stub down to every pin 1 (+12V)
  channel VALVE trunk 1 mm straight down: FET drain -> LED cathode -> SS34 anode -> terminal pin 2
          +12V 1 mm: pin 1 up to the SS34 cathode, then 0.4 mm on to the 4.7k
          LED_V 0.3 mm (4.7k -> LED); gate 0.3 mm (100k -> FET gate); 100k GND end -> FET source 0.6 mm
          FET source -> two 0.8/0.4 mm GND vias 1 mm to its left, so the valve current reaches both pours
The GND return to J2.2 is the two pours; pour.py gives J2.2 a solid (not thermal-relief) connection.
From the irrigation board's valve_route.py; only the references differ (channel i: J(4+i), Q(1+i), SS34 D(3+2i),
LED D(4+2i), 100k R(3+2i), 4.7k R(4+2i); input D1, bulk C1), and nets are read off the pads, not named."""
import json, pcbnew
PCB = '../../daughter/irrigation_daughter.kicad_pcb'
b = pcbnew.LoadBoard(PCB); mm = pcbnew.FromMM; V = pcbnew.VECTOR2I
OX, OY = 50.0, 50.0
pl = json.load(open('placement.json'))
# ---- collect pad positions first (SWIG: no reads after mutation) ----
pad = {}
for f in b.GetFootprints():
    for p in f.Pads():
        q = p.GetPosition(); pad.setdefault((f.GetReference(), p.GetNumber()), (q.x / 1e6 - OX, q.y / 1e6 - OY))
padnet = {}
for f in b.GetFootprints():
    for p in f.Pads(): padnet.setdefault((f.GetReference(), p.GetNumber()), p.GetNetname())
net = {n: b.FindNet(n) for n in set(padnet.values()) if n}
T = []; VIAS = []
def trk(layer, w, n, *pts):
    for (x0, y0), (x1, y1) in zip(pts, pts[1:]): T.append((layer, w, n, x0, y0, x1, y1))
F, B = pcbnew.F_Cu, pcbnew.B_Cu
# input and feed
j2, f1a, f1b = pad[('J2', '1')], pad[('F1', '1')], pad[('F1', '2')]
d2a, d2k = pad[('D1', '2')], pad[('D1', '1')]
trk(F, 2.0, padnet[('J2', '1')], j2, (f1a[0], j2[1]), f1a)
trk(F, 2.0, padnet[('F1', '2')], f1b, (d2a[0], f1b[1]), d2a)
feed = [tuple(v) for v in pl['feed']]
mid = feed[1]
trk(F, 2.0, '+12V', d2k, (d2k[0], feed[0][1]), feed[-1])         # down from the cathode, then along the vias
c22 = pad[('C1', '1')]
trk(F, 1.0, '+12V', c22, (feed[0][0], c22[1]) if abs(c22[1] - feed[0][1]) < 0.05 else (c22[0], feed[0][1]), feed[0])
for v in feed: VIAS.append((v, 0.8, 0.4, '+12V'))
# bus
p1 = [pad[(f'J{4 + i}', '1')] for i in range(8)]
ybus = p1[0][1] - 3.0
trk(B, 2.0, '+12V', mid, (mid[0], ybus))
trk(B, 2.0, '+12V', (p1[0][0], ybus), (p1[-1][0], ybus))
for x, y in p1: trk(B, 2.0, '+12V', (x, ybus), (x, y))
# channels
for i in range(8):
    J, D, R4, L, Q, R1 = f'J{4 + i}', f'D{3 + 2 * i}', f'R{4 + 2 * i}', f'D{4 + 2 * i}', f'Q{1 + i}', f'R{3 + 2 * i}'
    vn, ln, gn = padnet[(Q, '3')], padnet[(R4, '2')], padnet[(Q, '1')]
    qd, qs, qg = pad[(Q, '3')], pad[(Q, '2')], pad[(Q, '1')]
    pin1, pin2 = pad[(J, '1')], pad[(J, '2')]
    xt = qd[0]
    trk(F, 1.0, vn, qd, (xt, pin2[1]))                                # through LED K and SS34 A onto pin 2's pad
    dk = pad[(D, '1')]; r4a, r4b = pad[(R4, '1')], pad[(R4, '2')]
    trk(F, 1.0, '+12V', (pin1[0] + 0.3, pin1[1]), (pin1[0] + 0.3, dk[1]))
    trk(F, 0.4, '+12V', (r4a[0], dk[1]), r4a)
    trk(F, 0.3, ln, r4b, pad[(L, '2')])
    trk(F, 0.3, gn, pad[(R1, '1')], (pad[(R1, '1')][0], qg[1]), qg)
    r1g = pad[(R1, '2')]
    trk(F, 0.6, 'GND', r1g, (r1g[0], qs[1]))
    gv = [(qs[0] - 1.65, qs[1]), (qs[0] - 1.65, qs[1] + 1.3)]
    trk(F, 1.0, 'GND', qs, gv[0], gv[1])
    for v in gv: VIAS.append((v, 0.8, 0.4, 'GND'))
# ---- mutate ----
for layer, w, n, x0, y0, x1, y1 in T:
    if abs(x0 - x1) < 1e-6 and abs(y0 - y1) < 1e-6: continue
    t = pcbnew.PCB_TRACK(b); t.SetStart(V(mm(OX + x0), mm(OY + y0))); t.SetEnd(V(mm(OX + x1), mm(OY + y1)))
    t.SetWidth(mm(w)); t.SetLayer(layer); t.SetNet(net[n]); b.Add(t)
for (x, y), d, dr, n in VIAS:
    v = pcbnew.PCB_VIA(b); v.SetPosition(V(mm(OX + x), mm(OY + y))); v.SetWidth(mm(d)); v.SetDrill(mm(dr))
    v.SetLayerPair(F, B); v.SetNet(net[n]); b.Add(v)
print('tracks', len(T), 'vias', len(VIAS))
pcbnew.SaveBoard(PCB, b)
