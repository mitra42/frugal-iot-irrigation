"""Edit out/board.dsn -> out/board_r.dsn: GND keeps one pin (nothing to route, its pour-side copper stays as
obstacles) and ALL existing wiring and vias become (type fix) so the router keeps them: the GND fan-out from
prep_route.py and the high-current copper from valve_route.py (D82)."""
import re
s = open('out/board.dsn').read()
i = s.index('(net GND'); j = s.index('(pins', i); k = s.index(')', j)
pins = s[j + 5:k].split()
s = s[:j] + '(pins ' + pins[0] + s[k:]
s = re.sub(r'\(type route\)', '(type fix)', s)
open('out/board_r.dsn', 'w').write(s)
print('GND pins', len(pins), '-> 1; fixed items', s.count('(type fix)'))
