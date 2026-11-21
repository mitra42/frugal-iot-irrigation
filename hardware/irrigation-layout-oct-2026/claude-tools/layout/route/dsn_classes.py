"""Rewrite net classes in a DSN (mirror of layout/netclasses.py): split PowerFine off Power, narrow USB."""
import re, sys
src, dst = sys.argv[1], sys.argv[2]
s = open(src).read()
# Sub-1 A rails at 0.4 mm. +5V, VBAT and the cell-protection path joined them on the 62 mm board (D83): at 0.6 mm
# the router could not get between the TP4056 / FS8205A / AP2112 pins in the dense charger corner.
FINE = ['+3V3', '+3V3_SW', '+5V_SW', 'VBUS', '+5V', 'VBAT', '/CELL_NEG', 'Net-(Q1A-D)', 'Net-(D7-K)']
if '(class PowerFine ' in s:    # KiCad already exported it from the project's net classes (netclasses.py)
    FINE = []
i = s.index('(class Power '); j = s.index('(circuit', i)
names = s[i + len('(class Power '):j].split()
keep = [n for n in names if n.strip('"') not in FINE]
s = s[:i] + '(class Power ' + ' '.join(keep) + '\n      ' + s[j:]
fine = ('(class PowerFine ' + ' '.join(FINE) + '\n      (circuit\n        (use_via "Via[0-1]_800:400_um")\n      )\n'
        '      (rule\n        (width 400)\n        (clearance 200)\n      )\n    )\n    ')
if FINE: s = s.replace('(class Power ', fine + '(class Power ', 1)
k = s.index('(class USB '); r = s.index('(rule', k); e = s.index(')\n    )', r)
s = s[:r] + '(rule\n        (width 250)\n        (clearance 150)\n      ' + s[e:]
open(dst, 'w').write(s); print('ok')
