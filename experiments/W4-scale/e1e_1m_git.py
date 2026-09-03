#!/usr/bin/env python3
"""Git ops on a 1M-row .tbl (13 revisions only -- 50 would be 7 GB loose)."""
import sys, os, time, json, statistics, subprocess, shutil, random
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib')); sys.path.insert(0, HERE)
import gen
from e1b_git import g, timed, newrepo, numstat, WORK
n = 1000000
r = newrepo(os.path.join(WORK, 'tbl1m')); p = os.path.join(r, 'data.tbl')
text = gen.tbl_text(n); open(p, 'w').write(text)
t_add, _ = timed(lambda: g(r, 'add', 'data.tbl'), 1)
g(r, 'commit', '-qm', 'base')
L = text.split('\n'); ti = [i for i, l in enumerate(L) if l.startswith('|')]
def cell(li, v):
    c = L[li][1:-1].split('|'); w = len(c[3]); s = ' ' + v
    c[3] = s.ljust(w) if len(s) <= w else s + ' '
    L[li] = '|' + '|'.join(c) + '|'
cell(ti[2 + n // 2], '999'); open(p, 'w').write('\n'.join(L))
t_diff, _ = timed(lambda: g(r, 'diff', '--stat', '--', 'data.tbl'), 3)
a, d = numstat(r, 'data.tbl')
t_status, _ = timed(lambda: g(r, 'status', '--porcelain'), 3)
g(r, 'checkout', '--', 'data.tbl')
g(r, 'checkout', '-qb', 'ours'); L = text.split('\n'); cell(ti[3], '111'); open(p,'w').write('\n'.join(L)); g(r,'commit','-qam','o')
g(r, 'checkout', '-q', 'main'); g(r, 'checkout', '-qb', 'theirs'); L = text.split('\n'); cell(ti[n], '222'); open(p,'w').write('\n'.join(L)); g(r,'commit','-qam','t')
g(r, 'checkout', '-q', 'ours')
t0 = time.perf_counter(); m = g(r, 'merge', '--no-edit', 'theirs', check=False); t_merge = time.perf_counter() - t0
g(r, 'checkout', '-q', 'main')
rng = random.Random(3); L = text.split('\n')
t0 = time.perf_counter()
for rev in range(12):
    for _ in range(5000): cell(ti[2 + rng.randrange(n)], str(rng.randint(1, 500)))
    open(p, 'w').write('\n'.join(L)); g(r, 'commit', '-qam', f'r{rev}')
t_12 = time.perf_counter() - t0
loose = sum(os.path.getsize(os.path.join(dp,f)) for dp,_,fs in os.walk(r+'/.git') for f in fs)
t_pack, _ = timed(lambda: g(r, 'repack', '-adq'), 1)
packed = sum(os.path.getsize(os.path.join(dp,f)) for dp,_,fs in os.walk(r+'/.git') for f in fs)
t_clone = None
cl = os.path.join(WORK, 'clone1m'); shutil.rmtree(cl, ignore_errors=True)
t0 = time.perf_counter(); subprocess.run(['git','clone','-q','--no-hardlinks',r,cl],check=True,capture_output=True); t_clone = time.perf_counter()-t0
shutil.rmtree(cl, ignore_errors=True)
rec = dict(n=n, file_mb=len(text.encode())/2**20, add_s=t_add, diff_s=t_diff, diff_add=a, diff_del=d,
           status_s=t_status, merge_s=t_merge, merge_ok=m.returncode==0, rev12_s=t_12,
           loose_mb=loose/2**20, repack_s=t_pack, packed_mb=packed/2**20, clone_s=t_clone)
print('E1b1M', json.dumps(rec), flush=True)
json.dump(rec, open(os.path.join(HERE,'out/e1_1m_git.json'),'w'), indent=1)
