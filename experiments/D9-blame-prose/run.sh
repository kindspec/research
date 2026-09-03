#!/bin/bash
# D9-4b: "who wrote this paragraph?" -- git blame on REFLOWED PROSE
set -u
export GIT_CONFIG_NOSYSTEM=1
export HOME=$PWD/fakehome; rm -rf fakehome; mkdir -p fakehome
printf '[user]\n\tname=t\n\temail=t@t\n[init]\n\tdefaultBranch=main\n' > fakehome/.gitconfig
rm -rf r; git init -q r; cd r
hr(){ echo; echo "=================================================="; echo "### $*"; echo "=================================================="; }

hr "SETUP: three authors write three sentences, hard-wrapped at 72 cols"
cat > doc.md <<'EOF'
# The Report

Alice wrote this opening sentence about the quarterly results and it
runs across two wrapped lines because the file is hard wrapped.

Bob added this second paragraph concerning the supply chain, which
also happens to wrap onto a second physical line of the source file.

Carol contributed the closing paragraph summarising the outlook for
the coming year and the risks that the board should be aware of now.
EOF
git add -A; GIT_AUTHOR_NAME=Alice GIT_COMMITTER_NAME=Alice GIT_AUTHOR_EMAIL=a@x GIT_COMMITTER_EMAIL=a@x git commit -qm "alice: skeleton + para 1"
# make each paragraph genuinely authored by a different person
python3 - <<'PY'
s=open('doc.md').read()
open('doc.md','w').write(s)
PY
sed -i 's/^Bob added.*/Bob added this second paragraph concerning the supply chain, which/' doc.md
GIT_AUTHOR_NAME=Bob GIT_COMMITTER_NAME=Bob GIT_AUTHOR_EMAIL=b@x GIT_COMMITTER_EMAIL=b@x git commit -qam "bob: para 2" 2>/dev/null || true
echo "-- blame BEFORE reflow --"
git blame --line-porcelain doc.md 2>/dev/null | grep '^author ' | sort | uniq -c
git blame doc.md | sed 's/^/  /'

hr "THE EVENT: Dave changes ONE WORD in Bob's paragraph and the editor rewraps to 80 cols"
python3 - <<'PY'
import textwrap
src=open('doc.md').read()
paras=src.split('\n\n')
out=[]
for p in paras:
    if not p.strip(): continue
    if p.startswith('#'): out.append(p); continue
    flat=' '.join(l.strip() for l in p.strip().split('\n'))
    flat=flat.replace('supply chain','logistics network')   # ONE semantic change
    out.append(textwrap.fill(flat,80))
open('doc.md','w').write('\n\n'.join(out)+'\n')
PY
echo "-- the new file --"; sed 's/^/  /' doc.md
GIT_AUTHOR_NAME=Dave GIT_COMMITTER_NAME=Dave GIT_AUTHOR_EMAIL=d@x GIT_COMMITTER_EMAIL=d@x git commit -qam "dave: one word + rewrap"

hr "RESULT: git blame after the rewrap"
git blame doc.md | sed 's/^/  /'
echo
echo "-- author attribution tally --"
git blame --line-porcelain doc.md | grep '^author ' | sort | uniq -c
echo
echo "-- does -w (ignore whitespace) rescue it? --"
git blame -w doc.md | awk '{print $2}' | sort | uniq -c
echo "-- does -M -C -C -C (detect moves/copies) rescue it? --"
git blame -w -M -C -C -C doc.md | awk '{print $2}' | sort | uniq -c
echo
echo "-- git diff of that one-word commit --"
git show --stat --oneline HEAD | sed 's/^/  /'
echo "-- lines changed for a ONE WORD edit --"
git show --numstat HEAD | tail -2 | sed 's/^/  /'

hr "CONTROL: the same one-word edit with NO rewrap (one sentence per line)"
cd ..; rm -rf r2; git init -q r2; cd r2
printf '# The Report\n\nAlice paragraph one.\n\nBob paragraph about the supply chain.\n\nCarol paragraph three.\n' > doc.md
git add -A; GIT_AUTHOR_NAME=Alice GIT_COMMITTER_NAME=Alice GIT_AUTHOR_EMAIL=a@x GIT_COMMITTER_EMAIL=a@x git commit -qm alice
sed -i 's/supply chain/logistics network/' doc.md
GIT_AUTHOR_NAME=Dave GIT_COMMITTER_NAME=Dave GIT_AUTHOR_EMAIL=d@x GIT_COMMITTER_EMAIL=d@x git commit -qam dave
git blame doc.md | sed 's/^/  /'
echo "-- numstat --"; git show --numstat HEAD | tail -1 | sed 's/^/  /'
