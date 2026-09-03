#!/usr/bin/env python3
"""E1b: git diff / merge / object+pack size on .tbl at scale.
E1c: the alignment (padding) question, measured as diff line counts.
E1d: the width problem (50 / 200 columns).
"""
import sys, os, time, json, statistics, subprocess, shutil, random, re
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, 'lib')); sys.path.insert(0, HERE)
import gen

WORK = os.environ.get('W4WORK', '/home/cam/.local/state/scratch/claude-1000/w4')
ENV = dict(os.environ, GIT_AUTHOR_NAME='w', GIT_AUTHOR_EMAIL='w@x', GIT_COMMITTER_NAME='w',
           GIT_COMMITTER_EMAIL='w@x', GIT_CONFIG_GLOBAL='/dev/null', GIT_CONFIG_SYSTEM='/dev/null')


def g(repo, *a, check=True):
    return subprocess.run(['git', '-C', repo] + list(a), env=ENV, check=check,
                          capture_output=True, text=True)


def timed(fn, reps=5):
    ts = []
    for _ in range(reps):
        t0 = time.perf_counter(); r = fn(); ts.append(time.perf_counter() - t0)
    return statistics.median(ts), r


def newrepo(path):
    shutil.rmtree(path, ignore_errors=True); os.makedirs(path)
    subprocess.run(['git', 'init', '-q', '-b', 'main', path], env=ENV, check=True, capture_output=True)
    g(path, 'config', 'gc.auto', '0')
    return path


def edit_cell(text, row_i, col_i, newval, pad):
    """Replace one cell in a padded or unpadded pipe table, preserving format."""
    lines = text.split('\n')
    tbl_idx = [i for i, l in enumerate(lines) if l.startswith('|')]
    li = tbl_idx[2 + row_i]
    cells = lines[li][1:-1].split('|')
    w = len(cells[col_i])
    if pad:
        cells[col_i] = (' ' + newval).ljust(w) if len(newval) + 1 <= w else ' ' + newval + ' '
    else:
        cells[col_i] = ' ' + newval + ' '
    lines[li] = '|' + '|'.join(cells) + '|'
    return '\n'.join(lines)


def repad(text):
    """Re-pad a whole pipe table so columns line up (what a conformant writer does)."""
    lines = text.split('\n')
    idx = [i for i, l in enumerate(lines) if l.startswith('|')]
    rows = [[c.strip() for c in lines[i][1:-1].split('|')] for i in idx]
    w = [0] * len(rows[0])
    for r in rows:
        for j, c in enumerate(r):
            w[j] = max(w[j], len(c))
    for k, i in enumerate(idx):
        lines[i] = '| ' + ' | '.join(c.ljust(w[j]) for j, c in enumerate(rows[k])) + ' |'
    return '\n'.join(lines)


def numstat(repo, path):
    o = g(repo, 'diff', '--numstat', '--', path).stdout.strip()
    if not o:
        return 0, 0
    a, d, _ = o.split('\t')
    return int(a), int(d)


results = {}

