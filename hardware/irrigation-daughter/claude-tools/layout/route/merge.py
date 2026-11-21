"""Merge a Freerouting .ses back into a .dsn as (type route) wiring, so the next run continues from it.
Usage: merge.py in.dsn in.ses out.dsn   (SES coords are 0.1 um, DSN coords um)
Copied from frugal-iot-hw-lora; changed to skip wires that are already in the DSN as (type fix) - Freerouting
writes the fixed wires back into its .ses, and merging them again would give every fixed wire a routable twin."""
import re, sys
dsn, ses, out = sys.argv[1:4]
d = open(dsn).read(); s = open(ses).read()
body = s[s.find('(network_out'):]
items = []
for block in re.split(r"\n      \(net ", body)[1:]:
    name = block.split("\n", 1)[0].strip()
    q = name if name.startswith('"') else (f'"{name}"' if re.search(r'[\s()]', name) else name)
    for m in re.finditer(r"\(wire\s*\(path (\S+) (\d+)\n((?:\s+-?\d+ -?\d+\n)+)", block):
        pts = ' '.join(f'{int(a) / 10:g} {int(b) / 10:g}' for a, b in (l.split() for l in m.group(3).strip().split('\n')))
        items.append(f'    (wire (path {m.group(1)} {int(m.group(2)) / 10:g}  {pts})(net {q})(type route))')
    for m in re.finditer(r'\(via "([^"]+)" (-?\d+) (-?\d+)', block):
        items.append(f'    (via "{m.group(1)}" {int(m.group(2)) / 10:g} {int(m.group(3)) / 10:g} (net {q})(type route))')
fixed = {re.sub(r'\s+', ' ', m.group(1)).strip() for m in re.finditer(r'\(wire \(path ([^)]*)\)', d)}
def path_of(it): return re.sub(r'\s+', ' ', re.search(r'\(path ([^)]*)\)', it).group(1)).strip() if '(wire' in it else None
items = [it for it in items if path_of(it) is None or path_of(it) not in fixed]
i = d.index('(wiring'); j = d.index('\n', i)
d = d[:j + 1] + '\n'.join(items) + '\n' + d[j + 1:]
open(out, 'w').write(d)
print('merged', len(items), 'items')
