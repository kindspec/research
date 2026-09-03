#!/usr/bin/env python3
"""D8 v3: where do computed anchors go WRONG, and can a hardened policy drive
the SILENT-WRONG rate to zero by converting those cases into LOUD refusals?

Hardened policy (all must hold to accept a fuzzy anchor):
  H1 margin      : best ratio must beat runner-up by >= 0.15
  H2 context     : prefix+suffix similarity >= 0.30 (avg of the two)
  H3 entropy     : quote must carry >= 24 distinct chars OR >= 8 distinct words
                   (low-entropy blocks -- code fences, TOC lines, boilerplate --
                    are refused rather than guessed at)
"""
import sys, os, re, difflib, random
from collections import Counter
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from anchor_eval import git, blocks, anchor_of, inject_ids, merge3, conflict_regions, MARK, CTX
from anchor_eval2 import line_oracle

FUZZ=0.5; MARGIN=0.15; CTXMIN=0.30

def btype(c):
    if c.startswith('```') or c.startswith('~~~'): return 'code'
    if c.startswith('#'): return 'heading'
    if re.match(r'^\s*([-*+]|\d+[.)])\s', c): return 'list'
    if c.startswith('|'): return 'table'
    if c.startswith('<'): return 'html'
    return 'prose'

def entropy_ok(q):
    return len(set(q)) >= 24 or len(set(re.findall(r'\w+', q))) >= 8

def reanchor2(text, anc, cand, hard):
    q=anc['quote']
    hits=[i for i,b in enumerate(cand) if b['content']==q]
    if len(hits)==1: return 'EXACT', hits[0]
    def ctxscore(i):
        o=cand[i]['off']
        pre=text[max(0,o-CTX):o]; suf=text[o+len(cand[i]['content']):o+len(cand[i]['content'])+CTX]
        return (difflib.SequenceMatcher(None,pre,anc['prefix']).ratio()+
                difflib.SequenceMatcher(None,suf,anc['suffix']).ratio())/2
    if len(hits)>1:
        sc=sorted(((ctxscore(i),i) for i in hits), reverse=True)
        if len(sc)>1 and sc[0][0]-sc[1][0] < 0.05: return 'AMBIGUOUS', (None if hard else sc[0][1])
        return 'EXACT_CTX', sc[0][1]
    if hard and not entropy_ok(q): return 'REFUSED_LOWENTROPY', None
    cands=[]
    for i,b in enumerate(cand):
        r=difflib.SequenceMatcher(None,q,b['content']).ratio()
        if r>=FUZZ: cands.append((r,i))
    if not cands: return 'ORPHAN', None
    cands.sort(reverse=True)
    if hard:
        if len(cands)>1 and cands[0][0]-cands[1][0] < MARGIN: return 'REFUSED_MARGIN', None
        if ctxscore(cands[0][1]) < CTXMIN: return 'REFUSED_CONTEXT', None
    return 'FUZZY', cands[0][1]

def run(repo,glob,gap,sf=14,sb=30,seed=7):
    rnd=random.Random(seed); t=Counter(); pairs=0
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
            pairs+=1; orc=line_oracle(ti,tj,bi,bj)
            idx=list(range(len(bi))); rnd.shuffle(idx)
            for k in idx[:sb]:
                anc=anchor_of(ti,bi[k])
                if len(anc['quote'])<20: continue
                truth,tgt=orc[k]
                if truth=='UNKNOWN': t['skip']+=1; continue
                ty=btype(bi[k]['content']); t['EV']+=1; t['TY:'+ty]+=1
                for lab,hard in (('naive',False),('hard',True)):
                    st,hit=reanchor2(tj,anc,bj,hard)
                    ok = (hit==tgt) if truth=='SURVIVED' else (hit is None)
                    if hit is None and truth=='SURVIVED': cls='LOUD'
                    elif ok: cls='correct'
                    else: cls='WRONG'
                    t[f'{lab}:{cls}']+=1
                    if cls=='WRONG': t[f'{lab}:WRONG:{ty}']+=1
    return t,pairs

if __name__=='__main__':
    for repo,glob in [('corpora/rust-book','src/*.md'),('corpora/obsidian-help','en/*.md'),('corpora/cmspec','*.md')]:
        for gap in (5,25):
            try: t,p=run(repo,glob,gap)
            except Exception as e: print(repo,glob,gap,'ERR',e); continue
            ev=t['EV']
            if ev<50: print(f"### {os.path.basename(repo)} {glob} gap={gap}: too few ({ev})"); continue
            print(f"\n### {os.path.basename(repo)} {glob} gap={gap}  pairs={p}  oracle-confident anchors={ev}")
            print("   block types: "+" ".join(f"{k[3:]}={v}" for k,v in sorted(t.items()) if k.startswith('TY:')))
            for lab in ('naive','hard'):
                print(f"   {lab:<6} correct {100*t[lab+':correct']/ev:5.1f}%   LOUD-refusal {100*t[lab+':LOUD']/ev:5.1f}%   SILENT-WRONG {100*t[lab+':WRONG']/ev:5.2f}%  (n={t[lab+':WRONG']})"
                      + ("  by type: "+" ".join(f"{k.split(':')[2]}={v}" for k,v in sorted(t.items()) if k.startswith(lab+':WRONG:')) if t[lab+':WRONG'] else ""))
