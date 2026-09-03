import json
items=[("r_7f3a","widget",10,12.00),("r_9b21","gadget",20,6.00),("r_4c8e","sprocket",10,4.50),
       ("r_2d15","flange",5,12.00),("r_a604","cog",20,6.00),("r_ef37","bracket",7,9.25),
       ("r_1c9d","washer",10,4.50),("r_88b0","bolt",5,12.00)]
# R1 format: opaque id column + named columns + header formula
t="| id     | item     | qty | unit  | total = qty * unit |\n| ------ | -------- | --: | ----: | -----------------: |\n"
for i,n,q,u in items: t+=f"| {i} | {n:<8} | {q:>3} | {u:>5.2f} |                    |\n"
open("e_tbl_r1.tbl","w").write(t)
# same data as nested JSON WITH ids (steelman: give the nested form ids too)
doc={"type":"table","columns":[{"name":c} for c in ["item","qty","unit","total"]],
     "rows":[{"id":i,"cells":[{"v":n},{"v":q},{"v":u},{"v":None}]} for i,n,q,u in items]}
open("f_nested_id.json","w").write(json.dumps(doc,indent=2)+"\n")
# R6: prose, one sentence per line vs reflowed at 72 cols
import textwrap
sents=["Procurement totalled 660.00 against a plan of 500.00.",
 "The overage is concentrated in the widget line, which doubled in Q3.",
 "We reviewed the gadget contract and found no comparable increase.",
 "The flange order was placed twice and one instance has been cancelled.",
 "Finance has asked for a revised forecast before the board meeting.",
 "The overage is concentrated in the widget line, which doubled in Q3."]
open("g_prose_semantic.md","w").write("\n".join(sents)+"\n")
open("h_prose_wrapped.md","w").write(textwrap.fill(" ".join(sents),72)+"\n")
