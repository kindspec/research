#!/usr/bin/env python3
"""Which node should stage 1 of a quote anchor resolve, when the anchored text
sits inside a list or a block quote? (kindspec/blockspec#4)

D8 §3.4 and §7.3 resolve an anchor in two stages: stage 1 finds a block, stage
2 finds the anchored span inside it. This measures stage 1's scope, with D8's
independent line oracle, under three choices and one combination:

  B    the top-level node that contains the text (a list is one node); then the
       leaf inside it
  D    the smallest list item that contains the text (the top-level node if
       none does, as in a block quote); then the leaf inside it
  F    the leaf itself: the paragraph, heading, code block, HTML block or table
  F+B  F, and B whenever F's exact quote is ambiguous after context
  F+Bc F, and B only for an anchor whose leaf was already ambiguous in the
       version it was taken against (the anchoring client can see that)

The anchored text is always a leaf of at least MINLEN characters that lies
inside a top-level list or block quote: the only place the four differ. Every
stage uses D8's hardened policy (anchor_eval3.reanchor2, hard=True). Truth is
D8's line oracle (anchor_eval2.line_oracle's rule) applied to leaves: the leaf
that holds the majority of the anchored leaf's surviving lines.

Each anchor is classified correct, loud (refused or orphaned though the text
survived) or WRONG (resolved to a leaf the oracle did not pick, or resolved
although the oracle says the text was deleted). It also reports, at the pinned
tree, how many anchors refuse loudly against their own unchanged file, and the
length of the stage-1 quote each scheme stores.

Usage:
    python3 -I scope.py --clone NAME=PATH ... > results.txt
with the clone names of ../D8-block-definitions/arms.json. Each clone must be
at its pin with no tracked changes.
"""
import argparse
import difflib
import json
import os
import random
import re
import subprocess
import sys
from collections import Counter

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "D8-identity"))
from anchor_eval import CTX  # noqa: E402
from anchor_eval3 import reanchor2, entropy_ok, FUZZ, MARGIN, CTXMIN  # noqa: E402
import markdown_it  # noqa: E402

EXPECT_PARSER = "3.0.0"
MINLEN = 20
ARMS = ("rust-book", "obsidian-help", "cmspec", "k8s-en", "cncf-toc", "site-policy")
GAPS = (5, 25)
SAMPLE_FILES, SAMPLE_ANCHORS, SEED = 60, 30, 7
SCHEMES = ("B", "D", "F", "F+B", "F+Bc")


def die(msg, code=2):
    print(f"scope.py: {msg}", file=sys.stderr)
    sys.exit(code)


def git(repo, *a):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True)
    if r.returncode != 0:
        die(f"git -C {repo} {' '.join(a)}: exit {r.returncode}: {r.stderr.strip()}")
    return r.stdout


def check_clone(name, repo, pin):
    if not os.path.isdir(repo):
        die(f"{name}: clone does not exist: {repo}")
    head = git(repo, "rev-parse", "HEAD").strip()
    if head != pin:
        die(f"{name}: HEAD is {head}, pinned at {pin}")
    if git(repo, "status", "--porcelain", "--untracked-files=no").strip():
        die(f"{name}: tracked files differ from HEAD")
    if git(repo, "rev-parse", "--is-shallow-repository").strip() == "true":
        die(f"{name}: shallow clone; this walks file history")
    print(f"arm {name} HEAD {head} (pin)", file=sys.stderr, flush=True)


FENCE = re.compile(r"---[ \t]*\n.*?\n---[ \t]*(\n|$)", re.DOTALL)
GENERATED = re.compile(r"THIS FILE IS AUTO-GENERATED|^auto_generated:[ \t]*true[ \t]*$",
                       re.IGNORECASE | re.MULTILINE)
MARKER = re.compile(r"^[ \t]*(?:[-*+]|\d{1,9}[.)])(?:[ \t]+|$)")
QUOTE = re.compile(r"^(?:[ \t]*>[ \t]?)+")
LIST_OPEN = ("bullet_list_open", "ordered_list_open")


