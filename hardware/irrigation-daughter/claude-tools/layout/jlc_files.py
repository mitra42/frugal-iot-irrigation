"""Turn KiCad exports into JLCPCB upload files: BOM_JLCPCB.csv, CPL_JLCPCB.csv, gerbers.zip. Cross-checks refs."""
import csv, re, zipfile, os, sys
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
with open(DST + '/BOM_JLCPCB.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['Comment', 'Designator', 'Footprint', 'LCSC Part #']); w.writerows(bom_rows)
cpl_refs = set()
with open(DST + '/CPL_JLCPCB.csv', 'w', newline='') as f:
    w = csv.writer(f); w.writerow(['Designator', 'Mid X', 'Mid Y', 'Layer', 'Rotation'])
    for r in csv.DictReader(open('pos_kicad.csv')):
        cpl_refs.add(r['Ref'])
        w.writerow([r['Ref'], f"{float(r['PosX']):.4f}mm", f"{float(r['PosY']):.4f}mm", 'Top' if r['Side'] == 'top' else 'Bottom', f"{float(r['Rot']):.0f}"])
with zipfile.ZipFile(DST + '/gerbers.zip', 'w', zipfile.ZIP_DEFLATED) as z:
    for n in sorted(os.listdir('gerbers')):
        if n.endswith(('.gbr', '.drl')) and 'drl_map' not in n: z.write(f'gerbers/{n}', n)
print('BOM lines', len(bom_rows), 'parts', len(bom_refs), '| CPL parts', len(cpl_refs))
print('in BOM not CPL:', sorted(bom_refs - cpl_refs)); print('in CPL not BOM:', sorted(cpl_refs - bom_refs))
print('zip:', zipfile.ZipFile(DST + '/gerbers.zip').namelist())
