#!/usr/bin/env bash
# Cost of 21 revisions of one image under: plain git, git-lfs, content-defined chunking.
set -e
cd "$(dirname "$0")"
EXT=$1   # png | ppm
DIR=svg
SINGLE=$(stat -c%s $DIR/diagram-00.$EXT)
TOTAL=$(cat $DIR/*.$EXT | wc -c)

rm -rf out; mkdir -p out

# --- plain git ---
rm -rf out/plain; mkdir out/plain; cd out/plain; git init -q
git config user.email t@t; git config user.name t
for f in ../../$DIR/*.$EXT; do cp "$f" img.$EXT; git add img.$EXT; git commit -qm "$(basename $f)"; done
git gc -q --aggressive --prune=now 2>/dev/null
PLAIN=$(du -sb .git | cut -f1)
cd ../..

# --- git-lfs ---
rm -rf out/lfs; mkdir out/lfs; cd out/lfs; git init -q
git config user.email t@t; git config user.name t
git lfs install --local >/dev/null 2>&1
git lfs track "*.$EXT" >/dev/null 2>&1
git add .gitattributes; git commit -qm lfs
for f in ../../$DIR/*.$EXT; do cp "$f" img.$EXT; git add img.$EXT; git commit -qm "$(basename $f)"; done
git gc -q --prune=now 2>/dev/null
LFS=$(du -sb .git | cut -f1)
cd ../..

echo "format=$EXT  single=$SINGLE  naive_total(21x)=$TOTAL"
echo "  plain git .git        = $PLAIN  ($(python3 -c "print(round($PLAIN/$SINGLE,2))")x a single copy)"
echo "  git-lfs   .git        = $LFS  ($(python3 -c "print(round($LFS/$SINGLE,2))")x)"
python3 cdc.py "$DIR" "$EXT" "$SINGLE"
