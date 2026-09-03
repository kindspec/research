#!/usr/bin/env python3
"""gws merge server -- server-side, type-aware merge for a BARE git repository.

Why this exists: a bare repository does not consult .gitattributes, so a forge's
merge button runs stock git merge and silently corrupts structured artifacts.
Nothing inside the repo can prevent it.  The fix is a process that OWNS the
write:

    git merge-tree --write-tree   ->  merged tree + the three conflict stages
    type-aware merge on the blobs ->  merged bytes
    hash-object -w / write-tree   ->  new tree
    commit-tree -p ours -p theirs ->  a real merge commit
    update-ref <new> <old>        ->  compare-and-swap

A plain `git clone` with no .gitattributes, no merge config and none of our
tooling then receives a correct artifact.

Stdlib only.  Shells out to git.  Single file by design -- it is a security
boundary and it should be auditable in one sitting.

Usage:
    gws_merge_server.py merge --repo R.git --into refs/heads/main \\
                              --from refs/heads/topic [--message M]
    gws_merge_server.py conflicts --repo R.git
"""
from __future__ import annotations

import argparse
import contextlib
import fcntl
import json
import os
import re
import subprocess
import sys
import time
import unicodedata

# ---------------------------------------------------------------- policy knobs

MAX_BLOB_BYTES = 4 * 1024 * 1024   # refuse type-aware merge above this
MAX_CONFLICT_PATHS = 256           # refuse a merge touching more than this
MAX_ROWS = 50_000                  # refuse a .tbl with more rows than this
MAX_COLS = 512
GIT_TIMEOUT = 60                   # seconds, per git invocation
CAS_MAX_RETRIES = 50

REGULAR_MODES = {"100644", "100755"}   # anything else is not ours to merge

# zero-width / bidi / invisible characters that make two ids render identically
INVISIBLE = re.compile(
    "[­​-‏‪-‮⁠-⁤⁪-⁯﻿᠎]"
)


class Refuse(Exception):
    """A merge we decline to perform.  Loud, never silent."""


class GitError(Exception):
    pass


# ------------------------------------------------------------------ git plumbing

class Repo:
    def __init__(self, path):
        self.path = os.path.abspath(path)
        self.env = dict(os.environ)
        self.env.update(
            GIT_DIR=self.path,
            GIT_CONFIG_NOSYSTEM="1",
            GIT_TERMINAL_PROMPT="0",
            # the server's identity, never the requester's
            GIT_AUTHOR_NAME="gws-merge-server",
            GIT_AUTHOR_EMAIL="gws@localhost",
            GIT_COMMITTER_NAME="gws-merge-server",
            GIT_COMMITTER_EMAIL="gws@localhost",
        )
        self.env.pop("GIT_INDEX_FILE", None)
        self.env.pop("GIT_WORK_TREE", None)
        self.calls = 0

    def git(self, *args, input=None, check=True, text=True, env=None):
        self.calls += 1
        e = dict(self.env)
        if env:
            e.update(env)
        p = subprocess.run(
            ("git",) + args,
            cwd=self.path, env=e, input=input,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            text=text, timeout=GIT_TIMEOUT,
        )
        if check and p.returncode != 0:
            err = p.stderr if text else p.stderr.decode("utf8", "replace")
            raise GitError(f"git {' '.join(args)} -> {p.returncode}: {err.strip()}")
        return p

    def out(self, *args, **kw):
        return self.git(*args, **kw).stdout.strip()

    def rev(self, ref):
        p = self.git("rev-parse", "--verify", "--quiet", f"{ref}^{{commit}}", check=False)
        return p.stdout.strip() or None

    def cat(self, oid):
        return self.git("cat-file", "blob", oid, text=False).stdout

    def size(self, oid):
        return int(self.out("cat-file", "-s", oid))

    def is_ancestor(self, a, b):
        return self.git("merge-base", "--is-ancestor", a, b, check=False).returncode == 0


# ---------------------------------------------------- path / mode safety checks

