"""Run with KiCad's python on the Mac. Reads ../schematic/out/netlist.xml, loads each footprint,
writes fp.json: {ref: {fp, value, dnp, bbox:[x0,y0,x1,y1] courtyard rel. to origin (mm, rot 0), pads:{num:[x,y]}}}"""
import json, sys, xml.etree.ElementTree as ET, pcbnew
LIB = '/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints'
nl = ET.parse('../schematic/out/netlist.xml').getroot()
out = {}
cache = {}
for c in nl.iter('comp'):
    ref = c.get('ref'); fpn = c.findtext('footprint')
    dnp = any(p.get('name') == 'dnp' for p in c.iter('property'))
    if fpn not in cache:
        lib, name = fpn.split(':')
        d = '../../esp32_io_board/irrigation.pretty' if lib == 'irrigation' else f'{LIB}/{lib}.pretty'
        fp = pcbnew.FootprintLoad(d, name)
        cy = fp.GetCourtyard(pcbnew.F_CrtYd)
        if cy.OutlineCount():
            b = cy.BBox(); bb = [b.GetX(), b.GetY(), b.GetRight(), b.GetBottom()]
        else:
            b = fp.GetBoundingBox(False); bb = [b.GetX(), b.GetY(), b.GetRight(), b.GetBottom()]
        pads = {}
        for p in fp.Pads():
            pos = p.GetPosition(); pads.setdefault(p.GetNumber(), [pos.x / 1e6, pos.y / 1e6])
        cache[fpn] = dict(bbox=[v / 1e6 for v in bb], pads=pads,
                          tht=any(p.GetAttribute() == pcbnew.PAD_ATTRIB_PTH for p in fp.Pads()))
    out[ref] = dict(fp=fpn, value=c.findtext('value'), dnp=dnp, **cache[fpn])
json.dump(out, open('fp.json', 'w'), indent=0)
print(len(out), 'parts')
