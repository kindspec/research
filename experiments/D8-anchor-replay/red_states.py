#!/usr/bin/env python3
"""Break replay.py's grading on purpose, on a fixture where every truth is
known, and fail unless each break moves the counts exactly as it must.

Real arms rarely exercise every branch of the grader: on site-policy, a span
that is gone from its surviving paragraph is never counted. So the states
run on one fixed pair of versions instead, which holds:

- F, A, two copies of E, and D, unchanged: the span survives. F holds a
  line separator (U+2028) inside a line, which the reader does not split
  on; the second E is anchored with nth 1;
- B, two lines, its second rewritten, and the span with it: the paragraph
  survives (one of its two lines does), the span is gone;
- C, deleted, with nothing like it left: deleted;
- G, two lines, its second rewritten to repeat the span: the span occurs
  twice in the target, so it is not counted;
- H, one line, reworded: no line survives and the new line is 61% like it,
  above the deleted test's 30% and below 90%, so the oracle cannot place it
  and it is not counted.

A control and three broken resolvers must give exactly these counts:

| state | correct | loud | WRONG |
| --- | --: | --: | --: |
| as is | 7 | 0 | 0 |
| every comment resolves, on the first paragraph | 1 | 0 | 6 |
| every resolution one character off | 2 | 0 | 5 |
| every comment refused | 2 | 5 | 0 |

`as is` also checks the oracle's truths: the span survives in 5, is gone in
1, 1 paragraph is deleted, and 2 comments are not counted. A last state
checks `replay.rates`, the three refusal rates the report prints, on fixed
counts. A break in the oracle, the grader or the rates moves one of these,
and the script exits 1.

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

F_ = "Foxtrot holds a line separator\u2028inside one of its lines, which the reader keeps."
A_ = "Alpha is the first paragraph, and nothing in it changes between the versions."
B1 = "Bravo opens with a short line."
B2 = "then the scram limit and the shift log close it out here."
B2_NEW = "and nothing else follows from the second line at all now."
C_ = "0987 6543 2109 8765 4321 0000 1111 2222 3333 4444 5555 6666 7777."  # like nothing kept
E_ = "Echo is written twice, word for word, so the second copy has nth one."
G1 = "Golf carries its span on the first of two lines, well inside the middle there."
G2 = "Its second line changes."
G2_NEW = "Now its second line repeats it: of two lines, well inside."
H_ = "Hotel is one line that the later version rewords a little, kept nearby."
H_NEW = "Hotel is one line, and the later version says something else entirely."  # 0.61 like H_
D_ = "Delta closes the document and stays exactly as it was written before."
OLD = f"{F_}\n\n{A_}\n\n{B1}\n{B2}\n\n{C_}\n\n{E_}\n\n{E_}\n\n{G1}\n{G2}\n\n{H_}\n\n{D_}\n"
NEW = f"{F_}\n\n{A_}\n\n{B1}\n{B2_NEW}\n\n{E_}\n\n{E_}\n\n{G1}\n{G2_NEW}\n\n{H_NEW}\n\n{D_}\n"

TRUTH = {"truth span survives": 5, "truth survived": 1, "truth deleted": 1}
RATES = ("5.0%", "13.6%", "32.1%", 10)  # rates() on the counts in main()


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
        ("as is", real, (7, 0, 0)),
        ("every comment resolves, on the first paragraph", first_paragraph, (1, 0, 6)),
        ("every resolution one character off", one_off, (2, 0, 5)),
        ("every comment refused", refuse, (2, 5, 0)),
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
            ok = ok and truth == TRUTH and t["comments"] == 9 and t["not counted"] == 2
        failed |= not ok
        print(
            f"{'PASS' if ok else 'FAIL'}  {name:48s} correct {got[0]}  loud {got[1]}  "
            f"WRONG {got[2]}   (want {want[0]}, {want[1]}, {want[2]})"
        )
    A.resolve = real
    counts = Counter({"span survives": 100, "loud": 5, "not counted DETACHED": 6,
                      "not counted REFUSED(crowded-gap)": 4, "not counted RESOLVED": 20,
                      "not counted EDITED": 3, "comments on them": 30})
    got = replay.rates(counts)
    ok = got == RATES
    failed |= not ok
    print(f"{'PASS' if ok else 'FAIL'}  {'the three rates on fixed counts':48s} {got}   (want {RATES})")
    sys.exit(1 if failed else 0)


if __name__ == "__main__":
    main()
