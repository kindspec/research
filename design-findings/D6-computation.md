# D6 — The computation and structured-data model

Research date 2026-08-28. Builds on `L1-nominal-merge-results.md` (named columns
merge correctly where A1 merges silently wrong), `L5-derivation-results.md`
(a 40-line content-addressed derivation engine invalidates exactly), and
`PASS3-invariants.md` (I1 locality, I2 nominal addressing, I3 loud failure,
I4 no hidden state, I5 valid artifacts).

Everything marked **[measured]** was run here; the harnesses are in
`experiments/D6-computation/`. Everything else is a fetched primary source with
a URL. Where a source could not be verified it says so.

---

## 0. The answer in one page

**The core abstraction is the NAMED, ORDERED ENTITY MAP EVALUATED BY A
DEMAND-DRIVEN, CONTENT-ADDRESSED REBUILDER — one engine, one namespace, at
column-or-coarser granularity, with no derived value in any committed file.**

Concretely, five commitments, each of which a measurement below either forced
or corrected:

| # | Commitment | Forced by |
|---|---|---|
| C1 | Formulas attach to **columns**, not cells | §4 measurement: per-cell memoisation costs **21× the arithmetic it protects**; Grist's per-column graph; Excel Tables' calculated columns |
| C2 | The engine is **one** suspending-scheduler / constructive-trace rebuilder for formulas, transclusion and export | *Build Systems à la Carte* §5.2 + L5 + §5 falsification below |
| C3 | Every name lives in **one flat single-assignment namespace**; a duplicate name is a hard error | §2 measurement: this is the *only* thing that turned a silently-wrong merge into a loud one |
| C4 | Row identity is a **declared key, else an explicit opaque id column**; never a content hash, never a position | §6 ablation: content-hash identity silently *splits a row in two*; a natural key silently *loses an edit* |
| C5 | **No derived value is ever committed** | §3 measurement: committing results turns a correct 660 into either a silent falsehood or a conflict offering two wrong answers |
| C6 | Canonical form is **tidy/long plaintext, key-sorted, one record per line, with an OPTIONAL Table Schema sidecar**; binary is cache-only | §10: wide-form conflicted where long merged; CSVW archived 2026; Parquet bytes vary by writer and row-group size |

Two honest negatives:

- **The correctness case for types and units is not empirically supported**
  (§8.5), and the field's leading error researcher names strong typing as an
  unproven prescription that may *increase* errors. The correctness case that
  *is* supported is different and stronger — reviewability — and it is the one
  this project is uniquely placed to make (§8.4).
- **There may be no data structure that can replace the flexible grid** for
  authoring (§9.2, Chalhoub & Sarkar CHI 2022, stated as a finding, not a
  conjecture). The design must therefore not try to; it must be the *storage and
  review* form for something a grid can still edit. And ~93% of real
  spreadsheets contain no formula at all, so a blank table must be the cheapest
  artifact in the system.

---

## 1. Is "spreadsheet" the right frame?

No. It is one configuration of something more general, and the historical
evidence says the *frame* is where the previous attempts died, not the maths.

### 1.1 The frame that failed: Improv

Lotus Improv (1991) is the strongest historical evidence against the named
thesis, and the case must be stated at full strength before it is answered.

Improv separated three things — data, formulas, views — the way this design
proposes to. Pito Salas's founding idea, per Simson Garfinkel's contemporaneous
*NeXTWORLD* account:

> "the raw data in a spreadsheet, the way that the user views the data, and the
> formulas used to perform calculations can all be separated from each other.
> The formulas should be general, so that the user can type something like
> `PROFIT=PRICE-COST` and have the spreadsheet calculate every PROFIT cell from
> its corresponding PRICE and COST cells."
> — <https://simson.net/clips/1991/1991.NW.Improv.html>

