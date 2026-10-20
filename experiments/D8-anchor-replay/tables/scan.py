#!/usr/bin/env python3
"""Every table leaf, not only sampled comments: for each arm, every file in
its pathspec whose history at the pin has a table in the earlier version
of a pair, up to PAIRS_PER_FILE pairs GAP commits apart (replay.py's sampling,
same seed), every base table leaf that pairs EXACT: does 0004's word rule
refuse it near-copy, does 0003's code-point rule, and does the word rule
still reach 0.5 without `|` words?

Usage: python3 -I scan.py BLOCKSPEC_0004 BLOCKSPEC_0003 ARM CLONEPATH [GAP]
"""

import os
import random
import sys
from collections import Counter

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # this directory's replay.py
import replay  # noqa: E402

A4, R4, h4 = replay.load_blockspec(sys.argv[1])
# load 0003 as a separate package copy
for m in [m for m in sys.modules if m == "blockspec" or m.startswith("blockspec.")]:
    del sys.modules[m]
sys.path.remove(os.path.join(sys.argv[1], "reference"))
A3, R3, h3 = replay.load_blockspec(sys.argv[2])
assert A3 is not A4
arm, repo = sys.argv[3], sys.argv[4]
gap = int(sys.argv[5]) if len(sys.argv) > 5 else 5
spec = next((a for a in replay.load_arms() if a["name"] == arm), {"pathspec": "*.md"})


def ws(wa, wb):
    if not wa or not wb:
        return 0, 2
    return A4.lcs_length(wa, wb), len(wa) + len(wb)


def near3(A, corr, k):
    """0003's EXACT near-copy check."""
    for u in corr.unmatched():
        sim = corr.similarity(k, u)
        if A.at_least_half(sim) and A.below_one(sim):
            return True
    return False


rnd = random.Random(replay.SEED)
files = [f for f in replay.git(repo, "ls-files", "--", *spec["pathspec"].split()).split("\n") if f]
rnd.shuffle(files)
t = Counter()
ex, every = [], []
for f in files:
    pairs = replay.pairs_for(repo, f, gap, rnd)
    for a, b in pairs:
        try:
            old, new = replay.git(repo, "show", f"{a}:{f}"), replay.git(repo, "show", f"{b}:{f}")
        except UnicodeDecodeError:
            continue
        if "|" not in old:
            continue
        try:
            o4, n4 = A4.Snapshot(R4, old), A4.Snapshot(R4, new)
        except A4.Refusal:
            t["pairs the profile refuses"] += 1
            continue
        tables = [lf for lf in o4.leaves if lf.type == "table"]
        if not tables:
            continue
        t["pairs with a table"] += 1
        c4 = A4.Correspondence(o4.leaves, n4.leaves)
        o3, n3 = A3.Snapshot(R3, old), A3.Snapshot(R3, new)
        c3 = A3.Correspondence(o3.leaves, n3.leaves)
        for lf in tables:
            t["base table leaves"] += 1
            k = lf.index
            if k not in c4.pair or c4.pair[k][1] != A4.EXACT:
                continue
            t["EXACT table leaves"] += 1
            unm = c4.unmatched()
            if unm:
                t["EXACT table leaves with an unmatched current leaf"] += 1
            trig = [u for u in unm if c4.current[u].key != lf.key
                    and A4.at_least_half(A4.word_similarity(lf, c4.current[u]))]
            r3 = c3.pair.get(k, (None, None))[1] == A3.EXACT and near3(A3, c3, k)
            if r3:
                t["0003 refuses near-copy"] += 1
            if not trig:
                continue
            t["0004 refuses near-copy"] += 1
            wk = [w for w in A4.words(lf) if w != "|"]
            pipe_only = all(not A4.at_least_half(ws(wk, [w for w in A4.words(c4.current[u]) if w != "|"]))
                            for u in trig)
            t["0004 refuses, every trigger |-only" if pipe_only else "0004 refuses, a trigger without |"] += 1
            t[f"0004 refuses, 0003 refuses={r3}, |-only={pipe_only}"] += 1
            for u in trig:
                t[f"trigger type {c4.current[u].type}"] += 1
            u = trig[0]
            cu = c4.current[u]
            wu = [w for w in A4.words(cu) if w != "|"]
            s, s2, s3 = A4.word_similarity(lf, cu), ws(wk, wu), A4.similarity(lf, cu)
            every.append(f"{f} {a}..{b} leaf {k} (trigger leaf {u} of {len(trig)}): "
                         f"0003 refuses={r3}, |-only={pipe_only}; words {2*s[0]/s[1]:.3f}, "
                         f"without | {2*s2[0]/s2[1]:.3f}, code points {2*s3[0]/s3[1]:.3f}")
            if len(ex) < 8:
                ex.append(f"{f} {a[:10]}..{b[:10]} leaf {k}: words {2*s[0]/s[1]:.3f}, without | "
                          f"{2*s2[0]/s2[1]:.3f}, code points {2*s3[0]/s3[1]:.3f}\n"
                          f"    table: {lf.text[:240]!r}\n    trigger ({cu.type}): {cu.text[:240]!r}")
print(f"# scan.py {arm} gap={gap}: 0004 at {h4[:12]}, 0003 at {h3[:12]}; files {len(files)}")
for k, v in sorted(t.items()):
    print(f"  {v:6d}  {k}")
print("  every 0004 refusal, first trigger's similarities:")
for e in every:
    print("    " + e)
for e in ex:
    print("  e.g. " + e)
