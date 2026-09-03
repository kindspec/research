# M2 — independent implementation of rowspec from SPEC.md alone

**What was done.** A second, clean-room implementation of rowspec in Python
(stdlib only) at `rowspec/reference/rowspec_alt/table.py` (~980 lines),
exposing `parse`, `structure`, `evaluate`, `render`, `canon`, `set_cell`,
`Malformed`.

**Isolation.** I read only `rowspec/SPEC.md`, `conformance/cases/`, and
`conformance/run_cases.py`. I did **not** open `reference/rowspec/`,
`design-findings/`, `experiments/`, `DESIGN.md`, `PLAN.md`, `RESEARCH.md`, or
`conformance/mutants.py`. No contamination to report.

**Result: 129 / 131 fixture cases pass.** The two failures
(`parse/crlf-refused`, `parse/lone-cr-refused`) are unpassable by *any*
implementation — see §3.1. Nothing was committed or installed.

**A note on timing that is itself a finding.** The fixture tree grew from 57 to
114 to 131 cases while I worked. My first implementation, written from SPEC.md
alone, passed **57/57** of the original tree — and then failed **9** of the
newly-added cases. Every one of those 9 failures was a place where I had
guessed, the prose did not say, and the new fixture said I had guessed wrong.
That is the cleanest available evidence for the verdict in §6: *passing the
suite is not evidence the prose is sufficient; it is evidence the suite is
small.*

The seven behaviours I had to guess and got **wrong** on the spec-only pass:

| # | I inferred | Fixture says |
|---|---|---|
| 1 | `@c` is numerically coerced like any reference (§8) | `@c` is compared raw, so text columns can be grouped on |
| 2 | `count()` counts rows, unaffected by a text cell | an uncoercible cell poisons `count` too |
| 3 | a value in a computed cell is ignored | it is a hard refusal |
| 4 | whitespace after the closing `\|` is part of the last field | it is decoration `canon` must drop and `render` must restore |
| 5 | `lookup()` is unimplementable, so refuse it | it must parse, be accepted, and evaluate |
| 6 | `inf`/`nan` in the order column fall out of the mixed-type rule | they need their own refusal |
| 7 | a BOM is not my problem | it is a refusal |

---

## 1. Ambiguities — ranked by how likely two implementations are to differ

**1. `@c` in a group predicate is not numerically coerced — but §8 says it is.**
§7: *"`@c` means *this row's* value of `c`"*, with the example
`sum(amount where region = @region)`. §8: *"A value that will not coerce to a
number is `#REF!`, not a guess"*. Read together, `@region` over a text column
is `#REF!` and the format's own SUMIF example can never work. I implemented
§8 literally, passed the then-current suite, and was later contradicted by
`eval/group-aggregate-at-ref`. **Two implementations will differ here** and the
disagreement is silent: one returns a group subtotal, the other `#REF!`.

**2. Which row's `@` binding a predicate uses.** §7 never states that the
predicate is evaluated against the *current* row while the column is scanned
over *candidate* rows. Binding both to the same row (the obvious first
implementation, and my first one) makes every predicate trivially true and
turns every group aggregate into a grand total — a *plausible number*, never an
error. This is the single most dangerous ambiguity in the document.

**3. Does an uncoercible cell poison `count`?** §8 says *"An aggregate over any
column containing a `#REF!` is itself `#REF!`"* — but a cell holding `1,000` is
not yet a `#REF!`; it becomes one only when something coerces it. `count` need
not coerce. `eval/ref-poisons-every-aggregate` settles it (it does), but only
the fixture does. Divergence yields `3` versus `#REF!(amt)`.

**4. `min`/`max`/`avg` over a column containing blanks.** §8 says *"A blank
cell is not zero"*; §7 lists the functions and says nothing more. Skip blanks,
or treat them as `#REF!`? I skip. **No fixture distinguishes zero-filling from
skipping for any aggregate** — including `eval/sum-skips-blanks`, whose name
promises exactly that test but whose data (`[5, blank]`) yields `5.0` either
way. Verified: mutating my `sum`/`min`/`max` to treat blank as `0.0` still
passes 129/131.

**5. `avg`'s denominator.** Non-blank cells, or all rows? Unstated; unfixtured
(`eval/avg-basic` has no blanks). Verified: both mutants pass.

**6. What `prior`/`delta` yield on the first row.** The fixtures demand `""`.
§8 says *"A broken reference never evaluates to zero, empty, or a stale
value"* and *"A blank cell is not zero"* — the prose points away from the
required answer, and §7's one-line descriptions ("that column's value in the
preceding row") say nothing about there not being one.

**7. The order of the `rows` list `evaluate` returns.** File order or derived
order? The runner indexes `rows[row_index]` in `rowrel` cases, so it matters —
but every `rowrel` fixture uses a file whose file order *is* its derived order.
Verified: both choices pass 131/131. `§6` insists position is never an input to
computation, which is an argument for derived order; the parameter is called
`row_index`, which is an argument for file order. I chose file order.

