#!/usr/bin/env python3
"""Break each part of replay.py's grading on purpose and show that the counts
move the way they must. A grader that cannot see a wrong resolution would
report a perfect resolver.

Each state runs one arm at one gap on the first FILES files, with:

- `as is`: nothing broken, the control;
- `resolver picks the first paragraph`: every resolution that resolves is
  moved to the document's first paragraph, its span unchanged. WRONG must
  appear;
- `resolver refuses everything`: every resolution is
  `REFUSED(red-state)`. Every surviving span must be `loud`, and nothing
  `correct` among them;
- `oracle says deleted`: every paragraph is deleted. Every comment that
  resolves must be WRONG.

Usage:
    python3 -I red_states.py --blockspec PATH --clone NAME=PATH --arm NAME [--gap N]
"""

import argparse
import json
import os
import sys

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import replay  # noqa: E402

FILES = 5


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blockspec", required=True)
    ap.add_argument("--clone", action="append", default=[], metavar="NAME=PATH")
    ap.add_argument("--arm", required=True)
    ap.add_argument("--gap", type=int, default=1)
    args = ap.parse_args()
    A, R, head = replay.load_blockspec(args.blockspec)
    clones = dict(c.split("=", 1) for c in args.clone)
    arms = json.load(open(os.path.join(HERE, "..", "D8-block-definitions", "arms.json")))["arms"]
    (arm,) = [a for a in arms if a["name"] == args.arm]
    repo = clones[arm["clone"]]
    replay.FILES = FILES
    real_resolve, real_oracle = A.resolve, replay.line_oracle

    def first_paragraph(repo_in, queries, reader):
        out = real_resolve(repo_in, queries, reader)
        for got in out["records"].values():
            if got["status"] in replay.RESOLVES:
                snap = A.Snapshot(reader, repo_in["tree"]["d.md"])
                first = next(lf for lf in snap.leaves if lf.type == "p")
                got["leaf"] = {"node": list(first.node.path), "type": "paragraph"}
        return out

    def refuse(repo_in, queries, reader):
        out = real_resolve(repo_in, queries, reader)
        for got in out["records"].values():
            got.update(status="REFUSED(red-state)", leaf=None, span=None)
        return out

    def deleted(old, new, old_ps, new_ps):
        return [("DELETED", None) for _ in old_ps]

    states = [
        ("as is", real_resolve, real_oracle),
        ("resolver picks the first paragraph", first_paragraph, real_oracle),
        ("resolver refuses everything", refuse, real_oracle),
        ("oracle says deleted", real_resolve, deleted),
    ]
    print(f"# red_states.py: blockspec reference at {head[:12]}; {arm['name']} gap={args.gap}, files={FILES}")
    for name, resolver, oracle in states:
        A.resolve, replay.line_oracle = resolver, oracle
        t = replay.run_arm(A, R, arm["name"], repo, arm["pathspec"], args.gap, [])
        print(
            f"{name:40s} correct {t['correct']:5d}  loud {t['loud']:5d}  WRONG {t['WRONG']:5d}  "
            f"span survives {t['span survives']:5d}"
        )
    A.resolve, replay.line_oracle = real_resolve, real_oracle


if __name__ == "__main__":
    main()
