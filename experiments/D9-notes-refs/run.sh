#!/bin/bash
# D9-3: git notes + custom ref namespaces as a home for MUTABLE COLLABORATIVE STATE
set -u
export GIT_CONFIG_NOSYSTEM=1
export HOME=$PWD/fakehome; rm -rf fakehome; mkdir -p fakehome
printf '[user]\n\tname=t\n\temail=t@t\n[init]\n\tdefaultBranch=main\n' > fakehome/.gitconfig
W=$PWD/work; rm -rf "$W"; mkdir -p "$W"; cd "$W"
hr(){ echo; echo "=========================================================="; echo "### $*"; echo "=========================================================="; }

hr "1. Do notes / custom refs transfer on CLONE by default?"
git init -q --bare origin.git
git init -q up; cd up; git remote add origin ../origin.git
echo hello > a.txt; git add -A; git commit -qm one
git notes add -m 'review: LGTM, 2 comments' HEAD
git update-ref refs/gws/conflicts/0001 $(git rev-parse HEAD)
git update-ref refs/bugs/abc123 $(git rev-parse HEAD)
echo "-- local refs before push --"; git for-each-ref --format='  %(refname)' | sort
echo "-- push (default refspec) --"; git push -q origin main 2>&1 | head -3
echo "-- refs that landed on the SERVER --"; git --git-dir=../origin.git for-each-ref --format='  %(refname)' | sort
cd "$W"
echo "-- fresh clone --"; git clone -q origin.git c1; cd c1
echo "-- refs in the clone --"; git for-each-ref --format='  %(refname)' | sort
echo "-- git notes show HEAD --"; git notes show HEAD 2>&1 | head -2
echo ">> VERDICT: notes and custom refs are NOT pushed and NOT cloned by default."
cd "$W"

hr "2. Explicit refspecs — do they work? and what does a forge accept?"
cd up
echo "-- push notes explicitly --"
git push origin 'refs/notes/*:refs/notes/*' 2>&1 | head -4
echo "-- push custom namespaces explicitly --"
git push origin 'refs/gws/*:refs/gws/*' 'refs/bugs/*:refs/bugs/*' 2>&1 | head -4
echo "-- server refs now --"; git --git-dir=../origin.git for-each-ref --format='  %(refname)' | sort
cd "$W"; rm -rf c2; git clone -q origin.git c2; cd c2
echo "-- default clone of a server that HAS them --"; git for-each-ref --format='  %(refname)' | sort
echo "-- must ask explicitly: --"
git fetch -q origin 'refs/notes/*:refs/notes/*' 'refs/gws/*:refs/gws/*'
git for-each-ref --format='  %(refname)' | sort
echo ">> Every participant must configure a custom refspec. Nothing in the repo can do it for them."
cd "$W"

hr "3. git notes MERGE: what happens when two people annotate the same object?"
cd up
git notes add -f -m 'A: first note' HEAD
git rev-parse refs/notes/commits > /dev/null
git update-ref refs/notes/other refs/notes/commits
GIT_NOTES_REF=refs/notes/other git notes add -f -m 'B: conflicting note' HEAD
echo "-- ours: $(git notes show HEAD)"
echo "-- theirs: $(GIT_NOTES_REF=refs/notes/other git notes show HEAD)"
echo
echo "-- (3a) default strategy (manual) --"
git notes merge refs/notes/other 2>&1 | head -8; echo "exit=$?"
ls -la .git/NOTES_MERGE_WORKTREE 2>/dev/null | head -4
echo "-- the conflicted note ON DISK --"
find .git/NOTES_MERGE_WORKTREE -type f 2>/dev/null | head -2 | xargs -r cat
git notes merge --abort 2>/dev/null
echo
echo "-- (3b) -s union --"
git notes merge -s union refs/notes/other 2>&1 | head -3
echo "result: "; git notes show HEAD | sed 's/^/    /'
echo
echo "-- (3c) -s cat_sort_uniq --"
git update-ref refs/notes/other2 refs/notes/commits
GIT_NOTES_REF=refs/notes/other2 git notes add -f -m 'C: third' HEAD
git notes merge -s cat_sort_uniq refs/notes/other2 2>&1 | head -3
git notes show HEAD | sed 's/^/    /'
echo ">> notes merge strategies: manual|ours|theirs|union|cat_sort_uniq. NO structured/type-aware option."
echo ">> 'manual' uses a WORKTREE at .git/NOTES_MERGE_WORKTREE -> unusable in a bare/server context."
cd "$W"

hr "4. notes.rewriteRef: do notes survive rebase/amend?"
cd up
git checkout -q -b nb; echo x >> a.txt; git commit -qam two
git notes add -f -m 'note on commit two' HEAD
OLD=$(git rev-parse HEAD)
echo "-- default notes.rewriteRef: '$(git config notes.rewriteRef || echo UNSET)'"
git commit -q --amend -m 'two amended'
echo "-- after amend, note present? --"; git notes show HEAD 2>&1 | head -2
git reset -q --hard $OLD
git config notes.rewrite.amend true; git config notes.rewriteRef 'refs/notes/commits'
git commit -q --amend -m 'two amended2'
echo "-- with notes.rewriteRef set: --"; git notes show HEAD 2>&1 | head -2
echo ">> notes copy-forward across rewrites requires LOCAL config (notes.rewriteRef). Same failure class."
cd "$W"

hr "5. Object cost of a ref-based op-log: 1000 tiny mutations"
rm -rf oplog; git init -q oplog; cd oplog
echo seed > s; git add -A; git commit -qm seed
PARENT=""
S=$(date +%s%N)
for i in $(seq 1 1000); do
  BLOB=$(printf '{"op":%d,"kind":"comment","body":"x"}' $i | git hash-object -w --stdin)
  TREE=$(printf '100644 blob %s\top\n' "$BLOB" | git mktree)
  if [ -z "$PARENT" ]; then C=$(git commit-tree -m "op$i" "$TREE"); else C=$(git commit-tree -p "$PARENT" -m "op$i" "$TREE"); fi
  git update-ref refs/gws/oplog "$C"; PARENT="$C"
done
E=$(date +%s%N)
echo "1000 ops appended in $(( (E-S)/1000000 )) ms  => $(( 1000000000 / ((E-S)/1000) )) ops/sec-ish"
echo "loose objects: $(find .git/objects -type f -not -path '*pack*' | wc -l)"
echo "du .git: $(du -sh .git | cut -f1)"
git gc -q --aggressive 2>/dev/null
echo "after gc: $(du -sh .git | cut -f1)"
echo "-- reading the whole log back --"
S=$(date +%s%N); git rev-list refs/gws/oplog | wc -l; E=$(date +%s%N); echo "rev-list: $(( (E-S)/1000000 )) ms"
