import os, sys, statistics
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from edit_b_vs_d import parse, git
for a in sys.argv[1:]:
    name, rest = a.split("=", 1); repo, spec = rest.split(":", 1)
    L, I, items_per = [], [], []
    for f in [f for f in git(repo, "ls-files", *spec.split()).split("\n") if f.endswith(".md")]:
        body, B, IT = parse(open(f"{repo}/{f}", encoding="utf-8").read())
        for x in B:
            if x["list"]:
                L.append(len(x["content"])); items_per.append(sum(1 for y in IT if x["lines"][0] <= y["lines"][0] < x["lines"][1]))
        I += [len(y["content"]) for y in IT]
    q = lambda v, p: sorted(v)[int(p * (len(v) - 1))]
    print(f"{name}: lists={len(L)} chars median={q(L,.5)} p90={q(L,.9)} max={max(L)}; items/list median={q(items_per,.5)} p90={q(items_per,.9)}; item chars median={q(I,.5)}")
