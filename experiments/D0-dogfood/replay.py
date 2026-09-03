"""Walk the real history of one CSV, per-commit, through rowspec.

Two phases. Phase 1 is sequential because row-id carriage is a chain: each
commit inherits its parent's id assignment. Phase 2 is per-commit independent
and runs in a pool, because `rowspec.table.parse` costs ~4.4s on a 40k-row
.mdtbl and the sequential form would take nine hours.

Nothing is allowed to skip a commit silently: every commit in the traversal
gets exactly one record in the ledger, and the run asserts on the count.
"""

import json
import os
import sys
import time
from collections import Counter
from multiprocessing import Pool

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import (  # noqa: E402
    Git,
    Malformed,
    build_mdtbl,
    canon_churn,
    csv_mode_check,
    diff_size,
    evaluate,
    ident_ok_reference,
    ident_ok_spec,
    mangle,
    mint,
    natkeys,
    read_csv,
    representability,
    similarity,
    witness,
)

HERE = os.path.dirname(os.path.abspath(__file__))
CORPORA = json.load(open(os.path.join(HERE, "corpora.json")))
_G = {}


def _git(repo):
    if repo not in _G:
        _G[repo] = Git(repo)
    return _G[repo]


def work(task):
    """Everything that depends only on this commit and its first parent."""
    (repo, path, rev, sha, ids_s, psha, pids_s, colmap, keycol, natkey, name, csvkey) = task
    g = _git(repo)
    rec = {}
    raw = g.blob(sha)
    header, rows, notes = read_csv(raw)
    ids = ids_s.split("\n") if ids_s else []

    bad = representability(header, rows)
    rec["defects"] = dict(Counter(b[0] for b in bad))
    rec["defect_examples"] = [
        {"kind": b[0], "row": b[1], "col": b[2], "bytes": b[3][:150]} for b in bad[:3]
    ]
    md = build_mdtbl(header, rows, ids, keycol, colmap)
    mdb = md.encode()
    try:
        evaluate(md)
        rec["mdtbl"] = "accepted"
    except Malformed as e:
        rec["mdtbl"] = "refused"
        rec["mdtbl_reason"] = str(e)[:400]

    errs, warns = csv_mode_check(raw, path, csvkey)
    rec["csvmode"] = "refused" if errs else "accepted"
    if errs:
        rec["csvmode_reason"] = [str(x) for x in errs[:3]]
    rec["csvmode_warnings"] = sorted({x.rule for x in warns})

    nfc, trim, exn, ext = canon_churn(rows)
    rec["canon_nfc_cells"], rec["canon_trim_cells"] = nfc, trim
    if exn:
        rec["canon_nfc_ex"] = [[a, b, c] for a, b, c in exn]
    if ext:
        rec["canon_trim_ex"] = [[a, b, repr(c)] for a, b, c in ext]
    rec["canon_crlf"] = "crlf" in notes

    if psha:
        praw = g.blob(psha)
        pheader, prows, _ = read_csv(praw)
        pids = pids_s.split("\n") if pids_s else []
        w = witness(prows, rows)
        rec["witness_pairs"] = len(w)
        rec["witness_kept_id"] = sum(1 for bi, ai in w.items() if ids[bi] == pids[ai])
        rec["witness_deleted"] = len(prows) - len(w)
        rec["witness_added"] = len(rows) - len(w)
        pidx = {rid: ai for ai, rid in enumerate(pids)}
        rec["id_on_different_row"] = sum(
            1
            for bi, rid in enumerate(ids)
            if rid in pidx and similarity(prows[pidx[rid]], rows[bi]) < 0.5
        )
        pmd = build_mdtbl(pheader, prows, pids, keycol, colmap_for(pheader, keycol)).encode()
        cl, cb = diff_size(praw, raw, f"{name}_csv_{os.getpid()}")
        ml, mb = diff_size(pmd, mdb, f"{name}_md_{os.getpid()}")
        rec["csv_diff_lines"], rec["csv_diff_bytes"] = cl, cb
        rec["md_diff_lines"], rec["md_diff_bytes"] = ml, mb
        # guard against comparing diffs of different things
        rec["diff_guard_rows"] = [len(prows), len(rows)]
    return rev, rec


def colmap_for(header, keycol):
    taken = {keycol}
    cm = {}
    for h in header:
        m = mangle(h, taken)
        taken.add(m)
        cm[h] = m
    return cm


