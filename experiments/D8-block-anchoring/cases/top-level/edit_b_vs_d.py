#!/usr/bin/env python3
"""Anchoring a comment on a top-level list item across real edits, under
(b) list-as-one-block with two-stage resolution (list, then item inside it)
versus (d) item-as-block. Resolver: D8 anchor_eval3.reanchor2, hard policy.
Oracle: D8 anchor_eval2.line_oracle's rule, with line ranges taken from the
parse instead of text.index(). Usage: edit_b_vs_d.py NAME=REPO:PATHSPEC ..."""
import sys, os, re, random, difflib
from collections import Counter
D8 = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "D8-identity")
sys.path.insert(0, D8)
from anchor_eval import git, show, CTX           # noqa: E402
from anchor_eval3 import reanchor2, entropy_ok    # noqa: E402
import markdown_it                                 # noqa: E402

assert markdown_it.__version__ == "3.0.0"
MD = markdown_it.MarkdownIt("commonmark").enable("table")
FENCE = re.compile(r"\A---[ \t]*\n.*?\n---[ \t]*(\n|\Z)", re.S)
MARKER = re.compile(r"^\s*([-*+]|\d{1,9}[.)])[ \t]?")


def parse(text):
    m = FENCE.match(text)
    body = (text[m.end():] if m else text).replace("\r\n", "\n").replace("\r", "\n")
    lines = body.split("\n")
    starts = [0]
    for l in lines:
        starts.append(starts[-1] + len(l) + 1)
    def span(a, b, skip=0):
        s = starts[a] + skip
        e = starts[b] - 1 if b > a else s
        raw = body[s:e]
        c = raw.strip()
        if not c:
            return None
        return {"content": c, "off": s + raw.index(c), "lines": (a, b)}
    B, ITEMS = [], []
    for t in MD.parse(body):
        if t.nesting == -1 or not t.block or t.map is None:
            continue
        if t.level == 0:
            x = span(*t.map)
            if x:
                x["list"] = t.type in ("bullet_list_open", "ordered_list_open")
                B.append(x)
        if t.type == "list_item_open" and t.level == 1:
            a, b = t.map
            mk = MARKER.match(lines[a])
            x = span(a, b, mk.end() if mk else 0)
            if x:
                ITEMS.append(x)
    return body, B, ITEMS


def oracle(li, lj, bi, bj):
    sm = difflib.SequenceMatcher(None, li, lj, autojunk=False)
    m = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            m[a + k] = b + k
    jj = {}
    for n, x in enumerate(bj):
        for L in range(*x["lines"]):
            jj[L] = n
    out = []
    for x in bi:
        nonblank = [L for L in range(*x["lines"]) if li[L].strip()]
        if not nonblank:
            out.append(("UNKNOWN", None)); continue
        mapped = [m[L] for L in nonblank if L in m]
        frac = len(mapped) / len(nonblank)
        if frac >= 0.5:
            tg = Counter(jj[L] for L in mapped if L in jj)
            out.append(("SURVIVED", tg.most_common(1)[0][0]) if tg else ("UNKNOWN", None))
        elif frac == 0.0:
            best = max((difflib.SequenceMatcher(None, x["content"], y["content"]).ratio() for y in bj), default=0)
            out.append(("DELETED", None) if best < 0.3 else ("UNKNOWN", None))
        else:
            out.append(("UNKNOWN", None))
    return out


def anchor(text, x):
    o, q = x["off"], x["content"]
    return {"quote": q, "prefix": text[max(0, o - CTX):o], "suffix": text[o + len(q):o + len(q) + CTX]}


def inside(item, blk):
    return blk["lines"][0] <= item["lines"][0] and item["lines"][1] <= blk["lines"][1]


def stage2(bodyj, anc, items):
    """Find the item inside the resolved list: the same reanchor2 hard policy,
    restricted to the items the resolved list contains."""
    return reanchor2(bodyj, anc, items, True)[1]


def classify(truth, tgt, hit):
    if truth == "SURVIVED":
        return "correct" if hit == tgt else ("loud" if hit is None else "WRONG")
    return "correct" if hit is None else "WRONG"


def run(repo, spec, gap, t, sf=60, cap=30, seed=7):
    rnd = random.Random(seed)
    files = [f for f in git(repo, "ls-files", *spec.split()).split("\n") if f.endswith(".md")]
    rnd.shuffle(files)
    for f in files[:sf]:
        cs = [c for c in git(repo, "log", "--format=%H", "--reverse", "--", f).split("\n") if c]
        if len(cs) < gap + 1:
            continue
        for s in range(0, len(cs) - gap, max(1, (len(cs) - gap) // 3 or 1)):
            ti, tj = show(repo, cs[s], f), show(repo, cs[s + gap], f)
            if not ti or not tj or ti == tj:
                continue
            bi_body, bi, ii = parse(ti)
            bj_body, bj, ij = parse(tj)
            li, lj = bi_body.split("\n"), bj_body.split("\n")
            orc_i = oracle(li, lj, ii, ij)
            t["pairs"] += 1
            idx = list(range(len(ii))); rnd.shuffle(idx)
            for k in idx[:cap]:
                it = ii[k]
                if len(it["content"]) < 20:
                    continue
                truth, tgt = orc_i[k]
                if truth == "UNKNOWN":
                    t["unknown"] += 1; continue
                t["n"] += 1
                if truth == "SURVIVED":
                    t["survived"] += 1
                ianc = anchor(bi_body, it)
                # (d): the item is the block
                hit_d = reanchor2(bj_body, ianc, ij, True)[1]
                # (b): resolve the parent list, then the item inside it
                parent = next(x for x in bi if inside(it, x))
                hit_b = None
                lh = reanchor2(bj_body, anchor(bi_body, parent), bj, True)[1]
                if lh is not None:
                    sub = [n for n, y in enumerate(ij) if inside(y, bj[lh])]
                    h = stage2(bj_body, ianc, [ij[n] for n in sub])
                    hit_b = sub[h] if h is not None else None
                    if h is None: t["b_stage2_none"] += 1
                else:
                    t["b_stage1_none"] += 1
                if any(parent["content"] == y["content"] for y in bj):
                    t["parent_exact"] += 1
                cd, cb = classify(truth, tgt, hit_d), classify(truth, tgt, hit_b)
                t["d:" + cd] += 1; t["b:" + cb] += 1
                t[f"pair:{cb}/{cd}"] += 1


def main():
    for a in sys.argv[1:]:
        name, rest = a.split("=", 1)
        repo, spec = rest.split(":", 1)
        for gap in (5, 25):
            t = Counter()
            run(repo, spec, gap, t)
            n = t["n"]
            print(f"### {name} gap={gap} pairs={t['pairs']} item-anchors={n} survived={t['survived']} unknown={t['unknown']} parent-list-unchanged={t['parent_exact']}")
            if not n:
                continue
            for d in ("b", "d"):
                print(f"  {d}: correct {100*t[d+':correct']/n:5.1f}%  loud {100*t[d+':loud']/n:5.1f}%  SILENT-WRONG {100*t[d+':WRONG']/n:5.2f}% (n={t[d+':WRONG']})")
            print(f"  b stage1 refused={t['b_stage1_none']} stage2 refused={t['b_stage2_none']}")
            print("  b/d: " + " ".join(f"{k[5:]}={v}" for k, v in sorted(t.items()) if k.startswith("pair:")))


if __name__ == "__main__":
    main()
