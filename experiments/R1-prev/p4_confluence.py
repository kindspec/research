#!/usr/bin/env python3
"""P4: is the merged ROW ORDER (which `prev.` makes semantic) confluent?
Three writers, merged in the six possible sequences."""
import sys, os, itertools, subprocess, tempfile, shutil
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [H, os.path.join(H,'..','L1-nominal-merge')]
import tblprev as T

HDR = ("| id     | desc      | amount | balance = prev.balance * 1.05 + amount |\n"
       "| ------ | --------- | -----: | -------------------------------------: |\n")
TAIL = "\nkey     := id\nclosing := last(balance)\nlow     := min(balance)\n"
def r(i, d, a): return f'| r_{i:04d} | {d:9s} | {a:>6s} |{"":40s}|\n'
ROWS = [r(1,'opening','1000')] + [r(i,f'm{i}','-200') for i in range(2, 9)]
BASE = HDR + ''.join(ROWS) + TAIL

VARIANTS = {
  'A': HDR + ''.join(ROWS[:2] + [r(20,'bigA','900')] + ROWS[2:]) + TAIL,   # insert after row1
  'B': HDR + ''.join(ROWS[:6] + [r(21,'bigB','-900')] + ROWS[6:]) + TAIL,  # insert after row5
  'C': HDR + ''.join([ROWS[0], ROWS[7]] + ROWS[1:7]) + TAIL,               # move last row up
}

def sh(*a, cwd=None): return subprocess.run(a, cwd=cwd, capture_output=True, text=True)

def sequence(order):
    d = tempfile.mkdtemp()
    try:
        sh('git','init','-q',d); sh('git','config','user.email','t@e',cwd=d); sh('git','config','user.name','t',cwd=d)
        p = os.path.join(d,'led.tbl'); open(p,'w').write(BASE)
        sh('git','add','-A',cwd=d); sh('git','commit','-qm','b',cwd=d); sh('git','branch','-M','main',cwd=d)
        for k in VARIANTS:
            sh('git','checkout','-q','-b',k,'main',cwd=d)
            open(p,'w').write(VARIANTS[k]); sh('git','commit','-qam',k,cwd=d)
        sh('git','checkout','-q','main',cwd=d)
        for k in order:
            res = sh('git','merge',k,'-m','m',cwd=d)
            if res.returncode: return order, 'CONFLICT at ' + k, None, None
        txt = open(p).read()
        rows, ag = T.evaluate(txt)
        return order, [x['desc'] for x in rows], ag['closing'], ag['low']
    finally: shutil.rmtree(d)

seen = {}
for order in itertools.permutations('ABC'):
    o, desc, cl, lo = sequence(order)
    key = (str(desc), cl, lo)
    seen.setdefault(key, []).append(''.join(o))
    print(f'  {"".join(o)}: closing={cl if cl is None else round(cl,2)} '
          f'low={lo if lo is None else round(lo,2)}  order={desc}')
print()
print(f'  distinct outcomes: {len(seen)}')
if len(seen) > 1:
    print('  ==> NON-CONFLUENT: merge ORDER decides the committed number, every merge clean.')
else:
    print('  ==> confluent across all 6 sequences: HELD.')
