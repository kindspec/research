#!/bin/bash
export GIT_DIR="$2"
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
id=$1; n=$3; base=$4
ok=0; retries=0; gaveup=0
for i in $(seq 1 $n); do
  attempt=0
  while :; do
    attempt=$((attempt+1))
    old=$(git rev-parse --verify -q main) || { echo "NOREF"; exit 1; }
    blob=$(printf 'w%s i%s a%s\n' "$id" "$i" "$attempt" | git hash-object -w --stdin)
    idx="$base/.idx.$id"; rm -f "$idx"
    GIT_INDEX_FILE="$idx" git read-tree "$old^{tree}" || exit 1
    GIT_INDEX_FILE="$idx" git update-index --add --cacheinfo 100644,"$blob","file-$id.txt" || exit 1
    tree=$(GIT_INDEX_FILE="$idx" git write-tree) || exit 1
    new=$(git commit-tree "$tree" -p "$old" -m "w$id i$i") || exit 1
    if git update-ref refs/heads/main "$new" "$old" 2>/dev/null; then ok=$((ok+1)); break; fi
    retries=$((retries+1))
    if [ $attempt -gt 500 ]; then gaveup=$((gaveup+1)); break; fi
  done
done
echo "writer=$id committed=$ok cas_retries=$retries gaveup=$gaveup"
