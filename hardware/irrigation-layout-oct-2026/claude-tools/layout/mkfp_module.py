"""Make irrigation.pretty/ESP32-C3-C6-MINI-1U.kicad_mod from KiCad's RF_Module:ESP32-C6-MINI-1.
Keeps all pads (1-53, EP = 49) - land pattern identical for C3-MINI-1U (datasheet v2.2 fig 11-2) and
C6-MINI-1U (v1.5 fig 11-2). Replaces courtyard/fab/silk with the 1U body (13.2 x 12.5, bottom edge 5.6 below
pad centre, i.e. y -6.9..+5.6) and drops the PCB-antenna keep-out zone (the -1U uses a U.FL)."""
import re, uuid
src = open('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/RF_Module.pretty/ESP32-C6-MINI-1.kicad_mod').read()
def top_nodes(s):
    # split the footprint body into top-level child nodes
    i = s.index('(', 1); depth = 0; start = None; out = []
    for j in range(i, len(s)):
        c = s[j]
        if c == '(':
            if depth == 0: start = j
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0: out.append(s[start:j + 1])
            if depth < 0: break
    return out
head = src[:src.index('(', 1)]
nodes = top_nodes(src)
keep = []
for n in nodes:
    tag = n[1:].split(None, 1)[0]
    if tag == 'zone': continue
    if tag in ('fp_line', 'fp_poly', 'fp_rect', 'fp_circle', 'fp_arc') and re.search(r'\(layer "(F\.CrtYd|F\.Fab|F\.SilkS)"\)', n):
        continue
    if tag == 'property' and n.startswith('(property "Description"'):
        n = re.sub(r'"Description" "[^"]*"', '"Description" "ESP32-C3-MINI-1U or ESP32-C6-MINI-1U (U.FL antenna), shared land pattern"', n)
    keep.append(n)
def rect(x0, y0, x1, y1, layer, w):
    u = lambda: str(uuid.uuid4())
    return (f'(fp_rect (start {x0} {y0}) (end {x1} {y1}) (stroke (width {w}) (type solid)) (fill no) '
            f'(layer "{layer}") (uuid "{u()}"))')
def line(x0, y0, x1, y1, layer, w):
    return (f'(fp_line (start {x0} {y0}) (end {x1} {y1}) (stroke (width {w}) (type solid)) '
            f'(layer "{layer}") (uuid "{uuid.uuid4()}"))')
g = [rect(-6.6, -6.9, 6.6, 5.6, 'F.Fab', 0.1),
     rect(-6.85, -7.15, 6.85, 5.85, 'F.CrtYd', 0.05),
     # silk: body outline only beyond the pad rows (top edge + top of sides), pin-1 dot left of pad 1
     line(-6.75, -7.05, 6.75, -7.05, 'F.SilkS', 0.12),
     line(-6.75, -7.05, -6.75, -5.4, 'F.SilkS', 0.12), line(6.75, -7.05, 6.75, -5.4, 'F.SilkS', 0.12),
     f'(fp_circle (center -7.0 -4.9) (end -6.75 -4.9) (stroke (width 0.12) (type solid)) (fill yes) (layer "F.SilkS") (uuid "{uuid.uuid4()}"))',
     f'(fp_text user "U.FL" (at 0 -5.9 0) (layer "F.Fab") (uuid "{uuid.uuid4()}") (effects (font (size 0.8 0.8) (thickness 0.12))))']
head = re.sub(r'\(footprint "[^"]+"', '(footprint "ESP32-C3-C6-MINI-1U"', src[:src.index('\n') + 1])
body = '\n\t'.join(keep + g)
out = head + '\t' + body + '\n)\n'
open('../../esp32_io_board/irrigation.pretty/ESP32-C3-C6-MINI-1U.kicad_mod', 'w').write(out)
print('pads:', len(re.findall(r'\(pad "', out)), 'zones:', out.count('(zone'), 'bytes', len(out))
