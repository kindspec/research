#!/usr/bin/env python3
"""Score the labels on sample.py's packets against the word oracle and the
resolver.

Two labellers label every packet independently; where they disagree, a
third labels it, and that label is final. A label is
`{"id", "survives", "paragraph", "note"}`: whether the commented words
survive in the later version as the same passage, whitespace aside, and if
so the later paragraph that holds them.

Within each stratum, the share of labelled comments with each property is
scaled to the stratum's size (sample.py's `strata.json`). That gives:

- the oracle's error where it places a comment: a `placed` comment
  labelled gone or in another paragraph, or a `gone` one labelled as
  surviving;
- the refusal rate with labels for truth: loud comments labelled as
  surviving, over all comments labelled as surviving;
- each resolving comment the labels put elsewhere, listed.

Each stratum's shares get an exact two-sided 95% interval (Clopper-Pearson;
none where every comment in it was labelled), and each estimate is given
with every stratum at the ends of its interval. That range is not itself a
confidence interval; it stays finite where a stratum shows no errors, where
a bootstrap would show none.

The rate is among comments on pairs whose later version the profile
accepts. Comments on the others (sample.py's `profile refused`) cannot be
labelled; they are printed beside it, with the rate as if each were a
refusal of surviving text.

Usage:
    python3 -I score.py --keydir DIR --labels A.jsonl --labels B.jsonl [--adjudicated C.jsonl]
"""

import argparse
import json
import math
import os
from collections import defaultdict

def binom_cdf(k, n, p):
    return sum(math.comb(n, i) * p**i * (1 - p) ** (n - i) for i in range(k + 1))


def interval(k, n, alpha=0.05):
    """Clopper-Pearson: the exact two-sided interval for k successes in n."""
    def solve(f):
        lo, hi = 0.0, 1.0
        for _ in range(60):
            mid = (lo + hi) / 2
            lo, hi = (mid, hi) if f(mid) else (lo, mid)
        return lo
    low = 0.0 if k == 0 else solve(lambda p: 1 - binom_cdf(k - 1, n, p) < alpha / 2)
    high = 1.0 if k == n else solve(lambda p: binom_cdf(k, n, p) > alpha / 2)
    return low, high


def read(path, key=None):
    """One JSON object per line, by id. With `key`, each must be a label of
    a packet in it, given once: `survives` a boolean, and `paragraph` a
    paragraph number when it survives, null when not."""
    out = {}
    for n, line in enumerate(open(path, encoding="utf-8"), 1):
        if not line.strip():
            continue
        row = json.loads(line)
        if key is not None:
            where = f"{path}:{n}"
            if row.get("id") not in key:
                raise SystemExit(f"{where}: no packet {row.get('id')!r}")
            if row["id"] in out:
                raise SystemExit(f"{where}: {row['id']} labelled twice")
            if not isinstance(row.get("survives"), bool):
                raise SystemExit(f"{where}: survives must be true or false")
            para = row.get("paragraph")
            ok = (isinstance(para, int) and not isinstance(para, bool) and para >= 0) if row["survives"] else para is None
            if not ok:
                raise SystemExit(f"{where}: paragraph must be a number when it survives, null when not")
        out[row["id"]] = row
    return out


def same(x, y):
    return x["survives"] == y["survives"] and (not x["survives"] or x["paragraph"] == y["paragraph"])


def facts(k, lab):
    s = lab["survives"]
    _, oracle, resolver = k["stratum"].rsplit("/", 2)
    err = None
    if oracle == "placed":
        err = not s or lab["paragraph"] != k["target"]
    elif oracle == "gone":
        err = s
    return {
        "survives": s,
        "counted": err is not None,
        "loud_survives": s and resolver == "loud",
        "oracle_err": err,
        "resolver_elsewhere": resolver == "resolves" and (not s or lab["paragraph"] != k["resolved_to"]),
    }


