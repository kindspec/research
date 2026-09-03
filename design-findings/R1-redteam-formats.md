# R1 — Red team: silent-wrong outcomes in the proposed formats

Adversarial pass. The only target is SILENT-WRONG: a merge or an evaluation
that succeeds cleanly and yields an incorrect result, with no conflict, no
error and no marker. A legitimate conflict is not a win and is recorded as a
loss for the attacker.

All reproductions are runnable:

    cd experiments && sh R1-common/run_all.sh

Every merge below is **stock `git merge`** in a fresh repo with no
`.gitattributes`, no merge driver and no config beyond `user.name`/`user.email`
(`experiments/R1-common/gw.py`).

Severity key, as requested:

    (a) silent-wrong under stock git
    (b) silent-wrong under our tooling
    (c) legitimate-but-terrible UX
    (d) cosmetic

---

## 1. Catalogue, ranked

### (a1) The `.tbl` AGGREGATE namespace is scattered — the exact defect PASS4 diagnosed in markdown, inside the format PASS4 held up as the safe contrast

`experiments/R1-table/t1_namespace.py`

PASS4: *"column names are all declared on ONE line, so a name collision IS a
line collision"*. True — and irrelevant, because the aggregate namespace is one
binding per line in the trailing block.

    $ cd experiments/R1-table && python3 t1_namespace.py
    --- T1a duplicate AGGREGATE name, added at different offsets ---
    git merge exit=0 (CLEAN) markers=0
    merged trailing block:
        key   := id
        subtotal := sum(qty)
        grand := sum(total)
        count := count(id)
        subtotal := sum(total)
    evaluated: {'subtotal': 480.0, 'grand': 480.0, 'count': 4}
    Alice meant subtotal=sum(qty)=43.0; Bob meant subtotal=sum(total)=480.0
    RESULT: subtotal = 480.0  -- one author silently lost, no marker

Same shape as `V-mdref`'s `[api]` label. The rule "co-locate a namespace's
bindings" was stated in PASS4 and then not applied to the format's own second
namespace. `{{ budget.tbl#subtotal }}` resolves, to one of two things.

Sub-case T1b: the two names differ only by Unicode normalisation (`café` NFC vs
NFD). Merge is clean; the NFD declaration does not even match the aggregate
regex (`\w` does not match U+0301), so it is **silently skipped** — I7's
"unknown lines -> error, not skip" is violated by the reference parser — and
the NFC binding answers to a name that renders identically.

Sub-case T1c: the same NFC/NFD collision in a COLUMN name does conflict, because
the header is genuinely co-located. That half of PASS4's claim holds.

### (a2) The grammar has no escaping rule: one pipe in a cell shifts every field and changes the arithmetic

`experiments/R1-table/t3_shift.py`

    --- T3a a product code containing a pipe ---
      source row      : | r_0002 | 10|12    |   3 |  8.00 |     (qty 3 @ 8.00 = 24)
      parsed row      : {'id': 'r_0002', 'item': '10', 'qty': '12', 'unit': '3', 'total': 36.0}
      grand           : 156.0   (truth: 120 + 24 = 144)

    --- T3b the same defect arriving through a CLEAN stock-git merge ---
      git merge exit=0 markers=0
      grand = 360.0   (truth: 120 + 120 + 0 = 240)

Alice renames an item; Bob edits a distant row. Clean merge, plausible file,
50% error. GFM defines `\|`; PASS5's grammar defines nothing and `split_row`
implements nothing. `dict(zip(cols, vals))` then truncates or misaligns
silently.

### (a3) `prev.` is a coordinate, and it reintroduces the 480-vs-660 defect the format exists to remove

