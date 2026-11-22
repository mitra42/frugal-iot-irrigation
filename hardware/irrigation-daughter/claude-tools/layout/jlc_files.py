"""Turn KiCad exports into JLCPCB upload files: BOM_JLCPCB.csv, CPL_JLCPCB.csv, gerbers.zip. Cross-checks refs."""
import csv, re, zipfile, os, sys, json, math
HERE = os.path.dirname(os.path.abspath(__file__)); RAW = HERE + '/out/fab'; DST = HERE + '/../../fabrication'
os.chdir(RAW)
def refs(s):
    out = []
    for t in s.split(','):
        m = re.match(r'([A-Z]+)(\d+)-[A-Z]+(\d+)$', t.strip())
        out += [f'{m[1]}{i}' for i in range(int(m[2]), int(m[3]) + 1)] if m else [t.strip()]
    return out
bom_rows = []; bom_refs = set()
for r in csv.DictReader(open('bom_kicad.csv')):
    if r['DNP'] or not r['LCSC']: continue
    rr = refs(r['Refs']); bom_refs |= set(rr)
    bom_rows.append([r['Value'], ','.join(rr), r['Footprint'].split(':')[-1], r['LCSC']])
merged = {}                       # one line per LCSC part number (e.g. the eight KF128 valve terminals)
for v, d, fp, lc in bom_rows:
    if lc in merged: merged[lc][1] += ',' + d
    else: merged[lc] = [v, d, fp, lc]
bom_rows = list(merged.values())
with open(DST + '/BOM_JLCPCB.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #']); w.writerows(bom_rows)
# JLCPCB's part models differ from KiCad's footprints, so a CPL copied straight from KiCad shows parts turned or
# shifted in the assembly preview (found on frugal-iot-hw-sensor, 28 Oct 2026, and fixed there by hand each time
# until it was put here). Rotation is ADDED to KiCad's, by footprint; only SOT-23 is in this board's BOM, the
# rest are what the sensor board needed, kept so the next board starts from known-good values.
# For through-hole parts whose KiCad origin is pin 1, JLCPCB centres its model on the given point, so we give it
# the centre of the pin row instead.
# Found in JLCPCB's preview of this board (22 Nov 2026): the TSSOP-16 (U1) model has its leads along the other axis
# from the pads, and the 1x4 header (J3) model is vertical and centred on pin 1, so both need -90 and the header
# needs centring as well. Whether the rotation sign puts pin 1 at the right end is checked in the preview, not
# assumed. Confirmed in the preview of the 22 Nov 2026 order: Q1-Q5 and D_SMA (D5, D7) need no further change. NOT YET CONFIRMED: LED_0603, Q6-Q8, D1/D2 and the KF128 terminals' pin 1 and centring.
ROT_FIX = {'SOT-23': 180, 'SOT-23-5': -90, 'SOIC-8_3.9x4.9mm_P1.27mm': -90,
           'SOIC-8-1EP_3.9x4.9mm_P1.27mm_EP2.41x3.3mm': -90, 'JST_PH_S2B-PH-K_1x02_P2.00mm_Horizontal': 180,
           'TSSOP-16_4.4x5mm_P0.65mm': -90, 'PinHeader_1x04_P2.54mm_Vertical': -90}
CENTRE = ('TerminalBlock_', 'JST_PH_', 'PinHeader_')
FP = json.load(open(HERE + '/fp.json'))
def pin_row_centre(ref, rot):
    pads = [v for k, v in FP[ref]['pads'].items() if k.isdigit()]
    x = sum(p[0] for p in pads) / len(pads); y = sum(p[1] for p in pads) / len(pads)
    a = math.radians(rot); c, s_ = round(math.cos(a), 9), round(math.sin(a), 9)
    return x * c + y * s_, -x * s_ + y * c          # board coordinates, y down
cpl_refs = set()
with open(DST + '/CPL_JLCPCB.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
    for r in csv.DictReader(open('pos_kicad.csv')):
        cpl_refs.add(r['Ref'])
        x, y, rot = float(r['PosX']), float(r['PosY']), float(r['Rot'])
        if r['Package'].startswith(CENTRE):
            dx, dy = pin_row_centre(r['Ref'], rot); x += dx; y -= dy     # pos file has y up
        rot = (rot + ROT_FIX.get(r['Package'], 0)) % 360
        w.writerow([r['Ref'], f"{x:.4f}mm", f"{y:.4f}mm", 'Top' if r['Side'] == 'top' else 'Bottom', f"{rot:.0f}"])
with zipfile.ZipFile(DST + '/gerbers.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for n in sorted(os.listdir('gerbers')):
        if n.endswith(('.gbr', '.drl')) and 'drl_map' not in n: z.write(f'gerbers/{n}', n)
print('BOM lines', len(bom_rows), 'parts', len(bom_refs), '| CPL parts', len(cpl_refs))
print('in BOM not CPL:', sorted(bom_refs - cpl_refs)); print('in CPL not BOM:', sorted(cpl_refs - bom_refs))
print('zip:', zipfile.ZipFile(DST + '/gerbers.zip').namelist())
