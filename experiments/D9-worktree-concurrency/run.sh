#!/bin/bash
# D9-5: do PER-USER WORKTREES over ONE object store allow concurrent commits?
set -u
export GIT_CONFIG_NOSYSTEM=1
export HOME=$PWD/fakehome; rm -rf fakehome; mkdir -p fakehome
printf '[user]\n\tname=t\n\temail=t@t\n[init]\n\tdefaultBranch=main\n[gc]\n\tauto=0\n' > fakehome/.gitconfig
W=$PWD/work; rm -rf "$W"; mkdir -p "$W"; cd "$W"
hr(){ echo; echo "=========================================================="; echo "### $*"; echo "=========================================================="; }
N=${N:-16}

hr "SETUP: 1 repo, $N linked worktrees (git worktree add), each on its own branch"
git init -q main; cd main; echo seed > seed.txt; git add -A; git commit -qm seed
for i in $(seq 1 $N); do git worktree add -q -b wt$i ../wt$i >/dev/null 2>&1; done
echo "worktrees: $(git worktree list | wc -l)"
echo "index files: $(find .git -name index | sed 's|^|  |')"
echo ">> NOTE: each linked worktree gets its OWN index at .git/worktrees/<name>/index"
cd "$W"

hr "TEST 1: $N concurrent commits, each in its own worktree, own branch, own file"
for i in $(seq 1 $N); do
 ( cd wt$i && echo "content $i $RANDOM" > f$i.txt && \
   git add f$i.txt >/dev/null 2>>"$W/err1_$i" && \
   git commit -qm "c$i" >/dev/null 2>>"$W/err1_$i" && echo OK > "$W/res1_$i" ) &
done
wait
echo "succeeded: $(ls "$W"/res1_* 2>/dev/null | wc -l) / $N"
echo "errors:"; cat "$W"/err1_* 2>/dev/null | sort | uniq -c | sed 's/^/  /'
[ -s "$W/err1_1" ] || echo "  (none)"

hr "TEST 2: $N concurrent commits ALL TARGETING THE SAME BRANCH ref"
cd "$W"; rm -rf main2 && git init -q main2 && cd main2
echo seed > seed.txt; git add -A; git commit -qm seed
# detached worktrees all trying to update refs/heads/main via update-ref
for i in $(seq 1 $N); do git worktree add -q --detach ../w2_$i >/dev/null 2>&1; done
cd "$W"
rm -f res2_* err2_*
for i in $(seq 1 $N); do
 ( cd w2_$i && echo "x $i" > g$i.txt && git add g$i.txt 2>>"$W/err2_$i" && \
   C=$(git commit-tree $(git write-tree) -p refs/heads/main -m "c$i" 2>>"$W/err2_$i") && \
   git update-ref refs/heads/main "$C" "$(git rev-parse refs/heads/main)" 2>>"$W/err2_$i" && echo OK > "$W/res2_$i" ) &
done
wait
echo "succeeded (CAS on refs/heads/main): $(ls "$W"/res2_* 2>/dev/null | wc -l) / $N"
echo "errors:"; cat "$W"/err2_* 2>/dev/null | sed 's/^/  /' | sort | uniq -c | head -6
echo ">> the ref is the serialization point: compare-and-swap means at most one winner per round"

hr "TEST 3: $N concurrent writers all sharing ONE worktree/index (the naive server)"
cd "$W"; rm -rf single && git init -q single && cd single
echo seed>s.txt; git add -A; git commit -qm seed
rm -f "$W"/res3_* "$W"/err3_*
for i in $(seq 1 $N); do
 ( echo "y $i" > h$i.txt; git add h$i.txt 2>>"$W/err3_$i" && echo OK > "$W/res3_$i" ) &
done
wait
echo "git add succeeded: $(ls "$W"/res3_* 2>/dev/null | wc -l) / $N"
cat "$W"/err3_* 2>/dev/null | grep -o 'index.lock\|Unable to create\|File exists' | sort | uniq -c | sed 's/^/  /'

hr "TEST 4: concurrent OBJECT WRITES only (hash-object) — is the object store safe?"
cd "$W"; rm -rf objs && git init -q objs && cd objs
rm -f "$W"/res4_*
S=$(date +%s%N)
for i in $(seq 1 64); do
 ( for j in $(seq 1 20); do printf 'blob %d-%d\n' $i $j | git hash-object -w --stdin >/dev/null 2>>"$W/err4_$i"; done; echo OK > "$W/res4_$i" ) &
done
wait
E=$(date +%s%N)
echo "workers OK: $(ls "$W"/res4_* 2>/dev/null | wc -l)/64, 1280 objects in $(( (E-S)/1000000 )) ms"
echo "objects on disk: $(find .git/objects -type f -not -path '*pack*' -not -path '*info*' | wc -l)"
echo "errors: $(cat "$W"/err4_* 2>/dev/null | wc -l)"
echo "fsck:"; git fsck --no-progress 2>&1 | head -3
echo ">> the OBJECT store is concurrency-safe (content-addressed, write-to-temp+rename)."
echo ">> the INDEX and the REFS are not."

hr "TEST 5: worktree add/remove under concurrency (server provisioning N sessions)"
cd "$W"; rm -rf prov && git init -q prov && cd prov
echo s>s; git add -A; git commit -qm s
rm -f "$W"/res5_* "$W"/err5_*
for i in $(seq 1 $N); do
 ( git worktree add -q --detach "$W/p_$i" >/dev/null 2>>"$W/err5_$i" && echo OK > "$W/res5_$i" ) &
done
wait
echo "concurrent 'git worktree add': $(ls "$W"/res5_* 2>/dev/null|wc -l) / $N"
cat "$W"/err5_* 2>/dev/null | sed 's/^/  /' | sort | uniq -c | head -5
echo "disk cost of $N worktrees of a trivial repo: $(du -sh "$W" 2>/dev/null | cut -f1)"
