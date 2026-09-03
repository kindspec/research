#!/usr/bin/env python3
"""Run the A1 -> named-column translator over a corpus of real .xlsx workbooks.

For each sheet: infer a header row and a data region exactly as the importer does,
then classify every formula cell. Reports the four verdicts plus the reason
histogram for the failures.
"""
import sys, os, re, glob, json, zipfile, collections, traceback
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import a1trans
from a1trans import NS, col2n, n2col, to_r1c1, translate, read_workbook, sheet_cells

def grid(cells):
    g=collections.defaultdict(dict)
    for ref,d in cells.items():
        m=re.match(r'([A-Z]+)(\d+)$',ref)
        if m: g[int(m.group(2))][col2n(m.group(1))]=d
    return g

UNIQ={}
def layout(name, cells):
    g=grid(cells)
    if not g: return None
    rows=sorted(g)
    hrow=None
    for r in rows[:20]:
        vals=[d for d in g[r].values() if (d['v'] or '').strip()]
        if len(vals)>=2 and not any(d['f'] for d in g[r].values()) \
           and all(not re.fullmatch(r'-?\d+(\.\d+)?', (d['v'] or '').strip()) for d in vals):
            hrow=r; break
    if hrow is None: return {'g':g,'hdr':{},'drange':(rows[0],rows[-1]),'hrow':None,'nf':
                             sum(1 for d in cells.values() if d['f'])}
    hdr={c:re.sub(r'\W','_',(d['v'] or '').strip()) for c,d in g[hrow].items() if (d['v'] or '').strip()}
    data=[r for r in rows if r>hrow]
    if not data: return {'g':g,'hdr':hdr,'drange':(hrow,hrow),'hrow':hrow,'nf':0}
    def shape(r): return frozenset((c,'f' if g[r][c].get('f') else 'v') for c in g[r] if c in hdr)
    s0=shape(data[0]); body=[]; run=True
    for r in data:
        if run and shape(r)==s0: body.append(r)
        else: run=False
    if not body: body=[data[0]]
    return {'g':g,'hdr':hdr,'drange':(body[0],body[-1]),'hrow':hrow,'nf':0}

def classify_sheet(name, cells, cnt, reasons, samples):
    L=a1trans.WB.get(name)
    if L is None: return
    g=L['g']; hdr=L['hdr']; hrow=L['hrow']; drange=L['drange']
    if hrow is None:
        cnt['NO-HEADER']+=L.get('nf',0); return
    if not hdr:
        cnt['NO-HEADER']+=sum(1 for d in cells.values() if d['f']); return
    for r in sorted(g):
        if r<=hrow: continue
        for c,d in g[r].items():
            if not d['f']: continue
            cell=f'{n2col(c)}{r}'
            try:
                v,expr,why = translate(d['f'], cell, name, hdr, drange, None)
            except Exception as e:
                v,expr,why='ERROR',None,f'{type(e).__name__}: {e}'
            cnt[v]+=1
            try: UNIQ.setdefault(to_r1c1(d['f'],cell), v)
            except Exception: pass
            if not v.startswith('CLEAN') and v not in ('AGGREGATE','AGGREGATE-FILTER'):
                key=re.sub(r"'[^']*'",'X',re.sub(r'\[.*?\]','[]',why))
                key=re.sub(r'\d+','N',key)
                reasons[v+' | '+key[:90]]+=1
                if len(samples[v])<6: samples[v].append((d['f'][:70], why[:80]))
            else:
                if len(samples[v])<8: samples[v].append((d['f'][:56], (expr or '')[:64]))

def main(files, limit=None):
    cnt=collections.Counter(); reasons=collections.Counter()
    a1trans.STATS=collections.Counter()
    samples=collections.defaultdict(list)
    ok=0; bad=0
    for i,p in enumerate(files):
        if limit and i>=limit: break
        try:
            z,sst,sheets,wb = read_workbook(p)
            a1trans.WB.clear(); a1trans._UNIQ_CACHE.clear()
            allcells={}
            for name,tgt in sheets:
                if tgt not in z.namelist(): continue
                root,cells = sheet_cells(z,sst,tgt)
                allcells[name]=cells
                L=layout(name,cells)
                if L is not None: a1trans.WB[name]=L
            for name,cells in allcells.items():
                classify_sheet(name,cells,cnt,reasons,samples)
            ok+=1
        except Exception as e:
            bad+=1
        if i%400==0: print(f'  ..{i} files, {sum(cnt.values())} formulas', file=sys.stderr, flush=True)
    return cnt, reasons, samples, ok, bad

if __name__=='__main__':
    files=sorted(glob.glob(sys.argv[1], recursive=True))
    lim=int(sys.argv[2]) if len(sys.argv)>2 else None
    cnt,reasons,samples,ok,bad=main(files,lim)
    n=sum(cnt.values())
    print(f'\nworkbooks read OK: {ok}   unreadable: {bad}   formula cells classified: {n}')
    for k,c in cnt.most_common(): print(f'  {k:16} {c:8d}  {100*c/n:5.1f}%')
    print('\n-- failure reasons --')
    for k,c in reasons.most_common(20): print(f'  {c:8d} {100*c/n:5.1f}%  {k}')
    uc=collections.Counter(UNIQ.values()); un=sum(uc.values())
    print(f'\n-- deduplicated by R1C1-normalised formula string (n={un} distinct) --')
    for k,c in uc.most_common(): print(f'  {k:16} {c:8d}  {100*c/un:5.1f}%')
    if a1trans.EXT and a1trans.STATS:
        print('\n-- extended-grammar instrumentation --')
        for k,c in sorted(a1trans.STATS.items()): print(f'  {c:8d}  {k}')
    print('\n-- samples --')
    for k in ['CLEAN','CLEAN-LOOKUP','AGGREGATE-FILTER','AGGREGATE','NEEDS-HUMAN','UNTRANSLATABLE']:
        for a,b in samples[k][:6]: print(f'  {k:15} {a:52} -> {b}')
    json.dump({'counts':dict(cnt),'reasons':dict(reasons)}, open(sys.argv[3] if len(sys.argv)>3 else 'out/corpus.json','w'), indent=1)
