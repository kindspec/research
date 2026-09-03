#!/usr/bin/env python3
"""T1: the .tbl AGGREGATE namespace is SCATTERED, exactly like markdown link labels.

PASS4 held the table format up as the SAFE contrast to markdown's scattered
namespace, because "column names are all declared on ONE line". Aggregates are
NOT. They are one per line in a trailing block.
"""
import sys, os, re
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'R1-common'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'L1-nominal-merge'))
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
count := count(id)
"""

# Alice adds a "subtotal" aggregate near the top of the trailing block.
OURS = BASE.replace("key   := id\n", "key   := id\nsubtotal := sum(qty)\n")
# Bob adds a "subtotal" aggregate at the bottom. Different LINE, same NAME.
THEIRS = BASE.replace("count := count(id)\n", "count := count(id)\nsubtotal := sum(total)\n")

rc, txt, n = git_merge(BASE, OURS, THEIRS, 'b.tbl')
print('--- T1a duplicate AGGREGATE name, added at different offsets ---')
print(f'git merge exit={rc} ({"CLEAN" if rc==0 else "CONFLICT"}) markers={n}')
print('merged trailing block:')
for l in txt.splitlines():
    if ':=' in l: print('   ', l)
rows, aggs = tbl.evaluate(txt)
print('evaluated:', {k: v for k, v in aggs.items()})
print(f'Alice meant subtotal=sum(qty)={sum(float(r["qty"]) for r in rows)}; '
      f'Bob meant subtotal=sum(total)={aggs["grand"]}')
print(f'RESULT: subtotal = {aggs.get("subtotal")}  -- one author silently lost, no marker')

print()
print('--- T1b same, but the two names differ only by UNICODE NORMALISATION ---')
NFC = 'café'          # café  (U+00E9)
NFD = 'café'         # café  (e + U+0301)
print(f'  NFC bytes={NFC.encode()!r}  NFD bytes={NFD.encode()!r}  equal={NFC==NFD}  look identical: {NFC} vs {NFD}')
O2 = BASE.replace("key   := id\n", f"key   := id\n{NFC} := sum(qty)\n")
T2 = BASE.replace("count := count(id)\n", f"count := count(id)\n{NFD} := sum(total)\n")
rc2, txt2, n2 = git_merge(BASE, O2, T2, 'b.tbl')
print(f'git merge exit={rc2} ({"CLEAN" if rc2==0 else "CONFLICT"}) markers={n2}')
rows2, aggs2 = tbl.evaluate(txt2)
print('  BOTH declarations are in the merged file:',
      [l for l in txt2.splitlines() if ':=' in l and 'caf' in l])
print('  aggregate names the PARSER produced:', [ascii(k) for k in aggs2])
print('  Bob (NFD) line matched the aggregate regex:',
      bool(re.match(r'\s*(\w+)\s*:=\s*(\w+)\(', NFD + ' := sum(total)')))
print('  ==> the NFD declaration is SILENTLY SKIPPED (regex \\w does not match the')
print('      combining mark), and the NFC one answers to a name that RENDERS IDENTICALLY.')
print('  evaluated:', {ascii(k): v for k, v in aggs2.items()})

print()
print('--- T1c duplicate COLUMN name via unicode normalisation (header IS co-located) ---')
def addcol(t, name, tag):
    L = []
    for i, l in enumerate(t.splitlines()):
        if not l.startswith('|'): L.append(l)
        elif i == 0: L.append(l + f' {name} |')
        elif i == 1: L.append(l + ' ---- |')
        else: L.append(l + f' {tag}{i} |')
    return '\n'.join(L) + '\n'
rc3, txt3, n3 = git_merge(BASE, addcol(BASE, NFC, 'A'), addcol(BASE, NFD, 'B'), 'b.tbl')
print(f'git merge exit={rc3} ({"CLEAN" if rc3==0 else "CONFLICT"}) markers={n3}  '
      f'-- co-located header saves it')
