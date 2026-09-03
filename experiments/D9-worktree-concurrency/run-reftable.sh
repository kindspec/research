#!/bin/bash
# D9-5b: does the reftable backend (git 2.45+) enable CONCURRENT ref writers,
# or only cheaper ref updates? Gerrit drove reftable for lock contention.
set -u
export GIT_CONFIG_NOSYSTEM=1
export HOME=$PWD/fakehome
W=$PWD/work-rt; rm -rf "$W"; mkdir -p "$W"; cd "$W"
N=16
hr(){ echo; echo "=========================================================="; echo "### $*"; echo "=========================================================="; }
echo "git version: $(git --version)"

for FMT in files reftable; do
hr "REF FORMAT = $FMT"
rm -rf r_$FMT; git init -q --ref-format=$FMT r_$FMT 2>&1 | head -2
cd r_$FMT || { echo "  UNSUPPORTED"; cd "$W"; continue; }
echo "  actual format: $(git rev-parse --show-ref-format 2>/dev/null || echo n/a)"
echo seed > s; git add -A; git commit -qm seed
echo "  on-disk refs storage: $(ls .git/reftable 2>/dev/null | head -3 | tr '\n' ' ')$(ls .git/refs/heads 2>/dev/null | tr '\n' ' ')"

# (a) 16 concurrent CAS writers on the SAME ref
rm -f "$W"/rt_ok_*; 
for i in $(seq 1 $N); do
 ( C=$(git commit-tree $(git rev-parse HEAD^{tree}) -p HEAD -m "c$i" 2>/dev/null); \
   git update-ref refs/heads/main "$C" "$(git rev-parse refs/heads/main)" 2>>"$W/rt_err_${FMT}_$i" && echo OK > "$W/rt_ok_$i" ) &
done; wait
echo "  (a) concurrent CAS on ONE ref: $(ls "$W"/rt_ok_* 2>/dev/null | wc -l)/$N succeeded"

# (b) 16 concurrent writers to 16 DIFFERENT refs
rm -f "$W"/rt2_ok_*
for i in $(seq 1 $N); do
 ( git update-ref refs/gws/s$i HEAD 2>>"$W/rt2_err_${FMT}_$i" && echo OK > "$W/rt2_ok_$i" ) &
done; wait
echo "  (b) concurrent writes to 16 DISTINCT refs: $(ls "$W"/rt2_ok_* 2>/dev/null | wc -l)/$N succeeded"
cat "$W"/rt2_err_${FMT}_* 2>/dev/null | sort | uniq -c | head -3 | sed 's/^/      /'

# (c) cost of creating 20000 refs
S=$(date +%s%N)
for i in $(seq 1 200); do
  { for j in $(seq 1 100); do echo "create refs/gws/bulk/$i-$j $(git rev-parse HEAD)"; done; } | git update-ref --stdin
done
E=$(date +%s%N)
echo "  (c) 20000 refs created (batched 100/txn): $(( (E-S)/1000000 )) ms"
echo "      ref count: $(git for-each-ref --format='%(refname)' | wc -l)"
echo "      refs storage size: $(du -sh .git/reftable 2>/dev/null | cut -f1)$(du -sh .git/refs .git/packed-refs 2>/dev/null | cut -f1 | tr '\n' '+')"
S=$(date +%s%N); git for-each-ref >/dev/null; E=$(date +%s%N); echo "      for-each-ref (20k): $(( (E-S)/1000000 )) ms"
S=$(date +%s%N); git update-ref refs/gws/onemore HEAD; E=$(date +%s%N); echo "      ONE more ref update at 20k refs: $(( (E-S)/1000000 )) ms"
cd "$W"
done
