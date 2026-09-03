#!/usr/bin/env python3
"""E4: one repo that looks like a real user's after a year.

~2,000 artifacts, mixed types, ~5,000 commits, some large tables, attachments.
Then: clone, status, log-on-one-file, full check, full build, total size.
"""
import sys, os, time, json, statistics, subprocess, shutil, random, hashlib
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib')); sys.path.insert(0, HERE)
import gen, blocks, tbl, derive

WORK = os.environ.get('W4WORK', '/home/cam/.local/state/scratch/claude-1000/w4')
REPO = os.path.join(WORK, 'year')
ENV = dict(os.environ, GIT_AUTHOR_NAME='w', GIT_AUTHOR_EMAIL='w@x', GIT_COMMITTER_NAME='w',
           GIT_COMMITTER_EMAIL='w@x', GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null')
N_COMMITS = int(os.environ.get('W4COMMITS', '5000'))


def g(repo, *a, check=True):
    return subprocess.run(['git', '-C', repo] + list(a), env=ENV, check=check,
                          capture_output=True, text=True)


def med(f, reps=5):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter(); r = f(); ts.append(time.perf_counter() - t0)
    return statistics.median(ts), r


def du(p):
    return sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(p) for f in fs
               if os.path.exists(os.path.join(dp, f)))


