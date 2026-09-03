# R2 — Red team, round two: breaking the FIXED design

Target: the three mechanisms added after R1 — declared row order
(`experiments/X1-order/`), meaning-drift detection (`experiments/X2-drift/`),
and the conformance suite with its mutation gate (`conformance/`) — plus the
namespace audit (`experiments/X3-namespaces/`).

All reproductions are runnable:

    cd experiments && sh R2-order/run_all.sh

Every merge is stock `git merge` in a fresh repo: no `.gitattributes`, no merge
driver, no config beyond `user.name`/`user.email`. Every experiment imports
`conformance/ref_tbl.py` verbatim (copied in as `otbl.py`), i.e. the *fixed*
implementation, not an older prototype.

Severity: **(a)** silent-wrong under stock git · **(b)** silent-wrong under our
tooling · **(c)** false positive that gets the feature ignored · **(d)**
legitimate-but-terrible UX · **(e)** cosmetic.

---

## 1. Break catalogue, ranked

### (a1) `order := by(date)` — the design's own example — is a lexicographic sort of a STRING CONCATENATION, not a tuple

`experiments/R2-order/o1_string_dates.py`

    if order:
        def sortkey(r):
            try: return (0, float(r[order]), str(r.get(key, '')))
            except (ValueError, TypeError): return (1, 0.0, str(r[order]) + str(r.get(key, '')))

A date is not a float, so **every date-ordered table takes the second branch**,
where the "tiebreak" is *string-concatenated onto the order key* rather than
being a second tuple element.

    --- O1a a hand-typed unpadded month: 2026-2-1 (1 Feb) ---
       declared order actually used: ['2026-01-15', '2026-03-01', '2026-2-1']
       otbl says low = 45.0    (truth 5.0)
       the file is accepted, no error, no #REF!, no warning.

    --- O1b the same defect arriving through a CLEAN stock-git merge ---
       git merge exit=0 markers=0
       merged low = 55.0  truth = 5.0

`low := min(balance)` is an overdraft check. It reads 55.00 where the account
went to 5.00. Alice typed a date; Bob edited a distant row; git did nothing
wrong. This is the 480-vs-660 defect restored, one abstraction layer up: the
running total is now sensitive to *how the order key was spelled*.

### (a2) The opaque row id is a load-bearing input to row order

`experiments/R2-order/o1_string_dates.py`, O1c

Because the tiebreak is concatenated rather than tupled, the id participates in
comparisons between rows whose order keys **differ**:

    order := by(name); "Ann" < "Anna" in every collation on earth.
    otbl order: ['Anna', 'Ann']       <-- wrong
       "Ann"+"r_0001" = "Annr_0001"  vs  "Anna"+"a_0002" = "Annaa_0002"
    re-mint Ann's id r_0001 -> 0001: ['Ann', 'Anna']   <-- order flips

DESIGN §7 justifies the opaque id precisely because "a human writes column
names into formulas and never writes a row id into anything, so the id is
machine-managed noise, not an address." Here re-minting one row's id changes
the computed order of a **different** row, and therefore the value of every
row-relative column. The id is an address again.

### (a3) `key :=` is optional, so ties fall back to PHYSICAL FILE ORDER — insertion point decides the answer

`experiments/R2-order/o2_ties.py`

Nothing in `parse()` requires a key when an order is declared, and no
conformance case requires one. With no key, `r.get(None,'')` is `''` for every
row, every tie is unbroken, and Python's stable sort returns file order.

    --- O2b now add ONE row that ties on `day` with an existing row ---
       pasted above   order=[r_0001,r_0006,r_0005,...]  low=-40.0
       pasted below   order=[r_0001,r_0005,r_0006,...]  low=10.0

    --- O2c and it arrives through a clean stock-git merge ---
       Alice pasted above   git exit=0 markers=0  low=-40.0
       Alice pasted below   git exit=0 markers=0  low=10.0

