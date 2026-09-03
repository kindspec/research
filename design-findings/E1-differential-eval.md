<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# E1 — Differential evaluation: does rowspec compute what the spreadsheet computed?

Everything below was run. Harness: `experiments/E1-differential/e1.py`.
Raw counters and samples: `experiments/E1-differential/out/*.json`.
Measured against a **pinned snapshot** of the implementation, taken because the
repo changed under the run (see §7): `experiments/E1-differential/snapshot/`
— `reference/rowspec/table.py` md5 `b359c007bb2a96e29841a3db59e6db8c`
(mtime 2026-08-30 09:39:52), `SPEC.md` md5 `b0e22de976d6dc2b67a24fa78804a571`.
No packages installed; OOXML via stdlib `zipfile` + `ElementTree`.

---

## 0. Verdict up front

**On the arithmetic it can actually do, rowspec is right. The evaluator has one
class of genuine bug, and it has exactly one root cause: the reference
implementation does not implement §4.2 — it delegates the normative expression
grammar to Python's `ast.parse`.**

Three consequences, all silent, all reproduced on header names taken from real
spreadsheets:

    | Nº | No | out = Nº |      ->  out = 22.   THE OTHER COLUMN'S VALUE.
    | 1000_2999 | out = 1000_2999 |  ->  out = 10002999.  A NUMBER.
    | a | out = a*1e3 |         ->  2000, though `1e3` in a CELL is #REF!.

The second-order finding is about the *claim*, not the code: **30.5% of the
formulas the W3 translator calls "mechanically translatable" cannot be
evaluated by rowspec at all.** `CLEAN` meant "fits the `.tbl` surface", never
"the evaluator implements it".

---

## 1. Corpora, and what was actually evaluated

Reused from W3-interop (`experiments/W3-interop/corpus-hunt/`), because they
are real `.xlsx` written by real spreadsheet engines and each formula cell
carries Excel's own last computed value in `<v>`:

| corpus | source | workbooks | formula cells |
|---|---|---|---|
| **SpreadsheetBench 912** | HF `KAKA22/SpreadsheetBench` | 5,458 | 1,013,559 |
| **TmplEnron** | figshare 5838600, real Enron business workbooks | 68 | 976,328 |
| SB verified-400 | curated subset, *overlaps SB912* — used as a check only | 800 | 61,224 |

The primary figures are **SB912 + TmplEnron**; SB400 overlaps SB912 and is
never added into a total. `<f t="shared">` groups were expanded (the master
formula shifted by (Δrow, Δcol)), which is what makes fill-down columns visible
at all: **641,494 of the formula cells reached are shared-formula expansions**,
0 unresolved.

