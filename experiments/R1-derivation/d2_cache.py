#!/usr/bin/env python3
"""D2: the content-addressed cache is keyed on ONE artifact's bytes, so a
cross-artifact dependency never invalidates it. L5 claims "invalidation is
exact"."""
import os, shutil, tempfile, sys
H = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, H)
import derive2

d = tempfile.mkdtemp(); os.chdir(d)
RATE = """| id     | item | pct |
| ------ | ---- | --: |
| r_0001 | vat  |  20 |

key := id
rate := sum(pct)
"""
BUDGET = """| id     | item   | qty | unit  | net = qty * unit | total = net * {{ rates.tbl#rate }} |
| ------ | ------ | --: | ----: | ---------------: | ---------------------------------: |
| r_0001 | widget |  10 | 12.00 |                  |                                    |

key   := id
grand := sum(total)
"""
open('rates.tbl','w').write(RATE); open('budget.tbl','w').write(BUDGET)
st = {'hit':0,'miss':0}
print('  first evaluation      : grand =', derive2.value('budget.tbl','grand',st), f'  {st}')

# The VAT rate changes. rates.tbl is edited. budget.tbl is untouched.
open('rates.tbl','w').write(RATE.replace('|  20 |','|  25 |'))
st = {'hit':0,'miss':0}
print('  after rates.tbl 20->25: grand =', derive2.value('budget.tbl','grand',st), f'  {st}')
print('  truth: 10 * 12.00 * 25 = 3000.00')
print('  ==> CACHE HIT on a stale key. The cache key hashes budget.tbl only.')
print('      "Invalidation is exact" is true only for single-artifact derivations.')

print()
print('--- D2b a cycle across two artifacts ---')
shutil.rmtree('.gws-cache', ignore_errors=True)
open('a.tbl','w').write("""| id     | x | y = x * {{ b.tbl#bv }} |
| ------ | -: | --------------------: |
| r_0001 | 2 |                       |

av := sum(y)
""")
open('b.tbl','w').write("""| id     | x | y = x * {{ a.tbl#av }} |
| ------ | -: | --------------------: |
| r_0001 | 3 |                       |

bv := sum(y)
""")
st = {'hit':0,'miss':0}
try:
    print('  a.tbl#av =', derive2.value('a.tbl','av',st))
except RecursionError as e: print('  RecursionError (LOUD, held):', e)
except RecursionError: pass

print()
print("--- D2c NEGATIVE RESULT: I could not turn the cycle into a silent fixed point.")
print("    With this cache key (artifact bytes) every cycle member misses on first")
print("    visit, so the stack check fires. HELD.")
print(f'  workdir: {d}')
