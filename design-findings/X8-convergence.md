# The convergence — three independent lines, one answer

Three research tracks that did not talk to each other arrived at the same
conclusion about what this project actually is. That convergence is the most
useful result of the whole exercise, and it is not what I set out to build.

## Line 1 — demand

Demand for correct MERGING is absent and measurable as absent: a 230:1
give-up-to-hack ratio, zero reported instances of a silently wrong merged
number, GitHub archiving its own productised version, $65M of destroyed capital,
and no regulatory hook.

Demand for a VALIDATOR is present and hand-rolled: the four reference-data
registries surveyed had each independently built a CI check, a bespoke
`db:validate`, and a CONTRIBUTING file warning contributors in bold to *"make
sure that the number of columns in the file has not changed"* — which is a
field-count check, one of the eleven refusals in the spec, written by hand by
people who had never seen it.

## Line 2 — prior art

The format ideas have real precedent and must be credited:

- **formula belongs to the column, not the cell** — Lotus Improv (1991),
  Javelin (1984), the OOPSLA 1986 analytic-spreadsheet paper, **ClassSheets**
  (ASE 2005), **Object Spreadsheets** (Onward! 2016), Analytica, Calculation
  View (VL/HCC 2018).
- **row identity for merge** — **Coopy/daff**, thirteen years of a shipping,
  row-ID-aware, git-integrated CSV three-way merge tool with `--id` and
  `daff git csv`. This is the closest prior art found anywhere.

The methodology has none. Checked and confirmed: jujutsu's merge tests assert on
trees, Pijul's correctness is purely algebraic, and **nbdime — the one strong
remaining lead, a VCS-integrated merge tool for an evaluable format — has no
execution machinery in its test suite at all** (no `ExecutePreprocessor`, no
kernel). The nearest neighbour in the literature is the Da Silva/Borba
semantic-conflict-via-tests line (ICSME 2020, JSS 2024), which runs project
tests over merged *general source code*, never a fixed conformance suite over
evaluated tabular values.

    Nobody does: check out two branches -> run stock `git merge` -> parse and
    EVALUATE the merged file -> assert on the computed number.

## Line 3 — the architecture itself

The namespace audit found 9 of 11 namespaces protected by parse-time validation
rather than co-location, and established that **CI is the only repo-resident
configuration a forge executes** — hooks are not cloned, merge drivers need
local config and are ignored by bare repos.

## What all three say

    The format is not the contribution. The merge is not the product.
    The conformance methodology and the validator are both.

- It is the one part with **no prior art** (line 2).
- It is the one part with **observed, hand-rolled demand** (line 1).
- It is the one part the **architecture actually depends on** (line 3).

And Coopy's own theory sharpens the point. Its author chose content-based row
matching and treated IDs as an optional optimisation. A mandatory opaque ID is
therefore a deliberate departure from the closest prior art, not a
rediscovery — but it is a departure that only pays off if something *enforces*
it. daff shipped the mechanism thirteen years ago and delivered it as a merge
driver, which this project measured to be undeployable. **The mechanism was
never the missing piece. The enforcement was.**

## The revised pitch

    WAS: a git-backed substrate for knowledge artifacts, whose tables merge
         correctly because they use nominal addressing.

    NOW: a specified format for tabular data in git, with a conformance suite
         that asserts on evaluated values after a real merge, and a validator
         that runs in CI. Correct merging is a property you get, not the reason
         to adopt it.

## What must be credited on the first commit

- **Coopy/daff** — direct ancestor of the merge problem and of row-ID merging;
  cite it and state the mandatory-ID divergence explicitly.
- **ClassSheets** (Engels & Erwig, ASE 2005) and **Object Spreadsheets**
  (McCutchen, Itzhaky & Jackson, Onward! 2016) — column/class-scoped formulas.
- **Lotus Improv** and **Javelin** — the historical root of named-dimension
  modelling.
- **org-mode `#+TBLFM:`** — twenty years of nominal column addressing in
  plaintext, and the most instructive negative control.

Four leads remain unverified and must not be cited specifically until they are:
Quantrix Modeler, Erwig's Gencel, and the exact Subtext "Schematic Tables"
post. (nbdime is now closed.)
