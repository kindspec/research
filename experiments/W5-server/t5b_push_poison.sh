#!/bin/bash
# W5-T5b: can a malformed tree actually be PUSHED to a bare server repo?
# If yes, one crafted push permanently aborts every merge on that repo:
# `git merge-tree` dies on a C assertion (SIGABRT), it does not return an error.
set -u
export GIT_CONFIG_NOSYSTEM=1 GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t \
       GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t GIT_CONFIG_GLOBAL=/dev/null
H=$(cd "$(dirname "$0")" && pwd); W=$H/work-t5b; rm -rf "$W"; mkdir -p "$W"; cd "$W"

echo "### building a client repo containing a malformed tree object"
git init -q client; cd client
printf '| id |\n| -- |\n| a |\n' > b.tbl
git add -A; git commit -qm main >/dev/null; git branch -M main
MAINC=$(git rev-parse HEAD)
B=$(printf '| id |\n| -- |\n| a |\n' | git hash-object -w --stdin)
# a tree entry whose NAME contains a slash: structurally invalid, writable anyway
RAW=$(python3 -c "
import sys,binascii
oid='$B'
sys.stdout.buffer.write(b'100644 ../../../etc/evil.tbl\x00'+binascii.unhexlify(oid))
" | git hash-object -w -t tree --literally --stdin)
echo "  malformed tree = $RAW"
C=$(git commit-tree "$RAW" -p "$MAINC" -m poison)   # SHARES history with main
git update-ref refs/heads/poison "$C"
echo "  commit         = $C"
echo -n "  git fsck says  : "; git fsck --strict 2>&1 | head -2

for FSCK in false true; do
  echo
  echo "=================================================================="
  echo "### push to a bare repo with receive.fsckObjects=$FSCK"
  echo "=================================================================="
  cd "$W"; rm -rf srv.git; git init -q --bare srv.git
  git -C srv.git config receive.fsckObjects $FSCK
  echo "  (git's DEFAULT for receive.fsckObjects is 'false')"
  cd client
  git push -q ../srv.git poison >"$W/push.log" 2>&1; PRC=$?
  sed 's/^/    /' "$W/push.log"
  [ $PRC -eq 0 ] && echo "  PUSH ACCEPTED (exit 0)" || echo "  PUSH REJECTED (exit $PRC)"
  cd "$W"
  echo -n "  poison ref on server: "; git -C srv.git rev-parse --verify -q refs/heads/poison || echo "(absent)"
done

echo
echo "=================================================================="
echo "### effect on the server, with the poison accepted (default config)"
echo "=================================================================="
cd "$W"; rm -rf srv.git; git init -q --bare srv.git
cd client; git push -q ../srv.git main poison 2>/dev/null; cd "$W"
echo "--- direct git merge-tree against the poison ref ---"
git -C srv.git merge-tree --write-tree main poison >/dev/null 2>"$W/mt.err"; MRC=$?
sed 's/^/    /' "$W/mt.err"; echo "  exit=$MRC   (134 = SIGABRT / assertion failure)"
echo
echo "--- the gws server on the same input ---"
python3 "$H/gws_merge_server.py" merge --repo srv.git --into refs/heads/main --from refs/heads/poison >"$W/srv.log" 2>&1; SRC=$?
sed 's/^/  /' "$W/srv.log"; echo "  exit=$SRC"
echo "--- did the ref move? ---"
echo "  main = $(git -C srv.git rev-parse --short main)"
echo
echo ">> The server SURVIVES (subprocess isolation: SIGABRT in the child is just"
echo ">> a non-zero exit) and refuses. But merges against that ref are"
echo ">> permanently broken, and git's DEFAULT config accepts the poison."
echo ">> OPERATIONAL REQUIREMENT: receive.fsckObjects=true on the server repo."
