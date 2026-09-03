# Named-column vs positional addressing — full survey

Relayed sub-agent research, 2026-08-28. Sourced from direct doc fetches, repo
source, and APIs (GitHub, GitLab, dblp, OpenAlex, arXiv, Crossref, Zendesk) —
the agent's WebSearch budget was exhausted, so discovery was hypothesis-driven
rather than exhaustive. Verification labels are its own.

## Headline

Named-column relative addressing is **the dominant model in every system that
treats a table as a table** — Excel Tables, all seven database-spreadsheet tools,
all data tooling. It is **absent from every plaintext markup spec** (Quarto,
Typst, MultiMarkdown, djot, AsciiDoc). Positional A1 survives in legacy grids
and, tellingly, in *bolt-on markdown table-formula plugins that imitate them* —
which chose the fragile model despite a free hand.

So a git-backed suite adopting named columns is not making a novel bet. It is
adopting the mainstream, in a corner of the world that is the outlier.

## 1. Storage: names vs IDs — and why the no-code pattern is unavailable to us

| System | Stored form | Displayed | On rename | Evidence |
|---|---|---|---|---|
| Airtable | `LEFT(4, {fldXXXXXXXXXXXXXX})` | `LEFT(4, {Birthday})` | nothing breaks | VERIFIED, API field-model docs |
| Notion | property ID, `{{notion:block_property:...}}` | `prop("Priority")` / a pill | nothing breaks | VERIFIED |
| Teable | `{fldXXXXXXXX}` | `{Unit price}` | nothing breaks | VERIFIED — `formula.field.ts`, `ConversionVisitor` |
| NocoDB | dual: `formula` (ID) + `formula_raw` (names) | `{Qty} * {Price}` | nothing breaks | VERIFIED — `FormulaColumn.ts` |
| Grist | `$ColId`, derived via `sanitizeIdent()`, **untieable** | `$Quantity * $Unit_Price` | tied: rewrites dependents | VERIFIED — `FieldConfig.ts` |
| Baserow | **NAMES** in user-facing formula; derived `internal_formula` uses `field_{id}` | `field('Current Quantity')` | app rewrites the raw string | VERIFIED — `formula/handler.py` |
| **Excel** | **NAMES as literal text**: `Table1[[#This Row],[Qty]]` | same text | Excel rewrites dependents | REPORTED |

Airtable verbatim: *"The formula including fields referenced by their IDs. For
example, `LEFT(4, {Birthday})` in the Airtable.com formula editor will be
returned as `LEFT(4, {fldXXXXXXXXXXXXXX})` via API."*
Notion verbatim: *"`prop("Name")` matches a property by its current name, but the
saved formula references the property by ID, so renaming the property later
doesn't break the formula."*

**The trap.** Four of seven store an opaque ID and *project* a name for display.
That is only possible when a UI layer sits between the bytes and the human. **In
a plaintext git-backed format the file IS the UI.** A hidden ID destroys the
readability that is the entire point: `=col_a7f3 * col_9b21` in a markdown table
is worse than `=B2*C2` — positional addressing with the ergonomics removed.

So the ID pattern is unavailable, and that is fine: the two systems closest to a
plaintext model made the same choice we must. **Excel — the mainstream
named-column system, the one everyone's intuitions are calibrated on — stores
names as literal text in the formula.** Baserow does too. Both accept that
rename is a *refactoring that rewrites dependents*, not a no-op absorbed by
indirection.

**The failure mode to engineer against.** Baserow documents its own weak point:
deleting a referenced field errors the formula, and a listed remedy is literally
*"Rename another field to match the deleted field's name."* Because binding is by
name and the rewrite lives in an application code path, **any rename outside that
path — a restore, a botched import, a hand edit, a bad merge — silently strands
the formula.** In a git repo, edits outside the app are *normal*, not exceptional.

This makes it a **diagnostics** problem, not a storage problem: a formula
referencing a missing column must fail **loudly and locally** — an inline error
naming the missing column — never evaluate to zero, empty, or a stale cached
value. Silent wrong numbers are how positional addressing hurts people; named
addressing only wins if it refuses to guess.

## 2. Excel structured references — the precedent, precisely

Source: Microsoft "Using structured references with Excel tables" (VERIFIED).

Item specifiers: `#All`, `#Data`, `#Headers`, `#Totals`, and
`#This Row` / `@` / `@[Column Name]` — *"Just the cells in the same row as the
formula."* Cannot be combined with other specifiers.

