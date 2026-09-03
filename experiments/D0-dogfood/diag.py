import sys, difflib
D="/home/cam/repos_kindspec/working-git-backed-gws/experiments/D0-dogfood"
sys.path.insert(0, D); sys.path.insert(0,"/home/cam/repos_kindspec/rowspec/reference")
from harness import Git, read_csv, build_mdtbl, mint, evaluate, Malformed
from replay import CORPORA, colmap_for
from rowspec.table import canon
nm = sys.argv[1]; lim = int(sys.argv[2])
cfg=CORPORA[nm]; g=Git(cfg["repo"])
revs=g.run("rev-list","--full-history","--topo-order","HEAD","--",cfg["path"]).split()
shown=0
for rev in revs[:lim]:
    sha=g.blob_sha(rev,cfg["path"])
    if not sha: continue
    try: hdr,rows,_=read_csv(g.blob(sha))
    except Malformed: continue
    ids=[mint(rev,i) for i in range(len(rows))]
    md=build_mdtbl(hdr,rows,ids,"rowid",colmap_for(hdr,"rowid"))
    try: evaluate(md)
    except Malformed: continue
    c=canon(md)
    if c!=md:
        a=md.splitlines(); b=c.splitlines()
        diffs=[(x,y) for x,y in zip(a,b) if x!=y]
        print(f"{nm} {rev[:8]}: canon rewrote {len(diffs)} of {len(a)} lines")
        for x,y in diffs[:3]:
            sm=difflib.SequenceMatcher(None,x,y)
            for tag,i1,i2,j1,j2 in sm.get_opcodes():
                if tag!="equal":
                    print(f"    {tag}: {x[i1:i2]!r} -> {y[j1:j2]!r}")
        shown+=1
        if shown>=3: break
print("done")
