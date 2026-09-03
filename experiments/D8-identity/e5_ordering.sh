#!/usr/bin/env bash
# D8-E5: is a FRACTIONAL INDEX necessary in a text serialization, given that
# document order IS line order and stock git already merges lines?
set -u
ROOT=$(mktemp -d)
t () { # $1 label $2 base $3 ours $4 theirs
  local d="$ROOT/$RANDOM$RANDOM"; mkdir -p "$d"; cd "$d"
  git init -q .; git config user.email a@b.c; git config user.name x
  printf '%s' "$2" > f.md; git add -A; git commit -qm b
  git checkout -q -b a; printf '%s' "$3" > f.md; git commit -qam a
  git checkout -q master; git checkout -q -b o; printf '%s' "$4" > f.md; git commit -qam o
  git checkout -q a; git merge o >/dev/null 2>&1; local rc=$?
  printf '%-46s exit=%d markers=%d\n' "$1" "$rc" "$(grep -c '^<<<<<<<' f.md)"
  [ "${SHOW:-0}" = 1 ] && { sed 's/^/      /' f.md; }
  return 0
}

# ---------- Format A: pure LINE ORDER, no keys ----------
BA='- alpha
- bravo
- charlie
- delta
- echo
- foxtrot
'
echo "== Format A: line order (no keys) =="
t "A1 inserts at two DIFFERENT points" "$BA" \
'- alpha
- bravo
- ALICE
- charlie
- delta
- echo
- foxtrot
' \
'- alpha
- bravo
- charlie
- delta
- echo
- BOB
- foxtrot
'
t "A2 inserts at the SAME point" "$BA" \
'- alpha
- bravo
- ALICE
- charlie
- delta
- echo
- foxtrot
' \
'- alpha
- bravo
- BOB
- charlie
- delta
- echo
- foxtrot
'
t "A3 Alice MOVES 'echo' to top, Bob EDITS 'echo'" "$BA" \
'- echo
- alpha
- bravo
- charlie
- delta
- foxtrot
' \
'- alpha
- bravo
- charlie
- delta
- echo EDITED BY BOB
- foxtrot
'

# ---------- Format B: fractional index, lines kept SORTED by key ----------
BB='- a0 alpha
- a1 bravo
- a2 charlie
- a3 delta
- a4 echo
- a5 foxtrot
'
echo "== Format B: fractional key, file kept sorted by key =="
t "B1 inserts at two DIFFERENT points" "$BB" \
'- a0 alpha
- a1 bravo
- a1V ALICE
- a2 charlie
- a3 delta
- a4 echo
- a5 foxtrot
' \
'- a0 alpha
- a1 bravo
- a2 charlie
- a3 delta
- a4 echo
- a4V BOB
- a5 foxtrot
'
t "B2 inserts at the SAME point (interleaving test)" "$BB" \
'- a0 alpha
- a1 bravo
- a1V ALICE
- a2 charlie
- a3 delta
- a4 echo
- a5 foxtrot
' \
'- a0 alpha
- a1 bravo
- a1G BOB
- a2 charlie
- a3 delta
- a4 echo
- a5 foxtrot
'
t "B3 Alice MOVES 'echo' (key change only), Bob EDITS it" "$BB" \
'- Zz echo
- a0 alpha
- a1 bravo
- a2 charlie
- a3 delta
- a5 foxtrot
' \
'- a0 alpha
- a1 bravo
- a2 charlie
- a3 delta
- a4 echo EDITED BY BOB
- a5 foxtrot
'

# ---------- Format C: fractional index, file in CREATION order, sorted at render ----------
echo "== Format C: fractional key, file NOT sorted (render sorts) =="
t "C3 Alice MOVES 'echo' (key edit in place), Bob EDITS it" "$BB" \
'- a0 alpha
- a1 bravo
- a2 charlie
- a3 delta
- Zz echo
- a5 foxtrot
' \
'- a0 alpha
- a1 bravo
- a2 charlie
- a3 delta
- a4 echo EDITED BY BOB
- a5 foxtrot
'
echo
echo "-- C3 detail --"
SHOW=1 t "C3 (shown)" "$BB" \
'- a0 alpha
- a1 bravo
- a2 charlie
- a3 delta
- Zz echo
- a5 foxtrot
' \
'- a0 alpha
- a1 bravo
- a2 charlie
- a3 delta
- a4 echo EDITED BY BOB
- a5 foxtrot
'
