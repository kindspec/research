#!/usr/bin/env bash
set -u
ROOT=$(mktemp -d); d="$ROOT/dup"; mkdir -p "$d"; cd "$d"
git init -q .; git config user.email a@b.c; git config user.name t
P="The reactor scram threshold is 4.2 sigma above baseline."
FILL=""; for i in $(seq 1 12); do FILL="$FILL
Filler section $i with enough text to keep hunks apart from one another.
"; done
{ echo "# Safety"; echo; echo "$P ^a3f91c2b"; echo "$FILL"; echo "END OF DOCUMENT"; } > doc.md
git add -A; git commit -qm base
git checkout -q -b alice
# Alice copy-pastes the id-bearing paragraph into an appendix (normal user act)
{ cat doc.md; echo; echo "## Appendix"; echo; echo "$P ^a3f91c2b"; } > t && mv t doc.md
git commit -qam alice
git checkout -q master; git checkout -q -b bob
sed -i '1s/# Safety/# Safety Requirements/' doc.md   # Bob retitles, far from the paste
git commit -qam bob
git checkout -q alice; git merge bob >/dev/null 2>&1; rc=$?
echo "merge exit=$rc"
echo "conflict markers: $(grep -c '^<<<<<<<' doc.md)"
echo "occurrences of ^a3f91c2b: $(grep -c '\^a3f91c2b' doc.md)"
echo "--- which block does a reference [[doc#^a3f91c2b]] resolve to? ---"
grep -n '\^a3f91c2b' doc.md