Same base, same two edits, same declared order, two answers. X-open-problems
verified item 2 as *"physically shuffling every row in the file -> IDENTICAL
results"*; O2a reproduces that on the fixture used (distinct numeric keys, no
ties) and O2b breaks it with one tied row. **Two transactions on the same day
is the normal case for a ledger.**

O2d: even *with* `key := id`, ties are ordered by a lexicographic sort of
opaque ids — `r_10` before `r_9`. Deterministic and confluent, and not what any
author reading the file expects.

### (a4) `order := by(<a computed column>)` is silently `order := by(<row id>)`

`experiments/R2-order/o3_computed_order.py`, O3a

`evaluate()` sorts *before* it evaluates any column formula, so it sorts on the
blank cells of a computed order column. `float('')` raises, the row falls into
the string branch, and the sort key becomes `'' + id`.

    parse ACCEPTED. `order := by(seq)` where seq is computed.
    after re-minting r_0003 -> a_0003: [('a_0003','9'),('r_0001','1'),('r_0002','5')]  low = -5.0

`order := by(seq)` where `seq` is any derived ranking — the obvious way to
express an explicit sequence — silently orders by row id.

### (a5) `nan` in the order column destroys the total order

`experiments/R2-order/o3_computed_order.py`, O3b

    float('nan') is accepted by the order key. derived order: [r_0001,r_0002,r_0003,r_0004] low = 10.0
    the SAME rows, physically reordered in the file: [r_0003,r_0002,r_0001,r_0004] low = -40.0

`nan` compares false against everything, so `sorted()` is not sorting: physical
position decides. `inf`, `1_000`, `12.5e2` and fullwidth digits are all
accepted by `float()` too (S3d). R1 (b3) reported this for values; it is worse
in the order key, because there it decides the sequence.

### (a6) Three canvas namespaces the audit did not enumerate, all unprotected

`experiments/R2-namespaces/n1_missed.py`

    .canvas  edge identity (a -> b)      clean  (accepted)  UNPROTECTED
    .canvas  @layout anchor reference    clean  (accepted)  UNPROTECTED
    .canvas  @layout property name       clean  (accepted)  UNPROTECTED
    .tbl     aggregate function name     clean  (accepted)  UNPROTECTED
    .tbl     declaration keyword vs aggregate name  clean  (accepted)  UNPROTECTED

- **Edge identity.** An edge has no name; `(a,b)` *is* its identity. Two
  branches add `edge api -> auth` with different labels: clean merge, parser
  accepts, one relationship with two bindings.
- **`@layout` anchor.** `parse_canvas` checks that the override *key* is a
  known node and never checks the anchor on the right of `below:`. A node
  renamed on the other branch leaves `db { below: auth }` pointing at nothing —
  R1's C1a in a different spelling, in the validator written to fix C1a.
- **`@layout` property name.** `db { below: auth, below: api }` — two values
  for one property on ONE line. Co-location does not help here: git sees one
  line and the parser never looks inside the braces. This is the audit's own
  "SAFE (co-located)" verdict being wrong about what co-location buys.
- **`key`/`order` are reserved words inside the aggregate namespace.**
  `key := sum(qty)` matches the function-form regex, `name == 'key'` wins
  before the aggregate branch, and it is swallowed as a *key declaration* on
  column `qty`. The aggregate vanishes from the output and a uniqueness
  constraint appears from nowhere (S3e).
- **Aggregate function names** are an unvalidated namespace: `grand :=
  mean(total)` parses, and `grand` is simply never written to the output.
  `{{ t.tbl#grand }}` resolves to nothing.

### (a7) The FILE PATH is a namespace, and it is not in the audit at all

`experiments/R2-namespaces/n2_paths.py`

The address grammar is `artifact#namepath`, and the artifact half is a path.

    NFC 'café.tbl' bytes=9 / NFD 'café.tbl' bytes=10
    git merge exit=0
    tracked files: ['"caf\303\251.tbl"', '"cafe\314\201.tbl"', 'README.md']

