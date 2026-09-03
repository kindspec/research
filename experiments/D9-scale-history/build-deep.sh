#!/bin/bash
set -eu
export GIT_CONFIG_NOSYSTEM=1; export HOME=$PWD/fakehome
rm -rf deep; git init -q deep; cd deep
git config gc.auto 0
mkdir -p docs
for i in $(seq 0 199); do printf '# Doc %d\n\nbody line\n' $i > docs/d$i.md; done
git add -A; git commit -qm init
python3 - <<'PY'
import subprocess,os,random
random.seed(7); env=dict(os.environ)
N=50000
p=subprocess.Popen(['git','fast-import','--quiet'],stdin=subprocess.PIPE,env=env,text=True)
w=p.stdin.write
head=subprocess.check_output(['git','rev-parse','HEAD'],env=env,text=True).strip()
w(f'reset refs/heads/main\nfrom {head}\n')
for k in range(N):
    f=random.randrange(200)
    w('commit refs/heads/main\n')
    w('mark :%d\n'%(k+1))
    w('committer t <t@t> %d +0000\n'%(1700000000+k))
    msg=f'c{k}'
    w('data %d\n%s\n'%(len(msg),msg))
    body=f'# Doc {f}\n\nbody line rev{k}\n'
    w('M 100644 inline docs/d%d.md\n'%f)
    w('data %d\n%s'%(len(body),body))
    w('\n')
p.stdin.close(); p.wait()
PY
git reset -q --hard refs/heads/main
echo "deep history: $(git rev-list --count HEAD) commits, $(git ls-files|wc -l) files"
git gc -q 2>/dev/null || true
echo "packed .git: $(du -sh .git|cut -f1)"
