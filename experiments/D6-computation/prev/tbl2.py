#!/usr/bin/env python3
"""L1 table evaluator extended with an explicit row-relative operator `prev.`

    | date | amount | balance = prev.balance + amount |

`prev.` names the PREDECESSOR IN ROW ORDER, not a coordinate.  There is still
no A1 anywhere.  The question under test is whether an ordinal (not positional)
back-reference survives concurrent structural edits.
"""
import re, sys, ast, operator
OPS={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv}
def split_row(l): return [c.strip() for c in l.strip().strip('|').split('|')]
def is_align(l): return all(re.fullmatch(r':?-{2,}:?',c) for c in split_row(l) if c!='')

def parse(text):
    tbl=[l for l in text.splitlines() if l.strip().startswith('|')]
    aggs={}
    for l in text.splitlines():
        m=re.match(r'\s*(\w+)\s*:=\s*(\w+)\(\s*(\w+)\s*\)',l)
        if m: aggs[m.group(1)]=(m.group(2),m.group(3))
    cols,formulas=[],{}
    for h in split_row(tbl[0]):
        if '=' in h:
            n,e=h.split('=',1); cols.append(n.strip()); formulas[n.strip()]=e.strip()
        else: cols.append(h)
    rows=[dict(zip(cols,split_row(l))) for l in tbl[2:] if not is_align(l)]
    return cols,formulas,rows,aggs

def ev(node,env,prev):
    if isinstance(node,ast.Expression): return ev(node.body,env,prev)
    if isinstance(node,ast.BinOp): return OPS[type(node.op)](ev(node.left,env,prev),ev(node.right,env,prev))
    if isinstance(node,ast.Constant): return node.value
    if isinstance(node,ast.Attribute):           # prev.<col>
        if isinstance(node.value,ast.Name) and node.value.id=='prev':
            if prev is None: return 0.0          # first row: identity
            v=prev.get(node.attr)
            if isinstance(v,str) and v.startswith('#'): raise KeyError(node.attr)
            if v in ('',None): raise KeyError(node.attr)
            return float(v)
        raise ValueError('bad attribute')
    if isinstance(node,ast.Name):
        v=env.get(node.id,'')
        if v in ('',None): raise KeyError(node.id)
        return float(v)
    raise ValueError(ast.dump(node))

def evaluate(text):
    cols,formulas,rows,aggs=parse(text)
    prev=None
    for r in rows:                                # single ordered pass
        for name,expr in formulas.items():
            try: r[name]=ev(ast.parse(expr,mode='eval'),r,prev)
            except KeyError as e: r[name]=f'#REF!({e.args[0]})'
        prev=r
    out={}
    for name,(fn,col) in aggs.items():
        vals=[r.get(col) for r in rows]
        bad=[v for v in vals if isinstance(v,str) and v.startswith('#')]
        if bad: out[name]=bad[0]
        elif fn=='sum': out[name]=sum(float(v) for v in vals)
        elif fn=='last': out[name]=float(vals[-1]) if vals else 0.0
        elif fn=='count': out[name]=len(vals)
    return rows,out

if __name__=='__main__':
    rows,aggs=evaluate(open(sys.argv[1]).read())
    for r in rows: print('  ',{k:(round(v,2) if isinstance(v,float) else v) for k,v in r.items()})
    for k,v in aggs.items(): print(f'{k} = {v}')
