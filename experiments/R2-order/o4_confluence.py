#!/usr/bin/env python3
"""O4: the suite's ONE confluence case passes for the wrong reason.

conformance/cases.py CONFLUENCE uses LEDGER, whose aggregate is
`final := max(balance)` over amounts 100, -30, 50 plus three positive inserts.
max(cumulative) with a positive grand total is just sum(), which is
commutative -- so that case is confluent whatever the ordering mechanism does.
It cannot distinguish a working implementation from one that ignores order.
"""
import itertools, otbl, gw
from copy import copy

LEDGER = """| id     | date | amount | balance = cumulative(amount) |
| ------ | ---: | -----: | ---------------------------: |
| r_0001 |    1 | 100.00 |                              |
| r_0002 |    3 | -30.00 |                              |
| r_0003 |    5 |  50.00 |                              |

key   := id
order := by(date)
final := max(balance)
"""
BRANCHES = [
  gw.ins(LEDGER, 'r_0001', '| r_0005 |    2 |  11.00 |                              |'),
  gw.ins(LEDGER, 'r_0003', '| r_0006 |    6 |   7.00 |                              |'),
  gw.ins(LEDGER, 'r_0002', '| r_0009 |    4 |   1.00 |                              |'),
]
print('--- O4a the suite case, but with the ordering mechanism DISABLED ---')
import re
src = open('otbl.py').read()
open('noorder_impl.py','w').write(src.replace('seq = sorted(rows, key=sortkey)', 'seq = rows'))
import noorder_impl
res_real, res_broken = set(), set()
for o in itertools.permutations(range(3)):
    st, m = gw.mergeN(LEDGER, BRANCHES, o)
    res_real.add(tuple(sorted(otbl.evaluate(m)[1].items())))
    res_broken.add(tuple(sorted(noorder_impl.evaluate(m)[1].items())))
print('   reference impl        :', res_real, f'({len(res_real)} outcome)')
print('   `ignore-declared-order`:', res_broken, f'({len(res_broken)} outcome)')
print('   The confluence case is GREEN for an implementation that never sorts.')

print()
print('--- O4b the same three branches with a NON-commutative aggregate ---')
L2 = LEDGER.replace('final := max(balance)', 'low := min(balance)')
L2 = L2.replace('| 100.00 |', '|  10.00 |').replace('| -30.00 |', '| -60.00 |')
B2 = [b.replace('final := max(balance)', 'low := min(balance)')
       .replace('| 100.00 |', '|  10.00 |').replace('| -30.00 |', '| -60.00 |') for b in BRANCHES]
outs = {}
for o in itertools.permutations(range(3)):
    st, m = gw.mergeN(L2, B2, o)
    outs[o] = (st, None if m is None else otbl.evaluate(m)[1])
for o, v in outs.items(): print('   ', o, v)
print('   distinct:', len({str(v) for v in outs.values()}))