def build():
    shutil.rmtree(REPO, ignore_errors=True)
    os.makedirs(REPO)
    subprocess.run(['git', 'init', '-q', '-b', 'main', REPO], env=ENV, check=True, capture_output=True)
    g(REPO, 'config', 'gc.auto', '0')
    for d in ('docs', 'data', 'diagrams', 'assets'):
        os.makedirs(os.path.join(REPO, d))
    rng = random.Random(42)
    tables, docs, others = [], [], []

    # 600 tables: 5 large (20k rows), 95 medium (1k), 500 small (20-200)
    plan = [20000] * 5 + [1000] * 95 + [rng.randint(20, 200) for _ in range(500)]
    rng.shuffle(plan)
    for i, rows in enumerate(plan):
        p = f'data/t{i:04d}.tbl'
        open(os.path.join(REPO, p), 'w').write(gen.tbl_text(rows, seed=i))
        tables.append((p, rows))

    # 1200 documents, most referencing a table aggregate
    for j in range(1200):
        p = f'docs/d{j:04d}.md'
        ref = f'{rng.choice(tables)[0]}#grand' if rng.random() < 0.6 else None
        open(os.path.join(REPO, p), 'w').write(gen.doc_text(j, nblocks=rng.randint(15, 60), ref=ref))
        docs.append(p)

    # 150 small canvases
    for k in range(150):
        p = f'diagrams/c{k:03d}.canvas'
        n = rng.randint(5, 40)
        lines = [f'node n{i} "Node {i}" {{kind: service}}' for i in range(n)]
        lines += [f'edge n{rng.randrange(n)} -> n{rng.randrange(n)} "calls"' for _ in range(n)]
        open(os.path.join(REPO, p), 'w').write('\n'.join(lines) + '\n')
        others.append(p)

    # 50 binary attachments, semi-compressible, 100 KB - 2 MB
    for a in range(50):
        p = f'assets/a{a:03d}.bin'
        sz = rng.randint(100_000, 2_000_000)
        chunk = bytes(rng.randrange(256) for _ in range(4096))
        blob = (chunk * (sz // 4096 + 1))[:sz]
        blob = bytes(b ^ (i & 0x1f) for i, b in enumerate(blob[:20000])) + blob[20000:]
        open(os.path.join(REPO, p), 'wb').write(blob)
        others.append(p)

    t0 = time.perf_counter()
    g(REPO, 'add', '.')
    g(REPO, 'commit', '-qm', 'initial import')
    t_initial = time.perf_counter() - t0
    return tables, docs, others, t_initial, rng


def edit_tbl(path, rows, rng):
    """Change one cell, format-preserving (padded, as the format specifies)."""
    L = open(path).read().split('\n')
    ti = [i for i, l in enumerate(L) if l.startswith('|')]
    li = ti[2 + rng.randrange(rows)]
    cells = L[li][1:-1].split('|')
    w = len(cells[3]); v = ' ' + str(rng.randint(1, 500))
    cells[3] = v.ljust(w) if len(v) <= w else v + ' '
    L[li] = '|' + '|'.join(cells) + '|'
    open(path, 'w').write('\n'.join(L))


def edit_md(path, rng):
    L = open(path).read().split('\n')
    cands = [i for i, l in enumerate(L) if l and not l.startswith(('#', '-', '`', '{', '|'))]
    if not cands: return
    i = rng.choice(cands)
    L[i] = L[i].rstrip() + ' ' + rng.choice(gen.WORDS).capitalize() + '.'
    open(path, 'w').write('\n'.join(L))


def history(tables, docs, others, rng):
    """~N_COMMITS commits of realistic editing, weighted to a working set."""
    hot_t = rng.sample(tables, 60)
    hot_d = rng.sample(docs, 150)
    t0 = time.perf_counter()
    for c in range(N_COMMITS):
        touched = []
        for _ in range(rng.choice([1, 1, 1, 2, 3])):
            if rng.random() < 0.45:
                p, rows = rng.choice(hot_t) if rng.random() < 0.8 else rng.choice(tables)
                edit_tbl(os.path.join(REPO, p), rows, rng); touched.append(p)
            else:
                p = rng.choice(hot_d) if rng.random() < 0.8 else rng.choice(docs)
                edit_md(os.path.join(REPO, p), rng); touched.append(p)
        g(REPO, 'add', *set(touched))
        g(REPO, 'commit', '-qm', f'edit {c}', check=False)   # no-op edits happen
        if c % 500 == 0:
            print(f'  ...commit {c} ({time.perf_counter()-t0:.0f}s)', flush=True)
    return time.perf_counter() - t0


def measure(tables, docs):
    res = {}
    res['worktree_mb'] = (du(REPO) - du(os.path.join(REPO, '.git'))) / 2**20
    res['git_loose_mb'] = du(os.path.join(REPO, '.git')) / 2**20
    t_gc, _ = med(lambda: g(REPO, 'repack', '-adq'), 1)
    res['repack_s'] = t_gc
    res['git_packed_mb'] = du(os.path.join(REPO, '.git')) / 2**20
    res['files'] = int(g(REPO, 'ls-files').stdout.count('\n'))
    res['commits'] = int(g(REPO, 'rev-list', '--count', 'HEAD').stdout.strip())

    res['status_cold_s'], _ = med(lambda: g(REPO, 'status', '--porcelain'), 1)
    res['status_s'], _ = med(lambda: g(REPO, 'status', '--porcelain'), 5)
    hot = max(tables, key=lambda x: x[1])[0]
    res['log_file_s'], lg = med(lambda: g(REPO, 'log', '--oneline', '--', hot), 3)
    res['log_file_commits'] = lg.stdout.count('\n')
    res['log_follow_s'], _ = med(lambda: g(REPO, 'log', '--oneline', '--follow', '--', hot), 3)
    res['log_all_s'], _ = med(lambda: g(REPO, 'log', '--oneline'), 3)
    res['diff_head_s'], _ = med(lambda: g(REPO, 'diff', 'HEAD~50', 'HEAD', '--stat'), 3)
    res['blame_s'], _ = med(lambda: g(REPO, 'blame', '--line-porcelain', docs[0], check=False), 1)

    cl = os.path.join(WORK, 'clone')
    for name, args in (('clone_local_s', []), ('clone_nohardlink_s', ['--no-hardlinks']),
                       ('clone_shallow_s', ['--depth', '1'])):
        shutil.rmtree(cl, ignore_errors=True)
        t0 = time.perf_counter()
        subprocess.run(['git', 'clone', '-q'] + args + ['file://' + REPO if args and args[0] == '--depth'
                                                        else REPO, cl], env=ENV, check=True, capture_output=True)
        res[name] = time.perf_counter() - t0
        res[name.replace('_s', '_mb')] = du(cl) / 2**20
    shutil.rmtree(cl, ignore_errors=True)
    return res


def check_run():
    """`check`: parse+validate every artifact, assert round-trip on documents."""
    t0 = time.perf_counter()
    n_ok = n_bad = 0
    bad = []
    for dp, _, fs in os.walk(REPO):
        if '.git' in dp: continue
        for f in fs:
            p = os.path.join(dp, f)
            try:
                if f.endswith('.tbl'):
                    tbl.parse(open(p).read()); n_ok += 1
                elif f.endswith('.md'):
                    t = open(p).read()
                    assert blocks.render(blocks.parse(t)) == t
                    n_ok += 1
            except Exception as e:
                n_bad += 1; bad.append((p, str(e)[:80]))
    return time.perf_counter() - t0, n_ok, n_bad, bad[:5]


def build_run(cold):
    cwd = os.getcwd(); os.chdir(REPO)
    try:
        if cold:
            shutil.rmtree(derive.CACHE, ignore_errors=True)
        st = {'hit': 0, 'miss': 0}
        errs = 0
        t0 = time.perf_counter()
        for dp, _, fs in os.walk('.'):
            if '.git' in dp or derive.CACHE in dp: continue
            for f in fs:
                if not f.endswith('.md'): continue
                try:
                    derive.render(os.path.join(dp, f), st)
                except Exception:
                    errs += 1
        return time.perf_counter() - t0, st, errs
    finally:
        os.chdir(cwd)


if __name__ == '__main__':
    os.makedirs(WORK, exist_ok=True)
    t0 = time.perf_counter()
    tables, docs, others, t_init, rng = build()
    print(f'built fixtures in {time.perf_counter()-t0:.1f}s (initial commit {t_init:.1f}s)', flush=True)
    t_hist = history(tables, docs, others, rng)
    print(f'history: {N_COMMITS} commits in {t_hist:.1f}s', flush=True)
    res = measure(tables, docs)
    res['initial_commit_s'] = t_init
    res['history_s'] = t_hist
    res['commit_ms_each'] = 1000 * t_hist / N_COMMITS
    c_s, ok, bad, badlist = check_run()
    res.update(check_s=c_s, check_ok=ok, check_bad=bad, check_bad_sample=badlist)
    b_cold, st_c, e_c = build_run(True)
    b_warm, st_w, e_w = build_run(False)
    res.update(build_cold_s=b_cold, build_cold_miss=st_c['miss'], build_cold_hit=st_c['hit'],
               build_cold_errors=e_c,
               build_warm_s=b_warm, build_warm_miss=st_w['miss'], build_warm_hit=st_w['hit'],
               build_warm_errors=e_w)
    print('E4', json.dumps(res, indent=1), flush=True)
    json.dump(res, open(os.path.join(HERE, 'out/e4_repo.json'), 'w'), indent=1)
