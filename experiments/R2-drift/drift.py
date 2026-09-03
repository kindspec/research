#!/usr/bin/env python3
"""Detect MEANING DRIFT: a reference that still resolves, to something else.

Identity across versions rests on a column's DEFINITION, not its values --
otherwise every ordinary data edit fires a false positive, which would make the
check worthless. A literal column's identity is its name; a computed column's
identity is its formula, resolved through any renames already detected.

Rebinding requires a name to change what it denotes. That needs either a
definition change or a change to the set of names. If neither happened, no
check is possible or necessary.
"""
import sys, re, otbl

def defs(text):
    cols, formulas, rows, decls, order, key = otbl.parse(text)
    d = {c: formulas.get(c) for c in cols}          # None => literal column
    refs = {}
    for name, expr in formulas.items(): refs[f'column {name}'] = expr
    for name, (fn, arg) in decls.items():
        if name not in ('key', 'order'): refs[f'{name} :='] = f'{fn}({arg})'
    return d, refs

def norm(expr, rename):
    """Rewrite a formula through a rename map so definitions become comparable."""
    if expr is None: return None
    return re.sub(r'[A-Za-z_]\w*', lambda m: rename.get(m.group(0), m.group(0)), expr)

def names_in(t): return set(re.findall(r'[A-Za-z_]\w*', t))

def literal_permutation(old_text, new_text, od, nd):
    """A swap of two literal column NAMES leaves every definition unchanged, so
    definition-based identity cannot see it. A permutation is distinguishable
    from a data edit: the value vectors MOVED between names rather than
    changing."""
    import hashlib
    def fps(text, d):
        rows, _ = otbl.evaluate(text)
        return {c: hashlib.sha256('\x1f'.join(f'{r.get(c)!r}' for r in rows).encode()
                                  ).hexdigest()[:12] for c in d if d[c] is None}
    try:
        o, n = fps(old_text, od), fps(new_text, nd)
    except Exception:
        return {}
    moved = {}
    for name in set(o) & set(n):
        if o[name] == n[name]: continue
        src = [m for m in o if o[m] == n[name] and m != name]
        if src: moved[name] = src[0]          # this name now holds what `src` held
    return moved


def check(old_text, new_text):
    od, orefs = defs(old_text)
    nd, nrefs = defs(new_text)
    findings, notes = [], []

    lit_perm = literal_permutation(old_text, new_text, od, nd)
    if (set(od) == set(nd) and all(od[c] == nd[c] for c in od) and not lit_perm):
        return [], ['no definitions or names changed; nothing to check']

    # 1. detect renames: a definition present in both versions under two names.
    rename = {}
    for _ in range(len(od) + 1):                     # iterate to a fixpoint
        changed = False
        for o, oexpr in od.items():
            if o in rename: continue
            for n, nexpr in nd.items():
                if n in rename.values(): continue
                if oexpr is None or nexpr is None: continue
                if norm(oexpr, rename) == nexpr and o != n:
                    rename[o] = n; changed = True; break
        if not changed: break

    # 2. rebinding: a name that exists in BOTH versions but whose definition,
    #    read through the renames, is not the same thing it used to be.
    rebound = {}
    for name in set(od) & set(nd):
        before, after = od[name], nd[name]
        if norm(before, rename) == after: continue   # same definition
        was = next((o for o, n in rename.items() if n == name), None)
        rebound[name] = (before, after, was)

    # 3. references whose TEXT did not change but whose referent did
    for label, oexpr in orefs.items():
        nexpr = nrefs.get(label)
        if nexpr is None or nexpr != oexpr:
            continue                                  # the author edited it; they saw it
        for nm in names_in(oexpr):
            if nm in rebound:
                before, after, was = rebound[nm]
                extra = f", which used to be called {was!r}" if was else ""
                findings.append(
                    f"MEANING DRIFT   {label}  ->  `{oexpr}`\n"
                    f"    unchanged reference to {nm!r}, but {nm!r} was rebound:\n"
                    f"      was:  {before if before else '(literal column)'}\n"
                    f"      now:  {after if after else '(literal column)'}{extra}")
    for name, src in lit_perm.items():
        findings.append(
            f"MEANING DRIFT   literal column {name!r} was rebound:\n"
            f"    it now holds the data that {src!r} held. Every unchanged "
            f"reference to {name!r} silently means something else.")
    for o, n in rename.items(): notes.append(f"rename: {o!r} -> {n!r}")
    return findings, notes

if __name__ == '__main__':
    f, notes = check(open(sys.argv[1]).read(), open(sys.argv[2]).read())
    for n in notes: print(f"  note: {n}")
    for x in f: print(x)
    print(f"\n{len(f)} meaning-drift finding(s)")
    sys.exit(1 if f else 0)