def show(repo, rev, path):
    if not git(repo, "ls-tree", rev, "--", path).strip():
        return ""
    return git(repo, "show", f"{rev}:{path}")


class Doc:
    """One file version. Every unit is a dict with content, a line range
    [a, b) of the body, and off/end: the body offsets its context is read
    around."""

    def __init__(self, md, text):
        m = FENCE.match(text)
        body = (text[m.end():] if m else text).replace("\r\n", "\n").replace("\r", "\n")
        self.body = body
        self.lines = lines = body.split("\n")
        starts = [0]
        for ln in lines:
            starts.append(starts[-1] + len(ln) + 1)

        def unit(a, b, content):
            if not content:
                return None
            first = lines[a]
            col = first.find(content.split("\n", 1)[0][:20])
            off = starts[a] + (col if col >= 0 else 0)
            if body[off:off + len(content)] == content:
                end = off + len(content)
            else:
                end = max(off, starts[b] - 1 if b > a else off)
            return {"content": content, "lines": (a, b), "off": off, "end": end}

        self.top, self.items, self.leaves = [], [], []
        self.leaf_top, self.leaf_item, self.leaf_contained = [], [], []
        toks = md.parse(body)
        stack = []  # open containers: (type, unit index or None)
        cur_top = None
        quotes = 0
        for i, t in enumerate(toks):
            if t.type == "blockquote_open":
                quotes += 1
            elif t.type == "blockquote_close":
                quotes -= 1
            if t.nesting == -1:
                if t.type == "list_item_close":
                    stack.pop()
                continue
            if not t.block or t.map is None:
                continue
            a, b = t.map
            if t.level == 0:
                u = unit(a, b, "\n".join(lines[a:b]).strip())
                cur_top = None
                if u:
                    u["container"] = t.type in LIST_OPEN or t.type == "blockquote_open"
                    self.top.append(u)
                    cur_top = len(self.top) - 1
            if t.type == "list_item_open":
                ls = lines[a:b]
                if quotes:
                    ls = [QUOTE.sub("", ln, count=1) for ln in ls]
                c = "\n".join([MARKER.sub("", ls[0], count=1)] + [ln.lstrip() for ln in ls[1:]]).strip()
                u = unit(a, b, c)
                if u:
                    self.items.append(u)
                stack.append(len(self.items) - 1 if u else None)
                continue
            c = None
            if t.type == "paragraph_open":
                c = toks[i + 1].content.strip()
            elif t.type == "heading_open":
                c = "#" * int(t.tag[1:]) + " " + toks[i + 1].content.strip()
            elif t.type == "fence":
                c = f"{t.markup}{t.info}\n{t.content}{t.markup}"
            elif t.type == "code_block":
                c = t.content.strip("\n")
            elif t.type == "html_block":
                c = t.content.strip()
            elif t.type == "table_open":
                c = "\n".join(ln.strip() for ln in lines[a:b]).strip()
            if c is None:
                continue
            u = unit(a, b, c)
            if not u:
                continue
            self.leaves.append(u)
            self.leaf_top.append(cur_top)
            inner = next((s for s in reversed(stack) if s is not None), None)
            self.leaf_item.append(inner)
            self.leaf_contained.append(t.level > 0)


