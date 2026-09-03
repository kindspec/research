# W4 — Scale and performance: where the formats break

Empirical pass, 2026-08-28. Everything below was generated, run and timed on
this machine; nothing is estimated unless the line says EXTRAPOLATED.
Harness: `experiments/W4-scale/` (`gen.py`, `e1_table.py`, `e1b_git.py`,
`e1e_1m_git.py`, `e2_doc.py`, `e3_derive.py`, `e3b_fix.py`, `e3c_dag.py`,
`e4_repo.py`); raw JSON and logs in `experiments/W4-scale/out/`.

Environment: Linux 6.12, Python 3.13.5, git 2.47.3, 12 cores, 31 GB RAM,
NVMe. Timings are medians of 3–5 runs unless noted. `gc.auto=0` in every
generated repo so pack sizes are attributable rather than incidental.

Prototypes measured as shipped: `experiments/L1-nominal-merge/tbl.py`,
`experiments/L3-block-roundtrip/{blocks,bmerge2}.py`,
`experiments/L5-derivation/derive.py`.

---

## 0. The breaking-point table

| Operation | Acceptable up to | Limiting factor |
|---|---|---|
| `.tbl` parse | ~1M rows (3.5 s) | linear, 3.4 µs/row — CPU |
| `.tbl` evaluate | **~300k rows** (4.9 s) | linear, 16.3 µs/row — `ast.parse` per cell per row |
| `.tbl` in memory | **~500k rows** (368 MB) | 735 bytes of Python objects per row = 5.3× the file |
| `git diff` on one `.tbl` | ~1M rows (1.1 s) | linear in file bytes |
| `git merge` on one `.tbl` | **~200k rows** (~1 s) | linear; 10.5 s at 1M rows |
| **`.tbl` with alignment padding** | **~any size, but only for width-preserving edits** | a value that widens a column reflows every row: 2n diff lines, and two disjoint edits **conflict** |
| `.tbl` column count | **~50 columns** (446-char lines) | line length; 203 columns = 1 496-char lines = 12.5 terminal widths |
| Markdown boundary parse | no measured limit (57 MB/s, 10k docs = 1.25 s) | linear; round-trip exact 100% at every size |
| **`bmerge2` similarity merge** | **~300 changed blocks per side** (10 s) | O(k²) `difflib.ratio` calls, k = blocks changed per side. 500 → 62 s; 1000 → 363 s |
| Derivation build, warm | ~10 000 artifacts (3.8 s) | **closure hash is 84% of it**; cache saves only 1.5× |
| Derivation, deep chain | **~50 deep** | closure hash is O(depth) *per resolve*; full build is O(depth²)+ — 20.2 s at depth 400 |
| Derivation, wide fan-in | ~1000 (1.2 s) | O(fan-in) closure hashes of the same hub; warm == cold |
| Reference cycles | **detected: never** | no cycle detection exists at all |
| Realistic repo (2 000 artifacts, 5 000 commits) | comfortable — `status` 4 ms, clone 0.26 s, `check` 1.06 s | `git log` on one file 0.44 s (O(total commits)); `.git` 178 MB loose until repacked to 11.9 MB |

Three of these force a design change before planning: **the alignment
padding**, **the closure-hash cost**, and **the absence of cycle detection**.
Details in §1.4, §3.2, §3.5.

---

## 1. The table format at scale

### 1.1 Parse, evaluate, memory

Realistic shape: 6 literal columns (`id item region qty unit tax_rate`),
3 chained computed columns (`total = qty * unit`, `taxed = total * tax_rate`,
`net = total - taxed`) and 3 aggregates (`grand := sum(total)`,
`nrows := count(id)`, `taxes := sum(taxed)`).

