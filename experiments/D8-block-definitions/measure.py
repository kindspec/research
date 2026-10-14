#!/usr/bin/env python3
"""D8's within-file uniqueness measurement (D8-identity/e4_uniqueness.py),
re-run under each candidate definition of a block (kindspec/blockspec#4).

e4 split a file with D8's boundary-only splitter -- blank-line chunks, fences
respected -- and reported a chunk typed `prose` as the block. This parses each
file with a CommonMark parser instead, so that a paragraph, a top-level node, a
list, a list item and a section are each a real node, and counts the same thing
under every definition: how many blocks of at least MINLEN characters share
their exact content with another block in the same file.

Usage (see README.md):

    python3 -I measure.py --clone rust-book=PATH --clone obsidian-help=PATH \
        --clone cmspec=PATH --clone kubernetes-website=PATH \
        --clone cncf-toc=PATH --clone site-policy=PATH > results.txt

Every check fails loudly, exit 2: a clone that is missing, not a git work tree,
not at its pin, or with tracked changes; an arm whose pathspec selects no .md
file or whose files yield no block; a parser that is not markdown-it-py
EXPECT_PARSER; and a run without D8's three arms, because the validation step
needs them. Exit 1: the validation step -- D8's own procedure, re-run here on
D8's three arms, must reproduce D8-identity/results-e4.txt byte for byte, or
nothing is measured.
"""
import argparse
import hashlib
import json
import os
import re
import subprocess
import sys
from collections import Counter, defaultdict

sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__))
EXPECT_PARSER = "3.0.0"
MINLENS = (1, 20, 40, 120)
TYPE_MINLEN = 40
D8_ARMS = ("rust-book", "obsidian-help", "cmspec")

DEFS = [
    ("a0", "d8-prose", "D8's blank-line chunks typed prose by btype() -- the brief's figure"),
    ("a1", "para-top", "top-level paragraphs"),
    ("a2", "para-any", "every paragraph, at any depth (inside list items and quotes too)"),
    ("b", "top-node", "every top-level node; a list is one node, so this is also (c)"),
    ("b2", "top-node-text", "(b) without code and raw-HTML nodes"),
    ("d", "top-items", "(b), with each top-level list replaced by its items"),
    ("d2", "items-any", "every list item at any depth; a parent item contains its sub-items"),
    ("e", "section", "top-level heading to the next of same or higher rank; overlapping"),
    ("e2", "section-flat", "top-level heading to the next heading of any rank; a partition"),
    ("f", "leaf", "every leaf block at any depth: paragraph, heading, code, html, table, hr"),
    ("f0", "d8-chunk", "D8's blank-line chunks, every type"),
]


def die(msg, code=2):
    print(f"measure.py: {msg}", file=sys.stderr)
    sys.exit(code)


# ------------------------------------------------------------------ inputs

def git(repo, *a, env=None):
    r = subprocess.run(["git", "-C", repo, *a], capture_output=True, text=True, env=env)
    if r.returncode != 0:
        die(f"git -C {repo} {' '.join(a)}: exit {r.returncode}: {r.stderr.strip()}")
    return r.stdout


def check_clone(name, repo, pin):
    """The same refusals as blockspec spike/harness/d8_cheap_arm.py check_corpus."""
    if not os.path.isdir(repo):
        die(f"{name}: clone does not exist: {repo}")
    r = subprocess.run(["git", "-C", repo, "rev-parse", "--show-toplevel", "HEAD"],
                       capture_output=True, text=True)
    if r.returncode != 0:
        die(f"{name}: not a git work tree: {repo}: {r.stderr.strip()}")
    top, head = r.stdout.split()
    if os.path.realpath(top) != os.path.realpath(repo):
        die(f"{name}: {repo} is inside a work tree rooted at {top}, not its root")
    if head != pin:
        die(f"{name}: HEAD is {head}, pinned at {pin}")
    st = git(repo, "status", "--porcelain", "--untracked-files=no",
             env={**os.environ, "GIT_OPTIONAL_LOCKS": "0"})
    if st.strip():
        die(f"{name}: tracked files differ from HEAD; this reads the work tree:\n{st.strip()[:400]}")
    print(f"arm {name} HEAD {head} (pin)", file=sys.stderr, flush=True)


