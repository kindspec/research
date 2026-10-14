#!/usr/bin/env python3
"""Stage-1 resolution under D8's hardened policy (anchor_eval3.reanchor2, hard=True),
for paragraphs >= 40 chars inside a top-level list, at file-version gap G.
  (b) the anchored block is the enclosing top-level list; candidates are top-level nodes
  (f) the anchored block is the paragraph; candidates are every leaf at any depth
Block offset = start of the node's first source line (inline content is not a
substring of the file once list indentation is stripped).
Correctness proxy (no independent oracle): (f) is counted CORRECT when the resolved
leaf is the paragraph's own successor as judged by (b) or (f) agreeing on the line
range; reported only as status counts plus agreement between the two.
usage: edits2.py REPO PATHSPEC GAP MAXFILES
"""
import os, re, subprocess, sys, random
from collections import Counter
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", "D8-identity"))
from anchor_eval3 import reanchor2
from anchor_eval import CTX
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
    loff = [0]
    for l in lines:
        loff.append(loff[-1] + len(l) + 1)
    toks = md.parse(body)
    top, leaves, inlist = [], [], []
    cur = None
    for i, t in enumerate(toks):
        if t.level == 0 and t.nesting == -1 and t.type in ("bullet_list_close", "ordered_list_close"):
            cur = None
        if t.nesting == -1 or not t.block or t.map is None:
            continue
        span = (t.map[0], t.map[1])
        if t.level == 0:
            blk = {"content": "\n".join(lines[span[0]:span[1]]).strip(), "off": loff[span[0]], "span": span}
            top.append(blk)
            if t.type in ("bullet_list_open", "ordered_list_open"):
                cur = len(top) - 1
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
        if c is not None:
            leaves.append({"content": c, "off": loff[span[0]], "span": span})
            if t.type == "paragraph_open" and cur is not None and t.level > 0 and len(c) >= MINLEN:
                inlist.append((len(leaves) - 1, cur))
    return body, top, leaves, inlist


def anchor(text, blk):
    o, q = blk["off"], blk["content"]
    end = o + len(q) if text[o:o + len(q)] == q else text.find("\n\n", o)
    end = len(text) if end < 0 else end
    return {"quote": q, "prefix": text[max(0, o - CTX):o], "suffix": text[end:end + CTX]}


def ok(st):
    return st in ("EXACT", "EXACT_CTX", "FUZZY")


def main():
    repo, pathspec, gap, maxfiles = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4])
    files = [f for f in git(repo, "ls-files", *pathspec.split()).split("\n") if f.endswith(".md")]
    random.Random(7).shuffle(files)
    files = files[:maxfiles]
    sb, sf, both = Counter(), Counter(), Counter()
    n = pairs = 0
    for f in files:
        revs = git(repo, "log", "--format=%H", "--", f).split()[::-1]
        for k in range(0, len(revs) - gap):
            try:
                A = git(repo, "show", f"{revs[k]}:{f}")
                B = git(repo, "show", f"{revs[k + gap]}:{f}")
            except subprocess.CalledProcessError:
                continue
            ta, topa, leava, ia = parse(A)
            tb, topb, leavb, _ = parse(B)
            if not ia:
                continue
            pairs += 1
            for li, ti in ia:
                lq, tq = leava[li]["content"], topa[ti]["content"]
                if sum(x["content"] == lq for x in leava) != 1 or sum(x["content"] == tq for x in topa) != 1:
                    continue
                n += 1
                stb, ib = reanchor2(tb, anchor(ta, topa[ti]), topb, True)
                stf, jf = reanchor2(tb, anchor(ta, leava[li]), leavb, True)
                sb[stb] += 1
                sf[stf] += 1
                if ok(stf) and ok(stb):
                    inside = topb[ib]["span"][0] <= leavb[jf]["span"][0] < topb[ib]["span"][1]
                    both["f leaf lies inside b's list" if inside else "f leaf OUTSIDE b's list"] += 1
                elif ok(stf):
                    both["f resolves, b refuses/orphans"] += 1
                elif ok(stb):
                    both["b resolves, f refuses/orphans"] += 1
                else:
                    both["neither resolves"] += 1
    print(f"repo={repo} pathspec={pathspec!r} gap={gap} files={len(files)} pairs={pairs} anchors={n}")
    for lab, c in (("(b) list", sb), ("(f) leaf", sf)):
        print(f"  {lab}: " + "  ".join(f"{k}={v} ({100*v/n:.1f}%)" for k, v in sorted(c.items())))
    for k, v in sorted(both.items()):
        print(f"  {k}: {v} ({100*v/n:.1f}%)")


main()
