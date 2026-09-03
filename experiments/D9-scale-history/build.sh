#!/bin/bash
# D9-4: MANY FILES x LONG HISTORY (the shape a document app actually produces)
# Prior work measured 100k files at ONE commit. This measures history depth.
set -eu
export GIT_CONFIG_NOSYSTEM=1
export HOME=$PWD/fakehome; rm -rf fakehome; mkdir -p fakehome
printf '[user]\n\tname=t\n\temail=t@t\n[init]\n\tdefaultBranch=main\n[gc]\n\tauto=0\n' > fakehome/.gitconfig
rm -rf repo; git init -q repo; cd repo
NFILES=${NFILES:-500}
NREV=${NREV:-100}
mkdir -p docs
python3 - "$NFILES" <<'PY'
import sys,os,random
n=int(sys.argv[1]); random.seed(1)
words=open('/usr/share/dict/words').read().split() if os.path.exists('/usr/share/dict/words') else ['lorem','ipsum','dolor','sit','amet','consectetur','adipiscing','elit','sed','do','eiusmod','tempor']
for i in range(n):
    with open(f'docs/doc{i:05d}.md','w') as f:
        f.write(f'# Document {i}\n\n')
        for p in range(20):
            f.write(' '.join(random.choice(words) for _ in range(60))+'\n\n')
PY
git add -A; git commit -qm "initial import of $NFILES docs"
echo "initial commit done: $(git rev-list --count HEAD) commits"
# NREV rounds; each round touches 20 random files -> each file gets ~NREV*20/NFILES revisions
python3 - "$NFILES" "$NREV" <<'PY' > /dev/null
import sys,random,subprocess,os
n=int(sys.argv[1]); r=int(sys.argv[2]); random.seed(2)
env=dict(os.environ)
for k in range(r):
    for f in random.sample(range(n),20):
        p=f'docs/doc{f:05d}.md'
        lines=open(p).read().split('\n')
        idx=random.randrange(2,len(lines)-1)
        lines[idx]=lines[idx]+f' edit{k}'
        open(p,'w').write('\n'.join(lines))
    subprocess.run(['git','commit','-qam',f'round {k}'],check=True,env=env)
PY
echo "history built: $(git rev-list --count HEAD) commits, $(git ls-files | wc -l) files"