Two artifacts, one apparent name, in `ls`, in a PR diff, and in every UI.
`{{ café.tbl#grand }}` resolves to 10 or to 20 depending on how the *reader's*
source is normalised. C4 mandates NFC "enforced by the parser" — a parser
cannot see a path. On macOS/Windows one checkout silently overwrites the other.
`Budget.tbl` vs `budget.tbl` is the same hole (N2b). `corpus_check.py` walks
paths and never looks at them.

N2c adds the **`.notes/` sidecar key space**: a note keyed to an artifact id
that does not exist passes `corpus_check` silently. The audit found the `cp`
duplicate and stopped at one half of the relation.

### (b1) The mutation gate: 17 new mutants, 17 survive

See §2. This is the largest single result.

### (b2) Meaning drift misses three rebindings, each with a wrong number

`experiments/R2-drift/d2_false_negatives.py` — see §3.

### (b3) Drift across a merge: the pair a tool would choose is silent

`experiments/R2-drift/d3_merge.py`

Alice does an ordinary header rename pass (`net`→`total`, `total`→`gross`) and
updates the one reference she can see. Bob, on his branch, adds
`reported := sum(total)` meaning the inc-VAT column.

    git merge exit=0 markers=0
    MERGED {'grand':288.0, ..., 'reported': 240.0}   <-- `reported` is now ex-VAT
    drift.check(base   -> merged): 0 finding(s)   <-- SILENT
    drift.check(alice  -> merged): 0 finding(s)   <-- SILENT
    drift.check(bob    -> merged): 1 finding(s)

`check(old,new)` has no three-way form and the design names no base. A PR check
compares the merge base, or the first parent, to the result — both silent. The
rebinding is visible only from the *second* parent, because a reference that
did not exist in the old version is never inspected
(`for label, oexpr in orefs.items()`).

### (b4) I3's "never zero" is violated by a table of only computed columns

`experiments/R2-suite/s3_live_defects.py`, S3c: `| a = 1 + 1 | b = a * 3 |`
with one empty row evaluates to `{'g': 0}`. The all-empty row matches
`is_align` and is dropped; `sum([])` is `0`.

### (b5) The CI workflow — the "portable enforcement point" — enforces neither thing it claims

`experiments/R2-suite/s5_cases_and_ci.py`, S5d

    step 1  runner.py   -> exit 0: TOTAL FAILURES: 0
            it runs the FIXTURES in cases.py. It never opens a single
            .tbl / .md / .canvas in the repository being checked.
    step 3  mutants.py  -> exit 1: FileNotFoundError: 'ref_tbl.py'

The step labelled *"validate every artifact (in-file namespaces)"* validates
zero artifacts in the repository. X3's central claim — nine of eleven
namespaces are safe "for anyone whose toolchain validates on load", and CI is
the portable place that happens — is not delivered by the shipped workflow.
The mutation-gate step crashes on a relative path and never runs at all.

`corpus_check.py` (S5c) run over a tree containing a `.tbl` with a duplicate
row id, a `.tbl` that does not parse, and an orphaned sidecar reports only
`1 duplicate id` — and it found that id **inside a fenced code block**.

### (c1) Meaning drift fires on six ordinary edits — see §3.

### (d1) Loud crashes where I3 promises local, propagating errors

`experiments/R2-suite/s3_live_defects.py`

    empty table, min() over zero rows        -> *** UNHANDLED ValueError
    one-row ledger, max(delta)               -> *** UNHANDLED ValueError
    unit = '1,500.00'                        -> *** UNHANDLED ValueError
    unit = '(500)'                           -> *** UNHANDLED ValueError
    order := by(<deleted column>), no row-relative column -> *** UNHANDLED KeyError

The `order not in cols` guard sits *inside* the loop over row-relative
formulas, so a table with none is never checked, and `sortkey` catches only
`ValueError`/`TypeError`.

---

## 2. New mutants that SURVIVE the conformance suite

