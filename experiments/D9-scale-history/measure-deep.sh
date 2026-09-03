#!/bin/bash
set -u
export GIT_CONFIG_NOSYSTEM=1; export HOME=$PWD/fakehome
cd deep
t(){ local L="$1"; shift; local S=$(date +%s%N); "$@" >/dev/null 2>&1; local E=$(date +%s%N); printf '  %-52s %8d ms\n' "$L" $(( (E-S)/1000000 )); }
tv(){ local L="$1"; shift; local S=$(date +%s%N); local O=$("$@" 2>&1|tail -1); local E=$(date +%s%N); printf '  %-52s %8d ms  %s\n' "$L" $(( (E-S)/1000000 )) "$O"; }
echo "=== DEEP HISTORY: $(git rev-list --count HEAD) commits, $(git ls-files|wc -l) files, pack $(du -sh .git/objects/pack/*.pack|cut -f1) ==="
F=docs/d7.md
echo "  revisions of $F: $(git rev-list --count HEAD -- $F)"
rm -f .git/objects/info/commit-graph; rm -rf .git/objects/info/commit-graphs; rm -f .git/objects/pack/multi-pack-index
echo
echo "--- NO commit-graph, NO midx ---"
tv "git rev-list --count HEAD"                       git rev-list --count HEAD
tv "git log --oneline -- ONE FILE  (count)"          bash -c "git log --oneline -- $F | wc -l"
t  "git log --follow -- ONE FILE"                    git log --follow -- $F
t  "git blame ONE FILE"                              git blame $F
t  "git log --oneline -1000"                         git log --oneline -1000
tv "git describe / merge-base HEAD HEAD~40000"       git merge-base HEAD HEAD~40000
t  "git checkout HEAD~49000 (distant)"               git checkout -q --detach HEAD~49000
t  "git checkout back to tip"                        git checkout -q --detach refs/heads/main
echo
echo "--- WRITE commit-graph + multi-pack-index ---"
S=$(date +%s%N); git commit-graph write --reachable >/dev/null 2>&1; E=$(date +%s%N)
printf '  %-52s %8d ms  (%s)\n' "commit-graph write --reachable" $(( (E-S)/1000000 )) "$(du -sh .git/objects/info/commit-graph|cut -f1)"
S=$(date +%s%N); git multi-pack-index write >/dev/null 2>&1; E=$(date +%s%N)
printf '  %-52s %8d ms  (%s)\n' "multi-pack-index write" $(( (E-S)/1000000 )) "$(du -sh .git/objects/pack/multi-pack-index 2>/dev/null|cut -f1)"
echo
echo "--- WITH commit-graph + midx ---"
tv "git rev-list --count HEAD"                       git rev-list --count HEAD
tv "git log --oneline -- ONE FILE  (count)"          bash -c "git log --oneline -- $F | wc -l"
t  "git log --follow -- ONE FILE"                    git log --follow -- $F
t  "git blame ONE FILE"                              git blame $F
t  "git checkout HEAD~49000 (distant)"               git checkout -q --detach HEAD~49000
t  "git checkout back to tip"                        git checkout -q --detach refs/heads/main
echo
echo "--- feature.manyFiles / core.untrackedCache / fsmonitor availability ---"
echo "  git status (cold):"; t "  git status" git status
git config feature.manyFiles true
echo "  feature.manyFiles=true implies: index.version=4, core.untrackedCache=true, index.skipHash=true"
git config --get-all index.version; git config core.untrackedCache 2>/dev/null
t "  git status (feature.manyFiles)" git status
echo "  core.fsmonitor built-in available? "
git config core.fsmonitor true 2>&1 && git status >/dev/null 2>&1 && echo "    fsmonitor accepted: $(git fsmonitor--daemon status 2>&1 | head -1)"
git config --unset core.fsmonitor
echo
echo "--- sparse-index / sparse-checkout ---"
git sparse-checkout init --cone --sparse-index 2>&1 | head -2
git sparse-checkout set docs 2>&1 | head -2
echo "  sparse index in use: $(git config core.sparseCheckoutCone) / $(test -f .git/index && git ls-files --sparse 2>/dev/null | head -1)"
git sparse-checkout disable 2>/dev/null
echo
echo "--- scalar available? ---"
which scalar 2>&1 || echo "  scalar not on PATH"
git scalar --help >/dev/null 2>&1 && echo "  'git scalar' subcommand present" || echo "  'git scalar' not present"
echo
echo "--- CLONE the deep repo ---"
cd ..; rm -rf deep-clone deep-shallow
t "git clone (full, 50k commits)"                    git clone -q --no-hardlinks file://$PWD/deep deep-clone
echo "     -> $(du -sh deep-clone/.git|cut -f1)"
t "git clone --depth=1"                              git clone -q --depth=1 file://$PWD/deep deep-shallow
echo "     -> $(du -sh deep-shallow/.git|cut -f1)"
