#!/usr/bin/env python3
"""Two representations of the same diagram, compared under concurrent edit.

A) SEMANTIC + SPARSE NAMED OVERRIDES  (USD-style layered composition)
   nodes/edges are declared; positions are DERIVED by auto-layout;
   human nudges live in a separate @layout block keyed BY NAME.

B) FULL COORDINATES  (what Excalidraw / draw.io / SVG actually store)
   every element carries absolute x/y in the file.
"""
import sys, re, json

def parse_semantic(t):
    nodes, edges, over = [], [], {}
    sec = 'body'
    for l in t.splitlines():
        s = l.strip()
        if not s or s.startswith('#'): continue
        if s == '@layout': sec = 'layout'; continue
        if sec == 'layout':
            m = re.match(r'(\w+)\s*\{\s*at:\s*(-?\d+)\s*,\s*(-?\d+)\s*\}', s)
            if m: over[m.group(1)] = (int(m.group(2)), int(m.group(3)))
            continue
        m = re.match(r'node\s+(\w+)\s+"([^"]*)"', s)
        if m: nodes.append((m.group(1), m.group(2))); continue
        m = re.match(r'edge\s+(\w+)\s*->\s*(\w+)', s)
        if m: edges.append((m.group(1), m.group(2)))
    return nodes, edges, over

def layout(nodes, edges, over):
    """Deterministic derived layout: layer by longest path, then order."""
    succ = {}
    for a, b in edges: succ.setdefault(a, []).append(b)
    depth = {n: 0 for n, _ in nodes}
    for _ in range(len(nodes)):
        for a, b in edges:
            if b in depth and a in depth: depth[b] = max(depth[b], depth[a] + 1)
    byl = {}
    pos = {}
    for n, _ in nodes:
        d = depth[n]; i = byl.get(d, 0); byl[d] = i + 1
        pos[n] = (100 + i * 160, 80 + d * 120)
    pos.update(over)                      # human nudges win
    return pos

if __name__ == '__main__':
    n, e, o = parse_semantic(open(sys.argv[1]).read())
    for k, v in sorted(layout(n, e, o).items()): print(f'{k:10s} {v}')
