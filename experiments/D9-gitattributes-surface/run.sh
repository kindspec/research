#!/bin/bash
# D9-1: .gitattributes capability surface — which mechanisms are REPO-PORTABLE
# (config lives in .gitattributes, checked in) vs LOCAL-CONFIG-REQUIRED.
set -u
export GIT_AUTHOR_NAME=t GIT_AUTHOR_EMAIL=t@t GIT_COMMITTER_NAME=t GIT_COMMITTER_EMAIL=t@t
export GIT_CONFIG_NOSYSTEM=1
export HOME=$PWD/fakehome; rm -rf fakehome; mkdir -p fakehome
printf '[user]\n\tname=t\n\temail=t@t\n[init]\n\tdefaultBranch=main\n' > fakehome/.gitconfig
W=$PWD/work; rm -rf "$W"; mkdir -p "$W"
hr(){ echo; echo "=============================================================="; echo "### $*"; echo "=============================================================="; }

######################################################################
hr "A. diff=<driver> + textconv  — needs LOCAL config?"
cd "$W"; rm -rf a; mkdir a; cd a; git init -q .
printf 'binary-ish payload v1\n' > f.bin
echo 'f.bin diff=upper' > .gitattributes
git add -A; git commit -qm one
printf 'binary-ish payload v2\n' > f.bin
echo "-- (a1) fresh clone state: diff=upper declared, NO merge/diff config --"
git diff --stat -- f.bin; echo "   textual diff:"; git diff -- f.bin | tail -4
echo "-- (a2) now define diff.upper.textconv locally --"
git config diff.upper.textconv 'tr a-z A-Z <'
git diff -- f.bin | tail -4
echo ">> VERDICT A: textconv output changed only after local git config. Attribute alone = no-op."

######################################################################
hr "B. built-in diff drivers (diff=markdown etc) — SHIP WITH GIT, no config"
cd "$W"; rm -rf b; mkdir b; cd b; git init -q .
cat > code.md <<'EOF'
# Heading One

alpha
beta
gamma
delta
epsilon

## Heading Two

zeta
EOF
git add -A; git commit -qm one
sed -i 's/gamma/GAMMA/' code.md
echo "-- (b1) NO attribute:"; git diff -U1 -- code.md | grep '^@@'
echo 'code.md diff=markdown' > .gitattributes; git add .gitattributes
echo "-- (b2) WITH 'diff=markdown' (built-in funcname driver, zero config):"; git diff -U1 -- code.md | grep '^@@'
echo ">> git's built-in language drivers: $(git config -f /dev/null --list >/dev/null; echo ok)"
echo "-- list of built-in diff drivers compiled into git (userdiff.c):"
git help attributes 2>/dev/null | grep -oE '^   [a-z+]+$' | head -50 | tr -d ' ' | tr '\n' ' '; echo

######################################################################
hr "C. diff wordRegex — LOCAL config? (word-diff granularity)"
cd "$W"; rm -rf c; mkdir c; cd c; git init -q .
printf 'a,b,c,d,e\n' > t.csv; git add -A; git commit -qm one
printf 'a,b,X,d,e\n' > t.csv
echo 'ok' > /dev/null
echo "-- (c1) default word diff:"; git diff --word-diff=plain -- t.csv | tail -2
echo 't.csv diff=csv' > .gitattributes
echo "-- (c2) attribute set, driver undefined:"; git diff --word-diff=plain -- t.csv | tail -2
git config diff.csv.wordRegex '[^,\n]+|,'
echo "-- (c3) after local 'git config diff.csv.wordRegex':"; git diff --word-diff=plain -- t.csv | tail -2
echo ">> VERDICT C: wordRegex is LOCAL-ONLY config."

######################################################################
hr "D. merge=union — BUILT IN, repo-portable, zero config (but is it SAFE?)"
cd "$W"; rm -rf d; mkdir d; cd d; git init -q .
printf 'name,qty\napple,1\n' > s.csv
echo 's.csv merge=union' > .gitattributes
git add -A; git commit -qm base
git checkout -qb feat; printf 'name,qty\napple,1\nbanana,2\n' > s.csv; git commit -qam feat
git checkout -q main; printf 'name,qty\napple,1\ncherry,3\n' > s.csv; git commit -qam main
git merge -q feat 2>&1 | head -3; echo "exit=$?"
echo "-- resulting s.csv --"; cat s.csv
echo ">> union merged CLEANLY with no config. Note ordering/duplication semantics."
echo
echo "-- D2: union on a CONCURRENT EDIT OF THE SAME LINE (the dangerous case) --"
cd "$W"; rm -rf d2; mkdir d2; cd d2; git init -q .
printf 'total,100\n' > s.csv; echo 's.csv merge=union' > .gitattributes; git add -A; git commit -qm base
git checkout -qb feat; printf 'total,200\n' > s.csv; git commit -qam feat
git checkout -q main; printf 'total,300\n' > s.csv; git commit -qam main
git merge feat 2>&1 | head -3
echo "-- resulting s.csv (union of a same-line edit) --"; cat s.csv
echo ">> union NEVER conflicts. It duplicates. For CSV that is a SILENTLY WRONG file."

