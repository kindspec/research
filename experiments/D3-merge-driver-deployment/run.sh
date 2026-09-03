#!/bin/bash
# Empirically determine which git operations invoke a custom .gitattributes merge driver.
set -u
EXP="$(cd "$(dirname "$0")" && pwd)"
WORK="$EXP/work"
rm -rf "$WORK"; mkdir -p "$WORK"
export PROBE_LOG="$WORK/driver-invocations.log"
: > "$PROBE_LOG"

GIT="git -c user.name=T -c user.email=t@e -c init.defaultBranch=main -c advice.detachedHead=false"

mkrepo () {   # $1 = dir ; sets up base + two divergent OVERLAPPING edits
  local d="$1"
  rm -rf "$d"; mkdir -p "$d"; cd "$d"
  $GIT init -q .
  printf 'line1\nCONTESTED-BASE\nline3\n' > data.txt
  printf '* text=auto\ndata.txt merge=probe\n' > .gitattributes
  $GIT add -A; $GIT commit -qm base
  $GIT checkout -qb feature
  printf 'line1\nCONTESTED-THEIRS\nline3\n' > data.txt
  $GIT commit -qam theirs
  $GIT checkout -q main
  printf 'line1\nCONTESTED-OURS\nline3\n' > data.txt
  $GIT commit -qam ours
}

# Register the driver in LOCAL config only (this is the whole point of the test)
register () { cd "$1"; $GIT config merge.probe.name "probe driver"; $GIT config merge.probe.driver "$EXP/driver.sh %O %A %B %L %P"; }

banner () { echo; echo "==================================================================="; echo "### $*"; echo "==================================================================="; }

report () {   # $1 = label ; look at log delta + file content
  local n_after; n_after=$(wc -l < "$PROBE_LOG")
  if [ "$n_after" -gt "$MARK" ]; then echo "  >> DRIVER INVOKED ($((n_after-MARK))x)"; else echo "  >> driver NOT invoked"; fi
  MARK=$n_after
}
mark () { MARK=$(wc -l < "$PROBE_LOG"); }

########################################################################
banner "1. git merge"
mkrepo "$WORK/r_merge"; register "$WORK/r_merge"; mark
$GIT merge feature; echo "exit=$?"
report; echo "--- data.txt ---"; cat data.txt

########################################################################
banner "2. git rebase"
mkrepo "$WORK/r_rebase"; register "$WORK/r_rebase"; mark
$GIT rebase feature; echo "exit=$?"
report; echo "--- data.txt ---"; cat data.txt; $GIT rebase --abort 2>/dev/null

########################################################################
banner "3. git cherry-pick"
mkrepo "$WORK/r_cp"; register "$WORK/r_cp"; mark
$GIT cherry-pick feature; echo "exit=$?"
report; echo "--- data.txt ---"; cat data.txt; $GIT cherry-pick --abort 2>/dev/null

########################################################################
banner "4. git revert"
mkrepo "$WORK/r_rev"; register "$WORK/r_rev"; mark
# revert the base->ours commit while worktree has a further conflicting change
printf 'line1\nCONTESTED-LATER\nline3\n' > data.txt; $GIT commit -qam later
$GIT revert --no-edit HEAD~1; echo "exit=$?"
report; echo "--- data.txt ---"; cat data.txt; $GIT revert --abort 2>/dev/null

########################################################################
banner "5. git stash pop"
mkrepo "$WORK/r_stash"; register "$WORK/r_stash"; mark
printf 'line1\nCONTESTED-STASHED\nline3\n' > data.txt
$GIT stash -q
printf 'line1\nCONTESTED-COMMITTED\nline3\n' > data.txt; $GIT commit -qam committed
$GIT stash pop; echo "exit=$?"
report; echo "--- data.txt ---"; cat data.txt

########################################################################
banner "6. git pull --rebase (real remote)"
rm -rf "$WORK/r_pull_up" "$WORK/r_pull"
mkrepo "$WORK/r_pull_up"
$GIT checkout -q main
cd "$WORK"; $GIT clone -q "$WORK/r_pull_up" r_pull; cd "$WORK/r_pull"; register "$WORK/r_pull"
# upstream advances
cd "$WORK/r_pull_up"; printf 'line1\nCONTESTED-UPSTREAM\nline3\n' > data.txt; $GIT commit -qam upstream
cd "$WORK/r_pull"; printf 'line1\nCONTESTED-LOCAL\nline3\n' > data.txt; $GIT commit -qam local
mark
$GIT pull --rebase; echo "exit=$?"
report; echo "--- data.txt ---"; cat data.txt; $GIT rebase --abort 2>/dev/null