### The exclusion ladder — SB912, every step measured

    1,013,559  formula cells read
     -244,244  sheet has no inferrable header row              (24.1%)
      -57,020  array formula (<f t="array">)                    (5.6%)
     -785,734  NEEDS-HUMAN or UNTRANSLATABLE (W3's result)
    ----------
      170,805  mechanically translatable                       (16.9%)
     -101,435  NO GROUND TRUTH: the file's <v/> is empty        (59.4% of these)
    ----------
       69,370  translatable AND carrying Excel's own answer
      -21,165  translates, but is OUTSIDE rowspec's grammar     (30.5%)
    ----------
       48,305  evaluable  (48,090 row formulas + 215 aggregates)
      -30,876  a DUPLICATE header name makes the reference ambiguous
    ----------
       17,329  compared

TmplEnron loses nothing after translation: 38,352 translatable, all evaluable,
all with cached values, **38,352 compared**.

    COMPARED, PRIMARY:  55,681 cells
                        267 distinct workbooks, 1,908 distinct sheets

## 2. Tolerance, stated and justified

A cached numeric `<v>` is text. Both Excel and rowspec compute in IEEE binary64.
The comparison is on **doubles**, never on formatted strings, and the input
literals I write into the `.mdtbl` are the *shortest text that reparses to the
identical double* (`repr`, falling back to an exact non-exponential decimal
expansion), so no precision is lost on the way in.

Three tiers are reported separately and never merged:

- **exact** — `rs == excel` as doubles. 36,571 cells.
- **15-sig** — equal to 15 significant decimal digits. 1,000 cells. Justified,
  not chosen for convenience: **Excel's own serializer writes at most 15
  significant digits.** Measured, over the numeric `<v>` of 300 SB400
  workbooks (78,000 values): the significant-digit histogram runs 1..15 and then
  stops — 1,311 values at 15 digits, and the 2,085 values at 16-17 digits are
  the shortest-`repr` signature of a non-Excel producer, not of Excel. An input
  read back from a `.xlsx` is therefore only known to 15 digits, and no
  recomputation from it can be more accurate than that.
- **worse than 15-sig** — a disagreement. Not tolerated at any epsilon.

**Adversarial check that the tolerance has teeth.** The whole run was repeated
with a known defect injected into rowspec's operator table (`E1_MUTATE`), on
SB400:

    mutant            A.exact   moved to disagreement
    none                 631            0
    `+` becomes `-`      499          228
    `*` off by 1e-15     394          336      <-- a ~1-ulp error IS caught
    blank treated as 0   840         -209      <-- exactly the blank class, nothing else

A one-ulp perturbation of multiplication is caught. The tolerance does not hide
errors, and the blank-cell class is precisely and only the blank-cell class.

## 3. The result

    AGREEMENT                                        38,164 / 55,681  = 68.5%
      exact double equality                          36,571
      equal to 15 significant digits                  1,000
      Excel cached an error, rowspec produced #REF!      593

    DISAGREEMENT                                     17,517
      blank operand: Excel says 0, rowspec #REF!     16,953   BY DESIGN (§8)
      text passthrough: `out = a`, a is text            504   BY DESIGN (§7)
      NUMERIC-LITERAL SHADOWING                          48   ROWSPEC BUG
      cancellation on 15-digit inputs                    12   LEGITIMATE

    Excluding the two by-design classes:              38,164 / 38,224 = 99.84%
    Wrong numbers that are nobody's design decision:      48 = 0.13%

**There is not one unexplained disagreement in 55,681 comparisons.** Every cell
lands in a class with a mechanism. No evidence of a stale Excel cache anywhere
in the compared set.

### 3.1 Every class, with a worked example

**(a) Blank operand — legitimate, 16,953 cells (30.4% of all comparisons).**
`48643/1_48643_golden.xlsx!E5`, `=B5*C5` with B5 and C5 both empty. Excel: `0`.
rowspec:

    | x0 | x1 | zout = x0 * x1 |
    | --- | --- | --- |
    |  |  |  |                      ->  zout = #REF!(x0)

§8 is explicit — "a blank cell is not zero" — and rowspec is right and Excel is
wrong, in the sense that matters here: Excel's `0` is the plausible-wrong-value
this format exists to refuse. But see the spec gap in §5(c): the *token* is
wrong even though the refusal is right.

**(b) Text passthrough — legitimate by design, 504 cells.**
`CF_22493!T3`, `=E3` where E3 is `"Amazon Credit Card"`. rowspec: `#REF!(x0)`,
because §7's formulas are arithmetic and §8 makes a non-numeric operand `#REF!`.
Correct — but note what it costs: **a computed column can never carry text**,
and W3-interop's own showcase translation `IF(C2>10,"BIG","small")` is therefore
untranslatable in fact while being labelled CLEAN.

**(c) Numeric-literal shadowing — ROWSPEC BUG, 48 cells.** §4 below.

**(d) Float cancellation — legitimate, 12 cells.**
`50442!K4`, `=Table1[[#This Row],[EXIT]]-Table1[[#This Row],[ENTRY]]` on two
time serials. Excel `-0.30000000000000099`, rowspec `-0.29999999999999716`,
40-digit decimal on the same inputs `-0.3`. Neither engine has the right answer;
subtracting two nearly-equal 15-digit values destroys the low digits. Nothing
here is fixable in rowspec.

**(e) Both errored — agreement, 593 cells.** `49613!E3`, `=C3/D3` with `D3 = 0`.
Excel `#DIV/0!`, rowspec `#REF!(/0)`. Against the *previous* revision of the
file this crashed with an uncaught `ZeroDivisionError` (36 corpus instances);
the revision measured here fixes it. See §7.

## 4. Genuine rowspec bugs, most severe first

All three are one bug: **`_ast()` calls `ast.parse`, so rowspec's normative
§4.2 expression grammar is in fact Python's.** The independent implementation
in the same repo, `reference/rowspec_alt/`, hand-writes a tokenizer and gets all
three right — so these are also *interoperability* failures between two
implementations shipped side by side.

### B1 — Python's NFKC identifier folding silently reads a DIFFERENT COLUMN

    | Nº | No | out = Nº |
    | --- | --- | --- |
    | 11 | 22 |  |

    reference:  out = 22.0        <-- the value of column `No`
    rowspec_alt: out = 11.0       <-- correct
    control:    `g := sum(Nº)` gives 11.0 in BOTH -- so ONE FILE, TWO
                READINGS OF ONE NAME, in two subsystems of one implementation.

`ast.parse` NFKC-normalises identifiers; `Nº` becomes `No`. §3 is explicit that
"identifiers are compared after Unicode **NFC** normalisation", and under NFC
`Nº` and `No` are distinct columns — so §3's duplicate-key refusal correctly
does not fire, and nothing else catches it. With only `Nº` present the answer is
`#REF!(No)`, naming a column that does not exist in the file.

This is the worst failure mode the format has: a wrong number, from the wrong
column, with no diagnostic. `Nº` is not synthetic — it appears as a real header
in SB912. The same holds for every NFKC-compatibility character: `fiﬁ` reads
column `fifi`.

### B2 — a legal column name is read as a numeric literal

    | 1000_2999 | out = 1000_2999 |
    | --- | --- |
    | 5 |  |

    reference:  out = 10002999.0      rowspec_alt: REFUSED
    control:    `g := sum(1000_2999)` gives 5.0 in the reference.

§4.1.9 admits digits and `_` in an `ident`, so `1000_2999` is a legal column
name; §4.2's `literal` is `1*DIGIT [ "." 1*DIGIT ]`, which `1000_2999` is not,
so §4.2 says unambiguously that this is an `ident`. Python's PEP 515 digit
separators say otherwise. rowspec's own `num()` docstring names this exact
hazard ("`num('1_000')` is 1000.0") and guards the *data* channel against it —
the formula channel walks straight into it.

Corpus-wide: **43 of 8,171 header-bearing sheets (0.53%) carry at least one
column name the reference reads as a number**, 65 distinct names, and they are
the natural ones — `10_00`/`10_15`/… (a time-of-day header row), `1_0`/`2_0`
(version numbers), `31_03_2021` (a date header), `1000_2999` (an amount bucket).
48 evaluated cells produced a wrong number this way.

### B3 — literal spellings the format refuses as data are accepted in formulas

    | a | out = a*1e3 |   ->  2000.0        | a |  ... | 1e3 |  ->  #REF!(a)

`1e3`, `0x10`, `0b1`, `1_0` all evaluate in a formula. §4.1.6 refuses every one
of them as a cell value (SPEC line 208 names `0x10` explicitly), and §4.2's
`literal` admits none of them. One lexeme, two meanings, one file.

### B4 — the two reference implementations disagree on `+a` and on `#REF!` text

Found by the same differential, and they are `rowspec_alt`'s bugs, not the
reference's:

- `| a | b | out = +a*b |` — reference REFUSES (correct: §4.2's
  `factor = [ "-" ] primary` has no unary plus); **`rowspec_alt` returns 6.0**.
  Not exotic: `=+B2*C2` is the Lotus-inherited idiom, **384 cells in SB912**.
- division by zero — reference `#REF!(/0)` as §4.2 rule 2 now requires;
  **`rowspec_alt` returns `#REF!(division by zero)`**. Error values are data:
  they land in cells and poison aggregates, so two spellings are two files.

## 5. Spec gaps the comparison exposed

**(a) The arithmetic model is not specified.** §4.2 fixes the operators; nothing
fixes the number system. Measured: of the 1,000 cells that agree only to 15
digits, **501 are cells where 40-digit decimal arithmetic on the same inputs
reproduces Excel's cached value exactly and rowspec's binary64 does not.** A
decimal implementation and a binary64 implementation are both conformant today
and will disagree in the last digit on 3.1% of SB912's numeric
comparisons (501 of 16,232; TmplEnron had none, its arithmetic being coarser). For a format whose
§2 says two implementations disagreeing here "produce silent corruption rather
than an argument", this is a first-order omission. §2 currently files "number
formatting" under *deliberately left open* — that is fine for display and wrong
for the evaluator.

**(b) Overflow produces a value the format cannot store.** Both implementations
return `inf` for a product that overflows binary64. §4.2 rule 2 rejects `inf` as
the answer for division by zero using precisely the argument that applies here —
"producing one would manufacture a value the format cannot store, so `canon`
could not round-trip its own output" — and then leaves overflow undefined. Not
observed in the corpus; found by taking the spec's own reasoning seriously.

**(c) `#REF!(name)` conflates two different conditions.** §8 defines
`#REF!(name)` as "a reference to a name that does not exist". rowspec emits the
identical token for a column that *does* exist whose cell is blank, and for one
whose cell holds text. The reader cannot tell a broken schema from a hole in the
data — and the blank case is 30.4% of every comparison in this study.

**(d) The data-region boundary is still a guess, and it is load-bearing for
aggregates.** Measured: `31202!I48`, `SUBTOTAL(109,tblNomina[TOTAL])`. Excel
`135,500`; the shape heuristic inferred a one-row data region and rowspec
totalled `7,500` — a plausible wrong number with no diagnostic. Reading the
declared `xl/tables/*.xml` range instead fixes it (24 cells). rowspec is not at
fault; the *importer* is, and this is the risk-1 shape that W3-interop §2.2(b)
already flagged, now with a number on it.

## 6. What was excluded, and what the harness cannot do

- **101,435 translatable cells (59.4%) had no ground truth**: the corpus file
  contains `<f>…</f><v/>` — a formula with an empty cached value. Not a harness
  choice; there is nothing to compare against.
- **30,876 evaluable cells dropped for a duplicate header name.** Two columns
  share a name, so the A1→name translation is ambiguous. rowspec would refuse
  such a file outright (§4 duplicate column name), so nothing is being hidden —
  but it is the single largest *harness* exclusion and it is not small.
- **21,165 translatable cells are outside rowspec's grammar** — this is a
  finding, not an exclusion. `SUM(…)` 5,309, `IF` 12,643, `ROUND` 921, `INT`
  621, `MIN`/`MAX` 581, `AVERAGE` 192, `CEILING` 186, unary `+` 384, `&` 76.
  **W3-interop's 11.4% cell-weighted "mechanically translated" figure must be
  read as ~7.9% once "and rowspec can evaluate it" is required.**
- **Per-cell isolation.** Each formula is tested alone: its inputs are the
  cached values from the same row. **3,422 of 17,214 SB912 row comparisons
  (19.9%) had an input that was itself a formula cell**, so for those, error
  *propagation along a chain* is untested — only the one step is. Since every
  step agrees, a chain of agreeing steps agrees, but a chain-level test would be
  a stronger claim than this one makes.
- Only 267 of 5,526 workbooks contributed a single comparison. The evaluated set
  is real but it is a thin, non-random slice: the workbooks that happen to have
  a header row, no duplicate names, cached values, and same-row-only arithmetic.
- **No Excel.** The oracle is the cached value in the file. A stale cache would
  present as a rowspec bug; zero unexplained disagreements across 55,681
  comparisons argues there is none in this set, but it cannot prove it.
- Nothing was tested for `lookup` (reserved, §7), filtered aggregates over other
  rows, cross-sheet references, or dates — the corpus has all four in quantity
  and rowspec has vocabulary for none of them.

## 7. A note on the moving target

`reference/rowspec/table.py` was edited by another agent **during this run**
(09:39:52), and `SPEC.md` six minutes earlier. Against the pre-09:39 revision
this harness measured two further defects that the current revision fixes, and
they are recorded because they show what the differential catches:

- **division by zero raised an uncaught `ZeroDivisionError`** out of
  `evaluate()` — 36 real corpus instances, and a direct contradiction of §8's
  "the evaluator is total". Now `#REF!(/0)`.
- **`a & b` and `a ^ b`** — both legal Excel operators, 76 corpus cells —
  produced `#REF!(<class 'ast.BitAnd'>)`: a *syntax* error degraded into a
  *reference* error, per row, with a Python class repr leaked into the data
  channel. Now a refusal with a real message.

Both were fixed independently of this experiment, which is a point in the
project's favour and also the reason every figure above is pinned to a snapshot.

**Re-verified against a still-newer head** (`table.py` md5
`f1ab8c209012a9aa2e120b4ba0268ce8`, which also lands a batch of new
`conformance/cases/eval/*` including `bare-numeric-position-decides` and
`aggregate-over-a-numeric-name-is-a-broken-reference`): **every bug in §4 and
every gap in §5 is still present, unchanged.** `out = Nº` still returns `22.0`;
`out = 1000_2999` still returns `10002999.0` while `sum(1000_2999)` returns
`5.0`; `a*1e3` and `a*0x10` still evaluate; `rowspec_alt` still accepts `+a*b`
and still spells division by zero `#REF!(division by zero)`; overflow still
yields `inf` in both. The numeric-name work in flight addresses a *bare all-digit*
name, not the digit-with-separator and NFKC-compatibility cases this study
found in real headers.

## 8. The one result that should move confidence

**Up:** 38,352 formula cells from 47 real Enron business workbooks, evaluated
against Excel's own cached values, **30,720 bit-exact and not one wrong number**
— the remaining 7,632 are the blank-operand rule, behaving exactly as §8 says it
should. On the arithmetic the format claims, the evaluator is correct on real
data at scale, and a 1-ulp mutation is detected.

**Down, and it should weigh more:**

    | Nº | No | out = Nº |     ->  22.0
    | Nº | No |                ->  sum(Nº) = 11.0

One file. One name. Two answers, from two subsystems of the same
implementation, with no diagnostic — because §4.2's grammar is normative prose
and `ast.parse` is what actually runs. The number of *corpus cells* this hit is
small. The number that matters is that it exists at all in the one place the
format promises it cannot: a name resolving to something other than the column
it names.
