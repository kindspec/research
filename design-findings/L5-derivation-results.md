# L5 — cross-artifact derivation as one mechanism (my own work)

`experiments/L5-derivation/`. Tests H8 (one nominal address grammar) and H10
(formulas, references, charts and exports are ONE mechanism, not four).

## Setup

`report.md` — a prose document — references a value computed inside a table:

    Procurement totalled {{ budget.tbl#grand }} across all line items,

`budget.tbl` is the L1 format; `grand := sum(total)` is a column aggregate over
a computed column. So the chain crosses three layers — prose reference ->
table aggregate -> column formula -> cell values — through ONE address grammar
with no coordinates anywhere in it.

Dependencies are DISCOVERED by parsing (the `refs` half of the type contract),
never declared. Cache keys are `hash(rule, artifact, name, content-hash)`.

## Results

    1. cold                          miss  -> 480.00
    2. warm, unchanged               hit   -> 480.00
    3. edit table: qty 20 -> 30      miss  -> 540.00     (invalidated exactly)
    4. revert the edit               HIT   -> 480.00
    5. break the dependency          ValueError: budget.tbl#grand -> #REF!(unit)

## What each result establishes

**(3) Staleness is exact.** No timestamps, no dirty flags, no manual
"recalculate". The key contains the input's content hash, so invalidation is a
consequence of the addressing rather than a mechanism bolted on.

**(4) is the interesting one.** Reverting an edit HITS the original cache
entry — undo costs nothing. A timestamp-based build system (make, and every
spreadsheet's dirty-bit recalc) must redo the work because mtime moved forward.
This is the concrete payoff of content addressing over mtime, and it is exactly
the "rebuilder" axis of *Build Systems à la Carte*: a spreadsheet is a
restarting scheduler with a dirty-bit rebuilder; this is a suspending scheduler
with a constructive-trace rebuilder, which is strictly better and no harder.

**(5) Errors cross artifact boundaries without degrading.** Renaming a column
inside the table surfaces as a named failure in the DOCUMENT that referenced
it. It does not render as blank, zero, or the last known good value. I3 holds
across artifacts, which is where it matters most — a stale number in a report
is exactly the failure nobody catches.

**(1,2) I4 holds.** `report.md` on disk always contains
`{{ budget.tbl#grand }}`, never `480.00`. There is no committed derived value
to go stale, and the diff of a document never churns because a number
elsewhere changed. The rendered artifact is a separate derived file; whether
it is committed is a `.gitignore` decision, not an architectural one.

## Cost

The whole derivation engine — reference discovery, resolution, content-
addressed memoisation, error propagation — is 40 lines. The claim it supports
is not that this is production-ready but that formulas, cross-document
references, charts and exports do not need four mechanisms. They need one, and
that one is small because the paper already worked it out.