**8. Division by zero.** Arithmetic is "over column names" with no division
semantics given. `#REF!`, `inf`, or a refusal? I return `#REF!`. Unfixtured;
verified that returning `0.0` also passes.

**9. Must `key := c` name an existing, stored column?** Not in §9's list.
I refuse; unfixtured; verified that accepting also passes. A `key` naming a
missing column makes refusal 9.5 (duplicate row id) unenforceable, which is a
correctness hole, so implementations *will* differ on a file that is
meaningfully broken.

**10. What counts as an alignment-style cell.** §10 shows `---` and `--:`;
`canon/idempotent-alignment-variants` also requires `:---`, `:-:`, `-:`. Is a
single `-` an alignment cell? Is an empty cell? The rule that decides
refusal 9.8 (`| --- | --- |` among data rows) versus `dashed-value-is-data`
(one cell of `---` is data) is never stated: I inferred *all* cells must match
`:?-+:?`. An implementer who required a *minimum of three* dashes, or *any*
cell matching, gets a different file classification.

**11. Comment syntax.** §9 promises *"Exactly one ignorable channel"* with an
*inertness promise* and never says what it is. `#` appears only inside a code
sample in §6 (`order := by(date)      # or omitted entirely`). Whether `#`
works mid-table, inside a cell, or only in the declaration block is undefined;
`parse/comment-after-declaration` pins only the trailing case.

**12. Refusal precedence.** §9 numbers 13 refusals but never says the list is
ordered. The three `parse/two-refusals-*` fixtures deliberately use
`"refusal_contains": ""`, i.e. they decline to pin it. Two implementations will
print different diagnostics for the same file. Benign for correctness,
corrosive for a suite that matches on message substrings elsewhere.

**13. Type classification of the order column.** §6 requires one of `number`,
`date`, `text` and refuses mixtures — but `text` is a superset that everything
satisfies, so "mixed" only means anything under a first-match classification
(number → date → text). And blanks: their type is unstated. I made blank its
own type, so any blank in the order column is a refusal. Unfixtured.

**14. Cycles.** `parse/mutually-recursive-columns` (`x = y`, `y = x`) and
`parse/self-referential-column` (`b = b + a`) must be **accepted**. §8 promises
the evaluator is "total, terminating" but never says what a cycle evaluates to.
I return `#REF!(name)`; another implementation might return blank or `0`.
Unfixtured beyond "does not crash".

---

## 2. What the spec omits entirely

Behaviour the fixtures require (or that any implementer must decide) with no
prose at all:

1. **Cell delimiting and escaping.** Nothing says a table line ends with `|`,
   how cells are split, that surrounding ASCII spaces are trimmed, or what a
   literal `|` inside a cell does. There is no escape mechanism, so a cell can
   never contain `|` — never stated.
2. **Trailing whitespace after the closing pipe** must be ignorable
   (`canon/idempotent-trailing-spaces`) yet byte-preserved by `render`.
3. **`canon` scope.** §10 shows only the table. That `canon` leaves the
   declaration block *verbatim* (`key   := id` keeps its three spaces) is
   required by `canon/already-canonical` and stated nowhere.
4. **Canonical alignment cells.** That `------` becomes `---` and `----:`
   becomes `--:` is inferable from §10's example only by comparing two
   snippets. The mapping for `:---`, `:-:`, `-:` is never given.
5. **Canonical blank cell** renders as `|  |` (two spaces). Inferable from the
   §10 sample line only if you count characters.
6. **Trailing-newline policy.** `roundtrip/no-trailing-newline` requires the
   absence of a final LF to survive; §10 never says whether canonical form ends
   with a newline.
7. **The exact conflict-marker syntax.** Refusal 9.1 says "conflict markers"
   and never defines them. `|||||||` (diff3 style) is *itself a table line*, so
   an implementer who does not think of it will parse a diff3 conflict as data.
   I check `^(<{7}|={7}|>{7}|\|{7})`.
8. **BOM refusal** (`parse/bom-refused`) — §3 says "no BOM" descriptively but
   §9, which claims to be *the exact set of refusals*, omits it.
9. **`Cf`-in-identifier refusal** — same: §3 states it, §9 omits it. Three
   fixtures enforce it.
10. **A value in a computed cell is a refusal.** §5 says computed cells "are
    empty" — a description, not a MUST — and §9 does not list it.
    `parse/computed-cell-has-value` makes it normative.
