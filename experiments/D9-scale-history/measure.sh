#!/bin/bash
set -u
export GIT_CONFIG_NOSYSTEM=1; export HOME=$PWD/fakehome
R=$PWD/repo
t(){ local L="$1"; shift; local S=$(date +%s%N); "$@" >/dev/null 2>&1; local E=$(date +%s%N); printf '  %-46s %7d ms\n' "$L" $(( (E-S)/1000000 )); }
tv(){ local L="$1"; shift; local S=$(date +%s%N); local O=$("$@" 2>&1); local E=$(date +%s%N); printf '  %-46s %7d ms   %s\n' "$L" $(( (E-S)/1000000 )) "$O"; }
cd "$R"
echo "=== REPO SHAPE ==="
echo "  commits:         $(git rev-list --count HEAD)"
echo "  files:           $(git ls-files | wc -l)"
echo "  file-revisions:  $(git rev-list --objects HEAD | wc -l) objects reachable"
echo "  .git (loose):    $(du -sh .git | cut -f1)"
git gc -q 2>/dev/null
echo "  .git (packed):   $(du -sh .git | cut -f1)"
echo "  packfile:        $(du -sh .git/objects/pack/*.pack 2>/dev/null | head -1 | cut -f1)"
echo "  worktree size:   $(du -sh --exclude=.git . | cut -f1)"
F=docs/doc00001.md
echo "  revisions of $F: $(git rev-list --count HEAD -- $F)"
echo
echo "=== A. THE TWO OPERATIONS A DOCUMENT APP NEEDS ==="
tv "git log --oneline -- one file (count)"        bash -c "git log --oneline -- $F | wc -l"
t  "git log -- one file (full)"                   git log -- $F
t  "git log --follow -- one file"                 git log --follow -- $F
t  "git blame one file"                           git blame $F
t  "git log -p -- one file (content history)"     git log -p -- $F
t  "git log --all --oneline (whole history)"      git log --all --oneline
echo
echo "=== B. WITHOUT vs WITH commit-graph ==="
rm -f .git/objects/info/commit-graph; rm -rf .git/objects/info/commit-graphs
t  "[no graph] git log --oneline | wc"            bash -c "git log --oneline | wc -l"
t  "[no graph] git rev-list --count HEAD"         git rev-list --count HEAD
t  "[no graph] git log --since=... "              git log --oneline --since='1 hour ago'
S=$(date +%s%N); git commit-graph write --reachable >/dev/null 2>&1; E=$(date +%s%N)
printf '  %-46s %7d ms   (%s)\n' "commit-graph write --reachable" $(( (E-S)/1000000 )) "$(du -sh .git/objects/info/commit-graph 2>/dev/null | cut -f1)"
t  "[graph]    git log --oneline | wc"            bash -c "git log --oneline | wc -l"
t  "[graph]    git rev-list --count HEAD"         git rev-list --count HEAD
echo
echo "=== C. CLONE COST ==="
cd "$(dirname $R)"; rm -rf clone-full clone-shallow clone-blobless clone-tree
t  "git clone (local, full)"                      git clone -q --no-hardlinks file://$R clone-full
echo "     -> $(du -sh clone-full/.git 2>/dev/null | cut -f1)"
t  "git clone --depth=1"                          git clone -q --depth=1 file://$R clone-shallow
echo "     -> $(du -sh clone-shallow/.git 2>/dev/null | cut -f1)"
t  "git clone --filter=blob:none"                 git clone -q --filter=blob:none file://$R clone-blobless
echo "     -> $(du -sh clone-blobless/.git 2>/dev/null | cut -f1)"
t  "git clone --filter=tree:0"                    git clone -q --filter=tree:0 file://$R clone-tree
echo "     -> $(du -sh clone-tree/.git 2>/dev/null | cut -f1)"
echo
echo "=== D. blame/log on a BLOBLESS partial clone (the mobile case) ==="
cd clone-blobless
tv "git log --oneline -- one file"                bash -c "git log --oneline -- $F | wc -l"
t  "git blame one file (must refetch blobs)"      git blame $F
echo "     .git after blame: $(du -sh .git | cut -f1)"
