"""Shared red-team harness: run a REAL stock-git three-way merge, no config."""
import os, subprocess, tempfile, shutil, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'L1-nominal-merge'))

def sh(*a, cwd=None):
    return subprocess.run(a, cwd=cwd, capture_output=True, text=True)

def git_merge(base, ours, theirs, fn='a.txt', extra=None):
    """Stock git merge. No .gitattributes, no drivers, no config beyond identity.
    Returns (returncode, merged_text, n_conflict_markers)."""
    d = tempfile.mkdtemp()
    try:
        sh('git', 'init', '-q', d)
        sh('git', 'config', 'user.email', 't@e', cwd=d)
        sh('git', 'config', 'user.name', 't', cwd=d)
        p = os.path.join(d, fn)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        open(p, 'w').write(base)
        if extra:
            for k, v in extra.items():
                open(os.path.join(d, k), 'w').write(v)
        sh('git', 'add', '-A', cwd=d); sh('git', 'commit', '-qm', 'base', cwd=d)
        sh('git', 'branch', '-M', 'main', cwd=d)
        sh('git', 'checkout', '-qb', 'x', cwd=d)
        open(p, 'w').write(theirs); sh('git', 'commit', '-qam', 'theirs', cwd=d)
        sh('git', 'checkout', '-q', 'main', cwd=d)
        open(p, 'w').write(ours); sh('git', 'commit', '-qam', 'ours', cwd=d)
        r = sh('git', 'merge', 'x', '-m', 'm', cwd=d)
        txt = open(p).read()
        n = sum(1 for l in txt.splitlines()
                if l.startswith(('<<<<<<<', '=======', '>>>>>>>', '|||||||')))
        return r.returncode, txt, n
    finally:
        shutil.rmtree(d)

def report(title, rc, txt, n):
    print(f'  merge exit={rc}  {"CLEAN" if rc == 0 else "CONFLICT"}  markers={n}')

def verdict(silent_wrong, note=''):
    print(f'  ==> {"SILENT-WRONG" if silent_wrong else "held (loud/legit)"}  {note}')
