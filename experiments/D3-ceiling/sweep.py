#!/usr/bin/env python3
"""
Quantify git's line-based 3-way merge on structured files.

Every trial is constructed so a STRUCTURAL merge has a unique, obviously-correct
answer: the two authors' edits target DISJOINT structural units (different rows /
different paragraphs), so they commute. There are therefore ZERO legitimate
conflicts by construction. Anything git reports as a conflict is a FALSE CONFLICT;
anything git merges cleanly but differently from the structural answer is a
SILENT WRONG MERGE.
"""
import csv, io, os, random, shutil, subprocess, sys, tempfile, collections

GIT = ["git", "-c", "user.name=T", "-c", "user.email=t@e", "-c", "init.defaultBranch=main"]

def run(cwd, *a, **kw):
    return subprocess.run(GIT + list(a), cwd=cwd, capture_output=True, text=True, **kw)

# ---------------------------------------------------------------- CSV model
def mk_table(n, formulas):
    rows = [["id", "name", "qty", "price", "total"]]
    for i in range(1, n + 1):
        tot = f"=C{i+1}*D{i+1}" if formulas else str(i * 10)
        rows.append([f"id{i:03d}", f"name{i}", str(i), "10", tot])
    if formulas:
        rows.append(["TOTAL", "", "", "", f"=SUM(E2:E{n+1})"])
    return rows

def renumber(rows, formulas):
    """Structural semantics: a row's formula always refers to its own row."""
    if not formulas: return rows
    out = [rows[0]]
    body = [r for r in rows[1:] if r[0] != "TOTAL"]
    for i, r in enumerate(body, start=2):
        r = list(r)
        if r[4].startswith("="): r[4] = f"=C{i}*D{i}"
        out.append(r)
    out.append(["TOTAL", "", "", "", f"=SUM(E2:E{len(body)+1})"])
    return out

def ser(rows):
    b = io.StringIO(); csv.writer(b, lineterminator="\n").writerows(rows); return b.getvalue()

def apply_ops(rows, ops, formulas):
    rows = [list(r) for r in rows]
    for kind, key, val in sorted(ops, key=lambda o: -o[1] if isinstance(o[1], int) else 0):
        pass
    # apply by id so order doesn't matter
    for kind, key, val in ops:
        if kind == "edit":
            for r in rows:
                if r[0] == key: r[val[0]] = val[1]
        elif kind == "delete":
            rows = [r for r in rows if r[0] != key]
        elif kind == "insert":
            idx = next(i for i, r in enumerate(rows) if r[0] == key) + 1
            rows.insert(idx, val)
    return renumber(rows, formulas)

def csv_trial(rng, n, formulas, k):
    base = mk_table(n, formulas)
    ids = [r[0] for r in base[1:] if r[0] != "TOTAL"]
    rng.shuffle(ids)
    # disjoint target rows for the two authors
    need = 2 * k
    if len(ids) < need: return None
    a_ids, b_ids = ids[:k], ids[k:2 * k]
    def gen(sel, tag):
        ops = []
        for j, i in enumerate(sel):
            c = rng.choice(["edit", "insert", "delete"])
            if c == "edit":
                col = rng.choice([1, 2, 3])
                ops.append(("edit", i, (col, f"{tag}{j}" if col == 1 else str(rng.randint(20, 99)))))
            elif c == "insert":
                ops.append(("insert", i, [f"{tag}new{j}", f"{tag}n{j}", str(rng.randint(1, 9)), "10",
                                          "=C0*D0" if formulas else str(rng.randint(1, 99))]))
            else:
                ops.append(("delete", i, None))
        return ops
    return base, gen(a_ids, "A"), gen(b_ids, "B"), formulas

# ---------------------------------------------------------------- MD model
def mk_doc(n):
    p = ["# Document", ""]
    for i in range(1, n + 1):
        p += [f"## Section {i}", "", f"Paragraph body for section {i}. It has some words in it.", ""]
    return p

def md_apply(lines, ops):
    """ops on section index; rebuild from a section list"""
    secs = []
    cur = None
    head = []
    for ln in lines:
        if ln.startswith("## "):
            if cur is not None: secs.append(cur)
            cur = [ln]
        elif cur is None: head.append(ln)
        else: cur.append(ln)
    if cur is not None: secs.append(cur)
    keyed = {s[0]: s for s in secs}
    order = [s[0] for s in secs]
    for kind, key, val in ops:
        if kind == "edit": keyed[key] = [keyed[key][0], "", val, ""]
        elif kind == "delete":
            order.remove(key); keyed.pop(key)
        elif kind == "insert":
            order.insert(order.index(key) + 1, val[0]); keyed[val[0]] = val
    out = list(head)
    for k in order: out += keyed[k]
    return "\n".join(out).rstrip() + "\n"

