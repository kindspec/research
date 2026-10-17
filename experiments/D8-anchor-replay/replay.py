#!/usr/bin/env python3
"""How often does blockspec's anchor resolver refuse, or resolve wrongly, on real
document history? (blockspec adjudication 0003, section 12 item 1)

0003 section 12 names "a replay over real history that prices the refusals"
as the first thing that would reverse its design: the resolver adds refusals
(near-copy, refilled-gap, crowded-gap, twin and context rules, and the
alignment) whose rate on real edits is unknown. This replays real file
histories against the blockspec reference resolver, and grades each
resolution with D8's line oracle (see the README for how independent it is).

For each arm, each sampled file, and up to three sampled pairs of versions GAP
commits apart in that file's history:

- every paragraph of the earlier version with at least MINLEN characters
  gets a comment on a span of SPAN words from its middle, written as
  blockspec SPEC.md section 11.1 creates one (`prefix + span + suffix` must
  occur once in the paragraph, or no comment is made);
- the comment is resolved against the later version by the reference
  resolver (`blockspec.anchor.resolve`), with the earlier version as `base`;
- truth is D8's line oracle (`../D8-identity/anchor_eval2.py`, `line_oracle`),
  applied to paragraphs: difflib maps the earlier file's lines onto the
  later's. If at least half of the paragraph's non-blank lines survive, its
  target is the later paragraph holding most of them. If none survive and no
  later paragraph is 30% similar, it was deleted. Anything else is unknown
  and is not counted.

A comment is graded against the target:

- the span survives (it occurs exactly once in the target): `correct` if it
  resolves there, on that span; `loud` if it is refused, `DETACHED` or
  `ORPHANED`; `WRONG` if it resolves anywhere else;
- the span is gone from the target, or the paragraph was deleted: `correct`
  if loud, `WRONG` if it resolves;
- the span occurs more than once in the target, or the oracle is unknown:
  not counted.

`loud` where the span survives is the cost 0003 asks to price: a refusal of
text that is still there. It is reported with its status, and a refusal
with its reason.

Usage:
    python3 -I replay.py --blockspec PATH --clone NAME=PATH ... [--arm NAME] [--gap N]

with the clone names of ../D8-block-definitions/arms.json. Each clone must be
at its pin with no tracked changes. PATH for --blockspec is a blockspec
checkout; its commit is printed.
"""

import argparse
import difflib
import importlib
import json
import os
import random
import re
import subprocess
import sys
from collections import Counter

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))

MINLEN = 20
SPAN = 3
FILES = 60
PAIRS_PER_FILE = 3
SEED = 7
GAPS = (1, 5, 25)
LOUD = ("DETACHED", "ORPHANED")
RESOLVES = ("RESOLVED", "EDITED", "MOVED")


def git(repo, *args):
    """git's stdout as UTF-8, bytes for bytes: no newline translation."""
    out = subprocess.run(["git", "-C", repo, *args], capture_output=True, check=True).stdout
    return out.decode("utf-8")


def lines_of(text):
    """The reader's line split (blockspec document.py: `\\r\\n|\\r|\\n`), so a
    line index means the same line to the oracle and to the reader."""
    return re.split(r"\r\n|\r|\n", text)


def blob_id(text):
    import hashlib

    data = text.encode("utf-8")
    return hashlib.sha1(b"blob %d\0" % len(data) + data).hexdigest()


def load_blockspec(path):
    sys.path.insert(0, os.path.join(path, "reference"))
    a = importlib.import_module("blockspec.anchor")
    a.Refusal = importlib.import_module("blockspec.document").Refusal
    head = git(path, "rev-parse", "HEAD").strip()
    if git(path, "status", "--porcelain", "--untracked-files=no"):
        sys.exit(f"{path} has changes; the reference must be a commit")
    return a, a._default_reader(), head


def paragraphs(A, R, text):
    """The snapshot's paragraphs that carry source lines, or None when the
    reader refuses the document."""
    try:
        snap = A.Snapshot(R, text)
    except A.Refusal:
        return None, None
    return snap, [lf for lf in snap.leaves if lf.type == "p" and lf.node.lines]


