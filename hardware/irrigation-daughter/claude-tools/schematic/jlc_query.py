"""Query JLCPCB parts API. Usage: python3 jlc_query.py C123 C456 ... or a keyword. Prints JSON lines.
Run on the Mac (needs internet). Fields: code, type (base/expand), stock, price tiers, name, desc, package."""
import json, sys, urllib.request, time
URL = 'https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList'
def q(kw, n=3):
    body = json.dumps({'keyword': kw, 'currentPage': 1, 'pageSize': n}).encode()
    r = urllib.request.Request(URL, body, {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    d = json.load(urllib.request.urlopen(r, timeout=20))
    return (d.get('data') or {}).get('componentPageInfo', {}).get('list') or []
def price(c, qty):
    for p in c.get('componentPrices') or []:
        if p['startNumber'] <= qty and (p['endNumber'] == -1 or qty <= p['endNumber']):
            return p['productPrice']
for kw in sys.argv[1:]:
    try:
        L = q(kw, 1 if kw.startswith('C') and kw[1:].isdigit() else 5)
    except Exception as e:
        print(json.dumps({'kw': kw, 'err': str(e)})); continue
    if not L: print(json.dumps({'kw': kw, 'err': 'not found'}))
    for c in L:
        print(json.dumps({'kw': kw, 'code': c.get('componentCode'), 'type': c.get('componentLibraryType'),
              'pref': c.get('preferredComponentFlag'), 'stock': c.get('stockCount'),
              'p10': price(c, 10), 'p100': price(c, 100), 'name': c.get('componentModelEn') or c.get('erpComponentName'),
              'pkg': c.get('componentSpecificationEn'), 'desc': (c.get('describe') or '')[:90]}))
    time.sleep(0.3)

def dump(codes, path):
    """Save raw API records {code: record} for cost estimation."""
    out = {}
    for c in codes:
        L = q(c, 1); out[c] = L[0] if L else None; time.sleep(0.3)
    json.dump(out, open(path, 'w'), indent=1)
