#!/usr/bin/env python3
"""T3: the grammar has NO ESCAPING RULE, so one cell containing a pipe shifts
every field to its left and the arithmetic silently changes."""
import sys, os
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(H,'..','R1-common'), os.path.join(H,'..','L1-nominal-merge')]
from gw import git_merge
import tbl

BASE = """| id     | item     | qty | unit  | total = qty * unit |
| ------ | -------- | --: | ----: | -----------------: |
| r_0001 | widget   |  10 | 12.00 |                    |
| r_0002 | gadget   |  20 |  6.00 |                    |

key   := id
grand := sum(total)
"""
print('--- T3a a product code containing a pipe ---')
# The item is literally called "10|12" (a part number). Nothing exotic.
BAD = BASE.replace('| r_0002 | gadget   |  20 |  6.00 |',
                   '| r_0002 | 10|12    |   3 |  8.00 |')
rows, aggs = tbl.evaluate(BAD)
print('  source row      : | r_0002 | 10|12    |   3 |  8.00 |     (qty 3 @ 8.00 = 24)')
print('  parsed row      :', rows[1])
print(f'  grand           : {aggs["grand"]}   (truth: 120 + 24 = 144)')
print('  ==> no exception, no marker. Fields shifted left by one; qty became 12,')
print('      unit became 3. GFM allows backslash-pipe escaping; this grammar')
print('      defines none and the reference parser implements none.')

print()
print('--- T3b the same defect arriving through a CLEAN stock-git merge ---')
# Alice renames the item to include a pipe (one line). Bob edits the other row.
WIDE = BASE.replace('| r_0002 | gadget   |  20 |  6.00 |                    |\n',
    '| r_0002 | gadget   |  20 |  6.00 |                    |\n'
    + ''.join(f'| r_{i:04d} | pad{i:03d}   |   1 |  0.00 |                    |\n'
              for i in range(100, 110)))
O = WIDE.replace('| r_0002 | gadget   |  20 |  6.00 |',
                 '| r_0002 | 10|12    |  20 |  6.00 |')
T = WIDE.replace('| r_0109 | pad109   |   1 |', '| r_0109 | pad109   |   2 |')
rc, txt, n = git_merge(WIDE, O, T, 'b.tbl')
rows, aggs = tbl.evaluate(txt)
print(f'  git merge exit={rc} markers={n}')
print(f'  grand = {aggs["grand"]}   (truth: 120 + 120 + 0 = 240)')
print('  ==> Alice only renamed an ITEM. The merge is clean, the file looks fine,')
print('      and the total is wrong by', aggs["grand"] - 240)

print()
print('--- T3c a row that loses its leading pipe is SILENTLY SKIPPED (I7 violation) ---')
NOPIPE = BASE.replace('| r_0002 | gadget   |  20 |  6.00 |                    |',
                      '  r_0002 | gadget   |  20 |  6.00 |                    |')
rows, aggs = tbl.evaluate(NOPIPE)
print(f'  rows parsed = {len(rows)}  grand = {aggs["grand"]}   (truth: 240)')
print('  ==> tbl.parse keeps only lines starting with "|". Everything else is')
print('      DISCARDED without error. I7 says "unknown lines inside a known')
print('      structure -> error, not skip". The parser skips.')

print()
print('--- T3d prose accidentally left inside the table is skipped, too ---')
PROSE = BASE.replace('| r_0002 | gadget   |  20 |',
                     'TODO check this figure with finance\n| r_0002 | gadget   |  20 |')
rows, aggs = tbl.evaluate(PROSE)
print(f'  rows={len(rows)} grand={aggs["grand"]}  exception raised: no')

print()
print('--- T3e a SECOND table in the same file is absorbed as data rows ---')
TWO = BASE + """
| id     | item   | qty | unit  | total = qty * unit |
| ------ | ------ | --: | ----: | -----------------: |
| s_0001 | cog    |   4 | 25.00 |                    |
"""
try:
    rows, aggs = tbl.evaluate(TWO)
    print(f'  rows={len(rows)} grand={aggs["grand"]}')
    for r in rows: print('   ', r)
except Exception as e:
    print(f'  raised {type(e).__name__}: {e}   <-- loud, held')
