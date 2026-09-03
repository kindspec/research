"""Migration by RENAME + verified rewrite (Raku's honesty + cargo fix's automation).

Rule under test: a breaking change gets a NEW SUFFIX. Old and new coexist in one
repo (type is the suffix, so this is free). The migration tool must not be trusted
-- it must be CHECKED, by evaluating both artifacts and comparing observable values.
"""
import sys, re
from decimal import Decimal
sys.path.insert(0,"/home/cam/repos_kindspec/working-git-backed-gws/experiments/D11-evolution")
from tbl import run

OLD = """| id  | item   | qty | unit  | total = qty * unit |
| --- | ------ | --: | ----: | -----------------: |
| r_1 | widget |  10 | 12.00 |                    |
| r_2 | gadget |  20 |  6.00 |                    |

grand := sum(total)
"""

def migrate(src):
    """v2 breaking change: bindings move from `name := expr` to `= name expr`."""
    return re.sub(r"^(\w[\w-]*)\s*:=\s*(.+)$", r"= \1 \2", src, flags=re.M)

def migrate_buggy(src):
    """A plausible bug: the regex also eats a `:=` appearing inside a cell."""
    return re.sub(r"(\w[\w-]*)\s*:=\s*(.+)", r"= \1 \2", src)

def eval_new(src):
    back = re.sub(r"^= (\w[\w-]*) (.+)$", r"\1 := \2", src, flags=re.M)
    return run(back, "H")[1]

old_vals = run(OLD, "H")[1]
for name, fn in (("correct migration", migrate), ("buggy migration", migrate_buggy)):
    new = fn(OLD)
    try:
        new_vals = eval_new(new)
    except Exception as e:
        new_vals = {"grand": f"<{e}>"}
    ok = old_vals.get("grand") == new_vals.get("grand")
    print(f"{name:20} old grand={old_vals.get('grand')}  new grand={new_vals.get('grand')}  "
          f"{'ACCEPT' if ok else 'REJECT MIGRATION'}")

print()
# the case a value check cannot catch: migration that preserves values but loses data
def migrate_lossy(src):
    return "\n".join(l for l in migrate(src).splitlines() if not l.startswith("%"))
SRC = OLD.replace("grand :=", "%owner alice\n\ngrand :=")
lossy = migrate_lossy(SRC)
print("values equal after lossy migration:",
      run(SRC,"H")[1].get("grand") == eval_new(lossy).get("grand"))
print("annotations lost:", "%owner" in SRC and "%owner" not in lossy)
print()
print("So the migration check needs TWO assertions, not one:")
print("  1. every derived value is unchanged        (semantic equivalence)")
print("  2. every byte not matched by a rewrite rule is present verbatim in the output")
print("     (a rewriter may only touch what it claims to touch)")