def estimate(by, sizes, num, den):
    """The share of comments with `den` that also have `num`, each sampled
    comment standing for its stratum's size over its sample's."""
    n = d = 0.0
    for h, fs in by.items():
        w = sizes[h] / len(fs)
        n += w * sum(1 for f in fs if f[den] and f[num])
        d += w * sum(1 for f in fs if f[den])
    return n / d if d else float("nan")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--keydir", required=True)
    ap.add_argument("--labels", action="append", required=True)
    ap.add_argument("--adjudicated")
    args = ap.parse_args()
    key = read(os.path.join(args.keydir, "key.jsonl"))
    meta = json.load(open(os.path.join(args.keydir, "strata.json"), encoding="utf-8"))
    sizes = meta["sizes"]
    if len(args.labels) != 2:
        raise SystemExit("--labels takes the two passes")
    a, b = (read(p, key) for p in args.labels)
    c = read(args.adjudicated, key) if args.adjudicated else {}
    missing = [i for i in key if i not in a or i not in b]
    if missing:
        raise SystemExit(f"{len(missing)} packets lack two labels, e.g. {missing[:3]}")
    agree = [i for i in key if same(a[i], b[i])]
    split = [i for i in key if i not in agree]
    unsettled = [i for i in split if i not in c]
    print(f"# score.py: gap {meta['gap']}, blockspec {meta['blockspec'][:12]}, {len(key)} packets")
    print(f"  the two labellers agree on {len(agree)} of {len(key)}; "
          f"they disagree on {len(split)}, of which {len(split) - len(unsettled)} are adjudicated")
    if unsettled:
        print("  not yet adjudicated: " + " ".join(sorted(unsettled)))
        raise SystemExit(1)
    final = {i: (a[i] if i in agree else c[i]) for i in key}
    by = defaultdict(list)
    for i, k in key.items():
        by[k["stratum"]].append(facts(k, final[i]))

    print(f"\n  {'stratum':32s} comments  sampled  labelled surviving  oracle wrong")
    for h in meta["caps"]:
        fs = by.get(h, [])
        errs = [f["oracle_err"] for f in fs if f["oracle_err"] is not None]
        print(f"  {h:32s} {sizes[h]:8d} {len(fs):8d} {sum(f['survives'] for f in fs):10d}"
              f"          {sum(errs) if errs else '-':>5}")

    print("\n  share of each stratum, 95% interval (exact where every comment was labelled)")
    bounds = {}
    for h, fs in by.items():
        for prop, den in (("survives", None), ("oracle_err", "counted")):
            pool = [f for f in fs if den is None or f[den]]
            if not pool:
                continue
            k = sum(1 for f in pool if f[prop])
            lo, hi = (k / len(pool),) * 2 if len(fs) == sizes[h] else interval(k, len(pool))
            bounds[h, prop] = (lo, hi)
            print(f"    {h:32s} {prop:10s} {k:3d} of {len(pool):3d}: {100 * lo:5.1f}% to {100 * hi:5.1f}%")

    def rate(loud_end, resolves_end, extra=0):
        top = sum(sizes[h] * bounds[h, "survives"][loud_end] for h in by if h.endswith("/loud"))
        rest = sum(sizes[h] * bounds[h, "survives"][resolves_end] for h in by if h.endswith("/resolves"))
        return (top + extra) / (top + rest + extra)

    counted = [h for h in by if (h, "oracle_err") in bounds]
    err = [sum(sizes[h] * bounds[h, "oracle_err"][e] for h in counted) / sum(sizes[h] for h in counted)
           for e in (0, 1)]
    print(f"\n  oracle wrong, where it places a comment: {100 * estimate(by, sizes, 'oracle_err', 'counted'):.1f}%"
          f" (each stratum at its interval's ends: {100 * err[0]:.1f}% to {100 * err[1]:.1f}%)")
    print(f"\n  refusal rate, labels for truth: {100 * estimate(by, sizes, 'loud_survives', 'survives'):.1f}%"
          f" (each stratum at its interval's least and most favourable end: "
          f"{100 * rate(0, 1):.1f}% to {100 * rate(1, 0):.1f}%), "
          f"among comments on versions the profile accepts")
    profile = sum(meta.get("profile refused", {}).values())
    point = estimate(by, sizes, "loud_survives", "survives")
    top = point * sum(sizes[h] * sum(f["survives"] for f in by[h]) / len(by[h]) for h in by)
    whole = sum(sizes[h] * sum(f["survives"] for f in by[h]) / len(by[h]) for h in by)
    print(f"  outside it: {profile} comments on versions the profile refuses, each REFUSED(not-in-profile);"
          f" as if each were a refusal of surviving text: {100 * (top + profile) / (whole + profile):.1f}%"
          f" ({100 * rate(0, 1, profile):.1f}% to {100 * rate(1, 0, profile):.1f}%)")

    print("\n## resolving comments the labels put elsewhere")
    for i, k in sorted(key.items()):
        f = facts(k, final[i])
        if f["resolver_elsewhere"]:
            print(f"  {i} {k['file']} {k['a'][:8]}..{k['b'][:8]} P{k['para']} {k['status']} "
                  f"to P{k['resolved_to']}; label {final[i]['survives']} P{final[i]['paragraph']}"
                  f"  {final[i].get('note', '')}")
    print("\n## the two labellers disagree")
    for i in sorted(split):
        print(f"  {i} [{key[i]['stratum']}] A {a[i]['survives']} P{a[i]['paragraph']}; "
              f"B {b[i]['survives']} P{b[i]['paragraph']}; final {c[i]['survives']} P{c[i]['paragraph']}")


if __name__ == "__main__":
    main()
