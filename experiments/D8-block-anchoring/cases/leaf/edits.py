#!/usr/bin/env python3
"""For paragraphs (>= MINLEN chars) that sit inside a top-level list, follow
each file's own history and compare, at file-version gap G, whether the
stage-1 exact quote still matches:
  under (b): the whole top-level list's text among top-level nodes of the later version
  under (f): the paragraph's inline text among all leaves of the later version
Counts 0 / 1 / >1 matches for each. Same extraction as D8-block-definitions/measure.py.
usage: edits.py REPO PATHSPEC GAP MAXFILES
"""
import re, subprocess, sys, random
from collections import Counter
import markdown_it

assert markdown_it.__version__ == "3.0.0"
md = markdown_it.MarkdownIt("commonmark").enable("table")
FENCE = re.compile(r"\A---\n.*?\n---\n", re.S)
MINLEN = 40


def git(repo, *a):
    return subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, check=True).stdout


def parse(text):
    m = FENCE.match(text)
    body = text[m.end():] if m else text
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    lines = body.split("\n")
    toks = md.parse(body)
    top = Counter()      # (b) contents
    leaves = Counter()   # (f) contents
    inlist = []          # (paragraph text, enclosing top-level list text)
    cur_list = None
    for i, t in enumerate(toks):
        if t.level == 0 and t.nesting == 1 and t.type in ("bullet_list_open", "ordered_list_open"):
            cur_list = "\n".join(lines[t.map[0]:t.map[1]]).strip()
        if t.level == 0 and t.nesting == -1 and t.type in ("bullet_list_close", "ordered_list_close"):
            cur_list = None
        if t.nesting == -1 or not t.block or t.map is None:
            continue
        if t.level == 0:
            top["\n".join(lines[t.map[0]:t.map[1]]).strip()] += 1
        if t.type == "paragraph_open":
            c = toks[i + 1].content.strip()
            leaves[c] += 1
            if cur_list is not None and len(c) >= MINLEN:
                inlist.append((c, cur_list))
        elif t.type == "heading_open":
            leaves["#" * int(t.tag[1:]) + " " + toks[i + 1].content.strip()] += 1
        elif t.type == "fence":
            leaves[f"{t.markup}{t.info}\n{t.content}{t.markup}"] += 1
        elif t.type == "code_block":
            leaves[t.content.strip("\n")] += 1
        elif t.type == "html_block":
            leaves[t.content.strip()] += 1
    return top, leaves, inlist


def bucket(n):
    return "0" if n == 0 else ("1" if n == 1 else ">1")


def main():
    repo, pathspec, gap, maxfiles = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    files = [f for f in git(repo, "ls-files", *pathspec.split()).split("\n") if f.endswith(".md")]
    random.Random(7).shuffle(files)
    files = files[:maxfiles]
    cross = Counter()
    pairs = 0
    listsize = []
    for f in files:
        revs = git(repo, "log", "--format=%H", "--", f).split()
        revs.reverse()
        for k in range(0, len(revs) - gap):
            try:
                a = git(repo, "show", f"{revs[k]}:{f}")
                b = git(repo, "show", f"{revs[k + gap]}:{f}")
            except subprocess.CalledProcessError:
                continue
            ta, la, ia = parse(a)
            tb, lb, _ = parse(b)
            if not ia:
                continue
            pairs += 1
            for para, lst in ia:
                if ta[lst] != 1 or la[para] != 1:
                    continue  # anchor only blocks unique at the anchoring version
                listsize.append(len(lst) / len(para))
                cross[(bucket(tb[lst]), bucket(lb[para]))] += 1
    n = sum(cross.values())
    print(f"repo={repo} pathspec={pathspec!r} gap={gap} files={len(files)} pairs={pairs} anchors={n}")
    print("  (b) list exact  (f) leaf exact   count")
    for (bb, ff), c in sorted(cross.items()):
        print(f"  {bb:>14}  {ff:>14}  {c:6d}  {100*c/n:5.1f}%")
    b_hit = sum(c for (bb, ff), c in cross.items() if bb == "1")
    f_hit = sum(c for (bb, ff), c in cross.items() if ff == "1")
    f_amb = sum(c for (bb, ff), c in cross.items() if ff == ">1")
    b_amb = sum(c for (bb, ff), c in cross.items() if bb == ">1")
    print(f"  exact unique hit: (b) {b_hit} {100*b_hit/n:.1f}%   (f) {f_hit} {100*f_hit/n:.1f}%")
    print(f"  exact >1 (loud):  (b) {b_amb} {100*b_amb/n:.1f}%   (f) {f_amb} {100*f_amb/n:.1f}%")
    listsize.sort()
    if listsize:
        print(f"  list/paragraph length ratio: median {listsize[len(listsize)//2]:.1f}  p90 {listsize[int(len(listsize)*.9)]:.1f}")


main()