`experiments/R2-suite/new_mutants.py` — same harness contract as
`conformance/mutants.py`, run against the unmodified `runner.py`/`cases.py`.

    2 killed, 17 SURVIVED, 0 stale

The two killed are deliberate controls (`drop-every-third-row`,
`render-reverses-rows`) proving the harness works. Every survivor is a real
behaviour change, demonstrated in `s2_mutants_are_real.py`:

    mutant                                              reference        mutant
    no-tiebreak-at-all                                      -40.0         -90.0
    tiebreak-reversed                                       -40.0         -90.0
    non-numeric-order-sorts-by-id-only                       10.0         -90.0
    prior-always-blank                                        9.0     ValueError
    delta-first-row-is-the-value                              4.0           9.0
    delta-is-negated                                          4.0           7.0
    count-off-by-one                                            2             1
    count-ignores-blanks                                        2             1
    unknown-aggregate-fn-silently-becomes-sum                None          10.0
    sum-crashes-on-a-blank-cell                               1.0     ValueError
    blank-cell-in-a-real-column-is-zero               #REF!(unit)         120.0
    float-accepts-thousands-separators                 ValueError        3000.0
    strip-only-ascii-spaces                                 120.0    #REF!(qty)
    computed-columns-evaluated-in-reverse-header-order  #REF!(net)         144.0
    allow-duplicate-order-declaration                     REFUSED           2.0
    order-none-is-ignored                                 REFUSED       REFUSED*
    is-align-matches-any-dashed-cell                         35.0          20.0

    17/17 surviving mutants demonstrably change an answer on a plausible input.

Concrete additions to `mutants.py` (patterns verified present in `ref_tbl.py`;
the full dict is in `new_mutants.py`, copy it wholesale):

    'no-tiebreak-at-all':
      ("try: return (0, float(r[order]), str(r.get(key, '')))",
       "try: return (0, float(r[order]))"),
    'non-numeric-order-sorts-by-id-only':
      ("except (ValueError, TypeError): return (1, 0.0, str(r[order]) + str(r.get(key, '')))",
       "except (ValueError, TypeError): return (1, 0.0, str(r.get(key, '')))"),
    'prior-always-blank':
      ("elif fn == 'prior':    r[nm] = prev if prev is not None else ''",
       "elif fn == 'prior':    r[nm] = ''"),
    'delta-first-row-is-the-value':
      ("elif fn == 'delta':    r[nm] = (v - prev) if prev is not None else ''",
       "elif fn == 'delta':    r[nm] = v"),
    'count-off-by-one':
      ("elif fn == 'count': out[nm] = len(vals)", "elif fn == 'count': out[nm] = len(vals) - 1"),
    'blank-cell-in-a-real-column-is-zero':
      ("        v = env.get(node.id, '')",
       "        v = env.get(node.id, '')\n        if node.id in env and v == '': return 0.0"),
    'computed-columns-evaluated-in-reverse-header-order':
      ("        for nm, expr in formulas.items():\n            if any(re.search",
       "        for nm, expr in reversed(list(formulas.items())):\n            if any(re.search"),
    'allow-duplicate-order-declaration':
      ("if order is not None: raise Malformed(f'line {n}: duplicate order declaration')", "pass"),
    'is-align-matches-any-dashed-cell':
      ("def is_align(l): return all(re.fullmatch(r':?-{2,}:?', c) for c in split_row(l) if c != '')",
       "def is_align(l): return any(re.fullmatch(r':?-{2,}:?', c) for c in split_row(l) if c != '')"),

**What the survivors mean, grouped.**

1. **The tiebreak, on which the confluence claim rests, is untested.** Three
   mutants that break it survive. Not one case in the suite has a tie.
2. **Two of the three row-relative operators are entirely unexercised.**
   `prior` and `delta` appear in no case at all — so their first-row semantics,
   their sign, and their interaction with `order` are unspecified in practice.
3. **`count` is untested; unknown aggregate functions are silently dropped;
   blank cells in an aggregated column are untested.**
