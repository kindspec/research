#!/usr/bin/env python3
"""Row-id stability under RE-IMPORT of an updated source file.

Scenario: month 1 a CSV is imported to .tbl and committed. Month 2 the same
spreadsheet is re-exported with rows added, edited, deleted and reordered, and
re-imported. How many ids survive, and how big is the git diff?

Four identity functions compared:
  M1 positional      id = r_<row number>
  M2 content-hash    id = hash(all cells)
  M3 natural-key     id = hash(key column)
  M4 three-tier      carriage -> declared key -> exact-content match -> mint
"""
import sys, os, re, csv, io, subprocess, hashlib, json, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from csvtbl import mint, content_sig, parse_tbl, esc

def rd(csvtext):
    r=list(csv.reader(io.StringIO(csvtext)))
    return r[0], [dict(zip(r[0],x)) for x in r[1:]]

import os as _os
PAD = _os.environ.get('GWS_PAD','1')=='1'
def render(cols, rows):
    cols=['id']+[c for c in cols if c!='id']
    if PAD:
        w=[max(len(h),*(len(r.get(h,'')) for r in rows)) for h in cols] if rows else [len(h) for h in cols]
    else:
        w=[0]*len(cols)
    L=lambda cs:'| '+' | '.join(x.ljust(n) for x,n in zip(cs,w))+' |'
    return '\n'.join([L(cols),'| '+' | '.join('-'*max(n,3) for n in w)+' |']+
                     [L([r.get(c,'') for c in cols]) for r in rows])+'\n'

def M1(cols, rows, prev, key):    # positional
    for i,r in enumerate(rows): r['id']=f'r_{i+1:04d}'
    return rows
def M2(cols, rows, prev, key):    # content hash
    for r in rows: r['id']='r_'+content_sig(r,cols)[:6]
    return rows
def M3(cols, rows, prev, key):    # natural key
    for r in rows: r['id']='r_'+hashlib.blake2s(r[key].encode(),digest_size=3).hexdigest()
    return rows
def M4(cols, rows, prev, key):    # three-tier
    pk={}; pc=collections.defaultdict(list)
    if prev:
        for pr in prev:
            if key and key in pr: pk[pr[key]]=pr['id']
            pc[content_sig(pr,[c for c in cols if c!='id'])].append(pr['id'])
    used=set()
    for i,r in enumerate(rows):
        rid=None
        if r.get('id','').startswith('r_'): rid=r['id']
        elif key and r.get(key) in pk: rid=pk[r[key]]
        else:
            cands=[c for c in pc.get(content_sig(r,cols),[]) if c not in used]
            if cands: rid=cands[0]
        if not rid or rid in used:
            rid=mint(f'{i}\x00'+content_sig(r,cols))
        used.add(rid); r['id']=rid
    return rows

def M5(cols, rows, prev, key):
    '''M4 + STABLE ORDER: matched rows keep the previous file's line order,
    new rows are appended. Order is not semantic, so the importer owns it.'''
    rows=M4(cols,rows,prev,key)
    if not prev: return rows
    order={r['id']:i for i,r in enumerate(prev)}
    return sorted(rows, key=lambda r:(order.get(r['id'], 10**6), r['id']))

def gitdiff(repo, path, old, new):
    open(os.path.join(repo,path),'w').write(old)
    subprocess.run(['git','add','-A'],cwd=repo,check=True,capture_output=True)
    subprocess.run(['git','commit','-qm','v1','--allow-empty'],cwd=repo,capture_output=True)
    open(os.path.join(repo,path),'w').write(new)
    d=subprocess.run(['git','diff','--numstat',path],cwd=repo,capture_output=True,text=True).stdout
    dd=subprocess.run(['git','diff','--stat',path],cwd=repo,capture_output=True,text=True).stdout
    subprocess.run(['git','checkout','--','.'],cwd=repo,capture_output=True)
    a,b = (d.split()[:2] if d.strip() else ('0','0'))
    return int(a), int(b)

