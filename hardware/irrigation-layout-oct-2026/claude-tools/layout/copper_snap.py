"""KiCad python. `copper_snap.py save`: write every track and via on the board to out/preroute.json (run after
prep_route.py, before routing). `copper_snap.py restore`: add back any of them the board no longer has (run after
import_ses.py). Why: Freerouting keeps (type fix) wires in its .ses but drops fixed vias, and KiCad's SES import
replaces all copper - so without this the GND fan-out vias, the FET source vias and the +12V feed vias vanish."""
import json, sys, pcbnew
SNAP = sys.argv[2] if len(sys.argv) > 2 else 'out/preroute.json'   # optional: another snapshot file
PCB = '../../esp32_io_board/esp32_io_board.kicad_pcb'
b = pcbnew.LoadBoard(PCB); mm = pcbnew.FromMM; V = pcbnew.VECTOR2I
def key(it):
    if it['via']: return ('v', it['x'], it['y'], it['net'])
    a, c = (it['x0'], it['y0']), (it['x1'], it['y1'])
    return ('t', it['layer'], it['net'], it['w'], min(a, c), max(a, c))
cur = []
for t in b.GetTracks():
    if t.GetClass() == 'PCB_VIA':
        p = t.GetPosition(); cur.append(dict(via=True, x=p.x, y=p.y, net=t.GetNetname(), w=t.GetWidth(pcbnew.F_Cu), drill=t.GetDrill()))
    else:
        s, e = t.GetStart(), t.GetEnd()
        cur.append(dict(via=False, x0=s.x, y0=s.y, x1=e.x, y1=e.y, layer=t.GetLayer(), net=t.GetNetname(), w=t.GetWidth()))
if sys.argv[1] == 'save':
    json.dump(cur, open(SNAP, 'w')); print('saved', len(cur))
else:
    have = {key(c) for c in cur}
    missing = [c for c in json.load(open(SNAP)) if key(c) not in have]
    nets = {c['net']: b.FindNet(c['net']) for c in missing}
    for c in missing:
        if c['via']:
            v = pcbnew.PCB_VIA(b); v.SetPosition(V(c['x'], c['y'])); v.SetWidth(c['w']); v.SetDrill(c['drill'])
            v.SetLayerPair(pcbnew.F_Cu, pcbnew.B_Cu); v.SetNet(nets[c['net']]); b.Add(v)
        else:
            t = pcbnew.PCB_TRACK(b); t.SetStart(V(c['x0'], c['y0'])); t.SetEnd(V(c['x1'], c['y1'])); t.SetWidth(c['w'])
            t.SetLayer(c['layer']); t.SetNet(nets[c['net']]); b.Add(t)
    print('restored', sum(c['via'] for c in missing), 'vias', sum(not c['via'] for c in missing), 'tracks')
    pcbnew.SaveBoard(PCB, b)