`[@Qty]` = one cell, this row. `[Qty]` = the whole data column. Microsoft's own
examples: unqualified `=[Sales Amount]*[% Commission]` *"multiplies the
corresponding values from the current row"*; fully qualified
`=DeptSales[Sales Amount]*DeptSales[% Commission]`. Rule: unqualified inside the
table, qualified outside.

Range algebra works on names too: `=DeptSales[[Sales Person]:[Sales Amount]]`
(adjacent columns), comma for union, space for intersection.

Auto-expansion: *"Because table data ranges often change, cell references for
structured references adjust automatically."*

Two gotchas worth carrying:
- **One-row-table trap:** Excel converts `#This Row` to `@` only in tables with
  more than one data row; in a one-row table it doesn't, *"which may cause
  unexpected calculation results when you add more rows."*
- **Sideways copy has a relative/absolute axis:** `=table[@[amt]]` shifts column
  when copied across; `=table[@[amt]:[amt]]` is the absolute form. Even the named
  model keeps a relative/absolute distinction — just along columns, not rows.

### Google Sheets — the sharpest single data point in the survey

Sheets shipped Tables in May 2024 *with* structured references:
`Table1[Column 1]`, `Table1[[#ALL],[Column 1]]`, `#HEADERS`/`#TOTALS`/`#DATA`,
`=SUM(DeptSales[Sales Amount])`. But verbatim from Google's docs:

> **"Tip: `#This Row` currently is not supported."**

**Sheets adopted named-column *absolute* references and explicitly declined
named-column *relative* ones.** Sheets users doing per-row arithmetic still write
`=B2*C2` or spill an `ARRAYFORMULA`. The per-row named reference — exactly the
thing in question — is the piece the second-largest spreadsheet in the world has
not shipped. (Also: Sheets table refs don't work in conditional formatting,
charts, or pivot tables.)

## 3. The seven database-spreadsheet tools

**None has any positional or A1-style reference. No `B2`, no `$A$1`, no relative
offset anywhere in the category.** Coda says it outright: *"If you've ever used
Excel or Google Sheets, you may be used to using coordinates to pinpoint a cell.
In Coda, all objects have names. No coordinates needed!"*

| Tool | Same-row syntax (all VERIFIED) |
|---|---|
| Airtable | `{Qty} * {Price}`, `MIN({Regular Price}, {Sale Price})` |
| Notion 2.0 | `Reach * Impact * Confidence / Effort`, `prop("Priority") == "High"` |
| Coda | `thisRow.DueDate - today()`, `thisRow.Project.EndDate` |
| Grist | `$Qty * $Price` ≡ `rec.Qty * rec.Price` — real Python |
| Baserow | `field('Current Quantity') * field('Cost')` |
| NocoDB | `{Qty} * {Price}` |
| Teable | `{Unit price} * {Quantity}` |

Teable's grammar is a **fork of Baserow's** — `Formula.g4` opens *"Portions of
this file are based on Baserow software… The MIT License"*.

### Licences — three of four common assumptions are wrong

| Tool | Actual licence | OSI? | Stars | Last commit |
|---|---|---|---|---|
| Grist (`gristlabs/grist-core`) | Apache-2.0, clean | **yes** | 11,630 | 2026-08-27 |
| Baserow | MIT Expat core; `premium/`+`enterprise/` proprietary; docs CC BY-SA | core only | 5,742 (GitHub) | 2026-08-28 |
| Teable | split: `apps/*` AGPL-3.0, `packages/*` MIT, §7(e) brand terms | yes | 21,730 | `develop` 2026-07-29 |
| **NocoDB** | **Sustainable Use License v1.0 since 2026-01-08** (was AGPL-3.0) | **NO** | 64,773 | 2026-08-28 |

NocoDB relicensing confirmed in git history: commit `d98ad39c` (2026-01-08)
deletes the 661-line AGPLv3 file and adds `LICENSE.md`; `8264821b` (2026-01-29)
extends the grant to `develop`. SUL text: *"You may use or modify the software
only for your own internal business purposes or for non-commercial or personal
use."* Despite 64.7k stars and a "Free & Self-hostable" tagline, **do not group
it with the open-source options.**

Also: Baserow migrated GitLab→GitHub (the GitLab project now self-describes as a
mirror; use 5,742 stars, not 2,265). Teable's public repo lags its releases —
`develop` static since 2026-07-29 but a release cut 2026-08-19, head commits
prefixed `[sync]`, `main` stale since 2024-03-20. Development happens privately.

## 4. Plaintext markup specs — uniformly no computation

