# M0 — adversarial conformance cases

Written from `SPEC.md` and the existing fixture tree only. `rowspec/reference/`
was **not** read. Two disclosures: (a) `conformance/mutants.py` stores its
mutants as literal source-patch pairs, so enumerating the existing mutant names
exposed ~30 fragments of implementation source; (b) after writing the fixtures I
called `ref.evaluate` / `ref.canon` / `ref.render` on my own inputs to diagnose
failures, which is what the runner does anyway. No case expectation was derived
from either — every expectation below is derived from a quoted sentence.

74 new cases: parse 32, eval 11, rowrel 10, merge 9, canon 7, roundtrip 2,
confluence 2, mutate 1. Nothing existing was modified or deleted.

Suite result: **20 of the 74 fail** against the current implementation.

---

## 1. Failures where the IMPLEMENTATION is at fault

### 1.1 Two silent-data-loss bugs (the important ones)

**`parse/no-alignment-row`** — §4: *"The table is a contiguous run of lines
beginning with `|`. The first is the HEADER, the second is the ALIGNMENT row,
the rest are DATA rows."*

A three-line table whose second line is a data row is **accepted, and the first
data row is silently consumed as the alignment row**:

    | id | qty | unit |
    | r_01 | 10 | 12.00 |
    | r_02 | 5 | 24.00 |
    ...
    g := sum(qty)

evaluates to `rows = [r_02]`, `g = 5.0`. The correct answer is either a refusal
or `15.0`; the one thing it must not be is a smaller number with a row missing.
This is precisely the failure mode §1 exists to prevent, and it is reachable
from a merge (see §1.2 of this document, and `merge/short-row-arrives-by-merge`,
which is the same class).

**`canon/idempotent-alignment-variants`** — §10: *"canonicalisation is a
separate explicit operation with `canon(canon(x)) == canon(x)`."*

Given an alignment row spelled with GFM's short forms —
`| :--- | :-: | ---: | :--: | -: |` — `canon` **emits no alignment row at all**,
and the second `canon` pass then eats the first data row:

    canon(x)        -> header, r_0001, r_0002      (alignment row gone)
    canon(canon(x)) -> header, r_0002              (r_0001 gone)

So `canon` is not idempotent *and* it destroys a row on the second application.
The two bugs are the same defect seen twice: the alignment-row recognizer
demands a spelling that the format never specified, and everything downstream
treats "not an alignment row" as "is a data row" or "there was none".

### 1.2 Unimplemented §7 features that the suite never asked for

- `eval/aggregate-where-literal` — §7: *"`eu    := sum(total where region =
  "EU")`"*. Refused as a malformed declaration.
- `eval/group-aggregate-at-ref`, `eval/group-aggregate-two-keys`,
  `parse/group-aggregate-syntax` — §7: *"`| region_total = sum(amount where
  region = @region) |`"* and *"`| rep_share = sum(amount where region = @region
  and rep = @rep) |`"*. **Uncaught `SyntaxError`.**
- `parse/lookup-syntax` — §7: *"`| who = lookup(customers.mdtbl, customer, name)
  |`"*. **Uncaught `AttributeError`.**
- `eval/avg-basic` — §7: *"Functions: `sum`, `count`, `min`, `max`, `avg`."*
  `avg` returns `None`, i.e. an aggregate name that the spec declares silently
  produces nothing.

The suite had **zero** coverage of `where`, `@`, `lookup` or `avg` — over half
of §7. That is the clearest signal that the suite was written to the
implementation's shape rather than to the spec's.

### 1.3 Recognition is not total — nine uncaught exceptions

§9: *"Recognition is total: every byte sequence has exactly one defined
outcome, and a parse error is *reported* separately from being *handled*."*
A Python traceback is neither outcome. Nine of my cases produce one; four
of them (the `lookup` and group-aggregate cases) are listed in §1.2 above.

- `eval/ref-poisons-every-aggregate` — **`ValueError: could not convert string
  to float: '1,000'`**. §8: *"An aggregate over any column containing a `#REF!`
  is itself `#REF!` — it must not sum the values it can read."* The existing
  suite only ever routed a bad value through a *computed* column
  (`eval/thousands-separator-refused`); a table-level aggregate reading the raw
  column directly crashes. This is a live bug, not just a missing feature.
- `parse/formula-syntax-garbage` (`x = 2 ** * 3`) — `SyntaxError`. §7 defines a
  formula as *"Arithmetic over column names"*, so this is not one.
- `parse/formula-reads-the-clock` (`x = time.time()`),
  `parse/formula-reads-a-path` (`x = open('/etc/hostname').read()`),
  `parse/formula-imports` (`x = __import__('os').getpid()`) — `AttributeError`.
  §8: *"Constructs that would read the clock, the network, or a path are not
  blocked — they are unparseable."* The good news is that none of the three
  executes; the bad news is that "unparseable" is delivered as a crash rather
  than a refusal, so a validator cannot report it. (`parse/aggregate-calls-python`
  passes — the declaration form does refuse.)

### 1.4 Refusals the spec mandates and the implementation skips

- `parse/computed-cell-has-value` — §5: *"A column with a formula is COMPUTED
  and its data cells are empty. Writing a value into a computed cell is an
  error."* The file is accepted and the hand-written `99` is silently discarded
  (`grand` stays `480.0`). Note the asymmetry: `mutate/computed-col-refused`
  already proves the *API* refuses this write, but the *parser* accepts a file
  that already contains one — and a text editor or a merge can produce one.
