#!/usr/bin/env python3
"""Render a .tbl to GFM markdown or HTML: evaluate, then emit values.
The id column is presentation noise and is dropped by default."""
import sys, os, re, ast, operator, html
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from csvtbl import parse_tbl
OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv}
def ev(n,e):
    if isinstance(n,ast.Expression): return ev(n.body,e)
    if isinstance(n,ast.BinOp): return OPS[type(n.op)](ev(n.left,e),ev(n.right,e))
    if isinstance(n,ast.Constant): return n.value
    if isinstance(n,ast.Name):
        v=e.get(n.id,'')
        if v=='' : raise KeyError(n.id)
        return float(v)
    raise ValueError(ast.dump(n))
def resolve(text):
    cols,fm,rows,ag,key=parse_tbl(text)
    for r in rows:
        for nm,x in fm.items():
            try: r[nm]=('%g'%ev(ast.parse(x,mode='eval'),r))
            except KeyError as k: r[nm]=f'#REF!({k.args[0]})'
    out={}
    for nm,(fn,c) in ag.items():
        vs=[r.get(c,'') for r in rows]
        bad=[v for v in vs if isinstance(v,str) and v.startswith('#REF!')]
        out[nm]=bad[0] if bad else ('%g'%(sum(float(v) for v in vs) if fn=='sum' else len(vs)))
    return cols,fm,rows,out,key
def md(text, keep_id=False):
    cols,fm,rows,ag,key=resolve(text)
    c=[x for x in cols if keep_id or x!='id']
    w=[max(len(h),*(len(str(r.get(h,''))) for r in rows)) for h in c]
    L=lambda cs:'| '+' | '.join(str(x).ljust(n) for x,n in zip(cs,w))+' |'
    o=[L(c),'| '+' | '.join('-'*n for n in w)+' |']+[L([r.get(x,'') for x in c]) for r in rows]
    if ag: o+=['']+[f'{k} = {v}' for k,v in ag.items()]
    return '\n'.join(o)+'\n'
def to_html(text, keep_id=False):
    cols,fm,rows,ag,key=resolve(text)
    c=[x for x in cols if keep_id or x!='id']
    E=html.escape
    th=''.join(f'<th title="{E(fm[x]) if x in fm else ""}">{E(x)}'
               + (f'<br><code>= {E(fm[x])}</code>' if x in fm else '') + '</th>' for x in c)
    tr=''.join('<tr'+(' data-id="%s"'%E(r.get('id','')))+'>'+''.join(
        f'<td class="{"derived" if x in fm else ""}">{E(str(r.get(x,"")))}</td>' for x in c)+'</tr>'
        for r in rows)
    tf=''.join(f'<tr><th>{E(k)}</th><td colspan="{len(c)-1}">{E(str(v))}</td></tr>' for k,v in ag.items())
    return (f'<table><thead><tr>{th}</tr></thead><tbody>{tr}</tbody>'
            + (f'<tfoot>{tf}</tfoot>' if tf else '') + '</table>\n')
if __name__=='__main__':
    t=open(sys.argv[2]).read()
    sys.stdout.write(md(t) if sys.argv[1]=='md' else to_html(t))