def resolve(text, anc, cand, hard=True):
    """D8 anchor_eval3.reanchor2, with one change: a candidate's suffix context
    is read from its 'end', not from off + len(content), because a nested
    leaf's content is not a substring of the file. For a top-level node the
    two are the same, and main() checks that they agree."""
    q = anc["quote"]
    hits = [i for i, b in enumerate(cand) if b["content"] == q]
    if len(hits) == 1:
        return "EXACT", hits[0]

    def ctxscore(i):
        o, e = cand[i]["off"], cand[i]["end"]
        pre, suf = text[max(0, o - CTX):o], text[e:e + CTX]
        return (difflib.SequenceMatcher(None, pre, anc["prefix"]).ratio()
                + difflib.SequenceMatcher(None, suf, anc["suffix"]).ratio()) / 2
    if len(hits) > 1:
        sc = sorted(((ctxscore(i), i) for i in hits), reverse=True)
        if sc[0][0] - sc[1][0] < 0.05:
            return "AMBIGUOUS", (None if hard else sc[0][1])
        return "EXACT_CTX", sc[0][1]
    if hard and not entropy_ok(q):
        return "REFUSED_LOWENTROPY", None
    cands = []
    for i, b in enumerate(cand):
        r = difflib.SequenceMatcher(None, q, b["content"]).ratio()
        if r >= FUZZ:
            cands.append((r, i))
    if not cands:
        return "ORPHAN", None
    cands.sort(reverse=True)
    if hard:
        if len(cands) > 1 and cands[0][0] - cands[1][0] < MARGIN:
            return "REFUSED_MARGIN", None
        if ctxscore(cands[0][1]) < CTXMIN:
            return "REFUSED_CONTEXT", None
    return "FUZZY", cands[0][1]


def anchor(doc, u):
    return {"quote": u["content"], "prefix": doc.body[max(0, u["off"] - CTX):u["off"]],
            "suffix": doc.body[u["end"]:u["end"] + CTX]}


def inside(inner, outer):
    return outer["lines"][0] <= inner["lines"][0] and inner["lines"][1] <= outer["lines"][1]


CHECKED = Counter()


def two_stage(dj, scope_anchor, scope_cands, leaf_anchor):
    st, h = resolve(dj.body, scope_anchor, scope_cands)
    if h is None:
        return st, None
    sub = [n for n, y in enumerate(dj.leaves) if inside(y, scope_cands[h])]
    st2, k = resolve(dj.body, leaf_anchor, [dj.leaves[n] for n in sub])
    return ("2:" + st2 if k is None else st), (sub[k] if k is not None else None)


def scope_of(di, n, scheme):
    """(stage-1 unit, candidate list name) for leaf n of doc di."""
    if scheme == "B":
        return di.top[di.leaf_top[n]], "top"
    if scheme == "D":
        k = di.leaf_item[n]
        return (di.items[k], "items") if k is not None else (di.top[di.leaf_top[n]], "top")
    raise ValueError(scheme)


def resolve_all(di, dj, n):
    """{scheme: (status, leaf index in dj or None)} for leaf n of di."""
    la = anchor(di, di.leaves[n])
    out = {}
    for s in ("B", "D"):
        u, which = scope_of(di, n, s)
        cands = dj.top if which == "top" else dj.items
        out[s] = two_stage(dj, anchor(di, u), cands, la)
        if s == "B":
            # The resolve() copy must agree with reanchor2 itself on top-level nodes.
            ref = reanchor2(dj.body, anchor(di, u), dj.top, True)
            mine = resolve(dj.body, anchor(di, u), dj.top)
            CHECKED["stage1 B vs reanchor2"] += 1
            if ref != mine:
                CHECKED["stage1 B vs reanchor2 DIFFER"] += 1
    out["F"] = resolve(dj.body, la, dj.leaves)
    out["F+B"] = out["B"] if out["F"][0] == "AMBIGUOUS" else out["F"]
    at_creation = out["F"] if di is dj else resolve(di.body, la, di.leaves)
    out["F+Bc"] = out["B"] if at_creation[1] != n else out["F"]
    return out


def targets(d):
    return [n for n, u in enumerate(d.leaves)
            if d.leaf_contained[n] and d.leaf_top[n] is not None and len(u["content"]) >= MINLEN]


