"""JLCPCB PCBA cost estimate at several quantities.
Inputs: out/bom.csv (run_kicad.sh), out/jlc_prices.json (jlc_dump.sh), out/netlist.xml.
Fees from jlcpcb.com/help/article/pcb-assembly-price (page updated 9 Sep 2026, read 14 Oct 2026).
Usage: python3 cost_estimate.py > ../../COST-ESTIMATE.txt   -> 10 (Economic), 100 (Economic, panelised)
For the irrigation daughter board; the bare PCB is estimated (see NOTES)."""
import csv, json, re, xml.etree.ElementTree as ET
from collections import defaultdict

ECON = dict(name='Economic', setup=8.18, stencil=1.53, panel=0.0, smt_joint=0.0016, manual_joint=0.0164,
            hand_labour=3.58, feeder_ext=3.07, feeder_all=0.0, min_smt_per_board=0.0, confirm=0.45,
            packing=0.0, fixture=0.0)
ECON_PANEL = dict(ECON, name='Economic, panelised', panel=8.21)
STD = dict(name='Standard', setup=25.56, stencil=8.21, panel=0.0, smt_joint=0.0016, manual_joint=0.0164,
           hand_labour=3.58, feeder_ext=0.0, feeder_all=1.53, min_smt_per_board=0.48, confirm=0.45,
           packing=0.50, fixture=None)   # fixture by quantity, see fixture_fee()
XRAY = [(10, 1.64), (50, 0.82), (200, 0.49), (500, 0.33), (1000, 0.25), (3000, 0.16), (99999, 0.082)]
XRAY_REFS = ()      # nothing with pads under its body
COLUMNS = [(10, ECON), (100, ECON_PANEL)]
# Bare PCB: ESTIMATED from the irrigation board's JLCPCB instant quote of 15 Oct 2026 (100 x 80 mm, 2-layer, 1.6 mm,
# HASL, green; A$, at JLCPCB's displayed 1.435 AUD/USD). This board is 100 x 42 mm: at 10 pcs it is inside JLCPCB's
# <=100 x 100 prototype price, so that stays; at 100 pcs the board line (A$85.67) is scaled by area, 42/80.
AREA = 42 / 80
PCB_QUOTE = {10: 7.18 / 1.435, 100: (11.48 + 3.16 + 85.67 * AREA) / 1.435}
SHIP_PCB_ONLY = {10: 30.47 / 1.435, 100: 70.86 / 1.435}   # DHL to Australia, bare boards only

def fixture_fee(n):
    for lim, f in [(29, 16.42), (99, 24.63), (199, 41.04), (349, 82.09), (499, 123.13), (10**6, 164.18)]:
        if n <= lim: return f
def is_tht(fp): return any(k in fp for k in ('THT', 'TerminalBlock', 'PinHeader', 'JST_PH'))
def refs(s):
    out = []
    for t in s.split(','):
        m = re.match(r'([A-Z]+)(\d+)-[A-Z]+(\d+)$', t)
        out += [f'{m[1]}{i}' for i in range(int(m[2]), int(m[3]) + 1)] if m else [t]
    return out
def price(rec, q):
    for p in rec['componentPrices']:
        if p['startNumber'] <= q and (p['endNumber'] == -1 or q <= p['endNumber']): return p['productPrice']
    return rec['componentPrices'][-1]['productPrice']

J = json.load(open('out/jlc_prices.json'))
pins = defaultdict(set)
for node in ET.parse('out/netlist.xml').getroot().iter('node'):
    pins[node.get('ref')].add(node.get('pin'))
G = {}   # group BOM rows by LCSC code: feeder fee and minimum buy are per part number
for r in csv.DictReader(open('out/bom.csv')):
    if r['DNP'] or not r['LCSC']: continue
    g = G.setdefault(r['LCSC'], dict(r, Refs='', Qty=0, Value=r['MPN'] if r['MPN'] != r['Value'] else r['Value']))
    g['Refs'] += (',' if g['Refs'] else '') + r['Refs']; g['Qty'] += int(r['Qty'])

smt_j = tht_j = xray = 0; ext = []; lines = []
for code, r in G.items():
    R = refs(r['Refs']); rec = J[code]
    kind = 'Basic' if rec['componentLibraryType'] == 'base' else ('PrefExt' if rec.get('preferredComponentFlag') else 'Ext')
    if kind == 'Ext': ext.append(code)
    j = sum(len(pins[x]) for x in R)
    if is_tht(r['Footprint']): tht_j += j
    else: smt_j += j
    xray += sum(1 for x in R if x in XRAY_REFS)
    lines.append((r, rec, kind))

def buy_qty(rec, q, n):
    return max(q * n + (rec.get('lossNumber') or 0), rec.get('leastPatchNumber') or 0)

