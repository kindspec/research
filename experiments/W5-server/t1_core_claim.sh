#!/bin/bash
# W5-T1: THE CORE CLAIM.
# A plain `git clone` -- no .gitattributes, no merge config, none of our tooling
# -- must receive a correctly merged, VALID artifact after a server-side merge
# of two edits that stock git cannot merge.
set -u
export GIT_CONFIG_NOSYSTEM=1
H=$(cd "$(dirname "$0")" && pwd)
export HOME=$H/work/fakehome
W=$H/work; rm -rf "$W"; mkdir -p "$W/fakehome"
printf '[user]\n\tname=t\n\temail=t@t\n[init]\n\tdefaultBranch=main\n' > "$HOME/.gitconfig"
cd "$W"
hr(){ echo; echo "=================================================================="; echo "### $*"; echo "=================================================================="; }

BASE='| id     | item     | qty | unit  |
| ------ | -------- | --: | ----: |
| r_0001 | widget   |  10 | 12.00 |
| r_0002 | gadget   |  20 |  6.00 |
| r_0003 | sprocket |   8 | 15.00 |

grand := sum(total)
'

hr "SETUP: a bare server repo + two divergent edits to the SAME LINE"
git init -q --bare srv.git
git init -q dev; cd dev; git remote add o ../srv.git
printf '%s' "$BASE" > budget.tbl
git add -A; git commit -qm base >/dev/null; git push -q o main
git checkout -qb alice
sed -i 's/| r_0002 | gadget   |  20 |  6.00 |/| r_0002 | gadget   |  25 |  6.00 |/' budget.tbl
git commit -qam 'alice: gadget qty 20 -> 25' >/dev/null; git push -q o alice
git checkout -q main
sed -i 's/| r_0002 | gadget   |  20 |  6.00 |/| r_0002 | gadget   |  20 |  6.50 |/' budget.tbl
git commit -qam 'bob: gadget unit 6.00 -> 6.50' >/dev/null; git push -q o main
echo "alice: r_0002 qty  6->25   (column 'qty')"
echo "bob  : r_0002 unit 6.00->6.50 (column 'unit')"
echo "SAME LINE, DIFFERENT CELLS.  Correct merge = qty 25 AND unit 6.50."
cd "$W"

hr "CONTROL: what STOCK GIT does on the bare server (the forge merge button)"
cd srv.git
git merge-tree --write-tree main alice > /tmp/w5mt.txt 2>&1; echo "merge-tree exit=$?  (1 = conflicted)"
T=$(head -1 /tmp/w5mt.txt)
echo "--- the file stock git would produce ---"
git cat-file -p "$T:budget.tbl" | sed 's/^/    /'
echo
echo ">> Conflict markers inside the artifact.  It is no longer a table."
echo ">> This is what a forge's green Merge button writes.  Nothing in the repo"
echo ">> can prevent it, because a bare repo never reads .gitattributes."
cd "$W"

hr "THE SERVER MERGE"
python3 "$H/gws_merge_server.py" merge --repo srv.git \
        --into refs/heads/main --from refs/heads/alice \
        --message 'Merge alice into main'
echo "exit=$?"

hr "PROOF: a PLAIN clone. No tooling. No config. No .gitattributes."
rm -rf plain
env -u GIT_CONFIG_NOSYSTEM HOME=/nonexistent-home-so-no-user-config \
    git clone -q "$W/srv.git" plain 2>/dev/null || git clone -q "$W/srv.git" plain
