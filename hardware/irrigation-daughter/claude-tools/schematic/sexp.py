"""Minimal S-expression reader/writer for KiCad files."""
import re

def parse(text):
    i = text.index('(')
    node, _ = _parse(text, i)
    return node

def _parse(s, i):
    assert s[i] == '('
    i += 1
    out = []
    while i < len(s):
        c = s[i]
        if c == '(':
            child, i = _parse(s, i)
            out.append(child)
        elif c == ')':
            return out, i + 1
        elif c == '"':
            j = i + 1; buf = []
            while s[j] != '"':
                if s[j] == '\\':
                    # store the UNESCAPED character. Keeping the backslash here means _atom
                    # escapes it again on the way out, so a string containing \" grows a
                    # backslash on every round trip - which silently corrupts KiCad's power
                    # symbols, whose Description fields contain escaped quotes, and shows up
                    # as lib_symbol_mismatch on every one of them.
                    buf.append(s[j+1]); j += 2
                else:
                    buf.append(s[j]); j += 1
            out.append(Str(''.join(buf)))
            i = j + 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < len(s) and not s[j].isspace() and s[j] not in '()"':
                j += 1
            out.append(s[i:j]); i = j
    raise ValueError('unterminated')

class Str(str):
    """A token that was quoted in the source and must be re-quoted."""
    __slots__ = ()

def dumps(node, indent=0):
    pad = '\t' * indent
    if not isinstance(node, list):
        return _atom(node)
    if not node:
        return '()'
    head = node[0]
    simple = all(not isinstance(c, list) for c in node)
    if simple:
        return '(' + ' '.join(_atom(c) for c in node) + ')'
    parts = ['(' + _atom(head)]
    inline = []
    k = 1
    while k < len(node) and not isinstance(node[k], list):
        inline.append(_atom(node[k])); k += 1
    if inline:
        parts[0] += ' ' + ' '.join(inline)
    body = [dumps(c, indent + 1) for c in node[k:]]
    return parts[0] + '\n' + '\n'.join('\t' * (indent + 1) + b for b in body) + '\n' + pad + ')'

def _atom(a):
    if isinstance(a, Str):
        return '"' + str(a).replace('\\', '\\\\').replace('"', '\\"') + '"'
    return str(a)

def find(node, name):
    return [c for c in node if isinstance(c, list) and c and c[0] == name]

def first(node, name):
    r = find(node, name)
    return r[0] if r else None

def prop(sym, name):
    for p in find(sym, 'property'):
        if len(p) > 1 and str(p[1]) == name:
            return p
    return None

def prop_val(sym, name):
    p = prop(sym, name)
    return str(p[2]) if p and len(p) > 2 else None
