#!/usr/bin/env python3
"""W5-T4: the R1 red-team cases, fed to the SERVER (not to merge3 directly).

For EACH case the question is exactly three-valued:
    CORRECT   -- the server produced the right merge
    REFUSED   -- the server declined, loudly, and did not move the ref
    *** SILENTLY WRONG *** -- the server produced a plausible, wrong artifact

Stock git is run on the same inputs as a control.  Per PASS4/I6, the type-aware
merge may only improve the EXPERIENCE, never the CORRECTNESS: any case where the
server is worse than stock git is a failure of the whole approach.
"""
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gws_merge_server as S

WORK = os.path.join(HERE, "work-t4")
ENV = dict(os.environ, GIT_CONFIG_NOSYSTEM="1", GIT_AUTHOR_NAME="t",
           GIT_AUTHOR_EMAIL="t@t", GIT_COMMITTER_NAME="t", GIT_COMMITTER_EMAIL="t@t",
           HOME="/nonexistent", GIT_CONFIG_GLOBAL="/dev/null")
ZWSP = "​"

BASE = """| id     | item     | qty | unit  |
| ------ | -------- | --: | ----: |
| r_0001 | widget   |  10 | 12.00 |
| r_0002 | gadget   |  20 |  6.00 |
| r_0003 | sprocket |   8 | 15.00 |
| r_0004 | flange   |   5 | 24.00 |

grand := sum(qty)
"""


def git(*a, cwd=None, check=True):
    return subprocess.run(("git",) + a, cwd=cwd, env=ENV, check=check,
                          capture_output=True, text=True)


def build(name, base, ours, theirs, fname="b.tbl"):
    d = os.path.join(WORK, name)
    if os.path.exists(d):
        shutil.rmtree(d)
    os.makedirs(d)
    srv, dev = os.path.join(d, "srv.git"), os.path.join(d, "dev")
    git("init", "-q", "--bare", srv); git("init", "-q", dev)
    w = lambda t: open(os.path.join(dev, fname), "w").write(t)
    w(base); git("add", "-A", cwd=dev); git("commit", "-qm", "base", cwd=dev)
    git("branch", "-M", "main", cwd=dev); git("push", "-q", srv, "main", cwd=dev)
    git("checkout", "-q", "-b", "topic", cwd=dev); w(theirs)
    git("commit", "-qam", "theirs", cwd=dev); git("push", "-q", srv, "topic", cwd=dev)
    git("checkout", "-q", "main", cwd=dev); w(ours)
    git("commit", "-qam", "ours", cwd=dev); git("push", "-q", srv, "main", cwd=dev)
    return srv, dev


def stock(srv, fname="b.tbl"):
    """What the forge's merge button would produce."""
    p = git("merge-tree", "--write-tree", "main", "topic", cwd=srv, check=False)
    tree = p.stdout.splitlines()[0] if p.stdout else None
    txt = git("cat-file", "-p", f"{tree}:{fname}", cwd=srv, check=False).stdout if tree else ""
    return p.returncode, txt


def rows(txt):
    ls = [l for l in txt.splitlines() if l.strip().startswith("|")]
    if len(ls) < 2:
        return []
    cols = [c.strip() for c in ls[0].strip().strip("|").split("|")]
    return [dict(zip(cols, [c.strip() for c in l.strip().strip("|").split("|")]))
            for l in ls[2:]]


CASES = []
def case(fn):
    CASES.append(fn); return fn


# -------------------------------------------------------------- R1 T2a
@case
def t2a_duplicate_row_id():
    """Copy-paste duplicates a row id, then the copies diverge.
    R1: merge3 kept only the LAST r_0002 and rendered BOTH with qty=30. Wrong by 60."""
    ours = BASE.replace("| r_0002 | gadget   |  20 |  6.00 |\n",
                        "| r_0002 | gadget   |  20 |  6.00 |\n"
                        "| r_0002 | gadget2  |  30 |  6.00 |\n")
    theirs = BASE.replace("| r_0004 | flange   |   5 |", "| r_0004 | flange   |   6 |")
    return ("T2a duplicate row id (copy-paste)", BASE, ours, theirs,
            lambda txt: sum(int(r["qty"]) for r in rows(txt)) == 10 + 20 + 30 + 8 + 6)


