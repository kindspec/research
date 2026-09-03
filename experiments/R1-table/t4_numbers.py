#!/usr/bin/env python3
"""T4: the aggregate is IEEE-754 float addition, which is not associative.
The design says row order is irrelevant to merge. It is not irrelevant to the
ANSWER. A pure reorder, which git merges clean, changes the committed total."""
import sys, os
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(H,'..','R1-common'), os.path.join(H,'..','L1-nominal-merge')]
from gw import git_merge
import tbl

HDR = ("| id     | item     | qty | unit          | total = qty * unit |\n"
       "| ------ | -------- | --: | ------------: | -----------------: |\n")
TAIL = "\nkey   := id\ngrand := sum(total)\n"
def row(i, item, qty, unit):
    return f'| r_{i:04d} | {item:8s} | {qty:3d} | {unit:13s} |                    |\n'

def naive_sum(vs):
    """What every other implementation does: a plain left fold."""
    a = 0.0
    for v in vs: a += v
    return a

print('--- T4a float addition is not associative: order changes the total ---')
print('  NOTE: CPython >= 3.12 uses Neumaier compensated summation inside sum(),')
print('  which ACCIDENTALLY hides this in the reference evaluator. Any other')
print('  conforming implementation (JS, Rust, SQL, python<3.12, a spreadsheet)')
print('  does a plain left fold. The FORMAT does not pin the arithmetic.')
vals = [1e16, 1.0, -1e16]
print(f'  rows [1e16, 1.00, -1e16]')
print(f'    left fold, order (open,fee,close) = {naive_sum([1e16, 1.0, -1e16])!r}')
print(f'    left fold, order (open,close,fee) = {naive_sum([1e16, -1e16, 1.0])!r}')
print(f'    CPython sum()                     = {sum([1e16,1.0,-1e16])!r} / {sum([1e16,-1e16,1.0])!r}')
print(f'    math.fsum()                       = {__import__("math").fsum([1e16,1.0,-1e16])!r}')
print('  ==> two conformant implementations of the SAME .tbl file disagree by 1.0,')
print('      and the two ROW ORDERS disagree under the common implementation.')
print()
o = row(1,'opening',1,'1e16'); f = row(2,'fee',1,'1.00'); c = row(3,'closing',-1,'1e16')
for label, t in (('opening, fee, closing', HDR+o+f+c+TAIL),
                 ('opening, closing, fee', HDR+o+c+f+TAIL)):
    rows, ag = tbl.evaluate(t)
    lf = naive_sum([float(r['total']) for r in rows])
    print(f'  {label}: reference grand = {ag["grand"]!r}   left-fold grand = {lf!r}')
print('  Reference evaluator HELD (Neumaier). A left-fold implementation does not.')

print()
print('--- T4b a reorder + an unrelated edit merge CLEAN and change the answer ---')
pad = ''.join(row(i,f'pad{i:03d}',1,'0.00') for i in range(100, 140))
BASE   = HDR + o + f + pad + c + TAIL          # closing entry last
OURS   = HDR + o + c + f + pad + TAIL          # Alice moves the closing entry up
THEIRS = (HDR + o + f + pad + c + TAIL).replace('| r_0120 | pad120   |   1 |',
                                                '| r_0120 | pad120   |   2 |')
rc, txt, n = git_merge(BASE, OURS, THEIRS, 'b.tbl')
print(f'  git merge exit={rc} ({"CLEAN" if rc==0 else "CONFLICT"}) markers={n}')
def both(t):
    rows, ag = tbl.evaluate(t)
    return ag['grand'], naive_sum([float(r['total']) for r in rows])
print(f'  base   grand = {both(BASE)}   (reference, left-fold)')
print(f"  Bob's  grand = {both(THEIRS)}   (what Bob saw when he committed)")
print(f'  merged grand = {both(txt)}')
print('  ==> Alice reordered rows, which the design calls semantically irrelevant.')
print('      Under a left-fold evaluator the merged answer is one nobody computed,')
print('      with no conflict and no marker. Under CPython 3.12 sum() it is hidden.')

print()
print('--- T4c the same table, two DIFFERENT clean merges, two different totals ---')
# Alice moves closing up; Bob moves closing to the very top. Distinct branches.
OURS2   = HDR + o + c + f + pad + TAIL
THEIRS2 = HDR + o + f + pad + c + TAIL
for lbl, (b, oo, tt) in {
        'merge(ours=A, theirs=B)': (BASE, OURS2, THEIRS),
        'merge(ours=B, theirs=A)': (BASE, THEIRS, OURS2)}.items():
    rc, txt, n = git_merge(b, oo, tt, 'b.tbl')
    if n == 0:
        rows, ag = tbl.evaluate(txt)
        v = (ag['grand'], naive_sum([float(r['total']) for r in rows]))
    else: v = 'CONFLICT'
    print(f'  {lbl}: exit={rc} markers={n} grand(ref, left-fold)={v}')

print()
print('--- T4d money: 100 cent-sized rows ---')
C = HDR + ''.join(row(i,'x',1,'0.10') for i in range(1,101)) + TAIL
_, ag = tbl.evaluate(C)
print(f'  sum of 100 x 0.10 = {ag["grand"]!r}   exact decimal answer = 10.00')
print(f'  rendered by derive.py as ",.2f": {ag["grand"]:,.2f}  <-- masked at 2dp, but the')
print('  stored value is not the number, and the mask fails at a rounding boundary:')
D = HDR + ''.join(row(i,'x',1,'0.005') for i in range(1,3)) + TAIL
_, ag = tbl.evaluate(D)
print(f'  sum of 2 x 0.005 = {ag["grand"]!r} -> ",.2f" = {ag["grand"]:,.2f}  (decimal: 0.01)')

print()
print('--- T4e locale and coercion ---')
for c in ['1,234.00','1 234.00','12,50','1_000','１２','(500)','nan','inf','  42  ','+7','5e3','٣']:
    try: out = f'-> {float(c)!r}'
    except Exception as e: out = f'-> REJECTED ({type(e).__name__}) [loud, held]'
    print(f'  float({c!r:12s}) {out}')

print()
print('--- T4f a cell containing nan poisons the aggregate without an error ---')
E = HDR + row(1,'a',1,'10.00') + row(2,'b',1,'nan') + row(3,'c',1,'5.00') + TAIL
_, ag = tbl.evaluate(E)
print(f'  grand = {ag["grand"]!r}  -- does not trip the #REF! path, is not an error object,')
print('  and NaN propagates through any downstream comparison as False.')