FENCE = re.compile(r"---[ \t]*\n.*?\n---[ \t]*(\n|$)", re.DOTALL)
GENERATED_KEY = re.compile(r"^auto_generated:[ \t]*true[ \t]*$", re.MULTILINE | re.IGNORECASE)
GENERATED_BANNER = re.compile(r"THIS FILE IS AUTO-GENERATED", re.IGNORECASE)


def frontmatter_end(text):
    m = FENCE.match(text)
    return m.end() if m else -1


def is_generated(text):
    """PRE-REGISTRATION-2 §6.3, d8_cheap_arm.py --generated-rule yaml-fence."""
    if GENERATED_BANNER.search(text):
        return True
    end = frontmatter_end(text)
    return end >= 0 and bool(GENERATED_KEY.search(text[:end]))


def read(repo, f):
    with open(os.path.join(repo, f), encoding="utf-8") as fh:
        return fh.read()


def select(name, repo, pathspec):
    files = [f for f in git(repo, "ls-files", *pathspec.split()).split("\n") if f.endswith(".md")]
    if not files:
        die(f"{name}: pathspec {pathspec!r} selects no .md files in {repo}")
    keep, generated, unreadable, texts = [], [], [], {}
    for f in files:
        try:
            t = read(repo, f)
        except (OSError, UnicodeDecodeError):
            unreadable.append(f)
            continue
        (generated if is_generated(t) else keep).append(f)
        texts[f] = t
    if not keep:
        die(f"{name}: every selected file is generated or unreadable")
    return keep, generated, unreadable, texts


# ------------------------------------------------------------- validation

def e4_output(d8, corpora, minlen):
    """e4_uniqueness.py's loop and printer, copied; only the corpus list and
    `print` -> a returned string changed. Reads files exactly as e4 does."""
    out = []
    for name, repo, glob in corpora:
        files = d8.md_files(repo, glob, history=False)
        per_file_dup = Counter(); corpus = Counter(); tot = Counter(); nfiles = 0
        for f in files:
            try: t = open(os.path.join(repo, f), encoding='utf-8').read()
            except Exception: continue
            nfiles += 1
            bs = [b for b in d8.blocks(t) if len(b['content']) >= minlen]
            c = Counter(b['content'] for b in bs)
            for b in bs:
                ty = d8.btype(b['content']); tot[ty] += 1
                if c[b['content']] > 1: per_file_dup[ty] += 1
                corpus[b['content']] += 1
        cross = Counter()
        for f in files:
            try: t = open(os.path.join(repo, f), encoding='utf-8').read()
            except Exception: continue
            for b in d8.blocks(t):
                if len(b['content']) >= minlen and corpus[b['content']] > 1: cross[d8.btype(b['content'])] += 1
        out.append(f"\n### {name}  files={nfiles}  blocks>={minlen}ch={sum(tot.values())}")
        out.append(f"{'type':<9}{'n':>7}{'dup in same file':>19}{'dup anywhere in corpus':>25}")
        for ty in sorted(tot):
            n = tot[ty]
            out.append(f"{ty:<9}{n:>7}{per_file_dup[ty]:>10} ({100*per_file_dup[ty]/n:4.1f}%){cross[ty]:>14} ({100*cross[ty]/n:5.1f}%)")
    return "\n".join(out) + "\n"


def validate(d8, d8dir, arms):
    corpora = [(a["name"], a["repo"], a["pathspec"]) for a in arms if a["name"] in D8_ARMS]
    got = "".join(e4_output(d8, corpora, n) for n in (20, 40, 120))
    want = read(d8dir, "results-e4.txt")
    h = lambda s: hashlib.sha256(s.encode()).hexdigest()
    print("## Validation")
    print()
    print("D8's procedure (D8-identity/anchor_eval.py blocks(), anchor_eval3.py btype(),")
    print("e4_uniqueness.py's loop) re-run here on D8's three arms at 20, 40 and 120,")
    print("against the committed D8-identity/results-e4.txt:")
    print(f"  {h(got)}  this run")
    print(f"  {h(want)}  results-e4.txt")
    if got != want:
        print("  DIFFERS")
        die("validation failed: D8's procedure does not reproduce results-e4.txt here", 1)
    print("  BYTE-IDENTICAL")


