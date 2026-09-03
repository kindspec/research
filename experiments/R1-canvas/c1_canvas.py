#!/usr/bin/env python3
"""C1: the canvas format's node namespace is SCATTERED (one node per line),
which is precisely the defect PASS4 diagnosed in markdown link labels -- and
the @layout override layer has no referential integrity at all."""
import sys, os
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(H,'..','R1-common'), os.path.join(H,'..','L4-spatial')]
from gw import git_merge
import canvas

BASE = """node api   "API Gateway"
node auth  "Auth Service"
node queue "Queue"
node work  "Worker"
node db    "Postgres"
edge api -> auth
edge auth -> queue
edge queue -> work
edge work -> db

@layout
db { at: 400, 500 }
"""
def lay(t):
    n, e, o = canvas.parse_semantic(t)
    return canvas.layout(n, e, o), [x for x, _ in n]

print('--- C1a an @layout override for a node DELETED on the other branch ---')
ALICE = BASE.replace('node db    "Postgres"\n', '').replace('edge work -> db\n', '')
BOB   = BASE.replace('db { at: 400, 500 }', 'db { at: 400, 500 }\napi { at: 20, 20 }')
rc, txt, n = git_merge(BASE, ALICE, BOB, 'arch.canvas')
print(f'  git merge exit={rc} ({"CLEAN" if rc==0 else "CONFLICT"}) markers={n}')
pos, names = lay(txt)
print(f'  nodes declared in merged file: {names}')
print(f'  positions returned by layout(): {sorted(pos)}')
print(f'  ==> layout() returns a position for {sorted(set(pos)-set(names))}, a node that')
print('      does not exist. pos.update(over) INSERTS the dangling override. A renderer')
print('      iterating the layout draws a deleted node. I3 says broken refs fail loudly.')

print()
print('--- C1b an EDGE to a node renamed on the other branch is silently dropped ---')
ALICE = (BASE.replace('node db    "Postgres"', 'node pg    "Postgres"')
             .replace('edge work -> db', 'edge work -> pg')
             .replace('db { at: 400, 500 }', 'pg { at: 400, 500 }'))
BOB   = BASE.replace('edge api -> auth\n', 'edge api -> auth\nedge api -> db\n')
rc, txt, n = git_merge(BASE, ALICE, BOB, 'arch.canvas')
print(f'  git merge exit={rc} ({"CLEAN" if rc==0 else "CONFLICT"}) markers={n}')
nodes, edges, over = canvas.parse_semantic(txt)
print(f'  edges in merged file: {edges}')
print(f'  nodes: {[x for x,_ in nodes]}')
dangling = [(a,b) for a,b in edges if a not in dict(nodes) or b not in dict(nodes)]
print(f'  DANGLING edges: {dangling}')
pos = canvas.layout(nodes, edges, over)
print(f'  layout() output: {sorted(pos)}')
print('  ==> layout() skips a dangling edge with `if b in depth and a in depth`.')
print('      Bob\'s new edge silently vanishes from the diagram. No error, no marker.')

print()
print('--- C1c two branches add DIFFERENT nodes with the SAME name ---')
ALICE = BASE.replace('node api   "API Gateway"\n',
                     'node cache "Redis"\nnode api   "API Gateway"\n')
BOB   = BASE.replace('node db    "Postgres"\n',
                     'node db    "Postgres"\nnode cache "Memcached"\n')
rc, txt, n = git_merge(BASE, ALICE, BOB, 'arch.canvas')
print(f'  git merge exit={rc} ({"CLEAN" if rc==0 else "CONFLICT"}) markers={n}')
nodes, edges, over = canvas.parse_semantic(txt)
print(f'  nodes: {nodes}')
pos = canvas.layout(nodes, edges, over)
print(f'  layout() gives ONE position for "cache": {pos["cache"]}')
print('  ==> the node namespace is one binding per line, scattered through the file,')
print('      so git cannot see the collision. arch.canvas#cache now resolves to one')
print('      of two different things. Same defect as the markdown [api] label.')

print()
print('--- C1d does adding an unrelated node move an existing one? ---')
p0, _ = lay(BASE)
p1, _ = lay(BASE.replace('node api   "API Gateway"\n',
                         'node cache "Redis"\nnode api   "API Gateway"\n'))
moved = {k: (p0[k], p1[k]) for k in p0 if k in p1 and p0[k] != p1[k]}
print(f'  nodes whose derived position changed: {moved}')
print('  ==> derived layout is a function of DECLARATION ORDER, and a merge decides')
print('      declaration order. Positions are not in the file, but they are still')
print('      coupled state -- just relocated into the layout function.')

print()
print('--- C1e is the layout function deterministic? ---')
runs = {str(sorted(lay(BASE)[0].items())) for _ in range(20)}
print(f'  20 runs, same input: {len(runs)} distinct results -> '
      f'{"deterministic (HELD)" if len(runs)==1 else "NON-DETERMINISTIC"}')
import subprocess
r = subprocess.run(['which','dot'], capture_output=True, text=True)
print(f'  graphviz `dot` installed here: {bool(r.stdout.strip())} '
      f'-- the design says wrap ELK/dagre/Graphviz, whose coordinates are NOT')
print('     stable across versions; that determinism claim is untested by anything.')
