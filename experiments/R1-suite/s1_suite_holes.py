#!/usr/bin/env python3
"""S1: attack the conformance suite. A suite is a claim about what cannot get
through. Here is what gets through."""
import sys, os, shutil, subprocess, tempfile
H = os.path.dirname(os.path.abspath(__file__))
L6 = os.path.join(H, '..', 'L6-conformance')

print('--- S1a the .tbl I1 round-trip test is a TAUTOLOGY ---')
print('  run_suite.py:')
print('      def tbl_parse(b):  cols,formulas,rows,aggs = tbl.parse(b); return b')
print('      def tbl_render(x): return x')
print('  conform.py then asserts  render(parse(doc)) == doc,  i.e.  doc == doc.')
print('  It can never fail, for any parser, for any corpus. The .tbl format has NO')
print('  round-trip coverage at all -- and I1 is the invariant the design says is')
print('  the whole point ("NOT as a coding guideline").')

print()
print('--- S1b: a deliberately broken .tbl parser passes the entire suite ---')
d = tempfile.mkdtemp()
shutil.copytree(L6, os.path.join(d, 'suite'))
sab = os.path.join(d, 'suite', 'tbl.py')
src = open(sab).read()
# Sabotage: silently drop any row whose qty is above 90. A data-loss bug that
# I1/I3/I6/I7 as currently tested cannot see.
src = src.replace(
  "    rows = [dict(zip(cols, split_row(l))) for l in tbl[2:] if not is_align(l)]",
  "    rows = [dict(zip(cols, split_row(l))) for l in tbl[2:] if not is_align(l)]\n"
  "    rows = [r for r in rows if not (r.get('qty','').strip().isdigit() and int(r['qty']) > 90)]")
open(sab, 'w').write(src)
r = subprocess.run([sys.executable, 'run_suite.py'], cwd=os.path.join(d, 'suite'),
                   capture_output=True, text=True)
tbl_part = r.stdout.split('=== .md')[0]
print(tbl_part.strip())
print(f'  ==> the .tbl half of the suite is GREEN with a parser that silently')
print('      discards rows. (The suite\'s only overall failure is the pre-existing')
print('      markdown link-label case.)')
shutil.rmtree(d)

print()
print('--- S1c the suite asserts "conflict" and then stops. I5 is never tested. ---')
sys.path[:0] = [os.path.join(H,'..','R1-common'), os.path.join(H,'..','L1-nominal-merge')]
from gw import git_merge
import tbl
BASE = """| item     | qty | unit  | total = qty * unit |
| -------- | --: | ----: | -----------------: |
| widget   |  10 | 12.00 |                    |
| gadget   |  20 |  6.00 |                    |
| sprocket |   8 | 15.00 |                    |
| flange   |   5 | 24.00 |                    |

grand := sum(total)
"""
def addcol(t, name, tag):
    L=[]
    for i,l in enumerate(t.splitlines()):
        if not l.startswith('|'): L.append(l)
        elif i==0: L.append(l+f' {name}  |')
        elif i==1: L.append(l+' ----- |')
        else: L.append(l+f' {tag}-{i:03d} |')
    return '\n'.join(L)+'\n'
rc, txt, n = git_merge(BASE, addcol(BASE,'code','A'), addcol(BASE,'code','B'), 'a.tbl')
print(f'  suite case "column-name collision": exit={rc} -> the suite records "ok".')
print(f'  the file left in the working tree ({n} marker lines):')
try:
    tbl.evaluate(txt); print('    parses fine')
except Exception as e:
    print(f'    tbl.evaluate -> {type(e).__name__}: {e}')
print('  I5: "the working tree never holds a file its own format cannot parse".')
print('  Every conflict case in the suite violates I5, and the suite scores them all')
print('  as passes because it only compares clean-vs-conflict.')

print()
print('--- S1d tests the suite does not contain ---')
for t in [
 'I1 round-trip for .tbl at all (currently a tautology)',
 'I1 round-trip on MERGED output, not just on hand-written corpora',
 'I5 at all: is the post-conflict working tree parseable by its own format?',
 'confluence: merge(A,B) == merge(B,A), and merge orders over 3+ branches',
 'duplicate ROW ID (the format declares `key := id` and nothing enforces it)',
 'duplicate AGGREGATE name (scattered namespace in the trailing block)',
 'a row whose field count differs from the header (silent zip truncation)',
 'a cell containing the delimiter (no escaping rule exists)',
 'numeric coercion: locale, nan/inf, unicode digits, float associativity',
 'evaluation order-independence: same rows, different order, same answer?',
 'the ADDRESS GRAMMAR: nothing in the suite resolves artifact#namepath',
 'cross-artifact derivation and cache invalidation (derive.py is untested)',
 '.canvas: the third native format has no conformance coverage at all',
 'the `prev.` operator (proposed in PASS5, implemented nowhere, untested)',
 'git merge-tree in a BARE repo -- the path PASS4 proved behaves differently',
 'CRLF, BOM, non-UTF8 bytes, missing trailing newline for .tbl',
 'unicode normalisation (NFC/NFD) of any name in any namespace',
 'corpus size: .tbl has ONE document; property tests need a generated corpus',
 'a mutation-testing gate: does the suite fail when the parser is sabotaged?',
]: print(f'    - {t}')
