"""DITA's class-ancestry specialization, transplanted to a line-oriented substrate.

DITA: <step class="- topic/li task/step "> -- a processor that never heard of
`step` reads the ancestry and processes it AS a `li`. Cheapest structural idea
available. Question: does it transplant?

Test it on both artifact kinds this design has: PROSE (a block) and COMPUTATION
(an aggregate).
"""
from decimal import Decimal

# --- PROSE: v2 invents a `warning` block, declaring ancestry to `blockquote`
V2_DOC = """::: warning {is=blockquote}
Do not deploy on a Friday.
:::
"""
def render_v1_doc(src):
    lines = src.splitlines()
    kind = lines[0].split()[1]
    anc  = lines[0].split("is=")[1].rstrip("}")
    body = "\n".join(lines[1:-1])
    known = {"blockquote", "paragraph"}
    if kind in known:
        return f"<{kind}>{body}</{kind}>", "exact"
    if anc in known:
        return f"<{anc}>{body}</{anc}>", "degraded-via-ancestry"
    return None, "reject"

out, how = render_v1_doc(V2_DOC)
print("PROSE  v1 renders a v2 `warning` block:")
print("   ", out, " [", how, "]")
print("    Is the result TRUE? yes -- a warning IS a blockquote. Loses emphasis, states nothing false.")
print()

# --- COMPUTATION: v2 invents `runningsum`, declaring ancestry to `sum`
COL = [Decimal("120.00"), Decimal("120.00"), Decimal("60.00")]
def sum_(c): return sum(c)
def runningsum(c):
    acc, out = Decimal(0), []
    for x in c: acc += x; out.append(acc)
    return out

print("COMPUTATION  `running :=[is=sum] runningsum(total)`   column =", [str(x) for x in COL])
print("    v2 (understands runningsum): ", [str(x) for x in runningsum(COL)])
print("    v1 degrading via ancestry  : ", sum_(COL))
print("    Is the result TRUE? NO. v1 prints a single scalar 300.00 where the")
print("    document asserts a per-row series. Same type, wrong value, no error.")
print()
print("VERDICT: ancestry fallback is sound when the ancestor's claim is IMPLIED by")
print("the descendant's claim (subtyping). Presentation specializations satisfy this;")
print("function specializations essentially never do. A `warning` IS-A blockquote.")
print("A `runningsum` is NOT-A sum.")
