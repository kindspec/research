#!/bin/bash
# Concurrent writer against a BARE repo: private index, commit-tree, update-ref CAS.
R=$1; ID=$2; N=$3; ok=0; fail=0
export GIT_DIR=$R
for i in $(seq 1 $N); do
  for attempt in $(seq 1 200); do
    OLD=$(git rev-parse refs/heads/main)
    export GIT_INDEX_FILE=$(mktemp /tmp/idx.XXXXXX)
    git read-tree $OLD
    # re-read current content and APPEND (re-apply intent, not a diff)
    git cat-file -p $OLD:log.txt > /tmp/c.$ID 2>/dev/null
    echo "writer$ID-$i" >> /tmp/c.$ID
    BLOB=$(git hash-object -w /tmp/c.$ID)
    git update-index --add --cacheinfo 100644,$BLOB,log.txt
    TREE=$(git write-tree)
    NEW=$(git commit-tree $TREE -p $OLD -m "w$ID-$i" 2>/dev/null)
    if git update-ref refs/heads/main $NEW $OLD 2>/dev/null; then ok=$((ok+1)); rm -f $GIT_INDEX_FILE; break
    else rm -f $GIT_INDEX_FILE; fi
  done
done
echo "$ID ok=$ok"
