#!/bin/bash
# W5-T7: do users who merge LOCALLY (tool installed) get the same bytes as the
# SERVER produces?  And what does a user with NO tooling get?
# Three merges of the SAME two commits, compared by blob sha.
set -u
export GIT_CONFIG_NOSYSTEM=1 GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t \
       GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t GIT_CONFIG_GLOBAL=/dev/null
H=$(cd "$(dirname "$0")" && pwd); W=$H/work-t7; rm -rf "$W"; mkdir -p "$W"; cd "$W"
hr(){ echo; echo "=================================================================="; echo "### $*"; echo "=================================================================="; }

BASE='| id     | item     | qty | unit  |
| ------ | -------- | --: | ----: |
| r_0001 | widget   |  10 | 12.00 |
| r_0002 | gadget   |  20 |  6.00 |

grand := sum(qty)
'

mkrepo(){    # $1 = dir  $2 = .gitattributes content (may be empty)
  rm -rf "$1"; git init -q "$1"; cd "$1"
  printf '%s' "$BASE" > b.tbl
  [ -n "${2:-}" ] && printf '%s\n' "$2" > .gitattributes
  git add -A; git commit -qm base >/dev/null
  git branch -M main
  git checkout -q -b topic
  sed -i 's/|  20 |/|  25 |/' b.tbl; git commit -qam theirs >/dev/null
  git checkout -q main
  sed -i 's/|  6.00 |/|  6.50 |/' b.tbl; git commit -qam ours >/dev/null
  cd "$W"
}

hr "1. THE SERVER (bare repo, no attributes, no config)"
rm -rf srv.git; git init -q --bare srv.git
mkrepo dev "*.tbl merge=gws"; cd dev; git push -q "$W/srv.git" main topic; cd "$W"
python3 "$H/gws_merge_server.py" merge --repo srv.git --into refs/heads/main --from refs/heads/topic >/dev/null
SRV_BLOB=$(git -C srv.git rev-parse main:b.tbl)
echo "  blob = $SRV_BLOB"
git -C srv.git cat-file -p main:b.tbl | sed 's/^/    /'

hr "2. A LOCAL USER WITH THE TOOL INSTALLED (.gitattributes + merge driver)"
mkrepo local_tool "*.tbl merge=gws"; cd local_tool
# the client-side deployment: a merge driver in LOCAL config + .gitattributes
cat > "$W/driver.sh" <<'DRV'
#!/bin/bash
# git passes: %O (base) %A (ours, also the output file) %B (theirs) %P (path)
exec python3 "$1" "$2" "$3" "$4" "$5"
DRV
chmod +x "$W/driver.sh"
cat > "$W/clientmerge.py" <<'PY'
import sys
sys.path.insert(0, sys.argv[0].rsplit('/',1)[0])
import gws_merge_server as S
base, ours, theirs, path = sys.argv[1:5]
b=open(base,'rb').read(); o=open(ours,'rb').read(); t=open(theirs,'rb').read()
try:
    merged, cf = S.merge_tbl(b, o, t, path)
except S.Refuse as e:
    sys.stderr.write("gws refuses: %s\n" % e); sys.exit(1)
open(ours,'wb').write(merged)
sys.exit(1 if cf else 0)
PY
cp "$H/gws_merge_server.py" "$W/"
git config merge.gws.name "gws type-aware merge"
git config merge.gws.driver "python3 $W/clientmerge.py %O %A %B %P"
echo "  local config:"; git config --get-regexp '^merge\.gws' | sed 's/^/    /'
echo "  .gitattributes: $(cat .gitattributes)"
git merge topic -m "local merge" >/dev/null 2>&1; echo "  git merge exit=$?"
LOCAL_BLOB=$(git rev-parse HEAD:b.tbl)
echo "  blob = $LOCAL_BLOB"
git cat-file -p HEAD:b.tbl | sed 's/^/    /'
cd "$W"

hr "3. A LOCAL USER WITH NO TOOLING (stock git) -- the colleague who just clones"
mkrepo plain "*.tbl merge=gws"; cd plain
git merge topic -m "plain merge" >/dev/null 2>&1; echo "  git merge exit=$?  (1 = conflict)"
echo "  NOTE: .gitattributes says 'merge=gws' but no such driver is configured."
echo "        git does NOT fail; it silently falls back to the default text merge:"
echo "  working-tree file:"; sed 's/^/    /' b.tbl
echo "  git status: $(git status --short b.tbl)"
cd "$W"

hr "COMPARISON"
echo "  server blob : $SRV_BLOB"
echo "  local  blob : $LOCAL_BLOB"
if [ "$SRV_BLOB" = "$LOCAL_BLOB" ]; then
  echo "  IDENTICAL -- a local merge and a server merge produce the same bytes."
else
  echo "  *** DIFFERENT BYTES ***"
  diff <(git -C srv.git cat-file -p "$SRV_BLOB") \
       <(git -C local_tool cat-file -p "$LOCAL_BLOB") | sed 's/^/    /'
fi
echo
echo "  no-tooling user: got a file with $(grep -c '<<<<<<<' plain/b.tbl) conflict marker(s)"
echo "  and git left the merge UNRESOLVED, so nothing was committed."

hr "4. WHAT IF THE NO-TOOLING USER RESOLVES BY HAND AND PUSHES?"
cd plain
git checkout -q --theirs b.tbl 2>/dev/null || true
# simulate the naive resolution: keep the markers, commit anyway
git add b.tbl; git commit -qm "naive resolution" >/dev/null
echo "  they committed: $(git rev-parse --short HEAD)"
echo -n "  does the committed file still contain markers? "
git cat-file -p HEAD:b.tbl | grep -qc '<<<<<<<' && echo "YES" || echo "no"
cd "$W"
rm -rf srv2.git; git init -q --bare srv2.git
cd plain; git push -q "$W/srv2.git" main 2>&1 | sed 's/^/    /'; cd "$W"
echo "  push accepted by a bare repo: $(git -C srv2.git rev-parse --short main 2>/dev/null || echo REJECTED)"
echo
echo ">> NOTHING in git stops this. The server only mediates merges it performs."
echo ">> A direct push of a corrupt artifact needs a pre-receive hook, which"
echo ">> github.com does not offer (GitHub Enterprise Server only)."
