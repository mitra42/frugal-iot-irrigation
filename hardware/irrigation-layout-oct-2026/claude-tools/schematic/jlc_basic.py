"""Search JLCPCB for Basic / preferred-extended parts. Usage: python3 jlc_basic.py 'keyword' [...]
Tries the API's library-type filter; prints only base or preferred parts with stock."""
import json, sys, urllib.request, time
URL = 'https://jlcpcb.com/api/overseas-pcb-order/v1/shoppingCart/smtGood/selectSmtComponentList'
def q(kw, extra, n=50):
    body = json.dumps({'keyword': kw, 'currentPage': 1, 'pageSize': n, **extra}).encode()
    r = urllib.request.Request(URL, body, {'Content-Type': 'application/json', 'User-Agent': 'Mozilla/5.0'})
    d = json.load(urllib.request.urlopen(r, timeout=20))
    return (d.get('data') or {}).get('componentPageInfo', {}).get('list') or []
for kw in sys.argv[1:]:
    L = q(kw, {'componentLibraryType': 'base', 'preferredComponentFlag': True})
    seen = 0
    for c in L:
        if c.get('componentLibraryType') == 'base' or c.get('preferredComponentFlag'):
            seen += 1
            p = c['componentPrices'][0]['productPrice'] if c.get('componentPrices') else None
            print(f"{kw[:22]:22} {c['componentCode']:9} {'B' if c['componentLibraryType']=='base' else 'P'} {c['stockCount']:>9} ${p} {c.get('componentModelEn','')[:28]:28} {c.get('componentSpecificationEn','')[:14]:14} {(c.get('describe') or '')[:70]}")
    print(f'# {kw}: {len(L)} returned, {seen} basic/preferred')
    time.sleep(0.3)