4. **Numeric coercion is untested in every direction** — thousands separators,
   NBSP, `nan`, `inf`, `-0.0`, unicode digits.
5. **Dependency order between computed columns is HEADER POSITION**, with no
   topological sort. Reversing it changes `#REF!(net)` into `144.0`. That is a
   coordinate inside the computation model, i.e. an I2 violation the suite
   cannot see, and reordering columns — which the drift detector explicitly
   treats as benign — changes results.
6. **`order` is validated for duplicates but `key` is the one the suite tests.**

### Is `render(structure(b)) == b` non-tautological now?

Barely, and not in the way claimed. `structure()` stores the raw lines
(`header_raw`, `align_raw`, `row_raws`, `tail`, `prefix`); `render()`
concatenates them; the parsed entity map is carried along and **never
consulted**. `experiments/R2-suite/s4_roundtrip_vacuous.py`:

    S4a  structure(text) -> {'raw': text};  render(st) -> st['raw']
         roundtrip cases passed: 5/5
    S4b  a parser that binds every cell after the first two to the WRONG column:
         reference eval {'grand': 480.0}   garbled eval {'grand': '#REF!(qty)'}
         roundtrip/basic ... /wide  exact=True  (all five)

A parser that understands nothing passes; a parser whose entity map is wrong
for every row passes. Both mutants X4 credits to round-trip mutate `render`,
not `parse`. The law tests the renderer against the raw-line store.

S4d is a live defect it *does* hide: a blank line inside the table is dropped
on render (78 B in, 77 B out) because `row_raws` takes only lines at table
indices and `tail` starts after the last one. No case covers it.

### Do `expect_merge` outcomes assert the right thing?

Two pass for the wrong reason (`s5_cases_and_ci.py`):

- `merge/column-name-collision` — `addcol()` appends a cell to *every* line, so
  the conflict is guaranteed by the row edits, not the header collision. (The
  property does hold; S5a re-tests it with identical row cells and git still
  conflicts. The case as written cannot show it.)
- `MUST_REFUSE` checks only `except ref.Malformed`, never why. An
  implementation that refuses any table with more than six lines passes both
  MUST_REFUSE cases.
- `confluence/ledger-three-way` uses `final := max(balance)` over a positive
  total, which is `sum()` — commutative. Running it against the
  `ignore-declared-order` mutant (`R2-order/o4_confluence.py`):

      reference impl         {(('final', 139.0),)} (1 outcome)
      `ignore-declared-order` {(('final', 139.0),)} (1 outcome)

  The suite's only confluence case is green for an implementation that never
  sorts.

### `corpus_check.py` holes

Never invokes the parser; matches `^id:` anywhere including inside fenced code;
ignores path collisions; ignores dangling `.notes/` keys; ignores files it
cannot parse. The nine "protected by validation" namespaces are not validated
by the corpus pass, and the CI step that claims to do it does not (§1 b5).

---

## 3. False positives in the drift detector

`experiments/R2-drift/d1_false_positives.py`. Identity is *formula text*
compared after a rename substitution, so **any** textual edit rebinds the
column and every unchanged reference to it fires.

    whitespace only:  `total * 1.2` -> `total*1.2`          1 finding  FALSE POSITIVE
    operand order:    `qty * unit`  -> `unit * qty`          1 finding  FALSE POSITIVE
    redundant parens: `total * 1.2` -> `(total) * 1.2`       1 finding  FALSE POSITIVE
    a VAT rate change: 1.2 -> 1.25                           1 finding  FALSE POSITIVE
    fixing a formula: `qty*unit` -> `qty*unit - 0`           1 finding  FALSE POSITIVE
    reconciling one literal column onto another's values     1 finding  FALSE POSITIVE

The fourth is fatal in practice. **Changing a rate is the single most common
edit a spreadsheet ever receives**, and it produces `MEANING DRIFT` on every
downstream aggregate — a message that says a name "was rebound" when the author
deliberately edited the formula in the same commit and can see it in the diff.
X-open-problems reports "zero false positives on the benign cases tested" over
seven hand-picked cases; the sixth here (copying one column's values onto
another, an ordinary reconciliation) also fires, from the value-vector check.

