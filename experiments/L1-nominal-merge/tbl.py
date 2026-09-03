#!/usr/bin/env python3
"""Minimal evaluator for a candidate nominal-addressing table format.

Format: a GFM table. A computed column declares its formula IN ITS HEADER:
    | item | qty | unit | total = qty * unit |
Cells of a computed column are blank in the file. Aggregates are declared in a
trailing block as  name := agg(column).
No coordinates exist anywhere in the format.
"""
import re, sys, ast, operator, unicodedata

OPS = {ast.Add: operator.add, ast.Sub: operator.sub,
       ast.Mult: operator.mul, ast.Div: operator.truediv}

def split_row(line):
    return [c.strip() for c in line.strip().strip('|').split('|')]

def is_align(line):
    return all(re.fullmatch(r':?-{2,}:?', c) for c in split_row(line) if c != '')

class Malformed(Exception): pass

CONFLICT = ('<<<<<<<', '=======', '>>>>>>>', '|||||||')

def parse(text):
    text = unicodedata.normalize('NFC', text)
    lines = [l for l in text.splitlines()]
    # I7 STRICT PARSING: reject rather than skip.
    for n, l in enumerate(lines, 1):
        if l.startswith(CONFLICT):
            raise Malformed(f'line {n}: unresolved conflict marker {l.split()[0]!r}')
    tbl = [l for l in lines if l.strip().startswith('|')]
    aggs = {}
    for n, l in enumerate(lines, 1):
        if ':=' not in l: continue
        m = re.match(r'\s*([^\s:=]+)\s*:=\s*(\w+)\(\s*([^\s()]+)\s*\)\s*$', l)
        if not m:
            raise Malformed(f'line {n}: malformed aggregate declaration: {l.strip()!r}')
        if m.group(1) in aggs:
            raise Malformed(f'line {n}: duplicate aggregate name {m.group(1)!r}')
        aggs[m.group(1)] = (m.group(2), m.group(3))
    header = split_row(tbl[0])
    cols, formulas = [], {}
    seen = set()
    for h in header:
        if '=' in h:
            name, expr = h.split('=', 1)
            cols.append(name.strip()); formulas[name.strip()] = expr.strip()
        else:
            cols.append(h)
    for c in cols:
        if c in seen: raise Malformed(f'duplicate column name {c!r}')
        seen.add(c)
    rows = [dict(zip(cols, split_row(l))) for l in tbl[2:] if not is_align(l)]
    return cols, formulas, rows, aggs

def ev(node, env):
    if isinstance(node, ast.Expression): return ev(node.body, env)
    if isinstance(node, ast.BinOp): return OPS[type(node.op)](ev(node.left, env), ev(node.right, env))
    if isinstance(node, ast.Constant): return node.value
    if isinstance(node, ast.Name):
        v = env.get(node.id, '')
        if v == '' or v is None: raise KeyError(node.id)
        return float(v)
    raise ValueError(ast.dump(node))

def evaluate(text):
    cols, formulas, rows, aggs = parse(text)
    for r in rows:
        for name, expr in formulas.items():
            try:
                r[name] = ev(ast.parse(expr, mode='eval'), r)
            except KeyError as e:
                r[name] = f'#REF!({e.args[0]})'
    out = {}
    for name, (fn, col) in aggs.items():
        vals = [r.get(col) for r in rows]
        bad = [v for v in vals if isinstance(v, str) and v.startswith('#REF!')]
        if bad: out[name] = bad[0]
        elif fn == 'sum': out[name] = sum(float(v) for v in vals)
        elif fn == 'count': out[name] = len(vals)
    return rows, out

if __name__ == '__main__':
    rows, aggs = evaluate(open(sys.argv[1]).read())
    for r in rows: print('  ', r)
    for k, v in aggs.items(): print(f'{k} = {v}')