- **Typst** (v0.15.1, VERIFIED): `table()` takes a flat row-major sequence of
  cells plus `columns:` **track sizing**. No named column exists in the model,
  and **a cell cannot reference another cell** — cells are already-evaluated
  content by the time `table()` sees them. `fill`/`align`/`stroke` accept
  `(x, y) => …` callbacks but these are positional *styling* hooks that never see
  values. The `context`/`state()` escape hatch is explicitly ruled out by the
  docs: `state.rs` marks the running-computation use case *"This doesn't work!"*,
  and self-referential state *"might never converge… Typst simply gives up."*
  The intended design is: data in a file → computation in ordinary script →
  table as presentation.
  **Universe registry survey of all 1,554 packages** found exactly one genuine
  hit: **`tada`** (v0.2.0, Unlicense, 21★) — and it is named-column:
  `add-expressions.with(total: "price * quantity", tax: "total * 0.2")`,
  implemented as `eval(expr, mode: "code", scope: <row dict>)`. Critically it is
  **declaration-ordered, not a dependency graph** — reorder and it breaks.
- **Quarto** (VERIFIED): pipe/grid/list/HTML tables, alignment, captions,
  cross-refs. **No formula or cell-reference syntax.** Nuance: an inline code
  expression *can* sit in a cell because knitr substitutes `` `r expr` `` before
  Pandoc parses (confirmed locally with pandoc 3.1.11.1) — but it references
  R/Python variables, never other cells.
- **MultiMarkdown** (VERIFIED): colspan, alignment, captions; *"Cell content must
  be on one line only."* No computation feature anywhere in MMD6.
- **Djot** (VERIFIED): pipe tables, alignment, captions. Zero formula support.
- **AsciiDoc** (VERIFIED): cols specs, colspan/rowspan, CSV/TSV/DSV data. No
  calculation capability.
- **LaTeX `spreadtab`** (VERIFIED, v0.61 2025-03-14, LPPL, in TeX Live since
  2009): *"The cells of a table have **row and column indices** and these can be
  used in formulas"*, relative offsets `[-1,0]`. The one mature, long-lived
  plaintext table-formula system in the LaTeX world is **positional**.

## 5. Obsidian — 7,039 plugins surveyed, exactly one is named-column

**MarkCalc** (`levis-code/markcalc`, MIT, 2★, created and last pushed
2026-06-08) is the closest public design to a named-column markdown table:

    | Product | Qty | Price | Total |
    |---------|----:|------:|------:|
    | Coffee  | 2   | 3.5   |       |
    <!-- calc: $Total = $Qty * $Price ; $Pct = round($Total / sum(col("Total")) * 100, 1) -->

| Reference | Meaning |
|---|---|
| `$Column` | value in the **current row** |
| `${Column with spaces}` | same, names with spaces/accents |
| `col("Column")` | **array** of the whole column |
| `Column(N)` / `cell("Column", N)` | a specific cell, 1-based |
| `row` | current row index |

Design choices worth stealing or arguing with:
- Formulas live in an **HTML comment** (source of truth, idempotent) while
  **results are baked into the cells as real markdown**, so the file survives
  without the plugin and diffs cleanly. Its own comparison table claims exactly
  this against Dataview: *"Survives without the plugin / in Git."*
- **Structure-relative row access** instead of absolute indices: `up("Col")`,
  `down("Col")`, `runningSum("Col")`. A running balance is one column formula —
  `$Balance = up("Balance") + $Net` — not one formula per row.
- Conditional aggregates: `sumIf`, `countIf`, `avgIf`.
- Cross-note refs via `@name`-tagged tables plus `xcell`/`xcol`/`xlookup`/`xfm`,
  with a frontmatter dependency graph for cascade recalc without vault scans.
- Keeps a **positional escape hatch**: `Qty(4) = Qty(1) + Qty(2)`, explicitly
  documented as order-dependent.
- Declaration-ordered evaluation; `new Function` eval (DataviewJS trust level).

Everything else is A1/positional: CalcCraft (88★, `=b2*c2` plus `2c3r` relative
offsets, mathjs), Power Tables (`=SUM(D2:D11)`, 49 Excel functions), Table Calc,
Simple Table Formulas, Tabula, and Advanced Tables (189★, org-like `@`/`$`, **last
pushed 2024-09-05**).

**Obsidian Bases** (first-party, `.base` YAML) uses **bare property names** —
`price * quantity`, `note.` as an optional explicit prefix — but has **no column
aggregate or summary row** (verified absence, weaker than a positive statement).

## 6. The aggregate problem — "sum of this column"