11. **Numeric literal syntax.** The set of accepted numbers is defined only by
    negation ("no thousands separators, no parenthesised negatives, no
    non-ASCII spaces"). Exponents? Leading `+`? Unicode digits? I had to guess
    (`[+-]?([0-9]+(\.[0-9]*)?|\.[0-9]+)`, ASCII only). Note that a naive
    `\d` in Python or Java silently accepts Arabic-Indic digits.
12. **Date grammar.** "`Y-M-D` or `Y/M/D`" — `rowrel/order-date-single-digit`
    requires `2024-1-5` to be accepted and to sort *before* `2024-01-12`, so
    dates are compared as `(y, m, d)` integers, not lexically. Nowhere stated.
    Mixed separators in one column must also be one type
    (`rowrel/order-date-mixed-separators`) — nowhere stated.
13. **Text ordering.** `rowrel/order-text-column` requires a text order column
    to sort. By code point? By NFC-normalised code point? Locale-independently?
    §6 names the type and never defines its order — a guaranteed
    interoperability bug the moment a non-ASCII order column appears.
14. **Key ordering for the tiebreak.** §6 requires the tuple `(value, key)` but
    never says how two keys compare.
15. **Where identifiers get NFC-normalised.** §3 says identifiers are compared
    after NFC. `eval/nfd-name-matches-nfc-reference` requires an NFD *column
    name* to match an NFC *reference inside a formula*. Whether **row keys** are
    NFC-compared (for refusal 9.5, and for `set_cell` lookup) is not stated;
    I normalise them.
16. **`set_cell` semantics.** Not mentioned in the spec at all, yet it is a
    required entry point: what it does to padding, whether it may create rows,
    what it does with a missing key. Only `mutate/computed-col-refused` pins
    anything.
17. **`structure` / `render` as a contract.** Also unmentioned. That
    `render(structure(x)) == x` byte-exactly is a *conformance requirement*
    exists only in the runner.
18. **Table location rules.** Whether content may precede the table, whether a
    second `|`-run later in the file is a second table or an error, and whether
    the blank separator line of §4 is mandatory. `roundtrip/no-declarations`
    proves the blank line and declarations are optional; the rest is guesswork.
19. **`lookup()` resolution.** §7 defines `lookup(customers.mdtbl, …)` and §8
    forbids I/O — and `evaluate(text)` is handed only the artifact's bytes, so
    there is no channel to resolve the path even in principle.
    `parse/lookup-syntax` requires it to be *accepted and evaluated*. I return
    `#REF!(file[key])` on the grounds that the target row is always absent.
    Any two implementations will differ here.
20. **Predicate comparison semantics.** `region = "EU"` — string equality, or
    numeric when both sides parse as numbers? Is it NFC-normalised? Is the
    literal grammar only double-quoted strings? Unstated.
21. **Aggregate/column name collision.** Nothing says an aggregate may not
    share a name with a column, nor which wins.
22. **`.rowspec` / editions (§12)** are unfixtured and unreachable — §12 says a
    reader "never consults it", so it has no observable behaviour at all.

---

## 3. Where the spec and the fixtures disagree

**3.1 Line endings — and a harness bug that makes two cases unpassable.**
§3: *"UTF-8, LF line endings, no BOM … Enforced by the parser."*
`parse/crlf-refused` and `parse/lone-cr-refused` agree. But `roundtrip/crlf`
requires `render(structure(x)) == x` on a CRLF file, i.e. `structure` must
**accept** it. The only reconciliation is to split recognition from handling —
`structure` records the diagnostic, `evaluate` raises it — which §9's *"a parse
error is reported separately from being handled"* arguably licenses but §9's
next clause (*"a validator and an evaluator run the same algorithm"*)
contradicts. I implemented the split.

It does not matter, because **`run_cases.py` reads every fixture with
`open(path, encoding="utf-8")`** — Python universal-newline mode. Every `\r` is
converted to `\n` before any implementation is called:

    parse/crlf-refused     bytes CR=9  text CR=0
    parse/lone-cr-refused  bytes CR=1  text CR=0
    roundtrip/crlf         bytes CR=9  text CR=0

So `roundtrip/crlf` does not test CRLF, and the two `*-refused` cases demand
that an implementation refuse a document from which the harness has already
deleted the offending bytes. **They cannot be passed.** Fix:
`open(..., encoding="utf-8", newline="")`. That will also make `roundtrip/crlf`
a real test — and put it back in direct conflict with `parse/crlf-refused`
unless one of the two is retired.

**3.2 §8 versus §7 on `@` coercion** — see ambiguity 1. The suite wins; §8's
"will not coerce to a number is `#REF!`" is therefore wrong as written and
needs to be scoped to *arithmetic* operands.

**3.3 §8 versus the fixtures on `prior`/`delta`.** "A broken reference never
evaluates to … empty" but `prior(c)` on the first row must be `""`.

**3.4 §9 is not the exact set of refusals**, though §2 claims it is
("Deliberately specified … the exact set of refusals (§9)"). At least four
refusals live outside it: BOM, `Cf` in identifiers, CR/CRLF, and a value in a
computed cell.

---

## 4. What is genuinely well-specified

This is not an all-negative report. These were unambiguous on first reading and
I implemented them correctly with no fixture consultation:

- **Error propagation (§8) — the core value proposition.** "An aggregate over
  any column containing a `#REF!` is itself `#REF!` — **it must not sum the
  values it can read**" is precise, motivated, and the boldface is doing real
  work. I got it right first time, and mutating it is caught by the suite.
  Likewise "a blank cell is not zero" and the explicit list of coercions to
  refuse (thousands separators, parenthesised negatives, non-ASCII spaces) —
  three fixtures, all passed on the first attempt.
- **`#REF!(name)` carries the *originating* name**, not the column it surfaces
  in. `eval/broken-ref` (formula `qty * unit`, missing `unit`, aggregate over
  `total`, expecting `#REF!(unit)`) confirmed my reading of §8 without
  amendment. This is a genuinely good design decision, clearly stated.
- **§6's ordering model.** "The sort key is the **tuple** `(typed value of c,
  key)`. It is never a string concatenation", with the reason given, is a model
  normative sentence: it states the rule, the wrong alternative, and why the
  wrong alternative is wrong. I implemented it directly from the prose.
- **§6's independence-from-file-position rule.** "A row's position in the file
  is never an input to any computation" is unambiguous and made the sort/derive
  architecture obvious. `merge/backdated-appended-last` passed first time.
- **§9's refusal list**, as a *list*, is excellent: 13 numbered, testable
  conditions with fixtures for all 13. Its problems are that it is incomplete
  (§3.4) and unordered (ambiguity 12), not that it is unclear.
- **§10's diff-size argument** makes the *purpose* of canonical form
  unmistakable even where the *mechanics* are underspecified.
- **§5's co-location argument** for column names, and §11's reasoning about
  bare repositories and merge drivers, are the clearest prose in the document.
  I never needed a fixture to understand what merges had to do.

---

## 5. Suite gaps found by mutation

I mutated my own (passing) implementation to see what the suite pins down.
Mutants **not caught** at 131 cases — each is a real behaviour two
implementations can differ on today:

| Mutant | Caught? |
|---|---|
| `canon` is the **identity function** | ✗ |
| `canon` performs no alignment-cell normalisation | ✗ |
| `sum`/`min`/`max` treat a blank cell as `0.0` | ✗ |
| `avg` divides by all rows rather than non-blank rows | ✗ |
| `evaluate` returns rows in derived rather than file order | ✗ |
| division by zero yields `0.0` | ✗ |
| `key := c` need not name an existing column | ✗ |
| naive string-concatenation sort key | ✓ |
| `canon` pads cells to column width | ✓ |
| `where` predicate ignored | ✓ |
| NFC normalisation removed | ✓ |
| `Cf` allowed in identifiers | ✓ |
| computed cell may hold a stored value | ✓ |
| trailing whitespace counted as a field | ✓ |
| aggregate skips `#REF!` cells | ✓ |

