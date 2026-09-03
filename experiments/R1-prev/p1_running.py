#!/usr/bin/env python3
"""P1: `prev.` makes ROW ORDER semantic, in a format whose merge rule is
"row order is irrelevant". Every order-changing merge is a silent-wrong."""
import sys, os
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(H,'..','R1-common'), H, os.path.join(H,'..','L1-nominal-merge')]
from gw import git_merge
import tblprev as T

HDR = ("| id     | desc     | amount | balance = prev.balance + amount |\n"
       "| ------ | -------- | -----: | ------------------------------: |\n")
TAIL = "\nkey     := id\nclosing := last(balance)\nlow     := min(balance)\n"
def r(i, desc, amt): return f'| r_{i:04d} | {desc:8s} | {amt:6s} |{"":33s}|\n'

BASE = HDR + r(1,'opening','1000') + r(2,'rent','-800') + r(3,'salary','2000') + TAIL
def show(label, t):
    rows, ag = T.evaluate(t)
    print(f'  {label:34s} balances={[x["balance"] for x in rows]}  '
          f'closing={ag["closing"]} low={ag["low"]}')

print('--- P1a the base ledger ---'); show('base', BASE)

print()
print('--- P1b two branches, both clean under stock git, different running totals ---')
# Alice inserts a refund immediately after opening. Bob appends a bank fee.
OURS   = HDR + r(1,'opening','1000') + r(4,'refund','500') + r(2,'rent','-800') + r(3,'salary','2000') + TAIL
THEIRS = HDR + r(1,'opening','1000') + r(2,'rent','-800') + r(3,'salary','2000') + r(5,'fee','-50') + TAIL
rc, txt, n = git_merge(BASE, OURS, THEIRS, 'led.tbl')
print(f'  git merge exit={rc} ({"CLEAN" if rc==0 else "CONFLICT"}) markers={n}')
show('merged', txt)
print('  This one is fine: both inserts are additive and `low` is unaffected.')

print()
print('--- P1c a REORDER, which the design says is semantically irrelevant ---')
# Alice sorts the ledger by date/description (a normal, intent-preserving act
# under `key := id`). Bob edits the salary amount.
SORTED = HDR + r(1,'opening','1000') + r(3,'salary','2000') + r(2,'rent','-800') + TAIL
BOB    = BASE.replace('| salary   |   2000 |', '| salary   |   1500 |')
rc, txt, n = git_merge(BASE, SORTED, BOB, 'led.tbl')
print(f'  git merge exit={rc} ({"CLEAN" if rc==0 else "CONFLICT"}) markers={n}')
if n == 0:
    show('merged', txt); show('Bob committed', BOB); show('Alice committed', SORTED)
print('  `closing` survives a reorder (addition is commutative).')
print('  `low`, the minimum running balance -- an overdraft check -- does NOT.')

print()
print('--- P1d MERGE ORDER DECIDES THE ANSWER (non-confluence) ---')
# Three writers. A inserts a large withdrawal near the top. B inserts a deposit
# near the top. Neither conflicts with the other under stock git.
A = HDR + r(1,'opening','1000') + r(6,'withdrawal','-900') + r(2,'rent','-800') + r(3,'salary','2000') + TAIL
B = HDR + r(1,'opening','1000') + r(7,'deposit','900')     + r(2,'rent','-800') + r(3,'salary','2000') + TAIL
for lbl, (o, t) in {'merge A then B': (A, B), 'merge B then A': (B, A)}.items():
    rc, txt, n = git_merge(BASE, o, t, 'led.tbl')
    if n:
        print(f'  {lbl}: exit={rc} markers={n} CONFLICT')
    else:
        rows, ag = T.evaluate(txt)
        print(f'  {lbl}: exit={rc} CLEAN  order={[x["desc"] for x in rows]}')
        print(f'      balances={[x["balance"] for x in rows]}  '
              f'closing={ag["closing"]}  low={ag["low"]}')
