#!/usr/bin/env python3
"""D8: how deep is each file's history, and which arms can the samples fill?

An arm at gap g needs a file with at least g+1 commits. The anchor harnesses
shuffle the corpus's .md files with random.Random(7) and keep the first 12
(anchor_eval.py) or 14 (anchor_eval2.py, anchor_eval3.py); the 12 are a prefix
of the 14. This prints the depth of every file in that sample and how many
files in the whole corpus are deep enough for each gap, so every `too few (N)`
and `pairs=0` line in results-anchor*.txt can be read against it.

Depth is `git log --format=%H -- <file>`, the list the harnesses walk.
Run from the directory holding corpora/, like anchor_eval3.py.
"""
import os, random, subprocess, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from corpus_pin import check

CORPORA = [('corpora/rust-book', 'src/*.md'), ('corpora/obsidian-help', 'en/*.md'), ('corpora/cmspec', '*.md')]
GAPS = (1, 5, 25)
SAMPLES = (12, 14)

def git(repo, *a):
    r = subprocess.run(['git', '-C', repo, *a], capture_output=True, text=True)
    if r.returncode != 0:
        sys.exit(f"git -C {repo} {' '.join(a)}: exit {r.returncode}: {r.stderr.strip()}")
    return r.stdout

check(*(r for r, _ in CORPORA))
for repo, glob in CORPORA:
    files = [f for f in git(repo, 'ls-files', glob).split('\n') if f.endswith('.md')]
    if not files:
        sys.exit(f"{repo}: no tracked .md files match {glob!r}; wrong corpus path?")
    depth = {f: len([c for c in git(repo, 'log', '--format=%H', '--', f).split('\n') if c]) for f in files}
    sample = list(files); random.Random(7).shuffle(sample)
    print(f"\n### {repo.split('/')[-1]}  {glob}  files={len(files)}  deepest={max(depth.values())}")
    print("   files with >= gap+1 commits, whole corpus:  "
          + "  ".join(f"gap={g}: {sum(d >= g + 1 for d in depth.values())}" for g in GAPS))
    for n in SAMPLES:
        s = sample[:n]
        print(f"   seed=7 sample of {n}: deepest={max(depth[f] for f in s)}  files with >= gap+1 commits:  "
              + "  ".join(f"gap={g}: {sum(depth[f] >= g + 1 for f in s)}" for g in GAPS))
    print("   sample of 14, in draw order (depth  file):")
    for f in sample[:14]:
        print(f"     {depth[f]:4d}  {f}")