**The largest single hole: `canon` is effectively untested.** An implementation
whose `canon` is `lambda x: x` passes 129/131. The cause is mechanical — the
runner has no branch for `check == "removes-padding"`:

```python
if "idempotent" in e["check"] and c1 != c2: ...
elif e["check"] == "preserves-values" ...
elif e["check"] == "already-canonical" ...
# "removes-padding" falls through and asserts nothing
```

`canon/removes-padding` is a dead fixture. Since §2 lists "the canonical byte
form (§10)" among the things *deliberately specified because disagreement
produces silent corruption*, this is the highest-value fix available.

---

## 6. Verdict

**Could a competent implementer who had never spoken to the author build a
conforming implementation from `SPEC.md` alone? No.**

The evidence is direct rather than rhetorical: I did exactly that, passed the
57-case suite that existed at the time, and then failed 9 of 74 subsequently
added cases — every failure a documented guess (see the table at the top).
Seven distinct behaviours were wrong. Three of them (`@` coercion, `count`
poisoning, predicate `@` binding) produce **plausible wrong numbers rather than
errors**, which is precisely the failure mode §1 exists to prevent.

What *is* achievable from SPEC.md alone is the architecture: opaque keys,
derived order, tuple sort keys, error propagation, line-per-row merge
behaviour. I got all of that right first time, from the prose, and it is the
hard part. The gaps are in the surface syntax and the total-function edges —
which is unfortunate, because those are exactly where silent divergence lives.

### The three highest-value fixes

1. **Give the file a lexical grammar (a new §4.1), and make §9 the complete
   refusal list.** One ABNF-ish block covering: the line terminator; that a
   table line is `"|" cell ("|" cell)* "|" ws*`; that cells are trimmed of
   ASCII spaces and cannot contain `|`; the alignment-cell pattern and how it
   is distinguished from a data row; the numeric literal grammar (ASCII digits,
   optional sign, no exponent); the date grammar and that dates compare as
   `(y, m, d)` integers; the text collation used for a `text` order column and
   for the key tiebreak; the comment syntax and where it is legal; and the
   conflict-marker set, `|||||||` included. Then fold BOM, `Cf`, CR/CRLF and
   "a value in a computed cell" into §9, and state whether §9's numbering is a
   precedence order. This single change closes roughly two-thirds of §2.

