"""Run with KiCad's python on the Mac (one job per process). Builds ../../esp32_io_board/esp32_io_board.kicad_pcb
from ../schematic/out/netlist.xml + placement.json: outline, 4x M3 holes, footprints linked to symbols, pad nets.
Writes out/padcheck.json (pad positions read back from pcbnew) BEFORE saving."""
import json, xml.etree.ElementTree as ET, pcbnew
LIB = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
PRJ = '../../esp32_io_board'
OX, OY = 50.0, 50.0                          # board origin on the page
mm = pcbnew.FromMM
pl = json.load(open('placement.json')); W, H = pl['W'], pl['H']
nl = ET.parse('../schematic/out/netlist.xml').getroot()
padnet = {}
for n in nl.iter('net'):
    for node in n.iter('node'): padnet[(node.get('ref'), node.get('pin'))] = n.get('name')
comps = []
for c in nl.iter('comp'):
    comps.append(dict(ref=c.get('ref'), value=c.findtext('value'), fp=c.findtext('footprint'),
                      ts=c.findtext('tstamps'), dnp=any(p.get('name') == 'dnp' for p in c.iter('property')),
                      fields={f.get('name'): f.text or '' for f in c.iter('field')},
                      desc=(c.find('libsource').get('description') if c.find('libsource') is not None else '')))
b = pcbnew.BOARD()
b.SetCopperLayerCount(2)
def V(x, y): return pcbnew.VECTOR2I(mm(OX + x), mm(OY + y))
r = pcbnew.PCB_SHAPE(b); r.SetShape(pcbnew.SHAPE_T_RECT); r.SetStart(V(0, 0)); r.SetEnd(V(W, H))
r.SetLayer(pcbnew.Edge_Cuts); r.SetWidth(mm(0.1)); b.Add(r)
def load(fpname):
    lib, name = fpname.split(':')
    d = f'{PRJ}/irrigation.pretty' if lib == 'irrigation' else f'{LIB}/{lib}.pretty'
    fp = pcbnew.FootprintLoad(d, name); fp.SetFPID(pcbnew.LIB_ID(lib, name)); return fp
placed = []
for c in comps:
    fp = load(c['fp'])
    fp.SetReference(c['ref']); fp.SetValue(c['value'])
    fp.SetPath(pcbnew.KIID_PATH('/' + c['ts']))
    x, y, rot = pl['place'][c['ref']]
    fp.SetPosition(V(x, y)); fp.SetOrientationDegrees(rot)
    if c['dnp'] and hasattr(fp, 'SetDNP'): fp.SetDNP(True)
    b.Add(fp); placed.append((fp, c))
for i, (hx, hy) in enumerate(pl['holes'].values()):
    fp = load('MountingHole:MountingHole_3.2mm_M3'); fp.SetReference(f'H{i + 1}'); fp.SetValue('M3')
    fp.SetPosition(V(hx, hy))
    fp.SetAttributes(fp.GetAttributes() | pcbnew.FP_BOARD_ONLY | pcbnew.FP_EXCLUDE_FROM_BOM | pcbnew.FP_EXCLUDE_FROM_POS_FILES)
    b.Add(fp)
nets = {}
for (ref, pin), name in padnet.items():
    if name not in nets:
        # KiCad escapes '/' inside generated unconnected-(...) names as {slash}
        kname = 'unconnected-(' + name[13:].replace('/', '{slash}') if name.startswith('unconnected-(') else name
        ni = pcbnew.NETINFO_ITEM(b, kname); b.Add(ni); nets[name] = ni
check = {}
for fp, c in placed:                         # nets AFTER board.Add(fp)
    for p in fp.Pads():
        n = padnet.get((c['ref'], p.GetNumber()))
        if n and n.startswith('unconnected-('): n = n  # escaped when nets are created
        if n: p.SetNet(nets[n])
        pos = p.GetPosition(); check.setdefault(c['ref'], {}).setdefault(p.GetNumber(), None)
        if check[c['ref']][p.GetNumber()] is None: check[c['ref']][p.GetNumber()] = [round(pos.x / 1e6 - OX, 3), round(pos.y / 1e6 - OY, 3)]
    if c['ref'].startswith('JP'):
        fp.SetAttributes(fp.GetAttributes() & ~pcbnew.FP_EXCLUDE_FROM_BOM)   # match the symbol (in BOM)
    for k, v in c['fields'].items():
        if k not in ('Footprint', 'Datasheet', 'Value', 'Reference'):
            try:
                fp.SetField(k, v)            # KiCad 8+: creates the field if missing
                for fld in fp.GetFields():
                    if fld.GetName() == k: fld.SetVisible(False); fld.SetLayer(pcbnew.F_Fab)
            except Exception as e:
                print('field', c['ref'], k, e)
json.dump(check, open('out/padcheck.json', 'w'))
out = f'{PRJ}/esp32_io_board.kicad_pcb'
pcbnew.SaveBoard(out, b)
print('saved', out, len(placed), 'footprints')
