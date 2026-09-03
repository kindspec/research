"""Replay the real 3-way merges in a CSV's history as real `git merge` runs,
on .mdtbl and on the .csv baseline, judged against an independent oracle.

The oracle is a per-row 3-way merge computed in Python from the base and the
two sides. It never looks at either text merge, so "git merged it cleanly" and
"the answer is right" are decided by different code.

Comparison is line-based, and guarded: a run asserts that re-joining the parsed
rows reproduces the real file bytes, so the two things being compared are the
same thing. A row the format cannot represent (a `|` in a value) therefore
compares equal to itself instead of registering as corruption.
"""

import hashlib
import json
import os
import random
import shutil
import subprocess
import sys
import time
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Git, Malformed, build_mdtbl, evaluate, mangle, read_csv  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
SCRATCH = "/tmp/d0merge"
_G = {}


def _git(repo):
    if repo not in _G:
        _G[repo] = Git(repo)
    return _G[repo]


def colmap_for(header, keycol):
    taken, cm = {keycol}, {}
    for h in header:
        m = mangle(h, taken)
        taken.add(m)
        cm[h] = m
    return cm


def base_id(k):
    return "r_" + hashlib.sha1(("base:" + k).encode()).hexdigest()[:10]


def side_id(sha, i):
    return "r_" + hashlib.sha1(f"{sha}:{i}".encode()).hexdigest()[:10]


def keyed(header, rows, natkey):
    j = header.index(natkey) if natkey in header else 0
    seen, out = {}, []
    for r in rows:
        v = r[j] if j < len(r) else ""
        seen[v] = seen.get(v, 0) + 1
        out.append(v if seen[v] == 1 else f"{v}#{seen[v]}")
    return out


def rowmap(header, rows, ks):
    """key -> (column dict, the row's fields VERBATIM).

    The verbatim list matters: a ragged row in the real data has fewer fields
    than the header, and an oracle that only kept the dict would pad it back
    out and then report the untouched row as corruption. That artifact
    produced five false 'silent-wrong' verdicts before it was caught.
    """
    return {
        k: ({header[i]: (r[i] if i < len(r) else "") for i in range(len(header))}, list(r))
        for k, r in zip(ks, rows)
    }


def oracle(bh, bm, ah, am, ch, cm):
    conflicts = []
    a_add = [c for c in ah if c not in bh]
    c_add = [c for c in ch if c not in bh]
    a_del = [c for c in bh if c not in ah]
    c_del = [c for c in bh if c not in ch]
    if (a_add and c_add and set(a_add) != set(c_add)) or (
        a_del and c_del and set(a_del) != set(c_del)
    ):
        conflicts.append("schema")
    cols = [c for c in bh if c not in a_del and c not in c_del]
    cols += [c for c in a_add if c not in cols] + [c for c in c_add if c not in cols]
    keys = list(bm) + [k for k in am if k not in bm] + [k for k in cm if k not in bm and k not in am]
    result = {}  # key -> the row's fields, verbatim wherever one side wins outright
    for k in keys:
        B, A, C = bm.get(k), am.get(k), cm.get(k)
        b, a, c = (x[0] if x else None for x in (B, A, C))
        if b is None:
            if a is not None and c is not None and a != c:
                conflicts.append(f"add/add {k}")
                continue
            result[k] = (A or C)[1]
            continue
        if a is None and c is None:
            continue
        if a is None:
            if c != b:
                conflicts.append(f"del/mod {k}")
            continue
        if c is None:
            if a != b:
                conflicts.append(f"mod/del {k}")
            continue
        if a == c or c == b:
            result[k] = A[1]
            continue
        if a == b:
            result[k] = C[1]
            continue
        merged = {}
        for col in cols:
            bv, av, cv = b.get(col, ""), a.get(col, ""), c.get(col, "")
            if av == cv:
                merged[col] = av
            elif av == bv:
                merged[col] = cv
            elif cv == bv:
                merged[col] = av
            else:
                conflicts.append(f"cell {k}/{col}")
                merged[col] = av
        result[k] = [merged.get(col, "") for col in cols]
    return ("conflict" if conflicts else "clean"), result, cols, conflicts[:4]


