#!/bin/bash
set -u
EXP="$(cd "$(dirname "$0")" && pwd)"
WORK="$EXP/work2"; rm -rf "$WORK"; mkdir -p "$WORK"
export PROBE_LOG="$WORK/log"; : > "$PROBE_LOG"
GIT="git -c user.name=T -c user.email=t@e -c init.defaultBranch=main -c advice.detachedHead=false"
b(){ echo; echo "=== $* ==="; }

########################################################################
b "A. SILENT DOWNGRADE: colleague without driver gets a CLEAN but WRONG merge"
# Non-overlapping edits to a CSV with A1 formulas: git text-merges cleanly.
D="$WORK/silent"; mkdir -p "$D"; cd "$D"; $GIT init -q .
cat > sheet.csv <<'EOF'
item,qty,price,total
a,1,10,=B2*C2
b,2,10,=B3*C3
c,3,10,=B4*C4
SUM,,,=SUM(E2:E4)
EOF
printf 'sheet.csv merge=tablemerge\n' > .gitattributes
$GIT add -A; $GIT commit -qm base
$GIT checkout -qb f1
sed -i '2a x,5,10,=B3*C3' sheet.csv; sed -i 's/=SUM(E2:E4)/=SUM(E2:E5)/' sheet.csv
$GIT commit -qam "f1 inserts row after a"
$GIT checkout -q main
sed -i '4a y,7,10,=B5*C5' sheet.csv; sed -i 's/=SUM(E2:E4)/=SUM(E2:E5)/' sheet.csv
$GIT commit -qam "main inserts row after c"
echo "-- ours:"; cat sheet.csv
echo "-- merging (NO driver configured, .gitattributes says merge=tablemerge):"
$GIT merge f1; echo "merge exit=$?"
echo "-- RESULT:"; cat -A sheet.csv | sed 's/\$$//'
echo "-- git status:"; $GIT status --short

########################################################################
b "B. rebase backends: --merge (default) vs --apply"
mk(){ D="$1"; rm -rf "$D"; mkdir -p "$D"; cd "$D"; $GIT init -q .
  printf 'a\nCONTESTED\nz\n' > f.txt; printf 'f.txt merge=probe\n' > .gitattributes
  $GIT add -A; $GIT commit -qm base
  $GIT checkout -qb feature; printf 'a\nTHEIRS\nz\n' > f.txt; $GIT commit -qam t
  $GIT checkout -q main; printf 'a\nOURS\nz\n' > f.txt; $GIT commit -qam o
  $GIT config merge.probe.name p; $GIT config merge.probe.driver "$EXP/driver.sh %O %A %B %L %P"; }
n(){ wc -l < "$PROBE_LOG"; }
for mode in "--merge" "--apply"; do
  mk "$WORK/rb$RANDOM"; M=$(n)
  $GIT rebase $mode feature >/dev/null 2>&1; E=$?
  A=$(n); if [ "$A" -gt "$M" ]; then R="DRIVER RAN"; else R="driver NOT run"; fi
  echo "rebase $mode -> exit=$E  $R  head-of-file: $(head -1 f.txt)"
  $GIT rebase --abort 2>/dev/null
done

########################################################################
b "C. merge-tree honours .gitattributes but needs the driver in the SERVER's config"
D="$WORK/mt"; mk "$D"
echo "-- with driver in config:"; M=$(n); $GIT merge-tree --write-tree main feature >/dev/null; [ $(n) -gt $M ] && echo "   DRIVER RAN" || echo "   not run"
$GIT config --unset merge.probe.driver
echo "-- driver UNSET (simulates a forge server that has .gitattributes but not the tool):"
M=$(n); OUT=$($GIT merge-tree --write-tree main feature 2>&1); E=$?
[ $(n) -gt $M ] && echo "   DRIVER RAN" || echo "   driver NOT run"
echo "   exit=$E"; echo "$OUT" | head -5
echo "   -> conflicted content merge-tree would produce:"
$GIT merge-tree main feature 2>/dev/null | head -20

########################################################################
b "D. CONFIG SCOPE: exactly which parts are repo-portable?"
D="$WORK/scope"; mk "$D"
echo "-- .gitattributes is a TRACKED FILE:"; $GIT ls-files .gitattributes
echo "-- merge.probe.driver lives in:"
for s in local global system worktree; do
  v=$($GIT config --$s --get merge.probe.driver 2>/dev/null); echo "   --$s : ${v:-<unset>}"
done
echo "-- is .git/config ever transferred by clone/fetch/push? check the clone:"
cd "$WORK"; $GIT clone -q "$D" scope_clone 2>/dev/null; cd "$WORK/scope_clone"
echo "   clone's merge.probe.driver: '$($GIT config --get merge.probe.driver || echo '<UNSET>')'"
echo "   clone's .gitattributes: $(cat .gitattributes)"

########################################################################
b "E. Does .gitattributes in .git/info/attributes vs tracked differ? (both work, but only tracked ships)"
echo "   (documented: gitattributes(5) precedence = .git/info/attributes > .gitattributes in-tree > parent dirs > core.attributesFile)"

########################################################################
b "F. CLEAN/SMUDGE FILTER COVERAGE"
D="$WORK/filt"; rm -rf "$D"; mkdir -p "$D"; cd "$D"; $GIT init -q .
FL="$WORK/filter.log"; : > "$FL"
cat > "$WORK/cleanf.sh" <<EOF
#!/bin/bash
echo "CLEAN \$1" >> "$FL"; sed 's/^SMUDGED://' 
EOF
cat > "$WORK/smudgef.sh" <<EOF
#!/bin/bash
echo "SMUDGE \$1" >> "$FL"; sed 's/^/SMUDGED:/'
EOF
chmod +x "$WORK/cleanf.sh" "$WORK/smudgef.sh"
$GIT config filter.pf.clean "$WORK/cleanf.sh %f"
$GIT config filter.pf.smudge "$WORK/smudgef.sh %f"
printf '*.dat filter=pf\n' > .gitattributes
printf 'hello\nworld\n' > a.dat
$GIT add -A; $GIT commit -qm base
probe(){ M=$(wc -l < "$FL"); shift 0; }
run(){ local label="$1"; shift; local M=$(wc -l < "$FL"); "$@" >/dev/null 2>&1; local A=$(wc -l < "$FL")
  local d=$(tail -n +$((M+1)) "$FL" | awk '{print $1}' | sort -u | tr '\n' ',' )
  printf '  %-34s -> %s\n' "$label" "${d:-none}"; }
echo "-- which operations invoke clean/smudge:"
run "checkout (rm + restore)" bash -c "rm a.dat; $GIT checkout -- a.dat"
run "git add (clean)" bash -c "touch a.dat; $GIT add a.dat"
run "git diff (worktree vs HEAD)" bash -c "printf 'hello\nWORLD\n' > a.dat; $GIT diff"
run "git log -p" $GIT log -p
run "git show HEAD" $GIT show HEAD
run "git archive HEAD" $GIT archive HEAD
run "git cat-file -p HEAD:a.dat" $GIT cat-file -p HEAD:a.dat
run "git grep hello" $GIT grep hello
run "git stash push/pop" bash -c "$GIT stash; $GIT stash pop"
echo "-- stored blob (should be UNsmudged):"; $GIT cat-file -p HEAD:a.dat
echo "-- worktree file (should be SMUDGED):"; rm a.dat; $GIT checkout -- a.dat; cat a.dat
echo "-- git archive contents:"; $GIT archive HEAD | tar -xO a.dat
echo "-- full filter log:"; cat "$FL"
