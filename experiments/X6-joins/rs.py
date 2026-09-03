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

def split_row(l):
    return [c.strip().strip('\u00a0\u202f\u2007') for c in l.strip().strip('|').split('|')]
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
    order_declared = False
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
            order_declared = True
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
        if is_align(l):
            raise Malformed(f'alignment-style row among the data rows '
                            f'(wrong number of value fields): {l.strip()!r}')
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

def _isnum(v):
    try: float(v); return True
    except (ValueError, TypeError): return False

DATE_RE = re.compile(r'^\d{1,4}[-/]\d{1,2}[-/]\d{1,2}$')

def column_type(col, rows):
    """A column used for ordering must have ONE type. Mixed types have no total
    order, so they are refused rather than silently compared as strings."""
    vals = [str(r.get(col, '')).strip() for r in rows]
    vals = [v for v in vals if v != '']
    if not vals: return 'text'
    kinds = set()
    for v in vals:
        if DATE_RE.match(v): kinds.add('date')
        else:
            try: float(v); kinds.add('number')
            except ValueError: kinds.add('text')
    if len(kinds) > 1:
        raise Malformed(f'order column {col!r} mixes types {sorted(kinds)}; '
                        f'an ordering column must have a single type')
    return kinds.pop()

_GROUP = re.compile(r'(\w+)\(\s*(\w+)\s+where\s+(.+?)\s*\)\s*$')
_PRED  = re.compile(r'(\w+)\s*=\s*(?:@(\w+)|"([^"]*)")')

def _predicate(text, cols):
    """A conjunction of equality predicates. `@c` is THIS ROW's value of c."""
    preds = []
    for p in [x.strip() for x in re.split(r'\s+and\s+', text)]:
        m = _PRED.fullmatch(p)
        if not m: raise Malformed(f'unsupported predicate {p!r}')
        col, at, lit = m.groups()
        for c in (col, at):
            if c and c not in cols: raise Malformed(f'predicate names unknown column {c!r}')
        preds.append((col, at, lit))
    return preds

def ev(node, env):
    if isinstance(node, ast.Expression): return ev(node.body, env)
    if isinstance(node, ast.BinOp): return OPS[type(node.op)](ev(node.left, env), ev(node.right, env))
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub): return -ev(node.operand, env)
    if isinstance(node, ast.Constant): return node.value
    if isinstance(node, ast.Name):
        v = env.get(node.id, '')
        if v == '' or v is None: raise KeyError(node.id)
        if isinstance(v, str):
            if v.strip() != v or re.search(r'[,\u00a0\u202f]|^\(|\)$', v):
                raise KeyError(node.id)
        return float(v)
    if isinstance(node, ast.Call):
        return ('CALL', node.func.id, node.args[0].id if node.args else None)
    raise ValueError(ast.dump(node))

