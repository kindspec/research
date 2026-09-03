#!/usr/bin/env python3
"""D8-E9: link rot for NAME-based addressing.  How often does a heading slug
survive N commits of real editing?  And is it unique within its file?"""
import sys,os,re,random
from collections import Counter
sys.path.insert(0,'.')
from anchor_eval import git
def slugs(t):
    out=[]
    for m in re.finditer(r'^(#{1,6})\s+(.+?)\s*$', t, re.M):
        s=re.sub(r'[^\w\s-]','',m.group(2).lower()).strip().replace(' ','-')
        out.append(s)
    return out
print(f"{'corpus':<16}{'gap':>5}{'pairs':>7}{'headings':>10}{'survived':>12}{'renamed/gone':>14}")
for repo,glob in [('corpora/rust-book','src/*.md'),('corpora/obsidian-help','en/*.md')]:
    files=[f for f in git(repo,'ls-files',glob).split('\n') if f.endswith('.md')]
    rnd=random.Random(7); rnd.shuffle(files); files=files[:30]
    for gap in (1,5,25,100):
        tot=0; surv=0; pairs=0
        for f in files:
            cs=[c for c in git(repo,'log','--format=%H','--reverse','--',f).split('\n') if c]
            if len(cs)<gap+1: continue
            for st in range(0,len(cs)-gap,max(1,(len(cs)-gap)//3 or 1)):
                ti,tj=git(repo,'show',f'{cs[st]}:{f}'),git(repo,'show',f'{cs[st+gap]}:{f}')
                if not ti or not tj: continue
                a,b=slugs(ti),set(slugs(tj))
                if not a: continue
                pairs+=1; tot+=len(a); surv+=sum(1 for s in a if s in b)
        if tot: print(f"{os.path.basename(repo):<16}{gap:>5}{pairs:>7}{tot:>10}{100*surv/tot:>11.1f}%{100*(tot-surv)/tot:>13.1f}%")
# uniqueness of heading slugs within a file
print()
for repo,glob in [('corpora/rust-book','src/*.md'),('corpora/obsidian-help','en/*.md')]:
    files=[f for f in git(repo,'ls-files',glob).split('\n') if f.endswith('.md')]
    tot=0; dup=0; nf=0
    for f in files:
        p=os.path.join(repo,f)
        if not os.path.exists(p): continue
        nf+=1; s=slugs(open(p,encoding='utf-8').read()); c=Counter(s)
        tot+=len(s); dup+=sum(v for v in c.values() if v>1)
    print(f"{os.path.basename(repo):<16} files={nf:<4} headings={tot:<5} duplicate slug within a file: {dup} ({100*dup/max(1,tot):.2f}%)")
