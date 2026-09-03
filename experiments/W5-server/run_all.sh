#!/bin/bash
# W5-server: run every experiment, regenerating all transcripts.
H=$(cd "$(dirname "$0")" && pwd); cd "$H"
set -x
bash   t1_core_claim.sh        > TRANSCRIPT-t1-core-claim.txt      2>&1
{ echo "### BARE CAS RETRY LOOP";   python3 t2_concurrency.py 2 8 16 32 64 128 192 256 | head -14
  echo; echo "### QUEUED (flock per ref)"; W5_QUEUE=1 python3 t2_concurrency.py 2 8 16 32 64 128 192 256 | head -14
} > TRANSCRIPT-t2-concurrency.txt 2>&1
python3 t3_crash.py            > TRANSCRIPT-t3-crash.txt           2>&1
python3 t4_adversarial.py      > TRANSCRIPT-t4-adversarial.txt     2>&1
python3 t5_malicious.py        > TRANSCRIPT-t5-malicious.txt       2>&1
bash   t5b_push_poison.sh      > TRANSCRIPT-t5b-push-poison.txt    2>&1
python3 t6_normal_git.py       > TRANSCRIPT-t6-normal-git.txt      2>&1
bash   t7_local_vs_forge.sh    > TRANSCRIPT-t7-local-vs-forge.txt  2>&1
bash   t8_idempotent.sh        > TRANSCRIPT-t8-idempotent.txt      2>&1
set +x
echo "=== HEADLINES ==="
grep -h "core-claim verification exit\|NOT fetched by default" TRANSCRIPT-t1-core-claim.txt
grep -h "SILENTLY WRONG CASES" TRANSCRIPT-t4-adversarial.txt
grep -h "SECURITY FAILURES" TRANSCRIPT-t5-malicious.txt
grep -h "VERDICT: CRASH" TRANSCRIPT-t3-crash.txt
grep -h "IDENTICAL\|DIFFERENT BYTES" TRANSCRIPT-t7-local-vs-forge.txt
grep -h "must be 1" TRANSCRIPT-t8-idempotent.txt
bash t9_churn.sh > TRANSCRIPT-t9-churn.txt 2>&1
