#!/usr/bin/env python3
"""T5: formula edits, column deletion, and blank-vs-zero-vs-missing."""
import sys, os
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(H,'..','R1-common'), os.path.join(H,'..','L1-nominal-merge')]
from gw import git_merge
import tbl

BASE = """| id     | item     | qty | unit  | total = qty * unit |
| ------ | -------- | --: | ----: | -----------------: |
| r_0001 | widget   |  10 | 12.00 |                    |
| r_0002 | gadget   |  20 |  6.00 |                    |
| r_0003 | sprocket |   8 | 15.00 |                    |
| r_0004 | flange   |   5 | 24.00 |                    |

key   := id
grand := sum(total)
"""
def q(t):
    try:
        r, a = tbl.evaluate(t); return a.get('grand')
    except Exception as e: return f'{type(e).__name__}: {e}'

print('--- T5a Alice changes the column formula; Bob adds rows the new formula ---')
print('    treats differently. Both clean.')
ALICE = BASE.replace('total = qty * unit', 'total = qty * unit * 1.2')   # add VAT
BOB   = BASE.replace('| r_0004 | flange   |   5 | 24.00 |                    |\n',
                     '| r_0004 | flange   |   5 | 24.00 |                    |\n'
                     '| r_0005 | zerorate |  10 | 30.00 |                    |\n')
rc, txt, n = git_merge(BASE, ALICE, BOB, 'b.tbl')
print(f'  git merge exit={rc} ({"CLEAN" if rc==0 else "CONFLICT"}) markers={n}  '
      f'grand={q(txt)}')
print('  Bob\'s zero-rated line item silently acquires 20% VAT. Legitimate mechanically;')
print('  no representation can catch it. Ranked (c), noted for completeness.')

print()
print('--- T5b two branches edit the SAME column formula ---')
A2 = BASE.replace('total = qty * unit', 'total = qty * unit * 1.2')
B2 = BASE.replace('total = qty * unit', 'total = qty * unit - 5')
rc, txt, n = git_merge(BASE, A2, B2, 'b.tbl')
print(f'  git merge exit={rc} markers={n}  <-- same line: HELD (legitimate conflict)')

print()
print('--- T5c an aggregate over a column DELETED on the other branch ---')
DEL = '\n'.join(l if not l.startswith('|') else '|'.join(l.split('|')[:4] + l.split('|')[5:])
                for l in BASE.splitlines()) + '\n'
print(f'  Alice deletes the `unit` column entirely. header now: {DEL.splitlines()[0]!r}')
BOB2 = BASE.replace('| r_0001 | widget   |  10 |', '| r_0001 | widget   |  11 |')
rc, txt, n = git_merge(BASE, DEL, BOB2, 'b.tbl')
print(f'  git merge exit={rc} markers={n}')
print(f'  evaluated: {q(txt)}')
print()
EXTRA = BASE.replace('grand := sum(total)', 'grand := sum(total)\nunits := sum(unit)')
rc, txt, n = git_merge(BASE, DEL, EXTRA, 'b.tbl')
print(f'  Alice deletes `unit`; Bob adds `units := sum(unit)` on a separate line:')
print(f'  git merge exit={rc} markers={n}')
try:
    r, a = tbl.evaluate(txt); print(f'  evaluated: {a}')
except Exception as e:
    print(f'  raised {type(e).__name__}: {e}   <-- crash, not a #REF!. Loud but not I3-shaped.')

print()
print('--- T5d a formula referencing a column added ONLY on the other branch ---')
A3 = BASE.replace('| total = qty * unit |', '| total = qty * unit * disc |')
B3 = BASE.replace('grand := sum(total)', 'grand := sum(total)')  # Bob does nothing relevant
rc, txt, n = git_merge(BASE, A3, B3, 'b.tbl')
print(f'  git merge exit={rc} markers={n}  evaluated grand = {q(txt)!r}')
print('  ==> #REF! propagates. I3 HELD.')

print()
print('--- T5e blank vs zero vs missing ---')
for label, cell in [('blank', '     '), ('zero', '  0  '), ('dash', '  -  '),
                    ('N/A', ' N/A '), ('missing field', None)]:
    if cell is None:
        t = BASE.replace('| r_0002 | gadget   |  20 |  6.00 |                    |',
                         '| r_0002 | gadget   |  20 |')
    else:
        t = BASE.replace('| r_0002 | gadget   |  20 |  6.00 |',
                         f'| r_0002 | gadget   |  20 |{cell}|')
    print(f'  {label:14s} -> grand = {q(t)!r}')
print('  blank/missing -> #REF! (loud, correct). "-" and "N/A" -> hard crash, not a')
print('  #REF! object, so the error does NOT propagate the way I3 specifies; it')
print('  aborts the whole evaluation including unrelated aggregates.')
