# Nimbalyst on-disk formats — primary source

Verified against `nimbalyst/nimbalyst` @ main via the GitHub API on 2026-08-28.
Repo: MIT, 1,595 stars, pushed 2026-08-28. Formerly **Crystal** (`stravu/crystal`,
3,113 stars, renamed ~Feb 2026). 28 first-party extensions in-tree plus ~30
third-party ones on GitHub.

This answers the question left open by the competitor sweep: **where do the
formulas live?**

## There are TWO spreadsheet extensions, with different formats

### 1. `csv-spreadsheet` — real CSV, formulas in-cell, metadata in a header comment

`packages/extensions/csv-spreadsheet/`, v1.3.0.
Stack: RevoGrid (MIT) + **@formulajs/formulajs** (MIT) + PapaParse + Zustand.

Formulas are A1-style (`=SUM(A1:B10)`), evaluated by formula.js against a
**static allowlist** of functions — the source comment says "Static by design:
dependency upgrades cannot silently expose new formula.js code." Roughly 100+
functions allowed (logical/lookup/info, arithmetic/trig, text, statistical).
There's a real dependency graph (`FormulaNode`, `dependencies: Set<string>`),
cycle detection via `activeCells`, and evaluation limits (`FORMULA_LIMITS`).

Formatting, header rows, frozen columns, column widths and cell styles are
persisted as **a single-line JSON comment on line 1 of the .csv**:

    # nimbalyst: {"hasHeaders":true,"headerRowCount":1,"frozenColumnCount":0}
    Product,Category,Q1 Revenue,Q2 Revenue,...
    Cloud Platform,Infrastructure,1250000,...

(verified: `csvParser.ts` `METADATA_PREFIX = '# nimbalyst:'`, and
`samples/demo.csv` opens with exactly that line.)

**Assessment.** No sidecar file — one artifact, nothing to lose. And because the
formula text is what's stored, Excel and Sheets will re-evaluate it on import
rather than seeing a dead value. But the tradeoffs are real:

- Vanilla CSV consumers do **not** skip `#` comments. Excel shows the metadata
  line as a data row; pandas needs `comment='#'`. It breaks plain-CSV interop
  precisely where CSV's value is.
- The metadata is one minified JSON line, so any formatting change rewrites that
  whole line. Contained (one line), but unreadable in a diff and merge-hostile.
- A1 references break silently when rows are inserted or reordered — the classic
  problem, and the thing Kova's named-column model deliberately avoids.

### 2. `calc-sheets` — `.calc.md`, line-oriented, unit-aware. The interesting one.

`packages/extensions/calc-sheets/`, v1.0.2. Own `parser.ts`, `evaluator.ts`,
`lineClassifier.ts`, `calcSheetSyntax.ts`, Monaco-based editor, Yjs collab adapter.
Self-described as "Line-based worksheets instead of grid-heavy spreadsheets."

From `samples/demo.calc.md` (verbatim):

    ---
    title: Falcon 9 Rocket Equation
    display:
      decimals: 1
    ---
    # Falcon 9 Rocket Equation
    // Approximate Falcon 9 Block 5 numbers for a simple two-stage model.

    ## Mission Inputs
    payload = 15500 kg
    target_orbit_delta_v = 9400 m / s

    ## Vehicle Assumptions
    g0 = 9.80665 m / s^2
    stage1_isp = 282 s

    ## Stage 1 Burn
    stage1_initial_mass = stage1_dry_mass + stage1_propellant + payload
    stage1_delta_v = to(stage1_isp * g0 * log(stage1_initial_mass / stage1_final_mass), "m / s")

    ## Mission Check
    payload_fraction_of_liftoff_mass = payload / stage1_initial_mass -> percent(2)
    assert stage2_propellant_remaining > 0 kg

Features: named variables (no cell addresses at all), **unit-aware arithmetic**
with dimensional checking (`kg`, `m / s`, `s^2`, `to(...)` conversion),
`->` output formatters (`percent(2)`, `currency(USD, 2)`), `assert` statements,
`//` comments, markdown headings as section structure, YAML frontmatter for
display defaults. Results render in a live gutter and are **never written to the
file** — the source keeps only formulas.

**Assessment.** This is the best git-shaped design of the three I've found. Every
line is an independent, self-describing statement, so a diff shows exactly which
assumption changed; two people editing different sections merge cleanly with
stock git; and an LLM can read and edit it with no tooling. Its cost is that it
is not a grid — it models calculations, not tabular data. Soulver/Numi/Calca in
a file, essentially.

## Slides

`.slides.md` — YAML frontmatter plus `---`-separated markdown, rendered via
reveal.js. A sample is committed at `design/transcript-embed-samples/launch.slides.md`.
Note there is **no slides package under `packages/extensions/`** — the three
spreadsheet/slides legs are not symmetric in maturity.

## Why this matters strategically

My earlier read — "sheets is the unsolved piece, nobody ships CSV plus formulas"
— **is wrong as stated.** Three shipped designs now exist:

| Design | Shape | Addressing | Diff quality | Interop |
|---|---|---|---|---|
| Nimbalyst `csv-spreadsheet` | grid, real .csv | A1 refs | good for cells, bad for the metadata line | breaks on the `#` line |
| Nimbalyst `calc-sheets` | line-oriented .calc.md | named variables + units | excellent | none (bespoke) |
| Kova `!sheet` | GFM markdown table | named columns, relative | excellent | it's just a markdown table |

What is genuinely still open is not "can formulas live in plaintext" — they can,
three ways — but **whether anyone has made one of these good enough to replace a
real spreadsheet**, and whether a single product carries docs + sheets + slides
in one coherent repo for a non-developer audience. Nimbalyst has all three legs
but sells to developers orchestrating coding agents; Kova is a deck tool that
grew a formula feature; Pithy had the right audience and stopped shipping.

The named-addressing insight (Kova's columns, calc-sheets' variables) is the real
finding: **A1 references are the thing that makes spreadsheets un-diffable**, and
both of the good designs threw them out.