def md_trial(rng, n, k):
    lines = mk_doc(n)
    keys = [f"## Section {i}" for i in range(1, n + 1)]
    rng.shuffle(keys)
    if len(keys) < 2 * k: return None
    a, b = keys[:k], keys[k:2 * k]
    def gen(sel, tag):
        ops = []
        for j, key in enumerate(sel):
            c = rng.choice(["edit", "insert", "delete"])
            if c == "edit": ops.append(("edit", key, f"Rewritten by {tag} number {j}. New sentence."))
            elif c == "insert":
                h = f"## {tag} New {j}"
                ops.append(("insert", key, [h, "", f"Body added by {tag} {j}.", ""]))
            else: ops.append(("delete", key, None))
        return ops
    return lines, gen(a, "A"), gen(b, "B")

# ---------------------------------------------------------------- harness
def git_merge(tmp, fname, base_s, a_s, b_s):
    d = tempfile.mkdtemp(dir=tmp)
    run(d, "init", "-q", ".")
    open(os.path.join(d, fname), "w").write(base_s)
    run(d, "add", "-A"); run(d, "commit", "-qm", "base")
    run(d, "checkout", "-qb", "B")
    open(os.path.join(d, fname), "w").write(b_s)
    run(d, "commit", "-qam", "b")
    run(d, "checkout", "-q", "main")
    open(os.path.join(d, fname), "w").write(a_s)
    run(d, "commit", "-qam", "a")
    r = run(d, "merge", "B")
    got = open(os.path.join(d, fname)).read()
    shutil.rmtree(d, ignore_errors=True)
    return r.returncode, got

def sweep(label, N, gen, fname, seed=7):
    rng = random.Random(seed)
    tmp = tempfile.mkdtemp()
    c = collections.Counter()
    examples = {}
    done = 0
    while done < N:
        t = gen(rng)
        if t is None: continue
        base_s, a_s, b_s, want = t
        rc, got = git_merge(tmp, fname, base_s, a_s, b_s)
        if rc != 0: k = "false-conflict"
        elif got.strip() == want.strip(): k = "clean-correct"
        else: k = "SILENT-WRONG"
        c[k] += 1
        examples.setdefault(k, (base_s, a_s, b_s, want, got))
        done += 1
    shutil.rmtree(tmp, ignore_errors=True)
    tot = sum(c.values())
    print(f"\n=== {label}  (n={tot}, zero legitimate conflicts by construction) ===")
    for k in ["clean-correct", "false-conflict", "SILENT-WRONG"]:
        print(f"   {k:16} {c[k]:5}   {100*c[k]/tot:5.1f}%")
    return c, examples

def csv_gen(formulas, n, k):
    def g(rng):
        t = csv_trial(rng, n, formulas, k)
        if t is None: return None
        base, aops, bops, f = t
        return (ser(base), ser(apply_ops(base, aops, f)), ser(apply_ops(base, bops, f)),
                ser(apply_ops(base, aops + bops, f)))
    return g

def md_gen(n, k):
    def g(rng):
        t = md_trial(rng, n, k)
        if t is None: return None
        lines, aops, bops = t
        return (md_apply(lines, []), md_apply(lines, aops), md_apply(lines, bops),
                md_apply(lines, aops + bops))
    return g

if __name__ == "__main__":
    N = int(sys.argv[1]) if len(sys.argv) > 1 else 200
    res = {}
    res['csv-plain-1'] = sweep("CSV, no formulas, 1 edit each, 20 rows", N, csv_gen(False, 20, 1), "t.csv")
    res['csv-plain-3'] = sweep("CSV, no formulas, 3 edits each, 20 rows", N, csv_gen(False, 20, 3), "t.csv")
    res['csv-form-1']  = sweep("CSV, A1 FORMULAS, 1 edit each, 20 rows", N, csv_gen(True, 20, 1), "t.csv")
    res['csv-form-3']  = sweep("CSV, A1 FORMULAS, 3 edits each, 20 rows", N, csv_gen(True, 20, 3), "t.csv")
    res['md-1']        = sweep("Markdown, 1 section op each, 12 sections", N, md_gen(12, 1), "d.md")
    res['md-3']        = sweep("Markdown, 3 section ops each, 12 sections", N, md_gen(12, 3), "d.md")
    print("\n=== SUMMARY TABLE ===")
    print(f"{'scenario':42} {'clean-correct':>14} {'false-conflict':>15} {'SILENT-WRONG':>14}")
    for k, (c, _) in res.items():
        t = sum(c.values())
        print(f"{k:42} {100*c['clean-correct']/t:13.1f}% {100*c['false-conflict']/t:14.1f}% {100*c['SILENT-WRONG']/t:13.1f}%")
    # dump one silent-wrong example per scenario
    for k, (c, ex) in res.items():
        if "SILENT-WRONG" in ex:
            b, a, bb, w, g = ex["SILENT-WRONG"]
            print(f"\n--- example SILENT-WRONG in {k} ---")
            print("BASE:\n" + b + "OURS(A):\n" + a + "THEIRS(B):\n" + bb)
            print("CORRECT STRUCTURAL MERGE:\n" + w + "GIT PRODUCED (clean, exit 0):\n" + g)
            break
