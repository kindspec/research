#!/usr/bin/env python3
"""Check red_states.py itself: break replay.py's grader, oracle and rates twelve ways,
each in a copy, and show red_states.py fails on every one. A break that does
not apply prints BROKEN, never a pass.

Usage:
    python3 -I red_sweep.py BLOCKSPEC_PATH
"""

import hashlib
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.dont_write_bytecode = True
src = Path(__file__).resolve().parent
BLOCKSPEC = sys.argv[1]
MUT = [
    ("grader ignores the span offset", " and target.text[s:e] == span:", ":"),
    ("a rewrapped span is gone", "if not any(span in flat(p.text) for p in new_ps)", "if not any(span in p.text for p in new_ps)"),
    ("gone counts as correct", '''    if truth[0] == "GONE":
        return ("WRONG" if resolved else "correct"), False''', '''    if truth[0] == "GONE":
        return "correct", False'''),
    ("oracle never says GONE", '            return ("GONE", None)', '            return ("UNKNOWN", None)'),
    ("oracle reads the span from the paragraph's first word", "g = first[i] + start", "g = first[i]"),
    ("oracle ignores whether the span's words are adjacent", "None not in got and got == list(range(got[0], got[0] + SPAN))", "None not in got"),
    ("oracle accepts a span split across paragraphs", "            if len(js) == 1:", "            if js:"),
    ("the gone test searches the earlier version", "span in flat(p.text) for p in new_ps", "span in flat(p.text) for p in old_ps"),
    ("loud counted as correct", '        return "loud", True', '        return "correct", True'),
    ("a span repeated in its target counted", "flat(target.text).count(span) > 1:", "flat(target.text).count(span) > 9:"),
    ("nth always 0", "        nth = sum(x.key == leaf.key for x in snap.leaves[: leaf.index])", "        nth = 0"),
    ("the unplaced rate counts resolving comments", "k[12:] not in RESOLVES", "k[12:] in RESOLVES"),
]
survived = []
for name, old, new in MUT:
    with tempfile.TemporaryDirectory() as t:
        d = Path(t) / "exp"; shutil.copytree(src, d, ignore=shutil.ignore_patterns("__pycache__"))
        shutil.copytree(src.parent / "D8-block-definitions", Path(t) / "D8-block-definitions")
        f = d / "replay.py"; text = f.read_text()
        if text.count(old) != 1:
            print(f"{name}: BROKEN (pattern occurs {text.count(old)} times)"); survived.append(name); continue
        before = hashlib.sha256(f.read_bytes()).digest(); f.write_text(text.replace(old, new))
        if hashlib.sha256(f.read_bytes()).digest() == before:
            print(f"{name}: BROKEN (file unchanged)"); survived.append(name); continue
        r = subprocess.run([sys.executable, "-I", str(d / "red_states.py"), "--blockspec", BLOCKSPEC], capture_output=True, text=True)
        fails = [l.split("  ")[1].strip() for l in r.stdout.splitlines() if l.startswith("FAIL")]
        print(f"{name}: exit {r.returncode}; failing states: {fails or r.stderr.strip()[-100:]}")
        if r.returncode == 0:
            survived.append(name)
print(f"{len(MUT) - len(survived)} of {len(MUT)} breaks caught")
sys.exit(1 if survived else 0)