def check_path(path: str):
    """A path we are willing to write.  The server is a privileged process on a
    shared repo; treat every path in a pushed tree as attacker-controlled."""
    if not path or path != path.strip("/"):
        raise Refuse(f"unsafe path (leading/trailing slash): {path!r}")
    if len(path) > 4096:
        raise Refuse("unsafe path (too long)")
    for ch in path:
        if ord(ch) < 0x20 or ch == "\x7f":
            raise Refuse(f"unsafe path (control character U+{ord(ch):04X}): {path!r}")
    parts = path.split("/")
    for p in parts:
        if p in ("", ".", ".."):
            raise Refuse(f"unsafe path component {p!r} in {path!r}")
        if p.lower() == ".git" or p.lower().startswith(".git."):
            raise Refuse(f"refusing to touch a .git path: {path!r}")
        if p.rstrip(" .") != p:          # NTFS trailing dot/space aliasing
            raise Refuse(f"unsafe path component {p!r} in {path!r}")
    if os.path.basename(path) == ".gitattributes":
        # merging this file changes how EVERY OTHER file merges.
        raise Refuse(f"refusing to auto-merge {path!r} (it governs merge policy)")
    if os.path.basename(path) in (".gitmodules",):
        raise Refuse(f"refusing to auto-merge {path!r}")
    return path


def check_mode(mode: str, path: str):
    if mode not in REGULAR_MODES:
        kind = {"120000": "symlink", "160000": "submodule/gitlink",
                "040000": "tree", "40000": "tree"}.get(mode, mode)
        raise Refuse(f"{path!r}: not a regular file ({kind}); no type-aware merge")


# =============================================================================
#  .tbl  --  entity-map merge, with the R1 red-team defects fixed by REFUSAL
# =============================================================================
#
# R1 (b1) found the original entity-map merger was LESS correct than stock git:
#   T2a duplicate row id  -> dict(entities) kept the LAST one, both rendered
#                            with the survivor's values.  Silent corruption.
#   T2b both sides mint the same id -> merger keeps one, git keeps both.
#   T2c an invisible char splits one id -> merger sees delete+add and SILENTLY
#                            DROPS one side's edit where git conflicted.
#
# The invariant `key := id` was declared and never enforced.  We enforce it at
# parse time, on ALL THREE stages, and refuse rather than guess.  Refusal is
# correct here: PASS4/I6 says a type-aware merge may improve the EXPERIENCE,
# never the CORRECTNESS.  A merger that cannot uphold that must decline.

CONFLICT_MARKERS = ("<<<<<<<", "=======", ">>>>>>>", "|||||||")
AGG_RE = re.compile(r"\s*(\S+)\s*:=\s*(.+?)\s*$")


def _cells(line: str):
    return [c.strip() for c in line.strip().strip("|").split("|")]


def _fold(s: str) -> str:
    """Two ids that a human cannot tell apart must not compare unequal."""
    return unicodedata.normalize("NFC", INVISIBLE.sub("", s)).casefold()


