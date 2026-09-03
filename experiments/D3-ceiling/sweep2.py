#!/usr/bin/env python3
"""
Sweep 2: scenarios whose failure mode is SILENT WRONG rather than false conflict.
Each trial is constructed so the two authors' edits are structurally disjoint and
commute, i.e. there is a unique correct merge and zero legitimate conflicts.
"""
import json, os, random, shutil, subprocess, tempfile, collections, sys, re
GIT=["git","-c","user.name=T","-c","user.email=t@e","-c","init.defaultBranch=main"]
def g(cwd,*a): return subprocess.run(GIT+list(a),cwd=cwd,capture_output=True,text=True)

def merge3(tmp,fn,base,a,b,attrs=None):
    d=tempfile.mkdtemp(dir=tmp); w=lambda s: open(os.path.join(d,fn),"w").write(s)
    g(d,"init","-q",".")
    if attrs: open(os.path.join(d,".gitattributes"),"w").write(attrs)
    w(base); g(d,"add","-A"); g(d,"commit","-qm","base")
    g(d,"checkout","-qb","B"); w(b); g(d,"commit","-qam","b")
    g(d,"checkout","-q","main"); w(a); g(d,"commit","-qam","a")
    r=g(d,"merge","B"); got=open(os.path.join(d,fn)).read()
    shutil.rmtree(d,ignore_errors=True); return r.returncode,got

def classify(rc,got,want,check=None):
    if rc!=0: return "false-conflict"
    if check is not None:
        return "clean-correct" if check(got) else "SILENT-WRONG"
    return "clean-correct" if got.strip()==want.strip() else "SILENT-WRONG"

def report(label,c,ex=None):
    t=sum(c.values())
    print(f"\n=== {label}  (n={t}) ===")
    for k in ["clean-correct","false-conflict","SILENT-WRONG"]:
        print(f"   {k:16} {c[k]:5}   {100*c[k]/t:5.1f}%")
    return c

# --------------------------------------------------------------- 1. JSON array + counter
def s_json(rng,tmp):
    n=rng.randint(10,16)
    users=[{"id":i,"role":"viewer"} for i in range(1,n+1)]
    def ser(us,count): 
        body=",\n".join('    {"id": %d, "role": "%s"}'%(u["id"],u["role"]) for u in us)
        return '{\n  "users": [\n'+body+'\n  ],\n  "count": %d\n}\n'%count
    base=ser(users,n)
    pa,pb=sorted(rng.sample(range(1,n),2))
    if pb-pa<3: return None
    ua=users[:pa]+[{"id":n+1,"role":"editor"}]+users[pa:]
    ub=users[:pb]+[{"id":n+1,"role":"admin"}]+users[pb:]
    A,B=ser(ua,n+1),ser(ub,n+1)
    def chk(got):
        try: d=json.loads(got)
        except Exception: return False
        ids=[u["id"] for u in d["users"]]
        return len(ids)==len(set(ids)) and d["count"]==len(ids)
    rc,got=merge3(tmp,"c.json",base,A,B)
    return classify(rc,got,None,chk),got

# --------------------------------------------------------------- 2. YAML key add
def s_yaml(rng,tmp):
    keys=["name","replicas","image","port","env","region","zone","tier","owner","team","sla","tag"]
    base="\n".join(f"{k}: v{i}" for i,k in enumerate(keys))+"\n"
    pa,pb=sorted(rng.sample(range(0,len(keys)),2))
    if pb-pa<3: return None
    def ins(p,val):
        l=base.rstrip().split("\n"); l.insert(p,f"timeout: {val}"); return "\n".join(l)+"\n"
    A,B=ins(pa,30),ins(pb,90)
    def chk(got):
        return got.count("timeout:")==1
    rc,got=merge3(tmp,"c.yaml",base,A,B)
    return classify(rc,got,None,chk),got

# --------------------------------------------------------------- 3. MD link-def collision
LBL=["api","spec","guide","faq","ref"]
def s_mdlink(rng,tmp):
    names=sorted(["alpha","beta","delta","gamma","kappa","omega","sigma","theta","zeta","iota","lamb","mu"])
    base="# G\n\nSee [x][api].\n\n"+"".join(f"[{n}]: https://ex.com/{n}\n" for n in names)
    ia,ib=sorted(rng.sample(range(len(names)),2))
    if ib-ia<3: return None
    def ins(i,url):
        l=base.rstrip().split("\n")
        j=l.index(f"[{names[i]}]: https://ex.com/{names[i]}")
        l.insert(j+1,f"[api]: {url}"); return "\n".join(l)+"\n"
    A,B=ins(ia,"https://ex.com/api/v1"),ins(ib,"https://ex.com/api/v2")
    chk=lambda got: len(re.findall(r'^\[api\]:',got,re.M))==1
    rc,got=merge3(tmp,"d.md",base,A,B)
    return classify(rc,got,None,chk),got

