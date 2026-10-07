#!/usr/bin/env python3
"""D8: print every silent-wrong that anchor_eval3.py counts.

anchor_eval3.py classifies each mis-anchor by type and discards it. This walks
the same arms with the same seed, sample and policies and prints each WRONG
case instead: arm, policy, type, file, the two commits, the quote anchored at
C_i and the block it resolved to at C_j. Quotes are cut at 70 characters, as
anchor_eval2.py's ex[...] lines are.

It is a copy of anchor_eval3.run()'s loop, so it checks itself: each arm's
oracle-confident count, per-policy WRONG count and per-policy, per-type
WRONG tally must equal what anchor_eval3.run() returns, or the script exits
non-zero. The printed cases themselves are checked only by diffing against
the committed results-anchor3-wrongs.txt.

Run from the directory holding corpora/, like anchor_eval3.py.
"""
import os, random, subprocess, sys
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anchor_eval import blocks, anchor_of
from anchor_eval2 import line_oracle
import anchor_eval3
from anchor_eval3 import reanchor2, btype

def git(repo, *a):
    r = subprocess.run(['git', '-C', repo, *a], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"git -C {repo} {' '.join(a)}: exit {r.returncode}: {r.stderr.strip()}")
    return r.stdout

def show(repo, rev, path):
    # `git log -- path` lists the commit that deletes or moves a file; the
    # harness reads that side as '' and skips the pair.
    if not git(repo, 'ls-tree', rev, '--', path).strip(): return ''
    return git(repo, 'show', f'{rev}:{path}')

def wrongs(repo, glob, gap, sf=14, sb=30, seed=7):
    rnd = random.Random(seed); t = Counter(); out = []
    files = [f for f in git(repo, 'ls-files', glob).split('\n') if f.endswith('.md')]
    if not files:
        sys.exit(f"{repo}: no tracked .md files match {glob!r}; wrong corpus path?")
    rnd.shuffle(files); files = files[:sf]
    for f in files:
        cs = [c for c in git(repo, 'log', '--format=%H', '--reverse', '--', f).split('\n') if c]
        if len(cs) < gap + 1: continue
        for start in range(0, len(cs) - gap, max(1, (len(cs) - gap) // 3 or 1)):
            ci, cj = cs[start], cs[start + gap]
            ti, tj = show(repo, ci, f), show(repo, cj, f)
            if not ti or not tj or ti == tj: continue
            bi, bj = blocks(ti), blocks(tj)
            if len(bi) < 4 or len(bj) < 4: continue
            orc = line_oracle(ti, tj, bi, bj)
            idx = list(range(len(bi))); rnd.shuffle(idx)
            for k in idx[:sb]:
                anc = anchor_of(ti, bi[k])
                if len(anc['quote']) < 20: continue
                truth, tgt = orc[k]
                if truth == 'UNKNOWN': continue
                ty = btype(bi[k]['content']); t['EV'] += 1
                for lab, hard in (('naive', False), ('hard', True)):
                    st, hit = reanchor2(tj, anc, bj, hard)
                    ok = (hit == tgt) if truth == 'SURVIVED' else (hit is None)
                    if (hit is None and truth == 'SURVIVED') or ok: continue
                    t[lab] += 1; t[f'{lab}:WRONG:{ty}'] += 1
                    out.append((lab, ty, st, truth, f, ci, cj, anc['quote'],
                                None if hit is None else bj[hit]['content']))
    return t, out

def clip(s, n=70):
    return None if s is None else s[:n]

if __name__ == '__main__':
    for repo, glob in [('corpora/rust-book', 'src/*.md'), ('corpora/obsidian-help', 'en/*.md'), ('corpora/cmspec', '*.md')]:
        for gap in (5, 25):
            t, out = wrongs(repo, glob, gap)
            ref, _ = anchor_eval3.run(repo, glob, gap)
            for key, mine in (('EV', t['EV']), ('naive:WRONG', t['naive']), ('hard:WRONG', t['hard'])):
                if mine != ref[key]:
                    sys.exit(f"{repo} gap={gap}: {key} {mine} here, {ref[key]} in anchor_eval3.run()")
            for key in sorted({k for k in (*t, *ref) if ':WRONG:' in k}):
                if t[key] != ref[key]:
                    sys.exit(f"{repo} gap={gap}: {key} {t[key]} here, {ref[key]} in anchor_eval3.run()")
            print(f"\n### {os.path.basename(repo)} {glob} gap={gap}  oracle-confident anchors={t['EV']}"
                  f"  naive WRONG={t['naive']}  hard WRONG={t['hard']}")
            for lab, ty, st, truth, f, ci, cj, q, h in out:
                print(f"   {lab:<5} {ty:<7} {st:<9} oracle={truth:<8} {f}  {ci[:8]}..{cj[:8]}")
                print(f"         {clip(q)!r}")
                print(f"      -> {clip(h)!r}")