| rows | file | `parse` | `evaluate` | peak Python heap |
|---:|---:|---:|---:|---:|
| 1 000 | 0.133 MB | 3.2 ms | 15.2 ms | 0.74 MB |
| 10 000 | 1.33 MB | 30.3 ms | 155 ms | 7.36 MB |
| 100 000 | 13.3 MB | 334 ms | 1.586 s | 73.4 MB |
| 1 000 000 | 132.6 MB | 3.477 s | 16.33 s | 735 MB |

Perfectly linear: 3.4 µs/row parse, 16.3 µs/row evaluate, 735 B/row resident.
Evaluate is 4.7× parse because `tbl.py` calls `ast.parse()` on the formula
string once per cell per row — hoisting the compile out of the row loop is an
obvious ~3–4× win and costs nothing architecturally.

The memory figure is the sharper constraint: a 1M-row table needs 735 MB of
process memory to evaluate a 133 MB file. **The working set, not the file, is
what sets the ceiling.**

### 1.2 File size versus CSV — the tax, decomposed

At 1M rows, byte-exact:

| representation | bytes | delta |
|---|---:|---|
| CSV, no row-id column | 39 234 252 | baseline |
| CSV, with opaque row-id | 50 234 255 | **+28.0%** ← the row-id tax |
| `.tbl`, single-space pipes | 70 234 439 | +39.8% over CSV ← the pipe/delimiter tax |
| `.tbl`, padded (the specified form) | 139 000 338 | **+97.9% over unpadded** ← the alignment tax |

Totals: the specified `.tbl` is **+176.7% over CSV-with-ids** and **+254.3%
over plain CSV**. Bytes/row 139.0 vs 50.2.

**Where the alignment tax actually goes.** 48.2% of the entire padded file is
whitespace *inside the three blank computed cells*, each padded to the width of
its formula header (`| total = qty * unit |` is 18 characters wide and every
cell under it is 18 spaces). That single decision is **88.7% of the whole
padding delta**; literal-column alignment is the other 11.3%. DESIGN.md §7's
own worked example has exactly this shape.

**The size objection mostly evaporates under compression, as §C5 predicted.**
gzip -6 at 10k rows: padded `.tbl` 147 851 B vs CSV 128 453 B — **+15.1%**;
padded vs unpadded `.tbl` is only +7.9%. Git stores compressed, so the size tax
is real but small. *The diff behaviour is the problem, not the bytes.*

### 1.3 Git operations

Padded `.tbl`, one-cell edit that does **not** change the cell's width.

| rows | file | `add` | `status` | `diff` (1 cell) | `diff` (row insert) | `merge` | `merge-tree` |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 000 | 0.13 MB | 1.8 ms | 2.5 ms | 3.7 ms | 2.5 ms | 10.8 ms | — |
| 10 000 | 1.33 MB | 5.0 ms | 5.3 ms | 21.6 ms | 11.4 ms | 53.9 ms | 56 ms |
| 100 000 | 13.3 MB | 36.6 ms | 38.4 ms | 206 ms | 107 ms | 478 ms | 503 ms |
| 1 000 000 | 132.6 MB | 1.26 s | 758 ms | 1.11 s | — | 10.52 s | — |

Every diff is **1 added / 1 deleted line** and every merge of two distant row
edits is **clean** — I1 and I6 hold, at every size, *for width-preserving
edits*. Row insertion is 1 add / 0 del. `git merge-tree --write-tree` (the
server-side path §8 makes non-optional) tracks in-tree merge cost closely.

Object and pack size, 50 revisions of realistic editing (0.5% of rows changed
per revision):

| rows | loose `.git` after 50 revs | packed `.git` | packed ÷ one copy |
|---:|---:|---:|---:|
| 1 000 | 1.48 MB | 0.104 MB | 0.78× |
| 10 000 | 10.5 MB | 0.554 MB | 0.42× |
| 100 000 | 99.6 MB | 4.85 MB | 0.37× |
| 1 000 000 (12 revs) | 293 MB | 15.0 MB | 0.11× |

