#!/usr/bin/env python3
"""xlsx -> .tbl, with a loss report. One .tbl per sheet that looks tabular."""
import sys, os, re, glob, zipfile, collections, hashlib
sys.path.insert(0, __file__.rsplit('/',1)[0])
import xml.etree.ElementTree as ET
from a1trans import (NS, col2n, n2col, to_r1c1, translate, read_workbook, sheet_cells)
from csvtbl import mint, esc

def sidecar(z):
    import json,re
    if 'docProps/custom.xml' not in z.namelist(): return None
    m=re.search(r'name="gws.tbl"><vt:lpwstr>(.*?)</vt:lpwstr>', z.read('docProps/custom.xml').decode(), re.S)
    if not m: return None
    import html
    try: return json.loads(html.unescape(m.group(1)))
    except Exception: return None

def analyse(path):
    z, sst, sheets, wb = read_workbook(path)
    parts = set(z.namelist())
    report=[]
    def R(sev,code,where,msg): report.append((sev,code,where,msg))

    # ---- workbook-level features ----
    if len(sheets)>1:
        R('REJECT','multi-sheet','workbook',
          f'{len(sheets)} sheets {[s[0] for s in sheets]}: .tbl is one table per file; '
          'a workbook is a directory, and cross-sheet references cannot survive the split')
    dn=[d.get('name') for d in wb.iter(f'{{{NS["m"]}}}definedName')]
    if dn: R('WARN','defined-names','workbook', f'{dn} dropped (.tbl has no workbook-scope namespace)')
    for pat,code,msg in [('xl/charts/','chart','chart definitions'),
                         ('xl/pivotCache','pivot','pivot caches/tables'),
                         ('xl/drawings/','drawing','drawings/shapes/images'),
                         ('xl/media/','media','embedded media'),
                         ('vbaProject','vba','VBA macros')]:
        hit=[p for p in parts if pat in p]
        if hit: R('WARN',code+'-dropped','workbook', f'{len(hit)} part(s) {msg} dropped: {sorted(hit)[:3]}')
    if 'xl/styles.xml' in parts:
        st=z.read('xl/styles.xml').decode()
        nf=len(re.findall(r'<numFmt ', st)); xf=len(re.findall(r'<xf ', st))
        R('WARN','styles-dropped','workbook',
          f'styles.xml: {xf} cell formats, {nf} custom number formats -> all dropped '
          '(.tbl stores the lexical value only)')

    out={}
    for name, target in sheets:
        root, cells = sheet_cells(z, sst, target)
        sx=z.read(target).decode()
        for tag,code,msg in [('mergeCell','merged-cells','merged cells'),
                             ('conditionalFormatting','conditional-format','conditional formatting'),
                             ('dataValidation','data-validation','data validation'),
                             ('pane','frozen-pane','frozen/split panes'),
                             ('autoFilter','autofilter','autofilter'),
                             ('hyperlink','hyperlink','hyperlinks')]:
            n=len(re.findall(r'<'+tag+r'[ />]', sx))
            if n: R(('REJECT' if tag=='mergeCell' else 'WARN'), code+'-dropped', name,
                    f'{n} {msg} dropped'+(' -- a merged cell has no row-per-line form' if tag=='mergeCell' else ''))
        if re.search(r'<comments|comments\d+\.xml', ' '.join(parts)) and name==sheets[0][0]:
            pass
        out[name]=(root, cells)
    ncom=[p for p in parts if re.match(r'xl/comments\d+\.xml',p)]
    if ncom:
        tot=sum(len(re.findall(r'<comment ', z.read(p).decode())) for p in ncom)
        R('WARN','comments-dropped','workbook', f'{tot} cell comment(s) dropped (no standoff channel on import)')
    return z, sst, sheets, out, report

def grid(cells):
    g=collections.defaultdict(dict)
    for ref,d in cells.items():
        m=re.match(r'([A-Z]+)(\d+)$',ref)
        g[int(m.group(2))][col2n(m.group(1))]=d
    return g

