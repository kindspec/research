"""Does a v1 reader that IGNORES an unknown construct also PRESERVE it?
Protobuf 3.5 restored unknown-field preservation precisely because proxies
doing read-modify-write were silently deleting data. Test the same hazard here.
"""
import sys, re
sys.path.insert(0,"/home/cam/repos_kindspec/working-git-backed-gws/experiments/D11-evolution")
from tbl import parse

V2 = """| id   | item   | qty | unit  | total = qty * unit |
| ---- | ------ | --: | ----: | -----------------: |
| r_1  | widget |  10 | 12.00 |                    |
| r_2  | gadget |  20 |  6.00 |                    |
%owner alice
%reviewed 2031-04-02

grand := sum(total)
"""

# Writer A: reconstruct from the parsed model (the natural implementation)
def write_from_model(text):
    h, rows, binds, ignored, unk = parse(text, "H")
    out = ["| " + " | ".join(h) + " |", "| " + " | ".join("---" for _ in h) + " |"]
    out += ["| " + " | ".join(r) + " |" for r in rows]
    out += [""] + [f"{k} := {v}" for k, v in binds.items()]
    return "\n".join(out) + "\n"

# Writer B: boundary edit -- locate the one line to change, splice, re-emit the rest verbatim
def write_by_splice(text, row_id, col, val):
    lines = text.splitlines(keepends=True)
    for i, ln in enumerate(lines):
        if ln.lstrip().startswith("|") and f" {row_id} " in ln:
            cells = ln.rstrip("\n").split("|")
            # cells[0] is "", header order: id item qty unit total
            cells[col] = f" {val:<5}"
            lines[i] = "|".join(cells) + "\n"
    return "".join(lines)

a = write_from_model(V2)
b = write_by_splice(V2, "r_1", 3, "11")

print("=== v2 input (a v1 reader does not understand %owner / %reviewed) ===")
print(V2)
print("=== Writer A: re-emit from the parsed model ===")
print(a)
print("annotations surviving:", re.findall(r"^%.*$", a, re.M) or "NONE  <-- DATA LOSS")
print()
print("=== Writer B: boundary splice (PASS5's 'parse boundaries, never re-emit') ===")
print(b)
print("annotations surviving:", re.findall(r"^%.*$", b, re.M))
print("lines changed vs input:", sum(1 for x,y in zip(V2.splitlines(), b.splitlines()) if x!=y))