# ------------------------------------------------------------- the blocks

MARKER = re.compile(r"^[ \t]*(?:[-*+]|\d{1,9}[.)])(?:[ \t]+|$)")
TOPTYPE = {
    "paragraph_open": "paragraph", "heading_open": "heading", "bullet_list_open": "list",
    "ordered_list_open": "list", "blockquote_open": "quote", "fence": "code",
    "code_block": "code", "html_block": "html", "hr": "hr", "table_open": "table",
}


def units(md, d8, text):
    """{def: [(type, content)]} for one file. Frontmatter is stripped before
    parsing and is a block under no CommonMark definition; a0 and f0 run D8's
    splitter on the whole text, as D8 did."""
    out = defaultdict(list)
    for b in d8.blocks(text):
        ty = d8.btype(b["content"])
        out["f0"].append((ty, b["content"]))
        if ty == "prose":
            out["a0"].append((ty, b["content"]))
    end = frontmatter_end(text)
    body = text[end:] if end >= 0 else text
    body = body.replace("\r\n", "\n").replace("\r", "\n")
    lines = body.split("\n")
    src = lambda m: "\n".join(lines[m[0]:m[1]]).strip()
    toks = md.parse(body)
    heads = []
    covered = [False] * len(lines)
    for i, t in enumerate(toks):
        if t.nesting == -1 or not t.block or t.map is None:
            continue
        if t.level == 0:
            ty = TOPTYPE[t.type]
            c = src(t.map)
            for k in range(t.map[0], t.map[1]):
                covered[k] = True
            out["b"].append((ty, c))
            if ty not in ("code", "html"):
                out["b2"].append((ty, c))
            if ty != "list":
                out["d"].append((ty, c))
            if ty == "heading":
                heads.append((t.map[0], int(t.tag[1:])))
        if t.type == "list_item_open":
            ls = lines[t.map[0]:t.map[1]]
            c = "\n".join([MARKER.sub("", ls[0], count=1)] + [l.lstrip() for l in ls[1:]]).strip()
            out["d2"].append(("item", c))
            if t.level == 1:
                out["d"].append(("item", c))
        elif t.type == "paragraph_open":
            c = toks[i + 1].content.strip()
            out["a2"].append(("paragraph", c))
            out["f"].append(("paragraph", c))
            if t.level == 0:
                out["a1"].append(("paragraph", c))
        elif t.type == "heading_open":
            out["f"].append(("heading", "#" * int(t.tag[1:]) + " " + toks[i + 1].content.strip()))
        elif t.type == "fence":
            out["f"].append(("code", f"{t.markup}{t.info}\n{t.content}{t.markup}"))
        elif t.type == "code_block":
            out["f"].append(("code", t.content.strip("\n")))
        elif t.type == "html_block":
            out["f"].append(("html", t.content.strip()))
        elif t.type == "hr":
            out["f"].append(("hr", t.markup))
        elif t.type == "table_open":
            out["f"].append(("table", "\n".join(l.strip() for l in lines[t.map[0]:t.map[1]]).strip()))
    first = heads[0][0] if heads else len(lines)
    pre = "\n".join(lines[:first]).strip()
    if pre:
        out["e"].append(("preamble", pre))
        out["e2"].append(("preamble", pre))
    for k, (start, lvl) in enumerate(heads):
        nxt = [s for s, l in heads[k + 1:] if l <= lvl]
        out["e"].append(("section", src((start, nxt[0] if nxt else len(lines)))))
        out["e2"].append(("section", src((start, heads[k + 1][0] if k + 1 < len(heads) else len(lines)))))
    uncovered = sum(1 for k, l in enumerate(lines) if l.strip() and not covered[k])
    return out, end >= 0, uncovered


