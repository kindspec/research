#!/usr/bin/env python3
"""Break replay.py's grading on purpose, on a fixture where every truth is
known, and fail unless each break moves the counts exactly as it must.

Real arms rarely exercise every branch of the grader: on site-policy, a span
that is gone from its surviving paragraph is never counted. So the states
run on one fixed pair of versions instead, which holds:

- F, A, two copies of E, and D, unchanged: the span survives. F holds a
  line separator (U+2028) inside a line, which the reader does not split
  on; the second E is anchored with nth 1;
- B, two lines, its second rewritten, and the span with it: the span's
  words all survive, but with a word between two of them, so it is gone;
- C, deleted, with nothing like it left: gone;
- G, two lines, its second rewritten to repeat the span: the span occurs
  twice in the target, so it is not counted;
- H, one line, reworded around the span: the span's words still map, so it
  survives, and the resolver refuses it (`crowded-gap`);
- S, split into two paragraphs between the span's words: gone;
- W, one line rewrapped into two, between the span's words: the span
  survives, whitespace aside;
- M, moved from near the top to the end, and rewrapped inside the span:
  the word matching keeps the longer run it jumped over, so M's text is
  later, whitespace aside, but not where the matching put it, and it is
  not counted.

A control and three broken resolvers must give exactly these counts:

| state | correct | loud | WRONG |
| --- | --: | --: | --: |
| as is | 8 | 2 | 0 |
| every comment resolves, on the first paragraph | 1 | 0 | 9 |
| every resolution one character off | 3 | 2 | 5 |
| every comment refused | 3 | 7 | 0 |

`as is` also checks the oracle's truths: the span survives in 7, is gone in
3, and 2 comments are not counted. A last state
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
B2_NEW = "then the scram rod limit and nothing else follows from it."
C_ = "0987 6543 2109 8765 4321 0000 1111 2222 3333 4444 5555 6666 7777."  # like nothing kept
E_ = "Echo is written twice, word for word, so the second copy has nth one."
G1 = "Golf carries its span on the first of two lines, well inside the middle there."
G2 = "Its second line changes."
G2_NEW = "Now its second line repeats it: of two lines, well inside."
H_ = "Hotel is one line that the later version rewords a little, kept nearby."
H_NEW = "Hotel is one line, and the later version says something else entirely."
S_ = "Sierra quartz xylophone jukebox zephyr wombat quiver banjo yodel kumquat fjord nymph glyph sphinx vex."
S1_NEW = "Sierra quartz xylophone jukebox zephyr wombat quiver banjo"
S2_NEW = "yodel kumquat fjord nymph glyph sphinx vex."
W_ = "Whiskey wraps its words onto lines and the later version rewraps them here."
W_NEW = "Whiskey wraps its words onto lines and\nthe later version rewraps them here."
M_ = "Mike moves from near the top of the document to its very end, word for word."
M_NEW = "Mike moves from near the top of\nthe document to its very end, word for word."
D_ = "Delta closes the document and stays exactly as it was written before."
OLD = f"{F_}\n\n{M_}\n\n{A_}\n\n{B1}\n{B2}\n\n{C_}\n\n{E_}\n\n{E_}\n\n{G1}\n{G2}\n\n{H_}\n\n{S_}\n\n{W_}\n\n{D_}\n"
NEW = f"{F_}\n\n{A_}\n\n{B1}\n{B2_NEW}\n\n{E_}\n\n{E_}\n\n{G1}\n{G2_NEW}\n\n{H_NEW}\n\n{S1_NEW}\n\n{S2_NEW}\n\n{W_NEW}\n\n{D_}\n\n{M_NEW}\n"

TRUTH = {"truth span survives": 7, "truth gone": 3}
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
        ("as is", real, (8, 2, 0)),
        ("every comment resolves, on the first paragraph", first_paragraph, (1, 0, 9)),
        ("every resolution one character off", one_off, (3, 2, 5)),
        ("every comment refused", refuse, (3, 7, 0)),
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
            ok = ok and truth == TRUTH and t["comments"] == 12 and t["not counted"] == 2
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