def tbl_parse(text: str, side: str):
    if "\x00" in text:
        raise Refuse(f"{side}: NUL byte in a .tbl (not text)")
    lines = text.split("\n")
    for n, l in enumerate(lines, 1):
        if l.startswith(CONFLICT_MARKERS):
            raise Refuse(f"{side}: line {n} already contains a conflict marker "
                         f"{l.split()[0]!r} -- input is already conflicted")
    if "\\|" in text:
        raise Refuse(f"{side}: escaped pipe -- the grammar defines no escaping "
                     f"rule (R1 a2); refusing rather than mis-splitting")

    tbl = [l for l in lines if l.strip().startswith("|")]
    tail = [l for l in lines if not l.strip().startswith("|")]
    if len(tbl) < 2:
        raise Refuse(f"{side}: no table found")
    if len(tbl) - 2 > MAX_ROWS:
        raise Refuse(f"{side}: {len(tbl)-2} rows exceeds MAX_ROWS={MAX_ROWS}")

    cols = _cells(tbl[0])
    align = dict(zip(cols, _cells(tbl[1])))   # GFM alignment is SEMANTIC; keep it
    # The column widths this file actually uses.  Re-rendering at MINIMAL width
    # rewrites every line of the table for a one-cell merge, which destroys
    # `git blame` and makes the merge unreviewable (W5-T9: 84 changed lines for
    # one changed cell).  Inherit the incoming widths instead.
    def _segw(line):
        r = line.strip()
        r = r[1:] if r.startswith("|") else r
        r = r[:-1] if r.endswith("|") else r
        return [len(seg) - 2 for seg in r.split("|")]
    widths = {c: len(c) for c in cols}
    for _l in tbl:                       # header, separator and every data row
        for c, wd in zip(cols, _segw(_l)):
            widths[c] = max(widths[c], wd)
    if len(cols) > MAX_COLS:
        raise Refuse(f"{side}: {len(cols)} columns exceeds MAX_COLS={MAX_COLS}")
    seen = {}
    for c in cols:
        f = _fold(c)
        if f in seen:
            raise Refuse(f"{side}: column {c!r} collides with {seen[f]!r} "
                         f"(after NFC + invisible-char folding)")
        seen[f] = c

    rows, keys = [], {}
    for n, l in enumerate(tbl[2:], 3):
        vals = _cells(l)
        if len(vals) > len(cols):
            raise Refuse(f"{side}: row {n} has {len(vals)} fields for {len(cols)} "
                         f"columns -- an unescaped '|' shifts every field (R1 a2)")
        vals += [""] * (len(cols) - len(vals))
        key = vals[0]
        if key == "":
            raise Refuse(f"{side}: row {n} has an empty key column")
        f = _fold(key)
        if f in keys:
            raise Refuse(
                f"{side}: duplicate row id {key!r} (also row {keys[f]}) -- "
                f"`key := id` is declared and violated; refusing (R1 T2a/T2b/T2c)")
        keys[f] = n
        if _fold(key) != key or key != unicodedata.normalize("NFC", key):
            # id that folds to something else: renders same, compares different
            raise Refuse(f"{side}: row id {ascii(key)} contains invisible or "
                         f"non-NFC characters -- refusing (R1 T2c)")
        rows.append((key, dict(zip(cols, vals))))

    aggs, agg_lines = [], {}
    for n, l in enumerate(tail, 1):
        if ":=" not in l:
            if l.strip() and not l.startswith(("#", " ")):
                pass  # free prose is allowed
            continue
        m = AGG_RE.match(l)
        if not m:
            raise Refuse(f"{side}: malformed aggregate declaration {l.strip()!r}")
        name, expr = m.group(1), m.group(2)
        f = _fold(name)
        if f in agg_lines:
            raise Refuse(f"{side}: duplicate aggregate name {name!r} (also "
                         f"{agg_lines[f]!r}) -- one binding silently wins (R1 T1a/T1b)")
        agg_lines[f] = name
        aggs.append((name, expr))
    prose = [l for l in tail if ":=" not in l]
    return cols, rows, aggs, prose, align, widths


def _sep(alignspec, width):
    """Rebuild a GFM alignment cell at `width`.  Alignment is semantic: silently
    turning '--:' into '---' left-aligns a numeric column in every renderer."""
    a = (alignspec or "").strip()
    lead, trail = a.startswith(":"), a.endswith(":") and len(a) > 1
    n = max(width, 3) - int(lead) - int(trail)
    return (":" if lead else "") + "-" * max(n, 1) + (":" if trail else "")


def _pad(v, width, alignspec):
    a = (alignspec or "").strip()
    if a.endswith(":") and not a.startswith(":"):
        return v.rjust(width)
    if a.startswith(":") and a.endswith(":") and len(a) > 1:
        return v.center(width)
    return v.ljust(width)


def tbl_render(cols, rows, aggs, prose, align, widths=None):
    widths = widths or {}
    w = [max([len(c), widths.get(c, 0)] + [len(d.get(c, "")) for _, d in rows])
         for c in cols]
    out = ["| " + " | ".join(_pad(c, w[i], align.get(c)) for i, c in enumerate(cols)) + " |",
           "| " + " | ".join(_sep(align.get(c), w[i]).ljust(w[i])
                             for i, c in enumerate(cols)) + " |"]
    for _, d in rows:
        out.append("| " + " | ".join(_pad(d.get(c, ""), w[i], align.get(c))
                                     for i, c in enumerate(cols)) + " |")
    body = "\n".join(out)
    tailtxt = "\n".join(f"{n} := {e}" for n, e in aggs)
    rest = "\n".join(l for l in prose if l.strip())
    parts = [body]
    if rest:
        parts.append(rest)
    if tailtxt:
        parts.append(tailtxt)
    return "\n\n".join(parts) + "\n"


def merge_seq(base, ours, theirs):
    """Merge ordered id lists: keep ours' order, apply both sides' ins/del."""
    res = [n for n in ours if not (n in base and n not in theirs)]
    for i, n in enumerate(theirs):
        if n in res or n in base:
            continue
        anchor = theirs[i - 1] if i else None
        res.insert(res.index(anchor) + 1 if anchor in res else len(res), n)
    return res