A detector that fires on whitespace will be muted within a week, and once muted
it stops catching the rename-swap it exists for. Ranked (c), the category the
brief names as the one that kills a feature.

### False negatives

`experiments/R2-drift/d2_false_negatives.py`

    N1 rename literal `unit` (a PRICE) to `price`, give the freed name `unit`
       to a NEW literal column (pack size); formulas untouched
         grand: 240.0 -> 80.0     findings: 0   <-- SILENT
    N2 swap two literal column names AND edit their data in one commit
       (`rate = qty / unit`; division does not commute)
         avg: 9.0 -> 0.558...     findings: 0   <-- SILENT
    N4 change `order := by(day)` to `order := by(seq)`
         low: 10.0 -> -90.0       findings: 0   <-- SILENT

N1 is R1's headline rename-swap with *literal* columns, which is the common
case: definition-based identity sees nothing because no definition changed, and
the permutation check sees nothing because no value vector moved. N2 defeats
the permutation check by editing data in the same commit — an author doing a
rename pass and a data correction together. N4 is the sharpest: `drift.defs()`
explicitly excludes `key` and `order`,

    if name not in ('key', 'order'): refs[f'{name} :='] = f'{fn}({arg})'

so **the one declaration that defines row-relative meaning — the entire subject
of mechanism 1 — is never compared across versions.** The two new mechanisms do
not compose.

---

## 4. Namespaces the audit missed

Seven, in the three formats it already covers, plus one it structurally cannot:

    .tbl     declaration keyword vs aggregate name   UNPROTECTED   (a6)
    .tbl     aggregate function name                 UNPROTECTED   (a6)
    .canvas  edge identity (a -> b)                  UNPROTECTED   (a6)
    .canvas  @layout anchor reference                UNPROTECTED   (a6)
    .canvas  @layout property name                   UNPROTECTED   (a6)
    (paths)  artifact path, NFC/NFD and case         UNPROTECTED   (a7)
    (paths)  .notes/ sidecar key -> artifact id      UNPROTECTED   (a7)
    (n/a)    row ORDER, when the order key ties      UNPROTECTED   (a3)

The last is a namespace of a different kind and the most interesting: declared
order makes *sequence position* a derived binding, and the binding is not
total. The audit's schema — "co-located or validated" — has no cell for it.

**Is "validated" protection real?** No, on the shipped artifacts. The
enforcement point is CI; the CI workflow runs the fixture suite, not the
repository's artifacts, and its mutation-gate step crashes (§1 b5). Beyond
that, X3's own argument concedes the shape of the hole: a contributor who
merges locally and pushes to a branch with CI disabled, or a forge merge button
on a repo whose required checks are not configured, sees none of the nine.
Under those conditions nine of eleven audited namespaces plus the seven above
are silent-wrong generators, which is I6 not holding for 16 of 18 namespaces.

---

## 5. What held under attack

Credible negatives. Each was attacked and did not break.

1. **Confluence over three branches with a NON-commutative aggregate.**
   `R2-order/o4_confluence.py` O4b: six merge orders, `low := min(balance)`,
   negative amounts — **1 distinct outcome**. I expected this to fall and it did
   not. Where the order key is numeric and unique, the mechanism does what it
   claims.
2. **Physical shuffling is irrelevant when the order key is numeric and
   distinct** (O2a). The X1 claim is true on its fixture; it fails only on ties,
   strings and `nan`.
3. **`order := none` really does make row-relative operators a parse error**,
   and the message names the fix. I could not evade it.
4. **Column-name co-location holds.** S5a: two branches adding *differently*
   named columns with identical row cells still conflict, because the header is
   one line.
5. **The conflict-marker check** survived everything I threw at it, including
   markers inside the declaration block.
