#!/usr/bin/env python3
"""P3: `prev.` IS A COORDINATE. It addresses "the row above", which is a
PLACE, and a concurrent insert changes it. I2 forbids exactly this.
This restores the 480-vs-660 defect that the format was designed to remove."""
import sys, os
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(H,'..','R1-common'), H, os.path.join(H,'..','L1-nominal-merge')]
from gw import git_merge
import tblprev as T

HDR = ("| id     | desc      | amount | balance = prev.balance * 1.05 + amount |\n"
       "| ------ | --------- | -----: | -------------------------------------: |\n")
TAIL = "\nkey     := id\nclosing := last(balance)\nlow     := min(balance)\n"
def r(i, desc, amt):
    return f'| r_{i:04d} | {desc:9s} | {amt:>6s} |{"":40s}|\n'

BASE = (HDR + r(1,'opening','1000') + r(2,'jan','-200') + r(3,'feb','-200')
        + r(4,'mar','-200') + r(5,'apr','-200') + r(6,'may','-200')
        + r(7,'jun','-200') + r(8,'jul','-200') + TAIL)

def show(label, t):
    rows, ag = T.evaluate(t)
    print(f'  {label:24s} balances={[round(x["balance"],2) for x in rows]}')
    print(f'  {"":24s} closing={ag["closing"]:.2f}  low={ag["low"]:.2f}')

print('--- P3a base: a compounding balance ---'); show('base', BASE)

print()
print('--- P3b Alice inserts a row NEAR THE TOP; Bob edits a row NEAR THE BOTTOM ---')
ALICE = BASE.replace(r(2,'jan','-200'), r(9,'grant','300') + r(2,'jan','-200'))
BOB   = BASE.replace(r(7,'jun','-200'), r(7,'jun','-250'))
rc, txt, n = git_merge(BASE, ALICE, BOB, 'led.tbl')
print(f'  git merge exit={rc} ({"CLEAN" if rc==0 else "CONFLICT"}) markers={n}')
show('Alice committed', ALICE); show('Bob committed', BOB); show('MERGED', txt)
rb = T.evaluate(BOB)[0];  rm = T.evaluate(txt)[0]
jul_b = [x for x in rb if x['desc']=='jul'][0]['balance']
jul_m = [x for x in rm if x['desc']=='jul'][0]['balance']
print(f'  Bob\'s row r_0008 (jul) balance: he saw {jul_b:.2f}, the file now says {jul_m:.2f}')
print('  ==> a row Bob did not touch, whose formula nobody edited, changed value')
print('      because a row was inserted ABOVE it. That is the A1 range defect,')
print('      reintroduced by an operator that addresses a PLACE. No marker.')

print()
print('--- P3c the overdraft check is silently wrong ---')
ALICE2 = BASE.replace(r(2,'jan','-200'), r(9,'bonus','400') + r(2,'jan','-200'))
BOB2   = BASE.replace(r(8,'jul','-200'), r(8,'jul','-200') + r(10,'aug','-900'))
for lbl, t in [('Alice alone', ALICE2), ('Bob alone', BOB2)]:
    ag = T.evaluate(t)[1]
    print(f'  {lbl:15s} low={ag["low"]:.2f}  overdrawn={ag["low"] < 0}')
rc, txt, n = git_merge(BASE, ALICE2, BOB2, 'led.tbl')
print(f'  git merge exit={rc} markers={n}')
if n == 0:
    ag = T.evaluate(txt)[1]
    print(f'  {"MERGED":15s} low={ag["low"]:.2f}  overdrawn={ag["low"] < 0}')

print()
print('--- P3d two clean merges of the same commits, different closing balance ---')
# Alice moves the `jul` row to the top of the schedule (a re-dating).
MOVED = (HDR + r(1,'opening','1000') + r(8,'jul','-200') + r(2,'jan','-200')
         + r(3,'feb','-200') + r(4,'mar','-200') + r(5,'apr','-200')
         + r(6,'may','-200') + r(7,'jun','-200') + TAIL)
# Bob inserts a big deposit in the middle.
INS = BASE.replace(r(5,'apr','-200'), r(11,'deposit','5000') + r(5,'apr','-200'))
for lbl, (o, t) in {'merge(MOVED <- INS)': (MOVED, INS),
                    'merge(INS <- MOVED)': (INS, MOVED)}.items():
    rc, txt, n = git_merge(BASE, o, t, 'led.tbl')
    if n: print(f'  {lbl}: exit={rc} markers={n} CONFLICT')
    else:
        rows, ag = T.evaluate(txt)
        print(f'  {lbl}: exit={rc} CLEAN order={[x["desc"] for x in rows]}')
        print(f'      closing={ag["closing"]:.2f} low={ag["low"]:.2f}')