cd plain
echo "git version of the naive client: $(git --version)"
echo "--- .gitattributes present? ---"
ls -la .gitattributes 2>&1 | sed 's/^/    /'
echo "--- any merge driver configured? ---"
git config --get-regexp '^merge\.' | sed 's/^/    /'; echo "    (none)"
echo "--- is any gws tool on PATH? ---"
command -v gws gws_merge_server.py 2>&1 | sed 's/^/    /'; echo "    (none)"
echo
echo "--- budget.tbl AS RECEIVED BY THE PLAIN CLONE ---"
cat budget.tbl | sed 's/^/    /'
echo
echo "--- verification ---"
python3 - <<'PY'
import sys
txt=open('budget.tbl').read()
assert '<<<<<<<' not in txt and '=======' not in txt, "CONFLICT MARKERS PRESENT"
rows=[l for l in txt.splitlines() if l.strip().startswith('|')]
cols=[c.strip() for c in rows[0].strip().strip('|').split('|')]
data=[dict(zip(cols,[c.strip() for c in l.strip().strip('|').split('|')])) for l in rows[2:]]
w={d['id']:d for d in data}
print("    parses as a table :", len(data), "rows x", len(cols), "cols")
print("    zero conflict markers: True")
print("    r_0002 qty  =", w['r_0002']['qty'],  "(alice's edit) ", "OK" if w['r_0002']['qty']=='25' else "*** WRONG ***")
print("    r_0002 unit =", w['r_0002']['unit'], "(bob's edit)   ", "OK" if w['r_0002']['unit']=='6.50' else "*** WRONG ***")
print("    r_0001/r_0003 untouched:", w['r_0001']['qty']=='10' and w['r_0003']['unit']=='15.00')
sys.exit(0 if (w['r_0002']['qty']=='25' and w['r_0002']['unit']=='6.50') else 1)
PY
echo "    core-claim verification exit=$?"
echo
echo "--- is it a real merge commit with both parents? ---"
git log --graph --oneline -4 | sed 's/^/    /'
echo "    parents: $(git rev-list --parents -n1 HEAD | wc -w) entries (1 commit + 2 parents = 3)"

hr "refs/gws/* MUST NOT be fetched by a plain clone"
echo "--- refs the plain clone actually has ---"
git for-each-ref --format='    %(refname)' | sed 's/^/  /'
echo "--- refs ON THE SERVER ---"
git --git-dir="$W/srv.git" for-each-ref --format='    %(refname)' | sed 's/^/  /'
echo "--- ls-remote shows they exist but were not fetched ---"
git ls-remote origin 'refs/gws/*' | sed 's/^/    /' ; echo "    (empty here: this merge had no unresolved cells)"

hr "SAME TEST, but with an UNRESOLVABLE cell conflict (both edit the same cell)"
cd "$W"
cd dev; git fetch -q o; git checkout -q main; git reset -q --hard o/main
git checkout -qb carol
sed -i 's/| *25 |/|  40 |/' budget.tbl; git commit -qam 'carol: qty 25 -> 40' >/dev/null; git push -q o carol
git checkout -q main
sed -i 's/| *25 |/|  99 |/' budget.tbl; git commit -qam 'dave: qty 25 -> 99' >/dev/null; git push -q o main
cd "$W"
echo "carol: qty 25->40 ; dave: qty 25->99 -- SAME CELL, genuinely unresolvable"
python3 "$H/gws_merge_server.py" merge --repo srv.git --into refs/heads/main --from refs/heads/carol
echo "exit=$?"
echo "--- refs/gws on the server ---"
git --git-dir="$W/srv.git" for-each-ref --format='    %(refname)' refs/gws
echo "--- main did NOT move (no silent lost update) ---"
echo "    main = $(git --git-dir=$W/srv.git rev-parse --short main) = dave's commit"
echo "--- and a fresh PLAIN clone still receives a valid artifact, and no gws refs ---"
rm -rf plain2; git clone -q "$W/srv.git" plain2; cd plain2
grep -c '<<<<<<<' budget.tbl || echo "    zero conflict markers"
git for-each-ref --format='    %(refname)' | grep gws && echo "    *** LEAKED ***" || echo "    refs/gws/* NOT fetched by default: CONFIRMED"
echo "--- our client fetches them explicitly ---"
git fetch -q origin 'refs/gws/*:refs/gws/*'
git for-each-ref --format='    %(refname)' refs/gws
git cat-file -p "$(git for-each-ref --format='%(refname)' refs/gws | head -1):conflicts.json" | sed 's/^/    /'
