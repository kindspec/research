#!/usr/bin/env python3
"""D3: drift across a MERGE. check(old,new) is two-way. There is no three-way
form and no rule saying which base to use, so the answer depends on which pair
you feed it -- and the merge-specific case is silent."""
import os, subprocess, tempfile, shutil, drift, otbl

def sh(*a, cwd=None): return subprocess.run(a, cwd=cwd, capture_output=True, text=True)
def merge(base, ours, theirs, fn='a.tbl'):
    d = tempfile.mkdtemp()
    try:
        sh('git','init','-q',d)
        for k,v in [('user.email','t@e'),('user.name','t')]: sh('git','config',k,v,cwd=d)
        p=os.path.join(d,fn); open(p,'w').write(base)
        sh('git','add','-A',cwd=d); sh('git','commit','-qm','b',cwd=d); sh('git','branch','-M','main',cwd=d)
        sh('git','checkout','-qb','x',cwd=d); open(p,'w').write(theirs); sh('git','commit','-qam','x',cwd=d)
        sh('git','checkout','-q','main',cwd=d); open(p,'w').write(ours); sh('git','commit','-qam','o',cwd=d)
        r=sh('git','merge','x','-m','m',cwd=d); t=open(p).read()
        return r.returncode, t.count('<<<<<<<'), t
    finally: shutil.rmtree(d)

BASE = """| id     | qty | unit  | net = qty * unit | total = net * 1.2 |
| ------ | --: | ----: | ---------------: | ----------------: |
| r_0001 |  10 | 12.00 |                  |                   |
| r_0002 |  20 |  6.00 |                  |                   |

key   := id
grand := sum(total)
n     := count(id)
mx    := max(qty)
mn    := min(qty)
"""
# ALICE: an ordinary rename pass on the header. `total`->`gross`, `net`->`total`.
#        She updates the ONE reference she can see: grand := sum(gross).
ALICE = BASE.replace('| net = qty * unit | total = net * 1.2 |',
                     '| total = qty * unit | gross = total * 1.2 |') \
            .replace('grand := sum(total)', 'grand := sum(gross)')
# BOB: on his branch, adds a NEW aggregate. He means the inc-VAT column,
#      which on his branch is called `total`.
BOB = BASE + 'reported := sum(total)\n'

rc, mk, M = merge(BASE, ALICE, BOB)
print(f'--- git merge exit={rc} markers={mk}')
print('merged declarations:')
for l in M.splitlines():
    if ':=' in l: print('   ', l)
print('   header:', M.splitlines()[0])
print()
print('base     grand =', otbl.evaluate(BASE)[1])
print('bob      reported =', otbl.evaluate(BOB)[1], '  (he meant inc-VAT: 288.0)')
print('MERGED   ', otbl.evaluate(M)[1], '  <-- `reported` is now ex-VAT')
print()
for lbl, a, b in (('base   -> merged', BASE, M),
                  ('alice  -> merged', ALICE, M),
                  ('bob    -> merged', BOB, M)):
    f, n = drift.check(a, b)
    print(f'drift.check({lbl}): {len(f)} finding(s)   {"" if f else "<-- SILENT"}')
    for x in f: print('     ', x.splitlines()[0])
print()
print("Only ONE of the three available pairs catches it, and it is the one no")
print("tool picks. A PR check compares the merge BASE (or the first parent) to")
print("the result: both are SILENT. The rebinding is visible only from the")
print("second parent, because a reference that did not exist in the old version")
print("is never inspected (`for label, oexpr in orefs.items()`).")
print("drift.check has no three-way form and the design names no base.")
