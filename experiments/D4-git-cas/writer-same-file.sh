#!/bin/bash
export GIT_DIR="$2"; export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
id=$1; n=$3; base=$4; ok=0; retries=0
for i in $(seq 1 $n); do
  attempt=0
  while :; do
    attempt=$((attempt+1))
    old=$(git rev-parse --verify -q main)
    # RE-READ current content at CAS-time and re-apply our intent (append one line)
    cur=$(git cat-file -p "$old:shared.md")
    blob=$(printf '%s\nline from w%s #%s\n' "$cur" "$id" "$i" | git hash-object -w --stdin)
    idx="$base/.idx2.$id"; rm -f "$idx"
    GIT_INDEX_FILE="$idx" git read-tree "$old^{tree}"
    GIT_INDEX_FILE="$idx" git update-index --add --cacheinfo 100644,"$blob",shared.md
    tree=$(GIT_INDEX_FILE="$idx" git write-tree)
    new=$(git commit-tree "$tree" -p "$old" -m "w$id i$i")
    if git update-ref refs/heads/main "$new" "$old" 2>/dev/null; then ok=$((ok+1)); break; fi
    retries=$((retries+1))
    [ $attempt -gt 500 ] && break
  done
done
echo "writer=$id committed=$ok cas_retries=$retries"
