import bmerge2, blocks
# base has a paragraph; THEIRS adds a NEW block whose text duplicates it.
BASE   = "# A\n\nShared sentence.\n\n# B\n\nOther text.\n"
OURS   = BASE.replace("Other text.", "Other text, edited.")
THEIRS = BASE.replace("# B\n", "# B\n\nShared sentence.\n")
out, conflicts = bmerge2.m3(BASE, OURS, THEIRS)
n_base   = BASE.count("Shared sentence.")
n_theirs = THEIRS.count("Shared sentence.")
n_out    = out.count("Shared sentence.")
print(f"  occurrences  base={n_base}  theirs={n_theirs}  merged={n_out}")
print("  -> their added block was DROPPED" if n_out < n_theirs else "  -> preserved")
