#!/usr/bin/env bash
# D8-E2: CONTROLLED arms. Does writing a block id CAUSE conflicts that would
# not otherwise exist, and does it CLEAN-MERGE things that should conflict?
set -u
ROOT=$(mktemp -d)
run () {  # $1=name $2=base $3=ours $4=theirs
  local d="$ROOT/$1"; mkdir -p "$d"; cd "$d"
  git init -q .; git config user.email a@b.c; git config user.name t
  printf '%s' "$2" > doc.md; git add -A; git commit -qm base
  git checkout -q -b alice; printf '%s' "$3" > doc.md; git commit -qam alice
  git checkout -q master; git checkout -q -b bob; printf '%s' "$4" > doc.md; git commit -qam bob
  git checkout -q alice; git merge bob >/dev/null 2>&1; local rc=$?
  local mk=$(grep -c '^<<<<<<<' doc.md)
  local dup=$(grep -o '\^a3f91c2b' doc.md | wc -l)
  printf '%-34s exit=%d markers=%d occurrences_of_^a3f91c2b=%d\n' "$1" "$rc" "$mk" "$dup"
  if [ "${SHOW:-0}" = 1 ]; then echo "--- doc.md ---"; cat doc.md; echo "---"; fi
}

P="The reactor scram threshold is 4.2 sigma above baseline."
P2="The reactor scram threshold is 3.8 sigma above baseline."
FILL=$'\nSection two.\n\nSection three.\n\nSection four.\n\nSection five.\n\nSection six.\n\nSection seven.\n\nSection eight.\n'

echo "=== ARM 1: Bob rewords a paragraph; Alice does/doesn't add an id to it ==="
run "1a-CONTROL-no-id-write" \
"# Safety

$P
$FILL" \
"# Safety

$P
$FILL
Alice adds a new closing paragraph.
" \
"# Safety

$P2
$FILL"

run "1b-alice-writes-blockid" \
"# Safety

$P
$FILL" \
"# Safety

$P ^a3f91c2b
$FILL
Alice adds a new closing paragraph.
" \
"# Safety

$P2
$FILL"

echo
echo "=== ARM 2: copy-paste duplication of an id-bearing block, far apart ==="
run "2a-dup-block-clean-merge" \
"# Safety

$P ^a3f91c2b
$FILL" \
"# Safety

$P ^a3f91c2b
$FILL
Quoting the rule again for the appendix:

$P ^a3f91c2b
" \
"# Safety

$P ^a3f91c2b
$FILL
Bob adds an unrelated note at the end.
"

echo
echo "=== ARM 3: same-id minted for DIFFERENT blocks in two branches (birthday) ==="
run "3a-id-collision-different-blocks" \
"# Log
$FILL" \
"# Log

Alice's brand new claim. ^a3f91c2b
$FILL" \
"# Log
$FILL
Bob's totally different claim. ^a3f91c2b
"

echo; echo "workdir: $ROOT"