`experiments/R1-prev/p3_prev_is_a_coordinate.py` (with `tblprev.py`, a minimal
implementation of PASS5's proposed operator).

`prev.balance` addresses *the row above*. That is a place, not a name. I2:
*"Nothing may be referenced by a coordinate that a concurrent edit can change."*

    --- P3b Alice inserts a row NEAR THE TOP; Bob edits a row NEAR THE BOTTOM ---
      git merge exit=0 (CLEAN) markers=0
      Bob committed            closing=-273.80  low=-273.80
      MERGED                   closing=218.68   low=218.68
      Bob's row r_0008 (jul) balance: he saw -273.80, the file now says 218.68

A row Bob did not touch, whose formula nobody edited, changed value because a
row was inserted above it. This is structurally identical to the A1 range that
L1 was celebrated for eliminating. Any format-level defence is impossible: the
operator's meaning *is* the position.

Corollary (P1c): `sum` survives a reorder because addition is commutative;
`min(balance)` — an overdraft check — does not. `prev.` silently converts a
commutative aggregate into a non-commutative one.

### (a4) A rename makes a DIFFERENT column answer to the old name; the cross-artifact reference still resolves

`experiments/R1-derivation/d1_meaning_drift.py`

    --- D1a a column rename makes a DIFFERENT column answer to the old name ---
      base   : grand = 576.00  (inc-VAT, which is what the report quotes)
      Alice  : grand = 480.00  (the SAME aggregate line, ex-VAT now)
      git merge exit=0 (CLEAN) markers=0
      merged : grand = 504.00
      header : | id | item | qty | unit  | total = qty * unit | gross = total * 1.2 |
      aggregate line, untouched by anyone: 'grand := sum(total)'
      The document now asserts 504.00 where the truth is 604.80. Off by 100.80.

Alice does an ordinary rename pass on ONE line (`total`->`gross`,
`net`->`total`). `grand := sum(total)` is untouched and now sums a different
column. `{{ budget.tbl#grand }}` resolves with no `#REF!`. This is the most
dangerous class in the whole design because the loud-failure machinery is
working exactly as specified — nothing is broken, the meaning moved.

D1b (redefining the aggregate) and D1c (deleting the column the name once
referred to) are the same defect in two other spellings.

### (a5) The canvas node namespace is scattered, and `@layout` has no referential integrity

`experiments/R1-canvas/c1_canvas.py`

    --- C1a an @layout override for a node DELETED on the other branch ---
      git merge exit=0 (CLEAN) markers=0
      nodes declared in merged file: ['api', 'auth', 'queue', 'work']
      positions returned by layout(): ['api', 'auth', 'db', 'queue', 'work']
      ==> layout() returns a position for ['db'], a node that does not exist.

`pos.update(over)` *inserts* the dangling override. A renderer iterating the
layout draws a deleted node.

    --- C1b an EDGE to a node renamed on the other branch is silently dropped ---
      git merge exit=0 (CLEAN) markers=0
      DANGLING edges: [('api', 'db')]
      layout() output: ['api', 'auth', 'pg', 'queue', 'work']

`if b in depth and a in depth` skips it. Bob's new edge vanishes from the
diagram with no error.

    --- C1c two branches add DIFFERENT nodes with the SAME name ---
      git merge exit=0 (CLEAN) markers=0
      nodes: [('cache','Redis'), ..., ('cache','Memcached')]
      layout() gives ONE position for "cache": (420, 80)

One node per line = a scattered namespace = the `[api]` defect again.
`arch.canvas#cache` now names two things.

### (a6) Markdown has four scattered namespaces, not one

`experiments/R1-doc/m1_namespaces.py` (resolved with real pandoc)

    --- M1a duplicate FOOTNOTE label ---
      git merge exit=0 (CLEAN) markers=0
      definitions present in file: 2
      rendered footnote text: ['Bob's footnote.', 'Bob's footnote.']

Both markers render Bob's text. Alice's footnote content is gone.

    --- M1b duplicate HEADING ANCHOR {#id} ---
      git merge exit=0 (CLEAN) markers=0
      ids emitted by pandoc: ['s1','findings','s3',...,'findings','s11','s12']

`q3-review.md#findings` — the design's own worked example from PASS5 — now
names two blocks.

    --- M1d duplicate YAML FRONTMATTER keys ---
      git merge exit=0 (CLEAN) markers=0
      yaml.safe_load -> {'id': ..., 'owner': 'bob', 'status': 'draft'}

Adjacent lines are not co-location. Git needs the SAME line. Frontmatter is a
scattered namespace too.

M1e (no reproduction, no mechanism exists): `cp doc.md copy.md` duplicates the
minted artifact UUID, and `.notes/` is keyed by it. Every standoff annotation
then attaches to two documents.

### (a7) One blank line silently reformats every item in a list

`experiments/R1-doc/m2_blocks.py`

    --- M2e ---
      git merge exit=0 (CLEAN) markers=0
      before: <li> items wrapped in <p>: 0 of 4
      after : <li> items wrapped in <p>: 4 of 4

Markdown list looseness is "one line encodes a property of every other line" —
PASS4's own catalogued defect — and the design adopts markdown unchanged.

### (b1) The type-aware merger is LESS correct than stock git

`experiments/R1-table/t2_rowid.py`

    --- T2a copy-paste duplicates a row id, then the two copies diverge ---
      stock git: exit=0 markers=0 rows=5 grand=684.0
      entity-map merge3: conflicts=0 rows=5 grand=744.0
      merge3 keyed rows by id, so dict(entities) kept only the LAST r_0002;
      BOTH r_0002 rows then rendered with qty=30. grand wrong by 60.0.

    --- T2b both branches mint the same id ---
      stock git: exit=0 grand=660.0 (both rows kept, duplicate key in file)
      merge3   : conflicts=3 grand=560.0

    --- T2c an invisible character splits one row into two ---
      stock git : exit=1 markers=3   <-- correct: same row, two values
      merge3    : conflicts=0 rows=4 grand=600.0
      Alice's edit is SILENTLY DROPPED.

PASS4/I6: *"Type-aware merge may only improve the EXPERIENCE, never the
CORRECTNESS."* Here it changes the correctness in the wrong direction, twice,
silently. Also note: nothing enforces `key := id`. `tbl.parse` rejects duplicate
COLUMN names and accepts duplicate ROW ids without comment.

### (b2) The content-addressed cache never invalidates on a cross-artifact dependency

`experiments/R1-derivation/d2_cache.py`

    first evaluation      : grand = 2400.00   {'hit': 0, 'miss': 2}
    after rates.tbl 20->25: grand = 2400.00   {'hit': 1, 'miss': 0}
    truth: 10 * 12.00 * 25 = 3000.00

The key is `h('resolve', artifact, name, sha256(artifact_bytes))` — one
artifact's bytes. L5 claims *"invalidation is exact"*. It is exact only for
single-artifact derivations, which is precisely the case the design says is not
the interesting one. Two machines on the same commit render different numbers,
which is also a direct I4 violation (the cache is hidden state affecting output).

### (b3) Numeric semantics are unspecified, so two conformant implementations disagree

`experiments/R1-table/t4_numbers.py`

    left fold, order (open,fee,close) = 0.0
    left fold, order (open,close,fee) = 1.0
    CPython sum()                     = 1.0 / 1.0

The reference evaluator HELD only because CPython >= 3.12 uses Neumaier
compensated summation inside `sum()`. Any left-fold implementation (JS, Rust,
SQL, python < 3.12, a spreadsheet) disagrees, and disagrees differently
depending on row order — which stock git reorders cleanly (T4b: base
left-fold total 0.0 -> merged 1.0, exit=0, markers=0).

Related, all silent: `float('nan')` and `float('inf')` are accepted and poison
an aggregate without tripping the `#REF!` path; `'1_000'` parses as 1000.0;
fullwidth and Arabic-Indic digits parse. Conversely `'12,50'`, `'1,234.00'` and
`'(500)'` are rejected loudly — so locale handling is half-safe, which is worse
than uniformly unsafe because it teaches false confidence.

### (b4) I3's error propagation is not uniform: some bad cells raise instead of producing `#REF!`

`experiments/R1-table/t5_formulas.py`

    blank          -> grand = '#REF!(unit)'      correct
    missing field  -> grand = '#REF!(unit)'      correct
    dash "-"       -> ValueError, whole evaluation aborts
    N/A            -> ValueError, whole evaluation aborts
    aggregate over a deleted column -> TypeError (float(None))

Loud, so not silent-wrong — but the error does not *propagate*, it aborts, so an
unrelated aggregate in the same file cannot be computed either. I3 as specified
("errors propagate through aggregates") is only implemented for one of the
several ways a cell can be bad.

### (c1) Column insert / reorder still produces whole-file conflicts that destroy the artifact

`experiments/R1-prev/p2_reorder_lost.py`, `R1-suite/s1_suite_holes.py` S1c.
Every conflicting case leaves a file `tbl.evaluate` refuses — I5 violated, as
L1 already recorded. Not a new finding; confirmed as still true and still
untested.

### (c2) A formula edit silently re-scopes existing and future rows

T5a: Alice adds VAT to the column formula, Bob adds a zero-rated line item.
Clean merge, VAT applied to Bob's row. Mechanically legitimate; no
representation can catch it. Listed so it is not mistaken for a break.

### (d1) blocks.py block identity is positional and unstable

`experiments/R1-doc/m2_blocks.py` M2a–M2c: block names are content hashes with
an ORDINAL suffix (`h`, `h.1`). `.1` means "the second one", which is a
coordinate; inserting a third copy above renames the others, so a stored
reference retargets. And editing a block renames it, which PASS5 R1 already
measured and rejected for rows ("content hash: SPLIT ROW") while leaving it in
place for blocks. Ranked (d) only because nothing in the current design stores
these names; it becomes (a) the moment block references exist.

M2d: `blocks.py` splits a valid CommonMark 4-backtick fence into two blocks with
two names, while `render(parse(b)) == b` still passes.

---

## 2. What held up under attack — negative results I trust

These were attacked and did not break. Each is a real defence, not a gap in the
attack.

1. **No coordinates in the base table grammar.** The L1 660 result is genuine
   and I could not reconstruct the 480 failure without introducing `prev.`.
   Row inserts, distant cell edits and column additions all behave.
2. **The column-name namespace is genuinely co-located.** Every collision I
   tried on the header line conflicted, including the NFC/NFD one (T1c).
   Two branches editing the same column formula conflict (T5b).
3. **`#REF!` propagation works** for the cases it covers: a formula naming a
   nonexistent column poisons the aggregate rather than summing what it can
   (T5d), including when the column is added only on the other branch.
4. **The address grammar is file-qualified**, so two artifacts defining the same
   name cannot collide (D1d). This is the one place the grammar genuinely earns
   its keep.
5. **Cross-file reference cycles fail loudly** while the cache is cold — the
   stack check fires and raises (D2b). I tried and failed to construct a cached
   fixed point that terminates silently.
6. **Merge order does not decide the answer.** Six merge sequences over three
   concurrent branches (two inserts and a row move) with a compounding `prev.`
   formula: `experiments/R1-prev/p4_confluence.py` reports **1 distinct outcome
   out of 6 orders**. I expected non-confluence here and did not find it.
7. **Reorder + edit of the reordered row conflicts**, it does not silently lose
   an update (p2). Note this qualifies L1 Result 4 in the *safe* direction: the
   clean-and-correct reorder merge reported there does not generalise, but the
   failure mode is a conflict, not a loss.
8. **`blocks.py` round-trip is byte-exact** on everything I threw at it,
   including the fence cases where its boundaries are wrong. I1's *letter* is
   unbreakable by construction — see below for why that is a problem.
9. **The layout function is deterministic** given a fixed file: 20 runs, one
   result (C1e).
10. **`tbl.parse` rejects conflict markers** on every path I could reach,
    including inside the trailing block. I7's headline case is solid.
11. **A second table appended to the same file** produces a loud `ValueError`
    rather than a wrong number (T3e).
12. **Blank and missing cells** produce `#REF!`, not zero (T5e). The specific
    "never zero" promise in I3 holds.

---

## 3. Tests the conformance suite is missing

`experiments/R1-suite/s1_suite_holes.py`

**The suite's `.tbl` round-trip test is a tautology.** `run_suite.py` defines
`tbl_parse(b) -> b` and `tbl_render(x) -> x`, so `conform.py` asserts
`doc == doc`. It cannot fail for any parser on any corpus. The `.tbl` format has
zero round-trip coverage, for the invariant the design says must be a property
test rather than a guideline.

**Mutation check.** Sabotaging `tbl.parse` to silently discard rows leaves the
entire `.tbl` half of the suite GREEN (S1b) — I1, I3, I6 and I7 all pass.

**I5 is never tested.** Every "expect conflict" case scores `ok` and stops. The
files those cases leave in the working tree are unparseable by their own format
(S1c). The suite's notion of correct is "clean vs conflict", which is exactly
the distinction I5 says is insufficient.

Tests it does not contain:

    - I1 round-trip for .tbl at all (currently a tautology)
    - I1 round-trip on MERGED output, not just hand-written corpora
    - I5: is the post-conflict working tree parseable by its own format?
    - confluence: merge(A,B) vs merge(B,A), and orders over 3+ branches
    - duplicate ROW ID -- `key := id` is declared and nothing enforces it
    - duplicate AGGREGATE name (the scattered namespace found above)
    - a row whose field count differs from the header (silent zip truncation)
    - a cell containing the delimiter (no escaping rule exists)
    - numeric coercion: locale, nan/inf, unicode digits, float associativity
    - evaluation order-independence: same rows, different order, same answer?
    - the ADDRESS GRAMMAR: nothing in the suite resolves artifact#namepath
    - cross-artifact derivation and cache invalidation (derive.py untested)
    - .canvas: the third native format has NO conformance coverage at all
    - the `prev.` operator: proposed in PASS5, implemented nowhere, untested
    - git merge-tree in a BARE repo -- the path PASS4 proved behaves differently
      and R5 makes load-bearing
    - CRLF, BOM, non-UTF8 bytes, missing trailing newline for .tbl
    - unicode normalisation (NFC/NFD) of any name in any namespace
    - corpus size: .tbl has ONE document; property tests need generation
    - a mutation gate: does the suite fail when the parser is sabotaged?

Two structural criticisms of the suite's design, beyond coverage:

- **It tests the implementation's agreement with itself.** `evaluate` is used to
  both produce and check the answer, so a parser bug that is consistent across
  the corpus is invisible. Expected values should be computed independently
  (by hand, in the case table), which `ev_expect` does for two cases and not
  for the rest.
- **`render(parse(b)) == b` is satisfiable by a parser that understands
  nothing** (M2d). Boundary-only parsing makes I1 free *and* makes it vacuous as
  evidence that the entity map is right. It needs a companion law — something
  like "moving a block by name and rendering equals the hand-edited file" — or
  it is measuring the wrong thing.

---

## 4. Judgement: achievable, or marketing?

Split by invariant. This is not a uniform verdict and should not be reported as
one.

**I1 LOCALITY — achievable, and already achieved, but currently self-certifying.**
Boundary-only parsing does deliver byte-exact round-trip, and I could not break
it. The problem is that it is *unfalsifiable as stated*: a parser that produces
garbage boundaries passes (M2d), and the suite's version of the test is a
literal tautology. Real, but the evidence for it is not.

**I2 NOMINAL ADDRESSING — achievable for the base table, and violated by three
things the design already contains or proposes.** `prev.` is a coordinate
(a3). `blocks.py`'s `.1` suffix is a coordinate (d1). Graphviz/dagre layout is a
function of declaration order, which a merge decides (C1d/C2: the same graph,
declarations reordered, gets different coordinates from `dot` 2.42.4) — so
"positions are derived, therefore not coupled state" relocates the coupling into
the layout function rather than removing it. The invariant is enforceable by
grammar only if the grammar refuses to grow the operators users will demand,
and `prev.` is the first one and it was already conceded.

**I3 LOUD FAILURE — half-implemented and, more importantly, aimed at the wrong
failure.** It catches broken references. The dangerous case is a reference that
still resolves to a different thing (a4), and no amount of loudness helps: the
system cannot know the meaning moved. Nothing in the design binds a name to a
meaning — no types, no units, no declared semantics on an aggregate — so a
rename pass is indistinguishable from a re-pointing. This is the finding I would
act on first.

**I4 NO HIDDEN STATE — violated by the design's own cache (b2).** Two machines
at the same commit produce different numbers. Fixable (hash the transitive
dependency set), but currently false.

**I5 VALID ARTIFACTS — aspirational under stock git, full stop.** Every conflict
in every experiment leaves a file its own format rejects. PASS4 already
established that `-merge` protects clients and not forges. R5's answer (own the
server) is correct and it means I5 is *not* an invariant of the format; it is a
property of a deployment. It should be worded that way.

**I6 STOCK-GIT CORRECTNESS — the sharpest invariant in the design, and the one
the evidence most clearly contradicts.** Seven independent (a)-class breaks
above are clean stock-git merges producing wrong answers. None of them needs an
exotic scenario: a duplicate aggregate name, a pipe in a product code, a rename
pass, a copy-pasted row, two people citing the same source, a nudge to a deleted
box. What the results actually show is a narrower and still-valuable claim:

    Stock git merges CORRECTLY when the unit of merge is the unit of meaning
    AND every namespace in the artifact is co-located on one line.

PASS4 found the first clause and stated the second as a rule, then did not audit
the formats against it. Doing that audit is most of the fix list: aggregates,
canvas nodes, canvas edges, markdown link labels, footnote labels, heading
anchors, block ids and frontmatter keys are all scattered namespaces, and every
one of them produced a silent-wrong in this pass.

**I7 STRICT PARSING — correct as a principle, not implemented.** The conflict
marker check is real and works. Everything else is permissive:
`[l for l in lines if l.strip().startswith('|')]` skips silently (T3c/T3d), the
aggregate regex skips any line it does not match (T1b), `zip` truncates rows,
duplicate row ids are accepted, and `float()` accepts more than the format
means. Each is one line, and each converted a loud failure into a number.

### Overall

Not marketing. The representation discipline is real and it demonstrably kills a
whole class of failure — items 1–12 in section 2 are not small. But the
invariants as written are **claims about a format, and most of the breaks live in
the places the format does not reach**: a second namespace nobody audited, an
operator that was conceded in one line of PASS5 without being tested, a cache
key, a layout library, and the fact that a name has no bound meaning.

The two changes with the highest yield, one line each as requested: (i) apply
PASS4's own co-location rule to *every* namespace in *every* format, mechanically,
as a conformance test; (ii) make `prev.` illegal, or make row order an explicit,
named, mergeable property rather than an emergent one — it cannot be both
semantically load-bearing and "irrelevant to merge".
