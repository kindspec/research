#!/usr/bin/env python3
"""For each arm's sampled files (replay.py's own sample of FILES), count the
files whose `replay.versions` differs from `git log --reverse -- FILE`: those
with a commit that deletes the file or moves it away. An arm where none
does gets the pairs the plain history would give it; where any does, every
file sampled after it can get different pairs too, because one generator
draws every file's pairs in turn. No resolver is run.

Usage:
    python3 -I histcheck.py --clone NAME=PATH ... [--arm NAME ...]

with the clone names of ../D8-block-definitions/arms.json.
"""

import argparse
import json
import os
import random
import sys

sys.dont_write_bytecode = True
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import replay  # noqa: E402


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--clone", action="append", default=[], metavar="NAME=PATH")
    ap.add_argument("--arm", action="append", default=[])
    args = ap.parse_args()
    clones = dict(c.split("=", 1) for c in args.clone)
    print("# histcheck.py: sampled files whose versions differ from their git log; arms "
          + ", ".join(args.arm or ["all with a clone"]))
    for arm in json.load(open(replay.ARMS, encoding="utf-8"))["arms"]:
        repo = clones.get(arm["clone"])
        if repo is None or (args.arm and arm["name"] not in args.arm):
            continue
        if replay.git(repo, "rev-parse", "HEAD").strip() != arm["pin"] or replay.git(
                repo, "status", "--porcelain", "--untracked-files=no"):
            sys.exit(f"{arm['name']}: {repo} is not at its pin {arm['pin'][:12]} or has changes")
        rnd = random.Random(replay.SEED)
        files = [f for f in replay.git(repo, "ls-files", "--", *arm["pathspec"].split()).split("\n") if f]
        rnd.shuffle(files)
        sampled = files[: replay.FILES]
        differ = [f for f in sampled
                  if replay.versions(repo, f) != [c for c in replay.git(
                      repo, "log", "--format=%H", "--reverse", "--", f).split("\n") if c]]
        print(f"  {arm['name']}: {len(differ)} of {len(sampled)}")


if __name__ == "__main__":
    main()
