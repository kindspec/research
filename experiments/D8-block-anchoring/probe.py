#!/usr/bin/env python3
"""Where markers and pipe tables land in the CommonMark tree.

Prints, for each input, the block tokens markdown-it-py 3.0.0 builds under
preset `commonmark` and under `commonmark` with GFM tables enabled, as
type@level, and the block constructors pandoc's `gfm` reader builds, when
pandoc is on PATH. Usage: python3 -I probe.py > probe.txt
"""
import re
import shutil
import subprocess
import sys

import markdown_it

if markdown_it.__version__ != "3.0.0":
    sys.exit(f"probe.py: markdown-it-py {markdown_it.__version__}, expected 3.0.0")
CM = markdown_it.MarkdownIt("commonmark")
GT = markdown_it.MarkdownIt("commonmark").enable("table")
SKIP = {"inline", "thead_open", "tbody_open", "tr_open", "th_open", "td_open"}
PANDOC = shutil.which("pandoc")

CASES = [
    ("marker, then list", "<!-- #x -->\n- one\n- two\n"),
    ("marker between items, column 0", "- one\n<!-- #x -->\n- two\n"),
    ("marker between items, indented", "- one\n  <!-- #x -->\n- two\n"),
    ("marker first in an item", "- <!-- #x -->\n  one\n- two\n"),
    ("marker before a nested list", "- one\n\n  <!-- #x -->\n  - a\n  - b\n"),
    ("region inside one item", "- one\n- <!-- #x:begin -->\n  two\n  <!-- #x:end -->\n- three\n"),
    ("region around one item, column 0", "- one\n<!-- #x:begin -->\n- two\n<!-- #x:end -->\n- three\n"),
    ("bullet character change", "- one\n- two\n* three\n"),
    ("table after a blank line", "Intro.\n\n| a | b |\n|---|---|\n| 1 | 2 |\n"),
    ("table right after a paragraph line", "Intro.\n| a | b |\n|---|---|\n| 1 | 2 |\n"),
    ("table without outer pipes", "a | b\n--|--\n1 | 2\n"),
    ("table in a list item", "- item\n\n  | a | b |\n  |---|---|\n  | 1 | 2 |\n"),
    ("marker, then table", "<!-- #t -->\n| a | b |\n|---|---|\n| 1 | 2 |\n"),
]


def toks(md, s):
    return " ".join(f"{t.type}@{t.level}" for t in md.parse(s)
                    if t.block and t.nesting >= 0 and t.type not in SKIP)


def pandoc(s):
    if not PANDOC:
        return "(pandoc not on PATH)"
    out = subprocess.run([PANDOC, "-f", "gfm", "-t", "native"], input=s,
                         capture_output=True, text=True, check=True).stdout
    return " ".join(re.findall(r"\b(Para|Plain|Table|BulletList|OrderedList|RawBlock|BlockQuote|CodeBlock|Header)\b", out))


if PANDOC:
    print("# " + subprocess.run([PANDOC, "--version"], capture_output=True, text=True).stdout.split("\n")[0])
print(f"# markdown-it-py {markdown_it.__version__}")
for name, s in CASES:
    print(f"\n{name}: {s!r}")
    print(f"  commonmark        {toks(CM, s)}")
    print(f"  commonmark+table  {toks(GT, s)}")
    print(f"  pandoc gfm        {pandoc(s)}")
