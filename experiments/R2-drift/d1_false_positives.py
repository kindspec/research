#!/usr/bin/env python3
"""D1: FALSE POSITIVES in the meaning-drift detector.

Identity rests on a column's DEFINITION -- compared as TEXT, after a rename
substitution. Any edit to the text of a formula therefore "rebinds" the column,
and every unchanged reference to it FIRES.
"""
import drift

BASE = """| id     | qty | unit  | total = qty * unit | gross = total * 1.2 |
| ------ | --: | ----: | -----------------: | ------------------: |
| r_0001 |  10 | 12.00 |                    |                     |
| r_0002 |  20 |  6.00 |                    |                     |

key   := id
grand := sum(gross)
"""

CASES = [
 ('whitespace only:  `total * 1.2` -> `total*1.2`',
   BASE.replace('gross = total * 1.2', 'gross = total*1.2')),
 ('operand order:    `qty * unit` -> `unit * qty`  (identical value)',
   BASE.replace('total = qty * unit', 'total = unit * qty')),
 ('redundant parens: `total * 1.2` -> `(total) * 1.2`',
   BASE.replace('gross = total * 1.2', 'gross = (total) * 1.2')),
 ('a VAT rate change: 1.2 -> 1.25  (the most ordinary edit there is)',
   BASE.replace('gross = total * 1.2', 'gross = total * 1.25')),
 ('fixing a bug in a formula: `qty * unit` -> `qty * unit - 0`',
   BASE.replace('total = qty * unit', 'total = qty * unit - 0')),
]
for label, v2 in CASES:
    f, notes = drift.check(BASE, v2)
    print(f'--- {label}')
    print(f'    findings: {len(f)}   {"<-- FALSE POSITIVE" if f else "silent (correct)"}')
    for x in f: print('     ', x.splitlines()[0], '|', x.splitlines()[2].strip())

print()
print('--- a literal-column FALSE POSITIVE: copying one column onto another ---')
L = """| id     | qty | plan | actual |
| ------ | --: | ---: | -----: |
| r_0001 |  10 |    3 |      7 |
| r_0002 |  20 |    4 |      9 |

key   := id
t := sum(actual)
"""
# "make plan match what actually happened" -- an ordinary reconciliation edit
L2 = L.replace('|    3 |', '|    7 |').replace('|    4 |', '|    9 |')
f, n = drift.check(L, L2)
print(f'    findings: {len(f)}')
for x in f: print('     ', x.replace('\n', '\n      '))
