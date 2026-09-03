#!/usr/bin/env python3
"""P2: REORDER + EDIT = SILENT LOST UPDATE under stock git.
L1 Result 4 asserts "Alice reorders four rows; Bob edits a cell in one of them.
Stock git merged clean and correctly." That result does not generalise."""
import sys, os
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(H,'..','R1-common'), os.path.join(H,'..','L1-nominal-merge')]
from gw import git_merge
import tbl

HDR = ("| id     | item     | qty | unit  | total = qty * unit |\n"
       "| ------ | -------- | --: | ----: | -----------------: |\n")
TAIL = "\nkey   := id\ngrand := sum(total)\n"
def r(i, item, qty, unit):
    return f'| r_{i:04d} | {item:8s} | {qty:3d} | {unit:5s} |                    |\n'

o, g, s, f = (r(1,'opening',1,'1000'), r(2,'gadget',20,'6.00'),
              r(3,'salary',1,'2000'), r(4,'flange',5,'24.00'))
BASE   = HDR + o + g + s + f + TAIL
ALICE  = HDR + o + s + g + f + TAIL                        # swap two adjacent rows
BOB    = BASE.replace('| salary   |   1 | 2000  |', '| salary   |   1 | 1500  |')

rc, txt, n = git_merge(BASE, ALICE, BOB, 'b.tbl')
print(f'git merge exit={rc} ({"CLEAN" if rc==0 else "CONFLICT"}) markers={n}')
print('merged rows:')
for l in txt.splitlines():
    if l.startswith('| r_'): print('   ', l)
_, ab = tbl.evaluate(BASE);  _, aa = tbl.evaluate(ALICE); _, abo = tbl.evaluate(BOB)
print(f'base grand    = {ab["grand"]}')
print(f'Alice grand   = {aa["grand"]}   (reorder only, value unchanged)')
print(f'Bob grand     = {abo["grand"]}   (2000 -> 1500)')
if n:
    print('==> LEGITIMATE CONFLICT. Reorder + edit of a moved row does NOT merge')
    print('    clean here, contrary to what L1 Result 4 suggests generalises.')
    print('    But note the conflicted file is not a table any more:')
    try: tbl.evaluate(txt)
    except Exception as e: print(f'    tbl.evaluate -> {type(e).__name__}: {e}  (I5 violated)')
else:
    _, am = tbl.evaluate(txt)
    print(f'MERGED grand  = {am["grand"]}   Bob\'s 1500 present: {"1500" in txt}')

print()
print('--- the same pair with the rows further apart ---')
pad = ''.join(r(i, f'pad{i:03d}', 1, '0.00') for i in range(100, 110))
BASE2  = HDR + o + g + pad + s + f + TAIL
ALICE2 = HDR + o + s + g + pad + f + TAIL      # Alice moves `salary` to the top block
BOB2   = BASE2.replace('| salary   |   1 | 2000  |', '| salary   |   1 | 1500  |')
rc, txt, n = git_merge(BASE2, ALICE2, BOB2, 'b.tbl')
print(f'git merge exit={rc} markers={n}')
if n == 0:
    _, am = tbl.evaluate(txt)
    print(f'  grand={am["grand"]}   Bob\'s 1500 present: {"1500" in txt}')
    print(f'  rows: {[l.split("|")[2].strip() for l in txt.splitlines() if l.startswith("| r_")]}')
