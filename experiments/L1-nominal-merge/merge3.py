#!/usr/bin/env python3
"""Generic three-way merge over ENTITY MAPS, written once, not per format.

An entity map is: ordered [(name, {attr: value})] plus a column order.
Row identity = the key column (first column by convention).
"""
import sys

def split_row(l): return [c.strip() for c in l.strip().strip('|').split('|')]

def parse(text):
    lines = text.splitlines()
    tbl = [l for l in lines if l.strip().startswith('|')]
    tail = [l for l in lines if not l.strip().startswith('|')]
    cols = split_row(tbl[0])
    ents = []
    for l in tbl[2:]:
        vals = split_row(l)
        vals += [''] * (len(cols) - len(vals))
        d = dict(zip(cols, vals))
        ents.append((vals[0], d))
    return cols, ents, tail

def render(cols, ents, tail):
    w = [max(len(c), *([len(e[1].get(c, '')) for e in ents] or [0])) for c in cols]
    out = ['| ' + ' | '.join(c.ljust(w[i]) for i, c in enumerate(cols)) + ' |',
           '| ' + ' | '.join('-' * w[i] for i in range(len(cols))) + ' |']
    for _, d in ents:
        out.append('| ' + ' | '.join(d.get(c, '').ljust(w[i]) for i, c in enumerate(cols)) + ' |')
    return '\n'.join(out + tail) + '\n'

def merge_seq(base, ours, theirs):
    """Merge ordered name lists: keep order, apply both sides' inserts/deletes."""
    res, conflicts = [], []
    for n in ours:
        if n in base and n not in theirs: continue          # deleted by theirs
        res.append(n)
    for i, n in enumerate(theirs):
        if n in res or n in base: continue                   # already there / deleted
        anchor = theirs[i-1] if i else None
        res.insert(res.index(anchor) + 1 if anchor in res else len(res), n)
    return res, conflicts

def merge3(bt, ot, tt):
    bc, be, btl = parse(bt); oc, oe, otl = parse(ot); tc, te, ttl = parse(tt)
    bd, od, td = dict(be), dict(oe), dict(te)
    conflicts = []
    # --- columns: union preserving order, both sides' additions survive
    cols = list(oc)
    for i, c in enumerate(tc):
        if c not in cols:
            cols.insert(min(i, len(cols)), c)
    for c in bc:
        if c not in oc or c not in tc:
            if c in cols: cols.remove(c)                     # deleted on one side
    names, _ = merge_seq([n for n, _ in be], [n for n, _ in oe], [n for n, _ in te])
    ents = []
    for n in names:
        b, o, t = bd.get(n, {}), od.get(n, {}), td.get(n, {})
        d = {}
        for c in cols:
            bv, ov, tv = b.get(c, ''), o.get(c, ''), t.get(c, '')
            if ov == tv:        d[c] = ov
            elif bv == ov:      d[c] = tv                    # only theirs changed
            elif bv == tv:      d[c] = ov                    # only ours changed
            else:
                conflicts.append((n, c, ov, tv)); d[c] = ov
        ents.append((n, d))
    return render(cols, ents, otl or ttl or btl), conflicts

if __name__ == '__main__':
    b, o, t = (open(p).read() for p in sys.argv[1:4])
    out, cf = merge3(b, o, t)
    sys.stdout.write(out)
    for c in cf: print(f'CONFLICT row={c[0]} col={c[1]} ours={c[2]!r} theirs={c[3]!r}', file=sys.stderr)
    sys.exit(1 if cf else 0)