def merge_tbl(base_b: bytes, ours_b: bytes, theirs_b: bytes, path: str):
    """Returns (merged_bytes, [conflict dicts]).  Raises Refuse to decline."""
    for b, s in ((base_b, "base"), (ours_b, "ours"), (theirs_b, "theirs")):
        if len(b) > MAX_BLOB_BYTES:
            raise Refuse(f"{s}: {len(b)} bytes exceeds MAX_BLOB_BYTES")
    try:
        texts = [b.decode("utf-8") for b in (base_b, ours_b, theirs_b)]
    except UnicodeDecodeError as e:
        raise Refuse(f"not valid UTF-8: {e}")

    bc, be, ba, bp, bal, bw = tbl_parse(texts[0], "base")
    oc, oe, oa, op, oal, ow = tbl_parse(texts[1], "ours")
    tc, te, ta, tp, tal, tw = tbl_parse(texts[2], "theirs")

    conflicts = []

    # --- columns: union preserving order; a delete on one side removes it
    cols = list(oc)
    for i, c in enumerate(tc):
        if c not in cols:
            cols.insert(min(i, len(cols)), c)
    for c in bc:
        if (c not in oc) != (c not in tc):          # deleted on exactly one side
            if c in cols:
                cols.remove(c)
    if cols and cols[0] != bc[0] and bc[0] in (oc[0], tc[0]):
        cols.remove(bc[0]); cols.insert(0, bc[0])   # key column stays first
    # a column renamed on one side is an add+delete pair; that loses data, so say so
    added = [c for c in cols if c not in bc]
    removed = [c for c in bc if c not in cols]
    if added and removed:
        raise Refuse(f"column set changed by add({added}) and remove({removed}) "
                     f"on opposite sides -- indistinguishable from a rename; refusing")

    bd, od, td = dict(be), dict(oe), dict(te)
    names = merge_seq([n for n, _ in be], [n for n, _ in oe], [n for n, _ in te])

    # modify/delete MUST be detected over the BASE name set, not over `names`.
    # merge_seq drops a row deleted on either side before any conflict check can
    # see it, so doing this inside the row loop below is dead code and the
    # other side's edit is SILENTLY LOST -- worse than stock git, which
    # conflicts here.  (Found by W5-T4 "row DELETED vs MODIFIED".)
    for n, _ in be:
        inO, inT = n in od, n in td
        if inO and not inT and od[n] != bd[n]:
            conflicts.append(dict(kind="modify/delete", row=n,
                                  ours="modified", theirs="deleted"))
        elif inT and not inO and td[n] != bd[n]:
            conflicts.append(dict(kind="delete/modify", row=n,
                                  ours="deleted", theirs="modified"))

    rows = []
    for n in names:
        b, o, t = bd.get(n, {}), od.get(n, {}), td.get(n, {})
        d = {}
        for c in cols:
            bv, ov, tv = b.get(c, ""), o.get(c, ""), t.get(c, "")
            if ov == tv:
                d[c] = ov
            elif bv == ov:
                d[c] = tv
            elif bv == tv:
                d[c] = ov
            else:
                conflicts.append(dict(kind="cell", row=n, column=c,
                                      base=bv, ours=ov, theirs=tv))
                d[c] = ov
        rows.append((n, d))

    # --- aggregates: a second entity map (name -> expr), merged the same way
    bad, oad, tad = dict(ba), dict(oa), dict(ta)
    anames = merge_seq([n for n, _ in ba], [n for n, _ in oa], [n for n, _ in ta])
    aggs = []
    for n in anames:
        bv, ov, tv = bad.get(n), oad.get(n), tad.get(n)
        v = ov if ov is not None else tv
        if ov is not None and tv is not None and ov != tv:
            if bv == ov:
                v = tv
            elif bv == tv:
                v = ov
            else:
                conflicts.append(dict(kind="aggregate", name=n,
                                      base=bv, ours=ov, theirs=tv))
                v = ov
        aggs.append((n, v))

    prose = op if op != bp else (tp if tp != bp else bp)
    if op != bp and tp != bp and op != tp:
        conflicts.append(dict(kind="prose", note="trailing prose changed on both sides"))
    align = {}
    for c in cols:
        b, o, t = bal.get(c), oal.get(c), tal.get(c)
        v = o if o == t else (t if b == o else (o if b == t else o))
        if o is not None and t is not None and o != t and b != o and b != t:
            conflicts.append(dict(kind="alignment", column=c, base=b, ours=o, theirs=t))
        align[c] = v if v is not None else (o or t or b)
    widths = {c: max(ow.get(c, 0), tw.get(c, 0)) for c in cols}
    return tbl_render(cols, rows, aggs, prose, align, widths).encode(), conflicts


