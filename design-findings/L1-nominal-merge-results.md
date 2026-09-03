# L1 — Testing the invariants on a real format (my own work, reproducible)

Harness: `experiments/L1-nominal-merge/tbl.py` (~60 lines) + real git repos.
Candidate format: GFM table where a computed column carries its formula IN THE
HEADER and its cells are blank; aggregates declared as `name := agg(column)`.
No coordinate appears anywhere in the format.

    | item     | qty | unit  | total = qty * unit |
    | -------- | --: | ----: | -----------------: |
    | widget   |  10 | 12.00 |                    |

    grand := sum(total)

## Result 1 — the 480-vs-660 silent-wrong merge disappears (H3)

Reconstructed the prior pass's failing scenario: base totals 480; Alice inserts
a row worth 100 near the top; Bob inserts a row worth 80 at the bottom.

- Stock `git merge`, no custom driver, no .gitattributes: **clean, exit 0**
- Evaluated after merge: **grand = 660.0** (correct)

The A1 version of this same scenario merged clean and produced 480. The fix is
not a better merge algorithm — it is the absence of a range to get stale. The
aggregate names a column, so there is nothing for an inserted row to fall
outside of.

## Result 2 — loud failure propagates (H4)

Renamed column `unit` -> `price`, leaving the formula referring to `unit`:

    total = '#REF!(unit)'   on every row
    grand = '#REF!(unit)'   -- the aggregate REFUSES to sum the good rows

The aggregate propagating the error rather than silently summing what it can is
the whole point. Excel's SUM over an error range does the same; most
hand-rolled implementations do not.

## Result 3 — locality holds (H2)

One cell edit, `qty 20 -> 21`:

    git diff --numstat  ->  1       1       budget.tbl

One line changed of nine. Compare: pandoc changed 42 of 53 lines on a markdown
torture file (prior pass), and Pithy's turndown path rewrites whole files.

## Result 4 — reorder composes with edit (adversarial, passed)

Alice reorders four rows; Bob edits a cell in one of them. Stock git merged
clean and correctly: the moved rows kept their new order AND Bob's edit landed
(grand = 954.0, arithmetically correct).

## Result 5 — COLUMN INSERT IS THE REAL FAILURE (adversarial, FAILED)

Alice adds a column (touching every line); Bob edits one cell.

    merge exit=1
    CONFLICT (content): Merge conflict in b.tbl

Whole-table conflict. Two consequences, both important:

1. This is a LEGITIMATE conflict, not a silent-wrong merge — the invariant
   holds in the sense that matters. But it is a terrible experience, and it is
   exactly the case `daff` handles correctly. **Type-aware merge is therefore
   required for tables, not optional.**
2. **The conflicted file is no longer a valid table.** Git's `<<<<<<<`
   markers destroy well-formedness. Any editor opening it must either parse
   conflict markers as a first-class concept or refuse the file. This is a
   core design problem, not an edge case, and it applies equally to CSV, JSON,
   SVG and every structured plaintext format.

## What this establishes

- H2, H3, H4 survive first contact and are cheap: a ~60-line evaluator and a
  header convention buy correct merges from unmodified git.
- H7 is now load-bearing rather than decorative: without a type-aware merge,
  ordinary column operations produce whole-file conflicts.
- Conflict REPRESENTATION is promoted to a core problem.

---

# L2 — generic entity-map merge (testing PASS2)

Pass 2 claims diff/merge can be written ONCE over entity maps rather than once
per format. `experiments/L1-nominal-merge/merge3.py`, ~70 lines, knows nothing
about spreadsheets: it merges an ordered set of named entities with attribute
maps.

Scenario, all three concurrently: Alice ADDS A COLUMN (touches every line);
Bob EDITS a cell AND INSERTS a row.

    stock git merge-file : exit=1, 2 conflict markers, whole table conflicted
    entity-map merge     : exit=0, all three changes composed correctly

Merged and evaluated: sku column present, gadget qty 99 applied, bolt row
added, grand = 1034.0 (arithmetically correct).

**~70 lines of format-agnostic code converts a whole-file conflict into a
correct merge.** This is the strongest single piece of evidence that the
generic entity-map merge belongs in the core: it is where the real work is,
and it is not per-format work.

## Caveat 1 — row identity requires a key

Row identity here is the first column. A table with no key column falls back to
alignment heuristics (daff's problem), and the guarantee weakens. **A declared
key is what buys the clean merge.** This should be an explicit part of the
format, not a convention.

## Caveat 2 — my own renderer violated the round-trip law within the hour

The merge output turned the alignment row `| --: |` into `| --- |`, silently
dropping right-alignment. `render(parse(b)) != b`.

I am recording this rather than quietly fixing it, because it is the single
best argument for making the round-trip law an enforced, property-tested
invariant of the substrate instead of a coding guideline. The failure mode that
destroyed Pithy's premise reappeared in 70 lines of my own code written by
someone who had just finished writing down the law. Discipline does not work
here. Only tests do.