FREEZE=set()
def sheet_to_tbl(name, cells, report):
    g=grid(cells)
    if not g: return None
    rows=sorted(g)
    hrow=rows[0]
    headers={c:(d['v'] or '').strip() for c,d in g[hrow].items() if d['v']}
    if not headers: return None
    hdr={c:re.sub(r'\W','_',v) for c,v in headers.items()}
    # data rows = contiguous rows after the header that are not all-formula summary rows
    data=[r for r in rows[1:]]
    # trailing summary rows: a row where col1 is text and most cells empty/aggregate
    # A data row is one whose SHAPE (which columns hold a literal vs a formula)
    # matches row 2's. Body = the maximal contiguous run from row 2 with that shape.
    def shape(r): return frozenset((c, 'f' if g[r][c].get('f') else 'v') for c in g[r] if c in hdr)
    if not data: return None
    s0=shape(data[0]); body=[]; trailer=[]
    run=True
    for r in data:
        if run and shape(r)==s0: body.append(r)
        else: run=False; trailer.append(r)
    if not body: return None
    if trailer:
        report.append(('NOTE','region-boundary',name,
          f'data region inferred as rows {body[0]}-{body[-1]}; rows {trailer} have a different '
          'shape and were read as trailer/summary. This boundary is a GUESS: the file does not '
          'state where the table ends.'))
    drange=(body[0], body[-1])

    # ---- per column: is it a fill-down column formula? ----
    colform={}; verdicts=[]; frozen=set()
    for c,cname in sorted(hdr.items()):
        fs=[(f'{n2col(c)}{r}', g[r][c]['f']) for r in body if c in g[r] and g[r][c]['f']]
        if not fs: continue
        norms={to_r1c1(f,cell) for cell,f in fs}
        if len(norms)>1:
            report.append(('REJECT','inconsistent-column',f'{name}.{cname}',
              f'{len(norms)} distinct formulas down one column: '
              'not a column formula; .tbl cannot express a per-cell exception'))
            for cell,f in fs: verdicts.append((name,cell,cname,f,'UNTRANSLATABLE',None,'inconsistent fill-down'))
            continue
        if len(fs)!=len(body):
            report.append(('REJECT','partial-column',f'{name}.{cname}',
              f'formula in {len(fs)} of {len(body)} rows: a .tbl computed column is total'))
        cell,f = fs[0]
        v,expr,why = translate(f, cell, name, hdr, drange, None)
        verdicts.append((name,cell,cname,f,v,expr,why))
        if v in ('CLEAN','CLEAN-WIDE'):
            colform[cname]=expr
            if v=='CLEAN-WIDE': report.append(('WARN','wide-source',f'{name}.{cname}',why))
        elif f'{name}.{cname}' in FREEZE or cname in FREEZE:
            frozen.add(cname)
            report.append(('NOTE','column-frozen',f'{name}.{cname}',
              f'{f}  --  imported as CACHED VALUES under an explicit --freeze; '
              f'renamed to {cname}_frozen so the bytes say it is not live'))
        else: report.append(('REJECT','column-formula-'+v.lower(), f'{name}.{cname}',
              f'{f}  --  {why}  [re-run with --freeze {name}.{cname} to import the cached '
              'values as inert data, or fix the source]'))
    # ---- trailer / aggregate cells ----
    aggs={}
    for r in trailer:
        for c,d in sorted(g[r].items()):
            if not d['f']: continue
            cell=f'{n2col(c)}{r}'
            v,expr,why = translate(d['f'], cell, name, hdr, drange, None)
            cname=hdr.get(c, n2col(c))
            verdicts.append((name,cell,cname,d['f'],v,expr,why))
            if v=='AGGREGATE':
                an=re.sub(r'\W','_',(hdr.get(c) or n2col(c)))+'_total'
                aggs[an]=expr
            else: report.append(('REJECT' if v=='UNTRANSLATABLE' else 'WARN',
                                 'cell-formula-'+v.lower(), f'{name}!{cell}', f'{d["f"]}  --  {why}'))
    # ---- render ----
    ren={c:(hdr[c]+'_frozen' if hdr[c] in frozen else hdr[c]) for c in hdr}
    hdr=ren
    def rw(e):
        for fc in sorted(frozen,key=len,reverse=True):
            e=re.sub(r'(?<![A-Za-z0-9_])'+re.escape(fc)+r'(?![A-Za-z0-9_])', fc+'_frozen', e)
        return e
    colform={ (k+'_frozen' if k in frozen else k):rw(v) for k,v in colform.items()}
    aggs={k:rw(v) for k,v in aggs.items()}
    cols=['id']+[hdr[c] for c in sorted(hdr) if hdr[c]!='id']
    recs=[]
    for i,r in enumerate(body):
        idcol=[c for c in hdr if hdr[c]=='id']
        carried=(g[r].get(idcol[0],{}).get('v') if idcol else None)
        d={'id': carried if (carried or '').startswith('r_') else
                 mint(f'{name}\x00{i}\x00'+ '\x00'.join((g[r].get(c,{}).get('v') or '') for c in sorted(hdr)))}
        for c in sorted(hdr):
            if hdr[c]=='id': continue
            cell=g[r].get(c,{})
            d[hdr[c]] = '' if (cell.get('f') and hdr[c] in colform) else (cell.get('v') or '')
        recs.append(d)
    heads=['id']+[(f'{hdr[c]} = {colform[hdr[c]]}' if hdr[c] in colform else hdr[c])
                  for c in sorted(hdr) if hdr[c]!='id']
    w=[max(len(h), *(len(esc(r.get(c,''))) for r in recs)) for h,c in zip(heads,cols)]
    L=lambda cs:'| '+' | '.join(x.ljust(n) for x,n in zip(cs,w))+' |'
    txt=[L(heads), '| '+' | '.join('-'*n for n in w)+' |']+[L([esc(r.get(c,'')) for c in cols]) for r in recs]
    txt.append('')
    for a,e in aggs.items(): txt.append(f'{a} := {e}')
    return '\n'.join(txt).rstrip()+'\n', verdicts

