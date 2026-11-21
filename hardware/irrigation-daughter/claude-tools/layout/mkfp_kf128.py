"""Write irrigation.pretty/TerminalBlock_KF128-5.08-2P.kicad_mod from KiCad's Phoenix MKDS-1,5-2-5.08 (D79).
Plain python. Same pin positions and pad size; changed to match the KF128-5.08 drawing (datasheets/KF128-5.08-2P_C474952.pdf):
  - drill 1.4 mm (datasheet PCB layout: 1.40 +0.10/-0), was 1.3;
  - body and courtyard exactly P x 5.08 = 10.16 mm wide (x -2.54..7.62), because KF128 blocks are made to butt
    together on a 5.08 mm grid. The MKDS courtyard is 11.17 mm wide, so eight of them in a row at 10.16 mm pitch
    would be eight courtyard overlaps, and at 11.2 mm pitch the row no longer fits between the corner holes;
  - depth 10.7 mm with the pins 5.4 mm from one face; which face is not certain from the drawing, so the
    courtyard takes +-5.45 mm, covering both."""
import re
SRC = ('/Applications/KiCad/KiCad.app/Contents/SharedSupport/footprints/TerminalBlock_Phoenix.pretty/'
       'TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal.kicad_mod')
NAME = 'TerminalBlock_KF128-5.08-2P'
t = open(SRC).read()
t = t.replace('"TerminalBlock_Phoenix_MKDS-1,5-2-5.08_1x02_P5.08mm_Horizontal"', f'"{NAME}"', 1)
t = re.sub(r'\(descr "[^"]*"\)', '(descr "Cixi Kefa KF128-5.08-2P screw terminal, 2 pins, pitch 5.08 mm, '
           'body 10.16 x 10.7 mm, drill 1.4 mm; blocks butt together (LCSC C474952)")', t)
t = re.sub(r'\(tags "[^"]*"\)', '(tags "THT terminal block KF128 5.08mm")', t)
t = t.replace('(drill 1.3)', '(drill 1.4)')
# courtyard: exactly the body width (0.01 mm inside, so neighbours touch without overlapping), +-5.45 deep
t = re.sub(r'\(start -3\.04 -5\.71\)\s*\(end 8\.13 5\.1\)', '(start -2.53 -5.45)\n\t\t(end 7.61 5.45)', t)
# silk 0.1 mm inside the body edge (not 0.12 mm outside it, as MKDS): butted neighbours' outlines then sit 0.2 mm
# apart instead of on top of each other, which DRC reports as 100+ silk overlaps
t = t.replace('-2.66', '-2.44').replace('7.74', '7.52')
open(f'../../daughter/irrigation.pretty/{NAME}.kicad_mod', 'w').write(t)
assert '(drill 1.4)' in t and '7.61 5.45' in t and '-2.66' not in t and '7.52' in t
print('wrote', NAME)
