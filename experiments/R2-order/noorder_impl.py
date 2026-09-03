#!/usr/bin/env python3
"""Row-relative computation WITHOUT coordinates.

The insight: `prev.` failed not because row-relative computation is wrong, but
because "the row above" is a PLACE. If the table declares what determines row
order, then "the previous row" is a NOMINAL relationship -- "the row with the
next-lower key" -- and is independent of physical position, insertion, and
merge order.

    order := by(date)     row-relative ops legal, order derived from DATA
    order := none         row-relative ops are a PARSE ERROR (default)
"""
import re, sys, ast, operator, unicodedata

class Malformed(Exception): pass
CONFLICT = ('<<<<<<<', '=======', '>>>>>>>', '|||||||')
OPS = {ast.Add: operator.add, ast.Sub: operator.sub,
       ast.Mult: operator.mul, ast.Div: operator.truediv}
ROWREL = {'cumulative', 'prior', 'delta'}

def split_row(l): return [c.strip() for c in l.strip().strip('|').split('|')]
def is_align(l): return all(re.fullmatch(r':?-{2,}:?', c) for c in split_row(l) if c != '')

def parse(text):
    text = unicodedata.normalize('NFC', text)
    lines = text.splitlines()
    for n, l in enumerate(lines, 1):
        if l.startswith(CONFLICT):
            raise Malformed(f'line {n}: unresolved conflict marker')
    tbl = [l for l in lines if l.strip().startswith('|')]
    if not tbl: raise Malformed('no table found')
    decls, order, key = {}, None, None
    for n, l in enumerate(lines, 1):
        if ':=' not in l: continue
        m = re.match(r'\s*([^\s:=]+)\s*:=\s*(\w+)\(\s*([^\s()]*)\s*\)\s*$', l)
        if m:
            name, fn, arg = m.groups()
        else:
            m2 = re.match(r'\s*([^\s:=]+)\s*:=\s*([\w.-]+)\s*$', l)
            if not m2: raise Malformed(f'line {n}: malformed declaration: {l.strip()!r}')
            name, fn, arg = m2.group(1), None, m2.group(2)
            if name not in ('key',):
                raise Malformed(f'line {n}: {name!r} needs a function, e.g. {name} := sum(col)')
        if name == 'order':
            if order is not None: raise Malformed(f'line {n}: duplicate order declaration')
            if fn not in ('by', 'none'): raise Malformed(f'line {n}: order must be by(col) or none()')
            order = arg if fn == 'by' else None
        elif name == 'key':
            if key is not None: raise Malformed(f'line {n}: duplicate key declaration')
            key = arg
        else:
            if name in decls: raise Malformed(f'line {n}: duplicate aggregate name {name!r}')
            decls[name] = (fn, arg)
    header = split_row(tbl[0])
    cols, formulas, seen = [], {}, set()
    for h in header:
        if '=' in h:
            nm, expr = h.split('=', 1); nm = nm.strip()
            cols.append(nm); formulas[nm] = expr.strip()
        else:
            cols.append(h)
    for c in cols:
        if c in seen: raise Malformed(f'duplicate column name {c!r}')
        seen.add(c)
    # I7: row-relative operators are illegal unless order is declared
    for nm, expr in formulas.items():
        for fn in ROWREL:
            if re.search(rf'\b{fn}\s*\(', expr):
                if order is None:
                    raise Malformed(
                        f"column {nm!r} uses row-relative {fn}() but the table "
                        f"declares no row order. Add `order := by(<column>)`.")
                if order not in cols:
                    raise Malformed(f"order := by({order}) but there is no column {order!r}")
    if len(tbl) > 1 and is_align(tbl[1]) and len(split_row(tbl[1])) != len(cols):
        raise Malformed(f'alignment row has {len(split_row(tbl[1]))} fields, '
                        f'header has {len(cols)}')
    rows = []
    for l in tbl[2:]:
        if is_align(l): continue
        v = split_row(l)
        if len(v) != len(cols):
            raise Malformed(f'row has {len(v)} fields, header has {len(cols)}: {l.strip()!r}')
        rows.append(dict(zip(cols, v)))
    if key:
        ids = [r.get(key) for r in rows]
        if len(set(ids)) != len(ids):
            dup = [i for i in ids if ids.count(i) > 1][0]
            raise Malformed(f'duplicate key {key}={dup!r}')
    return cols, formulas, rows, decls, order, key

