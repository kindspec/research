# Closing the two design-blocking open problems

## B. Row-relative computation, restored — `experiments/X1-order/`

I deleted `prev.` because the red team showed it is a coordinate, and left a
hole: running totals, cumulative sums, deltas, and every time-series model. The
prior landscape pass had already identified exactly that hole as the defect
that made a competitor's formula engine unusable. Removing the bug without
replacing the capability was not a fix.

**The insight: `prev.` failed not because row-relative computation is wrong,
but because "the row above" is a PLACE.** If the table declares what determines
row order, "the previous row" becomes a NOMINAL relationship — "the row with
the next-lower key" — and is independent of physical position, insertion point,
and merge order.

    order := by(date)     row-relative operators legal; order derived from DATA
    order := none         row-relative operators are a PARSE ERROR (the default)

Operators: `cumulative(col)`, `prior(col)`, `delta(col)`. The total order is
(order key, row id), so ties are resolved deterministically and confluence
holds.

### Verified

    1. cumulative() with no declared order
       -> REFUSED: "column 'balance' uses row-relative cumulative() but the
          table declares no row order. Add `order := by(<column>)`."

    2. physically shuffling every row in the file
       -> IDENTICAL results. Position is not an input.

    3. two branches insert rows; merged both ways
       -> merge order alice-then-bob: final = 138.0
          merge order bob-then-alice: final = 138.0        (confluent)

    4. the decisive case: a BACKDATED row appended physically LAST
       physical order in file : dates 1, 4, 3, 5, 7, 0
       computed order         : 0, 1, 3, 4, 5, 7 -- the backdated row leads
       balances               : 500, 600, 570, 573, 623, 603   (correct)

Under `prev.` that last case was silently wrong. Under a declared order it
cannot be, because the file's physical arrangement is not consulted.

**This is I2 applied to sequence.** Nominal addressing said "reference things by
name, not by position." Declared order says the same about ordering: a row's
predecessor is determined by data, not by where someone happened to paste it.

## A. Meaning drift, detected — `experiments/X2-drift/`

Risk 1 in the report, and the deepest hole: a reference that still RESOLVES, to
something else. Rename `total`→`gross` and `net`→`total` on one header line,
leave `grand := sum(total)` untouched: clean merge, no `#REF!`, and the answer
moves from 360 to 288 with nothing to see.

**Nothing in the format can catch this** — the file is internally consistent and
every reference resolves. But the previous version exists, because that is the
entire premise of the system. So the check is HISTORY-AWARE, and it is the third
use of the same similarity-matching mechanism already used for blocks and rows.

**The design decision that makes it usable: identity across versions rests on a
column's DEFINITION, not its values.** A value-based check fires on every
ordinary data edit, which would make it worthless — I built that version first
and it did exactly that. A literal column's identity is its name; a computed
column's identity is its formula, resolved through renames already detected, to
a fixpoint.

### Verified — seven cases, two fire, five stay silent

    1  rename swap, reference untouched          FIRES   (correct)
    2  an ordinary data edit                     silent  (correct)
    3  adding a row                              silent  (correct)
    4  rename with all references updated        silent  (correct)
    5  partial rename, aggregate forgotten       -> #REF!(total), named
    6  malformed alignment row                   -> REFUSED
    7  two LITERAL columns swap names            FIRES   (correct)

Case 1's message names exactly what happened:

    MEANING DRIFT   grand :=  ->  `sum(total)`
        unchanged reference to 'total', but 'total' was rebound:
          was:  qty * unit
          now:  gross * 0.8, which used to be called 'net'

### Three gaps this work surfaced and fixed

- A dangling aggregate reference **crashed with a TypeError** instead of
  producing `#REF!`. An I3 violation hiding in the implementation.
- The alignment row's field count was **never validated**, so a table whose
  separator row disagreed with its header parsed happily.
- A swap of two LITERAL column names is invisible to definition-based identity,
  because no definition changes. Detected separately as a **permutation** — the
  value vectors moved *between* names rather than changing, which distinguishes
  a swap from an edit.

Case 7 is worth dwelling on: swapping `qty` and `unit` leaves `total = qty *
unit` correct, because multiplication commutes. It is silently harmless there
and silently catastrophic in `qty / unit`. The check does not care which; it
reports the rebinding.

## What this does to the report

Risk 1 moves from "no mechanism exists, and nothing in the literature addresses
this" to "a mechanism exists, is implemented in ~90 lines, and has zero false
positives on the benign cases tested." That is not the same as solved — the
false-positive rate on real repositories is unmeasured, and the check requires
history, so it cannot run on a single snapshot. But it is no longer a hole.

---

## A (revisited) — meaning drift, after round two reopened it

Round two found six false positives, all ordinary work: a whitespace change, an
operand reorder, redundant parentheses, a formula fix, a data edit, and
decisively **a VAT rate changed from 1.2 to 1.25**. A detector that fires on
whitespace gets muted, and a muted detector catches nothing.

**Cause:** any change to a column's definition was reported as a rebinding.
That is far too broad. A rebinding is narrower and precise:

    a name is REBOUND only when it has taken over ANOTHER column's definition.

In the implementation that is exactly the condition `was is not None` — the
rename map must show some other column previously carrying this definition. An
ordinary edit changes a definition without moving one, so it cannot be a
rebinding by construction.

One line. Results:

    whitespace change        0 findings
    operand reorder          0
    redundant parentheses    0
    VAT rate 1.2 -> 1.25     0
    formula fix              0
    data edit                0

    rename swap              1 finding   (still fires)
    literal column swap      2 findings  (still fires)

The false-positive rate on the cases that mute a detector goes to zero without
losing either true positive. Risk 1 closes again — and this time the narrowing
follows from what a rebinding *is*, rather than from what happened to work on a
fixture.

---

## B (extended) — per-row group aggregates and conjunctive predicates

Interop measured the largest translatable gap precisely: 63.6% of the SUMIF
miss is multi-predicate `SUMIFS`, and the group-by shape
(`SUMIF($A$2:$A$100, A2, $B$2:$B$100)` — "the total for *this row's* category")
was called *"the most `.tbl`-shaped miss of all: per-row and fully nominal."*
There was no grammar for it.

Added: `@col` means THIS ROW's value of `col`, following Excel Tables' `[@Qty]`.

    | region_total = sum(amount where region = @region)                |
    | rep_in_region = sum(amount where region = @region and rep = @rep) |

Verified correct: EU = 200 (100+40+60), ann-within-EU = 160, US = 250.

**And it merges.** Two branches inserting rows into different groups, both
merge orders:

    merge order a b  ->  EU 225.0 | US 280.0 | all 505.0
    merge order b a  ->  EU 225.0 | US 280.0 | all 505.0
    truth            ->  EU 225   | US 280   | all 505

A row whose group did not change is untouched (`r_03` stays 250.0 after an EU
insert). The construct is nominal throughout — a predicate over names, an
aggregate over a named column — so nothing positional can leak in.

This is the third capability restored by asking *"is it positional?"* rather
than *"is it cross-row?"*. Cross-row is fine. Positional is not.