Systems where a bare/named reference **changes meaning by context** — the same
shape as Kova's `!` footer row:

- **Excel.** `[@Qty]` = this row, `[Qty]` = whole column. Same name, two
  meanings, disambiguated by `@`. **This is the mainstream precedent**, with one
  difference: Excel marks the *this-row* case; Kova marks the *whole-column*
  case. **Kova's inversion is arguably better** — this-row is the common case and
  should be unmarked, and a footer row is a *positional context already visually
  distinct on the page*, so the mode switch is legible exactly where the reader
  is looking rather than encoded in a sigil they must know.
- **Typst `tada`** reached precisely the same context-dependent semantics
  independently: bare name = this row in row context, = whole column in `agg`.
- **MarkCalc** uses two syntaxes instead of a mode switch (`$Total` vs
  `col("Total")`) — more verbose, unambiguous, and lets one line mix both.
- **Grist** is strongest, and the only one that aggregates a column from inside
  an ordinary cell formula: `SUM(Materials.all.Price)`,
  `SUM(Orders.lookupRecords(SKU=$id).Qty)`, `SUM($group.AnnualPay)`,
  `SUM(r.AnnualPay for r in $group if r.EmploymentStatus == "Active")`.
  `Table.all.Column` yields a real value vector — the nearest thing to a
  spreadsheet range without being positional.
- **Miller (`mlr`)** puts aggregates in a *different namespace*: `$` per-record,
  `@` out-of-stream accumulators, `end {}` to emit.

Systems that **punt aggregation to a separate field type** — Airtable, Notion,
Baserow, NocoDB, Teable — cannot aggregate from inside a formula field at all;
all require a Rollup over a link/relation. Airtable's rollup takes `SUM(values)`
where `values` is a magic name for collected linked-record values, *not a column
reference*. This is a real ergonomic cost and a strong point for the footer row.

**vs org-mode:** `@I..@-1` is positional but **anchored to structure** (the
hline) rather than absolute rows, so it degrades more gracefully than pure A1 —
but still breaks if the hline moves or a second appears. A typed footer row takes
the same idea one step further: the anchor is a *typed row*, not a *rule glyph*,
so it survives reformatting.

## 7. Prior art worth knowing

**Lotus Improv** (NeXTSTEP Feb 1991, Windows May 1993, killed Apr 1996) is the
purest expression of this model, 35 years old. It **separated data from formulas
entirely**: *"Improv separated these concepts and used the cells only for input
and output data. Formulas, macros and other objects existed outside the cells, to
simplify editing and reduce errors."* And: *"Improv used named ranges for all
formulas, as opposed to cell addresses."* Canonical example:
`Total Sales = Unit Price times Unit Sales`. Descendants: Quantrix Modeler
(commercial, live) and **Apple Numbers**, which *"combines a formula and naming
system similar to Improv's, but running within a conventional spreadsheet."*

Improv failed commercially against Excel while keeping *"a strong following in
certain niche markets, notably financial and what-if computations."* **That is a
caution as much as a validation** — this exact design has lost this exact fight
once already.

**Miller (`mlr`)** is the strongest plaintext precedent: `mlr put '$total = $qty *
$price'` over CSV, `${field with spaces}`, `$*` for the whole record. It
**segregates positional access into deliberately awkward syntax** — `$[[3]]` is
the *name* of field 3, `$[[[3]]]` the *value*. Available, never the default.
Note the sigil convergence with MarkCalc and Grist: `$name` = this row's value.

**VisiData:** `=` creates an expression column, bare names are Python identifiers.
**dplyr / pandas / dbt / SQL:** `mutate(mass2 = mass * 2, mass2_squared = mass2 *
mass2)`; pandas `assign` docs state *"Later items in `**kwargs` may refer to newly
created or modified columns"* — same declaration-ordered semantics as MarkCalc
and `tada`. **SQL has no positional column reference in expressions at all**; the
only ordinals are `ORDER BY 1`/`GROUP BY 1`, the idiom every style guide warns
against because it breaks when the select list changes — A1's failure mode in
miniature.

## 8. Literature (see also findings/10)

Additions beyond findings/10:

- **Miller, Hermans & Braun, "Gradual structuring," VL/HCC 2016** (DOI
  10.1109/VLHCC.2016.7739696) + ITHET 2016 companion. Read in full. Proposes
  **semantic axes** — named, hierarchically nestable rows/columns addressed by
  path queries, e.g. `[Total][Jan:Apr]`. Classifies Excel Tables and Apple Numbers
  as **"weak forms"** of gradual structuring. **If you cite one paper, cite this.**
