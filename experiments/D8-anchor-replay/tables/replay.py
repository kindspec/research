#!/usr/bin/env python3
# A copy of ../replay.py at research 95bfc44, changed only to place comments
# on table leaves (see README.md here):
#   - REPLAY_TYPES (default "p,table") names the leaf types the oracle and
#     the comments read; REPLAY_COMMENT_TYPES (default the same) narrows
#     which of them get a comment. Each comment is resolved alone, so a
#     comment's outcome does not depend on which others are placed.
#   - a table leaf is kept although its node has no `lines` (the original
#     filter, `lf.node.lines`, drops every table);
#   - each dumped comment carries its leaf `type`;
#   - HERE is the parent directory, so arms.json and heldout-arms.json are
#     read from where ../replay.py reads them;
#   - the first output line also names the types and the commented types.
# With REPLAY_TYPES=p, its gap=5 section for site-policy is byte-identical to
# that section of ../prereg5/regression/replay-site-policy.txt.
"""How often does blockspec's anchor resolver refuse, or resolve wrongly, on real
document history? (blockspec adjudication 0003, section 12 item 1)

0003 section 12 names "a replay over real history that prices the refusals"
as the first thing that would reverse its design: the resolver adds refusals
(near-copy, refilled-gap, crowded-gap, twin and context rules, and the
alignment) whose rate on real edits is unknown. This replays real file
histories against the blockspec reference resolver, and grades each
resolution with a word oracle (see the README for how independent it is).

For each arm, each sampled file, and up to three sampled pairs of versions GAP
commits apart in that file's history:

- every paragraph of the earlier version with at least MINLEN characters
  gets a comment on a span of SPAN words from its middle, written as
  blockspec SPEC.md section 11.1 creates one (`prefix + span + suffix` must
  occur once in the paragraph, or no comment is made);
- the comment is resolved against the later version by the reference
  resolver (`blockspec.anchor.resolve`), with the earlier version as `base`;
- truth is `word_oracle`: difflib matches the earlier version's paragraph
  words onto the later's. The span survives in the later paragraph its
  words all map to, in order and adjacent; it is gone when its words occur
  in order and adjacent in no later paragraph; anything else (a move, a
  copy) is unknown and is not counted.

A comment is graded against the target:

- the span survives (it occurs once in the target, whitespace aside):
  `correct` if it resolves there, on that span; `loud` if it is refused,
  `DETACHED` or `ORPHANED`; `WRONG` if it resolves anywhere else;
- the span is gone: `correct` if loud, `WRONG` if it resolves;
- the span occurs more than once in the target, or the oracle is unknown:
  not counted.

`loud` where the span survives is the cost 0003 asks to price: a refusal of
text that is still there. It is reported with its status, and a refusal
with its reason.

Usage:
    python3 -I replay.py --blockspec PATH --clone NAME=PATH ... [--arm NAME] [--gap N]
        [--dump JSONL]

with the clone names of ../D8-block-definitions/arms.json and heldout-arms.json. Each clone must be
at its pin with no tracked changes. PATH for --blockspec is a blockspec
checkout; its commit is printed.
"""

import argparse
import difflib
import importlib
import json
import os
import random
import subprocess
import sys
from collections import Counter

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

MINLEN = 20
SPAN = 3
FILES = 60
PAIRS_PER_FILE = 3
SEED = 7
GAPS = (1, 5, 25)
LOUD = ("DETACHED", "ORPHANED")
RESOLVES = ("RESOLVED", "EDITED", "MOVED")
ARMS = os.path.join(HERE, "..", "D8-block-definitions", "arms.json")
HELDOUT = os.path.join(HERE, "heldout-arms.json")
TYPES = tuple(os.environ.get("REPLAY_TYPES", "p,table").split(","))
COMMENT_TYPES = tuple(os.environ.get("REPLAY_COMMENT_TYPES", ",".join(TYPES)).split(","))


