#!/usr/bin/env python3
"""C2: the design says wrap ELK/dagre/Graphviz for the derived layout. Is a
real layout engine a function of the SEMANTICS, or of the declaration order
that a merge happens to produce?"""
import subprocess, re
G1 = 'digraph{a->b; a->c; b->d; c->d; e->d;}'
G2 = 'digraph{e->d; c->d; b->d; a->c; a->b;}'   # identical graph, declared in a
                                                # different order -- exactly what a
                                                # merge of two branches produces
def pos(g):
    out = subprocess.run(['dot','-Tplain'], input=g, capture_output=True, text=True).stdout
    return {l.split()[1]: (l.split()[2], l.split()[3])
            for l in out.splitlines() if l.startswith('node ')}
p1, p2 = pos(G1), pos(G2)
print('  declaration order 1:', p1)
print('  declaration order 2:', p2)
print('  identical:', p1 == p2)
same = subprocess.run(['dot','-V'], capture_output=True, text=True)
print(' ', same.stderr.strip())
print('  ==> the SAME graph, declared in a different order, gets DIFFERENT')
print('      coordinates. A merge that reorders declarations therefore moves every')
print('      box on the canvas -- a change no author made and no diff shows,')
print('      because the coordinates are not in the file.')
