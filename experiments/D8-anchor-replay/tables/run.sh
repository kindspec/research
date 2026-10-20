#!/bin/bash
# One arm of the table replay at gap 5: this directory's replay.py with the
# oracle over paragraphs and tables and comments on tables only.
#
# Usage: run.sh LABEL BLOCKSPEC ARM CLONEKEY CLONEPATH OUTDIR
#   LABEL      r0004 or r0003, the name analyze.py reads the dump by
#   BLOCKSPEC  a blockspec checkout (ae1d274 for r0004, 31e41d3 for r0003)
#   ARM        an arm name of ../../D8-block-definitions/arms.json or
#              ../heldout-arms.json
#   CLONEKEY   that arm's clone key; CLONEPATH the clone, at its pin
#   OUTDIR     where LABEL-ARM.txt (stdout), .jsonl (--dump) and .err go
set -uo pipefail
here=$(dirname "$(readlink -f "$0")")
label=${1:?LABEL} blockspec=${2:?BLOCKSPEC} arm=${3:?ARM} key=${4:?CLONEKEY}
clone=${5:?CLONEPATH} out=${6:?OUTDIR}
export REPLAY_TYPES=p,table REPLAY_COMMENT_TYPES=table
python3 -I "$here/replay.py" --blockspec "$blockspec" --clone "$key=$clone" \
  --arm "$arm" --gap 5 --dump "$out/$label-$arm.jsonl" \
  > "$out/$label-$arm.txt" 2> "$out/$label-$arm.err"
status=$?
echo "$label-$arm exit $status"
exit $status