V1 = """sku,item,qty,unit
A-1,widget,10,12.00
A-2,gadget,20,6.00
A-3,sprocket,5,3.50
A-4,flange,12,9.25
A-5,bolt,100,0.15
A-6,nut,100,0.09
"""
# month 2: A-3 qty edited, A-4 deleted, A-7/A-8 added, rows REORDERED, A-5 renamed item
V2 = """sku,item,qty,unit
A-7,washer,50,0.05
A-2,gadget,20,6.00
A-5,bolt M6,100,0.15
A-1,widget,10,12.00
A-3,sprocket,8,3.50
A-6,nut,100,0.09
A-8,rivet,25,0.30
"""
TRUTH = {'A-1':'same','A-2':'same','A-3':'same','A-5':'same','A-6':'same',
         'A-4':'deleted','A-7':'new','A-8':'new'}

def run(carry_id):
    repo=os.path.abspath('out/idrepo')
    subprocess.run(['rm','-rf',repo]); os.makedirs(repo)
    subprocess.run(['git','init','-q','-b','main',repo],check=True)
    subprocess.run(['git','-C',repo,'config','user.email','t@t'],check=True)
    subprocess.run(['git','-C',repo,'config','user.name','t'],check=True)
    c1,r1=rd(V1); c2,r2=rd(V2)
    print(f'\n### id carried back in the re-export: {carry_id}')
    print(f'{"method":12} {"kept":>5} {"of":>3}  {"wrong-new":>9} {"reused-wrong":>12}  git diff +/-   DUPLICATE IDS')
    for nm,fn in [('M1 position',M1),('M2 content',M2),('M3 natkey',M3),('M4 three-tier',M4),
                  ('M5 M4+order',M5)]:
        a=[dict(r) for r in r1]; b=[dict(r) for r in r2]
        a=fn(c1,a,None,'sku')
        old=render(c1,a)
        byk={r['sku']:r['id'] for r in a}
        if carry_id:
            for r in b:
                if r['sku'] in byk: r['id']=byk[r['sku']]
        b=fn(c2,b,a,'sku')
        new=render(c2,b)
        kept=sum(1 for r in b if TRUTH.get(r['sku'])=='same' and byk.get(r['sku'])==r['id'])
        should=sum(1 for k,v in TRUTH.items() if v=='same')
        wrongnew=sum(1 for r in b if TRUTH.get(r['sku'])=='same' and byk.get(r['sku'])!=r['id'])
        reused=sum(1 for r in b if TRUTH.get(r['sku'])=='new' and r['id'] in byk.values())
        add,dele=gitdiff(repo,'t.tbl',old,new)
        ids=[r['id'] for r in b]
        dup=len(ids)-len(set(ids))
        print(f'{nm:12} {kept:5} {should:3}  {wrongnew:9} {reused:12}  +{add}/-{dele}   dup-ids={dup}')
    return

SCEN2_V2 = """sku,item,qty,unit
A-1,widget,10,12.00
A-2,gadget,20,6.00
A-3X,sprocket,5,3.50
A-4,flange,12,9.25
A-5,bolt,100,0.15
A-6,nut,100,0.09
"""
SCEN3_V2 = """sku,item,qty,unit
A-1,widget,10,12.00
A-2,gadget,20,6.00
A-3,sprocket,5,3.50
A-4,flange,12,9.25
A-5,bolt,100,0.15
A-6,nut,100,0.09
A-6,nut,100,0.09
"""
def run2(title, v2, truth, carry):
    global V2, TRUTH
    o1,o2=V2,TRUTH; V2,TRUTH=v2,truth
    print(f'\n=== {title} ===')
    run(carry_id=carry)
    V2,TRUTH=o1,o2

if __name__=='__main__':
    print('=== SCENARIO 1: edits + delete + 2 inserts + REORDER, key stable ===')
    run(carry_id=True); run(carry_id=False)
    run2('SCENARIO 2: the natural KEY of one row is corrected (A-3 -> A-3X), nothing else changes',
         SCEN2_V2, {k:'same' for k in ['A-1','A-2','A-4','A-5','A-6']} | {'A-3X':'same-as-A-3'}, False)
    run2('SCENARIO 3: the source now contains a DUPLICATE row (A-6 twice)',
         SCEN3_V2, {k:'same' for k in ['A-1','A-2','A-3','A-4','A-5','A-6']}, False)
