import sys
from decimal import Decimal
sys.path.insert(0, "/home/cam/repos_kindspec/working-git-backed-gws/experiments/D11-evolution")
from tbl import run
from corpus import CASES

POLICIES = [("P","permissive"),("S","strict-all"),("H","hybrid"),("D","demand-driven")]
tally = {p: {} for p,_ in POLICIES}

rows=[]
for name, kind, text, truth in CASES:
    out=[]
    for p,_ in POLICIES:
        status, payload, ignored, unk = run(text, p)
        if status == "crash":
            v = "CRASH"
        elif status == "reject":
            v = "SAFE-REJECT" if truth is None else "REFUSE"
        else:
            got = payload.get("grand")
            if truth is None: v = "SILENT-WRONG"
            elif isinstance(got, Decimal) and got == truth: v = "CORRECT"
            else: v = "SILENT-WRONG"
        tally[p][v] = tally[p].get(v,0)+1
        out.append(v)
    rows.append((name, "reject" if truth is None else str(truth), out))

w=46
print(f"{'case':{w}} {'truth':>10}  " + "  ".join(f"{n:<14}" for _,n in POLICIES))
print("-"*(w+14+4*16))
for name, t, out in rows:
    print(f"{name:{w}} {t:>10}  " + "  ".join(f"{c:<14}" for c in out))
print()
keys=["CORRECT","SILENT-WRONG","SAFE-REJECT","REFUSE","CRASH"]
print(f"{'policy':14}" + "".join(f"{k:>14}" for k in keys))
for p,n in POLICIES:
    print(f"{n:14}" + "".join(f"{tally[p].get(k,0):>14}" for k in keys))
print()
print("CORRECT     = produced the value the format's own semantics demand")
print("SILENT-WRONG= produced a number that is not the truth, with no error   <-- the category that matters")
print("SAFE-REJECT = refused a file that has no correct answer")
print("REFUSE      = refused a file that did have a correct answer (cost of caution, not a wrong answer)")