Git delta-compresses these superbly. But note the **loose** column: without
`gc`, a 13 MB table under 50 revisions leaves 100 MB on disk. Auto-gc normally
handles it; a tool that writes tables in a loop must not disable it.

### 1.4 The alignment question — the design fork

**Test:** a 200-row table with a narrow column `n` holding single digits.
Change one cell from `9` to `1000` and re-pad, as a conformant writer must.
Minimal reproduction: `experiments/W4-scale/repro_padding.sh`.

```
pad:   202  202  data.tbl
nopad:   1    1  data.tbl
```

At scale, `git diff --numstat` for one such cell change:

| rows | padded | unpadded | padded diff output | unpadded diff output |
|---:|---:|---:|---:|---:|
| 200 | 202 +/202 − | 1 +/1 − | — | — |
| 1 000 | 1 002 / 1 002 | 1 / 1 | 293 744 B | 719 B |
| 10 000 | 10 002 / 10 002 | 1 / 1 | 2 930 746 B | 720 B |
| 100 000 | 100 002 / 100 002 | 1 / 1 | **29 300 748 B** | 725 B |

The padded diff is **2n lines and ~2× the file in bytes** for a one-character
semantic edit. That is a direct, unambiguous **I1 (LOCALITY) violation** — a
semantic edit of bounded size producing a byte diff of *unbounded* size.

**And it is not only cosmetic. It breaks merges.** Two branches making
genuinely disjoint edits — ours widens a cell in column `n`, theirs edits `qty`
on a row 100 000 rows away:

| rows | padded | unpadded |
|---:|---|---|
| 1 000 | **CONFLICT** | clean |
| 10 000 | **CONFLICT** | clean |
| 100 000 | **CONFLICT** | clean |

The reflow turns one side's edit into a whole-file rewrite, which overlaps
every hunk the other side produced. Under padding, **any width-changing edit
conflicts with every concurrent edit to the same table.** Pack cost for the
same two revisions at 100k rows: 6.06 MB padded vs 1.48 MB unpadded (4.1×).

**Verdict: alignment padding must go.** It is a decoration that costs I1, costs
merge correctness in exactly the class of concurrent edit the design exists to
get right, costs 98% of the file size and 4× the pack. The specified
serialization should be single-space (`| a | b | c |`); *rendering* aligned is a
view concern, exactly as "long/tidy, not wide" makes wide a view concern. If
alignment is kept for the human-facing form, it must never be what is committed,
and `render(parse(b)) == b` then forces the canonical form to be the unpadded
one. This is the one finding in W4 that changes the format itself.

A cheaper half-measure worth noting if padding is defended: dropping only the
padding *inside blank computed cells* removes 88.7% of the size tax but **none**
of the diff or merge damage, because the reflow is driven by literal columns.
It is not a fix.

### 1.5 The width problem

2 000 rows, one width-preserving cell edit.

| columns | padded max line | unpadded max / median | bytes/row padded | wraps at 120 cols |
|---:|---:|---:|---:|---:|
| 9 | 138 | 116 / 69 | 139 | 1.2 |
| 53 | 446 | 424 / 328 | 447 | 3.7 |
| 203 | 1 496 | 1 474 / 1 212 | 1 499 | 12.5 |

The diff stays 1+/1− at every width, so `git diff` remains *correct*; it stops
being *readable* somewhere between 50 and 200 columns, where one changed row
occupies 4–13 wrapped terminal lines and the reader must count pipes to find
the changed cell. Padding buys back almost nothing at width (1 496 vs 1 474)
because with many columns the max line is dominated by content, not alignment.

**The sharper width cost is concurrency, not readability.** The header line
carries the whole formula namespace, by design, so it is a single shared
mutable line. Measured on 500-row tables: two branches **adding different new
columns** conflict, and two branches **editing different columns' formulas**
conflict — at 9, 53 and 203 columns alike. That is the intended loud failure,
but the false-conflict rate scales with column count × schema-edit rate. A
200-column table is a table whose schema only one person can touch at a time.
Practical guidance: 50 columns is the usable ceiling, and the design's own
"long/tidy, not wide" rule is what keeps you under it.