# ------------------------------------------------------------- the counts

def stats(per_file, minlen, bytype=False):
    """per_file: [[(type, len, digest)]]. A content is its sha256; distinct
    contents are PRE-REGISTRATION-2 §6.1's unit, (arm, sha256(content))."""
    key = (lambda ty: ty) if bytype else (lambda ty: None)
    n = Counter(); dup = Counter()
    files_of = defaultdict(set); dup_somewhere = set(); ty_of = {}
    for fi, us in enumerate(per_file):
        us = [u for u in us if u[1] >= minlen]
        c = Counter(u[2] for u in us)
        for ty, _, dg in us:
            k = key(ty)
            n[k] += 1
            ty_of.setdefault(dg, k)
            files_of[dg].add(fi)
            if c[dg] > 1:
                dup[k] += 1
                dup_somewhere.add(dg)
    res = {}
    for k in n:
        ds = [d for d, kk in ty_of.items() if kk == k]
        local = [d for d in ds if len(files_of[d]) == 1]
        res[k] = (n[k], dup[k], len(ds), sum(d in dup_somewhere for d in ds),
                  len(local), sum(d in dup_somewhere for d in local))
    return res


def pct(a, b):
    return f"{100 * a / b:5.1f}%" if b else "    --"


def row(label, s):
    n, dup, d, dd, loc, ld = s
    return (f"{label:<30}{n:>8}{dup:>7} {pct(dup, n)}{d:>9}{dd:>6} {pct(dd, d)}"
            f"{loc:>9}{ld:>6} {pct(ld, loc)}")