- **Hermans et al., ICSM 2012**, journal extension EMSE 20(2) 2015 (DOI
  10.1007/s10664-013-9296-2); tooling **BumbleBee, FSE 2014** (DOI
  10.1145/2635868.2661673). Companions: inter-worksheet smells (ICSE 2012), data
  clone detection (ICSE 2013 — the "no structural reference available, so paste
  the value" pathology), problematic lookup functions (VL/HCC 2015 — VLOOKUP as
  the archetypal fragile positional reference), delocalized plans (ICPC 2017).
  Framing survey: "Spreadsheets are Code," FOSE@SANER 2016.
- **Vlootman & Hermans, EuSpRIG 2013** (arXiv:1401.7814): of 26 weighted
  maintainability questions, five concern naming, including Q26 *"Does the model
  have absolute links or names towards other cells?"* The authors then
  self-criticise: *"the results might be biased since 4 questions in this category
  concern naming… In retrospect, this focus might be a bit heavy."* An honest
  instance of the naming-is-good prior being **asserted rather than measured**.
- **Xu et al., SpreadCluster, MSR 2017** (arXiv:1704.08476): users *"rarely use
  version control tools"*, so versions coexist as separate files and lineage must
  be recovered from *"similar table headers and worksheet names"* — from naming
  signals, not positions.
- **Frictionless Table Schema** (VERIFIED) addresses fields by `name` and has **no
  computed/derived/formula field concept at all**. Data-description standards name
  their columns and stop short of computing over them.
- **Standards keep structure optional.** ODF v1.3 Part 4 OpenFormula §4.8 defines
  a reference as *"the smallest **cuboid** that…"* — irreducibly geometric — with
  named expressions in a separate §5.11 whose support is **tiered out of base
  conformance**. OOXML has `ssml:definedName` and `ssml:tableColumn`. **Neither
  major standard treats the named reference as constitutive.**

## 9. Implications

1. Named-column relative addressing is **the mainstream; the plaintext world is
   the outlier.** The holdouts are legacy grids and markdown plugins imitating them.
2. **The strongest empirical support is SheetDiff, not the smells literature.**
   "Row inserted, or many cells edited?" is formally undecidable under positional
   addressing and trivially decidable under named addressing — stated by people
   who tried to build the diff tool and hit the wall.
3. **Abiteboul et al. gives the precise statement:** equal expressive power,
   different primitive operators. Positional addressing doesn't cost
   expressiveness; it costs cheap composition and correspondence — which is what
   merging *is*.
4. **Store names, and make broken references loud.** Excel stores names as literal
   text; so should we. Rename becomes a refactoring that rewrites dependents, and
   the imperative shifts to diagnostics.
5. **A `!` footer row is Excel's `@` with the markedness inverted, defensibly.**
6. **Copy two escape-hatch precedents:** Miller's deliberately awkward positional
   syntax, and MarkCalc's `up()`/`down()`/`runningSum()` — relative to *structure*,
   never to *coordinates*.
7. **Decide evaluation order explicitly.** MarkCalc, `tada` and pandas `assign` use
   declaration order (simple, predictable, silently order-sensitive); Excel and
   Grist build real dependency graphs with cycle detection. Live design choice.
8. **Pre-empt McKeever/McDaid** (see findings/10). The defence is Miller &
   Hermans': a named range is pure indirection — *"not much more than an alias"* —
   whereas a column-header reference has **no indirection**, since the name is
   printed at the top of the column the reader is already looking at. `=qty * unit`
   is closer to a struct field access than to a named range. Make that argument
   before a reader finds the literature.

## Gaps — do not assert these

WebSearch budget was exhausted for the whole session; discovery was
hypothesis-driven and negative GitHub search results are weak evidence, not proof
of absence. Unverified: Apple Numbers' exact syntax (SPA docs); Quantrix Modeler's
syntax (vendor docs 404); Coda rename stability; a literal Coda `.Sum()`; Teable
and Notion rollup mechanics; Baserow's `sum(lookup(...))` wrapping; Excel
column-rename auto-update and the Total Row's `SUBTOTAL(109,…)` form; ECMA-376
Part 1 normative prose; ODF Part 3 §9.4.12/13 body text; RefBook's seven
refactorings.

Discarded source: a WebFetch summary claiming Baserow uses `[Quantity] *
[Unit Price]` was confabulated from a client-rendered page serving only nav
chrome. Baserow uses `field('name')`, confirmed against the ANTLR grammar.
