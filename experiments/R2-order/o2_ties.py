#!/usr/bin/env python3
"""O2: ties in the order key.

The tiebreak is documented as (order key, row id) -- "so ties are resolved
deterministically and confluence holds". But `key := <col>` is OPTIONAL:
nothing in parse() requires it when `order := by(<col>)` is declared, and no
conformance case requires it. With no key, sortkey() calls r.get(None, '')
== '' for every row, every tie is UNBROKEN, and Python's stable sort falls
back to PHYSICAL FILE ORDER.
"""
import otbl, gw

BASE = """| id     | day | amount | run = cumulative(amount) |
| ------ | --: | -----: | -----------------------: |
| r_0001 |   1 | 100.00 |                          |
| r_0005 |   5 |  50.00 |                          |
| r_0009 |   9 |  10.00 |                          |
| r_0010 |  10 |   1.00 |                          |
| r_0011 |  11 |   1.00 |                          |
| r_0012 |  12 |   1.00 |                          |
| r_0013 |  13 |   2.00 |                          |

order := by(day)
low   := min(run)
"""
print('--- O2a "physically shuffling every row gives IDENTICAL results" (X1 claim 2) ---')
SHUF = """| id     | day | amount | run = cumulative(amount) |
| ------ | --: | -----: | -----------------------: |
| r_0005 |   5 |  50.00 |                          |
| r_0009 |   9 |  10.00 |                          |
| r_0010 |  10 |   1.00 |                          |
| r_0011 |  11 |   1.00 |                          |
| r_0012 |  12 |   1.00 |                          |
| r_0013 |  13 |   2.00 |                          |
| r_0001 |   1 | 100.00 |                          |

order := by(day)
low   := min(run)
"""
for nm, t in (('as written', BASE), ('rows shuffled', SHUF)):
    r, a = otbl.evaluate(t); print(f'   {nm:14} {[x["id"] for x in r]}  low={a["low"]}')
print('   (no ties yet: the claim holds)')

print()
print('--- O2b now add ONE row that ties on `day` with an existing row ---')
TIE = '| r_0006 |   5 | -140.00 |                          |'
A = gw.ins(BASE, 'r_0001', TIE)     # Alice pastes it above the tied row
B = gw.ins(BASE, 'r_0005', TIE)     # ...or below it. Same logical content.
for nm, t in (('pasted above', A), ('pasted below', B)):
    r, a = otbl.evaluate(t)
    print(f'   {nm:14} order={[x["id"] for x in r]}  runs={[x["run"] for x in r]}  low={a["low"]}')
print('   Two files with the IDENTICAL SET OF ROWS and the identical declared')
print('   order evaluate to different answers. Insertion point is load-bearing.')

print()
print('--- O2c and it arrives through a clean stock-git merge ---')
BOB = BASE.replace('| r_0013 |  13 |   2.00 |', '| r_0013 |  13 |   3.00 |')   # distant cell edit
for nm, ours in (('Alice pasted above', A), ('Alice pasted below', B)):
    rc, mk, merged = gw.merge(BASE, ours, BOB)
    r, a = otbl.evaluate(merged)
    print(f'   {nm:20} git exit={rc} markers={mk}  low={a["low"]}')
print('   Same base, same two edits, same declared order, two answers.')

print()
print('--- O2d WITH `key := id` the tie is broken -- by a STRING sort of opaque ids ---')
KEYED = """| id    | day | amount | run = cumulative(amount) |
| ----- | --: | -----: | -----------------------: |
| r_9   |   5 | -90.00 |                          |
| r_10  |   5 |  50.00 |                          |

key   := id
order := by(day)
low   := min(run)
"""
r, a = otbl.evaluate(KEYED)
print('   ids r_9, r_10 on the same day. derived order:', [x['id'] for x in r], ' low =', a['low'])
print('   "r_10" < "r_9" as strings. Deterministic, confluent, and decided by a')
print('   value the design calls "machine-managed noise, not an address".')