def oracle(di, dj):
    """D8 anchor_eval2.line_oracle's rule over leaves: lines mapped by difflib
    on the line sequence; >= half of a leaf's non-blank lines survive -> the
    leaf holding most of them; none survive and no leaf is >= 0.3 similar ->
    deleted; anything else unknown."""
    li, lj = di.lines, dj.lines
    sm = difflib.SequenceMatcher(None, li, lj, autojunk=False)
    m = {}
    for a, b, k in sm.get_matching_blocks():
        for x in range(k):
            m[a + x] = b + x
    owner = {}
    for n, u in enumerate(dj.leaves):
        for L in range(*u["lines"]):
            owner.setdefault(L, n)
    out = {}
    for n in targets(di):
        u = di.leaves[n]
        nonblank = [L for L in range(*u["lines"]) if li[L].strip()]
        if not nonblank:
            out[n] = ("UNKNOWN", None)
            continue
        mapped = [m[L] for L in nonblank if L in m]
        frac = len(mapped) / len(nonblank)
        if frac >= 0.5:
            tg = Counter(owner[L] for L in mapped if L in owner)
            out[n] = ("SURVIVED", tg.most_common(1)[0][0]) if tg else ("UNKNOWN", None)
        elif frac == 0.0:
            best = max((difflib.SequenceMatcher(None, u["content"], y["content"]).ratio()
                        for y in dj.leaves), default=0)
            out[n] = ("DELETED", None) if best < 0.3 else ("UNKNOWN", None)
        else:
            out[n] = ("UNKNOWN", None)
    return out


def classify(truth, tgt, hit):
    if truth == "SURVIVED":
        return "correct" if hit == tgt else ("loud" if hit is None else "WRONG")
    return "correct" if hit is None else "WRONG"


