#!/usr/bin/env python3
import sys, re
from conform import run, Case
import tbl, blocks

# ---------------- .tbl : the nominal-addressing table format ----------------
BASE = """| item     | qty | unit  | total = qty * unit |
| -------- | --: | ----: | -----------------: |
| widget   |  10 | 12.00 |                    |
| gadget   |  20 |  6.00 |                    |
| sprocket |   8 | 15.00 |                    |
| flange   |   5 | 24.00 |                    |

grand := sum(total)
"""
def addcol(t, name, tag):
    L=[]
    for i,l in enumerate(t.splitlines()):
        if not l.startswith('|'): L.append(l)
        elif i==0: L.append(l+f' {name}  |')
        elif i==1: L.append(l+' ----- |')
        else: L.append(l+f' {tag}-{i:03d} |')
    return '\n'.join(L)+'\n'

def ins(after, line, t):
    L = t.splitlines()
    i = next(i for i,l in enumerate(L) if after in l)
    L.insert(i+1, line); return '\n'.join(L)+'\n'

def ev_expect(want):
    def f(text):
        _, aggs = tbl.evaluate(text)
        return aggs.get('grand'), want
    return f

tbl_cases = [
    Case('two distant row inserts',
         BASE,
         ins('widget','| cog      |   4 | 25.00 |                    |', BASE),
         ins('flange','| bolt     |  10 |  8.00 |                    |', BASE),
         'clean', ev_expect(660.0)),
    Case('same-row concurrent cell edit',
         BASE,
         BASE.replace('|  20 |  6.00 |','|  99 |  6.00 |'),
         BASE.replace('|  20 |  6.00 |','|  21 |  6.00 |'),
         'conflict'),
    Case('column-name collision (namespace)',
         BASE,
         addcol(BASE, 'code', 'A'),
         addcol(BASE, 'code', 'B'),
         'conflict'),
    Case('disjoint cell edits in different rows',
         BASE,
         BASE.replace('| widget   |  10 |','| widget   |  11 |'),
         BASE.replace('| flange   |   5 |','| flange   |   6 |'),
         'clean', ev_expect(11*12.0 + 120.0 + 120.0 + 6*24.0)),
]

def tbl_parse(b): 
    cols, formulas, rows, aggs = tbl.parse(b); return b   # boundary-preserving
def tbl_render(x): return x

def tbl_break():
    broken = BASE.replace('| unit  |','| price |')
    _, aggs = tbl.evaluate(broken)
    return isinstance(aggs.get('grand'), str) and aggs['grand'].startswith('#REF!')

f1 = run('.tbl (nominal addressing)', 'a.tbl', tbl_parse, tbl_render,
         [BASE], tbl_cases, tbl_break)

# ---- I7 strict parsing: malformed input must RAISE, never yield a number ----
def rejects(text, label):
    try:
        tbl.evaluate(text); return False, label
    except tbl.Malformed: return True, label
    except Exception: return False, label

CONFLICTED = BASE.replace('| gadget   |  20 |  6.00 |                    |',
  '<<<<<<< HEAD\n| gadget   |  20 |  6.00 |                    |\n=======\n'
  '| gadget   |  40 |  6.00 |                    |\n>>>>>>> branch')
i7 = [rejects(CONFLICTED, 'unresolved conflict markers'),
      rejects(BASE.replace('| unit  |', '| qty   |'), 'duplicate column name')]
print('\n  I7 strict parsing:')
for ok, label in i7:
    print(f'    {label:38s} {"rejected  ok" if ok else "ACCEPTED  FAIL"}')
    if not ok: f1.append(f'I7 accepted malformed input: {label}')

# ---------------- .md : boundary-parsed markdown ----------------
MD = open('../L3-block-roundtrip/torture.md').read()
DOC = """# Alpha

Alpha body.

# Beta

Beta body.

# Gamma

Gamma body.
"""
md_cases = [
    Case('edits to different paragraphs', DOC,
         DOC.replace('Alpha body.','Alpha body, revised by A.'),
         DOC.replace('Gamma body.','Gamma body, revised by B.'), 'clean'),
    Case('both edit the same paragraph', DOC,
         DOC.replace('Beta body.','Beta body, A version.'),
         DOC.replace('Beta body.','Beta body, B version.'), 'conflict'),
    Case('scattered namespace: duplicate link label', 
         '# Doc\n\n' + '\n'.join(f'## S{i}\n\nBody {i}.\n' for i in range(1,11)),
         ('# Doc\n\n' + '\n'.join(f'## S{i}\n\nBody {i}.\n' for i in range(1,11)))
             .replace('Body 2.','Body 2 [x][api].\n\n[api]: https://A/'),
         ('# Doc\n\n' + '\n'.join(f'## S{i}\n\nBody {i}.\n' for i in range(1,11)))
             .replace('Body 9.','Body 9 [x][api].\n\n[api]: https://B/'),
         'conflict'),   # ASSERTED REQUIREMENT: must not merge clean
]
f2 = run('.md (boundary-parsed)', 'a.md',
         lambda b: blocks.parse(b), lambda x: blocks.render(x),
         [MD, DOC], md_cases)

print('\n' + '='*62)
tot = len(f1) + len(f2)
print(f'TOTAL FAILURES: {tot}')
sys.exit(1 if tot else 0)
