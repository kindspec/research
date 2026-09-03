"""For every refusal on a real commit, show the offending bytes."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from harness import Git, read_csv
from replay import CORPORA

HERE = os.path.dirname(os.path.abspath(__file__))
name = sys.argv[1]
cfg = CORPORA[name]
g = Git(cfg["repo"])
L = [json.loads(x) for x in open(os.path.join(HERE, f"ledger-{name}.jsonl"))]
groups = {}
for r in L:
    ref = r.get("mdtbl") == "refused" or r.get("csvmode") == "refused" or r.get("outcome") == "refused"
    if not ref:
        continue
    why = tuple(sorted(set((r.get("csvmode_reason") or []) + ([r.get("mdtbl_reason")] if r.get("mdtbl_reason") else []) + ([r.get("reason")] if r.get("reason") else []))))
    groups.setdefault(why, []).append(r)
print(f"### {name}: {len(L)} commits, {sum(len(v) for v in groups.values())} refused, "
      f"{len(groups)} distinct refusal signatures\n")
for why, rs in sorted(groups.items(), key=lambda kv: -len(kv[1])):
    first = rs[0]
    meta = g.run("log", "-1", "--format=%h %ad %an :: %s", "--date=short", first["rev"]).strip()
    print(f"* {len(rs)} commit(s), first {meta}")
    for w in why:
        print(f"    REFUSAL: {w}")
    sha = g.blob_sha(first["rev"], cfg["path"])
    raw = g.blob(sha)
    hdr, rows, _ = read_csv(raw)
    body = raw.decode("utf-8", "replace").replace("\r\n", "\n").split("\n")[1:]
    shown = 0
    for i, r in enumerate(rows):
        if len(r) != len(hdr) and shown < 2:
            print(f"    BYTES  header {len(hdr)} fields: {','.join(hdr)[:110]}")
            print(f"    BYTES  row {len(r)} fields: {body[i][:150]!r}")
            shown += 1
    if shown == 0:
        print(f"    (no ragged row; see the message above) header: {','.join(hdr)[:160]}")
    print(f"    commits: {' '.join(x['rev'][:8] for x in rs[:8])}")
    print()
