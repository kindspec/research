import os, sys, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edit_b_vs_d import parse, anchor, inside, reanchor2, git
from collections import Counter
for a in sys.argv[1:]:
    name, rest = a.split("=", 1); repo, spec = rest.split(":", 1)
    t = Counter()
    for f in [f for f in git(repo, "ls-files", *spec.split()).split("\n") if f.endswith(".md")]:
        txt = open(f"{repo}/{f}", encoding="utf-8").read()
        if "THIS FILE IS AUTO-GENERATED" in txt or "auto_generated: true" in txt[:2000]: continue
        body, B, I = parse(txt)
        for k, it in enumerate(I):
            if len(it["content"]) < 40: continue
            t["n"] += 1
            st, h = reanchor2(body, anchor(body, it), I, True)
            if h != k: t["d_loud"] += 1
            par = next(n for n, x in enumerate(B) if inside(it, x))
            st, lh = reanchor2(body, anchor(body, B[par]), B, True)
            if lh != par: t["b_loud"] += 1; continue
            sub = [n for n, y in enumerate(I) if inside(y, B[lh])]
            st, h = reanchor2(body, anchor(body, it), [I[n] for n in sub], True)
            if h is None or sub[h] != k: t["b_loud"] += 1
    n = t["n"]
    print(f"{name}: items>=40ch={n}  at-rest loud (d)={t['d_loud']} ({100*t['d_loud']/n:.2f}%)  (b)={t['b_loud']} ({100*t['b_loud']/n:.2f}%)")
