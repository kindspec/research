"""Shared machinery for the D0 history-replay experiment.

Nothing here is allowed to skip a commit silently: every commit in the
traversal gets exactly one record in the ledger, and the caller asserts on the
count.
"""

import csv
import hashlib
import io
import os
import subprocess
import sys
import unicodedata
from collections import Counter, defaultdict

sys.path.insert(0, "/home/cam/repos_kindspec/rowspec/reference")
from rowspec import csvmode  # noqa: E402
from rowspec.sidecar import Sidecar  # noqa: E402
from rowspec.table import Malformed, _check_ident, evaluate, is_align  # noqa: E402

SPEC_EXTRA = set("_-.")


class Git:
    """One long-lived cat-file process; forking per blob dominated the runtime."""

    def __init__(self, repo):
        self.repo = repo
        self.p = subprocess.Popen(
            ["git", "-C", repo, "cat-file", "--batch"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
        )

    def run(self, *a):
        return subprocess.run(
            ["git", "-C", self.repo, *a], capture_output=True, text=True
        ).stdout

    def blob(self, sha):
        self.p.stdin.write((sha + "\n").encode())
        self.p.stdin.flush()
        hdr = self.p.stdout.readline().decode()
        if hdr.strip().endswith("missing"):
            return None
        size = int(hdr.split()[2])
        data = self.p.stdout.read(size)
        self.p.stdout.read(1)
        return data

    def blob_sha(self, rev, path):
        r = subprocess.run(
            ["git", "-C", self.repo, "rev-parse", f"{rev}:{path}"],
            capture_output=True,
            text=True,
        )
        return r.stdout.strip() if r.returncode == 0 else None


def mangle(name, taken):
    """One-time, deterministic column rename for adoption. Logged, never silent."""
    n = unicodedata.normalize("NFC", name)
    out = "".join(
        c if (c.isalnum() or unicodedata.category(c).startswith("M") or c == "_") else "_"
        for c in n
    )
    while "__" in out:
        out = out.replace("__", "_")
    out = out.strip("_") or "c"
    if out[0].isdigit():
        out = "c" + out
    base, i = out, 2
    while out in taken:
        out = f"{base}_{i}"
        i += 1
    return out


def ident_ok_reference(name):
    try:
        _check_ident(name, "column name")
        return True
    except Malformed:
        return False


def ident_ok_spec(name):
    """SPEC.md 4.1.9's ABNF: LETTER / MARK / NUM / '_' / '-' / '.'"""
    if not name:
        return False
    for ch in name:
        if ch in SPEC_EXTRA:
            continue
        if unicodedata.category(ch)[0] in ("L", "M", "N"):
            continue
        return False
    return True


def read_csv(raw):
    """Returns (header, rows, notes). Raises Malformed the way CSV mode does."""
    notes = []
    if raw.startswith(b"\xef\xbb\xbf"):
        notes.append("bom")
        raw = raw[3:]
    try:
        text = raw.decode("utf-8")
    except UnicodeDecodeError as e:
        raise Malformed(f"not valid UTF-8 at offset {e.start}") from None
    if b"\r\n" in raw:
        notes.append("crlf")
    recs = list(csv.reader(io.StringIO(text, newline="")))
    recs = [r for r in recs if r != []]
    if not recs:
        raise Malformed("file contains no table")
    return recs[0], recs[1:], notes


def mint(commit, i):
    return "r_" + hashlib.sha1(f"{commit}:{i}".encode()).hexdigest()[:10]


def natkeys(header, rows, natkey):
    """The join column, with an occurrence suffix so a legitimately non-unique
    column (iptv blocklist's `channel`) still yields a total correspondence."""
    if natkey not in header:
        return None
    j = header.index(natkey)
    seen = Counter()
    out = []
    for r in rows:
        v = r[j] if j < len(r) else ""
        seen[v] += 1
        out.append(v if seen[v] == 1 else f"{v}\x00{seen[v]}")
    return out


def build_mdtbl(header, rows, ids, keycol, colmap):
    cols = [keycol] + [colmap[h] for h in header]
    lines = ["| " + " | ".join(cols) + " |", "| " + " | ".join(["---"] * len(cols)) + " |"]
    for rid, r in zip(ids, rows):
        # r is used verbatim: truncating or padding a ragged row here would hide
        # the very refusal (SPEC 9.6) the experiment is trying to count.
        lines.append("| " + " | ".join([rid] + list(r)) + " |")
    return "\n".join(lines) + f"\n\nkey := {keycol}\n"


def representability(header, rows):
    """Defects that stop this CSV being a .mdtbl at all, with the offending bytes."""
    bad = []
    for i, r in enumerate(rows):
        for j, c in enumerate(r):
            if "|" in c:
                bad.append(("pipe-in-value", i, j, c))
            if "\n" in c or "\r" in c:
                bad.append(("newline-in-value", i, j, c))
    for i, r in enumerate(rows):
        if len(r) != len(header):
            bad.append(("field-count", i, -1, f"{len(r)} vs {len(header)}"))
        elif r and all(is_align("|" + c + "|") for c in r if c.strip()) and any(c.strip() for c in r):
            if all(c.strip() == "" or is_align("|" + c + "|") for c in r):
                bad.append(("align-style-row", i, -1, ",".join(r)))
    return bad


def canon_churn(rows):
    nfc = trim = 0
    ex_nfc, ex_trim = [], []
    for i, r in enumerate(rows):
        for j, c in enumerate(r):
            if unicodedata.normalize("NFC", c) != c:
                nfc += 1
                if len(ex_nfc) < 3:
                    ex_nfc.append((i, j, c))
            if c.strip(" \t") != c:
                trim += 1
                if len(ex_trim) < 3:
                    ex_trim.append((i, j, c))
    return nfc, trim, ex_nfc, ex_trim


# --- the independent witness -------------------------------------------------
# Row correspondence computed from CONTENT ONLY, never from the join column, so
# that "the ids were carried" is checked against something the id mechanism did
# not produce.


def witness(rows_a, rows_b):
    """1:1 correspondence between two row lists. Returns dict idx_b -> idx_a."""
    ja = defaultdict(list)
    for i, r in enumerate(rows_a):
        ja["\x01".join(r)].append(i)
    match = {}
    used_a = set()
    left_b = []
    for i, r in enumerate(rows_b):
        k = "\x01".join(r)
        if ja.get(k):
            a = ja[k].pop()
            match[i] = a
            used_a.add(a)
        else:
            left_b.append(i)
    left_a = [i for i in range(len(rows_a)) if i not in used_a]
    if not left_b or not left_a:
        return match
    # block on individual field values so a wholesale re-sort or a column
    # rewrite does not become an O(n*m) pairing
    idx = defaultdict(list)
    for i in left_a:
        for v in set(rows_a[i]):
            if v.strip():
                idx[v].append(i)
    for i in left_b:
        cand = Counter()
        for v in set(rows_b[i]):
            if v.strip() and len(idx.get(v, ())) < 400:
                for a in idx.get(v, ()):
                    if a not in used_a:
                        cand[a] += 1
        if not cand:
            continue
        best, score = cand.most_common(1)[0]
        denom = max(len(set(rows_b[i])), len(set(rows_a[best])), 1)
        if score / denom >= 0.5:
            match[i] = best
            used_a.add(best)
    return match


def similarity(ra, rb):
    sa, sb = set(x for x in ra if x.strip()), set(x for x in rb if x.strip())
    if not sa and not sb:
        return 1.0
    return len(sa & sb) / max(len(sa | sb), 1)


# --- diff sizes --------------------------------------------------------------

DIFFDIR = os.environ.get("D0_TMP", "/tmp/d0diff")


def diff_size(a_bytes, b_bytes, tag):
    os.makedirs(DIFFDIR, exist_ok=True)
    pa, pb = f"{DIFFDIR}/{tag}.a", f"{DIFFDIR}/{tag}.b"
    open(pa, "wb").write(a_bytes)
    open(pb, "wb").write(b_bytes)
    out = subprocess.run(
        ["git", "diff", "--no-index", "-U0", "--no-color", "--no-ext-diff", pa, pb],
        capture_output=True,
    ).stdout.decode("utf-8", "replace")
    lines = bytes_ = 0
    for ln in out.splitlines():
        if ln.startswith(("+++", "---", "@@", "diff ", "index ", "new file", "deleted file")):
            continue
        if ln[:1] in ("+", "-"):
            lines += 1
            bytes_ += len(ln.encode()) + 1
    return lines, bytes_


def csv_mode_check(raw, name, key):
    """The zero-migration arm: SPEC 9 on the .csv itself, with a 5-line sidecar."""
    try:
        text, warns = csvmode._decode(raw, name)
        side = Sidecar(name + ".rowspec.json", key=key)
        f = csvmode.check_text(text, name=name, side=side)
        return [x for x in f + warns if x.level == "refuse"], [
            x for x in f + warns if x.level == "warn"
        ]
    except Malformed as e:
        return [csvmode.Finding("refused", str(e))], []
