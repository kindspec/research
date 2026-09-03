"""OOXML mc:AlternateContent, transplanted: can a v2 WRITER downgrade for a v1 READER?

The mechanism must already exist in v1. Test both worlds.
"""
V1_GRAMMAR_WITHOUT_ALT = ["|row", ":=bind", "%annot", "!pragma"]
V1_GRAMMAR_WITH_ALT    = V1_GRAMMAR_WITHOUT_ALT + ["?alt"]

V2_FILE = """| id  | item   | qty | unit  |
| --- | ------ | --: | ----: |
| r_1 | widget |  10 | 12.00 |
? runningsum
!  running := runningsum(qty)
%  running := 10          # fallback: v1-expressible, materialised by the v2 writer
"""

def read(src, grammar):
    understood, chosen = [], None
    for ln in src.splitlines():
        s = ln.strip()
        if s.startswith("|"):  understood.append(("row", s)); continue
        if s.startswith("?"):
            if "?alt" not in grammar:
                return None, f"REJECT: line {s!r} -- v1 has no alternation construct"
            chosen = "pending"; continue
        if s.startswith("!"):
            if chosen == "pending":
                chosen = "skip-branch"; continue        # inside an alt: I don't know it, try next
            return None, f"REJECT: unknown pragma {s!r}"
        if s.startswith("%"):
            if chosen == "skip-branch":
                chosen = s; continue                    # fallback branch, v1-expressible
            continue                                    # plain annotation: ignore
    return chosen, "OK"

for name, g in (("v1 WITHOUT an alternation construct", V1_GRAMMAR_WITHOUT_ALT),
                ("v1 WITH   an alternation construct", V1_GRAMMAR_WITH_ALT)):
    r, msg = read(V2_FILE, g)
    print(f"{name:38} -> {msg}")
    if r: print(f"{'':38}    took fallback: {r}")
print()
print("Conclusion: the downgrade path is only available if the ALTERNATION MECHANISM")
print("shipped in v1. It cannot be retrofitted, because a v1 reader meeting it for the")
print("first time has no rule that says 'this thing means: try the next branch'.")
print("ECMA-376 shipped MCE as Part 3 alongside Part 1 for exactly this reason.")
