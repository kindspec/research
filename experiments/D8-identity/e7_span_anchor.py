#!/usr/bin/env python3
"""D8-E7: the STANDOFF SIDECAR case. A comment/tracked-change anchors to an
ARBITRARY CHARACTER SPAN inside a block -- the granularity the OHCO refutation
says a sidecar needs. Can quote+context anchoring hold such a span across real
edits, with no id in the file?

Anchor = W3C TextQuoteSelector (exact + prefix + suffix, 32 chars each, the
Hypothes.is convention) + TextPositionSelector as a hint.
Oracle: the SAME span located in the later version by the line-level oracle's
surviving block, then exact/near search within it.
"""
import sys,os,re,difflib,random
from collections import Counter
sys.path.insert(0,os.path.dirname(os.path.abspath(__file__)))
from anchor_eval import git, blocks
from anchor_eval2 import line_oracle

CTX=32
def spans_in(block, rnd, k=2):
    """pick k word-aligned spans of 4-12 words inside a block"""
    c=block['content']
    words=[m for m in re.finditer(r'\S+', c)]
    out=[]
    if len(words)<8: return out
    for _ in range(k):
        n=rnd.randint(4,min(12,len(words)-1)); i=rnd.randrange(0,len(words)-n)
        s,e=words[i].start(), words[i+n-1].end()
        out.append((s,e))
    return out

def anchor(text, off, s, e):
    a=off+s; b=off+e
    return {'exact':text[a:b],'prefix':text[max(0,a-CTX):a],'suffix':text[b:b+CTX],'start':a,'len':len(text)}

def find(text, anc, fuzzy=True):
    q=anc['exact']
    hits=[m.start() for m in re.finditer(re.escape(q), text)]
    if len(hits)==1: return 'EXACT', hits[0]
    if len(hits)>1:
        sc=sorted(((difflib.SequenceMatcher(None,text[max(0,h-CTX):h],anc['prefix']).ratio()
                   +difflib.SequenceMatcher(None,text[h+len(q):h+len(q)+CTX],anc['suffix']).ratio(), h) for h in hits), reverse=True)
        if sc[0][0]-sc[1][0] < 0.10: return 'AMBIGUOUS', None
        return 'EXACT_CTX', sc[0][1]
    if not fuzzy: return 'ORPHAN', None
    # fuzzy: slide a window, difflib on candidate substrings around anchor-relative position
    best=(0,None)
    L=len(q); step=max(1,L//4)
    guess=int(anc['start']/max(1,anc['len'])*len(text))
    lo=max(0,guess-4000); hi=min(len(text),guess+4000)
    for i in range(lo,max(lo+1,hi-L),step):
        r=difflib.SequenceMatcher(None,q,text[i:i+L]).quick_ratio()
        if r>best[0]:
            rr=difflib.SequenceMatcher(None,q,text[i:i+L]).ratio()
            if rr>best[0]: best=(rr,i)
    if best[0]>=0.7: return 'FUZZY', best[1]
    if best[0]>=0.5: return 'FUZZY_WEAK', best[1]
    return 'ORPHAN', None

def run(repo,glob,gap,sf=14,sb=20,seed=3):
    rnd=random.Random(seed); t=Counter()
    files=[f for f in git(repo,'ls-files',glob).split('\n') if f.endswith('.md')]
    rnd.shuffle(files); files=files[:sf]
    for f in files:
        cs=[c for c in git(repo,'log','--format=%H','--reverse','--',f).split('\n') if c]
        if len(cs)<gap+1: continue
        for start in range(0,len(cs)-gap,max(1,(len(cs)-gap)//3 or 1)):
            ti,tj=git(repo,'show',f'{cs[start]}:{f}'),git(repo,'show',f'{cs[start+gap]}:{f}')
            if not ti or not tj or ti==tj: continue
            bi,bj=blocks(ti),blocks(tj)
            if len(bi)<4 or len(bj)<4: continue
            orc=line_oracle(ti,tj,bi,bj)
            idx=[k for k in range(len(bi)) if orc[k][0]!='UNKNOWN']; rnd.shuffle(idx)
            for k in idx[:sb]:
                truth,tgt=orc[k]
                for (s,e) in spans_in(bi[k],rnd):
                    anc=anchor(ti,bi[k]['off'],s,e)
                    if len(anc['exact'])<25: continue
                    st,pos=find(tj,anc)
                    t['N']+=1; t['ST:'+st]+=1
                    if truth=='DELETED':
                        t['res:'+('correct_orphan' if pos is None else 'WRONG_on_deleted')]+=1
                    else:
                        if pos is None: t['res:loud_miss']+=1
                        else:
                            # correct iff the found position lies inside the oracle's target block
                            tb=bj[tgt]; lo=tb['off']; hi=lo+len(tb['content'])
                            t['res:'+('correct' if lo-2<=pos<=hi else 'WRONG_block')]+=1
    return t

for repo,glob in [('corpora/rust-book','src/*.md'),('corpora/obsidian-help','en/*.md')]:
    for gap in (5,25):
        t=run(repo,glob,gap); n=t['N']
        if n<40: print(f"### {os.path.basename(repo)} gap={gap}: too few"); continue
        print(f"\n### SUB-BLOCK SPAN anchoring — {os.path.basename(repo)} gap={gap}  spans={n}")
        print("   selector outcome: "+"  ".join(f"{k[3:]}={100*v/n:.1f}%" for k,v in sorted(t.items()) if k.startswith('ST:')))
        for k in ('correct','loud_miss','correct_orphan','WRONG_block','WRONG_on_deleted'):
            v=t['res:'+k]; print(f"     {k:<18}{v:5d}  {100*v/n:5.1f}%")
