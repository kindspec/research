#!/usr/bin/env python3
"""O3: what if the order column is itself COMPUTED, contains nan, or vanishes?

evaluate() sorts BEFORE it evaluates any column formula:

    seq = sorted(rows, key=sortkey)          # <- uses the RAW cell text
    for r in seq: ... r[nm] = ev(...)        # <- formulas computed after

So `order := by(<a computed column>)` sorts on the blank cells.
"""
import otbl, gw

print('--- O3a order := by(<computed column>) : sorts on BLANK cells ---')
T = """| id     | day | seq = day * 1 | amount | run = cumulative(amount) |
| ------ | --: | ------------: | -----: | -----------------------: |
| r_0003 |   9 |               |  -5.00 |                          |
| r_0001 |   1 |         100.00|        |                          |
| r_0002 |   5 |               | -90.00 |                          |

key   := id
order := by(seq)
low   := min(run)
"""
T = T.replace('|         100.00|', '|               |').replace('|        |', '| 100.00 |')
r, a = otbl.evaluate(T)
print('   parse ACCEPTED. `order := by(seq)` where seq is computed.')
print('   derived order:', [(x['id'], x['day'], x['seq']) for x in r])
print('   low =', a['low'], ' -- rows are in id order (r_0001,r_0002,r_0003),')
print('   NOT seq order, because every seq cell was blank when sorting happened.')
print('   Here id order and seq order agree by luck. Re-mint one id and they do not:')
T2 = T.replace('r_0003', 'a_0003')
r2, a2 = otbl.evaluate(T2)
print('   after re-minting r_0003 -> a_0003:', [(x['id'], x['day']) for x in r2],
      ' low =', a2['low'])
print('   No error. `order := by(seq)` is silently `order := by(id)`.')

print()
print('--- O3b nan in a NUMERIC order column destroys the total order ---')
N = """| id     | day  | amount | run = cumulative(amount) |
| ------ | ---: | -----: | -----------------------: |
| r_0001 |    1 | 100.00 |                          |
| r_0002 |  nan | -90.00 |                          |
| r_0003 |    5 |  50.00 |                          |
| r_0004 |    9 |   1.00 |                          |

key   := id
order := by(day)
low   := min(run)
"""
r, a = otbl.evaluate(N)
print("   float('nan') is accepted by the order key. derived order:",
      [x['id'] for x in r], ' low =', a['low'])
Nshuf = '\n'.join([N.splitlines()[0], N.splitlines()[1], N.splitlines()[4],
                   N.splitlines()[3], N.splitlines()[2], N.splitlines()[5]] +
                  N.splitlines()[6:]) + '\n'
r2, a2 = otbl.evaluate(Nshuf)
print('   the SAME rows, physically reordered in the file:',
      [x['id'] for x in r2], ' low =', a2['low'])
print('   nan compares false against everything, so sorted() is not sorting:')
print('   physical position decides again, silently. Same for `inf`, `1_000`,')
print("   and fullwidth digits -- all accepted by float().")

print()
print('--- O3c the order column DELETED, with no row-relative column ---')
D = """| id     | day | amount |
| ------ | --: | -----: |
| r_0001 |   1 | 100.00 |

key   := id
order := by(nope)
total := sum(amount)
"""
try:
    otbl.evaluate(D); print('   accepted')
except otbl.Malformed as e: print('   REFUSED (good):', e)
except Exception as e:
    print(f'   *** UNHANDLED {type(e).__name__}: {e}')
    print('   the `order not in cols` guard sits INSIDE the loop over row-relative')
    print('   formulas, so a table with none is never checked, and sortkey()')
    print('   catches only ValueError/TypeError -- a KeyError escapes as a crash.')
    print('   I5/I3: a valid-looking artifact aborts the whole evaluation.')