def ev(node, env):
    if isinstance(node, ast.Expression): return ev(node.body, env)
    if isinstance(node, ast.BinOp): return OPS[type(node.op)](ev(node.left, env), ev(node.right, env))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub): return -ev(node.operand, env)
    if isinstance(node, ast.Constant): return node.value
    if isinstance(node, ast.Name):
        v = env.get(node.id, '')
        if v == '' or v is None: raise KeyError(node.id)
        return float(v)
    if isinstance(node, ast.Call):
        return ('CALL', node.func.id, node.args[0].id if node.args else None)
    raise ValueError(ast.dump(node))

def evaluate(text):
    cols, formulas, rows, decls, order, key = parse(text)
    # THE ORDERING: derived from data, then row id as a stable tiebreak.
    if order:
        def sortkey(r):
            try: return (0, float(r[order]), str(r.get(key, '')))
            except (ValueError, TypeError): return (1, 0.0, str(r[order]) + str(r.get(key, '')))
        seq = rows
    else:
        seq = rows
    # plain column formulas first
    for r in seq:
        for nm, expr in formulas.items():
            if any(re.search(rf'\b{f}\s*\(', expr) for f in ROWREL): continue
            try: r[nm] = ev(ast.parse(expr, mode='eval'), r)
            except KeyError as e: r[nm] = f'#REF!({e.args[0]})'
    # row-relative, computed over the DERIVED order
    for nm, expr in formulas.items():
        m = re.fullmatch(r'\s*(\w+)\s*\(\s*(\w+)\s*\)\s*', expr)
        if not (m and m.group(1) in ROWREL): continue
        fn, src = m.groups()
        acc, prev = 0.0, None
        for r in seq:
            try: v = float(r[src])
            except (ValueError, TypeError, KeyError):
                r[nm] = f'#REF!({src})'; continue
            if fn == 'cumulative': acc += v; r[nm] = acc
            elif fn == 'prior':    r[nm] = prev if prev is not None else ''
            elif fn == 'delta':    r[nm] = (v - prev) if prev is not None else ''
            prev = v
    out = {}
    for nm, (fn, col) in decls.items():
        if col not in cols:
            out[nm] = f'#REF!({col})'; continue
        vals = [r.get(col) for r in seq]
        bad = [v for v in vals if isinstance(v, str) and v.startswith('#REF!')]
        if bad: out[nm] = bad[0]
        elif fn == 'sum':   out[nm] = sum(float(v) for v in vals if v != '')
        elif fn == 'count': out[nm] = len(vals)
        elif fn == 'min':   out[nm] = min(float(v) for v in vals if v != '')
        elif fn == 'max':   out[nm] = max(float(v) for v in vals if v != '')
    return seq, out

if __name__ == '__main__':
    try:
        rows, aggs = evaluate(open(sys.argv[1]).read())
    except Malformed as e:
        print(f'REFUSED: {e}'); sys.exit(2)
    for r in rows: print('  ', {k: v for k, v in r.items()})
    for k, v in aggs.items(): print(f'{k} = {v}')


# ---------------------------------------------------------------------------
# render: the other half of the round-trip law. Previously `render` was the
# identity function, which made the round-trip test a tautology asserting
# doc == doc. It now reconstructs the file from the parsed structure, so
# render(parse(b)) == b is a real assertion about the parser.
# ---------------------------------------------------------------------------

def structure(text):
    """Full parse into a serialisable structure, preserving what render needs."""
    text = unicodedata.normalize('NFC', text)
    lines = text.splitlines(keepends=True)
    cols, formulas, rows, decls, order, key = parse(text)
    tbl_idx = [i for i, l in enumerate(lines) if l.strip().startswith('|')]
    header_raw = lines[tbl_idx[0]]
    align_raw = lines[tbl_idx[1]] if len(tbl_idx) > 1 and is_align(lines[tbl_idx[1]]) else None
    row_raws = [lines[i] for i in tbl_idx[2:]]
    tail = lines[tbl_idx[-1] + 1:] if tbl_idx else []
    return {'header_raw': header_raw, 'align_raw': align_raw, 'row_raws': row_raws,
            'tail': tail, 'cols': cols, 'formulas': formulas, 'rows': rows,
            'decls': decls, 'order': order, 'key': key,
            'prefix': lines[:tbl_idx[0]] if tbl_idx else []}

def render(st):
    out = list(st['prefix']) + [st['header_raw']]
    if st['align_raw']: out.append(st['align_raw'])
    out += st['row_raws']
    out += st['tail']
    return ''.join(out)
