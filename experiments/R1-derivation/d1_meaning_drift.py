#!/usr/bin/env python3
"""D1: a reference that still RESOLVES, to a different thing.
{{ budget.tbl#grand }} is a NAME. I2 says names are safe. Names are only safe
if the binding is stable, and nothing in the design binds a name to a meaning."""
import sys, os, shutil, tempfile
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(H,'..','R1-common'), os.path.join(H,'..','L1-nominal-merge')]
from gw import git_merge
import tbl, re

# net = ex-VAT, total = inc-VAT.  The report quotes the inc-VAT figure.
BASE = """| id     | item     | qty | unit  | net = qty * unit | total = net * 1.2 |
| ------ | -------- | --: | ----: | ---------------: | ----------------: |
| r_0001 | widget   |  10 | 12.00 |                  |                   |
| r_0002 | gadget   |  20 |  6.00 |                  |                   |
| r_0003 | sprocket |   8 | 15.00 |                  |                   |
| r_0004 | flange   |   5 | 24.00 |                  |                   |

key   := id
grand := sum(total)
"""
REPORT = "Procurement totalled {{ budget.tbl#grand }} against a plan of 600.00.\n"

def q(t):
    _, ag = tbl.evaluate(t); return ag['grand']

print('--- D1a a column rename makes a DIFFERENT column answer to the old name ---')
print(f'  base   : grand = {q(BASE):.2f}  (inc-VAT, which is what the report quotes)')
# Alice does an ordinary rename pass on the HEADER LINE ONLY:
#   total -> gross    and    net -> total     (now "total" means ex-VAT)
ALICE = BASE.replace('| net = qty * unit | total = net * 1.2 |',
                     '| total = qty * unit | gross = total * 1.2 |')
print(f'  Alice  : grand = {q(ALICE):.2f}  (the SAME aggregate line, ex-VAT now)')
# Bob, far below, edits a quantity.
BOB = BASE.replace('| r_0004 | flange   |   5 |', '| r_0004 | flange   |   6 |')
rc, txt, n = git_merge(BASE, ALICE, BOB, 'budget.tbl')
print(f'  git merge exit={rc} ({"CLEAN" if rc==0 else "CONFLICT"}) markers={n}')
print(f'  merged : grand = {q(txt):.2f}')
print(f'  header : {txt.splitlines()[0]}')
print(f'  aggregate line, untouched by anyone: '
      f'{[l for l in txt.splitlines() if l.startswith("grand")][0]!r}')
print('  ==> {{ budget.tbl#grand }} still resolves. No #REF!, no conflict, no marker.')
print(f'     The document now asserts {q(txt):.2f} where the truth is '
      f'{q(BOB):.2f}. Off by {q(BOB)-q(txt):.2f}.')

print()
print('--- D1b the aggregate itself is redefined while the name stays ---')
ALICE2 = BASE.replace('grand := sum(total)', 'grand := sum(net)')
BOB2   = BASE.replace('| r_0001 | widget   |  10 |', '| r_0001 | widget   |  11 |')
rc, txt, n = git_merge(BASE, ALICE2, BOB2, 'budget.tbl')
print(f'  git merge exit={rc} markers={n}  merged grand = {q(txt):.2f} '
      f'(report expects an inc-VAT figure; truth {q(BOB2):.2f})')

print()
print('--- D1c the reference SURVIVES A DELETION of what it named ---')
GONE = BASE.replace('| net = qty * unit | total = net * 1.2 |',
                    '| total = qty * unit |').replace('grand := sum(total)',
                                                      'grand := sum(total)')
print(f'  a column deleted, the aggregate name kept: grand = {q(GONE):.2f} '
      f'(was {q(BASE):.2f})')
print('  Nothing broke. The name resolved. The meaning changed.')

print()
print('--- D1d two artifacts, same name: is the address grammar file-qualified? ---')
print('  {{ budget.tbl#grand }} is file-qualified, so cross-file name collision is')
print('  impossible. HELD -- and this is the one place the grammar genuinely helps.')
