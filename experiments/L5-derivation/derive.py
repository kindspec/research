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

class Cycle(Exception): pass

_H_MEMO = {}

def closure_hash(art, _stack=None, _memo=None):
    """H(a) = sha256(bytes(a) || sorted(H(d)) for d in deps(a))

    Memoised per node with an explicit recursion STACK, so a cycle is an
    ERROR rather than being silently truncated. The previous version passed a
    shared `seen` set, which made a cycle terminate quietly and return a hash
    for a closure it had not actually walked -- and made the cost O(depth) per
    resolve, which measured at 83-84% of a warm build.
    """
    memo = _H_MEMO if _memo is None else _memo
    stack = _stack if _stack is not None else []
    if art in memo: return memo[art]
    if art in stack:
        raise Cycle(' -> '.join(stack[stack.index(art):] + [art]))
    stack.append(art)
    try:
        d = hashlib.sha256(open(art, 'rb').read()).hexdigest()
        deps = sorted({dep for dep, _ in refs(art) if os.path.exists(dep)})
        parts = [closure_hash(dep, stack, memo) for dep in deps]
        h = hashlib.sha256((d + ''.join(sorted(parts))).encode()).hexdigest()[:12]
    finally:
        stack.pop()
    memo[art] = h
    return h

def invalidate():
    _H_MEMO.clear()

def value(art, name, stats):
    """Resolve artifact#namepath, memoised in a content-addressed cache."""
    invalidate()
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