- `parse/cf-in-column-name`, `parse/cf-in-aggregate-name` — §3: *"`Cf` format
  characters are rejected in identifiers."* A ZWJ (U+200D) inside a column name
  or an aggregate name is accepted, so two visually identical identifiers can
  coexist. `parse/cf-in-key-declaration` passes only by accident (the ZWJ makes
  the declaration fail its own syntax check, reported as "malformed
  declaration", not as a Cf rejection).

### 1.5 Missing ignorable channel

- `parse/comment-after-declaration`, `eval/comment-is-inert` — §6 prints
  `order := by(date)      # or omitted entirely` as a legal declaration line,
  and §9 asserts *"Exactly one ignorable channel exists, and it carries an
  *inertness promise*"* and *"one differing from a valid file only by a
  comment"*. The reader refuses it as a malformed declaration. Either the
  implementation is missing the channel or the spec must name it (see gap 3).

## 2. Failures where I judge the SPEC at fault

- **`parse/crlf-refused`** — §3: *"UTF-8, LF line endings, no BOM. … Enforced by
  the parser."* The implementation accepts CRLF and round-trips it byte-exactly,
  and the pre-existing `roundtrip/crlf` case *requires* that. Per the preamble
  (*"Where this document and the conformance suite disagree, the suite wins"*),
  §3 is in error: CRLF is preserved, not refused. Recommendation: amend §3 to
  say line endings are preserved verbatim and only the *canonical* form is LF,
  then delete this case. (`parse/bom-refused` passes — the BOM half of the
  sentence *is* enforced, which is why the CRLF half reads as an oversight.)
- **`parse/lone-cr-refused`** — same §3 sentence, plus §1: *"Git merges by line.
  So one line is one row."* Here I think the refusal is genuinely right and the
  spec merely under-argues it: the implementation treats a bare `\r` as a row
  separator, so **two rowspec rows share one git line**. Two authors editing
  those two rows then collide, which is exactly the property §1 is built to
  guarantee. I would keep this case and add the justification to §3.

## 3. Spec gaps — things I could not write a case for

1. **The alignment row has no defined syntax, and no defined optionality.** §4
   names it, §9.7 refuses a field-count mismatch in it, §9.8 refuses an
   "alignment-style row" among the data — but nothing says which spellings are
   an alignment row (`---`, `--:`, `:-:`, `-:`, `-`?) or what happens when line
   2 is not one. Both silent-data-loss bugs in §1.1 live in that gap.
2. **§7 `lookup` contradicts §8.** §7 defines `lookup(customers.mdtbl, …)`;
   §8 says constructs that *"would read … a path are not blocked — they are
   unparseable."* One of the two must go. Separately, the **fixture format
   cannot express a lookup at all**: `run_cases.py` reads every `*.mdtbl` in the
   case directory but hands only `f["input"]` to `evaluate`, so a second table
   for the lookup to resolve against is unreachable. §7's cross-artifact
   feature — including the mandated `#REF!(file[key])` for an absent target —
   is untestable until the runner grows a directory-based entry point.
3. **The ignorable channel is asserted but never defined.** §9 promises exactly
   one such channel and a testable inertness promise; the spec never says what
   it looks like. The only evidence anywhere is the `#` comment in §6's example.
4. **Blank cells in the order column.** §6 requires *"a single type across all
   rows"*; a blank has no type. Refuse, or sort? Undefined.
5. **Aggregates over zero rows.** `parse/no-data-rows` is accepted; the spec
   never says whether `sum` of nothing is `0`, blank, or `#REF!`, nor what
   `min`/`max`/`avg` do.
6. **Evaluation order of computed columns.** §7 never says a computed column may
   reference another (the existing `rowrel/chained-computed` assumes it), nor
   whether a *forward* reference resolves. There is already a mutant named
   `computed-columns-evaluated-in-reverse-header-order` for a rule the spec
   does not state.
7. **Cycles.** §8 promises only that the evaluator terminates. What
   `b = b + a` or `x = y, y = x` *evaluate to* is undefined; I filed those two
   as accept-cases (`parse/self-referential-column`,
   `parse/mutually-recursive-columns`) purely to pin down "does not hang or
   crash", and both currently pass.
8. **Coercion is specified by example, not by rule.** §8 names three refusals
   (thousands separators, parenthesised negatives, non-ASCII spaces) and stops.
   Leading `+`, `1e3`, `inf`, `nan`, surrounding ASCII spaces, unicode digits,
   and a leading `.` are all undefined — the textbook *"undocumented degree of
   freedom [that] becomes an interoperability bug"* of §2. Note §6 refuses
   non-finite values in the *order* column but says nothing about `inf` in an
   arithmetic column.
9. **`count` semantics.** The suite says count includes blanks
   (`eval/count-includes-blanks`); the spec never says whether it counts rows or
   values, nor how §8's `#REF!` poisoning applies to it.
10. **Duplicate row ids with no `key` declaration.** §9.5's qualifier *"where a
    key is declared"* implies acceptance; nothing states it. Filed as
    `parse/duplicate-id-without-key-declared` (accept) on that reading — it
    passes.
11. **`.rowspec` / editions (§12) have no observable behaviour** (*"A reader
    never consults it"*), so nothing in the fixture format can test §12 at all.
12. **File shape edges**: whether the blank line before the declarations is
    required, whether text may follow the declarations, and whether a file may
    have a table and no declarations (I filed `roundtrip/no-declarations` on the
    assumption it may; it passes).

## 4. Proposed new mutants

Described semantically; the point is the defect, not a patch.

**Alignment row / shape**
1. `alignment-row-optional` — accept a table whose second line is a data row,
   consuming that row as the alignment row. (Currently a *real* bug.)
2. `is-align-requires-three-dashes` — the alignment recognizer rejects GFM's
   `:-:`, `-:`, `:-`, so such a row is treated as data. (Real bug.)
3. `canon-omits-an-unrecognised-alignment-row` — canon emits no alignment row
   when it did not recognise the input's, so a second pass eats a data row.
   (Real bug; the idempotence assertion is what catches it.)

**Ordering**
4. `date-order-falls-back-to-string-sort` — a date-typed order column sorts
   lexicographically, so `2024/01/05` follows `2024-02-01`.
5. `date-order-requires-zero-padding` — unpadded `2024-1-5` degrades to text
   comparison while padded dates stay chronological.
6. `mixed-type-order-is-accepted-with-strays-last` — instead of refusing a
   mixed-type order column, push the uncoercible rows to the end.
7. `order-accepts-non-finite` — `inf`/`nan` in the order column sort as ±inf /
   sink to one end rather than being refused.
8. `order-without-key-uses-file-position` — accept `order` with no `key` and
   break ties by physical position (the exact coordinate §6 forbids).
9. `order-by-the-key-column-becomes-a-no-op` — `order := by(id)` where `id` is
   the key silently degrades to file order.

**Error propagation**
10. `aggregate-over-an-uncoercible-cell-raises` — a table-level aggregate over a
    stored column holding `1,000` throws instead of yielding `#REF!`. (Real bug.)
11. `count-counts-through-a-ref` — `count` over a column containing `#REF!`
    returns the row count rather than `#REF!`.
12. `min-max-skip-refs` — `min`/`max` ignore `#REF!` cells and report the
    extremum of the readable ones — literally *"summing the values it can read"*.
13. `avg-divides-by-the-readable-count` — `avg` divides by the number of
    coercible cells, so `avg * count != sum`.
14. `cumulative-carries-past-a-ref` — a `#REF!` in the middle of a running total
    is skipped and the total continues, so only the poisoned row looks broken.
15. `single-row-delta-is-zero` — `prior`/`delta` on the first row (or a one-row
    table) yield `0` rather than blank — §8's *"never evaluates to zero"*
    generalised to the row-relative operators.
16. `prior-skips-blank-rows` — `prior(c)` returns the last *non-blank* value, so
    the preceding row is not the preceding row.

**Formulas §7**
17. `group-aggregate-ignores-its-predicate` — `sum(amount where region =
    @region)` returns the whole-column sum.
18. `group-aggregate-uses-only-the-first-conjunct` — the `and` in a two-term
    predicate is dropped, so `rep_share` becomes `region_total`.
19. `where-literal-is-coerced` — a quoted literal is numeric-coerced before
    comparison, so `region = "EU"` matches nothing (or everything).
20. `lookup-missing-row-is-blank` — an absent lookup target yields empty instead
    of `#REF!(file[key])`.
21. `lookup-resolves-by-row-index` — the lookup uses the target's position
    rather than the target's own declared key, making a row id an address.
22. `lookup-into-a-keyless-table-picks-the-first-match` — resolve against a
    target with no `key` declaration instead of refusing.
23. `self-referential-column-recurses` — a column naming itself recurses to a
    stack overflow, breaking *"the evaluator is total, terminating"*.
24. `formula-attribute-access-is-evaluated` — `time.time()` / `open(...)` inside
    a formula is executed instead of being unparseable. Nothing catches this
    today, and it is the security half of §8.

**Encoding / identifiers**
25. `cf-characters-survive-identifiers` — ZWJ or soft hyphen in a column name is
    accepted, so two visually identical names coexist. (Real bug.)
26. `nfc-normalisation-applied-to-cell-values` — normalise data cells as well as
    identifiers, silently rewriting user text and breaking byte-exact round-trip.
    §3 restricts NFC to identifier *comparison*; nothing tests the restriction.
27. `lone-cr-joins-two-rows` — a bare `\r` is treated as intra-line text so two
    rows share one git line.
28. `render-normalises-line-endings` — round-tripping a CRLF file rewrites every
    line, turning a one-cell edit into a whole-file diff.

**Canon / merge**
29. `canon-collapses-whitespace-inside-cells` — canon rewrites cell *values*, not
    just the delimiters, i.e. it edits data while claiming to edit decoration.
30. `canon-writes-rows-in-derived-order` — canon sorts the file by the order
    column, so canonical bytes depend on a value and one order-column edit
    reflows the file — manufacturing exactly the conflicts §10 exists to remove.
31. `merge-validation-trusts-gits-exit-code` — the merge path reports success
    whenever git exits 0 and never re-parses the merged file. §11's central
    claim (*"a tool that only inspects conflicts will publish git's wrong
    answer"*) has cases but no mutant.
32. `annotation-text-reaches-the-evaluator` — a trailing `#` annotation is kept
    as part of the expression, so stripping annotations changes a value —
    the inertness promise of §9 broken directly.
33. `refusal-choice-is-nondeterministic` — with two independent refusals in one
    file, which is reported varies between runs, breaking *"exactly one defined
    outcome"*. (`parse/two-refusals-*` pin one outcome each.)

## 5. Where the existing suite is weakest

1. **It tests the implemented subset, not the specified one.** `where`
   predicates, `@` group aggregates, `lookup` and `avg` — the majority of §7 —
   had no case at all. A suite that omits every unimplemented feature cannot
   distinguish "conforms" from "implements the same subset".
2. **Nothing asserted totality.** No case checked that a hostile input yields a
   refusal rather than a traceback; 9 of my 74 produce uncaught Python
   exceptions, including one (`1,000` read by a table-level aggregate) that is a
   plain bug in already-shipped behaviour.
3. **Fixture monoculture.** All 8 merge cases and all 5 canon cases are built
   from the same two tables (the 4-row widget table and the 3-row ledger). §10's
   headline *measured* claim — padded edits conflict, canonical ones merge
   cleanly — had no case whatsoever; `merge/padded-widening-conflicts` and
   `merge/canonical-widening-clean` now prove it under stock git.
4. **Canon idempotence was only tested on inputs that were already nearly
   canonical.** One non-default alignment spelling breaks it, with row loss.
5. **Order was tested with one type and no ties.** Every pre-existing order
   fixture used small positive integers in already-sorted file order, so the
   tuple sort of §6, dates in either spelling, text order, negatives and ties
   were all unexercised — which is why the mutation gate needed three
   tiebreak mutants that no fixture could distinguish from the outside.
6. **Refusal cases test the happy path of refusal.** Each of the thirteen was
   tested in isolation, in a hand-built file. None arrived via a merge (four now
   do), and none co-occurred with another refusal.

---

# Addendum — the two surviving mutants

Written after the §4/§3/§7/§9 amendments and the reference fixes. Three cases
added (two were requested; the third is inside the same mutant's scope and is
called out below). Suite is now **133 cases, 0 failures**.

**Read this section with its timeline.** Both new cases that assert a behaviour
change FAILED when written — `eval/non-ascii-space-padding-refused` reported
`grand = 253.0` and `parse/order-none-refused` was accepted — and the
implementation was corrected during the same pass, in the direction argued
below, while this was being written. The reasoning is left standing because it
is the justification for the cases, not a bug report; each case's `WHY.md`
carries the same record. Gate at the moment the cases landed:
**33 killed, 1 survived, 2 equivalent, 0 stale**. After the fix, three mutant
patterns no longer match the rewritten source and the gate reports them
**stale** — `strip-only-ascii-spaces`, `order-none-is-ignored` and
`allow-duplicate-order-declaration`. `mutants.py` is yours; I did not touch it.
Re-aiming guidance is in §B below.

## A. `order-none-is-ignored` — KILLED, plus one real bug

The reference parses an order declaration as `fn(arg)` and keeps `arg` only
when `fn == "by"`. Everything else silently becomes "no order declared". The
mutant keeps `arg` unconditionally.

**Why nothing killed it.** The two behaviours are indistinguishable on
`order := none()`, because `arg` is then `""`, which is as falsy as `None`. The
difference is observable only when the unrecognised construct carries an
argument, *and* the file contains a row-relative operator:

- `parse/order-unrecognised-construct-refused` — `order := none(day)` with a
  `cumulative()` column. Reference: refused (§9.9, no declared order). Mutant:
  `order = "day"`, a real stored column, so the file is **accepted and
  evaluated in an order nobody declared**. This case now kills the mutant.

  §4: *"A reader that cannot recognise a construct MUST refuse it, and MUST NOT
  degrade a failed recognition into a different successful one."* §6 defines
  exactly two states — `order := by(c)` or the line *"omitted entirely"*.
  `none(day)` is neither, so it must be refused; the reference happens to
  refuse it for the secondary reason (§9.9) rather than the primary one, which
  is why `refusal_contains` is left empty rather than encoding a message.

**And a real bug.** `parse/order-none-refused` — `order := none()` in a file
with no row-relative operator. Under §4 this must be refused; the reference
**accepted it** and evaluated the table as unordered, degrading a failed
recognition into a different successful one — the same move that consumed a
data row when an alignment row was unrecognised. **The implementation was at
fault**, and has since been fixed: every unrecognised order construct is now
refused with "order must be by(<column>); omit the line entirely for an
unordered table". This is the third case, and it is here because fixing it is
what makes the mutant's kill honest — before the fix the mutant was only
caught in the with-argument form.

## B. `strip-only-ascii-spaces` — still surviving, because it is not a bug

The mutant trims cell padding with `" "` instead of
`.strip().strip("   ")`. I could not kill it, and I do not
think it should be killed. **The mutant is the more spec-conformant of the
two.**

**What the prose determines.** §8: *"A value that will not coerce to a number
is `#REF!`, not a guess: thousands separators, parenthesised negatives, and
non-ASCII spaces are refused rather than interpreted."* That is a list of three
cell-content patterns a lenient reader would interpret away, and it forbids all
three without carving out padding position — `(500)` and `1,500` would also
coerce if you interpreted the offending character. §9's decision rule settles
any residual doubt about "padding is decoration": *"Reject when degrading could
yield a plausible VALUE; preserve and warn when it could only lose
DECORATION."* And §4 forbids degrading a failed recognition into a different
successful one.

`eval/non-ascii-space-padding-refused` puts U+00A0, U+202F and U+2007 in
padding position in three cells of a numeric column. The reference trimmed all
three and reported **`grand = 253.0`** — a plausible total, indistinguishable
from an honest one. The case expects `#REF!(qty)`, so when written it **FAILED,
while PASSING under the mutant**. The implementation was at fault and has since
been fixed: the three cells now yield `#REF!(qty)`, and a cell holding only
U+00A0 is now `#REF!` rather than silently blank.

**Why this matters more than it looks.** A conforming *writer* never emits
non-ASCII padding: §10's canonical form is single ASCII-space delimiters. So a
U+00A0 or U+202F in padding position only ever arrives by paste from a
locale-aware spreadsheet or a web page — which is precisely the context in
which those two characters are a **thousands separator**, the first item in
§8's own list. `1 500` and ` 500` come from the same paste; the suite
refuses the first (`eval/nbsp-refused`, passing) and silently accepts the
second.

**Consequences for the gate.** Option 1 below is what happened; the entry is
now stale and needs re-aiming rather than restoring.

1. Fix the reference (stop interpreting non-ASCII whitespace before coercion —
   note that bare `.strip()` also removes U+00A0/U+202F/U+2007, so the explicit
   strip could not merely be deleted), then **retire or invert this gate
   entry**. The mutant worth guarding against is the reference's *former*
   behaviour: `non-ascii-padding-is-silently-trimmed` — "cell padding is
   trimmed with Unicode whitespace semantics, so a locale-pasted number loses
   its separator and coerces to a plausible value".
   `eval/non-ascii-space-padding-refused` kills that mutant, which is the
   entry I would write in place of the stale one.
2. The alternative — keep the mutant as written and add the spec sentence that
   makes it wrong — is no longer available, because the fix already chose.

**The spec gap either way.** SPEC.md never says that cell values are trimmed at
all, let alone which characters count as padding. It is inferable only from §10
(*"Padded input is valid and round-trips byte-exactly"*) plus the existing
padded fixtures. After the numeric direction is settled by §8, the trimming
rule remains observable in **text** comparison — predicate literals, `order :=
by(<text column>)`, lookup keys, and row-id identity — and there the spec is
silent. Concretely, under the mutant a row keyed ` r_01` and a row keyed
`r_01` collided and were refused; they are now distinct rows that render
pixel-identically, and §9.5's duplicate-row-id refusal never fires. §3's
clause — *"`Cf` format characters are rejected in identifiers, so that two
visually identical names cannot coexist"* — states the purpose that outcome
violates, but its mechanism (NFC, `Cf`) does not reach whitespace, so I will not
write the case. **Proposed sentence for §4 or §8**, which would close the gap
and make the mutant killable in one stroke:

> Cell values are trimmed of leading and trailing ASCII space and horizontal
> tab, and of nothing else. Any other character, whitespace included, is part
> of the value. Whitespace is also rejected in identifiers, for the reason §3
> rejects `Cf`.

With that sentence, a tab-padded text cell in a `where` predicate kills the
mutant while passing on a conforming reader; without it, no case can.

## C. Other places the gate could be probed (reported, not written)

Not in scope for this pass — say the word and I will add them.

1. **§9's ignorable channel has zero coverage.** No fixture in the tree
   contains a standalone annotation line (*"a line whose first non-space
   character is `#`, outside the table"*). §9 states it is *"preserved verbatim
   by `render` and by `canon`"* and carries an inertness promise, and nothing
   tests any of it. My `parse/comment-after-declaration` tests only §6's
   *inline* trailing comment, which is a different construct. Wanted:
   `roundtrip/annotation-line`, `canon/annotation-preserved`,
   `eval/annotation-is-inert`, and `parse/annotation-line-inside-the-table`
   (§4's *"contiguous run of lines beginning with `|`"* versus §9's *"outside
   the table"* — a `#` line between two data rows must not silently split or
   extend the table). Mutants: `render-drops-annotation-lines`,
   `canon-drops-annotation-lines`, `annotation-inside-the-table-is-skipped`.
2. **`canon` of a CRLF file.** §3 now says line endings are preserved and
   *"only the canonical form (§10) is LF"*. `roundtrip/crlf` covers
   preservation; nothing asserts that `canon` converts. Mutant:
   `canon-preserves-crlf`.
3. **§7's new lookup constraints are untestable in the current fixture
   format.** *"The target is a literal path … resolved relative to the
   referring artifact, and confined to the repository."* `run_cases.py` hands
   only `f["input"]` to `evaluate`, so no case can supply a target file, a
   `../` escape, or an absent row (§8's `#REF!(file[key])`). This needs a
   directory-based entry point before mutants such as
   `lookup-path-resolved-from-cwd`, `lookup-escapes-the-repository` or
   `lookup-missing-row-is-blank` can be written at all.
4. **§4's alignment-row grammar at its edges.** *"the run of hyphens is one or
   more"* — nothing tests the minimal `| - | - |`, nor rejects near-misses like
   `| :: |` or a cell with an interior space. `canon/idempotent-alignment-variants`
   covers the middle of the range only.
5. **The two `equiv` claims are load-bearing and unverified by any case.** Both
   `float-accepts-thousands-separators` and
   `computed-columns-evaluated-in-reverse-header-order` are argued in prose
   about the reference's control flow. An equivalence argument that depends on
   an upstream guard stops holding the moment that guard moves; a case that
   pins the *behaviour* (rather than the argument) would survive the refactor
   that invalidates the prose.

---

# Addendum 2 — the four reported probes

17 cases added: 9 annotation (§9), 4 CRLF (§3), 6 alignment-grammar (§4) —
`parse` 11, `eval` 4, `canon` 3 (counts overlap where one fixture serves two
kinds).

The tree grew from 133 to 164 while this was written: the lookup agent is
landing multi-artifact cases and editing `run_cases.py` concurrently. Of the
failures reported by a full run at the time of writing, **exactly these seven
are mine**; the rest (`parse/lookup-path-escape`, `rowrel/lookup-*`) are that
agent's, in flight, and not addressed here.

**7 failures, and the two sets are disjoint:**

| | reference | alt |
|---|---|---|
| `parse/annotation-containing-a-declaration` | FAIL | pass |
| `eval/annotation-with-declaration-syntax-is-inert` | FAIL | pass |
| `parse/annotation-line-inside-the-table` | FAIL | pass |
| `parse/alignment-empty-cell-refused` | FAIL | pass |
| `parse/crlf-accepted` | pass | FAIL |
| `eval/crlf-evaluates` | pass | FAIL |
| `canon/crlf-preserves-values` | pass | FAIL |

Every one is a place where two independent implementations of the same
sentence produce opposite outcomes on the same bytes. None is a spec defect:
in all seven the prose determines the answer and one implementation did not
follow it. Per-case reasoning is in each case's `WHY.md`.

## 1. §9's ignorable channel (9 cases)

Coverage was zero: no fixture in the tree had ever contained a standalone
annotation line. `parse/comment-after-declaration` tests §6's *inline* trailing
comment, which is a different construct.

Passing on both: `parse/annotation-line` (plain and indented — §9 says *"first
non-space character"*, so indentation is allowed), `roundtrip/annotation-line`
(*"preserved verbatim by `render`"*), `canon/annotation-preserved`
(*"and by `canon`"* — expressed as `already-canonical`, so canon must return
the file byte-for-byte including the indented annotation),
`parse/annotation-before-the-table` (*"outside the table"* includes before it),
`eval/annotation-is-inert` (decoys shaped like a data row and like a function
call), and `eval/hash-in-a-cell-is-not-an-annotation` (the channel is defined
on lines; a line beginning with `|` is not one).

**Failing on the reference — the inertness promise is broken by content.**
`rowspec.table` refuses any annotation line **containing `:=`**, whatever its
first character. `# note with := inside` is refused; `# a plain note` is
accepted. §9's definition is positional and total — *"a line whose first
non-space character is `#`"* — and exempts nothing on the basis of what the
rest of the line resembles. The two most likely things a human ever writes in
an annotation are a note about the declaration below it and an old declaration
commented out rather than deleted; both are refused. `rowspec_alt`, written
from the spec by an author who never read `reference/`, accepts them.
**Reference at fault.**

**Failing on the reference — a `#` line inside the table.** §4: *"The table is
a contiguous run of lines beginning with `|`."* §9: the channel is *"outside
the table"*. So a `#` line between two data rows is not ignorable and ends the
run, leaving `| r_02 | gadget | 5 |` as neither blank nor a declaration →
refused. The reference **accepts** and evaluates both rows, silently extending
the table across a line that does not begin with `|`; the alt refuses. The two
implementations disagree about **how many rows the file has**.
**Reference at fault** — the other reading needs §9's channel to work inside
the table, which §9 denies in the sentence that defines it.

## 2. `canon` of a CRLF file (4 cases) — and a check the runner lacks

`roundtrip/crlf` only exercises `render(structure(x))`. Nothing had ever asked
a CRLF file to **parse** or **evaluate**, and `rowspec_alt` refuses one
outright with *"CRLF line endings; §3 requires LF"* — §3 as it read before it
was amended. A whole implementation was sitting on the retired rule and all 133
cases were green. `parse/crlf-accepted` and `eval/crlf-evaluates` say it out
loud. **Alt at fault, not the spec:** §3 now reads *"LF and CRLF are both
accepted"*, and "accepted" is not "round-trips".

`canon/crlf-idempotent` and `canon/crlf-preserves-values` are the parts of the
conversion claim the runner can express today.

**It cannot express the claim itself.** §3: *"only the *canonical* form (§10)
is LF."* So `canon(crlf_file)` must come back LF-only. Measured right now:

    rowspec.table      canon output retains 3 of 7 CRs  (table lines stripped,
                       blank and declaration lines keep theirs -> MIXED endings)
    rowspec_alt.table  canon output retains all 7

Both are wrong, and no existing `canon` check catches either: `idempotent`
holds on a mixed-ending file, `preserves-values` ignores bytes,
`already-canonical` would demand the opposite, and `removes-padding` inspects
`splitlines()` output, which discards the `\r` before it looks. `run_cases.py`
belongs to the lookup agent this pass, so I did not add one. **One check
closes it** — either

    {"kind": "canon", "check": "canonical-line-endings"}   # assert "\r" not in canon(x)

or, more generally useful, a golden-file form (`expect.mdtbl` alongside
`input.mdtbl`, asserting `canon(input) == expect`) which would also let a case
pin the exact canonical bytes rather than a property of them. I will write the
CRLF case the moment either exists.

## 3. §4's alignment grammar at its edges (6 cases)

*"each cell is one of `---`, `:--`, `--:`, `:-:`, where the run of hyphens is
one or more"*, and *"If the second table line is not a valid alignment row, the
file is refused."*

Accepted, both implementations agree: `parse/alignment-minimal-hyphen`
(`| - | - | - |`, the "one or more" boundary), `parse/alignment-all-four-forms`,
`parse/alignment-long-runs`. Refused, both agree:
`parse/alignment-colon-only-refused` (`::`, no hyphen),
`parse/alignment-interior-space-refused` (`-- -`).

**`parse/alignment-empty-cell-refused` fails on the reference.** An empty cell
is none of the four spellings, so `|  | --- | --: |` must be refused. The
reference accepts it — it skips empty cells when validating the row. That is
the same defect shape as the one that once consumed a data row: an
unrecognised construct degraded into a successful parse instead of a refusal,
against §4's own closing rule. **Reference at fault.**

## 4. The lexical grammar — not yet landed

Checked at the time of writing: `SPEC.md` is unchanged since 17:05 and still
has 13 sections, with no grammar section for numeric literals, date literals,
text collation, identifier character sets, the comment channel, or the
conflict-marker set including `|||||||`. Nothing to read adversarially yet.
Send it when it lands and I will take it the same way.

Two things I would flag pre-emptively, from what the existing cases already
touch, so the grammar author can decide them rather than discover them:

- **`|||||||` is a 7-pipe run, and a data row of six empty cells is also a
  7-pipe run.** `parse/conflict-markers` covers `<<<<<<<`/`=======`/`>>>>>>>`
  only. Whichever way the grammar goes, the boundary needs a case, and the
  format's own delimiter is what makes it delicate: the diff3 marker is
  indistinguishable from a legal empty row in a six-column table by shape
  alone. Position (inside the table run vs anywhere) and the marker's required
  trailing content are the levers.
- **Text collation is currently `str` ordering in both implementations** —
  `rowrel/order-text-column` passes on both, but it only distinguishes ASCII
  lowercase words. Nothing pins case, accents, or NFC-equal-but-distinct
  strings, so `Ápple` vs `apple` vs `Apple` is undetermined and two
  implementations can order the same table differently while both pass.

---

# Addendum 3 — §4.1 read adversarially

27 cases: 10 number-grammar (§4.1.6), 4 date/type (§4.1.7, §6), 2 text order
(§4.1.8), 4 identifier (§9.16/§4.1.9), 2 conflict marker (§4.1.12), 5 lexical
shape (§4.1.2/.3/.5/.10), plus one control. Tree at 191 cases. The assigned
mutant `number-grammar-accepts-anything-python-does` is **killed by 7 of them**;
the gate reads 35 killed / 0 survived / 0 stale.

**11 of the 27 failed when written, in three buckets.** The split is the
interesting part, and it is why the buckets are kept below rather than collapsed
into a list of bugs.

**Status as this was filed.** `rowspec_alt` was rewritten while this was being
written and now passes all 191 cases: every failure in bucket 3, and the alt
half of bucket 1, is closed. `rowspec` still fails **6** — the whole of bucket 2
and the reference half of bucket 1:

    eval/non-number-in-arithmetic-is-ref              (§4.1.6 on the arithmetic path)
    parse/order-date-mixed-separator-within-one-date  (§4.1.7 same-separator rule)
    parse/column-name-with-parens-refused             (§9.16)
    parse/key-value-with-structural-char-refused      (§9.16)
    parse/aggregate-name-with-parens-refused          (§9.16, and §9.12)
    parse/table-line-missing-closing-pipe             (§9.18)

The four §9.16/§9.18 cases were written when **both** implementations failed
them; that they now fail on one is a fact about the last twenty minutes, not
about how well covered the rule was. A normative refusal that no reader
implemented is the finding, and it stands.

## Bucket 1 — fails on BOTH implementations (4 cases)

These are the ones to look at first: a normative rule that neither reader
enforces has no second opinion holding it up.

**§9.16 / §4.1.9, the identifier allowlist — three cases, and the section is
essentially unimplemented.** `parse/column-name-with-parens-refused` (the
section's own example, `total (USD)`), `parse/key-value-with-structural-char-refused`
(`@` in a key value), `parse/aggregate-name-with-parens-refused` (`g(x) :=`,
which is *also* a malformed declaration under §9.12 since `g(x)` is not an
`ident`). I probed all nine structural characters the section enumerates —
`|`, `=`, `:`, `#`, `(`, `)`, `,`, `"`, `@` — in column names, aggregate names
and key values. **Both implementations accept every one of them.** The single
exception is whitespace in a key column value, which the reference alone
refuses. §4.1.9's [CHOICE] argues for an allowlist "so that the answer for a
character nobody has thought of yet is *refused*"; as built it is not even a
denylist.

**§9.18 / §4.1.3, the closing pipe — `parse/table-line-missing-closing-pipe`.**
Both readers accept `| r_01 | widget | 10` with no closing `|`. §4.1.3's
argument for requiring it is the strongest in the section: it "is the only thing
that distinguishes a row truncated inside its final cell from a shorter one, and
the field-count refusal (§9.6) cannot see that truncation because the field
count does not change." A row cut short by a bad merge or a truncated write is
currently read as a complete row with a shorter last value.

## Bucket 2 — fails on the reference only (2 cases)

**`eval/non-number-in-arithmetic-is-ref` — the `number` guard is on one path of
two.** `sum(qty)` over `1e3` correctly yields `#REF!(qty)`; the identical cell
reached through a computed column `t = qty * unit` raises an uncaught
`ValueError`. §4.1.6 says `#REF!` "when used as an **arithmetic** or aggregate
operand", and §9's opening makes a traceback neither of the two defined
outcomes. Same for `١٢`, `+5`, `.5`, `0x10`, `inf` — all 13 spellings I probed
crash on the arithmetic path and are handled correctly on the aggregate path.

**`parse/order-date-mixed-separator-within-one-date`.** The reference accepts
`2024-01/05` as a date; §4.1.7 says "the two separators within one date must be
the same character", so it is text, the column is then date + text, and §6/§9.10
refuse it. The alt refuses it correctly.

## Bucket 3 — fails on the alternative implementation only (5 cases)

Specification signals, in the sense that produced the CRLF finding.

- **`eval/number-leading-plus-refused` and
  `eval/number-one-sided-decimal-point-refused`** — the alt reads `+5` as 5,
  `.5` as 0.5 and `5.` as 5. All three are named refusals in §4.1.6's own
  sentence. The reference gets these right on the aggregate path.
- **`rowrel/order-text-nfc-before-comparison`** — the alt compares the raw
  bytes, so an NFD `Ápple` sorts immediately after `Apple` rather than last;
  measured `lo = 10.0, hi = 110.0` against the spec's `-10.0, 95.0`. §4.1.8
  requires the comparison to run over the "NFC-normalised, trimmed value". The
  amounts in that fixture are chosen so both the minimum and the maximum move;
  a table of positive amounts hides it behind an identical total.
- **`parse/inline-annotation-without-space-refused`** — the alt accepts
  `g := sum(qty)# note`, which is §4.1.10's own counter-example.
- **`parse/all-digit-column-name`** — see the ambiguity below.

## What §4.1 still leaves undetermined

Read as instructed: it is new, and written by an author who could see the
implementation.

1. **The header formula language has no grammar at all.** §4.1 gives ABNF for
   `declaration`, `rhs` and `arg`, and defers `predicate` to §7 — but §7 has no
   grammar either, and neither covers the *header cell* language that every
   computed column is written in: `total = qty * unit`, `net * 1.2`,
   `cumulative(c)`, `sum(amount where region = @region)`. No operator set, no
   precedence, no associativity, no rule for whitespace, no numeric-literal
   alternative, no parenthesisation. §4.1 is titled "The layer the rest of this
   document assumed", and this is the one layer it still assumes. It is also
   where the surviving defects live: `parse/formula-syntax-garbage` and the
   arithmetic-path crash above are both formula-language cases.
2. **All-digit identifiers collide with numeric literals in that missing
   language.** `NUM` is `N*`, so `123` is a well-formed `ident` and a column may
   be named `123`; `arg = ident` with no literal alternative makes `sum(123)`
   unambiguously the column. `parse/all-digit-column-name` asserts that reading
   and the alt refuses it. But in a header formula `x = 123` is ambiguous
   between that column and the literal, and nothing in §4.1 resolves it. Whether
   the fix is to exclude all-digit idents or to define the formula grammar, it
   belongs in §4.1.
3. **String literals have no lexical definition.** §7 writes
   `sum(total where region = "EU")`; `"` is excluded from `ident` precisely
   because it is structural, but no rule says what a string literal is, whether
   it may contain `"`, whether an escape exists (§4.1.3 says none exists for
   cells — is that global?), or whether `'` is an alternative.
4. **§4.1.6's [CHOICE] rationale does not describe the set it justifies.** It
   refuses `+5`, `1e3`, `.5` and `5.` because "each is a second spelling of a
   value that already has one, and a second spelling compares equal as a number
   and unequal as text". `007` and `1.50` satisfy that test exactly and the
   grammar admits both — `eval/number-leading-zeros-accepted` pins that they are
   numbers. They cannot be refused without breaking zero-padded identifiers and
   two-decimal currency columns, so the rule is right and the reason is too
   broad. Worth a sentence, because the next person to extend the grammar will
   apply the reason, not the list.
5. **§9.1 still says "anywhere in the file"** while §4.1.12 defines a conflict
   line by its "first seven characters". `eval/seven-equals-in-a-cell-is-data`
   asserts the §4.1.12 reading — a cell may legitimately hold `=======` — and
   both implementations agree, so this is settled in practice and only the §9.1
   wording lags.

## Cases that now pin previously untested §4.1 claims (15 passing on both)

The digit set (`١٢`, `５`, `५` — the load-bearing one), `1_000`, `1e3`, `0x10`,
`inf`/`nan`/`Infinity`/`NaN` in an aggregate; the accepted forms as a control
against an over-strict fix; `2024-13-45` ordering as written with no calendar
validation; §4.1.7's own worked example (`2026-2-1` before `2026-03-01`, the
running balance the spec says must read 5.0 and not 55.0); code-point rather
than locale text order; `|||||||` as a shape-legal seven-cell empty row inside a
six-column table, which only the classification order rejects; `=======` inside
a cell as data; `\|` not being an escape; an en dash in the alignment row; two
tables in one file.

---

# Addendum 4 — the `\|` escape, read adversarially

13 cases for the reversed §4.1.3, plus one for a contradiction the amendment
introduced. Tree at 191, **0 failures against `rowspec.table`**. `rowspec_alt`
fails 10 of the 13 because it has not been updated for the escape — expected,
and not a signal about the specification this time. The mutant
`render-does-not-escape-pipes` is **killed**; the gate reads 36 killed / 0
survived / 0 stale.

## The cases

Value round-trip and preservation: `rowrel/escaped-pipe-unescapes-to-a-pipe`
(the value is `KS TV | Action`, the real datum),
`eval/escaped-pipe-keeps-the-field-count`, `roundtrip/escaped-pipe`,
`canon/escaped-pipe-preserved`, `rowrel/escaped-pipe-at-end-of-value`,
`rowrel/escaped-pipe-hugging-the-closing-pipe` (no `WSP` between the escape and
the delimiter that closes the cell — a reader that scans for `|` before `\|`
sees four fields in a three-field row).

The half of the retired case that survives: `parse/raw-pipe-in-a-value-refused`.
The reversal made `\|` writable; it did not give a bare `|` a new meaning, and
without this the suite would say nothing about the unescaped form.

The escape versus the identifier allowlist: `parse/pipe-in-a-key-value-refused`
and `parse/pipe-in-a-column-name-refused`. `\|` is well-formed as a *cell* and
the value it produces is ill-formed as an *identifier* (§9.16, §4.1.9). The two
rules meet on the header line of every file.

The escape versus the alignment row:
`parse/escaped-pipe-in-alignment-row-refused` — `-\|-` unescapes to `-|-`, not
one of the four `align-cell` spellings.

Writer side: `mutate/set-cell-with-a-pipe-escapes-on-write`. This is the
semantic form of "a writer escapes every literal `|` it emits", and the form
that matches how the defect reaches a repository: a tool sets a cell to a value
a human typed, `render` writes it, the file is committed. It asserts the
aggregate after the round trip rather than the bytes, because that is the
assertion that fails for the right reason.

## §4.1.3 read adversarially

**1. "A writer escapes every literal `|` it emits" is too broad, and following
it literally breaks a predicate.** The reader half is correctly scoped — "splits
**a table line** on unescaped pipes" — but the writer half is unqualified. A
declaration line is not a table line and is never unescaped, so a predicate
literal must be written **raw** there:

    g := sum(amt where region = "KS TV | Action")      <- declaration: raw
    | t = sum(amt where region = "KS TV \| Action") |  <- header cell: escaped

Both spellings denote the same string, and which one is correct is decided by
which *line* the formula sits on. `eval/predicate-literal-pipe-is-raw-in-a-declaration`
and `rowrel/predicate-literal-pipe-is-escaped-in-a-header` pin both; both pass
on the reference, so this is the behaviour the format has. It is written down
nowhere, and getting it wrong is silent — the escaped spelling in a declaration
matches zero rows and reports `0`, with no diagnostic. Suggested repair: add
"in a table line" to the writer sentence, and one clause noting the predicate
consequence.

**2. The ABNF for `cell` is ambiguous, and the prose is what disambiguates it.**

    cell    = *( escaped / ( char - "|" ) )
    escaped = "\" "|"

`char - "|"` includes `\`, so the string `\|` has two valid parses: one
`escaped` element, or a `char` element `\` after which the cell ends and the `|`
is a delimiter. The two give different field counts — precisely the harm rule 3
itself warns about ("an unrecognised escape makes a file whose field count
differs between readers"). Only the prose ("splits on **unescaped** pipes")
picks a winner. §4.1 has already set the precedent for fixing this: it declares
"**Classification order is normative**" for the alternatives of `line`. The same
one-line commitment for the alternatives of `cell` closes it.

**3. A backslash that is not escaping a pipe is undefined — reported, not
invented.** Both implementations already agree it is literal: `C:\path` stays
`C:\path`, `a\\b` stays `a\\b`, and a value ending in `\` survives because
canonical form always pads (`| a\ |` trims to `a\`). One sentence would settle
it — "a `\` not followed by `|` is an ordinary character" — and the agreement
between two independent readers suggests that is the intended rule rather than a
choice still to be made. Two consequences worth stating alongside it:

- The literal two-character sequence `\|` and an escaped pipe are the same
  bytes, so a value containing a backslash immediately before a pipe collapses
  onto a value containing a pipe. Nothing is lost today because the escape is
  the only thing a backslash can do, but it is a one-way door: any second escape
  ever added makes previously-written files change meaning.
- In *unpadded* input a value ending in `\` immediately before the closing
  delimiter (`|a\|`) is indistinguishable from an escaped pipe and is therefore
  unwritable. Canon always pads, so this bites only hand-written files, but a
  reader still needs a defined answer.

**4. §4.1.10's `#` reasoning survives the reversal — I checked, and it holds.**
The amended clause reads "there is only one escape and it is for the pipe (rule
3)". The argument was and remains: no escape covers `#`, so an inline comment
channel inside the table would make `#ff8800` unwritable. That is still true,
and the reversal arguably strengthens it — the format has now demonstrated it
will add an escape when data demands one, and did not add one for `#`. The
fragility is that the sentence's premise is now a *scoping* fact rather than an
absolute one: if a later amendment generalises the escape to `\#`, this
paragraph becomes false silently, because nothing links them. A cross-reference
in both directions would cost a clause.

## The drift you predicted, found in the amendment that fixed the last drift

**§4.1 rule 9 and rule 9a contradict each other about `-` and `.`, in adjacent
paragraphs.**

- Rule 9: "`-` and `.` were admitted by an earlier draft and **are not**: the
  formula language uses `-` as subtraction, so a column named `a-b` would be
  well-formed and permanently unreferenceable."
- Rule 9a ("Identifiers, continued"): "... are `ident`: one or more Unicode
  letters, marks or digits, `_`, **`-`, `.`**."
- The ABNF: `ident = 1*( LETTER / MARK / NUM / "_" )` — siding with rule 9.

Rule 9a looks like the pre-amendment text left behind when rule 9 was inserted
rather than replacing it; its heading is a form used nowhere else in §4.1.
**The two implementations are split exactly along the contradiction**:
`rowspec.table` refuses `a-b` as a column name, `a.b`, a key value `r-01` and an
aggregate named `a-b`; `rowspec_alt.table` accepts all four. Neither is wrong
against the document as it stands, which is the problem — and it is the same
failure mode as the ABNF/implementation drift the dogfood run caught, three
paragraphs away from it.

`parse/column-name-with-hyphen-refused` asserts the ABNF's reading, two
statements out of three and the one labelled normative. If rule 9a is the
intended rule instead, retire the case with a note and restore `-` and `.` to
the ABNF. One of the three must go either way.

## Gate observation: the writer-side escape has one covering case, not three

`render-does-not-escape-pipes` is killed by exactly one case —
`canon/escaped-pipe-preserved`. Neither `roundtrip/escaped-pipe` nor
`mutate/set-cell-with-a-pipe-escapes-on-write` detects it, because `render`
replays unmodified rows from their stored raw lines, so the serialiser the
mutant patches is only reached through `canon`. The escape-on-write guarantee
therefore has three cases and one covered code path.

Proposed companion mutant: **`set-cell-does-not-escape-pipes`** — the write path
that re-serialises a *modified* row omits the escape, so a tool that sets a cell
to a value a human typed emits a row with an extra delimiter. That is the path a
real editor takes, it is a different function from the one `canon` uses, and
`mutate/set-cell-with-a-pipe-escapes-on-write` already in the tree kills it on
the day it is added. A second, cheaper one: **`unescape-applied-to-declaration-lines`**
— unescaping run over every line rather than table lines only, which silently
turns a raw predicate literal into a non-matching one;
`eval/predicate-literal-pipe-is-raw-in-a-declaration` kills it.

## Unrelated, noted in passing

`count` over a *text* column returns `#REF!` on the reference (`count(name)`
where `name` holds `plain`, `z`). That follows from §4.1.6 read strictly — a
non-coercible aggregate operand is `#REF!` — but it means `count` can never
count a text column, which is a surprising thing for a counting function and is
not stated anywhere. Flagging rather than filing: I could not tell from the
prose whether it is intended, and `count`'s own definition in §7 is one word.

The lookup cases are absent from the tree as of this writing (0 under `parse/`
and `rowrel/`); that agent appears to be mid-refactor and it is not mine.

---

# Addendum 5 — adjudicating the `count` carve-out

**I agree with the change, and I think the argument is stronger than the one
you made for it.** `eval/ref-poisons-every-aggregate`'s `n` expectation is
changed from `#REF!(amt)` to `3`, with the reasoning recorded in that case's
`WHY.md` so the next reader finds it at the fixture rather than here. Three
cases added to pin the boundary the carve-out creates. Tree at 194,
**0 failures against `rowspec.table`**; gate at 38 killed / 0 survived / 0 stale.

## Why I agree

**The suite had already settled it, and the preamble says the suite wins.**
This is the argument I would lead with, and it was sitting in the tree the whole
time. `eval/count-includes-blanks` asserts `count = 2` over a column with a
blank cell. A blank is exactly a value that cannot serve as a numeric operand —
§8 says so in the same paragraph, "A blank cell is not zero" — and `count`
counts it anyway. `count` was therefore already a row-counter that does not
inspect values. Poisoning on `1,000` while not poisoning on a blank is
incoherent; both are "not a number". Your change makes those two agree. The old
behaviour did not, and nobody noticed because **nothing in the suite ever
counted a non-numeric column** — see the audit below.

**§4.1.6 already scoped it.** "Refused, and therefore text — `#REF!` **when used
as an arithmetic or aggregate operand** (§8)." The value is text and becomes
`#REF!` at the point of use. `count` never uses it. I read that clause
adversarially two passes ago and endorsed it; the poisoning reading requires
ignoring it.

**§8 is preserved, not weakened.** A `#REF!` genuinely in the column still
poisons `count`. The change is to *what counts as containing a `#REF!`* — an
error value, not any text that fails to parse — and that is a distinction the
implementation draws correctly today.

## Why the counter-argument loses

It is a real argument and I tested it rather than waving it off. A column the
author intended as numeric, holding one badly-pasted `1,000`, is a defect, and
loud failure is this format's instinct.

It loses on two counts. First, **the defect is already reported four times** —
`sum`, `min`, `max` and `avg` all return `#REF!(amt)` for that column, and all
four are asserted in the same file. A fifth report carries no information a
reader can act on. Second, and decisively, **the poisoning reading returns an
error for `count` on every text column in the format**, including ones where
nothing is wrong. §9 already rejects that in principle: "Refusing is not the
same as being strict for its own sake. A policy that refuses everything unknown
was measured to reject 6 of 12 files that had a correct answer."

The sharpest form of it: `sum`, `min`, `max` and `avg` are **type-committed** —
applying one *declares* numeric intent, so poisoning detects a violated intent.
`count` is type-agnostic. Poisoning `count` detects nothing; it only refuses to
count. Your instinct ("loud in the wrong place") was right, and this is why.

## What I checked before agreeing

Not the prose — the boundary, on both implementations:

| | reference | alt |
|---|---|---|
| column holds a real `#REF!` (computed col) | `#REF!` ✓ | `#REF!` |
| column holds unparseable text `1,000` | `3` ✓ | `#REF!` (not yet updated) |
| plainly textual column | `2` ✓ | `#REF!` (not yet updated) |
| missing column name | `#REF!(nope)` ✓ | `#REF!(nope)` |
| blanks | `2` ✓ | `2` |

The rule is implemented as specified, and the distinction is genuinely drawn
rather than collapsing into "count never poisons". That is what made me
comfortable; had the first row returned `3`, I would have argued the other way,
because then §8 would have been silently deleted rather than scoped.

## The audit you asked for

Every `count(` in the tree, checked against the column it counts: **exactly one
case depended on `count` coercing** — the one you identified. Every other
asserted `count` is over a numeric column with no unparseable values, where the
row count and the coercing count agree. Four more (`parse/self-referential-column`,
`parse/mutually-recursive-columns`, `parse/group-aggregate-syntax`,
`parse/no-data-rows`) evaluate a `count` but assert only acceptance.

The real finding of the audit is the other direction: **both sides of the new
boundary were untested.** Nothing counted a text column, and nothing counted a
column containing a genuine `#REF!`. The carve-out could have drifted into
"count never poisons" — deleting §8 for one aggregate — and the suite would have
stayed green. Now closed by:

- `eval/count-poisoned-by-a-ref-in-the-column` — a computed column whose cells
  evaluate to `#REF!(amt)`; `count` must be `#REF!`. This is the far edge, and
  it is deliberately the same offending value (`1,000`) in the same shape of
  file as `eval/ref-poisons-every-aggregate`, differing only in whether the
  error value reaches the counted column. Two cases, one bad cell, opposite
  answers, and the difference is the whole rule.
- `eval/count-over-a-text-column` — the positive form of the sentence, and the
  thing the carve-out buys.
- `eval/count-over-a-missing-column-is-ref` — a broken *name* still poisons
  `count`, which is a different failure from a broken *value* and one that "just
  return the row count" gets wrong. `eval/missing-agg-col` asserted this for
  `sum` only. It also now co-kills `missing-agg-col-crashes`.

## Two mutants the gate still lacks

`count-off-by-one` and `count-ignores-blanks` are the only `count` mutants, and
neither touches the new rule. Both drift directions now have cases and want a
mutant each:

- **`count-poisons-on-unparseable-text`** — the reverted behaviour: `count`
  returns `#REF!` when any cell fails to parse as a number. Dies to
  `eval/ref-poisons-every-aggregate` and `eval/count-over-a-text-column`.
- **`count-never-poisons`** — `count` returns the row count unconditionally,
  ignoring a `#REF!` actually present in the column. Dies to
  `eval/count-poisoned-by-a-ref-in-the-column` and
  `eval/count-over-a-missing-column-is-ref`.

Both kill immediately with cases already in the tree, so they cost nothing but
the entry, and together they pin the carve-out from both sides — which is what a
rule that was just moved needs most.

## Note

`rowspec_alt` has not been updated for the `count` rule and fails
`eval/count-over-a-text-column` and `eval/ref-poisons-every-aggregate`, on top
of the ten escape cases. Expected, and not a signal about the specification.

---

# Addendum 6 — pass ordering, and §4.2 read adversarially

32 cases. Tree at 226. `plain-pass-runs-only-once` is **killed** (by the three
BOM-shaped cases); gate at 41 killed / 0 survived / 0 stale.

**3 cases fail against `rowspec.table`, all three found by reading §4.2 rather
than by the assigned defects** — the assigned four are all fixed and now pinned.

## The assigned four

**1. The bill of materials.** `eval/group-aggregate-over-a-computed-column` and
`rowrel/group-aggregate-over-a-computed-column` carry the trial's own data and
its true subtotals — 17.75 / 4.87 / 7.00, against the `0` it reported. §4.2 rule
5 is explicit that the shape is legal: "The aggregated column itself carries no
such restriction: `sum(total where region = @region)` over a computed `total` is
well-formed and rule 9 gives it a value." All five aggregates are asserted
together deliberately: in the failure only `sum` returned a plausible number,
and the loudness of `min`/`max`/`avg` is the only reason anyone could tell.
`eval/group-aggregate-declared-before-its-input` is the same table with the
aggregate written to the *left* of the column it reads.

**2. Row-relative composition.** `eval/` and `rowrel/column-depending-on-a-row-relative-column`
are §4.2 rule 3's own sanctioned example (`| run = cumulative(a) | twice = run * 2 |`).
`eval/column-depending-on-a-group-aggregate` is the group-side twin — an
ordinary formula whose operand is a group aggregate, which is the other half of
what the second plain pass is for. The two composition refusals
(`parse/rowrel-call-inside-an-expression-refused`,
`parse/group-call-inside-an-expression-refused`) pin the rule whose violation
produced the blank cells: rule 3 states the measurement in the spec itself, and
the fixture is that measurement.

**3. Order independence.** `eval/header-order-dependency-first` and
`-last` are rule 9's worked example, same data, computed columns in opposite
order, identical expectations. Neither case tests anything alone; the pair is
the test, which is why they are not folded into one file.

**4. Cycles.** Four cases: self, mutual, a column *depending* on a cycle (rule
9's "directly or transitively"), and one through a group aggregate.
`parse/self-referential-column` and `parse/mutually-recursive-columns` already
asserted that these files are accepted and terminate; nothing asserted the
*value*, which is why the spelling was free to drift.

## The three failures, all reference-side

**`eval/cycle-through-a-group-aggregate` — the cycle shape is lost when the
cycle crosses the group pass.** §4.2 rule 9 requires `#REF!(cycle)`; both
implementations return `#REF!(t)`. Plain cycles are handled correctly by the
reference (`b = b + a` → `#REF!(cycle)`), so this is specific to a cycle routed
through a group aggregate — the pass whose ordering just changed. §8 makes the
spelling load-bearing rather than cosmetic: "There are exactly three `#REF!`
shapes, and an implementation emits no fourth", and `#REF!(name)` is reserved
for "the column that could not be resolved or whose value would not coerce". A
reader cannot tell `#REF!(t)`-the-cycle from a broken reference to a column
actually named `t`.

**`eval/ref-carries-the-originating-name` — one of the things you asked me to
check, and it is broken.** §8: "`#REF!(name)` carries the *originating* name …
**not the column the error surfaces in**." Over `a` (holding `1,000`) →
`b = a * 2` → `c = b * 2`, the reference gives `sum(b)` = `#REF!(a)` and
`sum(c)` = `#REF!(b)`. It relabels at the second hop. `rowspec_alt` returns
`#REF!(a)` for both. One hop was already covered by two existing fixtures, which
is exactly why this survived: the relabelling is invisible until a third column
exists. The cost is the diagnostic the rule was written for — a reader who sees
`#REF!(b)` inspects `b`, finds a well-formed formula, and never reaches the cell
that is actually wrong.

**`parse/at-ref-on-a-declaration-line-refused` — the spec's verbatim example is
still accepted.** §4.2 rule 5: "`g := sum(amt where r = @s)` is a malformed
declaration (§9.12)", and the rule names the offender: "Any reading an
implementation invents — **and the reference implementation invents one,
comparing each candidate row against itself** — makes the predicate a filter the
author did not write." The reference still accepts the file and returns `5.0`,
which is that invented reading. §4.2 documents the bug in the present tense; the
implementation has not caught up. (The mirror case,
`parse/at-ref-in-arithmetic-refused`, the reference gets right and `rowspec_alt`
gets wrong — each implementation enforces one half of rule 5.)

## §4.2 adversarially: one real gap

**Rule 5's stored-column constraint is a MUST with no defined outcome, and §9
claims to be complete.**

> "**Both `ident`s of an equality — the left-hand one and the one after `@` —
> must name a stored column**, never a computed one."

§9's preamble: "This list is complete. Every refusal the format has is below; a
refusal argued elsewhere in this document appears here too, with a
back-reference." There is no entry for this one. §9.20 does not reach it either:
that entry is scoped to a right-hand side "not generated by §4.2's `formula`",
and this constraint is semantic — the grammar cannot tell a stored column from a
computed one.

So the document says MUST, and its complete list of refusals does not contain
it. The two implementations split accordingly, and the reference's answer is the
bad one:

| `t = sum(a where k = @g)`, `k` computed | |
|---|---|
| `rowspec.table` | `0.0` |
| `rowspec_alt.table` | `#REF!(g)` |

`0.0` is the BOM failure mode exactly — a plausible zero from a predicate that
matched nothing because a computed column has no cell text to compare. I have
**not** written a case, because choosing between "refuse" and "`#REF!`" is
inventing the rule rather than testing it, and §8's "never evaluates to zero"
does not settle it: sum over an empty match set is legitimately `0`, and the
empty match set is the symptom, not the error. Say which and I will write it in
one pass. My recommendation is refusal with a §9 entry, on the same reasoning
rule 5 already gives — the only available reading compares against a rendered
number, and §2 leaves number formatting to the implementation, so a value-shaped
answer here is unstable across readers in a way a refusal is not.

## §4.2 adversarially: one consequence reached by silence

**A whole-column aggregate repeated on every row is not expressible as a
computed column.** `group-call` makes the `where` clause mandatory, and `sum(a)`
is not an `expr` either, so `| x = sum(a) |` is refused under "Recognition is
whole-cell". That may well be intended — the per-row form is a column of one
repeated number, and `s := sum(a)` says it better — but it is a capability
decision arrived at by grammar rather than by a **[CHOICE]**, and it is the only
one in §4.2 that is not argued. `parse/group-call-without-a-where-refused` pins
the grammar's answer and its `WHY.md` records the observation.

Everything else in §4.2 checked out, and the checks are now cases: operator
precedence and left-associativity including unary `-` and parentheses (rule 1);
real division and `#REF!(/0)` (rule 2); the four refused operators (rule 1's
`[CHOICE]`, one case each, because "the rule is that `expr` is exactly what the
ABNF generates" makes them samples of a closed grammar rather than a denylist);
function names not being reserved words, with `sum` used as a column name and as
a function in the same file, and the no-space-before-`(` rule (rule 4); text-not-numeric
equality with the spec's own `3` versus `3.0` (rule 6); the bare numeric token in
both positions **with a column named `123` actually present**, which is the only
arrangement that distinguishes rule 7 from the alternative it rejects, plus
`sum(1)` = `#REF!(1)`; and `#` inside a formula (rule 8) — that last one guards
a defect reintroduced by an ordinary refactor, swapping a hand-written parser
for the host language's, which nothing else in the tree would notice.

## Your two fixes

`#REF!` shapes: correct except for the originating-name relabelling above — the
three shapes are otherwise emitted as §8 specifies, and
`eval/division-by-zero-is-ref-slash-zero` pins `#REF!(/0)` against
`rowspec_alt`'s `#REF!(division by zero)`, which is both a fourth shape and one
whose contents are prose rather than a name.

Unsupported operators: fixed and now pinned by four cases. The reference refuses
all four with messages citing §4.2.

## `rowspec_alt`

25 failures, and I agree they are staleness rather than specification signal —
10 escape cases, the `count` carve-out, `-`/`.` in identifiers, and then a
cluster that is genuinely §4.2 non-conformance rather than drift: it accepts
`cumulative(a) * 2` and `sum(...) + 1` (rule 3), accepts `@` in arithmetic (rule
5), accepts `sum (a where …)` with a space and `sum(a)` without a `where` (rule
4 and the grammar), compares predicates numerically (rule 6), and emits the name
shape for cycles and a fourth shape for division by zero (§8). Those nine are
worth passing to whoever owns it as a list rather than as a diff.

---

# Addendum 7 — the new parser, and a harness that passes broken cases

31 cases added, one retired. Tree at 256, **0 failures against `rowspec.table`**,
40 against `rowspec_alt`. Gate re-run: **41 killed / 0 survived / 0 stale**.

## (a) NFKC — `eval/` and `rowrel/nfkc-is-not-nfc-for-identifiers`

§3 says NFC; `ast.parse` folded NFKC. `Nº` (U+00BA) and `No` are two identifiers
under NFC and one under NFKC. Both assertions live in one case on purpose, as
you asked: `sum(Nº)` alone passed with the bug (the aggregate path never went
through Python's identifier normalisation), and `sum(out)` alone passes against
a reader that folds *everything* consistently. Only the pair pins that the
formula and the aggregate resolve one name to one column.

`eval/nfkc-compatibility-forms-stay-distinct` covers the other four classes a
real corpus produces — ligature `ﬁ`/`fi`, superscript `²`/`2`, fullwidth `Ａ`/`A`,
Roman numeral `Ⅻ`/`XII` — each NFC-distinct and NFKC-identical, so each is a
duplicate column name (§9.2) under folding. Expectations are powers of ten apart
so a fold in any one pair shows up in exactly one aggregate. I dropped the micro
sign from the set: U+00B5 NFKC-folds to Greek mu, not to `u`, so `µm`/`um` never
collide and the test would have been vacuous.

`rowspec_alt` passes all of these and always did — it never used a host parser
for identifiers, which is what makes it the useful witness here.

## (b) Maximal munch — five cases

`1000_2999` (amount band), `10_15` (time of day), `31_03_2021` (date-shaped),
each paired the same way; plus the same token in a **predicate** and in a
**declaration argument**, which are name positions and were the half that stayed
correct under PEP 515 while the formula went wrong; plus
`eval/maximal-munch-absent-name-is-a-broken-reference`, where no such column
exists and the answer is `#REF!(1_0)` rather than the number 10.

`rowspec_alt` fails all five: it lexes `1000` as a literal and reports "trailing
tokens". §4.2's maximal-munch paragraph is unambiguous and post-dates that
implementation, so this is conformance debt rather than a specification signal.

## (c) `1e3` and `0x10` — four cases

`#REF!(1e3)` and `#REF!(0x10)` from arithmetic, `#REF!(1e3)` from a declaration
aggregate, and — the over-correction guard you flagged —
`eval/exponent-named-column-resolves`, where a column **named** `1e3` exists and
`1e3 * 2` is 10.0. An implementation that refuses the name rather than reporting
a broken reference cannot represent that table at all. `rowspec_alt` refuses all
four.

## (d) Breaking the parser — two real finds, both now fixed

**Stacked unary minus.** `factor = [ "-" *WSP ] primary` is zero-or-one, and
`-a` is not a `primary`, so `--a` and `- -a` are not generated. Both
implementations accepted them as double negation. Now refused, with the case
passing unmodified. Its control,
`eval/unary-minus-after-binary-minus`, pins `a - -b`, `a * -b` and `a / -b`,
which **are** generated and which the obvious over-correction (refuse any `-`
following an operator) would break.

**Nesting depth.** Both implementations raised `RecursionError` — neither of
§9's outcomes — at a depth that differed between them because it was the host
call stack. Resolved as §9.23 with a number, which is the better of the two
closures the case offered, for the reason you gave: surviving 250 levels moves
the boundary from stack to heap and leaves it equally unspecified. The old case
is retired with its record; the replacement is a **pair**,
`parse/nesting-depth-64-accepted` and `-65-refused`, because a single refusal
case pins "deep is refused" and would keep passing at a limit of 8 or 4096.

Everything else I threw at the new parser agreed with `rowspec_alt` and with the
ABNF, and is now cases: `+a` refused (no unary `+` in the grammar — `rowspec_alt`
accepts it), `a(b)` refused as an unknown function, `1.5.2` refused, nested
parens, a horizontal tab as interior whitespace, and
`eval/leading-zero-literal-versus-a-column-named-007` — `007 * 2` is 14 while
`sum(007)` is 50, one token with two meanings decided by position, in a file
where the colliding column actually exists.

Two further probes I did **not** turn into cases:

- **A pure-`MARK` identifier.** `ident = 1*( LETTER / MARK / NUM / "_" )` has no
  start/continue distinction, so a name consisting only of a combining acute is
  well-formed by the ABNF. Both implementations refuse it. I think the
  implementations are right and the ABNF is wrong: a leading combining mark
  renders as a modification of whatever precedes it — in a header, the `|` or
  the padding space — which is precisely the visual-confusion hazard §3's `Cf`
  clause exists to prevent ("so that two visually identical names cannot
  coexist"). Writing the case in the ABNF's direction would pin behaviour I
  believe is unintended, so this is a report: `ident` wants a start/continue
  split, or a sentence excluding a leading `MARK`.
- **`a(b)` diagnostics.** Both refuse; `rowspec_alt`'s "unknown aggregate
  function" is the reading §4.2 rule 4 actually describes, the reference calls
  it trailing input. §9 makes the choice of diagnostic unspecified, so the case
  asserts only the refusal — noted in case rule 4's wording is meant to bind.

## §9.22 and the new rule 2

`parse/predicate-lhs-names-a-computed-column-refused` and
`parse/predicate-at-ref-names-a-computed-column-refused` go in, both sides of
the equality, with `eval/predicate-idents-both-stored` as the control against an
over-correction that refuses predicates naming columns a pass has not resolved
yet. **Your §9.22 wording and my cases agree**, including the part I would have
got wrong on my own: the entry explains why §9.20 cannot reach it, which is the
distinction between a grammar constraint and a semantic one that I had to work
out by probing.

Overflow: `eval/overflow-is-ref-overflow` and `-negative-`, using two 1e200
values written as plain digits because `1e200` is an `ident` and not a number.
`rowspec_alt` returns `inf` and `-inf` — the outcome rule 2 forbids, and worse
than loud, since `canon` would then write a cell no reader including its own can
read back.

Binary64: `eval/binary64-decimal-fraction` (`0.1 + 0.2` = 0.30000000000000004,
where a decimal reader returns exactly 0.3) and
`eval/binary64-round-to-nearest-even` (`9007199254740992 + 1` is unchanged,
where a decimal reader returns 9007199254740993). Both operands are plain digits
so nothing depends on number spelling, only on the arithmetic. Both
implementations already agree.

## Mutants for (a), (b), and the nesting limit

- **`identifier-folding-is-nfkc`** — identifiers compared after NFKC instead of
  NFC, so `Nº` and `No` become one column. Dies to
  `eval/nfkc-is-not-nfc-for-identifiers` (both assertions) and to
  `eval/nfkc-compatibility-forms-stay-distinct`.
- **`literal-lexed-before-ident`** — the tokeniser tries `literal` before
  `ident` instead of munching `ident` maximally, so `1000_2999` lexes as `1000`
  followed by `_2999`. Dies to all five munch cases and to the three `1e3`/`0x10`
  cases, which is the coverage worth having: the defect has one cause and six
  surface shapes.
- **`digit-separators-in-literals`** — the narrower PEP 515 form: `_` accepted
  *inside* a literal so `1000_2999` is the number 10002999 while `sum(1000_2999)`
  still finds the column. Dies to the same cases, but it is the one that actually
  happened, and it survives a fix that only reorders the two lexer alternatives.
- **`nesting-limit-raised`** — `MAX_NESTING` set to 4096 (or removed). Dies to
  `parse/nesting-depth-65-refused` and to nothing else in the tree.
- **`nesting-limit-off-by-one`** — the limit applied as `>= 64` rather than
  `> 64`. Dies only to `parse/nesting-depth-64-accepted`, which is the argument
  for the pair.

## The harness — three more ways it reports success without measuring

You fixed the empty tree. The same class is still open in three places, and I
have evidence rather than an argument. Three deliberately broken `expect.json`
files in a temp tree — an unknown `kind`, an empty `aggregates`, and a typo'd
canon `check` — **all three reported PASS**:

1. **`kind` is never validated.** The dispatch is `if k == "parse" … elif k ==
   "confluence"` with **no `else`**. A case whose kind is `"evaluate"`,
   `"parses"` or `"canonical"` matches no branch, raises nothing, and counts as
   passing. This is the likeliest one to bite — the tree now has 256 hand-written
   `expect.json` files and nothing checks the one field that decides whether
   anything runs at all.
2. **`canon`'s `check` is never validated**, same shape: an `if/elif` chain with
   no `else`, so `"idempotant"` runs nothing. Note also that the idempotence test
   is a substring match, `"idempotent" in e["check"]`, so a check named
   `"not-idempotent"` would run it.
3. **An empty `aggregates` dict asserts nothing.** `eval` and `merge`+`evaluate`
   both loop over `e["aggregates"]`, so `{}` is a case that runs the evaluator
   and checks no value. (A *misspelled* key raises `KeyError` and is caught, so
   only the empty-dict form is silent.)

Two more, from reading rather than from a reproduction:

4. **A missing or broken `git` turns every merge case into a pass-shaped
   result.** `git_merge` never checks the return code of `git init`, the two
   `git config` calls, `git add`, or `git commit`. If git is absent, every `sh()`
   fails quietly, the final `git merge` also fails, and the function returns
   `"conflict"` — so every case expecting `git_outcome: "conflict"` passes and
   the rest fail with a confusing diff. §14 says a conforming implementation runs
   these "against a **stock git binary**"; the harness should assert git is
   present and that the setup commands succeeded, so its absence is one loud
   error rather than a mixed result.
5. **`mutate` without an `aggregate` asserts only `str(value) in out`** — a
   substring test over the whole rendered file. Setting a cell to `10` in a table
   that already contains `10` anywhere passes without the mutation having
   happened.

The general fix for 1–3 is one line each: an `else: bad(f"unknown kind {k!r}")`,
an `else: bad(f"unknown check …")`, and a check that `aggregates` is non-empty.
They are worth having because they fail *closed*: the current design means a
typo in a fixture silently reduces the suite's size, which is the same defect as
the empty tree and harder to notice, because the case count does not change.