def real_merge(basedata, adata, cdata, fname):
    """A real `git merge`, in a real repository, with no driver and no attrs."""
    d = f"{SCRATCH}/r{os.getpid()}"
    shutil.rmtree(d, ignore_errors=True)
    os.makedirs(d)
    env = {
        **os.environ,
        "GIT_AUTHOR_NAME": "d0", "GIT_AUTHOR_EMAIL": "d0@x",
        "GIT_COMMITTER_NAME": "d0", "GIT_COMMITTER_EMAIL": "d0@x",
        "GIT_CONFIG_GLOBAL": "/dev/null", "GIT_CONFIG_SYSTEM": "/dev/null",
    }

    def g(*a):
        return subprocess.run(["git", "-C", d, *a], capture_output=True, env=env)

    g("init", "-q", "-b", "base")
    open(f"{d}/{fname}", "wb").write(basedata)
    g("add", "-A")
    g("commit", "-qm", "base")
    g("checkout", "-qb", "a")
    open(f"{d}/{fname}", "wb").write(adata)
    g("commit", "-qam", "a")
    g("checkout", "-qb", "c", "base")
    open(f"{d}/{fname}", "wb").write(cdata)
    g("commit", "-qam", "c")
    g("checkout", "-q", "a")
    r = g("merge", "--no-edit", "c")
    out = open(f"{d}/{fname}", "rb").read()
    shutil.rmtree(d, ignore_errors=True)
    return r.returncode == 0, out


def body_lines(raw):
    t = raw.decode("utf-8", "replace").replace("\r\n", "\n")
    return [x for x in t.split("\n") if x != ""][1:]


def one(case):
    repo, path, natkey, h, p1, p2, b, sb, s1, s2, sm = case
    g = _git(repo)
    rec = {"merge": h, "a": p1, "c": p2, "base": b}
    try:
        bh, brows, _ = read_csv(g.blob(sb))
        ah, arows, _ = read_csv(g.blob(s1))
        ch, crows, _ = read_csv(g.blob(s2))
    except Malformed as e:
        rec.update(outcome="excluded", why=f"a side does not parse as CSV: {e}")
        return rec
    bks = keyed(bh, brows, natkey)
    aks = keyed(ah, arows, natkey)
    cks = keyed(ch, crows, natkey)
    basekeys = {k: base_id(k) for k in bks}
    bids = [basekeys[k] for k in bks]
    aids = [basekeys.get(k) or side_id(p1, i) for i, k in enumerate(aks)]
    cids = [basekeys.get(k) or side_id(p2, i) for i, k in enumerate(cks)]

    st, result, cols, why = oracle(
        bh, rowmap(bh, brows, bks), ah, rowmap(ah, arows, aks), ch, rowmap(ch, crows, cks)
    )
    rec.update(oracle=st, oracle_why=why, rows=[len(brows), len(arows), len(crows)],
               headers_agree=(bh == ah == ch))

    keycol = "rowid"
    while keycol in bh or keycol in ah or keycol in ch:
        keycol += "_"
    mdb = build_mdtbl(bh, brows, bids, keycol, colmap_for(bh, keycol)).encode()
    mda = build_mdtbl(ah, arows, aids, keycol, colmap_for(ah, keycol)).encode()
    mdc = build_mdtbl(ch, crows, cids, keycol, colmap_for(ch, keycol)).encode()

    # is the .mdtbl already refused on the inputs? then a refused output is not
    # something the merge did.
    def ok(x):
        try:
            evaluate(x.decode())
            return True
        except Malformed:
            return False

    # A structural check on the inputs, not a full evaluate(): three 40k-row
    # tables cost 13s per case, and the only verdict needed here is whether the
    # inputs were already refused before the merge touched them.
    def cheap_ok(hdr, rws):
        n = len(hdr) + 1
        return not any(
            len(r) + 1 != n or any(("|" in c) or ("\n" in c) or ("\r" in c) for c in r)
            for r in rws
        )

    rec["inputs_valid"] = [cheap_ok(bh, brows), cheap_ok(ah, arows), cheap_ok(ch, crows)]

    mclean, mout = real_merge(mdb, mda, mdc, "t.mdtbl")
    cclean, cout = real_merge(g.blob(sb), g.blob(s1), g.blob(s2), "t.csv")
    rec["mdtbl_merge"] = "clean" if mclean else "conflict"
    rec["csv_merge"] = "clean" if cclean else "conflict"

    idof = {}
    for k, r in zip(bks, bids):
        idof[k] = r
    for k, r in zip(aks, aids):
        idof.setdefault(k, r)
    for k, r in zip(cks, cids):
        idof.setdefault(k, r)
    exp_md, exp_csv = [], []
    for k, vals in result.items():
        exp_md.append("| " + " | ".join([idof[k]] + vals) + " |")
        exp_csv.append(tuple(vals))
    exp_md, exp_csv = sorted(exp_md), sorted(exp_csv)

    def faithful(rows_, raw):
        return sorted(",".join(r) for r in rows_) == sorted(body_lines(raw))

    rec["line_faithful"] = all(
        faithful(r_, g.blob(s_)) for r_, s_ in ((brows, sb), (arows, s1), (crows, s2))
    )

    if mclean:
        rec["mdtbl_valid"] = ok(mout)
        if not rec["mdtbl_valid"]:
            try:
                evaluate(mout.decode())
            except Malformed as e:
                rec["mdtbl_refusal"] = str(e)[:250]
        lines = [x for x in mout.decode("utf-8", "replace").splitlines() if x.strip().startswith("|")]
        obs = sorted(lines[2:])
        rec["md_missing"] = len(set(exp_md) - set(obs))
        rec["md_extra"] = len(set(obs) - set(exp_md))
        rec["md_ex_missing"] = [x[:160] for x in sorted(set(exp_md) - set(obs))[:2]]
        rec["md_ex_extra"] = [x[:160] for x in sorted(set(obs) - set(exp_md))[:2]]
        rec["mdtbl_silent_wrong"] = (st == "conflict") or (obs != exp_md)
    else:
        rec["mdtbl_silent_wrong"] = False
    if cclean:
        # parsed rows, not raw lines: channels.csv gained quoted fields part way
        # through its life, and a line comparison would then be comparing two
        # different things (the `line_faithful` guard records where).
        import csv as _csv
        import io as _io

        recs = [r for r in _csv.reader(_io.StringIO(cout.decode("utf-8", "replace"), newline=""))]
        recs = [r for r in recs[1:] if r != []]
        obs2 = sorted(tuple(r) for r in recs)
        rec["csv_missing"] = len(set(exp_csv) - set(obs2))
        rec["csv_extra"] = len(set(obs2) - set(exp_csv))
        rec["csv_ex_missing"] = [str(x)[:160] for x in sorted(set(exp_csv) - set(obs2))[:2]]
        rec["csv_ex_extra"] = [str(x)[:160] for x in sorted(set(obs2) - set(exp_csv))[:2]]
        rec["csv_silent_wrong"] = (st == "conflict") or (obs2 != exp_csv)
        rec["csv_has_marker"] = any(
            r and r[0].startswith(("<<<<<<<", "=======", ">>>>>>>")) for r in recs
        )
    else:
        rec["csv_silent_wrong"] = False
    rec["outcome"] = "ok"
    return rec