---

## 2. The document format at scale

### 2.1 Boundary parse and round-trip — no problem found

| corpus | bytes | blocks | parse | round-trip | exact |
|---|---:|---:|---:|---:|---|
| 100 docs | 0.71 MB | 4 100 | 12.5 ms | 12.9 ms | 100/100 |
| 1 000 docs | 7.10 MB | 41 000 | 123 ms | 128 ms | 1000/1000 |
| 10 000 docs | 71.2 MB | 410 000 | 1.250 s | 1.287 s | 10000/10000 |
| single doc, 10 005 lines | 0.55 MB | 2 097 | 7.5 ms | 7.9 ms | exact |
| single doc, 100 004 lines | 5.50 MB | 21 055 | 85.3 ms | 84.8 ms | exact |

57 MB/s, 3.0 µs/block, flat across three orders of magnitude, and round-trip is
exact everywhere — as §7 claims, by construction. Render costs nothing measurable
over parse. **The document format has no scale problem.**

### 2.2 The block merge — the real O(n²)

`bmerge2.m3`, base + two sides, each side editing a fraction of blocks and
inserting one.

| blocks n | changed/side k | `ratio()` calls | merge time | conflicts |
|---:|---:|---:|---:|---:|
| 51 | 1 | 3 | 0.001 s | 0 |
| 101 | 10 | 123 | 0.039 s | 1 |
| 251 | 25 | 684 | 0.231 s | 2 |
| 501 | 50 | 2 621 | 0.621 s | 6 |
| 501 | 250 | 63 082 | 14.7 s | 129 |
| 1 001 | 100 | 10 250 | 2.56 s | 5 |
| 1 001 | 500 | 251 179 | **61.6 s** | 243 |
| 2 001 | 200 | 40 488 | 10.1 s | 14 |
| 2 001 | 1 000 | 1 002 374 | **362.5 s** | 500 |
| 4 001 | 80 | 6 595 | 1.75 s | 2 |
| 4 001 | 400 | 160 945 | 65.8 s | 41 |
| 8 001 | 160 | 26 000 | 10.6 s | 1 |

**The complexity is not O(n²) in blocks. It is O(k²) in *changed* blocks, and
independent of n.** `ratio_calls ≈ k²` fits every row (k=100→10 250;
k=200→40 488; k=500→251 179; k=1000→1 002 374). The exact-hash pre-pass already
removes all unchanged blocks from the candidate pool, so document *size* is
nearly free; what costs is *edit size*. Per-call cost is ~250–360 µs on
realistic paragraphs.

There is still a hidden O(k·n): the residue loop iterates the full base list
per unmatched block even to skip `used` entries, and `m3`'s final
`if raw not in out` is a linear list scan.

**Where it becomes unusable:** k ≈ 300 changed blocks per side is 10 s;
k ≈ 500 is 1 minute; k ≈ 1 000 is 6 minutes. EXTRAPOLATED at k²·330 µs:
k = 2 000 → ~22 min, k = 5 000 → ~2.3 h. Editing 300 paragraphs is not exotic —
it is one rebase of a long-lived branch, or one pass of a copy-editor over a
book chapter.

**Cheapest fix that preserves correctness — measured.** Since
`ratio = 2M/(la+lb)` and `M ≤ min(la,lb)`, `ratio > t` implies
`min/max > t/(2−t)`; at t = 0.5 that is `min/max > 1/3`. So a sorted length
index gives a **sound** candidate window (no false negatives, provably), and
`difflib`'s own `real_quick_ratio()`/`quick_ratio()` are upper bounds that
prune before the real comparison. Reusing one `SequenceMatcher` with `seq2`
fixed also builds the `b2j` index once instead of per pair.
`e2_doc.match_fast` does all three in ~25 lines:

