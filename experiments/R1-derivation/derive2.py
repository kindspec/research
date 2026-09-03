#!/usr/bin/env python3
"""derive.py extended exactly as PASS5 says the design works: "Formulas,
cross-document references, charts and exports are the same mechanism."
So a .tbl cell may hold {{ other.tbl#name }} too. Cache key is unchanged from
L5: h('resolve', artifact, name, sha256(artifact_bytes))."""
import re, os, hashlib, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                '..', 'L1-nominal-merge'))
import tbl

REF = re.compile(r'\{\{\s*([\w./-]+)#([\w.]+)\s*\}\}')
CACHE = '.gws-cache'

def h(*parts):
    d = hashlib.sha256()
    for p in parts: d.update(str(p).encode()); d.update(b'\0')
    return d.hexdigest()[:12]

def value(art, name, stats, stack=()):
    src = open(art, 'rb').read()
    key = h('resolve', art, name, hashlib.sha256(src).hexdigest())
    p = os.path.join(CACHE, key)
    if os.path.exists(p):
        stats['hit'] += 1
        return open(p).read()
    stats['miss'] += 1
    if (art, name) in stack:
        raise RecursionError('cycle: ' + ' -> '.join(f'{a}#{n}' for a, n in stack))
    text = src.decode()
    # resolve any embedded cross-artifact references FIRST (suspending scheduler)
    text = REF.sub(lambda m: value(m.group(1), m.group(2), stats, stack + ((art, name),)),
                   text)
    rows, aggs = tbl.evaluate(text)
    if name not in aggs: raise KeyError(f'{art}#{name}')
    v = aggs[name]
    if isinstance(v, str) and v.startswith('#REF!'): raise ValueError(f'{art}#{name} -> {v}')
    os.makedirs(CACHE, exist_ok=True); open(p, 'w').write(f'{v:.2f}')
    return f'{v:.2f}'
