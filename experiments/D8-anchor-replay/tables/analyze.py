#!/usr/bin/env python3
"""Table-leaf comments in the r0004 and r0003 dumps: statuses, and for each
0004 REFUSED(near-copy) on a table, which unmatched leaves trigger it, with
word similarity computed with and without `|` words.

Usage: python3 -I analyze.py BLOCKSPEC_0004 OUTDIR ARM=CLONEPATH ...

with OUTDIR holding run.sh's r0004-ARM.jsonl and r0003-ARM.jsonl for each
ARM, and CLONEPATH that arm's clone at its pin. Arms are reported in the
order given.
"""

import json
import os
import sys
from collections import Counter

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)  # this directory's replay.py
import replay  # noqa: E402

A, R, head = replay.load_blockspec(sys.argv[1])
out = sys.argv[2]
clone_path = dict(x.split("=", 1) for x in sys.argv[3:])
HELD = {"github-docs", "vscode-docs", "docker-docs", "mdn-en"}


def rows(label, arm):
    with open(os.path.join(out, f"{label}-{arm}.jsonl"), encoding="utf-8") as f:
        return [json.loads(x) for x in f]


def ws(wa, wb):
    if not wa or not wb:
        return 0, 2
    return A.lcs_length(wa, wb), len(wa) + len(wb)


def fmt(sim):
    return f"{2 * sim[0] / sim[1]:.3f}" if sim[1] else "-"


print(f"# analyze.py: 0004 reference at {head[:12]}; table-leaf comments, gap 5")
status = {"r0004": Counter(), "r0003": Counter()}
by_group = {g: {"r0004": Counter(), "r0003": Counter()} for g in ("held-out", "tuned")}
verdicts = {"r0004": Counter(), "r0003": Counter()}
trans = Counter()
nc = Counter()
examples = []
for arm in clone_path:
    group = "held-out" if arm in HELD else "tuned"
    r4, r3 = rows("r0004", arm), rows("r0003", arm)
    key = lambda r: (r["file"], r["a"], r["b"], r["para"], r["span"])
    m3 = {key(r): r for r in r3}
    if len(m3) != len(r3) or {key(r) for r in r4} != set(m3):
        sys.exit(f"{arm}: dumps do not hold the same comments")
    for lab, rs in (("r0004", r4), ("r0003", r3)):
        for r in rs:
            if r["type"] != "table":
                continue
            status[lab][r["status"]] += 1
            by_group[group][lab][r["status"]] += 1
            verdicts[lab][(r["status"], r["verdict"])] += 1
    snaps = {}
    for r in r4:
        if r["type"] != "table":
            continue
        trans[(m3[key(r)]["status"], r["status"])] += 1
        if r["status"] != "REFUSED(near-copy)":
            continue
        k = (r["file"], r["a"], r["b"])
        if k not in snaps:
            show = lambda c: replay.git(clone_path[arm], "show", f"{c}:{r['file']}")
            o, n = A.Snapshot(R, show(r["a"])), A.Snapshot(R, show(r["b"]))
            ops = replay.paragraphs(A, R, show(r["a"]))[1]
            snaps[k] = (o, n, ops, A.Correspondence(o.leaves, n.leaves))
        o, n, ops, corr = snaps[k]
        leaf = ops[r["para"]]
        kidx = leaf.index
        c, kind = corr.pair[kidx]
        unchanged = kind == A.EXACT
        nc[("EXACT" if unchanged else kind)] += 1
        if not unchanged:
            continue
        wk = A.words(leaf)
        wk_np = [w for w in wk if w != "|"]
        trig = []
        for u in corr.unmatched():
            cu = corr.current[u]
            if cu.key == leaf.key:
                continue
            sim = A.word_similarity(leaf, cu)
            if not A.at_least_half(sim):
                continue
            wu_np = [w for w in A.words(cu) if w != "|"]
            sim_np = ws(wk_np, wu_np)
            trig.append((u, cu.type, sim, sim_np, A.at_least_half(sim_np), A.similarity(leaf, cu)))
        if not trig:
            sys.exit(f"no trigger found for {k} P{r['para']}")
        only_pipe = all(not t[4] for t in trig)
        nc["EXACT, every trigger reaches 0.5 only with | words" if only_pipe else
           "EXACT, some trigger reaches 0.5 without | words"] += 1
        nc[f"EXACT, verdict {r['verdict']}" + (", |-only" if only_pipe else ", not |-only")] += 1
        nc[f"EXACT, 0003 status {m3[key(r)]['status']}" + (", |-only" if only_pipe else ", not |-only")] += 1
        for t in trig:
            nc[f"trigger leaf type {t[1]}" + (" (|-only)" if not t[4] else " (not |-only)")] += 1
        examples.append((arm, r["file"], r["a"][:10], r["b"][:10], r["para"], r["verdict"],
                         m3[key(r)]["status"], only_pipe, leaf.text, [(n.leaves[t[0]].text, t[1], fmt(t[2]), fmt(t[3]), fmt(t[5])) for t in trig]))

for lab in ("r0004", "r0003"):
    print(f"\n## table comments, status, {lab}: total {sum(status[lab].values())}")
    for s, v in status[lab].most_common():
        print(f"  {v:5d}  {s}   (held-out {by_group['held-out'][lab][s]}, tuned {by_group['tuned'][lab][s]})")
    print(f"  by status and verdict:")
    for (s, vd), v in sorted(verdicts[lab].items(), key=lambda x: -x[1]):
        print(f"    {v:5d}  {s} / {vd}")
print("\n## table comments, 0003 status -> 0004 status (changed only)")
for (a, b), v in trans.most_common():
    if a != b:
        print(f"  {v:5d}  {a} -> {b}")
print("\n## 0004 REFUSED(near-copy) on table comments")
for s, v in sorted(nc.items()):
    print(f"  {v:5d}  {s}")
print("\n## examples (EXACT near-copy)")
for e in examples[:400]:
    arm, f, a, b, p, vd, s3, op, text, trig = e
    print(f"\n- {arm} {f} {a}..{b} T{p} verdict={vd} 0003={s3} pipe-only={op}")
    print(f"  table: {text[:300]!r}")
    for t in trig:
        print(f"  trigger ({t[1]}): words {t[2]}, words without | {t[3]}, code points {t[4]}: {t[0][:300]!r}")
