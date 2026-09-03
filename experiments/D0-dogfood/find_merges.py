import subprocess, sys
repo, path = sys.argv[1], sys.argv[2]
def g(*a):
    return subprocess.run(["git","-C",repo,*a],capture_output=True,text=True).stdout.strip()
def blob(rev):
    out = subprocess.run(["git","-C",repo,"rev-parse",f"{rev}:{path}"],capture_output=True,text=True)
    return out.stdout.strip() if out.returncode==0 else None
merges = g("log","--full-history","--merges","--format=%H %P").splitlines()
real=[]
for line in merges:
    parts=line.split()
    h,ps=parts[0],parts[1:]
    if len(ps)!=2: continue
    bm=blob(h); b1=blob(ps[0]); b2=blob(ps[1])
    base=g("merge-base",ps[0],ps[1])
    if not base: continue
    bb=blob(base)
    if bb is None: continue
    if b1!=bb and b2!=bb:
        real.append((h,ps[0],ps[1],base,bb,b1,b2,bm))
print(f"{repo} {path}: {len(merges)} 2-parent merges, {len(real)} where BOTH sides changed the file")
for r in real[:40]:
    print("  ",r[0][:8],r[1][:8],r[2][:8],"base",r[3][:8])