def run(name, cfg, limit=None, outdir=HERE, procs=8):
    g = Git(cfg["repo"])
    path, natkey, repo = cfg["path"], cfg["natkey"], cfg["repo"]
    revs = [
        x
        for x in g.run(
            "rev-list", "--full-history", "--topo-order", "--reverse", "HEAD", "--", path
        ).split()
        if x
    ]
    if limit:
        revs = revs[:limit]
    pm = {}
    for line in g.run("rev-list", "--parents", "HEAD").splitlines():
        p = line.split()
        pm[p[0]] = p[1:]
    inset = set(revs)
    resolved = {}

    def nearest(c):
        if c in resolved:
            return resolved[c]
        chain, cur = [], c
        while cur is not None and cur not in inset:
            chain.append(cur)
            ps = pm.get(cur)
            cur = ps[0] if ps else None
        for x in chain:
            resolved[x] = cur
        resolved[c] = cur
        return cur

    preds, childcount = {}, Counter()
    for r in revs:
        ps = []
        for p in pm.get(r, []):
            a = nearest(p)
            if a is not None and a not in ps:
                ps.append(a)
        preds[r] = ps
        for p in ps:
            childcount[p] += 1

    base = {}  # rev -> record from phase 1
    natmaps = {}  # rev -> {natkey: rowid}
    idstr = {}  # rev -> "\n".join(ids)
    shas = {}
    tasks = []
    t0 = time.time()
    pool = Pool(procs)
    ndone = [0]

    def drain():
        # dispatched in batches so the in-flight id strings stay bounded; a
        # 7008-commit task list held whole was 7 GB of row ids.
        if not tasks:
            return
        for rv, rc in pool.imap_unordered(work, tasks, chunksize=4):
            base[rv].update(rc)
            ndone[0] += 1
        tasks.clear()

    for n, rev in enumerate(revs):
        rec = {"rev": rev, "i": n, "preds": preds[rev]}
        sha = g.blob_sha(rev, path)
        shas[rev] = sha
        if sha is None:
            rec.update(outcome="excluded", why="path absent at this commit")
            base[rev] = rec
            continue
        raw = g.blob(sha)
        rec["bytes"] = len(raw)
        try:
            header, rows, notes = read_csv(raw)
        except Malformed as e:
            rec.update(outcome="refused", stage="read", reason=str(e), mdtbl="refused",
                       csvmode="refused")
            base[rev] = rec
            continue
        rec["rows"], rec["cols"], rec["notes"] = len(rows), len(header), notes
        bad_ref = [h for h in header if not ident_ok_reference(h)]
        bad_spec = [h for h in header if not ident_ok_spec(h)]
        rec["n_illegal_reference"], rec["illegal_colnames_reference"] = len(bad_ref), bad_ref[:8]
        rec["n_illegal_spec"], rec["illegal_colnames_spec"] = len(bad_spec), bad_spec[:8]
        keycol = "rowid"
        while keycol in header:
            keycol += "_"
        colmap = colmap_for(header, keycol)
        rec["renamed"] = {h: m for h, m in colmap.items() if h != m}
        nks = natkeys(header, rows, natkey)
        rec["natkey_present"] = nks is not None
        parent = preds[rev][0] if preds[rev] else None
        pnat = natmaps.get(parent, {})
        ids, carried = [], 0
        for i, r in enumerate(rows):
            k = nks[i] if nks else None
            if k is not None and k in pnat:
                ids.append(pnat[k])
                carried += 1
            else:
                ids.append(mint(rev, i))
        if len(preds[rev]) > 1 and nks:
            m2 = natmaps.get(preds[rev][1], {})
            for i, k in enumerate(nks):
                if k in m2 and k not in pnat:
                    ids[i] = m2[k]
                    carried += 1
        rec["carried_by_key"] = carried
        rec["reminted"] = len(rows) - carried
        natmaps[rev] = dict(zip(nks, ids)) if nks else {}
        idstr[rev] = "\n".join(ids)
        rec["outcome"] = "ok"
        base[rev] = rec
        tasks.append(
            (repo, path, rev, sha, idstr[rev], shas.get(parent), idstr.get(parent, ""),
             colmap, keycol, natkey, name, cfg.get("csvkey"))
        )
        for p in preds[rev]:
            childcount[p] -= 1
            if childcount[p] <= 0:
                natmaps.pop(p, None)
                idstr.pop(p, None)
        if len(tasks) >= 192:
            drain()
        if n % 500 == 0:
            print(f"  [1] {name} {n}/{len(revs)} done={ndone[0]} {time.time() - t0:.0f}s",
                  flush=True)
    drain()
    pool.close()
    pool.join()

    assert len(base) == len(revs), (len(base), len(revs))
    dispatched = set()
    for r in revs:
        assert base[r].get("outcome") in ("ok", "refused", "excluded"), r
        if base[r]["outcome"] == "ok":
            assert "mdtbl" in base[r], f"phase2 lost {r}"
    out = os.path.join(outdir, f"ledger-{name}.jsonl")
    with open(out, "w") as fh:
        for r in revs:
            fh.write(json.dumps(base[r], default=str) + "\n")
    print(f"[dispatched {ndone[0]}] {name}: {len(revs)} commits -> {out}  ({time.time() - t0:.0f}s)")


if __name__ == "__main__":
    run(sys.argv[1], CORPORA[sys.argv[1]], int(sys.argv[2]) if len(sys.argv) > 2 else None)
