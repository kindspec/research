#!/bin/bash
# D9-7: conflicts as DATA in refs/gws/*, artifact stays valid. End to end.
set -u
export GIT_CONFIG_NOSYSTEM=1
export HOME=$PWD/fakehome; rm -rf fakehome; mkdir -p fakehome
printf '[user]\n\tname=s\n\temail=s@s\n[init]\n\tdefaultBranch=main\n' > fakehome/.gitconfig
W=$PWD/work; rm -rf "$W"; mkdir -p "$W"; cd "$W"
hr(){ echo; echo "=========================================================="; echo "### $*"; echo "=========================================================="; }

hr "A. '-merge' vs 'binary' vs nothing: what the CLIENT gets on a real conflict"
for ATTR in "" "s.csv -merge" "s.csv binary"; do
  L=${ATTR:-"(no attribute)"}
  rm -rf t; git init -q t; cd t
  printf 'item,qty\napple,1\n' > s.csv; [ -n "$ATTR" ] && echo "$ATTR" > .gitattributes
  git add -A; git commit -qm base
  git checkout -qb f; printf 'item,qty\napple,2\n' > s.csv; git commit -qam f
  git checkout -q main; printf 'item,qty\napple,3\n' > s.csv; git commit -qam m
  echo "--- [$L] ---"
  git merge f >/dev/null 2>&1
  echo -n "    file: "; tr '\n' '|' < s.csv; echo
  echo -n "    parses as CSV? "; python3 -c "
import csv,sys
try:
  r=list(csv.reader(open('s.csv')))
  w=set(len(x) for x in r if x)
  print('YES' if len(w)==1 else 'MALFORMED (ragged: %s)'%sorted(w))
except Exception as e: print('NO:',e)"
  echo "    status: $(git status --short s.csv)"
  cd "$W"
done

hr "B. SERVER records the residual conflict as DATA in refs/gws/conflicts/*"
rm -rf srv.git dev; git init -q --bare srv.git; git init -q dev; cd dev; git remote add o ../srv.git
printf 'item,qty,price\napple,1,10\n' > s.csv
printf '*.csv binary\n' > .gitattributes           # the portable client-side backstop
git add -A; git commit -qm base; git push -q o main
git checkout -qb alice; printf 'item,qty,price\napple,1,55\n' > s.csv; git commit -qam alice; git push -q o alice
git checkout -q main;   printf 'item,qty,price\napple,1,99\n' > s.csv; git commit -qam bob;   git push -q o main
echo "alice: price 10->55 ; bob: price 10->99  == a GENUINE cell conflict"
cd "$W"/srv.git
git merge-tree --write-tree main alice > o.txt 2>&1
B=$(awk '$4=="s.csv"&&$3==1{print $2}' o.txt); O=$(awk '$4=="s.csv"&&$3==2{print $2}' o.txt); T=$(awk '$4=="s.csv"&&$3==3{print $2}' o.txt)
echo "  stages: base=$B ours=$O theirs=$T"
# server policy: unresolvable cell -> keep OURS in the artifact, record the conflict beside it
REC=$(printf '{"path":"s.csv","row":"apple","column":"price","base":"10","ours":"99","theirs":"55","base_blob":"%s","ours_blob":"%s","theirs_blob":"%s"}\n' "$B" "$O" "$T")
RECBLOB=$(printf '%s' "$REC" | git hash-object -w --stdin)
CTREE=$(printf '100644 blob %s\tconflict.json\n' "$RECBLOB" | git mktree)
CCOMMIT=$(git commit-tree "$CTREE" -m "unresolved cell conflict s.csv/apple/price")
git update-ref refs/gws/conflicts/s.csv/apple/price "$CCOMMIT"
# the artifact keeps OURS -- valid CSV, no markers
NEWTREE=$(git ls-tree main | git mktree)
MC=$(git commit-tree "$NEWTREE" -p main -p alice -m "merge alice (1 unresolved cell recorded in refs/gws/conflicts)")
git update-ref refs/heads/main "$MC"
echo "  recorded: $(git for-each-ref --format='%(refname)' refs/gws/conflicts)"
echo "  record contents:"; git cat-file -p "$CCOMMIT^{tree}" >/dev/null; git cat-file -p "$RECBLOB" | sed 's/^/     /'

hr "C. What the PLAIN client sees after cloning"
cd "$W"; rm -rf plain; git clone -q srv.git plain; cd plain
echo "-- s.csv --"; sed 's/^/   /' s.csv
python3 -c "import csv;r=list(csv.reader(open('s.csv')));print('   parses as CSV:',len(r),'rows x',len(r[0]),'cols  ->  VALID')"
echo "-- refs the plain clone received --"; git for-each-ref --format='   %(refname)' | grep -v remotes
echo "   (conflict records are invisible to a plain clone -- by design; our client fetches refs/gws/*)"
echo "-- our client asks for them explicitly --"
git fetch -q origin 'refs/gws/*:refs/gws/*' && git for-each-ref --format='   %(refname)' refs/gws
echo "-- and reads the conflict as structured data, not markers --"
git cat-file -p "$(git rev-parse refs/gws/conflicts/s.csv/apple/price):conflict.json" | python3 -m json.tool | sed 's/^/   /'