# ---------------------------------------------------------------- E1b
def e1b(sizes):
    rows = []
    for n in sizes:
        r = newrepo(os.path.join(WORK, f'tbl{n}'))
        p = os.path.join(r, 'data.tbl')
        text = gen.tbl_text(n)
        open(p, 'w').write(text)
        t_add, _ = timed(lambda: g(r, 'add', 'data.tbl'), 3)
        g(r, 'commit', '-qm', 'base')
        size_loose = int(g(r, 'count-objects', '-v').stdout.split('size: ')[1].split()[0]) * 1024

        # small edit: change one cell in the middle (value width unchanged)
        e = edit_cell(text, n // 2, 3, '999', pad=True)
        open(p, 'w').write(e)
        t_diff_small, _ = timed(lambda: g(r, 'diff', '--stat', '--', 'data.tbl'), 5)
        add_s, del_s = numstat(r, 'data.tbl')
        t_status, _ = timed(lambda: g(r, 'status', '--porcelain'), 5)
        g(r, 'checkout', '--', 'data.tbl')

        # row insertion in the middle
        lines = text.split('\n')
        ti = [i for i, l in enumerate(lines) if l.startswith('|')]
        mid = ti[2 + n // 2]
        newrow = lines[mid].replace('r_', 'r_ffff', 1)[:len(lines[mid])]
        lines.insert(mid, newrow)
        open(p, 'w').write('\n'.join(lines))
        t_diff_ins, _ = timed(lambda: g(r, 'diff', '--stat', '--', 'data.tbl'), 5)
        add_i, del_i = numstat(r, 'data.tbl')
        g(r, 'checkout', '--', 'data.tbl')

        # three-way merge: two branches editing distant rows
        g(r, 'checkout', '-qb', 'ours')
        open(p, 'w').write(edit_cell(text, 1, 3, '111', pad=True))
        g(r, 'commit', '-qam', 'ours')
        g(r, 'checkout', '-q', 'main')
        g(r, 'checkout', '-qb', 'theirs')
        open(p, 'w').write(edit_cell(text, n - 2, 3, '222', pad=True))
        g(r, 'commit', '-qam', 'theirs')
        g(r, 'checkout', '-q', 'ours')
        t0 = time.perf_counter()
        mres = g(r, 'merge', '--no-edit', 'theirs', check=False)
        t_merge = time.perf_counter() - t0
        merge_ok = mres.returncode == 0
        # merge-tree (server-side, what the design says the forge component uses)
        g(r, 'checkout', '-q', 'main')
        t_mt, _ = timed(lambda: g(r, 'merge-tree', '--write-tree', 'ours', 'theirs', check=False), 3)

        # 50 revisions of realistic editing
        g(r, 'checkout', '-q', 'main')
        rng = random.Random(11)
        L = text.split('\n')
        ti = [i for i, l in enumerate(L) if l.startswith('|')]
        t0 = time.perf_counter()
        for rev in range(50):
            for _ in range(max(1, n // 200)):
                li = ti[2 + rng.randrange(n)]
                cells = L[li][1:-1].split('|')
                w = len(cells[3]); v = ' ' + str(rng.randint(1, 500))
                cells[3] = v.ljust(w) if len(v) <= w else v + ' '
                L[li] = '|' + '|'.join(cells) + '|'
            open(p, 'w').write('\n'.join(L))
            g(r, 'commit', '-qam', f'rev{rev}')
        t_50 = time.perf_counter() - t0
        loose = int(g(r, 'count-objects', '-v').stdout.split('size: ')[1].split()[0]) * 1024
        t_gc, _ = timed(lambda: g(r, 'repack', '-adq'), 1)
        packsz = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(os.path.join(r, '.git'))
                     for f in fs)
        t_log, _ = timed(lambda: g(r, 'log', '--oneline', '--', 'data.tbl'), 3)
        rec = dict(n=n, file_mb=len(text.encode()) / 2**20, add_s=t_add,
                   blob_loose_kb=size_loose / 1024,
                   diff_small_s=t_diff_small, small_add=add_s, small_del=del_s,
                   diff_insert_s=t_diff_ins, ins_add=add_i, ins_del=del_i,
                   status_s=t_status, merge_s=t_merge, merge_ok=merge_ok,
                   merge_tree_s=t_mt, rev50_commit_s=t_50,
                   loose_after50_mb=loose / 2**20, packed_git_mb=packsz / 2**20,
                   log_file_s=t_log)
        rows.append(rec); print('E1b', json.dumps(rec), flush=True)
    return rows


# ---------------------------------------------------------------- E1c alignment
def e1c(sizes):
    rows = []
    for n in sizes:
        for pad in (True, False):
            r = newrepo(os.path.join(WORK, f'align{n}{int(pad)}'))
            p = os.path.join(r, 'data.tbl')
            # narrow column 'n' (single digit) so a widening value forces reflow
            text = gen.tbl_text(n, pad=pad)
            lines = text.split('\n')
            idx = [i for i, l in enumerate(lines) if l.startswith('|')]
            # append a narrow literal column with single-digit values
            rng = random.Random(5)
            for k, i in enumerate(idx):
                if k == 0: c = 'n'
                elif k == 1: c = '---'
                else: c = str(rng.randint(1, 9))
                lines[i] = lines[i] + (' %s |' % c)
            text = '\n'.join(lines)
            if pad: text = repad(text)
            open(p, 'w').write(text)
            g(r, 'add', '.'); g(r, 'commit', '-qm', 'base')
            base_bytes = len(text.encode())
            # change one cell in that narrow column: 9 -> 1000
            ncol = len(gen.LIT) + len(gen.COMP)
            e = edit_cell(text, n // 2, ncol, '1000', pad=pad)
            if pad: e = repad(e)          # a conformant writer re-pads
            open(p, 'w').write(e)
            add, dele = numstat(r, 'data.tbl')
            t_diff, _ = timed(lambda: g(r, 'diff', '--', 'data.tbl'), 3)
            difflen = len(g(r, 'diff', '--', 'data.tbl').stdout.encode())
            # and: does a MERGE of two such edits still work?
            g(r, 'checkout', '--', 'data.tbl')
            g(r, 'checkout', '-qb', 'ours')
            a = edit_cell(text, 2, ncol, '1000', pad=pad)
            if pad: a = repad(a)
            open(p, 'w').write(a); g(r, 'commit', '-qam', 'o')
            g(r, 'checkout', '-q', 'main'); g(r, 'checkout', '-qb', 'theirs')
            b = edit_cell(text, n - 3, 3, '777', pad=pad)
            if pad: b = repad(b)
            open(p, 'w').write(b); g(r, 'commit', '-qam', 't')
            g(r, 'checkout', '-q', 'ours')
            mres = g(r, 'merge', '--no-edit', 'theirs', check=False)
            conflicted = mres.returncode != 0
            g(r, 'merge', '--abort', check=False)
            # git object delta cost of the widening edit
            g(r, 'checkout', '-q', 'main')
            open(p, 'w').write(e); g(r, 'commit', '-qam', 'widen')
            g(r, 'repack', '-adq')
            packsz = sum(os.path.getsize(os.path.join(dp, f)) for dp, _, fs in os.walk(os.path.join(r, '.git'))
                         for f in fs)
            rec = dict(n=n, padded=pad, base_bytes=base_bytes, diff_add=add, diff_del=dele,
                       diff_bytes=difflen, diff_s=t_diff, merge_conflicted=conflicted,
                       pack_2rev_kb=packsz / 1024)
            rows.append(rec); print('E1c', json.dumps(rec), flush=True)
    return rows


# ---------------------------------------------------------------- E1d width
def e1d():
    rows = []
    for extra in (0, 44, 194):
        ncols = len(gen.LIT) + len(gen.COMP) + extra
        for pad in (True, False):
            text = gen.tbl_text(2000, pad=pad, ncols_extra=extra)
            lines = [l for l in text.split('\n') if l.startswith('|')]
            L = [len(l) for l in lines]
            r = newrepo(os.path.join(WORK, f'w{ncols}{int(pad)}'))
            p = os.path.join(r, 'data.tbl')
            open(p, 'w').write(text); g(r, 'add', '.'); g(r, 'commit', '-qm', 'b')
            e = edit_cell(text, 1000, 3, '999', pad=pad)
            open(p, 'w').write(e)
            d = g(r, 'diff', '--', 'data.tbl').stdout
            hunk = [l for l in d.split('\n') if l.startswith(('+', '-')) and not l.startswith(('+++', '---'))]
            rec = dict(ncols=ncols, padded=pad, max_line=max(L), median_line=statistics.median(L),
                       header_line=L[0], bytes_per_row=len(text.encode()) / 2000,
                       diff_line_len=max(len(x) for x in hunk) if hunk else 0,
                       diff_lines=len(hunk),
                       terminal_wraps_80=max(L) / 80, terminal_wraps_120=max(L) / 120)
            rows.append(rec); print('E1d', json.dumps(rec), flush=True)
    return rows


if __name__ == '__main__':
    which = sys.argv[1] if len(sys.argv) > 1 else 'all'
    sizes = [int(x) for x in sys.argv[2:]] or [1000, 10000, 100000]
    os.makedirs(WORK, exist_ok=True)
    res = {}
    if which in ('all', 'b'): res['e1b'] = e1b(sizes)
    if which in ('all', 'c'): res['e1c'] = e1c(sizes)
    if which in ('all', 'd'): res['e1d'] = e1d()
    json.dump(res, open(os.path.join(HERE, f'out/e1b_{which}.json'), 'w'), indent=1)
