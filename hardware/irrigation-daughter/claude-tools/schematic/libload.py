import sys, os, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sexp import parse, dumps, find, first, prop_val, Str
REF = os.environ.get('KICAD10_SYMBOL_DIR', '/Applications/KiCad/KiCad.app/Contents/SharedSupport/symbols')
_cache = {}
def raw_symbol(lib, name):
    """return the symbol node from lib file, using a regex slice to avoid parsing huge files"""
    key = (lib, name)
    if key in _cache: return _cache[key]
    txt = _cache.get(lib)
    if txt is None:
        txt = open(os.path.join(REF, lib + '.kicad_sym')).read(); _cache[lib] = txt
    m = re.search(r'\n\t\(symbol "' + re.escape(name) + r'"\n', txt)
    if not m: raise KeyError(f'{lib}:{name}')
    i = m.start() + 2
    # find matching paren
    depth = 0; j = i; instr = False
    while True:
        c = txt[j]
        if instr:
            if c == '\\': j += 2; continue
            if c == '"': instr = False
        elif c == '"': instr = True
        elif c == '(': depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0: break
        j += 1
    node = parse(txt[i:j+1]); _cache[key] = node
    return node

def flat_symbol(lib, name):
    """flattened copy of lib symbol, named 'lib:name'"""
    sym = raw_symbol(lib, name)
    ext = first(sym, 'extends')
    if ext:
        parent = flat_symbol(lib, str(ext[1]))
        pname = str(ext[1])
        out = [sym[0], Str(f'{lib}:{name}')]
        # take non-property, non-symbol attributes from parent, properties from child (fallback parent)
        child_props = {str(p[1]): p for p in find(sym, 'property')}
        for c in parent[2:]:
            if isinstance(c, list) and c and c[0] == 'property':
                out.append(child_props.pop(str(c[1]), c))
            elif isinstance(c, list) and c and c[0] == 'symbol':
                sub = list(c); sub[1] = Str(str(c[1]).replace(pname.split(':')[-1] if False else str(parent[1]).split(':')[-1], name, 1))
                out.append(sub)
            else:
                out.append(c)
        for p in child_props.values(): out.append(p)
        return out
    out = list(sym); out[1] = Str(f'{lib}:{name}')
    return out

def pins(sym):
    res = []
    def walk(n):
        for p in find(n, 'pin'):
            at = first(p, 'at'); num = first(p, 'number'); nm = first(p, 'name')
            hidden = any(isinstance(x, list) and x and x[0]=='hide' for x in p) or 'hide' in [x for x in p if not isinstance(x, list)]
            res.append(dict(num=str(num[1]), name=str(nm[1]), x=float(at[1]), y=float(at[2]),
                            a=float(at[3]) if len(at) > 3 else 0.0, type=str(p[1]), length=float(first(p,'length')[1]) if first(p,'length') else 0))
        for s in find(n, 'symbol'): walk(s)
    walk(sym)
    return res
