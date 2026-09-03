#!/bin/bash
# D9-2: does a BARE repo (what a forge has) honour .gitattributes at all?
# Tests the FORGE MERGE PATH: git merge-tree --write-tree in a bare repo.
set -u
export GIT_CONFIG_NOSYSTEM=1
export HOME=$PWD/fakehome; rm -rf fakehome; mkdir -p fakehome
printf '[user]\n\tname=t\n\temail=t@t\n[init]\n\tdefaultBranch=main\n' > fakehome/.gitconfig
W=$PWD/work; rm -rf "$W"; mkdir -p "$W"; cd "$W"
hr(){ echo; echo "=========================================================="; echo "### $*"; echo "=========================================================="; }
echo "git version: $(git --version)"

# ---- build a repo with THREE attribute regimes on three files ----
git init -q src; cd src
printf 'total,100\n' > u.csv     # merge=union
printf 'total,100\n' > b.csv     # binary
printf 'total,100\n' > p.csv     # merge=probe (custom driver)
cat > .gitattributes <<'EOF'
u.csv merge=union
b.csv binary
p.csv merge=probe
EOF
git add -A; git commit -qm base
git checkout -qb feat
for f in u b p; do printf 'total,200\n' > $f.csv; done; git commit -qam feat
git checkout -q main
for f in u b p; do printf 'total,300\n' > $f.csv; done; git commit -qam main
cd "$W"

hr "1. NON-BARE (developer laptop) baseline: git merge-tree --write-tree"
cd src
T=$(git merge-tree --write-tree main feat 2>&1); echo "$T" | head -8
cd "$W"

hr "2. BARE repo (a forge). Same objects. Same .gitattributes IN THE TREE."
git clone -q --bare src bare.git
cd bare.git
echo "is-bare: $(git rev-parse --is-bare-repository)"
echo ".gitattributes in HEAD tree:"; git cat-file -p HEAD:.gitattributes | sed 's/^/    /'
echo "\$GIT_DIR/info/attributes exists? "; ls info/attributes 2>&1
echo
echo "-- merge-tree in the BARE repo --"
git merge-tree --write-tree main feat > /tmp/d9out 2>&1; echo "exit=$?"
cat /tmp/d9out | head -20
TREE=$(head -1 /tmp/d9out)
echo
echo "-- resulting u.csv (merge=union) in bare merge --"
git cat-file -p "$TREE:u.csv" 2>/dev/null | sed 's/^/    /'
echo "-- resulting b.csv (binary) in bare merge --"
git cat-file -p "$TREE:b.csv" 2>/dev/null | sed 's/^/    /'
echo "-- resulting p.csv (merge=probe) in bare merge --"
git cat-file -p "$TREE:p.csv" 2>/dev/null | sed 's/^/    /'

hr "3. Does attr.tree (git 2.40+) make the bare repo read .gitattributes?"
git -c attr.tree=HEAD merge-tree --write-tree main feat > /tmp/d9out2 2>&1; echo "exit=$?"
cat /tmp/d9out2 | head -20
TREE2=$(head -1 /tmp/d9out2)
echo "-- u.csv with attr.tree=HEAD --"; git cat-file -p "$TREE2:u.csv" 2>/dev/null | sed 's/^/    /'
echo "-- b.csv with attr.tree=HEAD --"; git cat-file -p "$TREE2:b.csv" 2>/dev/null | sed 's/^/    /'

hr "4. Same, but attributes placed in \$GIT_DIR/info/attributes (server operator action)"
cp <(git cat-file -p HEAD:.gitattributes) info/attributes
cat info/attributes | sed 's/^/    /'
git merge-tree --write-tree main feat > /tmp/d9out3 2>&1; echo "exit=$?"
cat /tmp/d9out3 | head -20
TREE3=$(head -1 /tmp/d9out3)
echo "-- u.csv --"; git cat-file -p "$TREE3:u.csv" 2>/dev/null | sed 's/^/    /'
echo "-- b.csv --"; git cat-file -p "$TREE3:b.csv" 2>/dev/null | sed 's/^/    /'
rm -f info/attributes

hr "5. The path Gitea/Forgejo actually take: temp WORKTREE + real 'git merge'"
cd "$W"; rm -rf srv-wt
git clone -q bare.git srv-wt   # server clones to a temp worktree
cd srv-wt
echo ".gitattributes checked out? $(ls -1 .gitattributes 2>&1)"
git merge origin/feat 2>&1 | head -6
echo "-- u.csv --"; cat u.csv | sed 's/^/    /'
echo "-- b.csv --"; cat b.csv | sed 's/^/    /'; git status --short b.csv
echo "-- p.csv (custom driver, undefined) --"; cat p.csv | sed 's/^/    /'
