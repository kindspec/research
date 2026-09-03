#!/bin/bash
# Custom merge driver probe.
# git invokes:  driver.sh %O %A %B %L %P
# %O = ancestor temp file, %A = ours temp file (MUST be overwritten with result),
# %B = theirs temp file, %L = conflict marker size, %P = pathname in worktree.
O="$1"; A="$2"; B="$3"; L="$4"; P="$5"
echo "DRIVER-RAN path=$P marker_size=$L caller_pid_cmd=$(ps -o args= -p $PPID 2>/dev/null | head -c 120)" >> "$PROBE_LOG"
# Produce an unmistakable, obviously-not-git result and exit 0 (= clean merge).
{
  echo "### MERGED BY CUSTOM DRIVER ###"
  echo "--- base ---";   cat "$O"
  echo "--- ours ---";   cat "$A"
  echo "--- theirs ---"; cat "$B"
} > "$A.out"
mv "$A.out" "$A"
exit 0
