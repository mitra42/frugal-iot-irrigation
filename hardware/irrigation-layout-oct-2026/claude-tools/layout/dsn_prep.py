"""Edit out/board.dsn -> out/board_r.dsn: GND keeps one pin (nothing to route, its pour-side copper stays as
obstacles) and all existing GND wiring/vias become (type fix) so the router keeps them."""
import re
s = open('out/board.dsn').read()
i = s.index('(net GND'); j = s.index('(pins', i); k = s.index(')', j)
pins = s[j + 5:k].split()
s = s[:j] + '(pins ' + pins[0] + s[k:]
s = re.sub(r'(\(net GND\)\s*)\(type route\)', r'\1(type fix)', s)
open('out/board_r.dsn', 'w').write(s)
print('GND pins', len(pins), '-> 1; fixed GND items', s.count('(net GND)(type fix)') + s.count('(net GND) (type fix)'))