######################################################################
hr "E. 'binary' and '-merge' — repo-portable refusal"
cd "$W"; rm -rf e; mkdir e; cd e; git init -q .
printf 'a\nO\nz\n' > f.dat; echo 'f.dat binary' > .gitattributes; git add -A; git commit -qm base
git checkout -qb feat; printf 'a\nT\nz\n' > f.dat; git commit -qam feat
git checkout -q main; printf 'a\nM\nz\n' > f.dat; git commit -qam main
git merge feat 2>&1 | head -4
echo "-- f.dat after conflict (binary attr) --"; cat f.dat; git status --short
echo ">> 'binary' is REPO-PORTABLE: no config needed, always refuses, keeps OURS verbatim, marks UU."
echo "   The file is NEVER corrupted with markers -> stays valid as its type."

######################################################################
hr "F. filter=<driver> clean/smudge — LOCAL config, and what a naive clone gets"
cd "$W"; rm -rf f; mkdir f; cd f; git init -q .
git config filter.strip.clean "sed 's/SECRET/REDACTED/'"
git config filter.strip.smudge cat
echo '*.txt filter=strip' > .gitattributes
printf 'value SECRET here\n' > a.txt
git add -A; git commit -qm one
echo "-- blob as stored in git (clean ran):"; git cat-file -p HEAD:a.txt
cd "$W"/f && git clone -q . ../fclone 2>/dev/null
cd "$W"/fclone
echo "-- fresh clone WITHOUT filter config: checked-out file --"; cat a.txt
echo "-- fresh clone: is it dirty? --"; git status --short; echo "(clean = filter absence silently ignored)"
echo "-- now a colleague edits and commits in the unconfigured clone --"
printf 'value SECRET here\nvalue SECRET two\n' > a.txt; git add -A; git -c user.email=t@t -c user.name=t commit -qm two
echo "-- blob now stored (clean did NOT run) --"; git cat-file -p HEAD:a.txt
echo ">> VERDICT F: filter FAILS OPEN AND SILENTLY. Unfiltered content enters history."
echo "-- F2: filter.<d>.required=true --"
git config filter.strip.required true
printf 'value SECRET three\n' >> a.txt
git add a.txt 2>&1 | head -3; echo "exit=$?"
echo ">> 'required' converts silent corruption into a hard error -- but 'required' is ALSO local config."

######################################################################
hr "G. text/-text/eol — repo-portable, handled by core git"
cd "$W"; rm -rf g; mkdir g; cd g; git init -q .
printf 'a\r\nb\r\n' > crlf.txt; printf 'a\r\nb\r\n' > keep.txt
printf 'crlf.txt text eol=lf\nkeep.txt -text\n' > .gitattributes
git add -A; git commit -qm one
echo "-- stored blob crlf.txt (text eol=lf -> normalized):"; git cat-file -p HEAD:crlf.txt | od -c | head -2
echo "-- stored blob keep.txt (-text -> verbatim):"; git cat-file -p HEAD:keep.txt | od -c | head -2
echo ">> VERDICT G: REPO-PORTABLE. Core git implements it; no driver, no config."

######################################################################
hr "H. export-subst / export-ignore — repo-portable but ARCHIVE-ONLY"
cd "$W"; rm -rf h; mkdir h; cd h; git init -q .
printf 'rev: $Format:%%H$\n' > ver.txt
printf 'secret\n' > private.txt
printf 'ver.txt export-subst\nprivate.txt export-ignore\n' > .gitattributes
git add -A; git commit -qm one
echo "-- working tree ver.txt (NOT substituted):"; cat ver.txt
git archive HEAD > ar.tar; mkdir -p ex && tar -xf ar.tar -C ex
echo "-- inside git archive:"; cat ex/ver.txt; echo "-- private.txt present in archive?"; ls ex/ | tr '\n' ' '; echo
echo ">> VERDICT H: REPO-PORTABLE, but only affects 'git archive'. Zero effect on clone/checkout/merge."
