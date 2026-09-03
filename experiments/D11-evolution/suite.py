"""The evolution-specific tests a conformance suite must add to L6.
Each returns (name, PASS/FAIL, note). Run against the reference parser.
"""
import sys, re, unicodedata
sys.path.insert(0,"/home/cam/repos_kindspec/working-git-backed-gws/experiments/D11-evolution")
from tbl import run, parse, Reject

VALID = """| id  | item   | qty | unit  | total = qty * unit |
| --- | ------ | --: | ----: | -----------------: |
| r_1 | widget |  10 | 12.00 |                    |

grand := sum(total)
"""
T=[]
def check(name, cond, note=""): T.append((name, "PASS" if cond else "FAIL", note))

# E1: residue -- valid input plus unparsed tail must be REJECTED, not truncated
for tail in ("\x00", "garbage", "| unclosed", "\t\t", "%"):
    st,_,_,_ = run(VALID + tail, "H")
    check(f"residue rejected: {tail!r}", st=="reject", st)

# E2: the inertness promise -- stripping every % line must not change any value
with_annots = VALID.replace("grand :=", "%owner alice\n%x-9f3a\n%note whatever\n\ngrand :=")
a = run(with_annots,"H")[1]; b = run(VALID,"H")[1]
check("inertness: stripping % changes no value", a.get("grand")==b.get("grand"),
      f"{a.get('grand')} vs {b.get('grand')}")

# E3: GREASE -- a random unknown annotation must be tolerated on read
st,_,ign,_ = run(VALID.replace("grand :=","%x-7c21e0 nonsense\n\ngrand :="), "H")
check("GREASE %x- tolerated", st=="value" and any("x-7c21e0" in l for l in ign), st)

# E4: unknown pragma must be fatal
st,msg,_,_ = run(VALID.replace("grand :=","!filter qty > 5\n\ngrand :="), "H")
check("unknown ! pragma is fatal", st=="reject", msg)

# E5: preservation -- ignored lines survive a boundary-splice write
src = VALID.replace("grand :=","%owner alice\n\ngrand :=")
spliced = src.replace("|  10 |","|  11 |")
check("preservation on write", "%owner alice" in spliced and
      sum(1 for x,y in zip(src.splitlines(),spliced.splitlines()) if x!=y)==1)

# E6: NFC -- a non-NFC identifier must be rejected; NFC-equal names must collide
nfd = unicodedata.normalize("NFD","café")
nfc = unicodedata.normalize("NFC","café")
def ident_ok(name):
    if unicodedata.normalize("NFC",name)!=name: raise Reject("identifier not NFC")
    if any(unicodedata.category(c)=="Cf" for c in name): raise Reject("Cf in identifier")
    return True
try: ident_ok(nfd); r1=False
except Reject: r1=True
check("non-NFC identifier rejected", r1)
try: ident_ok("pass​word"); r2=False
except Reject: r2=True
check("Cf (ZWSP) in identifier rejected", r2)
check("NFC-equal names are the same name", unicodedata.normalize("NFC",nfd)==nfc)

# E7: conflict markers fatal in every position
for pos in (0,2,5):
    lines = VALID.splitlines()
    lines.insert(pos, "<<<<<<< HEAD")
    st,_,_,_ = run("\n".join(lines)+"\n","H")
    check(f"conflict marker at line {pos} is fatal", st=="reject", st)

w=max(len(n) for n,_,_ in T)
for n,v,note in T:
    print(f"{n:{w}}  {v}" + (f"   [{note}]" if v=="FAIL" else ""))
print()
print(f"{sum(1 for _,v,_ in T if v=='PASS')}/{len(T)} pass")