@case
def t2b_both_mint_same_id():
    """Both branches independently mint r_0005.  Stock git keeps both (660).
    R1: merge3 kept ONE (560) -- a different answer, both 'clean'."""
    ours = BASE.replace("| r_0004 | flange   |   5 | 24.00 |\n",
                        "| r_0004 | flange   |   5 | 24.00 |\n"
                        "| r_0005 | bolt     |  10 |  8.00 |\n")
    theirs = BASE.replace("| r_0001 | widget   |  10 | 12.00 |\n",
                          "| r_0005 | cog      |   4 | 25.00 |\n"
                          "| r_0001 | widget   |  10 | 12.00 |\n")
    return ("T2b both sides mint the same id", BASE, ours, theirs, None)


@case
def t2c_invisible_char_id():
    """Bob retypes the id with a zero-width space.  Stock git CONFLICTS (correct).
    R1: merge3 saw delete+add and SILENTLY DROPPED Alice's edit."""
    ours = BASE.replace("| r_0002 | gadget   |  20 |", "| r_0002 | gadget   |  25 |")
    theirs = BASE.replace("| r_0002 | gadget   |  20 |",
                          f"| r_0002{ZWSP} | gadget   |  40 |")
    return ("T2c invisible character splits one row id", BASE, ours, theirs, None)


@case
def t1a_duplicate_aggregate():
    """Two authors add an aggregate with the SAME name at different offsets.
    R1: stock git merges CLEAN, one binding silently wins."""
    ours = BASE.replace("grand := sum(qty)\n", "grand := sum(qty)\nsubtotal := sum(qty)\n")
    theirs = BASE.replace("grand := sum(qty)\n", "subtotal := sum(unit)\ngrand := sum(qty)\n")
    return ("T1a duplicate AGGREGATE name", BASE, ours, theirs, None)


@case
def t1b_nfc_nfd_aggregate():
    """The two aggregate names differ only by Unicode normalisation.
    R1: clean merge; the NFD one does not even match the parser's regex."""
    nfc, nfd = "café", "café"
    ours = BASE.replace("grand := sum(qty)\n", f"grand := sum(qty)\n{nfc} := sum(qty)\n")
    theirs = BASE.replace("grand := sum(qty)\n", f"{nfd} := sum(unit)\ngrand := sum(qty)\n")
    return ("T1b NFC/NFD aggregate-name collision", BASE, ours, theirs, None)


@case
def t1c_nfc_nfd_column():
    nfc, nfd = "café", "café"
    ours = BASE.replace("| unit  |", f"| {nfc} |").replace("| ----: |", "| ----: |")
    theirs = BASE.replace("| unit  |", f"| {nfd} |")
    return ("T1c NFC/NFD COLUMN-name collision", BASE, ours, theirs, None)


@case
def column_renamed_one_side():
    """Alice renames 'unit' -> 'price'.  Bob edits a distant row.
    A rename is indistinguishable from add+delete in a line diff."""
    ours = BASE.replace("| unit  |", "| price |")
    theirs = BASE.replace("| r_0004 | flange   |   5 |", "| r_0004 | flange   |   6 |")
    return ("column RENAMED on one side", BASE, ours, theirs, None)


@case
def already_conflicted_file():
    """Someone committed a file that already contains conflict markers, then both
    sides edited around it.  Does the server merge a corpse?"""
    poisoned = BASE.replace(
        "| r_0002 | gadget   |  20 |  6.00 |\n",
        "<<<<<<< HEAD\n| r_0002 | gadget   |  20 |  6.00 |\n=======\n"
        "| r_0002 | gadget   |  99 |  6.00 |\n>>>>>>> other\n")
    ours = poisoned.replace("| r_0001 | widget   |  10 |", "| r_0001 | widget   |  11 |")
    theirs = poisoned.replace("| r_0003 | sprocket |   8 |", "| r_0003 | sprocket |   9 |")
    return ("input file is ALREADY CONFLICTED", poisoned, ours, theirs, None)