def line_oracle(old, new, old_ps, new_ps):
    """D8's line oracle (anchor_eval2.line_oracle's rule), on paragraphs:
    for each old paragraph, ('SURVIVED', new index), ('DELETED', None) or
    ('UNKNOWN', None)."""
    li, lj = lines_of(old), lines_of(new)
    sm = difflib.SequenceMatcher(None, li, lj, autojunk=False)
    m = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            m[a + k] = b + k
    jj = {ln - 1: n for n, p in enumerate(new_ps) for ln, _ in p.node.lines}
    out = []
    for p in old_ps:
        mine = [ln - 1 for ln, _ in p.node.lines]
        nonblank = [L for L in mine if L < len(li) and li[L].strip()]
        if not nonblank:
            out.append(("UNKNOWN", None))
            continue
        mapped = [m[L] for L in nonblank if L in m]
        frac = len(mapped) / len(nonblank)
        if frac >= 0.5:
            tgt = Counter(jj[L] for L in mapped if L in jj)
            out.append(("SURVIVED", tgt.most_common(1)[0][0]) if tgt else ("UNKNOWN", None))
        elif frac == 0.0:
            best = max(
                (difflib.SequenceMatcher(None, p.text, x.text).ratio() for x in new_ps), default=0
            )
            out.append(("DELETED", None) if best < 0.3 else ("UNKNOWN", None))
        else:
            out.append(("UNKNOWN", None))
    return out


def make_comment(A, snap, leaf, text):
    """A comment on SPAN words from the middle of `leaf`, as section 11.1
    creates one, or None when no window's span and context are unique."""
    words = leaf.text.split()
    if len(words) < SPAN:
        return None
    mid = (len(words) - SPAN) // 2
    for start in sorted(range(len(words) - SPAN + 1), key=lambda i: abs(i - mid)):
        span = " ".join(words[start : start + SPAN])
        if leaf.text.count(span) != 1:
            continue
        s = leaf.text.index(span)
        e = s + len(span)
        pre, suf = leaf.text[max(0, s - A.CONTEXT) : s], leaf.text[e : e + A.CONTEXT]
        if len(A.occurrences(leaf.text, pre + span + suf)) != 1:
            continue
        nth = sum(x.key == leaf.key for x in snap.leaves[: leaf.index])
        an = A.Anchor(blob_id(text), leaf.type, nth, leaf.text, span, pre, suf, None)
        record = f"---\nanchor: {A.write_anchor(an)}\nkind: comment\nstatus: open\n---\n\nc.\n"
        return span, record
    return None


def grade(got, truth, span, new_ps):
    """`correct`, `loud`, `WRONG`, or None when the comment is not counted;
    and whether the span survives."""
    status = got["status"]
    resolved = status in RESOLVES
    if truth[0] == "DELETED":
        return ("WRONG" if resolved else "correct"), False
    if truth[0] != "SURVIVED":
        return None, False
    target = new_ps[truth[1]]
    n = target.text.count(span)
    if n > 1:
        return None, False
    if n == 0:
        return ("WRONG" if resolved else "correct"), False
    if not resolved:
        return "loud", True
    s, e = got["span"]
    if got["leaf"]["node"] == list(target.node.path) and target.text[s:e] == span:
        return "correct", True
    return "WRONG", True


def pairs_for(repo, f, gap, rnd):
    cs = [c for c in git(repo, "log", "--format=%H", "--reverse", "--", f).split("\n") if c]
    if len(cs) < gap + 1:
        return []
    starts = list(range(0, len(cs) - gap))
    rnd.shuffle(starts)
    return [(cs[i], cs[i + gap]) for i in sorted(starts[:PAIRS_PER_FILE])]


def run_arm(A, R, name, repo, pathspec, gap, wrongs):
    rnd = random.Random(SEED)
    files = [f for f in git(repo, "ls-files", "--", *pathspec.split()).split("\n") if f]
    rnd.shuffle(files)
    t = Counter()
    for f in files[:FILES]:
        for a, b in pairs_for(repo, f, gap, rnd):
            try:
                old, new = git(repo, "show", f"{a}:{f}"), git(repo, "show", f"{b}:{f}")
            except UnicodeDecodeError:
                t["pairs not UTF-8"] += 1
                continue
            t["pairs"] += 1
            snap, old_ps = paragraphs(A, R, old)
            _, new_ps = paragraphs(A, R, new)
            if old_ps is None:
                t["pairs whose earlier version the profile refuses"] += 1
                continue
            if new_ps is None:
                # every comment on it is REFUSED(not-in-profile), surviving text or not
                t["pairs whose later version the profile refuses"] += 1
                t["comments on them"] += sum(
                    1 for lf in old_ps if len(lf.text) >= MINLEN and make_comment(A, snap, lf, old)
                )
                continue
            for got, span in replay_pair(A, R, old, new, snap, old_ps, new_ps, t):
                if len(wrongs) < 20:
                    wrongs.append((name, gap, f, a[:8], b[:8], got["status"], span))
    return t