2. **Rewrite §7's group aggregates and §8's coercion rule so they stop
   contradicting each other, and specify `lookup` or delete it.** Say
   explicitly: an `@c` reference is the cell's *raw* value, compared for
   equality, never coerced; the predicate's `@` bindings come from the row being
   computed while the aggregated column is scanned over all rows; a value that
   will not coerce to a number is `#REF!` *when used as an arithmetic or
   aggregate operand* — and state that this includes `count`. Add a worked
   two-row example with the expected numbers. For `lookup`: either define the
   resolution context (which means giving `evaluate` a second parameter and
   amending §8's I/O claim) or remove it. As written it is a mandatory feature
   with no possible implementation.

3. **Make the canonical form testable, and fix the harness.** Add a `canon`
   fixture kind that asserts an *exact expected output file*, not merely
   idempotence, and wire up (or delete) `removes-padding` in `run_cases.py`.
   Specify in §10: cells trimmed then re-emitted as `" " cell " "`, a blank
   cell as two spaces, the alignment-cell mapping for all five forms, that the
   declaration block is left byte-verbatim, and the trailing-newline rule.
   Separately, change the runner to `open(..., encoding="utf-8", newline="")`
   so the CR fixtures test anything at all — and then reconcile
   `roundtrip/crlf` with `parse/crlf-refused`, which cannot both stand.

### Secondary recommendations

- Document `structure`/`render`/`set_cell` in the spec. They are conformance
  requirements that exist only in the runner today.
- State the order of the `rows` sequence `evaluate` returns.
- Add fixtures for blanks under `min`/`max`/`avg`, division by zero, and a
  `key` naming a missing column — all currently free variables.
- Consider stating that §9's list is *not* exhaustive of refusals, or make it
  so. §2's claim that it is "the exact set" is currently false.

---
---

# M2, pass 2 — the amended specification

Appended, not overwritten; everything above is the report against the pre-
amendment `SPEC.md` and the 131-case tree. This pass re-implements
`reference/rowspec_alt/` against the amended spec (§3 line endings, §4 alignment
row and trimming, the new §4.1 lexical grammar, §7 lookup, §8's carve-out, §9
grown to 20 refusals) and the fixture tree as it now stands.

**Isolation held.** I read `SPEC.md`, `conformance/cases/` (including
`cases/README.md` and the `WHY.md` files, which are inside the fixture tree),
and `conformance/run_cases.py`. I did **not** open `reference/rowspec/` or
anything under `design-findings/`, `experiments/`, `DESIGN.md`, `PLAN.md`,
`RESEARCH.md`, or `conformance/mutants.py`. No contamination.

**Result: 190 / 190.** The tree grew from 164 to 190 while I worked; I started
the pass at 11 failures on 164 and finished at 0 on 190. The rewrite was
substantial: line classification, the table run, the alignment row, cell
trimming, the identifier allowlist, the number and date grammars, `lookup`, and
the derived-order row sequence are all new or replaced.

## 0. Did §4.1 close the surface-syntax gap? Mostly — and it is the best thing in the document

**Yes, decisively, for everything it names.** Pass 1's verdict was that the
architecture transmitted and the surface syntax did not. Of the twenty-two
"never stated at all" items in §2 of the pass-1 report, §4.1 closes **fifteen**
outright — cell delimiting, the `|` prohibition and the absence of an escape,
the trimming rule and *why* it stops at ASCII, the alignment-cell spellings and
the all-cells rule that separates §9.8 from a data cell of `---`, the numeric
literal set with the `\d`-matches-Arabic-Indic trap called out by name, date
comparison as an integer tuple, text collation by code point with locale
collation explicitly refused, the identifier allowlist, the annotation channel
in both forms, the conflict-marker set with `|||||||` and the ordering rule that
makes it work, and the last-line terminator rule.

I implemented every one of those from the prose alone and every one was right
first time. Three specific sentences did work that no other formulation would
have:

- **The normative classification order**, with the reason. I had guessed
  `|||||||` in pass 1 and got it right, but I guessed; §4.1 makes it derivable.
  `annotation` before `table-line` I would *not* have guessed — I would have
  scoped annotations to outside the table and then had to invent what a `#` line
  between two data rows does. §4.1.2 answers it and shows its working.
- **"A reader that cannot recognise a construct MUST refuse it, and MUST NOT
  degrade a failed recognition into a different successful one"** (§4). This is
  the single most useful sentence added. It resolves, by itself, a dozen
  questions §4.1 does not individually enumerate.
- **The `[CHOICE]` tags.** Marking a decision as a decision rather than a
  description is exactly right for a spec meant to survive independent
  implementers: it tells me where not to look for a deeper reason, and where an
  objection would be in scope.

**But §4.1 is a grammar for *declarations*, and the format's other expression
language — the header-cell formula — still has none.** That is where every
remaining lexical ambiguity now lives, and §4.1 has made two of them *worse*
than they were before it existed, by fixing `ident` without fixing the language
`ident` appears in. Details in §1.1–1.3 below.

## 1. Ambiguities in the amended spec, ranked

### 1.1 `ident` contains `-`, and the formula language uses `-` as an operator

§4.1.9: `ident = 1*( LETTER / MARK / NUM / "_" / "-" / "." )`. So `a-b` is a
well-formed column name. §7's formula language uses `-` for subtraction. §4.1
gives no formula grammar, so nothing arbitrates. My implementation's answers,
which are guesses:

    | id | a-b | c = a-b |     ->  c is #REF!(a), i.e. `a` minus `b`
    g := sum(a-b)              ->  refused: "expected ')'"

A column named `a-b` is legal to *declare* and impossible to *reference*. Two
implementations will differ here silently: one reads `a-b` as a reference and
totals a column, the other reads it as a subtraction and totals a different one.
This is the highest-risk item in this report — it is a plausible-wrong-number
divergence introduced by an amendment, in exactly the class §1 exists to
prevent. The same applies to `.`: I lex `a.b` as one identifier, so `a.b` can
never be a field access and a column named `a.b` works — but that is my choice,
not the spec's.

### 1.2 An all-digit token means different things in different positions

`parse/all-digit-column-name` and its `WHY.md` already name this, and I agree
with the diagnosis. What the fixture pins is only the declaration side. My
implementation therefore does this, in one file:

    g := sum(123)        ->  the column named 123          (fixture-required)
    | c = 123 * 2 |      ->  the numeric literal 123       (my guess, §4.1.6)
    g := sum(1)          ->  #REF!(1), a broken reference to a column named 1

The third line is the uncomfortable one: `sum(1)` is almost certainly a typo for
something, and under the fixture-required reading it is not a refusal but a
silent `#REF!`. Whichever way §4.1 resolves this, it should resolve it for both
positions at once, and say what `sum(1)` means.

### 1.3 `canon` and CRLF: §3/§10 and §4.1.1 give different answers

§3: *"only the *canonical* form (§10) is LF."* §4.1.1: *"`canon` terminates
every table line it emits and leaves annotations and declarations
**byte-verbatim**."* For a CRLF file those cannot both hold: byte-verbatim
declarations keep their CRLF, so the canonical form is not LF; normalising them
to LF is not byte-verbatim. The two available outputs for the same input are

    mine (§3/§10 reading)   '| id | a |\n| --- | --- |\n| r_01 | 1 |\n\nkey := id\n'
    the §4.1.1 reading      '| id | a |\n| --- | --- |\n| r_01 | 1 |\r\n\r\nkey := id\r\n'

Both are idempotent, so `canon/crlf-idempotent` passes either way; verified by
mutation (below). §2 lists the canonical byte form among the things
*deliberately specified because disagreement produces silent corruption*, and
two implementations canonicalising the same CRLF artifact to different bytes is
precisely that: a `canon` in a pre-commit hook would fight another
implementation's `canon` forever, each producing a whole-file diff.

### 1.4 A self-referential `lookup` reads the disk, not the artifact it was handed

`rowrel/lookup-self` requires `lookup(input.mdtbl, ...)` to resolve. `evaluate`
receives *text* and a *base directory*, so the target is loaded from the
filesystem — including when the target path happens to name the artifact being
evaluated. Demonstrated:

    text handed to evaluate() says "BETA"
    evaluate(text, dir)[0][0]["mate_label"]  ->  "beta"   (the on-disk value)

The returned value contradicts the bytes it was given. This matters directly for
§11, which requires a merging tool to *"merge and then validate every changed
path"*: a tool that validates the merged buffer before writing it gets answers
computed from the pre-merge file. Nothing in §7 or §8 says whether a lookup that
names the referring artifact sees the in-memory bytes or the stored ones, and
the two differ exactly when it matters most.

### 1.5 Confinement is checked against a root the API never names

§7 confines a lookup target *to the repository*; `cases/README.md` supplies the
missing definition ("the case directory is also the repository root") and the
runner supplies it as `evaluate(text, base)`. But `base` is the *artifact's*
directory, and for a chained lookup those diverge: evaluating
`<case>/sub/b.mdtbl` gives base `<case>/sub` while the root is still `<case>`, so
`lookup(../a.mdtbl)` from inside `sub/` is legal by §7 and looks like an escape
to a reader that checks lexically. My implementation threads the root separately
and checks against it; a lexical check passes the suite identically (verified),
so the distinction is untested and unstated. **The spec never defines how a
reader learns where the repository root is** — the only statement of it is in
the fixture tree's README.

### 1.6 §4.1.5's ABNF and its prose generate different languages

`align-cell = [ ":" ] 1*"-" [ ":" ]` generates `:--:`. The prose immediately
after says *"`:--`, `--:`, `:-:` and `---` are the four spellings"*. `:--:` is a
fifth. I accept it (ABNF is labelled normative) and canonicalise it to `:-:`;
a reader following the prose refuses the file. `parse/alignment-*` covers the
four and the refusals, not this.

### 1.7 May a declaration precede the table?

§4's file shape is table / blank / declarations. §4.1.2 says only that
*"annotations and blank lines may precede and follow"* the table — declarations
are not mentioned, and §4.1's `line` production permits a `declaration` anywhere.
I accept a pre-table declaration and honour it. A reader that took §4.1.2's list
as exhaustive would refuse the file under §9.19. Unfixtured; a whole file's
worth of behaviour hangs on whether one sentence is a permission or a
definition.

### 1.8 Blanks in the order column

§6 gives three types and refuses mixtures. A blank is none of them. I treat
`blank` as a fourth type, so one blank among numbers is *mixed* and refused,
while an all-blank order column is single-typed and sorts by key alone. A reader
that folded blank into `text` accepts the first file and orders it differently.
Verified untested by mutation.

### 1.9 Still open from pass 1, and still unfixtured

`min`/`max`/`avg` over a column containing blanks (skip or zero-fill — verified
untested, again); `avg`'s denominator; division by zero (I return
`#REF!(division by zero)`, which is not of §8's `#REF!(name)` shape at all —
nothing says what the name should be); whether `key := c` must name an existing
column; and whether an aggregate may share a name with a column (I allow it).
`key` and `order` are now effectively reserved words on the left of `:=` — §4.1.11
implies it but never says so, and an aggregate named `key` is therefore
impossible.

