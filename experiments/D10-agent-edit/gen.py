import json, itertools, random
random.seed(7)
items=[("widget",10,12.00),("gadget",20,6.00),("sprocket",10,4.50),("flange",5,12.00),
       ("cog",20,6.00),("bracket",7,9.25),("washer",10,4.50),("bolt",5,12.00)]
# 1. line-oriented .tbl with named columns + key
tbl="| item     | qty | unit  | total = qty * unit |\n| -------- | --: | ----: | -----------------: |\n"
for n,q,u in items: tbl+=f"| {n:<8} | {q:>3} | {u:>5.2f} |                    |\n"
tbl+="\nkey := item\ngrand := sum(total)\n"
open("a_tbl.tbl","w").write(tbl)
# 2. nested JSON (Portable-Text / tldraw style)
doc={"type":"table","columns":[{"name":"item"},{"name":"qty"},{"name":"unit"},{"name":"total","formula":"qty*unit"}],
     "rows":[{"cells":[{"v":n},{"v":q},{"v":u},{"v":None}]} for n,q,u in items]}
open("b_nested.json","w").write(json.dumps(doc,indent=2)+"\n")
# 3. CSV
csv="item,qty,unit,total\n"+"".join(f"{n},{q},{u:.2f},=B{i+2}*C{i+2}\n" for i,(n,q,u) in enumerate(items))
open("c_a1.csv","w").write(csv)
# 4. YAML-ish nested
y="table:\n  columns:\n"
for c in ["item","qty","unit","total"]: y+=f"    - name: {c}\n"
y+="  rows:\n"
for n,q,u in items: y+=f"    - item: {n}\n      qty: {q}\n      unit: {u:.2f}\n      total: null\n"
open("d_nested.yaml","w").write(y)