def load_arms():
    """D8's arms (`arms.json`), then the held-out arms (`heldout-arms.json`)."""
    arms = []
    for path in (ARMS, HELDOUT):
        with open(path, encoding="utf-8") as f:
            arms += json.load(f)["arms"]
    return arms


def git(repo, *args):
    """git's stdout as UTF-8, bytes for bytes: no newline translation."""
    out = subprocess.run(["git", "-C", repo, *args], capture_output=True, check=True).stdout
    return out.decode("utf-8")


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
    return snap, [lf for lf in snap.leaves if lf.type in TYPES and (lf.type == "table" or lf.node.lines)]


def word_oracle(old_ps, new_ps):
    """Truth for a comment's span, from difflib's matching of the earlier
    version's paragraph words onto the later's (both in document order).
    `truth(i, start, span)` for the span of SPAN words at word `start` of
    old paragraph `i` is ('SURVIVED', new index) when every word maps, in
    order and adjacent, into one later paragraph; ('GONE', None) when the
    span's words occur in order and adjacent in no later paragraph
    (`occurs`); and ('UNKNOWN', None) otherwise: the text is somewhere
    later, but not where the matching put it (a move, or a copy)."""
    ow = [(i, w) for i, p in enumerate(old_ps) for w in p.text.split()]
    nw = [(j, w) for j, p in enumerate(new_ps) for w in p.text.split()]
    sm = difflib.SequenceMatcher(None, [w for _, w in ow], [w for _, w in nw], autojunk=False)
    m = {}
    for a, b, n in sm.get_matching_blocks():
        for k in range(n):
            m[a + k] = b + k
    first = {}
    for g, (i, _) in enumerate(ow):
        first.setdefault(i, g)

    def truth(i, start, span):
        g = first[i] + start
        got = [m.get(g + k) for k in range(SPAN)]
        if None not in got and got == list(range(got[0], got[0] + SPAN)):
            js = {nw[x][0] for x in got}
            if len(js) == 1:
                return ("SURVIVED", js.pop())
        if not any(occurs(span, p.text) for p in new_ps):
            return ("GONE", None)
        return ("UNKNOWN", None)

    return truth


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
        return span, record, start
    return None


def flat(text):
    """Text with each run of whitespace one space: a soft line break inside
    a paragraph renders as a space, so a rewrapped span is the same text."""
    return " ".join(text.split())


def occurs(span, text):
    """How often `span`'s words occur in `text`, in order and adjacent:
    whitespace aside, and never inside a longer word."""
    words, want = text.split(), span.split()
    return sum(words[k : k + len(want)] == want for k in range(len(words) - len(want) + 1))


def grade(got, truth, span, new_ps):
    """`correct`, `loud`, `WRONG`, or None when the comment is not counted;
    and whether the span survives."""
    status = got["status"]
    resolved = status in RESOLVES
    if truth[0] == "GONE":
        return ("WRONG" if resolved else "correct"), False
    if truth[0] != "SURVIVED":
        return None, False
    target = new_ps[truth[1]]
    if occurs(span, target.text) > 1:
        return None, False
    if not resolved:
        return "loud", True
    s, e = got["span"]
    if got["leaf"]["node"] == list(target.node.path) and target.text[s:e] == span:
        return "correct", True
    return "WRONG", True


def versions(repo, f):
    """The commits of `git log --reverse -- f` since `f` last came to be: a
    commit that deletes it or moves it away has no version to compare, and
    the history before it is a file's history before a rename, which is not
    followed."""
    cs = [c for c in git(repo, "log", "--format=%H", "--reverse", "--", f).split("\n") if c]
    out = subprocess.run(["git", "-C", repo, "cat-file", "--batch-check"], capture_output=True, check=True,
                         input="".join(f"{c}:{f}\n" for c in cs).encode("utf-8")).stdout.decode("utf-8")
    held = [len(o.split()) == 3 and o.split()[1] == "blob" for o in out.splitlines()]
    if len(held) != len(cs):
        sys.exit(f"git cat-file gave {len(held)} answers for {len(cs)} commits of {f}")
    gone = [i for i, h in enumerate(held) if not h]
    return cs[gone[-1] + 1 :] if gone else cs


