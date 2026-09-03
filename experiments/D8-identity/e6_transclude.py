#!/usr/bin/env python3
"""D8-E6: transclusion blast radius + loud failure for prose references.

Three reference strategies, all through ONE address grammar (L5's):
   {{ src.md#name }}
   A. MATERIALISED  - the transcluded text is written into the referring file
   B. REFERENCE     - only the address is in the file; text resolved at render
Measure: (i) diff blast radius when the SOURCE is edited;
         (ii) behaviour when the target NAME disappears;
         (iii) behaviour when TWO blocks claim the same name.
"""
import os, re, subprocess, tempfile, shutil, sys

REGION = re.compile(r'^<!--\s*#([a-z0-9][a-z0-9-]*)\s*-->$', re.M)
REF    = re.compile(r'\{\{\s*([^\s#}]+)#([a-z0-9-]+)\s*\}\}')

def regions(text):
    """name -> [block text].  A named region is the block FOLLOWING a marker line."""
    out={}; lines=text.split('\n'); i=0
    while i < len(lines):
        m = REGION.match(lines[i].strip())
        if m:
            j=i+1
            while j<len(lines) and not lines[j].strip(): j+=1
            blk=[]
            while j<len(lines) and lines[j].strip() and not REGION.match(lines[j].strip()):
                blk.append(lines[j]); j+=1
            if blk: out.setdefault(m.group(1),[]).append('\n'.join(blk))
            i=j
        else: i+=1
    return out

def render(path, root, seen=()):
    txt = open(os.path.join(root,path),encoding='utf-8').read()
    def sub(m):
        tgt, name = m.group(1), m.group(2)
        key=(tgt,name)
        if key in seen: return f'**#REF!(cycle: {tgt}#{name})**'
        fp = os.path.join(root,tgt)
        if not os.path.exists(fp): return f'**#REF!(no such artifact: {tgt})**'
        r = regions(open(fp,encoding='utf-8').read())
        hits = r.get(name, [])
        if len(hits)==0: return f'**#REF!(no region `{name}` in {tgt})**'
        if len(hits)>1:  return f'**#REF!(region `{name}` declared {len(hits)}x in {tgt} — ambiguous)**'
        return hits[0]
    return REF.sub(sub, txt)

def sh(*a, cwd): return subprocess.run(a,cwd=cwd,capture_output=True,text=True)

d = tempfile.mkdtemp()
SRC = """# Safety policy

<!-- #scram-threshold -->
The reactor scram threshold is 4.2 sigma above baseline, measured over a
rolling 30-second window.

<!-- #hold-time -->
Hold time after scram is 600 seconds.
"""
open(os.path.join(d,'policy.md'),'w').write(SRC)
N=8
for i in range(N):
    open(os.path.join(d,f'proc{i}.md'),'w').write(
        f"# Procedure {i}\n\nBefore starting, confirm the limit.\n\n{{{{ policy.md#scram-threshold }}}}\n\nThen proceed.\n")
# materialised variants
for i in range(N):
    open(os.path.join(d,f'mat{i}.md'),'w').write(
        f"# Procedure {i}\n\nBefore starting, confirm the limit.\n\n"
        "The reactor scram threshold is 4.2 sigma above baseline, measured over a\nrolling 30-second window.\n\nThen proceed.\n")
sh('git','init','-q','.',cwd=d); sh('git','config','user.email','a@b.c',cwd=d); sh('git','config','user.name','x',cwd=d)
sh('git','add','-A',cwd=d); sh('git','commit','-qm','base',cwd=d)

print("== (i) BLAST RADIUS: edit the source sentence ==")
new = SRC.replace('4.2 sigma','3.8 sigma')
open(os.path.join(d,'policy.md'),'w').write(new)
for i in range(N):
    p=os.path.join(d,f'mat{i}.md'); t=open(p).read().replace('4.2 sigma','3.8 sigma'); open(p,'w').write(t)
print(sh('git','diff','--stat',cwd=d).stdout)
sh('git','checkout','--','.',cwd=d)

print("== (ii) LOUD FAILURE: the named region is deleted ==")
broken = SRC.replace('<!-- #scram-threshold -->\n','')
open(os.path.join(d,'policy.md'),'w').write(broken)
print(render('proc0.md', d))
print("   (materialised copy shows a STALE value instead:)")
print("   " + [l for l in open(os.path.join(d,'mat0.md')).read().split('\n') if 'sigma' in l][0])
sh('git','checkout','--','.',cwd=d)

print("== (iii) AMBIGUITY: two blocks claim the same name (scattered namespace) ==")
dup = SRC + "\n<!-- #scram-threshold -->\n\nEditorial note: the threshold was 4.2 sigma before 2019.\n"
open(os.path.join(d,'policy.md'),'w').write(dup)
print(render('proc0.md', d))
sh('git','checkout','--','.',cwd=d)

print("== (iv) does the duplicate NAME arise from a clean stock-git merge? ==")
sh('git','checkout','-qb','alice',cwd=d)
open(os.path.join(d,'policy.md'),'w').write(SRC.replace('<!-- #hold-time -->','<!-- #scram-threshold -->'))
sh('git','commit','-qam','alice renames a region',cwd=d)
sh('git','checkout','-q','master',cwd=d); sh('git','checkout','-qb','bob',cwd=d)
open(os.path.join(d,'proc1.md'),'a').write('\nBob adds a line.\n')
sh('git','commit','-qam','bob',cwd=d)
sh('git','checkout','-q','alice',cwd=d)
r=sh('git','merge','bob',cwd=d)
print(f"   merge exit={r.returncode}, markers={open(os.path.join(d,'policy.md')).read().count('<<<<<<<')}")
print("   render of proc0.md after the clean merge:")
print("   " + render('proc0.md', d).split('\n\n')[2].replace('\n','\n   '))
print("\nworkdir:", d)
