#!/usr/bin/env python3
"""tbl.py + the proposed `prev.` row-relative operator (PASS5: "Row-relative
access needs an explicit operator (prev.total), not an offset").

Everything else is unchanged: strict conflict-marker rejection, blank computed
cells, aggregates in the trailing block. `prev.X` resolves to the value of X on
the PRECEDING ROW IN FILE ORDER; on the first row it is 0.
"""
import re, sys, ast, operator
sys.path.insert(0, '../L1-nominal-merge')
from tbl import split_row, is_align, Malformed, CONFLICT, OPS

def parse(text):
    lines = text.splitlines()
    for n, l in enumerate(lines, 1):
        if l.startswith(CONFLICT):
            raise Malformed(f'line {n}: unresolved conflict marker')
    tbl = [l for l in lines if l.strip().startswith('|')]
    aggs = {}
    for l in lines:
        m = re.match(r'\s*(\w+)\s*:=\s*(\w+)\(\s*(\w+)\s*\)', l)
        if m: aggs[m.group(1)] = (m.group(2), m.group(3))
    header = split_row(tbl[0])
    cols, formulas, seen = [], {}, set()
    for h in header:
        if '=' in h:
            name, expr = h.split('=', 1)
            cols.append(name.strip()); formulas[name.strip()] = expr.strip()
        else: cols.append(h)
    for c in cols:
        if c in seen: raise Malformed(f'duplicate column name {c!r}')
        seen.add(c)
    rows = [dict(zip(cols, split_row(l))) for l in tbl[2:] if not is_align(l)]
    return cols, formulas, rows, aggs

def ev(node, env):
    if isinstance(node, ast.Expression): return ev(node.body, env)
    if isinstance(node, ast.BinOp): return OPS[type(node.op)](ev(node.left, env), ev(node.right, env))
    if isinstance(node, ast.Constant): return node.value
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name) \
            and node.value.id == 'prev':
        return float(env['__prev__'].get(node.attr, 0.0) or 0.0)
    if isinstance(node, ast.Name):
        v = env.get(node.id, '')
        if v == '' or v is None: raise KeyError(node.id)
        return float(v)
    raise ValueError(ast.dump(node))

def evaluate(text):
    cols, formulas, rows, aggs = parse(text)
    prev = {}
    for r in rows:
        r['__prev__'] = prev
        for name, expr in formulas.items():
            try: r[name] = ev(ast.parse(expr, mode='eval'), r)
            except KeyError as e: r[name] = f'#REF!({e.args[0]})'
        prev = {k: v for k, v in r.items() if k != '__prev__'}
    for r in rows: r.pop('__prev__', None)
    out = {}
    for name, (fn, col) in aggs.items():
        vals = [r.get(col) for r in rows]
        bad = [v for v in vals if isinstance(v, str) and str(v).startswith('#REF!')]
        if bad: out[name] = bad[0]
        elif fn == 'sum':  out[name] = sum(float(v) for v in vals)
        elif fn == 'count': out[name] = len(vals)
        elif fn == 'last': out[name] = vals[-1] if vals else None
        elif fn == 'min':  out[name] = min(float(v) for v in vals)
    return rows, out

if __name__ == '__main__':
    rows, aggs = evaluate(open(sys.argv[1]).read())
    for r in rows: print('  ', r)
    for k, v in aggs.items(): print(f'{k} = {v}')
