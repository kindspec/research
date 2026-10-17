#!/usr/bin/env python3
"""Sort the loud comments of one gap in a `replay.py --dump` by how much
their paragraph changed: by the resolver's status; whether the target
paragraph is unchanged, changed only in whitespace, or edited; and whether
the span's stored context (CONTEXT code points each side) is still beside
it in the target. Each kind is printed with one example pair.

Usage:
    python3 -I kinds.py --blockspec PATH --clone NAME=PATH --dump JSONL --gap N
"""

import argparse
import json
import os
import sys
from collections import Counter

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import replay  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blockspec", required=True)
    ap.add_argument("--clone", action="append", default=[], metavar="NAME=PATH")
    ap.add_argument("--dump", required=True)
    ap.add_argument("--gap", type=int, required=True)
    args = ap.parse_args()
    A, R, head = replay.load_blockspec(args.blockspec)
    clones = dict(c.split("=", 1) for c in args.clone)
    rows = [json.loads(line) for line in open(args.dump, encoding="utf-8")]
    loud = [r for r in rows if r["gap"] == args.gap and r["verdict"] == "loud"]
    versions, kinds, example = {}, Counter(), {}
    for r in loud:
        k = (r["arm"], r["file"], r["a"], r["b"])
        if k not in versions:
            show = lambda c: replay.git(clones[r["arm"]], "show", f"{c}:{r['file']}")
            versions[k] = (replay.paragraphs(A, R, show(r["a"]))[1], replay.paragraphs(A, R, show(r["b"]))[1])
        old_ps, new_ps = versions[k]
        old, new = old_ps[r["para"]].text, new_ps[r["target"]].text
        s = old.index(r["span"])
        e = s + len(r["span"])
        context = old[max(0, s - A.CONTEXT) : e + A.CONTEXT] in new
        change = "unchanged" if old == new else "whitespace only" if replay.flat(old) == replay.flat(new) else "edited"
        kind = (r["status"], change, "context kept" if context else "context changed")
        kinds[kind] += 1
        example.setdefault(kind, f"{r['file']} {r['a'][:8]}..{r['b'][:8]} P{r['para']}")
    print(f"# kinds.py: gap {args.gap}, blockspec reference at {head[:12]}, {len(loud)} loud comments")
    for kind, n in kinds.most_common():
        print(f"  {n:4d}  {', '.join(kind)}   e.g. {example[kind]}")


if __name__ == "__main__":
    main()