########################################################################
banner "6b. git pull (merge)"
cd "$WORK/r_pull"; $GIT rebase --abort 2>/dev/null; mark
$GIT pull --no-rebase --no-edit; echo "exit=$?"
report; echo "--- data.txt ---"; cat data.txt

########################################################################
banner "7. git merge-tree (what forges use)"
mkrepo "$WORK/r_mt"; register "$WORK/r_mt"; mark
echo "-- merge-tree --write-tree main feature:"
$GIT merge-tree --write-tree main feature; echo "exit=$?"
report
TREE=$($GIT merge-tree --write-tree main feature 2>/dev/null | head -1)
echo "resulting data.txt in tree $TREE:"; $GIT cat-file -p "$TREE:data.txt" 2>/dev/null || echo "(no clean tree)"
mark

########################################################################
banner "8. git merge-file (plumbing)"
cd "$WORK/r_mt"; mark
$GIT show main:data.txt > /tmp/_o 2>/dev/null
$GIT merge-file -p <($GIT show main:data.txt) <($GIT show main~1:data.txt) <($GIT show feature:data.txt) >/dev/null 2>&1; echo "exit=$?"
report

########################################################################
banner "9. git apply / am (patch application)"
mkrepo "$WORK/r_am"; register "$WORK/r_am"; mark
$GIT format-patch -1 feature -o "$WORK/patches" >/dev/null
$GIT am -3 "$WORK/patches"/*.patch; echo "exit=$?"
report; echo "--- data.txt ---"; cat data.txt; $GIT am --abort 2>/dev/null

########################################################################
banner "10. git checkout -m / restore --merge (re-create conflict)"
cd "$WORK/r_merge"; mark
$GIT merge --abort 2>/dev/null
echo "(state check)"; report

########################################################################
banner "11. COLLEAGUE CLONE: .gitattributes present, driver NOT in config"
rm -rf "$WORK/r_colleague"
mkrepo "$WORK/r_colleague_up"; register "$WORK/r_colleague_up"
cd "$WORK"; $GIT clone -q "$WORK/r_colleague_up" r_colleague
cd "$WORK/r_colleague"
echo "-- .gitattributes shipped in the clone:"; cat .gitattributes
echo "-- merge.probe.driver in cloned config: '$($GIT config merge.probe.driver || echo '<UNSET>')'"
mark
$GIT merge origin/feature; echo "exit=$?"
report
echo "--- data.txt (colleague result) ---"; cat data.txt
echo "--- git status ---"; $GIT status --short

########################################################################
banner "12. What if driver is declared but the binary is MISSING (exit 127)?"
mkrepo "$WORK/r_missing"; cd "$WORK/r_missing"
$GIT config merge.probe.name x; $GIT config merge.probe.driver "/nonexistent/mergiraf-that-is-not-installed %O %A %B"
$GIT merge feature; echo "exit=$?"
echo "--- data.txt ---"; cat data.txt
echo "--- status ---"; $GIT status --short

########################################################################
banner "13. Driver exits NONZERO (signals conflict)"
cat > "$WORK/fail-driver.sh" <<'EOF2'
#!/bin/bash
echo "DRIVER-CONFLICT" >> "$PROBE_LOG"
printf 'DRIVER SAYS CONFLICT\n' > "$2"
exit 1
EOF2
chmod +x "$WORK/fail-driver.sh"
mkrepo "$WORK/r_fail"; cd "$WORK/r_fail"
$GIT config merge.probe.name x; $GIT config merge.probe.driver "$WORK/fail-driver.sh %O %A %B"
$GIT merge feature; echo "exit=$?"
echo "--- data.txt ---"; cat data.txt
echo "--- status ---"; $GIT status --short

########################################################################
banner "14. Can the driver be configured FROM THE REPO? (.gitconfig in repo, include.path)"
mkrepo "$WORK/r_portable"; cd "$WORK/r_portable"
cat > .gitconfig-shipped <<EOF3
[merge "probe"]
	name = probe
	driver = $EXP/driver.sh %O %A %B %L %P
EOF3
$GIT add .gitconfig-shipped; $GIT commit -qm ship-config
echo "-- attempt: does git auto-read a repo-tracked config file? (no include configured)"
mark
$GIT merge feature; echo "exit=$?"
report
echo "--- data.txt ---"; cat data.txt
$GIT merge --abort 2>/dev/null

banner "FULL DRIVER INVOCATION LOG"
cat "$PROBE_LOG"
