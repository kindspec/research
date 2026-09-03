"""Adversarial checks on the replay harness itself.

The most likely way this experiment produces a flattering result is a bug here,
so each of the three named failure modes gets a control that must fail when the
harness is broken on purpose.
"""

import json
import os
import random
from collections import Counter
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import (  # noqa: E402
    Git,
    Malformed,
    build_mdtbl,
    diff_size,
    evaluate,
    mint,
    natkeys,
    read_csv,
    similarity,
    witness,
)
from replay import CORPORA, colmap_for  # noqa: E402
sys.path.insert(0, "/home/cam/repos_kindspec/rowspec/reference")
from rowspec.table import canon  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
random.seed(7)
fails = []


def check(name, cond, extra=""):
    print(("PASS " if cond else "FAIL ") + name + (" " + extra if extra else ""))
    if not cond:
        fails.append(name)


# --- 1. no commit is silently skipped ---------------------------------------
for nm, cfg in CORPORA.items():
    p = os.path.join(HERE, f"ledger-{nm}.jsonl")
    if not os.path.exists(p):
        print(f"SKIP {nm} (not finished)")
        continue
    L = [json.loads(x) for x in open(p)]
    g = Git(cfg["repo"])
    revs = g.run(
        "rev-list", "--full-history", "--topo-order", "--reverse", "HEAD", "--", cfg["path"]
    ).split()
    check(
        f"{nm}: ledger covers every commit git reports for the path",
        [r["rev"] for r in L] == revs,
        f"({len(L)} vs {len(revs)})",
    )
    check(
        f"{nm}: every non-excluded commit carries a verdict",
        all(("mdtbl" in r) or r["outcome"] == "excluded" for r in L),
    )
    check(
        f"{nm}: no commit has an unclassified outcome",
        all(r.get("outcome") in ("ok", "refused", "excluded") for r in L),
    )

# --- 2. round trip: the .mdtbl really holds the CSV's values ----------------
# and the two diffs really are diffs of the same change.
for nm, cfg in CORPORA.items():
    g = Git(cfg["repo"])
    revs = g.run(
        "rev-list", "--full-history", "--topo-order", "--reverse", "HEAD", "--", cfg["path"]
    ).split()
    sample = random.sample(revs, min(6 if "channels" in nm else 25, len(revs)))
    rt = badrt = canonstable = notcanon = unrep = 0
    canonkinds = Counter()
    for rev in sample:
        sha = g.blob_sha(rev, cfg["path"])
        if sha is None:
            continue
        try:
            header, rows, _ = read_csv(g.blob(sha))
        except Malformed:
            continue
        keycol = "rowid"
        while keycol in header:
            keycol += "_"
        ids = [mint(rev, i) for i in range(len(rows))]
        md = build_mdtbl(header, rows, ids, keycol, colmap_for(header, keycol))
        lines = [x for x in md.splitlines() if x.startswith("|")][2:]
        if len(lines) != len(rows):
            badrt += 1
            continue
        for ln, r, rid in zip(lines, rows, ids):
            cells = [c.strip(" \t") for c in ln.strip().strip("|").split("|")]
            want = [rid] + [c.strip(" \t") for c in r]
            if cells == want:
                rt += 1
            elif any(("|" in c) or ("\n" in c) or ("\r" in c) for c in r):
                # the format has no escape for `|`; this row cannot be written
                # at all, which is a finding about the format, not a harness bug
                unrep += 1
            else:
                badrt += 1
        try:
            evaluate(md)
            c = canon(md)
            if c == md:
                canonstable += 1
            else:
                notcanon += 1
                for x, y in zip(md.splitlines(), c.splitlines()):
                    if x != y:
                        canonkinds["padding-whitespace-in-a-value"
                                   if x.replace(" ", "") == y.replace(" ", "")
                                   else "OTHER: " + repr(x[:60])] += 1
        except Malformed:
            pass
    check(
        f"{nm}: every representable .mdtbl row round-trips to its CSV row",
        badrt == 0,
        f"({rt} ok, {badrt} harness-bug, {unrep} rows the format cannot write at all)",
    )
    check(
        f"{nm}: canon changes nothing but padding whitespace inside values",
        all(k.startswith("padding") for k in canonkinds),
        f"({canonstable} already canonical, {notcanon} not; {dict(canonkinds)})",
    )

# --- 3. controls: the harness must be able to report failure ----------------
cfg = CORPORA["iso-3166"]
g = Git(cfg["repo"])
rev = g.run("rev-list", "-1", "HEAD", "--", cfg["path"]).strip()
header, rows, _ = read_csv(g.blob(g.blob_sha(rev, cfg["path"])))
ids = [mint(rev, i) for i in range(len(rows))]
cm = colmap_for(header, "rowid")
good = build_mdtbl(header, rows, ids, "rowid", cm)
try:
    evaluate(good)
    accepted = True
except Malformed:
    accepted = False
check("control: an unmodified real commit is accepted", accepted)

inj = [list(r) for r in rows]
inj[5][0] = inj[5][0] + "|x"
bad = build_mdtbl(header, inj, ids, "rowid", cm)
try:
    evaluate(bad)
    caught = False
except Malformed:
    caught = True
check("control: a pipe injected into one value is refused", caught)

dup = list(ids)
dup[3] = dup[2]
bad2 = build_mdtbl(header, rows, dup, "rowid", cm)
try:
    evaluate(bad2)
    caught2 = False
except Malformed as e:
    caught2 = "duplicate" in str(e)
check("control: a duplicated row id is refused", caught2)

# carriage control: shuffled ids must NOT read as carriage
w = witness(rows, rows)
shuf = list(ids)
random.shuffle(shuf)
kept_same = sum(1 for b, a in w.items() if ids[b] == ids[a])
kept_shuf = sum(1 for b, a in w.items() if shuf[b] == ids[a])
check(
    "control: carriage is 100% for identical ids and ~0% for shuffled ids",
    kept_same == len(w) and kept_shuf < 0.05 * len(w),
    f"(same {kept_same}/{len(w)}, shuffled {kept_shuf}/{len(w)})",
)

# witness control: an unrelated row must not be paired with anything
w2 = witness(rows, rows[:-1] + [["ZZZZ"] * len(header)])
check(
    "control: the witness refuses to pair a row that shares nothing",
    len(w2) == len(rows) - 1,
    f"({len(w2)} pairs of {len(rows)})",
)

# diff control: a one-cell change must be a small diff, a re-sort a large one
a = build_mdtbl(header, rows, ids, "rowid", cm).encode()
r2 = [list(x) for x in rows]
r2[10][1] = "ZZ"
b = build_mdtbl(header, r2, ids, "rowid", cm).encode()
l1, _ = diff_size(a, b, "vfy1")
order = sorted(range(len(rows)), key=lambda i: rows[i][2] if len(rows[i]) > 2 else "")
c = build_mdtbl(header, [rows[i] for i in order], [ids[i] for i in order], "rowid", cm).encode()
l2, _ = diff_size(a, c, "vfy2")
check("control: diff_size distinguishes a one-cell edit from a re-sort", l1 == 2 and l2 > 50,
      f"(one-cell {l1} lines, re-sort {l2} lines)")

print()
print("FAILED:" if fails else "all controls passed", fails)
sys.exit(1 if fails else 0)
