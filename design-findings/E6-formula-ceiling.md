<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# E6 — The formula ceiling, and why it should stay where it is

Measured 2026-08-31 against `reference/rowspec/table.py` at v0.1.0, over the
full SpreadsheetBench corpus with the translator's `--expand-sum` step active.
Harness: `experiments/E1-differential/e1.py`.

---

## 0. Verdict

**Do not add `ROUND`, `ROUNDDOWN`, `INT`, `MIN`, `MAX` or `CEILING`.** Together
they account for 4,362 corpus cells and **nine distinct expressions**. Six
functions of permanent, twice-implementable surface area, for nine formulas.

The remaining gap is **8,417 cells and 70 distinct expressions**. Only one entry
in it has any breadth, and it is not a function.

## 1. The table that decides it

| blocker | cells | distinct expressions |
|---|---:|---:|
| `If:text-branch` | 2,602 | **29** |
| `Call:ROUNDDOWN` | 2,052 | **1** |
| `Call:ROUND` | 921 | 2 |
| `Call:INT` | 621 | 2 |
| `Call:MIN` | 543 | 2 |
| `Op:unary-plus` | 384 | 2 |
| `Call:AND` | 351 | 8 |
| `Op:&` | 333 | 7 |
| `Call:AVERAGE` | 192 | 4 |
| `Call:CEILING` | 186 | **1** |
| `Call:OR` | 141 | 7 |
| `Call:MAX` | 39 | 1 |
| everything else | 52 | 5 |
| **total** | **8,417** | **70** |

`ROUNDDOWN` is the case to look at. **2,052 cells, one expression:**

    IF(__of_Games=0, 0, (ROUNDDOWN(Pins/__of_Games, 0)))

A bowling average, filled down a column, in a problem the corpus ships six
times. `CEILING` is 186 cells and one expression. `MAX` is 39 cells and one.

## 2. Why the cell counts are so misleading

Two multipliers stack, and neither is visible in a function-name tally.

**The corpus replicates.** 557 of 2,667 SpreadsheetBench problems ship six files
each — input and answer across up to three instances. A contributing problem is
counted roughly sixfold.

**A formula is filled down.** One authored expression occupies every row of its
column, hundreds of cells for a single decision by a single person.

Multiply them and one formula becomes ~500 cells. The mean here is **485 cells
per distinct expression** across the six numeric functions.

## 3. This is the same finding as E4, arrived at from the other side

E4 examined `IF` and `SUM` because they were 17,952 of the 21,165 cells outside
the grammar, and found that `SUM` was 99.1% a **translator** gap — `SUM(a,b,c)`
is `a+b+c`, which §4.2 already generated. The lesson recorded then was that
*function-name frequency is not demand for a grammar*.

E6 is the same lesson with the next term corrected: **cell frequency is not
demand either.** The unit that matters is a distinct expression, because that is
the unit a person actually wrote.

Adding a function is not a local change. It costs normative text with its
`[CHOICE]`s argued, conformance fixtures written by an author who may not read
the implementation, mutants proving those fixtures bite, and a second
implementation built from the prose alone. That is the right price for a
capability. It is not the right price for nine formulas.

## 4. What the ceiling actually is

`.mdtbl` computes arithmetic over named columns, with `if`, comparisons, and
five aggregates. It does not compute spreadsheets. §1 already says matching a
particular spreadsheet's answers is not a goal; this is the measured shape of
that limit, and it should be quoted as a *deliberate scope*, not a coverage
figure to be improved.

## 5. The one entry with breadth, and it is a design question

`If:text-branch` — **2,602 cells, 29 distinct expressions**, the widest by an
order of magnitude — is `IF(cond, "PASS", "FAIL")`: a computed column holding
text.

That is not a function to add. It changes what a computed value *is*, and so
reaches §5 (a computed column's cells are empty), §7 (what `sum` over that
column means), §8 (the value model is number-or-error), §9.17, and §10's
canonical form. §4.2 rule 10 already states this and declines it deliberately.

If the ceiling is ever raised, this is the only candidate whose evidence is
breadth rather than replication — and it should be argued on its own terms,
with its own measurement, not folded in beside six arithmetic functions.

## 6. Method note

The first version of this table was wrong and reported the baseline rather than
the `--expand-sum` run: the dump script called `e1.main()` directly, and
`--expand-sum` is parsed in the harness's `__main__` block, so the option never
took effect. `Call:SUM` sat at the top with 5,861 cells — a bucket the
translator already handles.

Caught by asking why a number that should have been absent was the largest one
present. A configuration flag that a harness silently ignores produces a
plausible table, which is the same failure shape this project keeps recording,
in the measurement rather than in the code.