def validate_tbl(data: bytes, path: str):
    tbl_parse(data.decode("utf-8"), path)


MERGERS = {".tbl": merge_tbl}
VALIDATORS = {".tbl": validate_tbl}


def validate_result(repo: Repo, newtree: str, ours: str):
    """THE HOLE THIS CLOSES (W5-T4):  `git merge-tree` only reports paths where
    stock git FAILED.  Where stock git merges CLEANLY AND WRONGLY -- an
    unescaped pipe that shifts every field, a duplicated row id, a duplicate
    aggregate name, a file that already contained conflict markers -- there are
    no conflict stages, the type-aware merger is never invoked, and the server
    publishes stock git's wrong answer verbatim.

    Merging only the conflicted paths is therefore NOT sufficient.  The server
    must validate every path IT IS ABOUT TO PUBLISH that the merge changed."""
    p = repo.git("diff-tree", "-r", "-z", "--name-only", "--no-renames",
                 "--diff-filter=d",      # a path DELETED by the merge has nothing to validate
                 ours, newtree, check=False)
    if p.returncode != 0:
        return [f"cannot enumerate the resulting tree (malformed?): "
                f"{p.stderr.strip()[:200]}"]
    changed = p.stdout.split("\x00")
    problems = []
    for path in changed:
        if not path:
            continue
        v = VALIDATORS.get(os.path.splitext(path)[1])
        if v is None:
            continue
        try:
            check_path(path)
            oid = repo.out("rev-parse", f"{newtree}:{path}")
            if repo.size(oid) > MAX_BLOB_BYTES:
                raise Refuse(f"{path}: result exceeds MAX_BLOB_BYTES")
            v(repo.cat(oid), path)
        except Refuse as e:
            problems.append(f"post-merge validation: {e}")
        except UnicodeDecodeError as e:
            problems.append(f"post-merge validation: {path}: not UTF-8: {e}")
        except GitError as e:
            problems.append(f"post-merge validation: {path}: unreadable: {e}")
    return problems


# =============================================================================
#  the server
# =============================================================================

def parse_merge_tree(raw: bytes):
    """-z output: <tree>NUL then (mode SP oid SP stage TAB path NUL)* then NUL msgs"""
    fields = raw.split(b"\x00")
    tree = fields[0].decode()
    stages = {}          # path -> {stage: (mode, oid)}
    for f in fields[1:]:
        if not f or b"\t" not in f:
            continue      # the messages section (begins with an empty field)
        head, _, path = f.partition(b"\t")
        bits = head.split(b" ")
        if len(bits) != 3:
            continue
        mode, oid, stage = bits[0].decode(), bits[1].decode(), int(bits[2])
        stages.setdefault(path.decode("utf-8", "surrogateescape"), {})[stage] = (mode, oid)
    return tree, stages


TMPDIR = "gws-tmp"


def sweep_tmp(repo: Repo, max_age=3600):
    """A SIGKILL bypasses every finally block, so temp indexes leak into GIT_DIR.
    Unbounded growth in a bare repo is a real (if unglamorous) failure mode.
    Sweep on entry: the only safe garbage-collector for uncatchable death."""
    d = os.path.join(repo.path, TMPDIR)
    os.makedirs(d, exist_ok=True)
    now = time.time()
    for f in os.listdir(d):
        p = os.path.join(d, f)
        try:
            if now - os.stat(p).st_mtime > max_age:
                os.unlink(p)
        except OSError:
            pass
    return d


def write_tree_with(repo: Repo, base_tree: str, updates: dict, tmpindex: str):
    """New tree = base_tree with `updates` (path -> (mode, oid)) applied."""
    env = {"GIT_INDEX_FILE": tmpindex}
    if os.path.exists(tmpindex):
        os.unlink(tmpindex)
    repo.git("read-tree", base_tree, env=env)
    if updates:
        info = "".join(f"{m} {o}\t{p}\0" for p, (m, o) in updates.items())
        repo.git("update-index", "-z", "--add", "--index-info", input=info, env=env)
    t = repo.out("write-tree", env=env)
    try:
        os.unlink(tmpindex)
    except OSError:
        pass
    return t


