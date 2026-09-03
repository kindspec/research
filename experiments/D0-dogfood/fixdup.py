"""The colmap bug: `colmap` was keyed by original column name, so a file with
two columns of the SAME name (channels.csv has stretches of empty ones) emitted
one mangled name twice and the .mdtbl was refused for a duplicate column the
harness had manufactured. Find every affected commit and re-decide it."""
import json, os, sys
sys.path.insert(0, "/home/cam/repos_kindspec/working-git-backed-gws/experiments/D0-dogfood")
from harness import Git, read_csv, build_mdtbl, mangle, evaluate, Malformed, mint
from replay import CORPORA

def colmap_list(header, keycol):
    taken, out = {keycol}, []
    for h in header:
        m = mangle(h, taken); taken.add(m); out.append(m)
    return out

for nm, cfg in CORPORA.items():
    g = Git(cfg["repo"])
    L = [json.loads(x) for x in open(f"/home/cam/repos_kindspec/working-git-backed-gws/experiments/D0-dogfood/ledger-{nm}.jsonl")]
    hits = []
    for r in L:
        if r.get("outcome") != "ok":
            continue
        sha = g.blob_sha(r["rev"], cfg["path"])
        raw = g.blob(sha)
        head = raw.split(b"\n", 1)[0].decode("utf-8", "replace").rstrip("\r")
        cols = head.split("," if not cfg["path"].endswith(".tsv") else "\t")
        if len(set(cols)) != len(cols):
            hits.append((r, cols))
    print(f"{nm}: {len(hits)} commit(s) whose CSV header has a repeated column name")
    fixed_refuse = 0
    for r, cols in hits:
        sha = g.blob_sha(r["rev"], cfg["path"])
        header, rows, _ = read_csv(g.blob(sha))
        keycol = "rowid"
        while keycol in header:
            keycol += "_"
        names = colmap_list(header, keycol)
        lines = ["| " + " | ".join([keycol] + names) + " |",
                 "| " + " | ".join(["---"] * (len(names) + 1)) + " |"]
        for i, rr in enumerate(rows):
            lines.append("| " + " | ".join([mint(r["rev"], i)] + list(rr)) + " |")
        md = "\n".join(lines) + f"\n\nkey := {keycol}\n"
        try:
            evaluate(md); verdict = "accepted"; why = ""
        except Malformed as e:
            verdict = "refused"; why = str(e)[:110]
        if verdict == "refused":
            fixed_refuse += 1
        print(f"   {r['i']:5d} {r['rev'][:9]} ledger={r['mdtbl']:8s} corrected={verdict:8s} {why}")
        print(f"         repeated names: {[c for c in set(cols) if cols.count(c) > 1][:3]!r} "
              f"x{max(cols.count(c) for c in set(cols))}")
    print(f"   -> corrected refusals among these: {fixed_refuse} of {len(hits)}")
