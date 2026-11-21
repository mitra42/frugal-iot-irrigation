"""KiCad python, one job: add a GND via at (x, y) with a 0.4 mm track to the pad centre (px, py), board mm.
For a GND pad left in a pocket of top pour with no way to the rest of GND - the router does not route GND
(dsn_prep.py). Used once after patch_power.py, for U4 (XB5353A) pad 4: gnd_via.py 20.66 12.65 21.263 12.65.
Find a clear spot first with out/gndvia_search.py-style search; DRC is the check."""
import sys, pcbnew
x, y, px, py = map(float, sys.argv[1:5]); O = 50.0
b = pcbnew.LoadBoard('../../esp32_io_board/esp32_io_board.kicad_pcb'); mm = pcbnew.FromMM
P = lambda u, v: pcbnew.VECTOR2I(mm(O + u), mm(O + v)); g = b.FindNet('GND')
v = pcbnew.PCB_VIA(b); v.SetPosition(P(x, y)); v.SetWidth(mm(0.6)); v.SetDrill(mm(0.3))
v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(g); b.Add(v)
t = pcbnew.PCB_TRACK(b); t.SetStart(P(px, py)); t.SetEnd(P(x, y)); t.SetWidth(mm(0.4)); t.SetLayer(pcbnew.F_Cu); t.SetNet(g); b.Add(t)
pcbnew.SaveBoard('../../esp32_io_board/esp32_io_board.kicad_pcb', b); print('via', x, y)