| blocks | changed | current | fixed | speedup | identical matching? |
|---:|---:|---:|---:|---:|---|
| 101 | 10 | 0.019 s | 0.0054 s | 3.5× | yes |
| 501 | 50 | 0.298 s | 0.060 s | 5.0× | yes |
| 1 001 | 100 | 1.251 s | 0.282 s | 4.4× | yes |
| 2 001 | 200 | 5.687 s | 1.173 s | 4.8× | yes |

Identical output at every size. That moves the 10-second wall from k ≈ 300 to
k ≈ 650. It does **not** remove the k², so the structural recommendation is:
keep the hash pre-pass, add the length window + quick-ratio prune now (cheap,
sound, verified), and if k in the thousands ever matters, replace candidate
generation with a token-shingle inverted index — that is the only change that
takes k² to near-linear, and it can be added behind the same `match()`
signature.

### 2.3 A silent-wrong merge found on the way

`m3`'s de-duplication guard `if n not in mt and raw not in out` drops a
their-side **new** block whose text happens to equal a block already emitted.
Reproduced: base = A,B,C; ours unchanged; theirs adds a second copy of "Alpha
line." Result: the added block is **silently discarded**, no conflict, no
warning. This is an eighth item for the DESIGN.md appendix, and it is the same
species as correction 1 — content equality standing in for identity.

---

## 3. The derivation graph at scale

Graphs of N artifacts, half `.tbl` (20 rows each, 30% of them declaring a
dependency on another table), half `.md` with 3 references each.

### 3.1 Cold, warm, incremental

| artifacts | cold | warm | incremental (one leaf touched) | warm cache hits | opens/resolve |
|---:|---:|---:|---:|---:|---:|
| 100 | 0.059 s | 0.035 s | 0.036 s | 150/150 | 4.95 |
| 1 000 | 0.560 s | 0.364 s | 0.368 s | 1 500/1 500 | 4.98 |
| 10 000 | 5.72 s | 3.78 s | 3.76 s | 15 000/15 000 | 5.15 |

**The cache buys 1.5×.** With a 100% hit rate and zero recomputation, warm is
only a third faster than cold, and incremental after touching one leaf is
indistinguishable from warm.

### 3.2 Why: the closure hash is the whole cost

`closure_hash` is **83.2 / 83.8 / 84.2%** of warm build time at 100 / 1 000 /
10 000 artifacts. It runs on *every* `value()` call, re-reads and re-SHA-256s
every file in the transitive closure, and `refs()` re-reads each file again to
find the edges — ~5 `open()` calls per resolve.

Yes, it is O(closure) per lookup, and the answer to "how badly" is: **badly
enough that content addressing currently costs more than the work it protects.**
DESIGN.md §9 rates artifact-granularity hashing at 2.3% of the parse it guards;
that measurement was made on a single artifact with no dependencies. As soon as
the closure has depth, the ratio inverts.

Deep chain (artifact *i* depends on *i−1*):

| depth | `closure_hash` alone | cold resolve of tip | warm resolve of tip | file opens |
|---:|---:|---:|---:|---:|
| 1 | 0.15 ms | 0.88 ms | 0.22 ms | 5 |
| 10 | 1.45 ms | 2.03 ms | 1.55 ms | 23 |
| 50 | 7.61 ms | 8.42 ms | 8.10 ms | 103 |
| 100 | 15.8 ms | 15.3 ms | 14.9 ms | 203 |
| 200 | 30.3 ms | 31.4 ms | **31.9 ms** | 403 |

~150 µs and 2 file reads per link. From depth ~25 upward **the warm path is no
faster than the cold path**, because computing the cache key costs as much as
the computation the key protects. A full build of a d-deep chain with one
consumer per level is superquadratic in practice: 0.795 s at 100, 3.21 s at
200, **20.15 s at 400**.

### 3.3 Wide fan-in