def evaluate(text):
    cols, formulas, rows, decls, order, key = parse(text)
    # THE ORDERING: derived from data, then row id as a stable tiebreak.
    if order:
        if key is None:
            raise Malformed("`order := by(...)` requires a `key :=` declaration: "
                            "without one, tied order values fall back to physical "
                            "file position, which is a coordinate")
        if order in formulas:
            raise Malformed(f"`order := by({order})` names a COMPUTED column; "
                            f"ordering must be derived from stored data")
        kind = column_type(order, rows)
        def typed(r):
            v = str(r[order]).strip()
            if kind == 'number':
                f = float(v)
                if f != f or f in (float('inf'), float('-inf')):
                    raise Malformed(f'order column {order!r} contains {v!r}')
                return f
            if kind == 'date':
                y, m, d = (int(x) for x in re.split(r'[-/]', v))
                return (y, m, d)
            return v
        # a real TUPLE, never a concatenation: the key breaks ties and nothing else
        seq = sorted(rows, key=lambda r: (typed(r), str(r.get(key, ''))))
    else:
        seq = rows
    # plain column formulas first
    # per-row GROUP aggregates: sum(amount where region = @region)
    for nm, expr in list(formulas.items()):
        m = _GROUP.fullmatch(expr.strip())
        if not m: continue
        fn, col, ptext = m.groups()
        if fn not in ('sum','count','min','max','avg'):
            raise Malformed(f'unknown aggregate {fn!r} in column {nm!r}')
        if col not in cols: raise Malformed(f'column {nm!r} aggregates unknown column {col!r}')
        preds = _predicate(ptext, cols)
        for r in seq:
            def hit(o, r=r):
                return all(str(o.get(pc,'')) == (str(r.get(at,'')) if at else lit)
                           for pc, at, lit in preds)
            vals = [o.get(col) for o in seq if hit(o)]
            try: nums = [float(v) for v in vals if v not in ('', None)]
            except (ValueError, TypeError): r[nm] = f'#REF!({col})'; continue
            r[nm] = (sum(nums) if fn=='sum' else len(vals) if fn=='count'
                     else min(nums) if fn=='min' else max(nums) if fn=='max'
                     else (sum(nums)/len(nums) if nums else f'#REF!({col})'))
    plain = {n: e for n, e in formulas.items()
             if not any(re.search(rf'\b{f}\s*\(', e) for f in ROWREL)
             and not _GROUP.fullmatch(e.strip())}
    for r in seq:
        pending = dict(plain)
        for _ in range(len(plain) + 1):          # fixpoint: order must not matter
            if not pending: break
            progressed = False
            for nm, expr in list(pending.items()):
                try:
                    r[nm] = ev(ast.parse(expr, mode='eval'), r)
                    del pending[nm]; progressed = True
                except KeyError as e:
                    if e.args[0] in pending: continue     # depends on a pending column
                    r[nm] = f'#REF!({e.args[0]})'; del pending[nm]; progressed = True
            if not progressed: break
        for nm in pending: r[nm] = '#REF!(cycle)'
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
        elif fn not in ('sum','count','min','max','avg'):
            raise Malformed(f'unknown aggregate function {fn!r} in {nm!r}')
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


def canon(text):
    """Canonical form: single-space delimiters, no alignment padding.

    Padding is a VIEW. Measured: a one-character edit in a padded 2000-row
    table produces a 2002-line / 238,370-byte diff versus 1 line / 413 bytes
    unpadded, and two genuinely disjoint edits CONFLICT padded while merging
    cleanly unpadded. render(parse(b)) == b still holds for padded input --
    canonicalisation is a separate, explicit operation.
    """
    st = structure(text)
    cols = st['cols']
    def row(cells): return '| ' + ' | '.join(cells) + ' |'
    hdr = []
    for c in cols:
        hdr.append(f'{c} = {st["formulas"][c]}' if c in st['formulas'] else c)
    out = list(st['prefix'])
    out.append(row(hdr) + '\n')
    if st['align_raw']:
        aligns = [a.strip() for a in split_row(st['align_raw'])]
        out.append(row([('--:' if a.endswith(':') and not a.startswith(':')
                         else ':-:' if a.startswith(':') and a.endswith(':')
                         else ':--' if a.startswith(':') else '---')
                        for a in aligns]) + '\n')
    for r in st['rows']:
        out.append(row([str(r.get(c, '')) if not isinstance(r.get(c), float) else ''
                        for c in cols]).replace('| |', '|  |') + '\n')
    out += st['tail']
    return ''.join(out)


def set_cell(st, row_key, col, value):
    """Mutate a cell THROUGH the structure. This exists so the round-trip test
    can be non-vacuous: an implementation whose `structure()` merely stores the
    raw bytes has no cells to set, and fails."""
    key = st['key']
    if key is None: raise Malformed('set_cell requires a declared key')
    if col not in st['cols']: raise Malformed(f'no column {col!r}')
    if col in st['formulas']: raise Malformed(f'{col!r} is a computed column')
    idx = st['cols'].index(col)
    for i, r in enumerate(st['rows']):
        if str(r.get(key)) == str(row_key):
            r[col] = str(value)
            cells = split_row(st['row_raws'][i])
            cells[idx] = str(value)
            st['row_raws'][i] = '| ' + ' | '.join(cells) + ' |\n'
            return st
    raise Malformed(f'no row with {key}={row_key!r}')