6. **Drift catches a three-way rename cycle** of literal columns with data
   untouched (N3: 3 findings), a swap of two computed columns' *definitions*
   (D4b), and a literal name swap under computed references (D4c).
7. **The rename fixpoint terminates** — the loop is bounded by `len(od)+1` — and
   I could not make it mis-converge into a numeric error.
   `R2-drift/d4_rename_fixpoint.py` D4a shows the map is a greedy first match
   over an unordered dict and resolves an ambiguous rename arbitrarily, but two
   columns with identical definitions denote the same value, so the ambiguity
   has no numeric consequence. I tried three constructions; all were caught or
   harmless. This is the one place where I attacked hard and got nothing.
8. **Duplicate `order :=`, duplicate `key :=`, duplicate column and duplicate
   aggregate names are all refused** by the parser, including the NFC/NFD forms.
   The R1 (a1) scattered-aggregate defect is genuinely fixed.
9. **`merge/duplicate-row-id` and `merge/scattered-aggregate` do refuse** — the
   MUST_REFUSE outcome is weakly asserted (§2) but the underlying behaviour is
   right.

---

## 6. Judgement: sound, or merely untested?

**Declared row order: the idea is sound; the implementation is not, and the
gap is not incidental.** "The previous row is the row with the next-lower key"
is the right reformulation of `prev.`, and O4b shows it delivers confluence
where the key is a well-behaved total order. But the design asserts a total
order and ships a partial one. Three of the four things people actually order
by — dates written as text, keys with duplicates, and derived rankings — are
outside the numeric happy path, and every one of them silently falls back to
*physical file position*, which is the exact coordinate the mechanism was built
to eliminate. **The defect did not move; it moved into the sort key.** It is
fixable — require `key` whenever `order` is declared, make the sort key a
genuine tuple, type the order column and reject a mixed one, reject `nan`,
forbid ordering by a computed column or evaluate before sorting — and none of
those fixes is deep. But as it stands the mechanism is *untested* in the exact
place its correctness argument lives, and it is currently **silently wrong on
its own documented example**, `order := by(date)`.

**Meaning drift: not sound, and I do not think this version is salvageable in
its current framing.** It fires on whitespace and on a rate change (§3) and
stays silent on the literal-column rename-swap, on a swap combined with a data
edit, and on the `order :=` re-declaration that redefines every row-relative
column. That combination is the worst one available: it is noisy on the edits
people make daily and quiet on the ones it exists to catch. The root problem is
that formula *text* is being used as a proxy for meaning, and text equality is
neither necessary nor sufficient for it. Something narrower would be more
honest — for instance, alert only when a name's binding changes while every
*reference* to it stays byte-identical **and** the previous binding survives
under a different name, which is exactly the rename-swap signature and nothing
else. Also, it needs a defined base for merges; it has none, and two of the
three available pairs are silent (§1 b3).

**The conformance suite: the right deliverable, and currently the weakest of
the three.** Its structure is correct — cases as data, assertions on evaluated
values after a stock-git merge, a mutation gate — and the gate is what let me
falsify it in one afternoon, which argues for it. But "15 mutants, 15 killed, 0
survived" measures the mutants, not the suite: 17 more, all plausible, all
survive, and they cluster exactly where the two new mechanisms live (the
tiebreak, `prior`/`delta`, numeric coercion, computed-column dependency order).
The round-trip law is still satisfiable by a parser that understands nothing.
The confluence case is green for an implementation that ignores order. And the
CI workflow that X3 identifies as the design's one portable enforcement point
validates no artifact and its gate step crashes.

The direction survives round two as it survived round one. What does not
survive is the second assurance in a row: *"11 namespaces, 0 unprotected"* and
*"15 mutants, 15 killed"* are both artifacts of the enumerator and the mutation
author being the implementation author. That is now the third independent
instance of the same failure mode in this project, and it is the argument for
the suite being written adversarially, by someone other than the implementer,
as a standing role rather than a pass.
