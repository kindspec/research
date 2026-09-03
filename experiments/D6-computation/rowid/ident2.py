#!/usr/bin/env python3
"""Row-identity ablation.  Same generic entity-map 3-way merge, four different
identity functions.  Which scenarios each scheme survives is the whole question."""
import hashlib, itertools, sys

def rows(t): return [ [c.strip() for c in l.strip().strip('|').split('|')]
                      for l in t.strip().splitlines() if l.strip().startswith('|') ]

IDENT = {
  'natural-key'  : lambda i,r,cols: r[cols.index('item')],
  'content-hash' : lambda i,r,cols: hashlib.sha256('|'.join(r).encode()).hexdigest()[:8],
  'opaque-id-col': lambda i,r,cols: r[cols.index('id')],
  'positional'   : lambda i,r,cols: f'#{i}',
}

def merge(base, ours, theirs, scheme):
    B,O,T = rows(base), rows(ours), rows(theirs)
    cols = B[0]
    f = IDENT[scheme]
    def emap(R): return [ (f(i,r,cols), dict(zip(cols,r))) for i,r in enumerate(R[2:]) ]
    be,oe,te = emap(B),emap(O),emap(T)
    bd,od,td = dict(be),dict(oe),dict(te)
    order=[n for n,_ in oe]
    for i,(n,_) in enumerate(te):
        if n not in order and n not in bd:
            a = te[i-1][0] if i else None
            order.insert(order.index(a)+1 if a in order else len(order), n)
    for n,_ in be:
        if (n in bd) and (n not in od or n not in td) and n in order: order.remove(n)
    out, cf = [], []
    for n in order:
        b,o,t = bd.get(n,{}), od.get(n,{}), td.get(n,{})
        d={}
        for c in cols:
            bv,ov,tv=b.get(c,''),o.get(c,''),t.get(c,'')
            if ov==tv: d[c]=ov
            elif bv==ov: d[c]=tv
            elif bv==tv: d[c]=ov
            else: cf.append((n,c,ov,tv)); d[c]=ov
        out.append(d)
    return out, cf

BASE = """| id | item   | qty | price |
| -- | ------ | --- | ----- |
| r1 | widget | 10  | 12    |
| r2 | gadget | 20  | 18    |
| r3 | bolt   | 5   | 2     |
"""
def mod(t, subs):
    for a,b in subs: t=t.replace(a,b)
    return t

SCEN = {
 'S1 edit different cols of same row':
   (mod(BASE,[('| 10  |','| 99  |')]), mod(BASE,[('| 12    |','| 15    |')])),
 'S2 one side renames the key value':
   (mod(BASE,[('| widget','| WIDGET')]), mod(BASE,[('| 10  |','| 99  |')])),
 'S3 both insert a row at different places':
   (mod(BASE,[('| r2 |','| r9 | nut    | 1   | 3     |\n| r2 |')]),
    mod(BASE,[('| r3 | bolt   | 5   | 2     |','| r3 | bolt   | 5   | 2     |\n| r8 | screw  | 7   | 1     |')])),
 'S4 duplicate key values exist in the table':
   (mod(BASE.replace('| r3 | bolt','| r3 | widget'),[('| 10  |','| 99  |')]),
    BASE.replace('| r3 | bolt','| r3 | widget')),
}
for scen,(ours,theirs) in SCEN.items():
    b = BASE
    if scen.startswith('S4'): b = BASE.replace('| r3 | bolt','| r3 | widget')
    print(f'\n=== {scen} ===')
    for sch in IDENT:
        try:
            out,cf = merge(b, ours, theirs, sch)
            desc = ' ; '.join(f"{r['item']}/{r['qty']}/{r['price']}" for r in out)
            print(f'  {sch:14s} rows={len(out)} conflicts={len(cf)}  -> {desc}')
        except Exception as e:
            print(f'  {sch:14s} ERROR {type(e).__name__}: {e}')
