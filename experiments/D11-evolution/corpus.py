"""Corpus of inputs a v1 reader meets over decades, with declared ground truth.

truth = Decimal   -> a correct value for `grand` exists; producing it is CORRECT,
                     producing anything else is SILENTLY WRONG, rejecting is SAFE-BUT-BLIND.
truth = None      -> no correct value exists; the ONLY correct outcome is reject.
"""
from decimal import Decimal as D

BASE_HEADER = """| id   | item   | qty | unit  | total = qty * unit |
| ---- | ------ | --: | ----: | -----------------: |
| r_1  | widget |  10 | 12.00 |                    |
| r_2  | gadget |  20 |  6.00 |                    |
"""
BASE_BIND = "grand := sum(total)\n"

CASES = [
    # name, kind, text, truth
    ("v1 baseline", "same-version",
     BASE_HEADER + "\n" + BASE_BIND, D("240.00")),

    ("v2 adds inert annotation (%owner)", "forward-compat",
     BASE_HEADER + "%owner alice\n%reviewed 2031-04-02\n\n" + BASE_BIND, D("240.00")),

    ("v2 adds unreferenced new binding (median)", "forward-compat",
     BASE_HEADER + "\n" + BASE_BIND + "midpoint := median(total)\n", D("240.00")),

    ("v2 adds evaluation pragma (!filter)", "forward-compat",
     BASE_HEADER + "!filter qty > 15\n\n" + BASE_BIND, D("120.00")),

    ("v2 adds evaluation pragma (!round-half-even)", "forward-compat",
     BASE_HEADER + "!round-half-even\n\n" + BASE_BIND, D("240.00")),

    ("v2 unknown fn feeds the aggregate", "forward-compat",
     BASE_HEADER + "\ngrand := sum(total) - median(qty)\n", D("225.00")),

    ("v2 semantic annotation (%unit-scale)", "forward-compat-TRAP",
     BASE_HEADER + "%unit-scale 1000\n\n" + BASE_BIND, D("240000.00")),

    ("git conflict markers", "corruption",
     BASE_HEADER.rstrip("\n") + "\n<<<<<<< HEAD\n| r_3 | sprocket | 8 | 15.00 | |\n=======\n| r_3 | sprocket | 16 | 15.00 | |\n>>>>>>> branch\n\n" + BASE_BIND, None),

    ("truncated mid-row", "corruption",
     BASE_HEADER.rstrip("\n")[:-14] + "\n" + BASE_BIND, None),

    ("duplicate binding from bad merge", "corruption",
     BASE_HEADER + "\ngrand := sum(total)\ngrand := sum(qty)\n", None),

    ("stray prose line (paste accident)", "corruption",
     BASE_HEADER + "TODO check these numbers with finance\n\n" + BASE_BIND, None),

    ("row with a dropped cell", "corruption",
     BASE_HEADER.replace("| r_2  | gadget |  20 |  6.00 |                    |",
                         "| r_2  | gadget |  20 |  6.00 |") + "\n" + BASE_BIND, None),
]
