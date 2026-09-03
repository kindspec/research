#!/bin/bash
set -u
W="$(cd "$(dirname "$0")" && pwd)/work3"; rm -rf "$W"; mkdir -p "$W"
GIT="git -c user.name=T -c user.email=t@e -c init.defaultBranch=main"
mk(){ D="$W/$1"; rm -rf "$D"; mkdir -p "$D"; cd "$D"; $GIT init -q .
  printf 'a\nC\nz\n' > f.txt; printf 'f.txt merge=probe\n' > .gitattributes
  $GIT add -A; $GIT commit -qm base
  $GIT checkout -qb feature; printf 'a\nT\nz\n' > f.txt; $GIT commit -qam t
  $GIT checkout -q main; printf 'a\nO\nz\n' > f.txt; $GIT commit -qam o; }

echo "=== THE THREE CONFIG STATES A CLONER CAN BE IN ==="
echo
echo "--- STATE 1: nothing in config (plain clone, tool not installed) ---"
mk s1
echo "git merge      :"; $GIT merge feature 2>&1 | sed 's/^/    /'; echo "    exit=${PIPESTATUS[0]}"
$GIT merge --abort 2>/dev/null
echo "git merge-tree :"; $GIT merge-tree --write-tree main feature 2>&1 | sed 's/^/    /'; echo "    exit=$?"

echo
echo "--- STATE 2: merge.probe.name set, merge.probe.driver MISSING ---"
mk s2; $GIT config merge.probe.name "some tool"
echo "git merge      :"; $GIT merge feature 2>&1 | sed 's/^/    /'
$GIT merge --abort 2>/dev/null
echo "git merge-tree :"; $GIT merge-tree --write-tree main feature 2>&1 | sed 's/^/    /'; echo "    exit=$?"

echo
echo "--- STATE 3: driver set but executable missing on PATH ---"
mk s3; $GIT config merge.probe.driver "mergiraf-not-installed merge %O %A %B -o %A"
echo "git merge      :"; $GIT merge feature 2>&1 | sed 's/^/    /'
echo "    resulting file:"; sed 's/^/      /' f.txt
$GIT merge --abort 2>/dev/null
echo "git merge-tree :"; $GIT merge-tree --write-tree main feature 2>&1 | sed 's/^/    /'; echo "    exit=$?"

echo
echo "=== BUILT-IN 'union' DRIVER: the only merge driver that IS repo-portable ==="
mk u; sed -i 's/merge=probe/merge=union/' .gitattributes 2>/dev/null
$GIT checkout -q main
printf 'f.txt merge=union\n' > .gitattributes; $GIT commit -qam attr
$GIT checkout -q feature; printf 'f.txt merge=union\n' > .gitattributes; $GIT commit -qam attr2
$GIT checkout -q main
$GIT merge feature 2>&1 | sed 's/^/    /'
echo "    result:"; sed 's/^/      /' f.txt
echo "    (union = concatenate both sides, NO markers, ALWAYS 'clean'. Ships in .gitattributes; needs zero local config.)"

echo
echo "=== '-merge' / 'binary' attribute: refuse to merge at all ==="
mk nm; $GIT checkout -q main; printf 'f.txt -merge\n' > .gitattributes; $GIT commit -qam a
$GIT checkout -q feature; printf 'f.txt -merge\n' > .gitattributes; $GIT commit -qam a2
$GIT checkout -q main; $GIT merge feature 2>&1 | sed 's/^/    /'
echo "    result (ours kept verbatim, no markers, marked conflicted):"; sed 's/^/      /' f.txt
$GIT status --short | sed 's/^/      /'
