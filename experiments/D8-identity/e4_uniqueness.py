#!/usr/bin/env python3
"""D8-E4: is a quote a UNIQUE key in real corpora?  If prose blocks are
textually unique, an exact-quote anchor needs no id to disambiguate."""
import sys, os, re, subprocess
from collections import Counter
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from anchor_eval import blocks, git
from anchor_eval3 import btype

for repo,glob in [('corpora/rust-book','src/*.md'),('corpora/obsidian-help','en/*.md'),('corpora/cmspec','*.md')]:
    files=[f for f in git(repo,'ls-files',glob).split('\n') if f.endswith('.md')]
    per_file_dup=Counter(); corpus=Counter(); tot=Counter(); nfiles=0
    for f in files:
        try: t=open(os.path.join(repo,f),encoding='utf-8').read()
        except Exception: continue
        nfiles+=1
        bs=[b for b in blocks(t) if len(b['content'])>=20]
        c=Counter(b['content'] for b in bs)
        for b in bs:
            ty=btype(b['content']); tot[ty]+=1
            if c[b['content']]>1: per_file_dup[ty]+=1
            corpus[b['content']]+=1
    cross=Counter()
    for f in files:
        try: t=open(os.path.join(repo,f),encoding='utf-8').read()
        except Exception: continue
        for b in blocks(t):
            if len(b['content'])>=20 and corpus[b['content']]>1: cross[btype(b['content'])]+=1
    print(f"\n### {os.path.basename(repo)}  files={nfiles}  blocks>=20ch={sum(tot.values())}")
    print(f"{'type':<9}{'n':>7}{'dup in same file':>19}{'dup anywhere in corpus':>25}")
    for ty in sorted(tot):
        n=tot[ty]
        print(f"{ty:<9}{n:>7}{per_file_dup[ty]:>10} ({100*per_file_dup[ty]/n:4.1f}%){cross[ty]:>14} ({100*cross[ty]/n:5.1f}%)")
