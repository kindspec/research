#!/bin/bash
set -u
export GIT_CONFIG_NOSYSTEM=1
export HOME=$PWD/fakehome
W=$PWD/work3; rm -rf "$W"; mkdir -p "$W"; cd "$W"
git init -q r; cd r; echo a > a; git add -A; git commit -qm one
# common ancestor note
git notes add -m 'BASE note' HEAD
git update-ref refs/notes/theirs refs/notes/commits    # fork point
# ours diverges
git notes add -f -m 'OURS note' HEAD
# theirs diverges independently
GIT_NOTES_REF=refs/notes/theirs git notes add -f -m 'THEIRS note' HEAD
echo "ours   ref: $(git rev-parse refs/notes/commits)  -> $(git notes show HEAD)"
echo "theirs ref: $(git rev-parse refs/notes/theirs)   -> $(GIT_NOTES_REF=refs/notes/theirs git notes show HEAD)"
echo "merge-base: $(git merge-base refs/notes/commits refs/notes/theirs)"
echo
echo "=== (a) default 'manual' strategy on a GENUINE divergence ==="
git notes merge refs/notes/theirs; echo "exit=$?"
echo "--- .git/NOTES_MERGE_WORKTREE contents ---"
find .git/NOTES_MERGE_WORKTREE -type f 2>/dev/null | while read f; do echo "  file: ${f#.git/NOTES_MERGE_WORKTREE/}"; sed 's/^/    /' "$f"; done
echo "--- git status / NOTES_MERGE_REF ---"; cat .git/NOTES_MERGE_REF 2>/dev/null
git notes merge --abort
echo
echo "=== (b) -s union ==="
git notes merge -s union refs/notes/theirs >/dev/null 2>&1; git notes show HEAD | sed 's/^/    /'
git update-ref refs/notes/commits $(git rev-parse refs/notes/commits^1 2>/dev/null || git rev-parse refs/notes/commits)
echo
echo "=== (c) can 'git notes merge' run in a BARE repo (i.e. server-side)? ==="
cd "$W"; git clone -q --bare r bare.git; cd bare.git
git fetch -q ../r 'refs/notes/*:refs/notes/*' 2>&1|head -2
echo "refs: $(git for-each-ref --format='%(refname)' refs/notes | tr '\n' ' ')"
git notes merge refs/notes/theirs 2>&1 | head -3; echo "exit=$?"
echo
echo "=== (d) notes.rewriteRef DEFAULT value per docs ==="
man git-config 2>/dev/null | col -b | grep -A8 'notes\.rewriteRef' | head -14
