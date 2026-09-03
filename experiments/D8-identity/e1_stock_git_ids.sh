#!/usr/bin/env bash
# D8-E1: How do embedded sub-file block IDs behave under STOCK git line merge?
# No merge driver, no .gitattributes, no tooling. Just git.
set -u
ROOT=$(mktemp -d)
run_case () {  # $1=name  $2=base  $3=ours  $4=theirs
  local d="$ROOT/$1"; mkdir -p "$d"; cd "$d"
  git init -q .; git config user.email a@b.c; git config user.name t
  printf '%s' "$2" > doc.md; git add -A; git commit -qm base
  git checkout -q -b alice; printf '%s' "$3" > doc.md; git commit -qam alice
  git checkout -q master 2>/dev/null || git checkout -q main
  git checkout -q -b bob; printf '%s' "$4" > doc.md; git commit -qam bob
  git checkout -q alice
  echo "=============================================================="
  echo "CASE $1"
  echo "--------------------------------------------------------------"
  git merge bob >/tmp/mo 2>&1; local rc=$?
  echo "merge exit=$rc"
  echo "conflict markers: $(grep -c '^<<<<<<<\|^>>>>>>>' doc.md)"
  echo "--- resulting doc.md ---"
  cat doc.md
  echo "--- end ---"
}

P="The reactor scram threshold is 4.2 sigma above baseline."

# A1: both sides mint a DIFFERENT id for the SAME paragraph (on-demand minting race)
run_case A1-concurrent-mint \
"# Safety

$P

Next paragraph unchanged.
" \
"# Safety

$P ^a3f91c2b

Next paragraph unchanged.
" \
"# Safety

$P ^7e40dd18

Next paragraph unchanged.
"

# A2: one side ADDS an id, other side EDITS the paragraph text
run_case A2-id-vs-edit \
"# Safety

$P

Next paragraph unchanged.
" \
"# Safety

$P ^a3f91c2b

Next paragraph unchanged.
" \
"# Safety

The reactor scram threshold is 3.8 sigma above baseline.

Next paragraph unchanged.
"

# A3: Logseq-style id:: on its OWN line, one side adds id, other edits text
run_case A3-ownline-id-vs-edit \
"- $P

- Next paragraph unchanged.
" \
"- $P
  id:: 6621e4a1-9c33-4f0e-b1d2-77a51e0cf9ab

- Next paragraph unchanged.
" \
"- The reactor scram threshold is 3.8 sigma above baseline.

- Next paragraph unchanged.
"

# A4: id-carrying block DUPLICATED by copy-paste on one side (namespace collision)
run_case A4-copypaste-dup \
"# Safety

$P ^a3f91c2b

## Appendix
" \
"# Safety

$P ^a3f91c2b

## Appendix

$P ^a3f91c2b
" \
"# Safety

$P ^a3f91c2b

## Appendix

Nothing to see here.
"

# A5: two sides each add a DIFFERENT NEW block, each with its own minted id,
#     at the same insertion point
run_case A5-concurrent-insert \
"# Log

- entry one ^b1
- entry two ^b2
" \
"# Log

- entry one ^b1
- ALICE entry ^a9x2
- entry two ^b2
" \
"# Log

- entry one ^b1
- BOB entry ^k7m4
- entry two ^b2
"

echo
echo "workdir: $ROOT"
