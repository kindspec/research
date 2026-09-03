#!/bin/bash
# Simulate a FORGE: a bare repo, merged with `git merge-tree --write-tree`.
set -u
E="$(cd "$(dirname "$0")" && pwd)"; W="$E/work4"; rm -rf "$W"; mkdir -p "$W"
export PROBE_LOG="$W/log"; : > "$PROBE_LOG"
GIT="git -c user.name=T -c user.email=t@e -c init.defaultBranch=main"
n(){ wc -l < "$PROBE_LOG"; }

# build a normal repo with .gitattributes committed, then push to a bare "server"
S="$W/src"; mkdir -p "$S"; cd "$S"; $GIT init -q .
printf 'a\nCONTESTED\nz\n' > f.txt; printf 'f.txt merge=probe\n' > .gitattributes
$GIT add -A; $GIT commit -qm base
$GIT checkout -qb feature; printf 'a\nTHEIRS\nz\n' > f.txt; $GIT commit -qam t
$GIT checkout -q main; printf 'a\nOURS\nz\n' > f.txt; $GIT commit -qam o
$GIT init -q --bare "$W/server.git"
$GIT push -q "$W/server.git" main feature

cd "$W/server.git"
echo "=== the bare 'server' repo ==="
echo "  is-bare: $($GIT rev-parse --is-bare-repository)"
echo "  .gitattributes IS in the tree: $($GIT cat-file -p main:.gitattributes)"
echo "  there is no working tree, so no checked-out .gitattributes file:"
ls | tr '\n' ' '; echo

echo
echo "--- (a) forge WITHOUT the driver configured (the real world) ---"
M=$(n); OUT=$($GIT merge-tree --write-tree main feature 2>&1); E1=$?
[ $(n) -gt $M ] && echo "    DRIVER RAN" || echo "    driver NOT run"
echo "    exit=$E1"; echo "$OUT" | sed 's/^/    /'

echo
echo "--- (b) same bare repo, driver configured IN THE SERVER'S config ---"
$GIT config merge.probe.name p
$GIT config merge.probe.driver "$E/driver.sh %O %A %B %L %P"
M=$(n); TREE=$($GIT merge-tree --write-tree main feature 2>&1); E2=$?
[ $(n) -gt $M ] && echo "    DRIVER RAN  <-- so merge-tree DOES read .gitattributes from the TREE, not a worktree" || echo "    driver NOT run"
echo "    exit=$E2  tree=$TREE"
$GIT cat-file -p "$TREE:f.txt" 2>/dev/null | sed 's/^/    /'

echo
echo "=== CONCLUSION: the mechanism works server-side, but ONLY if the server operator"
echo "=== installs the binary and writes merge.probe.driver into the server's git config."
echo "=== Nothing in the repository can cause that to happen."