It died. The distribution explanations (NeXTSTEP-only launch, Windows port in
1993, 1-2-3 cannibalisation, "Lotus' sales and marketing teams… did not know how
to sell Improv into the market, so they simply didn't") are real but are a
different failure from the one that matters here. The one that matters is
Salas's own verdict:

> "In the end it didn't go anywhere, probably because in setting out to improve
> on spreadsheets, **Improv lost the essence of a spreadsheet** and in doing so
> lost the market."
> — <https://salas.com/2004/11/29/20041129why-improv-didnt-succeed-html/>

and Joel Spolsky's, from running Excel's customer visits in 1993:

> "we visited dozens of Excel customers, and did not see anyone using Excel to
> actually perform what you would call 'calculations.' Almost all of them were
> using Excel because it was a convenient way to create a table… Suddenly we
> understood why Lotus Improv… had failed completely: because it was great at
> calculations, but terrible at creating tables… **The gridlines are the most
> important feature of Excel, not recalc.**"
> — <https://www.joelonsoftware.com/2012/01/06/how-trello-is-different/>

**The shape of that argument matters.** It is not "named dimensions compute
wrongly". It is that a coordinate grid is a *general-purpose data structure that
happens to compute*, whereas a named-dimension cube is a *computation model that
happens to display*. Most people wanted the data structure.

There is a second, technical lesson, and it is the one the design must answer
before shipping anything. Improv had no cheap representation for the
exceptional:

> "you might have one formula that says PROFIT=PRICE-COST; a second might say
> that TOTAL=groupsum(YEARS). But how should the total profit be calculated…
> Conflict. … **When Improv detected a conflict, it invalidated both formulas
> and complained to the user.**" — Garfinkel, ibid.

Quantrix — the surviving descendant, still shipping (docs at Modeler 26.x,
published 2026-08-05, <https://help.idbs.com/Quantrix/Modeler_Help/LATEST/>) —
survived by inventing three escape hatches Improv lacked: cell-specific formulas
(`=right side`), an override-by-new-formula gesture
(`J Jax:Stock:Mall:Television=`), and **eclipsing**: "the formula with the
highest number (that is, the last formula that calculates the cell's value)
wins."

Quantrix's own pitch for why the named model is worth it is, verbatim, the
version-control argument this project is making:

> "the structure, logic, and presentation of your model are dependent upon their
> relative physical locations… adding one more item… moves the location of your
> Product Total cell from D12 to D13."

**So: named addressing is defensible as a versioning argument, and Improv is
proof that the adoption argument has to be won separately.** Every commercially
durable named-dimension product — Anaplan (taken private at ~$10.4B in 2022),
Quantrix (quote-only, ~50k users in 20+ years), Analytica, TM1 — sells into
enterprise planning, at enterprise prices, to trained modellers. Zero
general-purpose survivors. That is a niche-confirming result, not a
model-confirming one, and it should be written down as such.

### 1.2 The reframe

The right frame is not "spreadsheet" and not "notebook". It is:

> **an ordered set of named entities with typed attributes, some of which are
> formulas, evaluated on demand by a memoising rebuilder.**

A table is that with entities = rows. A document is that with entities = blocks
and the principal attribute = text. This is PASS2's entity map, and D6 adds the
*evaluation* half: the same structure is also the dependency graph.

The one thing to take from Spolsky's critique and give up nothing else: **the
substrate must be good at making tables when nobody wants to compute at all.**
A blank table with no formula in it must be a first-class, zero-ceremony
artifact. Improv could not do that. A GFM table can.

---

## 2. [measured] The mechanism that produces loud failure is a single-assignment namespace — not reactivity, not the merge algorithm

This is the most useful thing I found, and it came from running marimo, not
from reading about it.

### 2.1 The three-way contrast

All three substrates below were given **the same class of concurrent edit**
(two branches independently introducing a value with the same identity, at
different points in the file) and **git auto-merged all three cleanly, exit 0**.
The outcomes are opposite.

| substrate | git merge | evaluated result |
|---|---|---|
| A1 spreadsheet (prior pass) | clean | **480 instead of 660**, silent |
| plain Python script (sequential) | clean | **last-wins, silent** (`NET 960`, where Alice's branch means 975) |
| marimo (reactive DAG, single-assignment) | clean | **refuses to run**, names both offending cells |

marimo's exact output on the merged file
(`experiments/D6-computation/m2/`, marimo 0.24.0):

```
=== MERGE (independent locations, SAME variable name) ===
Auto-merging model.py
Merge made by the 'ort' strategy.
merge exit=0
=== does marimo accept the merged file? ===
critical[multiple-definitions]: Variable 'fee' is defined in multiple cells
  13 | def _():
  14 |     fee = 25
     |     ^
   ...
  19 | def _():
  20 |     fee = 40
     |     ^
hint: Variables must be unique across cells.
marimo._ast.errors.MultipleDefinitionError: This app can't be run because it has
multiple definitions of the name x
```

**Why this works, and it is not because marimo is "reactive":** order-independence
removes the notion of "later", so there is no last-writer to silently win. The
collision has nowhere to hide, so it must become an error. A1 has no names at
all, so a range collision is *undetectable*; a sequential script has names but a
total order, so a collision is *resolvable* and therefore silent.

**I3 (loud failure) is therefore a property of the NAMESPACE, not of the
reference syntax.** Naming things is necessary but not sufficient. Names must be
unique and unordered.

### 2.2 [measured] The prototype fails this test today

The L1 format's namespace is *not* single-assignment. Fed a header with a
duplicated column name and two different formulas:

```
| item   | qty | unit | total = qty * unit | total = qty * unit * 1.13 |
->  total = 135.6 ;  grand = 135.6 ;  no error
```

The last formula silently wins — the identical failure mode as the plain Python
script. **Action: duplicate names in any namespace (column, aggregate,
cross-artifact) must be a hard parse error.** This is a five-line change and it
is the difference between the prototype behaving like marimo and behaving like a
shell script.

### 2.3 [measured] marimo's file has no coupled state — verified, and it is the standard to match

marimo writes each cell as `@app.cell def _(deps): ... return (defs,)`. Those
signatures look like committed derived metadata — exactly the coupled state I1
forbids. They are not authoritative. Two tests:

- Signature deliberately **stale** (body references `tax_rate`, signature omits
  it) → ran correctly, `TOTAL 542.4`.
- File order deliberately **wrong** (the consumer cell placed first) → ran
  correctly, `TOTAL 542.4`.

marimo re-derives the DAG by AST analysis at load; `codegen.to_functiondef`
builds the parameter list from `sorted(cell.refs)`, so the emitted signature is
canonically ordered and therefore diff-stable. And there is no output anywhere
in the file.

**This is the correct pattern for any derived material that must appear in a
file for tooling reasons: emit it canonically ordered, never read it back.**

---

## 3. [measured] Committed outputs — the verdict is no, and the evidence is worse than expected

The parallel org-mode finding (absolute `@row$col` refs "do not adapt if you edit
the table structure with normal editing commands"; "recalculation of a table is
normally not automatic") predicts that in-file results can contradict their own
formulas. I reproduced that, and found a second failure that is worse.

The control is L1's result: the nominal format with **blank** computed cells,
two concurrent row inserts → clean merge, `grand = 660.0`, correct.

Now hold the format and the edits fixed and change *only* whether results are
written into the file.

### Failure 1 — clean merge, every committed result false, no marker

Twelve-row table, results written in. Alice edits `qty` on row 1, Bob edits
`unit` on row 12. Neither recalculates. Edits far enough apart that git's context
does not overlap:

```
=== MERGE: two INPUT edits far apart, committed results untouched ===
Auto-merging budget.tbl
Merge made by the 'ort' strategy.
merge exit=0

| item00 |  99 | 12.00 |             120.00 |     <- asserts 99 x 12.00 = 120.00 (truth 1188.00)
| item11 |  21 | 50.00 |             252.00 |     <- asserts 21 x 50.00 = 252.00 (truth 1050.00)
```

Git reports a clean merge. Every derived value in the file is now false. This is
exactly the org-mode hazard, in a format that has no coordinates anywhere.

### Failure 2 — the aggregate conflicts, and BOTH offered answers are wrong

Same base, Alice inserts a row worth 100, Bob inserts a row worth 80, each
updating the committed aggregate:

```
=== MERGE of a NOMINAL table whose RESULTS ARE COMMITTED ===
CONFLICT (content): Merge conflict in budget.tbl
merge exit=1

<<<<<<< HEAD
grand := sum(total)  = 580.00
=======
grand := sum(total)  = 560.00
>>>>>>> bob

=== recomputed truth ===
grand = 660.0
```

**Git hands the user a two-way choice in which neither option is correct.** The
per-row `total` cells merged fine — they are local to their row. It is the
aggregate, whose dependency set spans rows, that breaks.

That gives the precise rule, which is sharper than "don't commit outputs":

> **A derived value may not be committed if its dependency set spans more than
> one mergeable entity.** A row-local derived value merges with its row and only
> goes stale; a cross-entity derived value produces conflicts whose candidate
> resolutions are all wrong.

Since staleness is also unacceptable (I3), the operative rule remains: commit
nothing derived. What the rule above buys is the *reason*, and the knowledge that
the two failure modes are different and the cross-entity one has no manual
remedy.

### 3.1 When committed outputs ARE acceptable

Three narrow cases, all of which share the property that the artifact is a
*release*, not a *source*:

1. **Published/rendered artifacts** (`report.pdf`, `site/`) committed to a
   deploy branch or a release, never to the branch that holds the source. They
   are outputs of the build, and the build is reproducible from the source.
2. **Quarto's `_freeze/`** is the interesting real-world counterexample and it
   is committed on purpose — because the alternative is requiring every CI
   runner to have the full scientific stack. It is a *cache*, keyed by input
   hash, in a directory nobody reads. That is acceptable precisely because it is
   not the artifact: nobody edits `_freeze/`, and a wrong entry there produces a
   wrong render, not a wrong source file. (See §7 for the notebook survey.)
3. **A frozen snapshot with the derivation recorded beside it** — a value
   deliberately pinned as of a date, stored as data with its provenance, and
   never re-derived. This is a *different attribute*, not a stale formula
   result, and the format should be able to say so.

Everything else: no.

---

## 4. [measured] Granularity — the decisive argument for column formulas

This is the measurement I could not find anywhere in the literature.
*Build Systems à la Carte* is a modelling paper with no measurements; Adapton
reports that fine-grained structural memoisation is "sometimes orders of
magnitude slower than from-scratch computation" but for a different workload.

200,000 cells, one multiplication each:

```
raw column compute          :     10.9 ms
per-CELL memo bookkeeping   :    232.9 ms   ( 21.3x the compute it protects)
per-COLUMN memo bookkeeping :     49.2 ms   (  4.5x)
distinct cached cell values :  1,261 of 200,000  -> the memo table is mostly redundant
```

And at artifact granularity, hashing the serialized bytes you already have:

```
serialized table: 5.13 MB, 200,000 rows
hash WHOLE ARTIFACT once :   2.52 ms
parse + evaluate column  : 109.41 ms
hashing is 2.3% of the work it guards
```

**Three orders of magnitude separate per-cell content addressing (2130%
overhead) from per-artifact content addressing (2.3% overhead).**

This closes a loop with *Build Systems à la Carte*. The paper characterises
Excel as the taxonomy's worst cell — "Our model of Excel uses the restarting
scheduler and the dirtyBitRebuilder", *Minimal: No; Cutoff: No* — and Excel is
there because **a dirty bit is the only rebuilder you can afford per cell**.
Move the unit of memoisation up to the column and content-addressing becomes
affordable, which is what buys minimality and early cutoff. The granularity
choice and the rebuilder choice are the same choice.

Corollary the numbers also make: a hash is ~100 ns, a multiply is ~1 ns. Any
scheme that content-addresses individual cells is two orders of magnitude
mispriced no matter how fast the language. This is a structural result, not a
Python artifact.

---

## 5. [measured] Does one engine really unify formulas, references and builds?

Prior work adopted **suspending scheduler + constructive-trace rebuilder**. That
is not an idiosyncratic pick: it is the cell *Build Systems à la Carte* itself
identifies as the most interesting empty one.

> "…12 possible build systems, 8 of which are inhabited by existing build
> systems… **The most interesting unfilled spot in the table is suspending
> constructive traces**, which would provide many benefits, and which we title
> Cloud Shake."
> — Mokhov, Mitchell & Peyton Jones, ICFP 2018,
> <https://www.microsoft.com/en-us/research/uploads/prod/2018/03/build-systems.pdf>

I implemented ~50 lines of it and attacked it four ways
(`experiments/D6-computation/bsalc/engine.py`).

| attack | result | verdict |
|---|---|---|
| **Cycle** (`a = b+1`, `b = a+1`) | `suspending scheduler DETECTS it: a -> b -> a` | Real but narrow gap (below) |
| **Dynamic dependency** — which input to read is itself computed (Excel's `INDIRECT`, a transclusion whose target is computed) | `total = 100`; change the pointer → `250` | **Unification holds. This is the strongest part of the claim.** |
| **Non-determinism** (`now()`) | two calls 50 ms apart returned the *identical* timestamp; `hit: 2` | **BROKEN** |
| **Hashing cost** | 1 MB: 0.5 ms; 64 MB: 34.9 ms; 256 MB: 132.7 ms (~1.9 GB/s) | Non-issue at document scale |

**Where it breaks, precisely:**

**(a) Non-determinism is the one true break, and it is contained rather than
solved.** `now` has no inputs, so its trace key is constant and the first value
is cached forever. Every real system does the same thing: BSaLC models volatile
tasks as depending on a special key `RealWorld` "whose value is changed in every
build" and states flatly that they "cannot be cached"; Bazel's remote-execution
proto has `do_not_cache` ("the `Action`'s result cannot be cached"); Excel marks
such cells volatile. So the answer is a **taint**: any rule reading a
non-deterministic source is marked volatile, is never constructive-trace-cached,
and propagates volatility to its dependents. This costs minimality and nothing
else. It must be in the type contract from day one, because retrofitting it means
auditing every existing cache entry.

**(b) Cycles are a genuine incompatibility, but a narrow one.** BSaLC: "**We
choose not to deal with cyclic dependencies**". Excel ships iterative
calculation. Salsa's answer is the right shape if it is ever needed: monotone
fixpoint via `cycle_initial`/`cycle_fn` with a hard cap — "If a cycle iterates
more than 200 times, Salsa will panic rather than iterate forever"
(<https://salsa-rs.github.io/salsa/cycles.html>). Recommendation: detect, name
the cycle head, refuse. Do not build iterative calculation.

**(c) Hashing cost is not the problem the design worried about.** At 1.9 GB/s a
5 MB table hashes in 2.5 ms, 2.3% of parsing it. It only bites for large binary
assets — which RESEARCH.md §4 already routes to content-defined chunking in a
CAS. The engineering answers, if ever needed, exist: Salsa's **durability**
levels ("Salsa tracks when tracked functions only consume values of high
durability and, if no high durability input has changed, it can skip traversing
their dependencies", <https://salsa-rs.github.io/salsa/reference/durability.html>)
map cleanly onto vendored/imported data = HIGH, the document being typed in =
LOW.

**(d) A trap the prior work has not verified about itself.** "Undo is free" is
*not* a property of content addressing in general. It is a property of retaining
more than one trace per key. BSaLC (JFP §5.2):

> "storing only one Trace per key means that if the dependencies of a key change
> but the resulting value does not, and then the dependencies change back to
> what they were before, **there will be no valid Trace available and the key
> will therefore have to be rebuilt**"

L5's cache is a content-addressed *directory* keyed by
`hash(rule, artifact, name, content-hash)`, so it retains many traces and the
property holds. But Shake's own production optimisation — verifying *step*
traces, 4-byte revision stamps instead of 32-byte hashes — gives it up. **Do not
adopt that optimisation. Write the property down as a test.**

**(e) The identity trap, from Adapton, which independently confirms §6.** Classic
Adapton matched memo entries structurally and was, per *Incremental Computation
with Names* (arXiv:1503.07792), "nearly always slower than Nominal Adapton
(sometimes orders of magnitude slower), and is sometimes orders of magnitude
slower than from-scratch computation", because inserting an element near the
front rehashes everything downstream. Their fix was first-class programmer-supplied
**names**. That is the same conclusion §6 reaches from merge semantics, arrived at
from performance. Two independent arguments for stable row identity.

**Verdict on the unification:** it holds for transclusion and export builds
without qualification, and for spreadsheet formulas with the correction that
Excel's own point in the design space is the *worst* one and must not be copied.
Non-determinism opts out rather than breaking it. Cycles are refused. Nothing
here falsifies the one-engine claim; it narrows it usefully.

---

## 6. [measured] Row identity — the prior work's answer is wrong, and the ablation says so

L1 caveat 1 recorded: "Row identity here is the first column… **A declared key is
what buys the clean merge.**" That is half right. I ran the ablation: the same
generic entity-map merge, four identity functions, four scenarios
(`experiments/D6-computation/rowid/ident2.py`).

```
=== S1 edit different cols of same row ===
  natural-key    rows=3 conflicts=0  -> widget/99/15 ; gadget/20/18 ; bolt/5/2      CORRECT
  content-hash   rows=4 conflicts=0  -> widget/99/12 ; gadget/20/18 ; bolt/5/2 ; widget/10/15   <-- SPLIT THE ROW
  opaque-id-col  rows=3 conflicts=0  -> widget/99/15 ; gadget/20/18 ; bolt/5/2      CORRECT
  positional     rows=3 conflicts=0  -> widget/99/15 ; gadget/20/18 ; bolt/5/2      CORRECT

=== S2 one side renames the key value ===
  natural-key    rows=3 conflicts=0  -> WIDGET/10/12 ; ...    <-- LOST BOB'S EDIT (qty should be 99)
  content-hash   rows=4 conflicts=0  -> ...                   <-- SPLIT THE ROW
  opaque-id-col  rows=3 conflicts=0  -> WIDGET/99/12 ; ...    CORRECT
  positional     rows=3 conflicts=0  -> WIDGET/99/12 ; ...    CORRECT

=== S3 both insert a row at different places ===
  natural-key    rows=5 conflicts=0  CORRECT
  content-hash   rows=5 conflicts=0  CORRECT
  opaque-id-col  rows=5 conflicts=0  CORRECT
  positional     rows=4 conflicts=4  <-- DROPPED A ROW, 4 SPURIOUS CONFLICTS

=== S4 duplicate key values exist in the table ===
  natural-key    rows=3 conflicts=0  -> widget/5/2 ; gadget/20/18 ; widget/5/2   <-- ROW 1 OVERWRITTEN BY ROW 3
  content-hash   rows=3 conflicts=0  CORRECT
  opaque-id-col  rows=3 conflicts=0  CORRECT
  positional     rows=3 conflicts=0  CORRECT
```

**Only the opaque id column survives all four.** Every failure above is silent —
zero conflicts reported in every wrong case.

- **Content hash of the row is fatal and worse than "fatal for edit-vs-edit".**
  Any edit changes the identity, so every edit is a delete+add; edit-vs-edit
  becomes *two unrelated adds that both survive*, producing a plausible file
  with duplicate rows and no marker.
- **A natural key fails two ways**: renaming the key value discards the other
  branch's edits (S2), and duplicate key values collapse rows (S4). Both silent.
- **Positional identity** produces spurious conflicts and drops rows on
  concurrent insert (S3) — the known result, reconfirmed.

### 6.1 What real systems do (and they agree)

- **Grist**: `id INTEGER PRIMARY KEY`, allocated by high-water mark
  (`sandbox/grist/useractions.py:407`), never content-derived, and **not
  exported** — Grist's CSV export filters to visible view fields, and the `id`
  column is not a field. Cross-version identity in Grist is a *user-declared
  key*: `MergeOptions.mergeCols` — "we consider rows whose columns values for all
  columns in `mergeCols` [are] the same record in both tables"
  (`app/server/lib/ActiveDocImport.ts:575`).
- **dbt** `generate_surrogate_key` hashes **only the declared natural-key
  columns**, i.e. it is a declared key with a hashing step, not content
  addressing. Its own history is a warning: the old macro is now a hard error
  because "The new macro treats null values differently to empty strings"; field
  order is significant and the `-` separator is unescaped, so `('a-b','c')` and
  `('a','b-c')` collide.
- **daff**, with no key, brute-forces it: score common columns by distinct-value
  count, keep the **top 5**, try all `2^5-1 = 31` subsets, reject a candidate if
  `top_freq/(h+20) >= 0.1`, link only rows unique on both sides, then a
  positional pass, then emit the rest as add/remove. Its own `--id` flag exists
  because the author knows this is a fallback. And its `Index.toKey` **drops
  empty values from the key string**, so `("Ann","")` and `("","Ann")` collide —
  the same null bug dbt fixed.
- **Git** has no line identity at all: content + position, plus *file*-level
  rename detection at "The default similarity index is 50%", abandoned entirely
  past `diff.renameLimit` (default 1000). Git survives this because a bad rename
  is loud. **A bad row match is quiet.**

### 6.2 The recommendation

> **Declared key when the data has one; otherwise an explicit, opt-in, opaque id
> column written into the file. Heuristic alignment is a diff renderer, never a
> merge driver.**

Precedence at merge time:

1. A declared key (one or more columns, named in the header/frontmatter), which
   the writer **validates for uniqueness and non-nullity on save** — S4 shows an
   unvalidated declared key is worse than no key, because it fails silently.
2. An opaque id column (short random token or monotonic integer), added when the
   user opts in or when the writer detects there is no unique key.
3. Otherwise: refuse to auto-merge. Render the alignment for a human.

**The objection, and its answer.** An auto-generated id is only stable if it is
generated once, at row creation; two branches generating ids independently
manufacture the illusion of identity. That objection is answered by an
architectural fact already established: RESEARCH.md §4's measured
single-writer-per-repository constraint (12/12 pushes rejected for a second
writer; 8/8 rebases conflicted). Rows are created by one writer, so ids are
assigned once. **If the single-writer constraint is ever relaxed, the id scheme
must move to (actor, counter) pairs, i.e. an RGA identifier.** Write that
dependency down.

### 6.3 The asymmetry that makes this palatable

RESEARCH.md §3 warns, correctly, against opaque identifiers in a plaintext
format: "`=col_a7f3 * col_9b21` is positional addressing with the ergonomics
removed." That objection applies to **columns** and not to **rows**, and the
difference is load-bearing:

> **A human writes column names into formulas. A human never writes a row id into
> anything.** Column formulas are row-relative by construction (`total = qty *
> unit`), and the `prev.` operator (§7.2) names an *ordinal* relationship, not an
> id. So the row id is referenced only by the merge algorithm.

Hence: **literal human names for columns, opaque ids for rows.** No indirection
is imposed on anything a person reads or writes.

---

## 7. [measured] The previous-row problem, and what the plaintext model wins

The brief asks whether a column-formula model can do running totals — the acid
test, and the reason prior work proposed an explicit `prev.` operator.

### 7.1 What the incumbents actually do

- **Grist** solved it in July 2024 with `PREVIOUS`/`NEXT`/`RANK`. The idiom is
  `PREVIOUS(rec, group_by=("SKU"), order_by=("Date")).Cumulative + $Stock_In`.
  It is O(log n), not O(n²), but only because Grist buys three things together:
  per-*cell* dirtiness, a maintained sorted index that is itself a node in the
  dependency graph (`LookupMapColumn`, described in `sandbox/grist/lookup.py` as
  "analogous to a database index"), and an evaluator that reorders on an
  `OrderError` exception and detects cycles per cell. Before that, users hit the
  wall: a forum report of a formula that "pulls 100-3000 records for EACH row in
  a 15000 row table", ~20 s per row insert
  (<https://community.getgrist.com/t/how-to-create-a-formula-to-show-accumulated-amount-per-account/1861>).
- **Excel Tables** have no "row above" operator in structured-reference syntax,
  so the idiom is the mixed-anchor `=SUM($D$2:D2)` — **an A1 positional range
  inside a named table**, i.e. the exact construct that merges silently wrong.
  Excel's clean functional alternative is unavailable where it is most wanted:
  `SCAN` spills, and Microsoft's own docs state "Spilled array formulas are not
  supported in Excel tables themselves, so you should place them in the grid
  outside of the Table"
  (<https://support.microsoft.com/en-us/office/dynamic-array-formulas-and-spilled-array-behavior-205c6b06-03ba-4151-89a1-87a7eb36e531>).

### 7.2 [measured] `prev.` in a plaintext table, and why it is cheaper here

`experiments/D6-computation/prev/tbl2.py` adds `prev.<column>` — the predecessor
**in row order**, not a coordinate — evaluated in a single ordered pass.

```
| date       | memo    | amount | balance = prev.balance + amount |
```

Alice inserts a transaction near the top; Bob inserts one at the bottom:

```
=== MERGE: concurrent row inserts, top and bottom, running-total column ===
Merge made by the 'ort' strategy.        merge exit=0
...
| 2026-02-02 | fees    |  -75   | balance 1675.0 |
closing = 1675.0     (expected 1000-400+900+250-75 = 1675)
```

**Correct running total, clean merge, stock git, one ordered pass, no index.**

The reason is worth stating because it is a genuine structural advantage of the
plaintext model over Grist's:

> **Grist needs a maintained sorted index because SQLite rows have no inherent
> order. A plaintext table's order IS its bytes.** `order_by` is free; `prev` is
> the previous line. The expensive machinery Grist must build to make
> `PREVIOUS` O(log n) is machinery this format does not need at all.

The limits of `prev.`, honestly:

- It gives the *immediately preceding row*, not "previous within a group". A
  running total per category needs `prev where <predicate>` or a group-by, and
  that reintroduces the index. Ship `prev.` first; treat grouped-prev as a
  separate, later decision.
- It makes derived values **order-sensitive**, and file order is merge-sensitive.
  A sort on one branch and an edit on the other conflicted in my test (loud, so
  acceptable) — but a sort is a semantic change to every derived value in the
  column, and the UI must say so.

### 7.3 [measured] A new failure class: the evaluator will happily evaluate a conflicted file

This is a defect in the existing prototype found by measurement, and it belongs
to the same family as everything else here.

The L1 evaluator skips any line not starting with `|`. Git's conflict markers do
not start with `|`. So:

```
=== L1's ORIGINAL evaluator, fed a CONFLICTED file ===
   widget  10 12.00 -> 120.0
   gadget  20 18.00 -> 360.0     <- HEAD's version
   gadget  20 30.00 -> 600.0     <- bob's version
grand = 1080.0

correct-under-HEAD grand = 480 ; correct-under-bob = 720
```

**1080 — a number that is neither.** The named-column design eliminated the
silent-wrong *merge*; a permissive parser reintroduced a silent-wrong *read*.

This escalates PASS3's I5 from a UX concern to a correctness one, and it
generalises: **I3 (loud failure) must be a property of PARSING, not only of
reference resolution.** Two rules follow, both cheap:

- Any file containing conflict markers must be **refused**, not parsed.
- A row whose column count does not match the header must be **refused**, not
  padded. (`merge3.py` currently pads with `''`.)

Together with §2.2's duplicate-name rule, that is three places where the
prototype is permissive and must be strict. All three produce plausible wrong
numbers today.

---

## 8. Units, types, and the empirical case for correctness — the honest answer

**Verdict: the naming evidence is SPLIT, and the split tracks one variable —
whether the binding is visible where the reference is. The units-and-types
evidence is UNSUPPORTED. And the one intervention with real evidence behind it
is neither of those.**

### 8.1 Errors are real and the numbers are solid enough

Panko, *Spreadsheet Errors: What We Know* (EuSpRIG 2000, arXiv:0802.3457) and
*What We Don't Know About Spreadsheet Errors Today* (EuSpRIG 2015,
arXiv:1602.02601), read in full from the PDFs. Verbatim:

Field audits (2015 table, 85 spreadsheets under intensive inspection):

| Authors | Spreadsheets | % with Errors | CER | Methodology |
|---|---|---|---|---|
| Hicks [1995] | 1 | 100% | 1.2% | Fagan Code Inspection, team of three |
| Coopers and Lybrand [1997] | 23 | 91% | | Commercial "Audit" |
| KPMG [1998] | 22 | 91% | | Commercial "Audit" |
| Lukasic [1998] | 2 | 100% | 2.2%, 2.5% | Reproduction in a financial modelling language |
| Butler [2000] | 7 | 86% | | UK tax audit |
| Lawrence and Lee [2001] | 30 | 100% | | Commercial "Audit" |
| **Total / Weighted Average** | **85** | **94%** | | |

Laboratory: 998 subjects, 1,170 spreadsheets, **51% contained errors** despite
"most spreadsheets were only 25 to 50 cells in total size", cell error rates
1%–5%. And the overconfidence result, which is the most useful single fact for a
product argument: developers' "median estimate was 10%, and the mean was 18%. In
fact, **86% had made an error**."

**Caveats that must travel with these numbers:** the 94% is dominated by
commercial auditing firms' own marketing audits (75 of 85 spreadsheets), three
of the six studies have n ≤ 7, and the earliest field audits Panko himself
tabulated in 2000 found errors in only 24% of 367 spreadsheets — the number rose
as methodology improved, which is the right direction but also means "94%" is a
statement about intensive inspection, not about spreadsheets.

### 8.2 The counter-evidence on named references, at full strength

McKeever & McDaid ran the only controlled experiments on this, three times, and
got the same answer three times.

- 2009 (arXiv:0908.0935, n=21, exploratory, no control group by their own
  admission): "novice users debug on average significantly fewer errors if the
  spreadsheet contains named ranges."
- 2010 (arXiv:1009.2765): "the group that used named ranges corrected
  **significantly fewer** formula errors. This was true for all sub-categories of
  formula errors, but was **most pronounced for cell and range reference
  errors**."
- 2011 (arXiv:1111.6872): "formulas developed by non-experts using range names
  are **more likely to contain errors and take longer to develop**… **contrary to
  published opinion we find no evidence to endorse the use of range names in the
  development of reliable spreadsheets by novice and intermediate users**."
  (Raw counts are small: 12 incorrect with names vs 4 with cell references in
  group one; 10 vs 6 in group two.)

And Panko, on the prescription itself — this is the field's leading error
researcher naming this design's thesis as an unproven remedy:

> "Many begin with a statement that, 'the problem with spreadsheets is X.' X may
> be having end users do development instead of professionals, **a failure to use
> a program with strong data typing**, or many other things… **requiring strong
> typing could put more burden on developers who are already overloaded and
> making errors as a result.** Given limits in human attention and other
> resources, adding burdens could increase errors much more than it reduces the
> type of error it was intended to reduce… Medicines must be tested to prove that
> they are safe and effective before they are accepted. We should require the
> same rigor for spreadsheet development prescriptions."
> — arXiv:1602.02601

### 8.3 The rebuttal, strengthened — and it comes from the papers themselves

RESEARCH.md's rebuttal (a named *range* is pure indirection; a *column header* is
not, since the name is printed atop the column) was recorded as "plausible but
unreplicated". The 2010 paper's own proposed mechanism is that rebuttal, stated
by the authors who found the negative result:

> "A range name is an additional piece of information that the user must
> remember. As the participants were unlikely to remember what each name referred
> to, **they would have to perform two checks, one to see if the correct name was
> used and another to see if the name referred to the correct range**."

A column-header reference collapses those two checks into one: the name is
rendered immediately above the values it names, and there is no separate Name
Manager holding the binding. **The measured harm is attributed by its own
discoverers to the exact property that column headers do not have.**

And there is now positive evidence on the other side of that line, which
RESEARCH.md did not have. **Calculation View** (Sarkar, Gordon, Peyton Jones &
Toronto, VL/HCC 2018,
<https://www.microsoft.com/en-us/research/wp-content/uploads/2018/10/sarkar_2018_calcview.pdf>)
adds a live, bidirectional *formula-list* view beside the grid, with named
range assignment (`TaxRate A1 = 0.01`, `B1:B10 = SQRT(A1)`). Measured, n=22,
within-subjects:

- authoring: median speed-up **37.14%** (median −54 s, Wilcoxon Z = −4.14,
  p = 3.6×10⁻⁵)
- debugging: median speed-up **40.7%** (median −20 s, Z = −3.3, p = 9.6×10⁻⁴)
- NASA-TLX cognitive load lower by median 2.25 on 21 points (p = 0.0024)
- **low-expertise users benefited most on authoring: 55.3% vs 13.5%** median
  speed-up — the opposite sign from McKeever & McDaid's novice result

**Elastic Sheet-Defined Functions** (McCutchen, Borghouts, Gordon, Peyton Jones,
Sarkar, JFP 2020) adds a second: named function abstraction beat array
combinators on workload, n=20, TLX M = 37.46 (SD 14.24) vs 52.25 (SD 14.80),
F(1,18) = 10.22, p < 0.01; and "All 3 tasks a participant could not solve at all
occurred in the array-combinator condition."

**So the honest statement is: named references measured *worse* when the binding
lives in a modal Name Manager (McKeever & McDaid ×3), and measured *better* when
the binding is rendered next to the reference (Calculation View, Elastic SDFs).**
Both bodies of evidence are small and neither tested a column-header reference
specifically. But the design conclusion is sharp and actionable: **a name is only
worth having if the thing it binds is visible from where the name is used.**
That is an argument for the column header and against a named-range registry,
and it is why the design must never grow an Excel-style Name Manager.

### 8.4 The correctness argument that IS supported — and it is a better one

Panko's 2000 abstract: "**To date, only one technique, cell-by-cell code
inspection, has been demonstrated to be effective.**" The 2015 paper quantifies
it: individuals caught 63% of errors, teams of three caught 83%, "This is a
modest percentage increase, but produced large jumps in detection rates for the
most difficult-to-find errors."

**A git-backed substrate is the only spreadsheet-shaped thing that makes code
inspection structurally possible.** Diffs, review, blame, history, and a text the
reviewer can read line by line are not correctness features bolted on; they are
the one intervention with evidence behind it. Excel has no reviewable diff.
Grist's `.grist` is a SQLite blob. Google Sheets' version history is a replay,
not a diff.

**This should be the headline correctness claim, and types/units should not be.**
It is empirically grounded, it is the thing the architecture already delivers,
and it does not require winning an argument the literature currently loses.

### 8.5 [measured] Units specifically: expensive, and orthogonal to the errors people make

```
pint 0.25.3
plain float mul   : 100,000 ops in    4.77 ms  ->     48 ns/op
pint Quantity mul :  20,000 ops in  127.26 ms  ->   6363 ns/op
pint is 133x slower per scalar operation

dimensional error caught: DimensionalityError Cannot convert from 'meter' ([length]) to 'second' ([time])
same-dimension nonsense NOT caught: 5 meter + 3 foot = 5.9144 meter
```

Two facts, and the second is the important one. Panko & Halverson's error
taxonomy is **mechanical** (pointing at the wrong cell), **logic**, and
**omission**. Pointing at the wrong cell of the *same dimension* is
dimensionally valid, so a unit system detects **none of the dominant error
class**. Units catch a real but narrow category — the Mars Climate Orbiter
category — and Nimbalyst's `.calc.md` shows they are lovely for engineering
models (`g0 = 9.80665 m / s^2`). They are not an error-rate intervention.

**Frink** deserves a note because it keeps being cited as the model to copy: its
site documents a large unit database, dimensional checking (`55 mph -> yards`
→ "Conformance error - Left side is velocity, Right side is length"), a
`conforms` operator, live currency rates and interval arithmetic. I fetched
frinklang.org and grepped the full rendered text for "licen", "open source" and
"source code": **no licence statement and no source availability anywhere on the
project site**, and `frinklang.org/fsp/license.html` returns a Java
`FileNotFoundException` from the author's own machine. Treat Frink as a
closed-source, single-author Java program — a specification to learn from, not a
dependency to take.

**Recommendation on units:** optional, per-column, declared in the schema,
checked at column boundaries only (not per scalar operation, which is where the
133× lives), and sold as an engineering-modelling feature rather than a
correctness one. Do not put units on the critical path of the tabular format.

---

## 9. The diagnosis is not the grid — it is the missing abstraction. And there may be no replacement structure.

This section is the strongest counter-evidence in the whole report to a
schema-first tabular format, and it comes from the group that shipped LAMBDA.

### 9.1 Every MSR design is ADDITIVE to the grid

- Peyton Jones, Blackwell & Burnett, *A user-centred approach to functions in
  Excel* (ICFP 2003,
  <https://www.microsoft.com/en-us/research/wp-content/uploads/2016/07/excel-1.pdf>).
  The diagnosis is flatness, not geometry:

  > "Thought of as a programming language, though, a spreadsheet is a very
  > strange one. In particular, it is completely flat: there are no functions
  > apart from the built-in ones."
  > "From a programming language point of view, then, spreadsheets lack the most
  > fundamental mechanism that we use to control complexity: the ability to
  > define re-usable abstractions… Can you imagine programming in C without
  > procedures, however clever the editor's copy-and-paste technology?"

  And the constraint on any fix:

  > "The implementation of a function must be defined by a spreadsheet, because
  > that is the only computational paradigm understood by our target audience."

- Calculation View (2018): "**We propose that the grid, and its formula syntax,
  be left untouched**, but to provide opportunities for abstraction through
  additional representations."
- Gridlets (CHI EA 2020): a *transparent* abstraction that carries "layout,
  formatting, and intermediate computations", explicitly ranked as more
  paradigm-consistent than sheet-defined functions because it preserves
  secondary notation. It never shipped and was never user-tested: "Gridlets…
  has been proposed but not evaluated in an empirical study."

### 9.2 The finding that must be answered

Chalhoub & Sarkar, *"It's Freedom to Put Things Where My Mind Wants": Understanding
and Improving the User Experience of Structuring Data in Spreadsheets*
(CHI 2022, n=21 interviews + n=20 prototype study,
<https://www.microsoft.com/en-us/research/wp-content/uploads/2021/12/chalhoub_2022_data_structuring.pdf>):

> "Recall from the introduction the motivating question for much research into
> novel spreadsheet structures, namely: is it possible to design a data
> structure that fits the needs of spreadsheet users to such an extent, that it
> could replace the unstructured grid and thereby eliminate all the errors that
> come with it? **Our findings suggest that in fact no such structure can exist,
> due to the dynamic and contextual nature of user needs.**"

> "There is no such thing as 'structured' or 'unstructured' data in any absolute
> sense… At any given moment the same spreadsheet can perform as either
> structured or unstructured, depending on the user and the task at hand."

> Structured alternatives "require planning and **premature commitment** to a
> certain set of structures or a certain regime of editing operations, which is
> simply incompatible with the exploratory, variable, and contingent nature of
> daily spreadsheet use."

Alongside the corpus statistic that frames the entire market:

> **"as little as ~7% of spreadsheets contain formulas, suggesting that much
> spreadsheet use consists of little more than data storage and manipulation"**
> — Sarkar et al., CHI EA 2020, citing the Fuse corpus (249,376 unique
> spreadsheets from 2.1M URLs, Barik et al. MSR 2015)

And from the Enron corpus (Hermans & Murphy-Hill, ICSE 2015, >15,000 real
corporate spreadsheets): "76% of spreadsheets in the presented corpus use the
same 15 functions", and "24% of Enron spreadsheets with at least one formula
contain an Excel error".

### 9.3 What this forces

Three consequences, all of which the design must accept:

1. **The 500-function argument is dead.** RESEARCH.md §3 worries that Kova's
   engine has 11 functions and recommends swapping in IronCalc's 495. Enron says
   76% of real usage is 15 functions. Function count is a marketing number, not a
   requirement. **Ship ~30 functions and a good `prev.`.**
2. **The formula-first framing is wrong for 93% of the artifact population.**
   A blank table with no formula must be the cheapest thing in the system.
   Schema declaration must be **optional and inferred**, never a precondition —
   "premature commitment" is the named failure mode, and requiring a
   `datapackage.json` before you can type a table is exactly it.
3. **Do not try to replace the grid; make the file the thing the grid is bad
   at.** Chalhoub & Sarkar say no structure can replace the flexible grid for
   authoring. They do not say a structure cannot be the *storage and review*
   form. The wedge is precisely the one thing the grid cannot do — be diffed,
   reviewed, merged and attributed — and §8.4's inspection evidence is the
   reason that wedge is worth anything.

### 9.4 The shipped-Excel data point that most vindicates this design

Excel shipped both a named-table abstraction and a computed-array abstraction —
**and they are mutually exclusive**. Microsoft's own docs:

> "Spilled array formulas are not supported in Excel tables themselves, so you
> should place them in the grid outside of the Table."
> — <https://support.microsoft.com/en-us/office/dynamic-array-formulas-and-spilled-array-behavior-205c6b06-03ba-4151-89a1-87a7eb36e531>

So `SCAN(0, [Amount], LAMBDA(a,b,a+b))` — Excel's clean functional answer to the
running total — **cannot live inside the Table whose named columns make it
readable**. The idiom that remains inside a Table is `=SUM($D$2:D2)`: an A1
positional range inside a named structure, i.e. exactly the construct measured to
merge silently wrong. §7.2's `prev.` in a plaintext, order-is-line-order table
does what neither Excel construct does: row-relative, coordinate-free, and
merge-correct.

And on LAMBDA as deployed, from a thematic analysis of **2,697 relevant comments**
across Reddit/HN/YouTube/MS Tech Community (Sarkar, Srinivasa Ragavan, Williams &
Gordon, VL/HCC 2022):

> "LAMBDA encourages an extended, programmatic style of formula writing that
> throws into sharp relief the limits of the current formula management
> environment"

with users saying *"I don't think name manager cuts it, they'll need a formula
manager… Sharing, vital"* and *"without the ability to easily audit a LAMBDA,
financial analysts will not adopt this feature"*. **A plaintext file under git is
a formula manager.** That is the gap, stated by Excel's own users.

---

## 10. The canonical tabular representation

**Recommendation: plain text, one record per line, tidy/long, key-sorted, with a
Table Schema-shaped sidecar carrying types and `primaryKey` — the sidecar
OPTIONAL and inferred by default. Binary formats are derived caches only, and are
never content-addressed on their own bytes.**

### 10.1 CSV loses on evidence, not taste

RFC 4180 pushes encoding, header presence and dialect **outside the file**
(§3: charset is a MIME parameter; §2.3: "There maybe an optional header line").
Its ABNF explicitly permits CR and LF inside a quoted field, which breaks the
line-orientation every git tool assumes. Measured:

- A one-cell change in a CSV with an embedded newline shows git counting 4
  "lines" in a 3-record file, with `^M` inside the line content.
- Two branches editing **different physical lines of the same logical cell**:
  `Auto-merging m.csv / Merge made by the 'ort' strategy / clean (exit 0)`.
  Git merged *inside a single cell* without knowing it.
- **Conflict markers are valid CSV.** Python's `csv` module parses
  `['<<<<<<< HEAD']`, `['=======']`, `['>>>>>>> b2']` as ordinary data rows,
  no error. This is the same defect as §7.3 and it is unfixable in CSV.
- Column insert on a 10,000-row file: `git diff --numstat` → **10002 10002**.
  One semantic edit, 20,004 line changes, 20,004× the cost of a row append.

### 10.2 Tidy/long is what makes tables mergeable — measured

Wickham, *Tidy Data*, JSS 59(10), 2014, verbatim: "1. Each variable forms a
column. 2. Each observation forms a row. 3. Each type of observational unit forms
a table." Messy-data problem #1 is "Column headers are values, not variable
names."

Same data, wide vs long. Branch A adds year 2022; branch B adds country DE:

```
Auto-merging long.csv
Auto-merging wide.csv
CONFLICT (content): Merge conflict in wide.csv
```

The long file merged correctly and automatically; the wide file conflicted across
its entire contents. The mechanism is exactly the coupled-state defect of PASS3:
**in wide form the header row is a shared mutable resource that every category
addition must rewrite**, so two additions always collide.

Honest residual: sorted-long only *approximates* key-identity merging, because
git still diffs lines. An insert landing adjacent to an edit on a different key
produced a false conflict. Closing that gap needs the `primaryKey`-keyed merge
driver — which is §6's answer and D3's known deployment risk.

### 10.3 The sidecar: Frictionless, not CSVW

- **CSVW is dead, and now formally so.** `w3c/csvw` is **archived** (169 stars,
  final activity 2026-05-22, two README edits; nothing substantive since
  2022-10-27), following the closure of the CSV on the Web Community Group in
  May 2026. Its metadata discovery presumes HTTP (`/.well-known/csvm`,
  `Link rel="describedby"`) — it is a web-publishing standard, not a file format.
  Mine its annotated-cell model; take no dependency.
- **Frictionless Table Schema v2** (profile `/profiles/2.0/tableschema.json`,
  shipped 2024-06-26) is alive and is the right shape: 16 types, constraints
  including `unique`/`enum`/`pattern`, `missingValues`, `foreignKeys`, and —
  the load-bearing one —

  > "A primary key is a field or set of fields that uniquely identifies each row
  > in the table. Per SQL standards, the fields cannot be `null`."

  Verified working against a deliberately dirty CSV (frictionless 5.19.0): it
  caught a type error, a `maximum` violation, an `enum` violation and a
  **primary-key duplicate**, from a declarative sidecar. Note the maintenance
  reality: 840 stars, 23 commits in 12 months. **Depend on the spec (it is JSON
  Schema); do not depend on the library.**

Per §9.2, the sidecar must be **optional**. Default to inference; let the user
promote inferred types to declared ones when they want the guarantee. Requiring
a schema before a table exists is the premature-commitment failure.

### 10.4 Binary formats: caches only, and not identity

- **Parquet.** Same writer + same options + same data → byte-identical
  (verified, pyarrow 25.0.1). But `created_by` is in the footer
  (`parquet.thrift` field 6), so **a library upgrade invalidates every cache
  key**, and row-group size — pure tuning — changes the bytes
  (`row_group_size 1000` → `cb097ea4…`; `256` → `61d683f0…`). DuckDB and Arrow
  produce different bytes for the same table. **Never content-address a Parquet
  file. Key the cache on canonical text + schema hash + an explicit writer
  fingerprint.**
- **SQLite as an application file format.** Hipp's case is correct and is
  entirely about a running application: "Only those parts of the file that
  actually change are written out to disk", atomic writes, portable, "promises
  to continue to be compatible in decades to come". None of it is about version
  control. Measured: a one-cell change → `db.sqlite | Bin 8192 -> 8192 bytes`,
  a whole new 8 KB blob, no diff. `sqldiff` and the session extension both work
  and both confirm §6 independently: sqldiff "does not compute changesets for…
  tables which have no explicit primary key", and "When sqldiff is made to
  compare only such tables, no error occurs. **However, the result may be
  unexpected.**" The session extension "only works with tables that have a
  declared PRIMARY KEY". Both are two-way diffs with a conflict callback, not
  three-way merges.
- **Dolt** is the honest "what if you did this properly": prolly trees give
  history-independent structure ("No matter which order you insert, update, or
  delete values, the Prolly tree is the same"), diffs proportional to the change
  rather than the tree, and genuine cell-level three-way merge with
  `dolt_conflicts_$table` carrying `base`/`ours`/`theirs` per column. Healthy:
  24,287 stars, 3,963 commits in 12 months. **And it is the wrong dependency
  here**, because it achieves this by not being git and not being plaintext —
  it is a MySQL-compatible server with its own VCS, remotes and hosting. Steal
  the architecture (declared PK, cell-level three-way merge, history-independent
  structure); do not take the dependency.
- **DuckDB is the right compute layer.** It reads plaintext in place, sniffs a
  nasty dialect with zero configuration, and — the important part — **fails
  loudly where pandas fails silently**. On a file whose 30,001st row breaks the
  type inferred from the first 20,480, DuckDB raises `Conversion Error… Could
  not convert string "N/A" to 'BIGINT'`; pandas silently produced `NaN` and
  turned the whole integer column into floats, with no error. That is the single
  best argument that types must be **declared, not sniffed** — and it is also
  why the sidecar being optional does not mean inference is trustworthy at
  scale.

### 10.5 Malloy is the model to copy for the formula language

Alive (2,559 stars, 486 commits in 12 months, v0.0.432 on 2026-08-20 — note
still 0.0.x after 5,238 commits). Real syntax:

```malloy
source: flights is duckdb.table('flights.parquet') extend {
  measure: on_time_rate is
    count() { where: cancelled = 'N' and arr_delay < 15 } / count() { where: cancelled = 'N' }
}
```

Every reference is nominal — no column letter, no ordinal, anywhere. And its
`measure:` / `dimension:` split (aggregate vs row-wise) is a distinction
spreadsheet formula languages conflate and should not: it is exactly the
distinction between §3's safe row-local derived value and its dangerous
cross-entity aggregate.

---

## 11. "dbt + Datasette + marimo already win" — the steelman, and why it does not close the case

**The steelman, at full strength.** Every component exists, is mature, and is
free. Git holds plaintext that diffs perfectly: dbt models are `.sql`, marimo
notebooks are `.py` (22,527 stars, v0.24.0 on 2026-08-17). Neither commits
derived tables, so **the merge problem evaporates** — you version recipes, not
results, and recipes are code, which git was designed for. `ref()` already gives
nominal addressing, and it buys three things from one annotation:

> "it is using these references between models to automatically build the
> dependency graph… dbt knows the proper order to run all models based on the
> use of the `ref` function"
> — <https://docs.getdbt.com/reference/dbt-jinja-functions/ref>

Datasette (11,415 stars) publishes the result as a browsable, queryable site with
an API. DuckDB removes the warehouse requirement. Malloy supplies named
dimensions and measures if SQL is too raw. Total new code required: **zero**. Any
new canonical format must beat a stack with ~50,000 combined stars and a decade
of production hardening — and *formats fail far more often than tools do*. CSVW
is the cautionary tale: a technically excellent W3C Recommendation, archived in
2026 with no adopters.

**Where it actually breaks — four places, and the first is decisive.**

1. **It versions recipes, not facts.** dbt's premise is "raw data is exogenous,
   transformations are code." Personal and small-team knowledge work is the
   inverse: the hand-maintained fact table *is* the primary artifact and has no
   upstream. dbt's one answer is seeds, and it is a documented weak spot — seeds
   over 1 MiB are state-compared **by file path, not contents**
   (<https://docs.getdbt.com/reference/node-selection/state-comparison-caveats>).
   **The one place dbt stores authored data is the one place its own machinery
   gives up.**
2. **No in-place editing anywhere in the stack.** Datasette's centre of gravity
   is immutable mode; marimo edits code; dbt edits SQL. Nothing supports "click
   the cell, change the value, commit." For a substrate whose data is *authored*
   rather than ingested, that is the whole requirement.
3. **The merge problem is deferred, not solved.** It vanishes only while data
   stays in a warehouse. The moment authored tables enter git — which is the
   premise — every measurement in §3, §6, §7.3 and §10.1 applies at full force,
   and none of these tools has a merge story. Dolt is the only project in this
   survey that solved it, and it solved it by not using git.
4. **Three DAGs, no shared model.** dbt's DAG, marimo's reactive graph and
   Datasette's schema are separate systems with separate notions of identity.
   Nothing propagates a rename from a dbt model into a marimo notebook. §5's
   one-engine claim is precisely what this stack does not have.

Simon Willison's **`git-history`** is the sharpest single corroboration, because
he hit this problem from the other end and reached the same answer. It reads a
file's whole git history into SQLite — and it **requires `--id`**:

```
git-history file ca-fires.db incidents.json --namespace incident --id UniqueId
```

It builds `item`/`item_version` tables, stores only changed columns per version,
and needs an extra `item_changed` table to distinguish "unchanged" from
"genuinely null". **He had to bolt row identity onto a format that lacked it,
after the fact, and pay a schema-complexity tax for the ambiguity.** Declaring
the key up front is the same insight, paid for once.

**The honest bottom line.** The steelman defeats any proposal framed as "a better
dbt" or "a better notebook", and that framing should be abandoned. It does not
defeat this one:

> **a canonical on-disk form for AUTHORED tables — declared row identity,
> optional declared types, no committed derived values — that merges correctly
> under git and is editable by hand.**

That is a *format* problem sitting underneath the entire stack, and none of these
tools solves it, because all of them are careful never to put authored tabular
data in git in the first place.

---

## 12. What the notebook ecosystem already settled, and the two things to copy

The reactive-notebook world has run this experiment for a decade. Six systems,
one question: are results committed?

| System | Results in the source file | Cached where | Cache committed? | Cache key |
|---|---|---|---|---|
| **marimo** | never | `__marimo__/session/`, `__marimo__/cache/` | **no** (`.gitignore: __marimo__`) | per-cell code hash + **transitive DAG ancestry** |
| **Observable Framework** | never | `.observablehq/cache` | **no** | loader mtime (preview) / existence (CI) |
| **Observable Notebooks 2.0** | never | `.observable/cache` | **no** | **manual** re-run; UI shows "query age" |
| **Pluto.jl** | never | none | n/a — but embeds `Manifest.toml`, an *input* | — |
| **Jupyter `.ipynb`** | **always** | n/a | unavoidably | none |
| **Quarto** | never in `.qmd` | `_freeze/` | **YES, recommended** | MD5 of **one** source file |

Four of six never commit results. Jupyter does it by accident of format, and the
ecosystem spent a decade building `nbstripout`, `nbdime` and `jupytext` to undo
it. Measured on a 15-line notebook: 317 bytes of source in a 69,130-byte file
(**218× bloat, 95.4% base64**); changing one literal produced a **131,328-byte
diff across 50 lines**, versus ~20 bytes and 1 line for the jupytext `.py`;
re-running with *zero* code change still produced a 1,976-byte diff of pure
timestamp churn. And two branches editing **disjoint** cells:

```
CONFLICT (content): Merge conflict in n.ipynb        (4 conflict regions, none semantic)
Auto-merging n.py                                    (0 conflict regions, both edits landed)
```

The reproducibility number that should end the argument, from Pimentel et al.,
MSR 2019 (1,159,166 notebooks from 264,023 GitHub repositories): of 863,878
attempted executions of valid notebooks, "**only 24.11% executed without errors
and only 4.03% produced the same results**."

Their vocabulary is the cleanest statement of the line this design draws:
**prospective** data (the cells) is source; **retrospective** data (outputs,
execution counters) is result. Commit the first, never the second.

**Quarto is the sole deliberate exception and its issue tracker is the receipt.**
It recommends checking in `_freeze/` — but only as a *transport mechanism* for an
environment CI cannot reconstitute ("esoteric or environment-specific
requirements… general fragility of dependencies over time"), and it warns in the
same breath: "you'll still want to take care to fully re-render your project when
things outside of source code change (e.g. input data)." The key is literally one
MD5 of one file (`freezeInputHash` = `md5HashSync(Deno.readTextFileSync(input))`)
— not data files, not the lockfile, not `_quarto.yml`, not includes. Every
predicted failure is filed: #3599 (cross-OS hash divergence producing
`<<<<<<< HEAD` inside a hash field), #4529 (conflict markers inside
`execute-results/*.json`, remedy "delete `_freeze` and re-render"), #6793
(includes don't invalidate, open since 2023), #10391 (stale vendored libs
silently reverting a site). quarto-web's own committed `_freeze` is
**14.67 MB / 199 blobs**, with post-execution markdown stored as one giant
single-line JSON string.

### 12.1 Two things to copy, one to avoid

**Copy: marimo's signature encoding of the DAG.** `def _(plt, x, y): … return x, y`
puts the dependency edges in reviewable plain text, canonically sorted
(`sorted(cell.refs)` in `codegen.to_functiondef`), so **topology changes appear in
code review for free** — while being non-authoritative, re-derived at load
(§2.3). That is the pattern for any derived material a file must carry.

**Avoid: Pluto's topological storage order.** Pluto writes cell bodies in
dependency order. Issue #3179, from a user, verbatim: "One of the advertising
features is 'Pluto notebook files are designed to work well with version
management.' **I would not subscribe to this statement**… the whole file shows up
as one large diff although one version only has a handful of cells added/changed
and the rest is some seemingly random resorting done by Pluto." **Store in
authored order; encode the graph elsewhere.** This is I1 (locality) restated, and
a reactive system violates it by default unless it is designed not to.

**Copy: Observable's graceful duplicate handling, in preference to marimo's.**
Observable's runtime: "If more than one variable has the same name… these
variables' definitions are temporarily overridden to throw a ReferenceError. When
and if the duplicate variables are deleted… the original definition of the
remaining variable is restored." So a merge that produces two `fee` cells breaks
*references to `fee`* and nothing else, and self-heals on resolution. marimo
refuses to run the entire notebook. **For a substrate where duplicates arrive
from merges rather than typos, Observable's failure mode is strictly better: it
is still loud (I3), still local (I1), and still leaves a working artifact (I5).**

### 12.2 The limit every one of them shares

None of them can see mutation. Verified against marimo's own `ScopedVisitor`:

```
cell1: defs=['data']  refs=[]        # data = {'n': 1}
cell2: defs=[]        refs=['data']  # data['n'] = 999   <-- MUTATION
cell3: defs=[]        refs=['data']  # print(data['n'])
```

The mutating cell **defines nothing**, so no edge cell2→cell3 exists and their
order is unconstrained. marimo's docs concede it: "marimo does not track
mutations to variables, nor assignments to attributes… Tracking mutations
reliably is impossible in Python." Pluto #564 is the same bug, open. Quarto
#6793 is the same bug at file granularity.

**This is not a reason to avoid the model; it is the reason a formula language
must be an expression language with no mutation at all.** A declarative
`total = qty * unit` has no `data['n'] = 999`. The notebook systems inherit this
wound because they embed a general-purpose imperative language. A design that
does not embed one does not inherit it — and that is a concrete argument against
"just use Python formulas" (Grist's choice) at the *core*, even though Grist's
runtime-tracing answer (§7.1) is the correct way to survive it if you do.

Their common failure mode is worth naming precisely, because this design will
have it too: **staleness at the boundary of static analysis** — the mutation the
AST cannot see, the data file the hash does not cover, the imported module
outside the cache key. Observable's most mature answer, reached only after trying
mtime inference, is to stop inferring and start *showing*: Notebooks 2.0 displays
a "query age" in the toolbar and requires manual re-run. **Make staleness
visible, not only inferred.**

---

## 13. Decisions, and what falsifies each

| Decision | Falsified by |
|---|---|
| **Column formulas, not cell formulas** | A workload where per-cell divergence is the norm rather than the exception. Excel's calculated columns permit it and flag it ("Inconsistent calculated column formula"); Grist forbids it and makes you convert the column to a trigger-formula data column. If field use shows per-cell overrides are common, the Quantrix answer (an override is a *new formula*, auditable and ordered by eclipsing) is the fallback — never "an override is data". |
| **One engine: suspending scheduler + constructive traces** | Demonstrated need for iterative calculation (§5b), or a workload where per-column memo bookkeeping still exceeds the compute. Note the engine is ~50 lines; the cost of being wrong is low. |
| **Nothing derived is committed** | A deployment where recomputation is impossible for a legitimate reason. Quarto proves this case exists. The answer is then Quarto's — a keyed cache in an ignored-by-default directory, never values inside the artifact — plus a key that covers the *whole* dependency set, which Quarto's does not. |
| **Opaque row id when there is no declared key** | Relaxing the single-writer constraint (§6.2), which breaks id stability and forces `(actor, counter)` identifiers. Or user research showing an extra visible column is intolerable — in which case the fallback is "refuse to auto-merge", not "guess". |
| **Tidy/long, key-sorted plaintext, optional Table Schema sidecar** | The premature-commitment finding (§9.2) if the sidecar becomes mandatory in practice. Watch for it: if users must write a schema before they can make a table, the format has failed on its own terms. |
| **Correctness sold as reviewability, not as types/units** | A controlled experiment showing structured/column-header references reduce errors. That experiment does not exist and would be cheap to run; Calculation View (§8.3) is the closest and it measures speed and workload, not errors. |
| **~30 functions, not 500** | A real user hitting the ceiling. Enron says 76% of usage is 15 functions; if that generalises, the ceiling is far away. |

### Three defects in the current prototype, found by measurement

All three are the same defect — *the evaluator is permissive where it must be
strict* — and all three produce plausible wrong numbers today:

1. **A conflicted file evaluates.** `grand = 1080.0`, where the two candidate
   answers were 480 and 720 (§7.3). Fix: refuse any file containing conflict
   markers.
2. **A duplicate column name silently last-wins.** `total = 135.6` with no error
   (§2.2). Fix: duplicate names in any namespace are a hard parse error.
3. **A short row is silently padded** by `merge3.py`. Fix: refuse.

Plus the one already recorded in L2 — the renderer dropped `| --: |` alignment —
which remains the best argument that I1 must be an enforced property test rather
than a coding guideline.

---

## Sources

Primary sources fetched and read for this pass. Session WebSearch budget was
exhausted early, so all web work was direct fetch of known URLs; anything that
could not be verified is flagged inline.

**Historical.** Garfinkel, *Improv: The Inside Story*, NeXTWORLD 1991
<https://simson.net/clips/1991/1991.NW.Improv.html> · Salas, *Why Improv didn't
succeed* (2004) <https://salas.com/2004/11/29/20041129why-improv-didnt-succeed-html/>
· Spolsky, *How Trello is different* (2012)
<https://www.joelonsoftware.com/2012/01/06/how-trello-is-different/> · Quantrix
Modeler Help 26.x <https://help.idbs.com/Quantrix/Modeler_Help/LATEST/>

**Spreadsheet research.** Peyton Jones, Blackwell & Burnett, ICFP 2003
<https://www.microsoft.com/en-us/research/wp-content/uploads/2016/07/excel-1.pdf>
· Sarkar, Gordon, Peyton Jones & Toronto, *Calculation View*, VL/HCC 2018
<https://www.microsoft.com/en-us/research/wp-content/uploads/2018/10/sarkar_2018_calcview.pdf>
· McCutchen et al., *Elastic Sheet-Defined Functions*, JFP 2020
<https://www.microsoft.com/en-us/research/wp-content/uploads/2018/11/elastic-sdfs-jfp2020.pdf>
· Joharizadeh, Sarkar, Gordon & Williams, *Gridlets*, CHI EA 2020
<https://www.microsoft.com/en-us/research/wp-content/uploads/2020/04/joharizadeh_2020_gridlets.pdf>
· Chalhoub & Sarkar, CHI 2022
<https://www.microsoft.com/en-us/research/wp-content/uploads/2021/12/chalhoub_2022_data_structuring.pdf>
· Sarkar et al., *End-user encounters with lambda abstraction*, VL/HCC 2022
<https://www.microsoft.com/en-us/research/wp-content/uploads/2022/06/sarkar_2022_lambdas.pdf>
· Hermans & Murphy-Hill, *Enron's Spreadsheets and Related Emails*, ICSE 2015

**Errors.** Panko, EuSpRIG 2000 <https://arxiv.org/abs/0802.3457> · Panko,
EuSpRIG 2015 <https://arxiv.org/abs/1602.02601> · McKeever & McDaid
<https://arxiv.org/abs/0908.0935>, <https://arxiv.org/abs/1009.2765>,
<https://arxiv.org/abs/1111.6872>

**Incremental computation.** Mokhov, Mitchell & Peyton Jones, *Build Systems à la
Carte*, ICFP 2018
<https://www.microsoft.com/en-us/research/uploads/prod/2018/03/build-systems.pdf>
and JFP 2020 <https://doi.org/10.1017/S0956796820000088> · Salsa
<https://salsa-rs.github.io/salsa/reference/algorithm.html>,
<https://salsa-rs.github.io/salsa/reference/durability.html>,
<https://salsa-rs.github.io/salsa/cycles.html> · rust-analyzer#19402 (memory
5–6 GB → 22–30 GB after the Salsa migration) · *Incremental Computation with
Names* <https://arxiv.org/abs/1503.07792> · *Differential Dataflow*, CIDR 2013
<https://www.cidrdb.org/cidr2013/Papers/CIDR13_Paper111.pdf> · Nix RFC 62 and
<https://www.tweag.io/blog/2020-09-10-nix-cas/> · Bazel remote-apis
`do_not_cache`

**Formats.** RFC 4180 <https://www.rfc-editor.org/rfc/rfc4180.txt> · W3C
Tabular Data Model <https://www.w3.org/TR/tabular-data-model/> and the archived
`w3c/csvw` · Table Schema v2
<https://datapackage.org/standard/table-schema/> · Wickham, *Tidy Data*
<https://vita.had.co.nz/papers/tidy-data.pdf> · `parquet.thrift` · SQLite
<https://sqlite.org/appfileformat.html>, <https://sqlite.org/sqldiff.html>,
<https://sqlite.org/sessionintro.html> · Dolt prolly trees
<https://www.dolthub.com/docs/architecture/storage-engine/prolly-tree> · Malloy
<https://docs.malloydata.dev/documentation/> · dbt `ref()`
<https://docs.getdbt.com/reference/dbt-jinja-functions/ref> and state-comparison
caveats · git-history <https://simonwillison.net/2021/Dec/7/git-history/>

**Notebooks.** marimo <https://docs.marimo.io/guides/reactivity/>,
<https://docs.marimo.io/api/caching/>, <https://marimo.io/blog/lessons-learned> ·
Observable runtime <https://github.com/observablehq/runtime>, Framework loaders
<https://observablehq.com/framework/loaders>, Observable 2.0
<https://observablehq.com/blog/observable-2-0> · Pluto #3179 and #564 · Quarto
code execution <https://quarto.org/docs/projects/code-execution.html> · Pimentel
et al., MSR 2019 <https://www.ic.uff.br/~leomurta/papers/pimentel2019a.pdf> ·
nbdime <https://nbdime.readthedocs.io/en/latest/>

**Source read.** `gristlabs/grist-core` (`sandbox/grist/depend.py`,
`relation.py`, `engine.py`, `table.py`, `lookup.py`, `column.py`, `schema.py`,
`useractions.py`, `functions/prevnext.py`; `app/server/lib/DocStorage.ts`,
`ActiveDocImport.ts`, `Export.ts`, `Patch.ts`) · `paulfitz/daff`
(`coopy/CompareTable.hx`, `IndexPair`, `Index.toKey`) ·
`dbt-labs/dbt-utils` (`generate_surrogate_key.sql`) · marimo 0.24.0
(`_ast/codegen.py`)

**Harnesses written and run for this pass.** `experiments/D6-computation/`:
`nb*.py`, `m2/` (marimo merge), `prev/` (`prev.` operator + merges),
`committed/` (committed-output merges), `rowid/ident2.py` (identity ablation),
`bsalc/engine.py` + `granularity.py` (engine falsification + memo cost).
