#!/usr/bin/env python3
"""T2: row identity. Opaque ids do not survive copy-paste, unicode, or
invisible characters -- and the entity-map merger silently drops rows."""
import sys, os, unicodedata
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(H,'..','R1-common'), os.path.join(H,'..','L1-nominal-merge')]
from gw import git_merge
import tbl, merge3

BASE = """| id     | item     | qty | unit  | total = qty * unit |
| ------ | -------- | --: | ----: | -----------------: |
| r_0001 | widget   |  10 | 12.00 |                    |
| r_0002 | gadget   |  20 |  6.00 |                    |
| r_0003 | sprocket |   8 | 15.00 |                    |
| r_0004 | flange   |   5 | 24.00 |                    |

key   := id
grand := sum(total)
"""

print('--- T2a copy-paste duplicates a row id, then the two copies diverge ---')
# Alice duplicates r_0002 (copy-paste in an editor keeps the id) and edits the copy.
OURS = BASE.replace('| r_0002 | gadget   |  20 |  6.00 |                    |\n',
                    '| r_0002 | gadget   |  20 |  6.00 |                    |\n'
                    '| r_0002 | gadget2  |  30 |  6.00 |                    |\n')
# Bob, far away, edits flange qty.
THEIRS = BASE.replace('| r_0004 | flange   |   5 |', '| r_0004 | flange   |   6 |')
rc, txt, n = git_merge(BASE, OURS, THEIRS, 'b.tbl')
rows, aggs = tbl.evaluate(txt)
print(f'stock git: exit={rc} markers={n}  rows={len(rows)}  grand={aggs["grand"]}')
print(f'  ids in merged file: {[r["id"] for r in rows]}   <-- r_0002 twice, no complaint')
print(f'  tbl.evaluate raises on duplicate COLUMN names but not duplicate ROW ids: '
      f'no exception raised')
# now the type-aware merge, which the design says is the accelerator
out, cf = merge3.merge3(BASE, OURS, THEIRS)
r2, a2 = tbl.evaluate(out)
print(f'entity-map merge3: conflicts={len(cf)}  rows={len(r2)}  grand={a2["grand"]}')
print(f'  ids: {[r["id"] for r in r2]}')
print(f'  ==> merge3 keyed rows by id, so dict(entities) kept only the LAST r_0002;')
print(f'      BOTH r_0002 rows then rendered with qty=30. The original gadget row was')
print(f'      silently REWRITTEN. stock git={aggs["grand"]} (correct), '
      f'merge3={a2["grand"]} (wrong by {a2["grand"]-aggs["grand"]}), 0 conflicts either way.')

print()
print('--- T2b two branches independently add a row, id generator collides ---')
O = BASE.replace('| r_0004 | flange   |   5 | 24.00 |                    |\n',
                 '| r_0004 | flange   |   5 | 24.00 |                    |\n'
                 '| r_0005 | bolt     |  10 |  8.00 |                    |\n')
T = BASE.replace('| r_0001 | widget   |  10 | 12.00 |                    |\n',
                 '| r_0005 | cog      |   4 | 25.00 |                    |\n'
                 '| r_0001 | widget   |  10 | 12.00 |                    |\n')
rc, txt, n = git_merge(BASE, O, T, 'b.tbl')
rows, aggs = tbl.evaluate(txt)
print(f'stock git: exit={rc} markers={n} rows={len(rows)} grand={aggs["grand"]} '
      f'ids={[r["id"] for r in rows]}')
out, cf = merge3.merge3(BASE, O, T)
r2, a2 = tbl.evaluate(out)
print(f'merge3   : conflicts={len(cf)} rows={len(r2)} grand={a2["grand"]} '
      f'ids={[r["id"] for r in r2]}')
print(f'  ==> stock git keeps both (grand={aggs["grand"]}), merge3 keeps one '
      f'(grand={a2["grand"]}). Both CLEAN. They DISAGREE by {aggs["grand"]-a2["grand"]}.')

print()
print('--- T2c an invisible character splits one row into two ---')
ZWSP = '\u200b'
print(f'  str.strip() removes NBSP  : {("r_0002\u00a0").strip() == "r_0002"}')
print(f'  str.strip() removes U+200B: {("r_0002"+ZWSP).strip() == "r_0002"}  <-- so two ids that')
print(f'  render identically compare UNEQUAL: {ascii(("r_0002"+ZWSP).strip())} != "r_0002"')
# Alice edits gadget qty 20 -> 25.
O = BASE.replace('| r_0002 | gadget   |  20 |', '| r_0002 | gadget   |  25 |')
# Bob edits the SAME row but re-typed/pasted the id with a zero-width space in it.
T = BASE.replace('| r_0002 | gadget   |  20 |', f'| r_0002{ZWSP} | gadget   |  40 |')
rc, txt, n = git_merge(BASE, O, T, 'b.tbl')
print(f'  stock git : exit={rc} markers={n}  <-- same line, so git DOES conflict (legit)')
out, cf = merge3.merge3(BASE, O, T)
r2, a2 = tbl.evaluate(out)
print(f'  merge3    : conflicts={len(cf)} rows={len(r2)} grand={a2["grand"]}')
print(f'  ids: {[ascii(r["id"]) for r in r2]}')
print(f'  ==> the type-aware merger sees a DELETE of r_0002 plus an ADD of r_0002<zwsp>.')
print(f'      Alice\'s edit (qty 25) is SILENTLY DROPPED; only Bob\'s row survives.')
print(f'      Stock git conflicted (correct: same row, two values). The "accelerator"')
print(f'      turned a legitimate conflict into a silent lost update. grand={a2["grand"]}.')