One 200-row hub table referenced by W documents:

| fan-in | cold | warm | after editing the hub |
|---:|---:|---:|---:|
| 10 | 0.016 s | 0.012 s | 0.015 s |
| 100 | 0.125 s | 0.119 s | 0.125 s |
| 1 000 | 1.214 s | **1.209 s** | 1.502 s |

Warm equals cold. The hub is opened and hashed once per referring document —
5 000 `open()` calls for 1 000 references.

### 3.4 The fix, measured

Two variants were implemented and benchmarked (`e3b_fix.py`, `e3c_dag.py`):

1. **Per-build memo at the top level** (~10 lines): **2.6–2.7×** on realistic
   graphs at 100 / 1 000 / 10 000 artifacts. It does not fix chains, because
   `closure_hash` threads a shared `seen` set through the recursion, which makes
   a node's returned value depend on which nodes were visited first — so it
   cannot be memoised per node as written.
2. **Restructure to a proper DAG hash**, `H(a) = sha256(bytes(a) ‖ sorted(H(d)
   for d in deps(a)))`, with a per-node memo, a `refs` memo, and an explicit
   recursion stack (~25 lines). Same invalidation semantics — a deep edit is
   still detected — and:

| chain depth | current engine | DAG hash | speedup |
|---:|---:|---:|---:|
| 10 | 0.0097 s | 0.0027 s | 3.6× |
| 50 | 0.211 s | 0.0104 s | 20.3× |
| 100 | 0.795 s | 0.0226 s | 35.1× |
| 200 | 3.212 s | 0.0423 s | 76.0× |
| 400 | 20.150 s | 0.2153 s | **93.6×** |

This is a small, local change to `derive.py` and it is the difference between a
derivation engine that scales and one that doesn't.

### 3.5 Cycle detection — there is none

| input | shipped engine | time |
|---|---|---:|
| 2-cycle `a → b → a` | returns hash `2cc20006fbb8`, **no error** | 0.35 ms |
| 100-artifact ring | returns hash `6f690e4b302c`, **no error** | 15.0 ms |
| self-reference `s → s` | returns hash `c67122b7e864`, **no error** | 0.16 ms |

Cheap, because the shared `seen` set terminates the walk — but it terminates it
by *silently truncating the closure*, which is the same failure shape as the
stale-cache defect the closure hash was introduced to fix. A cycle is a
representation error and I3 requires it to fail loudly. The DAG rewrite gets
this for free: `reference cycle: x.tbl -> y.tbl -> x.tbl` and
`reference cycle: s.tbl -> s.tbl`, at no measurable cost.

### 3.6 Two prototype/spec divergences found while building fixtures

- `key := id`, shown in DESIGN.md §7's `.tbl` example, is **rejected** by
  `tbl.py` as a malformed aggregate declaration (the grammar demands
  `name := fn(col)`).
- `unit = rates.tbl#rate`, the cross-table column formula in the design's own
  `experiments/L5-derivation/budget.tbl`, **crashes** `tbl.evaluate` with
  `ValueError: Attribute(...)`, and the `rates.tbl` beside it is a zero-byte
  file. Cross-artifact references therefore exist today as *dependency edges
  the engine discovers* but not as *values it can resolve*. Every table→table
  edge in §3 above is an edge only; the numbers measure the engine, not an
  evaluator that does not yet exist.

---

## 4. Realistic repo — a year of use

2 000 artifacts: 600 `.tbl` (5 × 20 000 rows, 95 × 1 000, 500 × 20–200),
1 200 `.md` (15–60 blocks, 60% carrying a `{{ table#agg }}` reference),
150 `.canvas`, 50 binary attachments (0.1–2 MB). 4 998 commits of realistic
editing weighted to a hot working set (60 tables, 150 documents), 1–3 files per
commit.