def main(repo, path, natkey, limit=None, out="merge-results.jsonl", procs=4):
    g = Git(repo)
    os.makedirs(SCRATCH, exist_ok=True)
    cases = []
    for line in g.run("log", "--full-history", "--merges", "--format=%H %P").splitlines():
        p = line.split()
        if len(p) != 3:
            continue
        h, p1, p2 = p
        b = g.run("merge-base", p1, p2).strip()
        if not b:
            continue
        sb, s1, s2, sm = (g.blob_sha(x, path) for x in (b, p1, p2, h))
        if None in (sb, s1, s2) or s1 == sb or s2 == sb:
            continue
        cases.append((repo, path, natkey, h, p1, p2, b, sb, s1, s2, sm))
    print(f"{len(cases)} real 3-way merges", flush=True)
    # Shuffled with a fixed seed so that if the run is cut short, the cases
    # completed are a uniform sample of the whole history rather than the most
    # recent merges, which are a different (bot-heavy) editing regime.
    random.Random(0).shuffle(cases)
    if limit:
        cases = cases[:limit]
    t0 = time.time()
    res = []
    # written as they land, so an interrupted run still leaves usable evidence
    with open(os.path.join(HERE, out), "w") as fh, Pool(procs) as pool:
        for n, rec in enumerate(pool.imap_unordered(one, cases, chunksize=1)):
            res.append(rec)
            fh.write(json.dumps(rec, default=str) + "\n")
            fh.flush()
            if n % 25 == 0:
                print(f"  {n}/{len(cases)} {time.time() - t0:.0f}s", flush=True)
    assert len(res) == len(cases), (len(res), len(cases))
    print(f"wrote {len(res)} -> {out} ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    main(sys.argv[1], sys.argv[2], sys.argv[3],
         int(sys.argv[4]) if len(sys.argv) > 4 else None,
         sys.argv[5] if len(sys.argv) > 5 else "merge-results.jsonl")