def record_conflicts(repo: Repo, into: str, ours: str, theirs: str, records: list):
    """Conflicts as DATA in refs/gws/conflicts/<into>/<oursha> -- never markers."""
    if not records:
        return None
    doc = json.dumps(dict(schema="gws.conflict/1", ref=into, ours=ours,
                          theirs=theirs, at=int(time.time()),
                          conflicts=records), indent=1, sort_keys=True) + "\n"
    blob = repo.out("hash-object", "-w", "--stdin", input=doc)
    tree = repo.out("mktree", input=f"100644 blob {blob}\tconflicts.json\n")
    commit = repo.out("commit-tree", tree, "-m",
                      f"{len(records)} unresolved conflict(s) merging {theirs[:12]}")
    slug = into.replace("refs/heads/", "")
    ref = f"refs/gws/conflicts/{slug}/{ours[:12]}-{theirs[:12]}"
    repo.git("update-ref", ref, commit)
    return ref


def merge_once(repo: Repo, into: str, frm: str, message=None, policy="refuse"):
    """One CAS attempt.  Returns a result dict; 'retry' means the ref moved."""
    ours = repo.rev(into)
    theirs = repo.rev(frm)
    if theirs is None:
        return dict(status="error", reason=f"no such ref: {frm}")
    if ours is None:
        return dict(status="error", reason=f"no such ref: {into}")

    # --- idempotence: already merged is a no-op, not a duplicate commit
    if repo.is_ancestor(theirs, ours):
        return dict(status="already-merged", ref=into, commit=ours)
    if repo.is_ancestor(ours, theirs):
        # A fast-forward still PUBLISHES content the server has never inspected.
        # Skipping validation here was a real hole (W5-T5b): a client could push
        # a descendant commit containing a malformed tree or an invalid artifact
        # and the server would advance the branch to it untouched.
        problems = validate_result(repo, theirs, ours)
        if problems and policy == "refuse":
            return dict(status="refused", reason="fast-forward: " + "; ".join(problems))
        p = repo.git("update-ref", into, theirs, ours, check=False)
        if p.returncode != 0:
            return dict(status="retry")
        return dict(status="fast-forward", ref=into, commit=theirs)

    mt = repo.git("merge-tree", "-z", "--write-tree", "--messages", ours, theirs,
                  check=False, text=False)
    if mt.returncode < 0 or mt.returncode > 1:
        return dict(status="error", reason="merge-tree failed: " +
                    mt.stderr.decode("utf8", "replace").strip())
    tree, stages = parse_merge_tree(mt.stdout)
    clean = (mt.returncode == 0)

    if len(stages) > MAX_CONFLICT_PATHS:
        return dict(status="refused",
                    reason=f"{len(stages)} conflicted paths > MAX_CONFLICT_PATHS")

    updates, records, refusals = {}, [], []
    for path, st in sorted(stages.items()):
        try:
            check_path(path)
            if set(st) != {1, 2, 3}:
                raise Refuse(f"{path}: add/add or delete conflict "
                             f"(stages {sorted(st)}); no type-aware merge")
            for s in (1, 2, 3):
                check_mode(st[s][0], path)
            suffix = os.path.splitext(path)[1]
            fn = MERGERS.get(suffix)
            if fn is None:
                raise Refuse(f"{path}: no type-aware merger for {suffix!r}")
            for s in (1, 2, 3):
                if repo.size(st[s][1]) > MAX_BLOB_BYTES:
                    raise Refuse(f"{path}: stage {s} blob exceeds MAX_BLOB_BYTES")
            merged, cf = fn(repo.cat(st[1][1]), repo.cat(st[2][1]),
                            repo.cat(st[3][1]), path)
            oid = repo.git("hash-object", "-w", "-t", "blob", "--stdin",
                           input=merged, text=False).stdout.decode().strip()
            updates[path] = (st[2][0], oid)
            for c in cf:
                c["path"] = path
            records += cf
        except Refuse as e:
            refusals.append(str(e))

    if refusals and policy == "refuse":
        return dict(status="refused", reason="; ".join(refusals),
                    conflicted=sorted(stages))
    if records and policy == "refuse":
        # unresolvable cell conflicts: do NOT write "ours" and call it a merge.
        # That is a silent lost update for anyone who does not fetch refs/gws/*.
        ref = record_conflicts(repo, into, ours, theirs, records)
        return dict(status="conflict", reason=f"{len(records)} unresolved",
                    conflict_ref=ref, records=records)

    newtree = write_tree_with(repo, tree, updates,
                              os.path.join(sweep_tmp(repo),
                                           f"index-{os.getpid()}-{time.time_ns()}"))
    problems = validate_result(repo, newtree, ours)
    if problems and policy == "refuse":
        return dict(status="refused", reason="; ".join(problems), tree=newtree)
    msg = message or f"Merge {frm} into {into} (gws type-aware)"
    if records:
        msg += f"\n\n{len(records)} unresolved conflict(s) recorded in refs/gws/conflicts."
    commit = repo.out("commit-tree", newtree, "-p", ours, "-p", theirs, "-m", msg)
    p = repo.git("update-ref", into, commit, ours, check=False)   # <-- the CAS
    if p.returncode != 0:
        return dict(status="retry", detail=p.stderr.strip())
    ref = record_conflicts(repo, into, ours, theirs, records) if records else None
    return dict(status="merged", ref=into, commit=commit, tree=newtree,
                resolved=sorted(updates), unresolved=len(records), conflict_ref=ref,
                clean_from_git=clean)


