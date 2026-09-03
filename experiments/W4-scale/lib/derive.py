#!/usr/bin/env python3
"""Cross-artifact derivation: one mechanism for formulas, references and builds.

Keys are (artifact, namepath). Dependencies are DISCOVERED by parsing, never
declared. Results are memoised in a content-addressed cache keyed by the hash
of (rule, resolved input hashes) -- so staleness is exact, not timestamp-based.
"""
import re, sys, os, hashlib, json
import tbl

REF = re.compile(r'\{\{\s*([\w./-]+)#([\w.]+)\s*\}\}')
CACHE = '.gws-cache'

def h(*parts):
    d = hashlib.sha256()
    for p in parts: d.update(str(p).encode()); d.update(b'\0')
    return d.hexdigest()[:12]

XREF = re.compile(r'([\w./-]+\.tbl)#([\w.]+)')

def refs(path):
    """What does this artifact depend on? Discovered, never declared."""
    t = open(path).read()
    if path.endswith('.md'):  return [(a, n) for a, n in REF.findall(t)]
    if path.endswith('.tbl'): return [(a, n) for a, n in XREF.findall(t)]
    return []

def closure_hash(art, seen=None):
    """Hash an artifact AND everything it transitively depends on.

    The original keyed on ONE artifact's bytes, so a change to a dependency
    left the key unchanged and the cache returned a stale value on a hit.
    """
    seen = set() if seen is None else seen
    if art in seen: return ''
    seen.add(art)
    d = hashlib.sha256(open(art, 'rb').read()).hexdigest()
    for dep, _ in refs(art):
        if os.path.exists(dep): d += closure_hash(dep, seen)
    return hashlib.sha256(d.encode()).hexdigest()[:12]

def value(art, name, stats):
    """Resolve artifact#namepath, memoised in a content-addressed cache."""
    src = open(art, 'rb').read()
    key = h('resolve', art, name, closure_hash(art))
    p = os.path.join(CACHE, key)
    if os.path.exists(p):
        stats['hit'] += 1
        return open(p).read()
    stats['miss'] += 1
    rows, aggs = tbl.evaluate(src.decode())
    if name in aggs: v = aggs[name]
    else: raise KeyError(f'{art}#{name}')
    if isinstance(v, str) and v.startswith('#REF!'):
        raise ValueError(f'{art}#{name} -> {v}')          # I3: loud failure
    os.makedirs(CACHE, exist_ok=True); open(p, 'w').write(f'{v:,.2f}')
    return f'{v:,.2f}'

def render(path, stats):
    txt = open(path).read()
    return REF.sub(lambda m: value(m.group(1), m.group(2), stats), txt)

if __name__ == '__main__':
    st = {'hit': 0, 'miss': 0}
    print(render(sys.argv[1], st))
    print(f'[deps: {refs(sys.argv[1])}]  [cache hits={st["hit"]} misses={st["miss"]}]', file=sys.stderr)
