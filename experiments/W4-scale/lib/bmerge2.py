import sys, difflib
from blocks import parse

THRESH = 0.5   # git's rename-detection default is 50% similarity

def match(base, side):
    """Correspond side-blocks to base-blocks: exact hash first, then similarity."""
    bd = dict(base); used = set(); m = {}
    for n, raw in side:
        if n in bd and n not in used: m[n] = n; used.add(n); continue
    for n, raw in side:
        if n in m: continue
        best, score = None, THRESH
        for bn, braw in base:
            if bn in used: continue
            r = difflib.SequenceMatcher(None, braw.strip(), raw.strip()).ratio()
            if r > score: best, score = bn, r
        if best: m[n] = best; used.add(best)
    return m   # side-name -> base-name (or absent = new)

def m3(b, o, t):
    B, O, T = parse(b), parse(o), parse(t)
    db, do, dt = dict(B), dict(O), dict(T)
    mo, mt = match(B, O), match(B, T)
    # base-name -> (ours-raw, theirs-raw)
    ro = {mo[n]: do[n] for n in mo}; rt = {mt[n]: dt[n] for n in mt}
    out, conflicts = [], []
    for n, raw in O:
        bn = mo.get(n)
        if bn is None: out.append(raw); continue          # new on our side
        ours, theirs, base = do[n], rt.get(bn), db[bn]
        if theirs is None: out.append(ours); continue     # deleted by theirs? keep ours
        co, ct, cb = ours.strip(), theirs.strip(), base.strip()
        sep = raw[len(raw.rstrip()):]
        if co == ct: out.append(ours)
        elif co == cb: out.append(ct + sep)
        elif ct == cb: out.append(ours)
        else:
            conflicts.append(bn)
            out.append(f'<<<<<<< ours\n{ours.rstrip()}\n=======\n{theirs.rstrip()}\n>>>>>>> theirs\n\n')
    for n, raw in T:
        if n not in mt and raw not in out: out.append(raw)  # new on their side
    return ''.join(out), conflicts

if __name__ == '__main__':
    b, o, t = (open(p).read() for p in sys.argv[1:4])
    s, c = m3(b, o, t); sys.stdout.write(s)
    print(f'\n[conflicts: {len(c)}]', file=sys.stderr)
