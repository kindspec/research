#!/bin/bash
# D9-6 CONSTRUCTIVE: a server that OWNS the repo does not need git's merge-driver
# machinery at all. merge-tree hands it the three stages; it merges them itself
# and writes the result with commit-tree. No .gitattributes, no local config.
set -u
export GIT_CONFIG_NOSYSTEM=1
export HOME=$PWD/fakehome; rm -rf fakehome; mkdir -p fakehome
printf '[user]\n\tname=s\n\temail=s@s\n[init]\n\tdefaultBranch=main\n' > fakehome/.gitconfig
W=$PWD/work; rm -rf "$W"; mkdir -p "$W"; cd "$W"
hr(){ echo; echo "=========================================================="; echo "### $*"; echo "=========================================================="; }

hr "SETUP: divergent edits to a CSV, pushed to a BARE server repo"
git init -q --bare srv.git
git init -q dev; cd dev; git remote add o ../srv.git
printf 'item,qty,price\napple,1,10\nbanana,2,20\ncherry,3,30\n' > s.csv
git add -A; git commit -qm base; git push -q o main
git checkout -qb alice; sed -i 's/^apple,1,10/apple,5,10/' s.csv; git commit -qam alice; git push -q o alice
git checkout -q main; sed -i 's/^apple,1,10/apple,1,99/' s.csv; git commit -qam bob; git push -q o main
echo "alice changed apple QTY 1->5 ; bob changed apple PRICE 10->99 ; SAME LINE"
cd "$W"

hr "STEP 1: on the BARE server, merge-tree exposes the THREE STAGES"
cd srv.git
git merge-tree --write-tree main alice > out.txt 2>&1; echo "exit=$?"
cat out.txt
:
OURS=$(awk '$4=="s.csv" && $3==2 {print $2}' out.txt)
THEIRS=$(awk '$4=="s.csv" && $3==3 {print $2}' out.txt)
BASE=$(awk '$4=="s.csv" && $3==1 {print $2}' out.txt)
echo
echo "stage1(base)=$BASE  stage2(ours)=$OURS  stage3(theirs)=$THEIRS"
echo "-- server can read all three WITHOUT a working tree: --"
for s in BASE OURS THEIRS; do eval o=\$$s; echo "  [$s]"; git cat-file -p $o | sed 's/^/     /'; done

hr "STEP 2: the server runs ITS OWN type-aware merge on the three blobs"
cat > /tmp/d9csvmerge.py <<'PY'
import sys,csv,io,subprocess
def rd(o):
    t=subprocess.check_output(['git','cat-file','-p',o],text=True)
    r=list(csv.reader(io.StringIO(t)))
    return r[0], {row[0]:row for row in r[1:]}
b_h,b=rd(sys.argv[1]); o_h,o=rd(sys.argv[2]); t_h,t=rd(sys.argv[3])
keys=list(dict.fromkeys(list(o)+list(t)))
out=[b_h]; conflicts=[]
for k in keys:
    bb=b.get(k); oo=o.get(k); tt=t.get(k)
    if oo is None: out.append(tt); continue
    if tt is None: out.append(oo); continue
    row=[]
    for i,col in enumerate(b_h):
        bv=bb[i] if bb else None; ov=oo[i]; tv=tt[i]
        if ov==tv: row.append(ov)
        elif bv==ov: row.append(tv)      # only theirs changed
        elif bv==tv: row.append(ov)      # only ours changed
        else: row.append(ov); conflicts.append((k,col,bv,ov,tv))
    out.append(row)
w=io.StringIO(); csv.writer(w,lineterminator='\n').writerows(out)
sys.stdout.write(w.getvalue())
sys.stderr.write(repr(conflicts))
PY
MERGED=$(python3 /tmp/d9csvmerge.py "$BASE" "$OURS" "$THEIRS" 2>/tmp/d9conf)
echo "-- cell-level 3-way merge result --"; echo "$MERGED" | sed 's/^/   /'
echo "-- residual cell conflicts (structured, NOT markers) --"; cat /tmp/d9conf; echo

hr "STEP 3: server writes the result back as a real git commit — NO working tree"
NEWBLOB=$(printf '%s\n' "$MERGED" | git hash-object -w --stdin)
TREE=$(head -1 out.txt)
# rebuild tree with the merged blob
NEWTREE=$(git ls-tree main | sed "s|^100644 blob [0-9a-f]*\ts.csv|100644 blob $NEWBLOB\ts.csv|" | git mktree)
COMMIT=$(git commit-tree "$NEWTREE" -p main -p alice -m "merge alice into main (type-aware CSV merge, server-side)")
git update-ref refs/heads/main "$COMMIT" "$(git rev-parse main^{commit} 2>/dev/null || git rev-parse main)" 2>/dev/null || git update-ref refs/heads/main "$COMMIT"
echo "new main = $(git rev-parse --short main)"
echo "-- s.csv on the server after the server-side merge --"
git cat-file -p main:s.csv | sed 's/^/   /'
echo "-- is it a real merge commit? --"; git log --oneline --graph -3 main | sed 's/^/   /'

hr "STEP 4: a PLAIN git client with NO tooling clones and sees a correct, VALID CSV"
cd "$W"; rm -rf plain; git clone -q srv.git plain; cd plain
echo "git version used by the naive client: $(git --version)"
echo "-- s.csv --"; cat s.csv | sed 's/^/   /'
python3 -c "import csv,sys;r=list(csv.reader(open('s.csv')));print('   parses as CSV:',len(r),'rows,',len(r[0]),'cols')"
echo "-- .gitattributes present? --"; ls .gitattributes 2>&1 | sed 's/^/   /'
echo "-- local merge driver config? --"; git config --get-regexp '^merge\.' | sed 's/^/   /'; echo "   (none)"
echo
echo ">> The type-aware merge RAN, on the SERVER, with zero client tooling,"
echo ">> zero .gitattributes, and zero local git config. It is deployable."
echo ">> What it required: the server OWNS the repo and mediates the write."