@case
def pipe_in_a_cell():
    """R1 a2: the grammar has no escaping rule.  One pipe shifts every field."""
    ours = BASE.replace("| r_0002 | gadget   |  20 |", "| r_0002 | gad|get  |  20 |")
    theirs = BASE.replace("| r_0004 | flange   |   5 |", "| r_0004 | flange   |   6 |")
    return ("unescaped PIPE inside a cell", BASE, ours, theirs, None)


@case
def clean_cell_level_merge():
    """The control: the case the whole design exists for.  MUST be CORRECT."""
    ours = BASE.replace("| r_0002 | gadget   |  20 |", "| r_0002 | gadget   |  25 |")
    theirs = BASE.replace("|  6.00 |", "|  6.50 |")
    return ("CONTROL: two cells on one line (the design's whole point)",
            BASE, ours, theirs,
            lambda t: [r for r in rows(t) if r["id"] == "r_0002"][0]["qty"] == "25"
            and [r for r in rows(t) if r["id"] == "r_0002"][0]["unit"] == "6.50")


@case
def row_deleted_vs_modified():
    ours = BASE.replace("| r_0003 | sprocket |   8 | 15.00 |\n", "")
    theirs = BASE.replace("| r_0003 | sprocket |   8 |", "| r_0003 | sprocket |  80 |")
    return ("row DELETED on one side, MODIFIED on the other", BASE, ours, theirs, None)


if __name__ == "__main__":
    if os.path.exists(WORK):
        shutil.rmtree(WORK)
    os.makedirs(WORK)
    verdicts = []
    for i, fn in enumerate(CASES):
        name, base, ours, theirs, check = fn()
        srv, dev = build(f"c{i}", base, ours, theirs)
        before = git("rev-parse", "main", cwd=srv).stdout.strip()
        grc, gtxt = stock(srv)
        r = S.merge(srv, "refs/heads/main", "refs/heads/topic")
        after = git("rev-parse", "main", cwd=srv).stdout.strip()
        moved = before != after
        merged = git("cat-file", "-p", "main:b.tbl", cwd=srv, check=False).stdout

        if r["status"] in ("merged",):
            if check is None:
                v = "MERGED (manual review below)"
            elif check(merged):
                v = "CORRECT"
            else:
                v = "*** SILENTLY WRONG ***"
        elif r["status"] in ("refused", "conflict"):
            v = "REFUSED" if not moved else "*** REFUSED BUT REF MOVED ***"
        else:
            v = r["status"].upper()

        print("=" * 74)
        print(f"### {name}")
        print("=" * 74)
        print(f"  stock git (the forge button): exit={grc} "
              f"markers={gtxt.count('<<<<<<<')}")
        for l in gtxt.splitlines()[:14]:
            print(f"      | {l}" if not l.startswith("|") else f"      {l}")
        print(f"  gws server: status={r['status']}")
        if r.get("reason"):
            print(f"      reason: {r['reason']}")
        if r.get("records"):
            for c in r["records"]:
                print(f"      conflict record: {c}")
        print(f"  ref moved: {moved}")
        if r["status"] == "merged":
            print("  --- artifact the server wrote ---")
            for l in merged.splitlines():
                print(f"      {l}")
        print(f"  VERDICT: {v}")
        print()
        verdicts.append((name, v, r["status"], grc))

    print("=" * 74)
    print("SUMMARY")
    print("=" * 74)
    for n, v, st, grc in verdicts:
        print(f"  {v:<32} {n}   [stock git exit={grc}]")
    wrong = [n for n, v, _, _ in verdicts if "SILENTLY WRONG" in v or "REF MOVED" in v]
    print()
    print("SILENTLY WRONG CASES:", wrong or "NONE")