if __name__=='__main__':
    args=sys.argv[1:]
    FREEZE.update(a for i,a in enumerate(args) if i>0 and args[i-1]=='--freeze')
    args=[a for i,a in enumerate(args) if a!='--freeze' and (i==0 or args[i-1]!='--freeze')]
    z,sst,sheets,out,report = analyse(args[0])
    allv=[]
    for name,(root,cells) in out.items():
        r=sheet_to_tbl(name,cells,report)
        if r is None: report.append(('WARN','not-tabular',name,'no header row found; skipped')); continue
        txt,verd=r; allv+=verd
        open(f'out/{name}.tbl','w').write(txt)
    sc = sidecar(z)
    if sc:
        for name in list(out):
            f=f'out/{name}.tbl'
            if not os.path.exists(f): continue
            txt=open(f).read().rstrip('\n')
            body=[l for l in txt.splitlines() if not re.match(r'\s*\w+\s*:=', l)]
            extra=([f'key   := {sc["key"]}'] if sc.get('key') else []) + \
                  [f'{k} := {v}' for k,v in sc.get('aggs',{}).items()]
            open(f,'w').write('\n'.join(l for l in body if l.strip())+'\n\n'+'\n'.join(extra)+'\n')
        report.append(('NOTE','sidecar-restored','workbook',
          'docProps/custom.xml gws.tbl restored key/aggregate names that OOXML has no place for'))
    print('===== LOSS REPORT =====')
    for s,c,w,m in report: print(f'{s:6} {c:28} {w:18} {m}')
    print(f'\n{sum(1 for i in report if i[0]=="REJECT")} REJECT / {sum(1 for i in report if i[0]=="WARN")} WARN')
    print('\n===== FORMULA VERDICTS =====')
    cnt=collections.Counter(v[4] for v in allv)
    for name,cell,cn,f,v,e,why in allv:
        print(f'{v:15} {name}!{cell:5} {f[:46]:48} {(e or why)[:70]}')
    n=len(allv)
    print(f'\nn={n}  ' + '  '.join(f'{k}={c} ({100*c/n:.1f}%)' for k,c in cnt.most_common()))
    nrej=sum(1 for i in report if i[0]=='REJECT')
    if nrej:
        for f in glob.glob('out/*.tbl'):
            pass
        print(f'\n== IMPORT REFUSED: {nrej} reject(s). No .tbl is authoritative until every '
              'one is resolved or explicitly frozen. ==')
        sys.exit(2)
