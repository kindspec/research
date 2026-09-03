#!/usr/bin/env python3
"""Markdown as an ENTITY MAP OF BLOCKS that retains raw bytes.

The parser finds block BOUNDARIES only. It never re-emits content.
Therefore render(parse(b)) == b by construction, for every input.
"""
import sys, hashlib, re

def parse(text):
    """-> [(name, raw)] preserving every byte including trailing newlines."""
    lines = text.splitlines(keepends=True)
    blocks, cur, fence = [], [], None
    for l in lines:
        s = l.strip()
        f = re.match(r'^(```|~~~)', s)
        if fence:
            cur.append(l)
            if f and s.startswith(fence): fence = None
            continue
        if f:
            if cur and not ''.join(cur).strip(): blocks.append(cur); cur = []
            elif cur: blocks.append(cur); cur = []
            fence = f.group(1); cur.append(l); continue
        if s == '':
            cur.append(l)
            if cur: blocks.append(cur); cur = []
            continue
        if s.startswith('#') and cur and ''.join(cur).strip():
            blocks.append(cur); cur = []
        cur.append(l)
    if cur: blocks.append(cur)
    out, seen = [], {}
    for b in blocks:
        raw = ''.join(b)
        h = hashlib.sha256(raw.strip().encode()).hexdigest()[:8]
        n = seen.get(h, 0); seen[h] = n + 1
        out.append((f'{h}' + (f'.{n}' if n else ''), raw))
    return out

def render(blocks): return ''.join(raw for _, raw in blocks)

if __name__ == '__main__':
    t = open(sys.argv[1], encoding='utf-8').read()
    b = parse(t)
    r = render(b)
    print(f'blocks={len(b)}  bytes_in={len(t)}  bytes_out={len(r)}')
    print('ROUND-TRIP EXACT:', r == t)
    if r != t:
        for i,(x,y) in enumerate(zip(t,r)):
            if x!=y: print('first diff at', i, repr(t[i-20:i+20]), repr(r[i-20:i+20])); break