def edits(md, repo, pathspec, gap):
    rnd = random.Random(SEED)
    t = Counter()
    files = [f for f in git(repo, "ls-files", *pathspec.split()).split("\n") if f.endswith(".md")]
    if not files:
        die(f"{repo}: pathspec {pathspec!r} selects no .md files")
    rnd.shuffle(files)
    for f in files[:SAMPLE_FILES]:
        cs = [c for c in git(repo, "log", "--format=%H", "--reverse", "--", f).split("\n") if c]
        if len(cs) < gap + 1:
            continue
        for s in range(0, len(cs) - gap, max(1, (len(cs) - gap) // 3 or 1)):
            ti, tj = show(repo, cs[s], f), show(repo, cs[s + gap], f)
            if not ti or not tj or ti == tj or GENERATED.search(ti) or GENERATED.search(tj):
                continue
            di, dj = Doc(md, ti), Doc(md, tj)
            orc = oracle(di, dj)
            t["pairs"] += 1
            idx = targets(di)
            rnd.shuffle(idx)
            for n in idx[:SAMPLE_ANCHORS]:
                truth, tgt = orc[n]
                if truth == "UNKNOWN":
                    t["unknown"] += 1
                    continue
                t["n"] += 1
                t["truth:" + truth] += 1
                res = resolve_all(di, dj, n)
                for s in SCHEMES:
                    t[s + ":" + classify(truth, tgt, res[s][1])] += 1
                    t[s + ":status:" + res[s][0]] += 1
                cb, cf = classify(truth, tgt, res["B"][1]), classify(truth, tgt, res["F"][1])
                t[f"B/F:{cb}/{cf}"] += 1
                cd = classify(truth, tgt, res["D"][1])
                t[f"D/F:{cd}/{cf}"] += 1
    return t


def at_rest(md, repo, pathspec, pin):
    t = Counter()
    size = {s: [] for s in ("B", "D", "F")}
    for f in [f for f in git(repo, "ls-files", *pathspec.split()).split("\n") if f.endswith(".md")]:
        txt = show(repo, pin, f)
        if not txt or GENERATED.search(txt):
            continue
        d = Doc(md, txt)
        for n in targets(d):
            t["n"] += 1
            res = resolve_all(d, d, n)
            for s in SCHEMES:
                if res[s][1] != n:
                    t[s + ":loud" if res[s][1] is None else s + ":WRONG"] += 1
            for s in ("B", "D"):
                size[s].append(len(scope_of(d, n, s)[0]["content"]))
            size["F"].append(len(d.leaves[n]["content"]))
    return t, size


def pct(a, n):
    return f"{100 * a / n:5.1f}%" if n else "    -"


def q(v, p):
    v = sorted(v)
    return v[int(p * (len(v) - 1))] if v else 0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clone", action="append", default=[], metavar="NAME=PATH")
    ap.add_argument("--arm", action="append", default=[], help="limit to these arms")
    a = ap.parse_args()
    if markdown_it.__version__ != EXPECT_PARSER:
        die(f"markdown-it-py {markdown_it.__version__}, expected {EXPECT_PARSER}")
    md = markdown_it.MarkdownIt("commonmark").enable("table")
    clones = dict(c.split("=", 1) for c in a.clone)
    arms = json.load(open(os.path.join(HERE, "..", "D8-block-definitions", "arms.json")))["arms"]
    run = [x for x in arms if x["name"] in ARMS and (not a.arm or x["name"] in a.arm)]
    if not run:
        die("no arm selected")
    for x in run:
        if x["clone"] not in clones:
            die(f"{x['name']}: no --clone {x['clone']}=PATH")
        x["repo"] = clones[x["clone"]]
        check_clone(x["name"], x["repo"], x["pin"])

    print(f"# scope.py: markdown-it-py {markdown_it.__version__}, commonmark + table;"
          f" MINLEN={MINLEN}, files={SAMPLE_FILES}, anchors/pair={SAMPLE_ANCHORS}, seed={SEED}")
    print("# anchored text: a leaf inside a top-level list or block quote")
    print("\n## At rest: each anchor resolved against its own unchanged file\n")
    print(f"{'arm':<15}{'anchors':>9}" + "".join(f"{s + ' loud':>14}{s + ' WRONG':>11}" for s in SCHEMES))
    sizes = {}
    for x in run:
        t, size = at_rest(md, x["repo"], x["pathspec"], x["pin"])
        sizes[x["name"]] = size
        n = t["n"]
        print(f"{x['name']:<15}{n:>9}" + "".join(
            f"{t[s + ':loud']:>8} {pct(t[s + ':loud'], n):>5}{t[s + ':WRONG']:>11}" for s in SCHEMES))

    print("\n## Stored stage-1 quote, characters, at rest (median / p90 / max)\n")
    for x in run:
        sz = sizes[x["name"]]
        print(f"{x['name']:<15}" + "".join(
            f"  {s}: {q(sz[s], .5):>5} / {q(sz[s], .9):>6} / {max(sz[s], default=0):>6}" for s in ("B", "D", "F"))
            + f"   B/F median ratio {q([b / f for b, f in zip(sz['B'], sz['F'])], .5):.1f}")

    print("\n## Under real edits, gap = file versions apart\n")
    for x in run:
        for gap in GAPS:
            t = edits(md, x["repo"], x["pathspec"], gap)
            n = t["n"]
            print(f"### {x['name']} gap={gap} pairs={t['pairs']} anchors={n}"
                  f" survived={t['truth:SURVIVED']} deleted={t['truth:DELETED']} unknown={t['unknown']}")
            if not n:
                continue
            for s in SCHEMES:
                print(f"  {s:<4} correct {pct(t[s + ':correct'], n)}  loud {pct(t[s + ':loud'], n)}"
                      f"  WRONG {pct(t[s + ':WRONG'], n)} (n={t[s + ':WRONG']})"
                      f"  exact {pct(t[s + ':status:EXACT'], n)}")
            print("  B/F " + " ".join(f"{k[4:]}={v}" for k, v in sorted(t.items()) if k.startswith("B/F:")))
            print("  D/F " + " ".join(f"{k[4:]}={v}" for k, v in sorted(t.items()) if k.startswith("D/F:")))
    print(f"\n# resolve() checked against reanchor2 on {CHECKED['stage1 B vs reanchor2']} stage-1 B lookups;"
          f" differ: {CHECKED['stage1 B vs reanchor2 DIFFER']}")
    if CHECKED["stage1 B vs reanchor2 DIFFER"]:
        die("resolve() disagrees with D8's reanchor2 on top-level nodes", 1)


if __name__ == "__main__":
    main()