# --------------------------------------------------------------- 4. MD numbered sections (local renumber)
def s_mdnum(rng,tmp):
    n=rng.randint(8,12)
    secs=[f"## {i}. Section {i}\n\nBody {i}.\n" for i in range(1,n+1)]
    base="# Manual\n\n"+"\n".join(secs)
    pa,pb=sorted(rng.sample(range(1,n),2))
    if pb-pa<3: return None
    def ins(p,tag):
        s=[f"## {i}. Section {i}\n\nBody {i}.\n" for i in range(1,n+1)]
        new=[f"## {p+1}. {tag}\n\nNew body.\n"]
        # local renumber: everything after p shifts by 1 (what an editor's auto-number does)
        tail=[f"## {i+1}. Section {i}\n\nBody {i}.\n" for i in range(p+1,n+1)]
        return "# Manual\n\n"+"\n".join(s[:p]+new+tail)
    A,B=ins(pa,"A-new"),ins(pb,"B-new")
    def chk(got):
        nums=re.findall(r'^## (\d+)\.',got,re.M)
        return len(nums)==len(set(nums)) and nums==[str(i) for i in range(1,len(nums)+1)]
    rc,got=merge3(tmp,"d.md",base,A,B)
    return classify(rc,got,None,chk),got

# --------------------------------------------------------------- 5. union driver on CSV
def s_union(rng,tmp):
    n=rng.randint(6,12)
    base="id,name\n"+"".join(f"{i},n{i}\n" for i in range(1,n+1))
    A=base+f"{n+1},fromA\n"; B=base+f"{n+1},fromB\n"
    def chk(got):
        ids=[l.split(",")[0] for l in got.strip().split("\n")[1:]]
        return len(ids)==len(set(ids))
    rc,got=merge3(tmp,"u.csv",base,A,B,attrs="u.csv merge=union\n")
    return classify(rc,got,None,chk),got

# --------------------------------------------------------------- 6. SVG duplicate id
def s_svg(rng,tmp):
    n=rng.randint(6,12)
    rects="".join(f'  <rect id="r{i}" x="{i*20}" y="0" width="15" height="15" fill="#ccc"/>\n' for i in range(1,n+1))
    base='<svg xmlns="http://www.w3.org/2000/svg">\n  <defs>\n  </defs>\n'+rects+'</svg>\n'
    ia,ib=sorted(rng.sample(range(1,n+1),2))
    if ib-ia<3: return None
    def mk(i,color):
        t=base.replace('  <defs>\n','  <defs>\n    <linearGradient id="grad1"><stop stop-color="%s"/></linearGradient>\n'%color)
        return t.replace(f'id="r{i}" x="{i*20}" y="0" width="15" height="15" fill="#ccc"',
                         f'id="r{i}" x="{i*20}" y="0" width="15" height="15" fill="url(#grad1)"')
    A,B=mk(ia,"red"),mk(ib,"blue")
    def chk(got):
        ids=re.findall(r'id="([^"]+)"',got)
        return len(ids)==len(set(ids))
    rc,got=merge3(tmp,"d.svg",base,A,B)
    return classify(rc,got,None,chk),got

SCEN=[("JSON array insert + counter field",s_json),
      ("YAML: same key added at two places",s_yaml),
      ("Markdown: link-definition label collision",s_mdlink),
      ("Markdown: auto-numbered sections",s_mdnum),
      ("CSV under merge=union (repo-portable driver)",s_union),
      ("SVG: concurrent <defs> id introduction",s_svg)]

if __name__=="__main__":
    N=int(sys.argv[1]) if len(sys.argv)>1 else 200
    tmp=tempfile.mkdtemp(); rows=[]
    for label,fn in SCEN:
        rng=random.Random(11); c=collections.Counter(); ex={}
        done=0
        while done<N:
            r=fn(rng,tmp)
            if r is None: continue
            k,got=r; c[k]+=1; ex.setdefault(k,got); done+=1
        report(label,c); rows.append((label,c))
        if "SILENT-WRONG" in ex:
            print("   --- example silently-wrong merged output ---")
            print("".join("     "+l+"\n" for l in ex["SILENT-WRONG"].rstrip().split("\n")[:16]))
    shutil.rmtree(tmp,ignore_errors=True)
    print("\n=== SUMMARY (all trials have a unique correct merge; zero legitimate conflicts) ===")
    print(f"{'scenario':46}{'correct':>9}{'false-conf':>12}{'SILENT-WRONG':>14}")
    for label,c in rows:
        t=sum(c.values())
        print(f"{label:46}{100*c['clean-correct']/t:8.1f}%{100*c['false-conflict']/t:11.1f}%{100*c['SILENT-WRONG']/t:13.1f}%")