HEADER = (f"{'':<30}{'blocks':>8}{'dup in file':>14}{'distinct':>9}{'dup in file':>13}"
          f"{'local':>9}{'dup in file':>13}")


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--clone", action="append", default=[], metavar="KEY=PATH",
                    help="where the clone named KEY in arms.json lives")
    ap.add_argument("--arms", default=os.path.join(HERE, "arms.json"))
    ap.add_argument("--d8-dir", default=os.path.join(HERE, "..", "D8-identity"))
    ap.add_argument("--show", metavar="DEF:ARM",
                    help="instead of the report, print the contents of DEF that repeat within a "
                         "file in ARM, most repeated first; quotes the corpus, so not committed")
    ap.add_argument("--show-minlen", type=int, default=TYPE_MINLEN)
    a = ap.parse_args()

    import markdown_it
    if markdown_it.__version__ != EXPECT_PARSER:
        die(f"markdown-it-py is {markdown_it.__version__}; this measurement is pinned to {EXPECT_PARSER}")
    md = markdown_it.MarkdownIt("commonmark").enable("table")

    if not os.path.isfile(os.path.join(a.d8_dir, "anchor_eval3.py")):
        die(f"--d8-dir has no anchor_eval3.py: {a.d8_dir}")
    sys.path.insert(0, os.path.abspath(a.d8_dir))
    import anchor_eval
    import anchor_eval3

    class D8:
        blocks = staticmethod(anchor_eval.blocks)
        md_files = staticmethod(anchor_eval.md_files)
        btype = staticmethod(anchor_eval3.btype)

    clones = {}
    for kv in a.clone:
        k, sep, p = kv.partition("=")
        if not sep:
            die(f"--clone wants KEY=PATH, got {kv!r}")
        clones[k] = p
    with open(a.arms, encoding="utf-8") as fh:
        arms = json.load(fh)["arms"]
    for arm in arms:
        if arm["clone"] not in clones:
            die(f"{arm['name']}: no --clone {arm['clone']}=PATH")
        arm["repo"] = clones[arm["clone"]]
        check_clone(arm["name"], arm["repo"], arm["pin"])
    if a.show:
        code, _, arm_name = a.show.partition(":")
        arm = next((x for x in arms if x["name"] == arm_name), None)
        if arm is None or code not in {c for c, _, _ in DEFS}:
            die(f"--show wants DEF:ARM with DEF one of the codes below and ARM in --arms, got {a.show!r}")
        keep, _, _, texts = select(arm["name"], arm["repo"], arm["pathspec"])
        rep = Counter(); ty_of = {}
        for f in keep:
            us = [(ty, c) for ty, c in units(md, D8, texts[f])[0][code] if len(c) >= a.show_minlen]
            n = Counter(c for _, c in us)
            for ty, c in us:
                if n[c] > 1:
                    rep[c] += 1; ty_of[c] = ty
        print(f"{code} {arm_name} minlen={a.show_minlen}: {sum(rep.values())} instances, {len(rep)} distinct contents")
        for c, n in rep.most_common():
            print(f"{n:>6}  {ty_of[c]:<10} {c[:70]!r}")
        return

    data = {}; armrows = []
    for arm in arms:
        name = arm["name"]
        keep, gen, unread, texts = select(name, arm["repo"], arm["pathspec"])
        per = defaultdict(list); nfm = 0; unc = 0
        for f in keep:
            us, fm, u = units(md, D8, texts[f])
            nfm += fm; unc += u
            for code, _, _ in DEFS:
                per[code].append([(ty, len(c), hashlib.sha256(c.encode()).digest()) for ty, c in us[code]])
        if not any(any(fl) for fl in per["b"]):
            die(f"{name}: read {len(keep)} files and found no block")
        data[name] = per
        armrows.append(f"{name:<15}{arm['pin'][:12]:<14}{len(keep):>7}{len(gen):>10}{len(unread):>11}"
                       f"{nfm:>12}{unc:>10}  {arm['pathspec']}")
    if any(n not in data for n in D8_ARMS):
        die(f"the validation step needs D8's three arms, {', '.join(D8_ARMS)}")

    print("# D8-block-definitions: within-file uniqueness under candidate block definitions")
    print()
    print(f"parser: markdown-it-py {markdown_it.__version__}, preset commonmark + table")
    print("generated-file rule: yaml-fence (blockspec PRE-REGISTRATION-2 §6.3)")
    print()
    validate(D8, a.d8_dir, arms)
    print()
    print("## Arms")
    print()
    print(f"{'arm':<15}{'pin':<14}{'files':>7}{'generated':>10}{'unreadable':>11}{'frontmatter':>12}"
          f"{'uncovered':>10}  pathspec")
    print("\n".join(armrows))
    print()
    print("files: selected by the pathspec, .md, minus generated and unreadable.")
    print("uncovered: non-blank lines after frontmatter that no top-level node spans")
    print("(link reference definitions produce no node).")

    print()
    print("## Definitions")
    print()
    for code, label, desc in DEFS:
        print(f"{code:<3} {label:<14} {desc}")

    print()
    print("## Columns")
    print()
    print("blocks       instances whose content is >= minlen characters")
    print("dup in file  instances whose exact content occurs again in the same file")
    print("distinct     distinct contents, sha256 over the arm: a block replicated")
    print("             across files, or within one, counts once")
    print("  dup in file  distinct contents that occur twice or more in some file")
    print("local        distinct contents found in exactly one file: anything")
    print("             replicated across files (templates, boilerplate) removed")
    print("  dup in file  local contents that occur twice or more in their file")

    for minlen in MINLENS:
        print()
        print(f"## Summary, minlen={minlen}")
        for code, label, _ in DEFS:
            print()
            print(f"{code} {label:<27}" + HEADER[30:])
            for arm in arms:
                s = stats(data[arm["name"]][code], minlen).get(None)
                if s is None:
                    print(f"  {arm['name']:<28}       0")
                else:
                    print(row("  " + arm["name"], s))

    print()
    print(f"## By type, minlen={TYPE_MINLEN}")
    for code, label, _ in DEFS:
        for arm in arms:
            st = stats(data[arm["name"]][code], TYPE_MINLEN, bytype=True)
            print()
            title = f"{code} {label} / {arm['name']}"
            print(f"{title:<30}" + HEADER[30:])
            for ty in sorted(st):
                print(row("  " + ty, st[ty]))


if __name__ == "__main__":
    main()