def pairs_for(repo, f, gap, rnd):
    cs = versions(repo, f)
    if len(cs) < gap + 1:
        return []
    starts = list(range(0, len(cs) - gap))
    rnd.shuffle(starts)
    return [(cs[i], cs[i + gap]) for i in sorted(starts[:PAIRS_PER_FILE])]


def run_arm(A, R, name, repo, pathspec, gap, wrongs, dump):
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
                for i, lf in enumerate(old_ps):
                    made = lf.type in COMMENT_TYPES and len(lf.text) >= MINLEN and make_comment(A, snap, lf, old)
                    if made:
                        t["comments on them"] += 1
                        dump.append({"arm": name, "gap": gap, "file": f, "a": a, "b": b, "para": i,
                                     "type": lf.type, "start": made[2], "span": made[0], "truth": None, "target": None,
                                     "status": "REFUSED(not-in-profile)", "resolved_to": None,
                                     "verdict": "profile"})
                continue
            log = []
            for got, span in replay_pair(A, R, old, new, snap, old_ps, new_ps, t, log):
                if len(wrongs) < 20:
                    wrongs.append((name, gap, f, a[:8], b[:8], got["status"], span))
            for row in log:
                dump.append({"arm": name, "gap": gap, "file": f, "a": a, "b": b, **row})
    return t


def replay_pair(A, R, old, new, snap, old_ps, new_ps, t, log=None):
    """Comment, resolve and grade every paragraph of one pair into `t`; the
    WRONG ones, as (resolution, span). Each comment is appended to `log`."""
    wrong = []
    truth_of = word_oracle(old_ps, new_ps)
    for i, leaf in enumerate(old_ps):
        if leaf.type not in COMMENT_TYPES or len(leaf.text) < MINLEN:
            continue
        made = make_comment(A, snap, leaf, old)
        if made is None:
            t["no comment made"] += 1
            continue
        span, record, start = made
        truth = truth_of(i, start, span)
        path = "d.md.notes/01J00000000000000000000001.md"
        repo_in = {"tree": {"d.md": new, path: record}, "blobs": {blob_id(old): old}}
        repo_in["object_format"] = "sha1"
        got = A.resolve(repo_in, {"records": [path]}, R)["records"][path]
        t["comments"] += 1
        verdict, survives = grade(got, truth, span, new_ps)
        if log is not None:
            to = next((j for j, x in enumerate(new_ps) if got["leaf"]
                       and list(x.node.path) == got["leaf"]["node"]), None)
            log.append({"para": i, "type": leaf.type, "start": start, "span": span, "truth": truth[0],
                        "target": truth[1], "status": got["status"], "resolved_to": to,
                        "verdict": verdict})
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
    ap.add_argument("--dump", metavar="JSONL", help="write every comment, one JSON line each")
    args = ap.parse_args()
    A, R, head = load_blockspec(args.blockspec)
    clones = dict(c.split("=", 1) for c in args.clone)
    arms = load_arms()
    print(
        f"# replay.py: blockspec reference at {head[:12]}; MINLEN={MINLEN}, SPAN={SPAN}, "
        f"files={FILES}, pairs/file={PAIRS_PER_FILE}, seed={SEED}, types={','.join(TYPES)}, comments on={','.join(COMMENT_TYPES)}"
    )
    wrongs, dump = [], []
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
            report(arm["name"], gap, run_arm(A, R, arm["name"], repo, arm["pathspec"], gap, wrongs, dump))
    if args.dump:
        with open(args.dump, "w", encoding="utf-8") as out:
            for row in dump:
                out.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("\n## WRONG, first 20")
    for w in wrongs:
        print("  " + " ".join(str(x) for x in w))


if __name__ == "__main__":
    main()
