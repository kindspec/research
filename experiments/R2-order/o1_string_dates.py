#!/usr/bin/env python3
"""O1: `order := by(date)` -- the design's own example -- with DATES.

otbl sorts with:
    try:    (0, float(r[order]), str(r.get(key,'')))
    except: (1, 0.0, str(r[order]) + str(r.get(key,'')))

Any real date is not a float, so EVERY date table lands in the second branch,
which is a *lexicographic string* sort of the CONCATENATION of order value and
row id. Two consequences below.
"""
import otbl, gw

BASE = """| id     | date       | amount | balance = cumulative(amount) |
| ------ | ---------- | -----: | ---------------------------: |
| r_0001 | 2026-01-15 | 100.00 |                              |
| r_0003 | 2026-03-01 |  40.00 |                              |

key   := id
order := by(date)
low   := min(balance)
final := max(balance)
"""

print('--- O1a a hand-typed unpadded month: 2026-2-1 (1 Feb) ---')
ALICE = gw.ins(BASE, 'r_0001', '| r_0002 | 2026-2-1   | -95.00 |                              |')
rows, aggs = otbl.evaluate(ALICE)
print('   declared order actually used:', [r['date'] for r in rows])
print('   balances                    :', [r['balance'] for r in rows])
print('   evaluated                   :', aggs)
print('   TRUTH (Jan 15, Feb 1, Mar 1):  100.00, 5.00, 45.00  -> low = 5.0')
print('   otbl says low =', aggs['low'], '  <-- the 1 Feb row is sorted LAST')
print('   the file is accepted, no error, no #REF!, no warning.')

print()
print('--- O1b the same defect arriving through a CLEAN stock-git merge ---')
BOB = gw.ins(BASE, 'r_0003', '| r_0004 | 2026-04-01 |  10.00 |                              |')
rc, mk, merged = gw.merge(BASE, ALICE, BOB)
print(f'   git merge exit={rc} markers={mk}')
rows, aggs = otbl.evaluate(merged)
print('   order used:', [r['date'] for r in rows])
print('   merged low =', aggs['low'], ' truth = 5.0  (overdraft check reads high)')

print()
print('--- O1c the row id leaks INTO the order: two DIFFERENT dates ---')
# concatenation, not a tuple: order value "b" + id "a1" == "ba1"
#                             order value "ba" + id "0"  == "ba0"  -> sorts FIRST
NAMES = """| id     | name | pay  | run = cumulative(pay) |
| ------ | ---- | ---: | --------------------: |
| r_0001 | Ann  | 10.0 |                       |
| a_0002 | Anna | 20.0 |                       |

key   := id
order := by(name)
first := min(run)
"""
rows, aggs = otbl.evaluate(NAMES)
print('   order := by(name); "Ann" < "Anna" in every collation on earth.')
print('   otbl order:', [r['name'] for r in rows], ' <-- Anna first')
print('   because the sort key is the STRING "Ann"+"r_0001" vs "Anna"+"a_0002"')
print('      "Annr_0001"  vs  "Annaa_0002"   ->  "Anna..." < "Annr..."')
print('   change ONE opaque row id and the ORDER OF A DIFFERENT ROW changes:')
FIX = NAMES.replace('r_0001', '0001')
rows2, _ = otbl.evaluate(FIX)
print("   re-mint Ann's id r_0001 -> 0001:", [r['name'] for r in rows2], ' <-- order flips')
print('   the row id is documented as "machine-managed noise, not an address".')
print('   here it is a load-bearing input to the computed row order.')
