import json
# Task: change the `unit` of the row whose item is "flange" from 12.00 to 15.00.
def min_window(path, target_pred):
    lines=open(path).read().splitlines()
    idxs=[i for i,l in enumerate(lines) if target_pred(l)]
    out=[]
    for i in idxs:
        for w in range(1,len(lines)+1):          # grow window upward from the target line
            for start in range(max(0,i-w+1), i+1):
                blk="\n".join(lines[start:start+w])
                if blk.count("\n")+1!=w: continue
                if "\n".join(lines).count(blk)==1:
                    out.append((i+1,w,blk)); break
            else: continue
            break
    return out
print("TASK: set flange's unit price 12.00 -> 15.00")
print()
print("--- a_tbl.tbl : target line ---")
for ln,w,blk in min_window("a_tbl.tbl", lambda l: "flange" in l):
    print(f"  line {ln}: minimum unique anchor = {w} line(s)"); print("   ",repr(blk))
print()
print("--- b_nested.json : the value to change is `\"v\": 12.0` ---")
lines=open("b_nested.json").read().splitlines()
cands=[i for i,l in enumerate(lines) if l.strip().startswith('"v": 12.0')]
print(f"  lines containing the literal target value: {[i+1 for i in cands]}  ({len(cands)} ambiguous matches)")
for ln,w,blk in min_window("b_nested.json", lambda l: l.strip().startswith('"v": 12.0')):
    print(f"  line {ln}: minimum unique anchor = {w} line(s)")
print()
print("--- d_nested.yaml ---")
lines=open("d_nested.yaml").read().splitlines()
cands=[i for i,l in enumerate(lines) if l.strip()=="unit: 12.00"]
print(f"  lines equal to 'unit: 12.00': {[i+1 for i in cands]}  ({len(cands)} ambiguous matches)")
for ln,w,blk in min_window("d_nested.yaml", lambda l: l.strip()=="unit: 12.00"):
    print(f"  line {ln}: minimum unique anchor = {w} line(s)")
print()
print("--- c_a1.csv (line-oriented but POSITIONAL formulas) ---")
for ln,w,blk in min_window("c_a1.csv", lambda l: l.startswith("flange")):
    print(f"  line {ln}: minimum unique anchor = {w} line(s): {blk!r}")
