#!/usr/bin/env python3
"""Break replay.py's grading on purpose, on a fixture where every truth is
known, and fail unless each break moves the counts exactly as it must.

Real arms rarely exercise every branch of the grader: on site-policy, a span
that is gone from its surviving paragraph is never counted. So the states
run on one fixed pair of versions instead, which holds one paragraph of each
kind:

- A and D, unchanged: the span survives;
- B, two lines, its second line rewritten, and the span with it: the
  paragraph survives (one of its two lines does), the span is gone;
- C, deleted, with nothing like it left: deleted.

Each state replaces the resolver, and must give exactly these counts:

| state | correct | loud | WRONG |
| --- | --: | --: | --: |
| as is | 4 | 0 | 0 |
| every comment resolves, on the first paragraph | 1 | 0 | 3 |
| every resolution one character off | 2 | 0 | 2 |
| every comment refused | 2 | 2 | 0 |

`as is` also checks the oracle: the span survives in 2, is gone in 1, and 1
paragraph is deleted. A break in the oracle or the grader moves one of
these, and the script exits 1.

Usage:
    python3 -I red_states.py --blockspec PATH
"""

import argparse
import os
import sys
from collections import Counter

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import replay  # noqa: E402

A_ = "Alpha is the first paragraph, and nothing in it changes between the versions."
B1 = "Bravo opens with a short line."
B2 = "then the scram limit and the shift log close it out here."
B2_NEW = "and nothing else follows from the second line at all now."
C_ = "0987 6543 2109 8765 4321 0000 1111 2222 3333 4444 5555 6666 7777."  # like nothing kept
D_ = "Delta closes the document and stays exactly as it was written before."
OLD = f"{A_}\n\n{B1}\n{B2}\n\n{C_}\n\n{D_}\n"
NEW = f"{A_}\n\n{B1}\n{B2_NEW}\n\n{D_}\n"

TRUTH = {"truth span survives": 2, "truth survived": 1, "truth deleted": 1}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blockspec", required=True)
    args = ap.parse_args()
    A, R, head = replay.load_blockspec(args.blockspec)
    real = A.resolve

    def first_paragraph(repo_in, queries, reader):
        out = real(repo_in, queries, reader)
        snap = A.Snapshot(reader, repo_in["tree"]["d.md"])
        first = next(lf for lf in snap.leaves if lf.type == "p")
        for got in out["records"].values():
            got.update(status="RESOLVED", leaf={"node": list(first.node.path)})
            got["span"] = got["span"] or [0, 1]
        return out

    def one_off(repo_in, queries, reader):
        out = real(repo_in, queries, reader)
        for got in out["records"].values():
            if got["status"] in replay.RESOLVES:
                got["span"] = [got["span"][0] + 1, got["span"][1] + 1]
        return out

    def refuse(repo_in, queries, reader):
        out = real(repo_in, queries, reader)
        for got in out["records"].values():
            got.update(status="REFUSED(red-state)", leaf=None, span=None)
        return out

    states = [
        ("as is", real, (4, 0, 0)),
        ("every comment resolves, on the first paragraph", first_paragraph, (1, 0, 3)),
        ("every resolution one character off", one_off, (2, 0, 2)),
        ("every comment refused", refuse, (2, 2, 0)),
    ]
    print(f"# red_states.py: blockspec reference at {head[:12]}; the fixture in this file")
    failed = False
    for name, resolver, want in states:
        A.resolve = resolver
        snap, old_ps = replay.paragraphs(A, R, OLD)
        _, new_ps = replay.paragraphs(A, R, NEW)
        t = Counter()
        replay.replay_pair(A, R, OLD, NEW, snap, old_ps, new_ps, t)
        got = (t["correct"], t["loud"], t["WRONG"])
        ok = got == want
        if name == "as is":
            truth = {k: t[k] for k in TRUTH}
            ok = ok and truth == TRUTH and t["comments"] == 4
        failed |= not ok
        print(
            f"{'PASS' if ok else 'FAIL'}  {name:48s} correct {got[0]}  loud {got[1]}  "
            f"WRONG {got[2]}   (want {want[0]}, {want[1]}, {want[2]})"
        )
    A.resolve = real
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