def estimate(n, F):
    parts = sum(buy_qty(rec, int(r['Qty']), n) * price(rec, buy_qty(rec, int(r['Qty']), n)) for r, rec, _ in lines)
    xr_n = xray * n; xr_rate = next(p for lim, p in XRAY if xr_n <= lim)
    smt = smt_j * F['smt_joint'] * n
    fees = {
        'Setup + stencil + confirm': F['setup'] + F['stencil'] + F['confirm'] + F['panel'],
        'SMT joints': max(smt, F['min_smt_per_board'] * n),
        'Through-hole joints (manual)': tht_j * F['manual_joint'] * n + F['hand_labour'],
        'Feeder loading': len(ext) * F['feeder_ext'] + len(lines) * F['feeder_all'],
        'X-ray (module)': xr_n * xr_rate,
        'Fixture + packing': (fixture_fee(n) if F['fixture'] is None else F['fixture']) + F['packing'],
        'Components': parts,
        'Bare PCB (see notes)': PCB_QUOTE.get(n, 0.0),
    }
    return fees

LEGEND = """Columns (part table):
  Type    Basic   = JLCPCB Basic part, permanently on a machine feeder: no feeder fee (Economic).
          PrefExt = 'Preferred Extended': Extended, but exempt from the feeder fee on Economic PCBA.
          Ext     = Extended: $3.07 feeder-loading fee once per part number per order (Economic).
  /brd    quantity per board.
  buy@N   quantity JLCPCB buys for N boards = max(/brd x N + JLCPCB's attrition allowance for that part,
          JLCPCB's minimum order for that part). E.g. a 0603 resistor at 10 boards: 1 x 10 + 10 = 20.
  $@N     buy@N x unit price at that quantity's price tier.
"""
NOTES = """Notes:
  * Bare PCB (100 x 42 mm) ESTIMATED from the irrigation board's quote, not quoted: A$7.18 / 10 (JLCPCB's
    prototype price, any board within 100 x 100), and at 100 the board line A$85.67 x 42/80 plus engineering
    A$11.48 and film A$3.16 = A$59.62 = $41.55. Re-quote from fabrication/gerbers.zip.
  * Shipping, tax and import duty not included.
  * Eight valve channels, all fitted; each of channels 5-8 can be left off (its six parts) to save ~$0.29 / board
    at 10 and ~$0.21 at 100, as on the irrigation board.
  * The host board is NOT included: frugal-iot-hw-sensor V0.2 is $11.51 / $7.16 per board, frugal-iot-hw-lora V0.3
    $17.31 / $11.58 (their own COST-ESTIMATE.txt). See DECISIONS D7 for the comparison with the irrigation board.
  * JLCPCB's FAQ says Economic PCBA above 30 pieces needs panelising; the panel fee ($8.21) is in the 100 column.
"""
if __name__ == '__main__':
    print(LEGEND)
    hdr = f'{"Refs":26} {"Value":22} {"LCSC":10} {"Type":7} {"/brd":>4} {"buy@10":>6} {"$@10":>7} {"buy@100":>7} {"$@100":>7}'
    print(hdr)
    for r, rec, kind in lines:
        q = int(r['Qty']); b10, b100 = buy_qty(rec, q, 10), buy_qty(rec, q, 100)
        print(f'{r["Refs"][:26]:26} {r["Value"][:22]:22} {r["LCSC"]:10} {kind:7} {q:4} {b10:6} {b10 * price(rec, b10):7.2f}'
              f' {b100:7} {b100 * price(rec, b100):7.2f}')
    print(f'\nPer board: {smt_j} SMT joints, {tht_j} through-hole joints, {len(lines)} part numbers '
          f'({len(ext)} Extended with fee).\n')
    E = [(n, F, estimate(n, F)) for n, F in COLUMNS]
    print(f'{"":32}' + ''.join(format(str(n) + ' ' + F['name'], '>24') for n, F, _ in E))
    for k in E[0][2]:
        print(f'{k:32}' + ''.join(f'{"$" + format(fees[k], ".2f"):>24}' for _, _, fees in E))
    print(f'{"TOTAL (excl. shipping)":32}' + ''.join(f'{"$" + format(sum(fees.values()), ".2f"):>24}' for _, _, fees in E))
    print(f'{"Per board":32}' + ''.join(f'{"$" + format(sum(fees.values()) / n, ".2f"):>24}' for n, _, fees in E))
    print('\nSame, per board:')
    for k in E[0][2]:
        print(f'{k:32}' + ''.join(f'{"$" + format(fees[k] / n, ".2f"):>24}' for n, _, fees in E))
    print(f'{"Per board":32}' + ''.join(f'{"$" + format(sum(fees.values()) / n, ".2f"):>24}' for n, _, fees in E))
    print('\n' + NOTES)
    print('Extended (fee-bearing on Economic):', ' '.join(ext))