### 1.10 The `rowrel` row sequence is defined only in the fixture tree

`cases/README.md` says a `rowrel` case asserts a cell *"in the **derived**
order"*. I switched to derived order on that authority. `SPEC.md` does not
mention the row sequence `evaluate` returns, and mutating mine back to file
order still passes 190/190. The normative statement lives in a README that is
not the specification.

## 2. New contradictions introduced by the amendments

1. **§3/§10 versus §4.1.1 on `canon` and line endings** (§1.3 above). Two
   sections amended in the same pass, giving different canonical bytes.
2. **§4.1.5's ABNF versus its own next sentence** (§1.6 above).
3. **§9 says "This list is complete" and it is not.** At least three refusals
   the suite requires have no entry:
   - a **malformed column formula**. `parse/formula-syntax-garbage`
     (`x = 2 ** * 3`), `parse/formula-imports`, `parse/formula-reads-the-clock`
     and `parse/formula-reads-a-path` all require a refusal. §9.12 is scoped to
     *"a line containing `:=`"*, which a header cell is not. §9.18 is about
     `table-line` shape, which the header satisfies. Nothing else applies.
   - a **computed `lookup` path**. `parse/lookup-computed-path` requires
     `lookup(stem + ".mdtbl", ...)` to be refused. §7 states the rule ("never
     computed at evaluation time"); §9 has no entry for it.
   - a **lookup target outside the repository**. `parse/lookup-path-escape`
     requires a refusal; §7 states the confinement; §9 has no entry.
   Each is a refusal the suite enforces, argued in another section, and absent
   from the list that claims to carry every refusal with a back-reference. The
   completeness claim is load-bearing — it is what lets an implementer stop
   looking — so a false one is worse than no claim.
4. **§8's carve-out is right; its last paragraph now overreaches.** *"Constructs
   that would read the clock, the network, or a path are not blocked — they are
   unparseable"* still says *a path*. `lookup` reads a path and is parseable. The
   sentence needs "other than §7's literal `lookup` target" or it re-introduces
   the contradiction the carve-out was added to remove. (The carve-out itself is
   excellent, and the paragraph admitting the fault — "That is a consistent
   reading, it is wrong, and the fault was this section's" — is the right way to
   amend a spec.)
5. **A refusal that is unreachable as written.** §9.16 refuses an identifier
   containing whitespace *or a `Cf` character*. §4.1.9 defines `ident` as an
   allowlist of `L*`/`M*`/`N*`/`_`/`-`/`.`, which already excludes both. The
   clause is now describing a subset of "any character outside `ident`", so the
   three `parse/cf-in-*` fixtures pass for a reason the spec no longer states
   (they are outside the allowlist, not because they are `Cf`). Harmless, but it
   means §3's `Cf` rule is now decorative and a reader could drop it without
   changing behaviour — worth saying so explicitly rather than leaving two
   independent-looking rules.

## 3. Cases I could not pass — none

All 190 pass. `parse/crlf-refused`, which pass 1 reported as unpassable, has
been retired, and `run_cases.py` now reads fixtures with `newline=""`, so the
`\r` fixtures test what they claim. Both fixes landed; the `roundtrip/crlf` +
`parse/crlf-accepted` + `eval/crlf-evaluates` triple is now coherent and my
implementation was wrong, not the suite — `parse/crlf-accepted/WHY.md` judges
that correctly.

Two observations on cases I pass but would flag:

- `parse/lookup-target-duplicate-keys` requires a refusal in the *target*
  artifact to become a refusal of the *referring* one. That is the right answer
  and nothing in §7 or §8 says it. It also means a file's validity is not a
  function of its own bytes, which sits awkwardly beside §12's *"interpretation
  is a function of the artifact's bytes alone"* and §4.1.8's repetition of the
  same commitment. The commitment now needs qualifying: interpretation is a
  function of the bytes of the artifact **and its lookup closure**.
- `parse/lookup-cycle` requires a cycle to be *accepted*. Its value is
  unasserted. I return `#REF!(wanted-column)` at the point of re-entry, which
  makes the answer depend on which artifact the evaluation started from — a
  cycle evaluated from `input.mdtbl` and the same cycle evaluated from
  `b.mdtbl` break at different edges. Deterministic per entry point, not
  confluent across them. §8 requires termination and says nothing about this.

## 4. What the 190-case suite still does not pin

Mutants of my passing implementation that the suite does not catch:

| Mutant | Caught? |
|---|---|
| `canon` leaves non-table line terminators verbatim (the §4.1.1 reading) | ✗ |
| `evaluate` returns rows in file order rather than derived order | ✗ |
| lookup confinement checked lexically instead of against the root | ✗ |
| lookup ignores the target's own derived order when scanning for the key | ✗ |
| a blank in an order column is `text` rather than its own type | ✗ |
| `sum`/`min`/`max` treat a blank cell as `0.0` | ✗ |
| `avg` divides by all rows rather than non-blank rows | ✗ |
| division by zero yields `0.0` | ✗ |
| `key := c` need not name an existing column | ✗ |
| an inline `#` inside a string literal ends the declaration | ✗ |
| `canon` is the identity function | ✓ (fixed since pass 1) |
| a refusal in a lookup target becomes `#REF!` instead of a refusal | ✓ |
| an all-digit token is a literal even in a name position | ✓ |

The `canon`-identity hole from pass 1 is closed — `run_cases.py` now asserts
`removes-padding` properly and that mutant dies. The blank-versus-zero family is
unchanged since pass 1 and remains the largest untested behaviour: `sum`, `min`,
`max` and `avg` may all treat a blank cell as zero and pass the whole suite,
directly contradicting §8's "A blank cell is not zero".

## 5. Verdict on the amended spec

**Could a competent implementer build a conforming implementation from the
amended `SPEC.md` alone? Much closer to yes, and not yet.**

The measurable difference: in pass 1, seven distinct behaviours I inferred from
the prose were wrong. In pass 2 — a substantially larger rewrite, against a much
larger suite — the count was **one**: the all-digit column name in a name
position (§1.2), which the fixture's own `WHY.md` agrees is a spec gap rather
than an implementation fault. Everything else the amendments touched, I got
right from the prose. §4.1 worked.

What did not transmit is what §4.1 did not cover: the header-cell formula
language. Every serious remaining ambiguity (§1.1, §1.2, and the `sum(1)` case)
is in that language, and two of them were *created* by §4.1 fixing `ident`
without fixing the grammar `ident` is used in.

### The three highest-value fixes now

1. **Give the formula language a grammar, in §4.1, at the same level of detail
   as the declaration grammar.** It must settle: how an identifier is lexed when
   `-` and `.` are both `ident` characters and `-` is also an operator (my
   recommendation: require whitespace around binary `-`, or drop `-` from
   `ident`, and say which); whether a bare numeric token in an operand position
   is a literal or a column, in *both* positions, including what `sum(1)` means;
   operator set and precedence; where a string literal is legal; the `@`
   production; and the path token, which is not an `ident` (`../x/y.mdtbl`
   contains `/`) and currently has no production anywhere. Dropping `-` and `.`
   from `ident` would close §1.1 and §1.2 at a stroke and cost only the ability
   to name a column `a-b`.

2. **Make §9 true.** Either add the three missing refusals — malformed column
   formula, computed lookup path, lookup target outside the repository — or drop
   the sentence "This list is complete." Add the fourth while there: say where a
   reader learns the repository root, since §7's confinement rule is
   unimplementable without it and the only definition currently lives in
   `cases/README.md`.

3. **Settle `canon` and line endings in one sentence, and settle the lookup
   closure in another.** For `canon`: state whether a CRLF artifact
   canonicalises to all-LF or to LF table lines with verbatim declarations —
   §3, §10 and §4.1.1 currently support both, and §2 promises this is exactly
   the kind of thing that will not be left open. For lookup: state that a
   target's refusals refuse the referrer, that a lookup naming the referring
   artifact sees the bytes under evaluation rather than the stored file, and
   amend §12/§4.1.8's "a function of the artifact's bytes alone" to "of the
   artifact and its lookup closure".

### Secondary

- State the row sequence `evaluate` returns; it is currently normative only in
  `cases/README.md`.
- Say whether declarations may precede the table (§4.1.2's list of what may
  precede it omits them, and §4.1's `line` production permits them).
- Reconcile §4.1.5's ABNF with its "four spellings" sentence.
- Amend §8's "constructs that would read ... a path are not blocked — they are
  unparseable" to except §7's literal target.
- Fixture the blank-versus-zero behaviour of `sum`/`min`/`max`/`avg`, division by
  zero, blanks in an order column, and `key` naming a missing column. All four
  are free variables today.
