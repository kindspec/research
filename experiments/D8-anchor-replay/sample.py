#!/usr/bin/env python3
"""Draw a stratified sample of replay.py's comments for labelling,
and write one blind packet per comment.

The word oracle cannot place a moved paragraph, and its placements are
difflib's, not a reader's. A labelled sample measures both: how often the
oracle is wrong where it places a comment, and how many of the comments it
does not place had text that survived.

Each comment in `replay.py --dump` falls in one stratum: the oracle's class
(`placed`, the span survives where the oracle puts it; `gone`; `unplaced`,
not counted) crossed with the resolver's (`loud` or `resolves`). Each
stratum is sampled at random up to its cap (CAPS). A packet holds the file's
two versions as numbered paragraphs, one line each with whitespace runs as
one space, and marks the commented span; it says nothing of the resolver's
status or the oracle's truth. Those go to KEYDIR/key.jsonl, which the
labellers are not given.

Usage:
    python3 -I sample.py --blockspec PATH --clone NAME=PATH --dump JSONL --gap N
        --packets DIR --keydir DIR
"""

import argparse
import json
import os
import random
import sys
from collections import defaultdict

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import replay  # noqa: E402

SEED = 11
CAPS = {
    ("placed", "loud"): 60,
    ("placed", "resolves"): 30,
    ("gone", "loud"): 25,
    ("gone", "resolves"): 25,
    ("unplaced", "loud"): 60,
    ("unplaced", "resolves"): 30,
}
MARK = ("⟦", "⟧")


def stratum(row):
    oracle = "unplaced" if row["verdict"] is None else "gone" if row["truth"] == "GONE" else "placed"
    return oracle, "resolves" if row["status"] in replay.RESOLVES else "loud"


def numbered(ps, mark=None):
    out = []
    for n, p in enumerate(ps):
        text = replay.flat(p.text)
        if mark is not None and n == mark[0]:
            words = p.text.split()
            s, span = mark[1], " ".join(words[mark[1] : mark[1] + replay.SPAN])
            text = " ".join(words[:s] + [MARK[0] + span + MARK[1]] + words[s + replay.SPAN :])
        out.append(f"[P{n}] {text}")
    return "\n".join(out)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blockspec", required=True)
    ap.add_argument("--clone", action="append", default=[], metavar="NAME=PATH")
    ap.add_argument("--dump", required=True)
    ap.add_argument("--gap", type=int, required=True)
    ap.add_argument("--packets", required=True)
    ap.add_argument("--keydir", required=True)
    args = ap.parse_args()
    A, R, head = replay.load_blockspec(args.blockspec)
    clones = dict(c.split("=", 1) for c in args.clone)
    rows = [json.loads(line) for line in open(args.dump, encoding="utf-8")]
    rows = [r for r in rows if r["gap"] == args.gap]
    by = defaultdict(list)
    for r in rows:
        by[stratum(r)].append(r)
    rnd = random.Random(SEED)
    picked = []
    sizes = {}
    for h, cap in CAPS.items():
        pool = by.get(h, [])
        sizes["/".join(h)] = len(pool)
        picked += [(h, r) for r in rnd.sample(pool, min(cap, len(pool)))]
    rnd.shuffle(picked)
    os.makedirs(args.packets, exist_ok=False)
    os.makedirs(args.keydir, exist_ok=True)
    ids = set()
    with open(os.path.join(args.keydir, "key.jsonl"), "w", encoding="utf-8") as key:
        for h, r in picked:
            while (i := f"{rnd.getrandbits(32):08x}") in ids:
                pass
            ids.add(i)
            repo = clones[r["arm"]]
            old = replay.git(repo, "show", f"{r['a']}:{r['file']}")
            new = replay.git(repo, "show", f"{r['b']}:{r['file']}")
            _, old_ps = replay.paragraphs(A, R, old)
            _, new_ps = replay.paragraphs(A, R, new)
            assert replay.flat(old_ps[r["para"]].text).count(r["span"]) >= 1
            body = (
                f"# Item {i}\n\nFile: {r['file']}\n\n"
                f"The comment is on paragraph P{r['para']} of the earlier version, on the "
                f"words marked {MARK[0]}like this{MARK[1]}.\n\n"
                f"## Earlier version\n\n{numbered(old_ps, (r['para'], r['start']))}\n\n"
                f"## Later version\n\n{numbered(new_ps)}\n"
            )
            with open(os.path.join(args.packets, f"{i}.md"), "w", encoding="utf-8") as f:
                f.write(body)
            key.write(json.dumps({"id": i, "stratum": "/".join(h), **r}, ensure_ascii=False) + "\n")
    with open(os.path.join(args.keydir, "strata.json"), "w", encoding="utf-8") as f:
        json.dump({"blockspec": head, "gap": args.gap, "seed": SEED, "sizes": sizes,
                   "caps": {"/".join(h): c for h, c in CAPS.items()}}, f, indent=1)
    print(f"# sample.py: gap {args.gap}, seed {SEED}, {len(picked)} packets")
    for h, n in sizes.items():
        print(f"  {h}: {n} comments, {min(CAPS[tuple(h.split('/'))], n)} sampled")


if __name__ == "__main__":
    main()
