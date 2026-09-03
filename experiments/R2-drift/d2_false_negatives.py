#!/usr/bin/env python3
"""D2: FALSE NEGATIVES -- rebindings the drift detector does not catch."""
import drift, otbl

def report(label, v1, v2, aggname):
    f, notes = drift.check(v1, v2)
    a1 = otbl.evaluate(v1)[1].get(aggname); a2 = otbl.evaluate(v2)[1].get(aggname)
    print(f'--- {label}')
    print(f'    {aggname}: {a1}  ->  {a2}     drift findings: {len(f)}'
          f'   {"" if f else "<-- SILENT"}')
    for x in f: print('       ', x.splitlines()[0])
    print()

# --- N1 ---------------------------------------------------------------------
N1a = """| id     | qty | unit  | total = qty * unit |
| ------ | --: | ----: | -----------------: |
| r_0001 |  10 | 12.00 |                    |
| r_0002 |  20 |  6.00 |                    |

key   := id
grand := sum(total)
"""
N1b = """| id     | qty | price | unit | total = qty * unit |
| ------ | --: | ----: | ---: | -----------------: |
| r_0001 |  10 | 12.00 |    2 |                    |
| r_0002 |  20 |  6.00 |    3 |                    |

key   := id
grand := sum(total)
"""
report("N1 rename the literal column `unit` (a PRICE) to `price`, and give the\n"
       "       freed name `unit` to a NEW literal column (units per pack).\n"
       "       `total = qty * unit` and `grand := sum(total)` are UNTOUCHED.\n"
       "       This is R1's headline rename-swap, with LITERAL columns.",
       N1a, N1b, 'grand')

# --- N2 ---------------------------------------------------------------------
N2a = """| id     | qty | unit | rate = qty / unit |
| ------ | --: | ---: | ----------------: |
| r_0001 |  10 |    2 |                   |
| r_0002 |  20 |    5 |                   |

key   := id
avg := sum(rate)
"""
N2b = """| id     | unit | qty | rate = qty / unit |
| ------ | ---: | --: | ----------------: |
| r_0001 |   11 |   3 |                   |
| r_0002 |   21 |   6 |                   |

key   := id
avg := sum(rate)
"""
report("N2 swap two literal column NAMES *and* edit their data in one commit.\n"
       "       Definition-based identity sees nothing (no definition changed);\n"
       "       the value-vector permutation check sees nothing (no vector matches).",
       N2a, N2b, 'avg')

# --- N3 ---------------------------------------------------------------------
N3a = """| id     |  a |  b |  c | t = a - b |
| ------ | -: | -: | -: | --------: |
| r_0001 |  9 |  1 |  5 |           |
| r_0002 |  8 |  2 |  6 |           |

key := id
g := sum(t)
"""
N3b = N3a.replace('|  a |  b |  c |', '|  c |  a |  b |')
report("N3 three-way rename CYCLE a->b->c->a of literal columns, data untouched",
       N3a, N3b, 'g')

# --- N4 ---------------------------------------------------------------------
N4a = """| id     | day | seq | amount | run = cumulative(amount) |
| ------ | --: | --: | -----: | -----------------------: |
| r_0001 |   1 |   3 | 100.00 |                          |
| r_0002 |   3 |   1 | -90.00 |                          |
| r_0003 |   5 |   2 |  50.00 |                          |

key   := id
order := by(day)
low   := min(run)
"""
N4b = N4a.replace('order := by(day)', 'order := by(seq)')
report("N4 change `order := by(day)` to `order := by(seq)`.  Every row-relative\n"
       "       column now means something else and no formula text changed.",
       N4a, N4b, 'low')
print("    drift.defs() explicitly drops `order` and `key` from the reference set:")
print("        if name not in ('key','order'): refs[f'{name} :='] = ...")
print("    so the ONE declaration that defines row-relative meaning -- the whole")
print("    subject of mechanism 1 -- is never compared across versions.")
