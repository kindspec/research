#!/usr/bin/env python3
"""A surviving mutant is only a hole if it is a REAL behaviour change.
For each survivor, a plausible input on which the reference and the mutant
disagree -- i.e. the case the suite is missing, written out."""
import importlib, subprocess, sys, os
import ref_tbl as R
from new_mutants import MUTANTS

def with_mutant(name):
    old, new = MUTANTS[name]
    src = open('ref_tbl.py').read()
    assert old in src, name
    mod = 'mut_' + ''.join(ch if ch.isalnum() else '_' for ch in name)
    open(mod + '.py','w').write(src.replace(old, new, 1))
    importlib.invalidate_caches()
    m = importlib.import_module(mod)
    os.remove(mod + '.py')
    return m

TIE = """| id    | day | amount | run = cumulative(amount) |
| ----- | --: | -----: | -----------------------: |
| r_2   |   5 | -90.00 |                          |
| r_1   |   5 |  50.00 |                          |

key   := id
order := by(day)
low   := min(run)
"""
DATES = """| id     | date       | amount | run = cumulative(amount) |
| ------ | ---------- | -----: | -----------------------: |
| r_0001 | 2026-03-01 | -90.00 |                          |
| r_0002 | 2026-01-01 | 100.00 |                          |

key   := id
order := by(date)
low   := min(run)
"""
PRIOR = """| id     | day | v    | p = prior(v) | d = delta(v) |
| ------ | --: | ---: | -----------: | -----------: |
| r_0001 |   1 |  5.0 |              |              |
| r_0002 |   2 |  9.0 |              |              |
| r_0003 |   3 |  2.0 |              |              |

key   := id
order := by(day)
mp := max(p)
md := max(d)
"""
COUNT = """| id     | x |
| ------ | -: |
| r_0001 |  1 |
| r_0002 |    |

key := id
n := count(x)
s := sum(x)
"""
UNKNOWN = """| id     | x |
| ------ | -: |
| r_0001 |  4 |
| r_0002 |  6 |

key := id
avg := mean(x)
"""
BLANK = """| id     | qty | unit  | total = qty * unit |
| ------ | --: | ----: | -----------------: |
| r_0001 |  10 | 12.00 |                    |
| r_0002 |  20 |       |                    |

key   := id
grand := sum(total)
"""
COMMA = """| id     | qty | unit     | total = qty * unit |
| ------ | --: | -------: | -----------------: |
| r_0001 |   2 | 1,500.00 |                    |

key   := id
grand := sum(total)
"""
NBSP = "| id     | qty | unit  | total = qty * unit |\n" \
       "| ------ | --: | ----: | -----------------: |\n" \
       "| r_0001 |  10 | 12.00 |                    |\n\nkey   := id\ngrand := sum(total)\n"
CHAIN = """| id     | qty | unit  | gross = net * 1.2 | net = qty * unit |
| ------ | --: | ----: | ----------------: | ---------------: |
| r_0001 |  10 | 12.00 |                   |                  |

key   := id
g := sum(gross)
"""
DUPORDER = """| id     | a | b | r = cumulative(a) |
| ------ | -: | -: | ---------------: |
| r_0001 |  1 |  9 |                  |
| r_0002 |  2 |  1 |                  |

key   := id
order := by(a)
order := by(b)
m := min(r)
"""
NONE = """| id     | a | r = cumulative(a) |
| ------ | -: | ---------------: |
| r_0001 |  1 |                  |

key   := id
order := none()
m := min(r)
"""
DASH = """| id     | item | qty | unit | total = qty * unit |
| ------ | ---- | --: | ---: | -----------------: |
| r_0001 | ok   |  10 |    2 |                    |
| r_0002 | ---  |   5 |    3 |                    |

key   := id
grand := sum(total)
"""

PROBES = [
 ('no-tiebreak-at-all',                 TIE,     'low'),
 ('tiebreak-reversed',                  TIE,     'low'),
 ('non-numeric-order-sorts-by-id-only', DATES,   'low'),
 ('prior-always-blank',                 PRIOR,   'mp'),
 ('delta-first-row-is-the-value',       PRIOR,   'md'),
 ('delta-is-negated',                   PRIOR,   'md'),
 ('count-off-by-one',                   COUNT,   'n'),
 ('count-ignores-blanks',               COUNT,   'n'),
 ('unknown-aggregate-function-silently-becomes-sum', UNKNOWN, 'avg'),
 ('sum-crashes-on-a-blank-cell',        COUNT,   's'),
 ('blank-cell-in-a-real-column-is-zero',BLANK,   'grand'),
 ('float-accepts-thousands-separators', COMMA,   'grand'),
 ('strip-only-ascii-spaces',            NBSP,    'grand'),
 ('computed-columns-evaluated-in-reverse-header-order', CHAIN, 'g'),
 ('allow-duplicate-order-declaration',  DUPORDER,'m'),
 ('order-none-is-ignored',              NONE,    'm'),
 ('is-align-matches-any-dashed-cell',   DASH,    'grand'),
]
def run(mod, t, k):
    try: return mod.evaluate(t)[1].get(k)
    except mod.Malformed as e: return f'REFUSED: {str(e)[:40]}'
    except Exception as e: return f'{type(e).__name__}: {str(e)[:40]}'

print(f"{'mutant':52} {'reference':>26} {'mutant':>26}  differ")
print('-'*112)
n = 0
for name, t, k in PROBES:
    m = with_mutant(name)
    a, b = run(R, t, k), run(m, t, k)
    d = a != b; n += d
    print(f'{name:52} {str(a):>26} {str(b):>26}  {"YES" if d else "no"}')
subprocess.run(['rm','-rf','__pycache__'])
print('-'*112)
print(f'{n}/{len(PROBES)} surviving mutants demonstrably change an answer on a plausible input.')