def replay_pair(A, R, old, new, snap, old_ps, new_ps, t):
    """Comment, resolve and grade every paragraph of one pair into `t`; the
    WRONG ones, as (resolution, span)."""
    wrong = []
    truths = line_oracle(old, new, old_ps, new_ps)
    for leaf, truth in zip(old_ps, truths):
        if len(leaf.text) < MINLEN:
            continue
        made = make_comment(A, snap, leaf, old)
        if made is None:
            t["no comment made"] += 1
            continue
        span, record = made
        path = "d.md.notes/01J00000000000000000000001.md"
        repo_in = {"tree": {"d.md": new, path: record}, "blobs": {blob_id(old): old}}
        repo_in["object_format"] = "sha1"
        got = A.resolve(repo_in, {"records": [path]}, R)["records"][path]
        t["comments"] += 1
        verdict, survives = grade(got, truth, span, new_ps)
        if verdict is None:
            t["not counted"] += 1
            t["not counted " + got["status"]] += 1
            continue
        t[verdict] += 1
        t["truth " + ("span survives" if survives else truth[0].lower())] += 1
        if survives:
            t["span survives"] += 1
            if verdict == "loud":
                t["loud " + got["status"]] += 1
        if verdict == "WRONG":
            wrong.append((got, span))
    return wrong


def pct(num, den):
    return f"{100 * num / den:.1f}%" if den else "-"


def rates(t):
    """Three rates of refusing text that survived, none of them a bound:
    among the comments the oracle places; as if every loud comment it does
    not place had surviving text; and as if, besides, every comment on a
    pair whose later version the profile refuses had surviving text (each
    of those resolves `REFUSED(not-in-profile)`)."""
    survives = t["span survives"]
    unplaced = sum(
        v for k, v in t.items() if k.startswith("not counted ") and k[12:] not in RESOLVES
    )
    profile = t["comments on them"]
    return (
        pct(t["loud"], survives),
        pct(t["loud"] + unplaced, survives + unplaced),
        pct(t["loud"] + unplaced + profile, survives + unplaced + profile),
        unplaced,
    )


def report(name, gap, t):
    survives = t["span survives"]
    placed, unplaced_rate, profile_rate, unplaced = rates(t)
    print(f"\n## {name} gap={gap}")
    for k in (
        "pairs",
        "pairs not UTF-8",
        "pairs whose earlier version the profile refuses",
        "pairs whose later version the profile refuses",
        "comments on them",
        "comments",
        "no comment made",
        "not counted",
    ):
        print(f"  {k}: {t[k]}")
    print(
        f"  counted: correct {t['correct']}, loud {t['loud']}, WRONG {t['WRONG']}; "
        f"span survives {survives}, loud among them {placed}"
    )
    for k, v in sorted((k, v) for k, v in t.items() if k.startswith("loud ")):
        print(f"    {k}: {v}")
    print(f"  as if every loud comment not counted had surviving text: {unplaced_rate} ({unplaced} more)")
    print(
        f"  and every comment on a pair whose later version the profile refuses: {profile_rate} "
        f"({t['comments on them']} more)"
    )
    for k, v in sorted((k, v) for k, v in t.items() if k.startswith("not counted ")):
        print(f"    {k}: {v}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--blockspec", required=True)
    ap.add_argument("--clone", action="append", default=[], metavar="NAME=PATH")
    ap.add_argument("--arm", action="append", default=[])
    ap.add_argument("--gap", action="append", type=int, default=[])
    args = ap.parse_args()
    A, R, head = load_blockspec(args.blockspec)
    clones = dict(c.split("=", 1) for c in args.clone)
    arms = json.load(open(os.path.join(HERE, "..", "D8-block-definitions", "arms.json")))["arms"]
    print(
        f"# replay.py: blockspec reference at {head[:12]}; MINLEN={MINLEN}, SPAN={SPAN}, "
        f"files={FILES}, pairs/file={PAIRS_PER_FILE}, seed={SEED}"
    )
    wrongs = []
    for arm in arms:
        if args.arm and arm["name"] not in args.arm:
            continue
        repo = clones.get(arm["clone"])
        if repo is None:
            continue
        pin = git(repo, "rev-parse", "HEAD").strip()
        if pin != arm["pin"] or git(repo, "status", "--porcelain", "--untracked-files=no"):
            sys.exit(f"{arm['name']}: {repo} is not at its pin {arm['pin'][:12]} or has changes")
        for gap in args.gap or GAPS:
            report(arm["name"], gap, run_arm(A, R, arm["name"], repo, arm["pathspec"], gap, wrongs))
    print("\n## WRONG, first 20")
    for w in wrongs:
        print("  " + " ".join(str(x) for x in w))


if __name__ == "__main__":
    main()