@contextlib.contextmanager
def ref_queue(repo_path, into, enabled):
    """§5.3: one standing owner per repo with a per-ref queue.  flock() turns a
    thundering herd of CAS retries into an ordered queue.  In a real server this
    is an in-process asyncio lock; flock models it across processes."""
    if not enabled:
        yield
        return
    lock = os.path.join(repo_path, "gws-queue." + into.replace("/", "_") + ".lock")
    fd = os.open(lock, os.O_CREAT | os.O_RDWR, 0o600)
    try:
        fcntl.flock(fd, fcntl.LOCK_EX)
        yield
    finally:
        fcntl.flock(fd, fcntl.LOCK_UN)
        os.close(fd)


def merge(repo_path, into, frm, message=None, policy="refuse",
          max_retries=CAS_MAX_RETRIES, queue=False):
    """A server must never turn a bad request into a crash: an unexpected
    exception is a REFUSAL, and the ref is left exactly where it was."""
    try:
        with ref_queue(os.path.abspath(repo_path), into, queue):
            return _merge(repo_path, into, frm, message, policy, max_retries)
    except Refuse as e:
        return dict(status="refused", reason=str(e))
    except (GitError, subprocess.TimeoutExpired, UnicodeDecodeError,
            OSError, ValueError) as e:
        return dict(status="refused", reason=f"{type(e).__name__}: {str(e)[:500]}")


def _merge(repo_path, into, frm, message, policy, max_retries):
    repo = Repo(repo_path)
    delay = 0.002
    for attempt in range(max_retries):
        r = merge_once(repo, into, frm, message, policy)
        if r["status"] != "retry":
            r["attempts"] = attempt + 1
            r["git_calls"] = repo.calls
            return r
        time.sleep(delay * (1 + os.getpid() % 7) * 0.1)
        delay = min(delay * 1.7, 0.25)
    return dict(status="error", reason="CAS livelock", attempts=max_retries)


def main(argv=None):
    ap = argparse.ArgumentParser(prog="gws_merge_server.py")
    sub = ap.add_subparsers(dest="cmd", required=True)
    m = sub.add_parser("merge")
    m.add_argument("--repo", required=True)
    m.add_argument("--into", required=True)
    m.add_argument("--from", dest="frm", required=True)
    m.add_argument("--message")
    m.add_argument("--policy", choices=["refuse", "ours-wins"], default="refuse")
    m.add_argument("--queue", action="store_true",
                   help="serialise on a per-ref flock (the DESIGN 5.3 standing owner)")
    c = sub.add_parser("conflicts")
    c.add_argument("--repo", required=True)
    a = ap.parse_args(argv)
    if a.cmd == "merge":
        r = merge(a.repo, a.into, a.frm, a.message, a.policy, queue=a.queue)
        print(json.dumps(r, indent=1, sort_keys=True))
        return 0 if r["status"] in ("merged", "already-merged", "fast-forward") else 1
    if a.cmd == "conflicts":
        repo = Repo(a.repo)
        for line in repo.out("for-each-ref", "--format=%(refname)",
                             "refs/gws/conflicts").splitlines():
            print(line)
            print(repo.out("cat-file", "-p", f"{line}:conflicts.json"))
        return 0


if __name__ == "__main__":
    sys.exit(main())
