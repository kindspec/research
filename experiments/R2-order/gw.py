"""Stock git in a throwaway repo. No .gitattributes, no driver, no config."""
import os, subprocess, tempfile, shutil
def sh(*a, cwd=None): return subprocess.run(a, cwd=cwd, capture_output=True, text=True)
def merge(base, ours, theirs, fn='a.tbl'):
    d = tempfile.mkdtemp()
    try:
        sh('git','init','-q',d)
        for k,v in [('user.email','t@e'),('user.name','t')]: sh('git','config',k,v,cwd=d)
        p = os.path.join(d, fn)
        open(p,'w').write(base); sh('git','add','-A',cwd=d); sh('git','commit','-qm','b',cwd=d)
        sh('git','branch','-M','main',cwd=d)
        sh('git','checkout','-qb','x',cwd=d); open(p,'w').write(theirs); sh('git','commit','-qam','x',cwd=d)
        sh('git','checkout','-q','main',cwd=d); open(p,'w').write(ours); sh('git','commit','-qam','o',cwd=d)
        r = sh('git','merge','x','-m','m',cwd=d)
        t = open(p).read()
        return (r.returncode, t.count('<<<<<<<'), t)
    finally: shutil.rmtree(d)
def mergeN(base, branches, order, fn='a.tbl'):
    d = tempfile.mkdtemp()
    try:
        sh('git','init','-q',d)
        for k,v in [('user.email','t@e'),('user.name','t')]: sh('git','config',k,v,cwd=d)
        p = os.path.join(d, fn)
        open(p,'w').write(base); sh('git','add','-A',cwd=d); sh('git','commit','-qm','b',cwd=d)
        sh('git','branch','-M','main',cwd=d)
        for i,b in enumerate(branches):
            sh('git','checkout','-q','main',cwd=d); sh('git','checkout','-qb',f'b{i}',cwd=d)
            open(p,'w').write(b); sh('git','commit','-qam',f'b{i}',cwd=d)
        sh('git','checkout','-q','main',cwd=d)
        for i in order:
            r = sh('git','merge',f'b{i}','-m','m',cwd=d)
            if r.returncode: return 'conflict', None
        return 'clean', open(p).read()
    finally: shutil.rmtree(d)
def ins(t, after, line):
    L=t.splitlines(); i=next(i for i,l in enumerate(L) if after in l)
    L.insert(i+1, line); return '\n'.join(L)+'\n'