| | |
|---|---:|
| working tree | 95.6 MB |
| `.git` loose, after 5 000 commits, no gc | 177.8 MB |
| `.git` packed | **11.86 MB** |
| `git repack -ad` | 7.86 s |
| objects in pack | 26 303 |
| commit throughput | 32.1 ms each (5 000 in 160.6 s) |
| `git status --porcelain` | **4.0 ms** (6.1 ms cold) |
| `git log --oneline` (all) | 27.3 ms |
| `git log` on the most-edited file (63 of 4 998 commits) | **444 ms** |
| `git log --follow` on it | 569 ms |
| `git blame` on it | 523 ms |
| `git grep` across the tree | 173 ms |
| `git diff HEAD~50 HEAD --stat` | 27.8 ms |
| `git clone` (local) | **262 ms**, 106 MB |
| `git clone --no-hardlinks` | 273 ms |
| `git clone --depth 1` | 687 ms, 102.6 MB |
| full `check` (parse 600 tables + parse/round-trip 1 200 docs) | **1.06 s**, 1 800 ok, 0 failures |
| full `build` cold (740 references resolved) | 10.46 s |
| full `build` warm | 3.80 s |

**This is comfortably usable.** Nothing here is near a wall. Two observations:

- `git log` on one file is 444 ms for a file with 63 commits, confirming the
  prior result that it is O(*total* commits): 17× the cost of `log --oneline`
  over everything. EXTRAPOLATED linearly, 50 000 commits ≈ 4.4 s per
  file-history query — which is where a "show me this artifact's history" UI
  starts needing a commit-graph or an index of its own.
- Packing matters more than it looks: 178 MB loose against 11.9 MB packed. Any
  agent or watcher that commits in a tight loop with `gc.auto` disabled will
  make a 96 MB repo look like a 270 MB one.
- `build` warm at 3.80 s for 740 references is the §3.2 defect showing up in the
  realistic case: with the DAG hash it should be well under a second.

---

## 5. What forces a design change before planning

1. **Drop alignment padding from the canonical `.tbl`.** A one-character edit
   that widens a column produces a 2n-line diff (100 002 lines / 29.3 MB at
   100k rows) and turns disjoint concurrent edits into conflicts at every size
   tested. It costs I1 outright and costs I6 in practice. Single-space
   serialization gives 1-line diffs and clean merges at every size, halves the
   file, and quarters the pack. Aligned rendering is a view.
2. **Rewrite `closure_hash` as a memoised DAG hash with explicit cycle
   detection.** As shipped it is 84% of every warm build, makes the cache worth
   1.5×, makes warm equal to cold beyond depth 25 and at fan-in 1 000, and
   returns a hash for a reference cycle instead of an error. The replacement is
   ~25 lines and measured at 2.6× on flat graphs and 93.6× on a 400-deep chain.
3. **Add the sound length/quick-ratio prune to block matching now** (4.4–5.0×,
   output identical), and treat k — blocks changed per side, not document size —
   as the parameter the merge is quadratic in. Publish the limit: past ~300
   changed blocks per side the similarity merge is not interactive.
4. **`bmerge2` silently drops a their-side added block that duplicates existing
   text.** Content equality is standing in for identity again. Add to the
   conformance suite before the code is written.
5. **State the ceilings in the spec**, since they are properties users will hit:
   `.tbl` evaluate is comfortable to ~300k rows and memory-bound at ~500k;
   50 columns is the readable/mergeable width limit; the header line is a
   serialization point for all schema edits.
6. **`key := id` and cross-table column formulas are in DESIGN.md and not in the
   reference implementation.** Milestone 0's conformance suite should assert on
   both, or the spec should drop them.

Nothing found here threatens the architecture. The document format is fast and
exact at every size tested; git is comfortable with a realistic year-old repo;
the table format's byte overhead largely disappears under compression. The two
things that genuinely break are a *decoration* (padding) and an *implementation
shortcut* (the closure walk) — both fixable now, and both much cheaper to fix
before a repo exists than after.
