#!/bin/bash
# The positive control for scan.py: blockspec's conformance case
# anchor/near-copy/a-table-s-separators-are-words, rebuilt as a git history
# with the case's base and current versions of policy.md GAP=5 versions
# apart, so scan.py's sampling pairs them.
#
# Usage: control.sh BLOCKSPEC DIR
#   BLOCKSPEC  a blockspec checkout at ae1d274
#   DIR        a new directory to build the history in; it must not exist
set -euo pipefail
case=${1:?BLOCKSPEC}/conformance/cases/anchor/near-copy/a-table-s-separators-are-words
dir=${2:?DIR}
[ -e "$dir" ] && { echo "$dir exists" >&2; exit 64; }
mkdir -p "$dir"
export GIT_AUTHOR_NAME=control GIT_AUTHOR_EMAIL=control@example.invalid
export GIT_COMMITTER_NAME=control GIT_COMMITTER_EMAIL=control@example.invalid
export GIT_AUTHOR_DATE='2026-01-01T00:00:00Z' GIT_COMMITTER_DATE='2026-01-01T00:00:00Z'
git -C "$dir" init -q
git -C "$dir" config commit.gpgsign false
cp "$case/blobs/policy.md" "$dir/policy.md"
git -C "$dir" add policy.md
git -C "$dir" commit -qm base
cp "$case/tree/policy.md" "$dir/policy.md"
git -C "$dir" commit -qam current
# four more versions after `current`, each adding a line at the end, so the
# file has six versions and one pair five apart: base..e4
for i in 1 2 3 4; do
  printf 'x%s\n' "$i" >> "$dir/policy.md"
  git -C "$dir" commit -qam "e$i"
done
git -C "$dir" log --oneline -- policy.md | wc -l
