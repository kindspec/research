# Spreadsheets as diffable plaintext in git

Research date: **2026-08-28**. Claims are labelled **[V]** verified (I read the spec, the
source, or the licence file), **[V-LOCAL]** verified by an experiment I ran on this machine
(LibreOffice 25.2.3.2, git 2.47.3, Debian 13), or **[R]** reported (secondhand, single
source).

Companion documents: `08-nimbalyst-formats.md` (primary-source read of Nimbalyst's two
spreadsheet formats — not duplicated here, cross-referenced throughout).

---

## TL;DR

**The hard part is not storing formulas as text. Three shipped products already do it three
different ways. The hard part is that `A1`-style cell references are positional, and
positional references cannot survive a distributed merge.**

I tested that claim rather than assuming it, and it is worse than the usual framing. Two
branches inserting a row into the same sheet, far enough apart that **git auto-merges with
no conflict at all**, produced a spreadsheet whose total was **480 instead of 660** — a 27%
error, silently, with no marker anywhere. [V-LOCAL, §A12]

**Recommendation: make named-column addressing the default, and ship more than one file
type — because "spreadsheet" is three unrelated jobs (§7.3).**

1. **`.sheet.md` — a GFM table with a `!sheet` directive and named-column formulas**
   (Kova's design). The **primary format**, covering most real spreadsheets. `=qty * unit` is
   invariant under row insert, delete and reorder, so it diffs at one line per row and merges
   correctly with stock git. It is also the format an LLM handles best, by a wide margin.
   Keep the syntax, **replace the 11-function evaluator with IronCalc's 495**.
2. **`.fods` — flat XML ODF** as the **fidelity format**, for anything needing real
   formatting, charts, or an Excel hand-off. A single standards-defined XML file that
   LibreOffice pretty-prints at ~3 lines per cell — and that verbosity buys **cell-level
   three-way merge from stock git with no merge driver**, which CSV structurally cannot have.
   [V-LOCAL, §A7] Ship the canonicalisation filter in §7.2 with it or it will commit the
   user's printer name on every save.
3. **`.calc.md` — line-oriented named variables with units** (Nimbalyst's design) for
   **models** rather than tables. Different job, different shape; the diff names the
   assumption that changed.

**Do not build on CSV + a formula sidecar.** I demonstrated the failure directly: the two
files merge independently, and git has no mechanism to keep an `A1`-keyed sidecar in sync
with row insertions in the CSV. [V-LOCAL, §A8]

**Do not build on HyperFormula without a legal decision.** It is **GPL-3.0-only** with a
paid proprietary alternative — not MIT, as widely repeated (including in this project's own
earlier `RESEARCH.md`). [V] Use **IronCalc** (MIT OR Apache-2.0, 495 functions, more than
HyperFormula, with spill and `LAMBDA` that HyperFormula lacks).

**The most useful thing I found**: named-column addressing is not a markdown-tool invention.
**Excel's own Tables already work this way** — `=[@Qty]*[@Unit]`, `=SUM(Table1[Total])`,
`#This Row` — added on top of A1 precisely because A1 does not survive row insertion. [V]
So the model is proven at scale, *and* it means a `.sheet.md` table can export to a real
Excel Table with structured references, preserving formula **meaning** rather than shipping
dead values (§6.7). That is a better interop story than any competitor has.

---

## 1. Why CSV is not enough, precisely

CSV holds values. It cannot hold formulas, number formats, styles, column widths, multiple
sheets, frozen panes, data validation, or charts. Everything below is an attempt to keep
some of that while staying diffable.

Two structural facts govern the whole design space:

**Fact 1 — diffability and fidelity trade off almost perfectly.** Every format that diffs
beautifully (Markdown tables, org-mode, `.sc`, `.calc.md`, marimo `.py`) buys it by
*discarding formatting and charts*. Every format that keeps them is either binary
(`.grist`, Quadratic `.grid`) or index-keyed nested JSON (Univer). `.fods` is the only
format surveyed that sits on both sides. [V]

**Fact 2 — the merge granularity you get is the line granularity you emit.** Git merges
lines. A CSV row is one line, so two people editing different *columns* of the same row is
an unavoidable conflict. A format that puts each cell on its own line gets cell-level merge
for free. I measured this both ways. [V-LOCAL, §A7]

---

## 2. Formats — comparison

| Format | One file? | Diff quality | Formulas | Addressing | Formatting | Charts | Excel/Sheets | LLM can edit raw | Status |
|---|---|---|---|---|---|---|---|---|---|
| **`.fods`** flat ODF | ✅ one XML | ✅ ~3 lines/cell, pretty-printed | ✅ OpenFormula | **A1** (`[.B2]`) | ✅ full ODF | ✅ | ❌ native; ✅ 1-cmd convert | ✅ [V-LOCAL] | OASIS standard, LO-native |
| **Kova `!sheet`** GFM table | ✅ `.md` | ✅✅ 1 row = 1 line | ✅ 11 fns | **named column** | ❌ | ❌ | ❌ (it's a md table) | ✅✅ | shipping, GPL-3.0 |
| **Nimbalyst `.calc.md`** | ✅ `.md` | ✅✅ 1 stmt = 1 line | ✅ + units | **named variable** | ❌ | ❌ | ❌ | ✅✅ | shipping, MIT |
| **Nimbalyst `csv-spreadsheet`** | ✅ `.csv` | ✅ cells / ❌ metadata line | ✅ ~100 fns | **A1** | via JSON line 1 | ❌ | ⚠️ breaks (see §3.4) | ✅ | shipping, MIT |
| **sc-im `.sc`** | ✅ | ✅✅ 1 cell = 1 line | ✅ own `@` dialect | **A1** | ✅ terminal-level | ❌ | via its xlsx export | ✅✅ | 5.7k★, active |
| **org-mode `#+TBLFM:`** | ✅ | ✅✅ 1 row = 1 line | ✅ Emacs Calc, rich | **positional** `$1` `@2$3` | ❌ | ❌ | ❌ | ✅✅ (can't evaluate) | Emacs-only |
| **md-advanced-tables** | ✅ | ✅✅ | ⚠️ weak (sum/mean) | positional | ❌ | ❌ | ❌ | ✅✅ | MIT, 2024 |
| **`.xlsx` unzipped** | folder | ⚠️ single-line XML | ✅ | A1 | ✅ | ✅ | ✅✅ native | ⚠️ | niche, tooling stale |
| **`.xlsx` committed as-is** | ✅ | ❌ binary | ✅ | A1 | ✅ | ✅ | ✅✅ | ❌ | universal but opaque |
| **Univer JSON snapshot** | ✅ | ❌ index-keyed, volatile viewport | ✅ | A1 | ✅ via id indirection | escaped strings | paid tier | ⚠️ | Apache-2.0 |
| **`ses.el`** | ✅ | ❌ newline-position-sensitive | ✅ elisp | A1 | ~ | ❌ | ❌ | ⚠️ | Emacs, unused |
| **Grist `.grist`** | ✅ | ❌ SQLite binary | ✅ Python | **named column** | ✅ | ✅ | export only | ❌ | Apache-2.0, 11.6k★ |
| **Quadratic `.grid`** | ✅ | ❌ zstd(JSON) binary | ✅ | A1 | ✅ | ✅ | ❌ | ❌ | **repo withdrawn** |
| **GridHub `.grid`** | ZIP | ❌ (text inside) | ✅ split csv | A1 | JSON sidecar | ❌ | ❌ | ❌ | **dead 2014, unlicensed** |
| **Frictionless / CSVW / CSVY / `.csvs`** | folder or one | ✅ CSV / ❌ descriptor | **❌ none** | — | ❌ | ❌ | ❌ | ✅ | see §3.5 |
| **SQLite (raw, in git)** | ✅ | ❌ binary, unmergeable | n/a | — | — | — | ❌ | ❌ | [V-LOCAL] |
| **marimo `.py`** | ✅ | ✅✅ | ✅ full Python | named | ❌ | code | ❌ | ✅✅ | Apache-2.0, 22.5k★ |

### 2.1 Notes on the leading candidates

**`.fods` is a real standard, but `.fods` is not.** The single-XML representation is
normative ODF — ODF 1.3 part 3 §3.1.2, conformance clause C: root element must be
`<office:document>`. But the strings `fods` and `flat XML` appear **zero times** in the ODF
spec. The *format* is standardised; the **extension and MIME type are LibreOffice
conventions**. [V] Siblings `.fodt` / `.fodp` / `.fodg` exist with the same filters. [V]

Evidence of real use: GitHub code search returns ~112 `.fods` files, overwhelmingly
**LibreOffice's own regression test corpus** (`sc/qa/unit/data/fods/`). LibreOffice trusts
it enough to keep hundreds of fixtures in git — but there is no broad ecosystem of people
keeping working books in it. [V]

**Kova's `!sheet` is a small but genuinely engineered implementation.** [V] I read the
source: `src/engine/sheet/` is **555 lines** across `lexer.ts` (49), `parser.ts` (128),
`evaluate.ts` (164), `sheet.ts` (162), `constants.ts` (52), with **63 tests**. It is a
proper recursive-descent parser with seven precedence levels, strings, booleans, `and`/`or`/
`not`, a ternary, memoised evaluation and **cycle detection** (`circular reference in column
'x'`). Details in §5.

**`.calc.md` has strong open prior art that Nimbalyst does not cite: Numbat.** See §5.3.

---

## 3. Format detail

### 3.1 Flat ODF `.fods` — the fidelity option

Formulas are stored as an attribute in ODF OpenFormula syntax, with the computed result
cached beside them:

    <table:table-cell table:formula="of:=[.B2]*[.C2]" office:value-type="float" office:value="25">
     <text:p>25</text:p>
    </table:table-cell>

Note ODF uses `;` as the argument separator, not `,`, and the `of:` prefix inside the
attribute value is a **real namespace prefix** — omit `xmlns:of` from the root element and
every formula silently becomes `Err:510`. I hit this. [V-LOCAL, §A3]

The strong result: **LibreOffice recalculates ODF formulas on load, so the cached values are
optional.** A `.fods` whose formula cells carry no cached result at all loads and computes
correctly. [V-LOCAL, §A2] That permits a *canonical, cache-free* form with no redundant
state to go stale — which matters because it also removes the whole class of "the diff shows
the value but not the formula" confusion.

⚠️ **Important precision.** This is an **ODF** behaviour and does **not** generalise to
`.xlsx`. For OOXML, LibreOffice defaults to `OOXMLRecalcMode=1` = *never* recalculate, and
will happily emit a falsified cached value. Both registry keys default to `1`; the ODF key's
own description scopes it to *"non-LibreOffice-generated ODF documents"*. Empirically, every
`.fods` I fed LibreOffice recalculated correctly — with a LibreOffice generator string, with
an alien one, with a deliberately falsified cache, and in a fresh user profile. [V-LOCAL]
**The robust design is to emit no cached values at all**, which makes the question moot.

The three real problems, all measured, all fixable:

1. **Machine state leaks into the file.** A no-op re-save injects the local **printer name
   and a ~700-char base64 `PrinterSetup` blob** naming your paper size and driver. Two
   developers on different machines churn it forever. [V-LOCAL, §A5]
2. **Auto-style-name churn.** A single value edit can rename a cell style `ce2`→`ce1` and
   drop a style block. LibreOffice does no style deduplication and keeps no stable names.
   [V] `fods_minimizer` (BSL-1.0, active 2026-07) exists solely for this and claims ~60%
   size reduction. [V]
3. **Run-length encoding splits on edit.** ODF collapses identical rows with
   `table:number-rows-repeated="22998"` — LibreOffice's own 23,000-row fixture is **2,315
   bytes**. Editing one row inside a repeated run splits it into three elements: a
   structural diff, not a one-line diff. [V]

I wrote and tested a **git `clean` filter that reduces the churn to zero** across repeated
LibreOffice saves. Script and results in §A5 / §7.2.

**Interop:** Microsoft's supported-formats page lists `.ods` and has **no entry for
`.fods`**. [V] No evidence Google Sheets imports it. So Excel/Sheets interop is a
one-command LibreOffice conversion, which I verified preserves formulas, sheet names and
styles in both directions. [V-LOCAL, §A10]

### 3.2 `.xlsx` — committed whole, or unzipped

**Committed whole it is unusable**: not only binary, but *non-deterministic* — building the
same workbook twice from identical input yields byte-different zips because entries embed
mtimes. [V] Every save is a churn commit.

**Unzipped it is still bad without a pretty-printer**: every OOXML part is a **single line**
(`xl/worksheets/sheet1.xml`: 1 line, 2,810 bytes). [V-LOCAL, §A6] Plus `sharedStrings.xml`
indirection — cell text is an integer index, so editing one label changes two files and can
renumber every later index.

One precision worth having: **`calcChain.xml` churn is an Excel problem, not an OOXML-
universal one.** LibreOffice-written `.xlsx` contains no `calcChain.xml` at all. [V-LOCAL]

The counter-intuitive measurement: over 21 commits each changing one cell of a 10,000-cell
sheet, `.git` grew to **212 K (csv), 268 K (fods), 1012 K (xlsx)**. `.xlsx` is 20× smaller
as a single file yet costs **3.8× more in the repo**, because a zip delta-compresses against
its predecessor essentially not at all. **Verbose text is cheaper in git than compact
binary.** [V-LOCAL, §A9]

Tooling is real but stale: `scholer/ooxml-git-hooks` (GPL-3.0, **last push 2018**) implements
explode/recreate properly; `dilshod/xlsx2csv` (MIT, pushed 2026-08-21) is the one genuinely
live dependency in the ecosystem. [V]

### 3.3 sc-im `.sc` — the best line diff of any real spreadsheet format

`andmarti1424/sc-im`: **5,690★, pushed 2026-08-26**, C, licence `NOASSERTION`. Actively
maintained. [V] One command per cell, one per line:

    format A 14 2 0
    leftstring C3 = "algo de ñandú"
    let C2 = 2+A3
    let H5 = @sum(A0:A0)
    fmt D22 "###,###.000"
    color "type=HEADINGS fg=BLACK bg=YELLOW bold=0"
    newsheet "DOS"

Multiple sheets, per-cell number formats and colour, CSV/TSV/**XLSX** import and export, ODS
import. [V] An edit is a true one-line diff. Its weakness for this project is the addressing
model — `let C2 = 2+A3` is A1-positional, so it inherits every problem in §6 — and its
formula dialect is its own, not Excel's.

### 3.4 Nimbalyst's two formats

Fully written up in `08-nimbalyst-formats.md`; two additions from my own testing.

**`csv-spreadsheet`'s metadata line is worse than "a stray row".** The design puts a
single-line JSON comment on line 1 of the `.csv`:

    # nimbalyst: {"hasHeaders":true,"headerRowCount":1,"frozenColumnCount":0}

Because minified JSON **contains commas**, a standard CSV parser splits that line into
*three fields*. Python's `csv` module reads it as `['# nimbalyst: {"hasHeaders":true',
'headerRowCount:1', 'frozenColumnCount:0}']`, and LibreOffice imports it as a 3-cell row —
**widening the whole sheet to three columns**. It doesn't just add a junk row, it corrupts
the table's shape. [V-LOCAL]

**`.calc.md` merges exactly as advertised.** Two branches editing two different assumptions
merged cleanly, and each change shows as a single `-`/`+` line pair naming the assumption.
[V-LOCAL] It is the best-behaved format I tested, at the cost of not being a grid.

### 3.5 The tabular-data standards carry no formulas at all

| | status | shape | formulas |
|---|---|---|---|
| **Frictionless Data Package v2** | alive, v2 released 2024-06-26 | folder: `datapackage.json` + CSVs | ❌ |
| **CSVW** (W3C) | **4 RECs, all 2015-12-17; `w3c/csvw` repo archived** | `data.csv` + `-metadata.json` | ❌ |
| **CSVY** | **no maintainer; csvy.org is off the air (404)**; repo last push 2018-11-19 | YAML front matter + CSV | ❌ |
| **`.csvs`** (UK Nat. Archives) | alive, 1.4.3 released 2026-01-06 | a *validation DSL*, holds no data | ❌ |

[V] This is a genuine, unfilled gap: **no text-first tabular standard has ever specified a
formula.** They are all data-plus-types. Frictionless is the hub (Grist even emits
Frictionless descriptors); CSVW is the standardised-but-abandoned alternative; `.csvs` is
orthogonal.

### 3.6 Dead ends, named so nobody re-researches them

- **Quadratic** — `quadratichq/quadratic` is **404** (withdrawn, not a rate-limit artifact).
  The org survives. Format was `bincode header + zstd(JSON)` — binary regardless. [V]
- **GridHub** — 14★, **last push 2014-12-03, no licence** (so not legally reusable),
  built on **node-webkit**. And the widely-repeated description is half wrong: a `.grid`
  is a **ZIP**, not a folder, containing `formulas.csv` + `values.csv` + `styles.json` per
  numbered sheet folder — plus, as a gimmick, **a `.git` directory inside the zip**. [V]
  The one idea worth stealing is splitting `formulas.csv` from `values.csv`, so the formula
  layer diffs independently of recomputed values.
- **`ses.el`** — writes *every* cell including empties (`(ses-cell A2 nil nil nil nil)`), and
  the manual forbids changing line counts because it locates cells by counting newlines.
  A merge that shifts one line corrupts the file. Disqualified. [V]
- **Obsidian Dataview** — a query engine, not a format; its docs state it *"will always
  leave [your notes] untouched"*, so computed tables exist only in the rendered view and
  never reach git. [V]

### 3.7 The markup languages have no table formulas at all

Worth stating so nobody goes looking:

- **GFM** defines only header, alignment delimiter and data rows — **no computation**. [V]
  Every markdown table formula system surveyed here (Kova, md-advanced-tables, Obsidian
  plugins) is an **extension in an HTML comment or a directive line**, not part of any spec.
- **Typst** has no in-table cell formulas. The nearest thing is
  `patrick-kidger/tableframe` — *"a simple columns-and-tables dataframe library for
  Typst"*, **Apache-2.0, v0.1.0, 1★, first pushed 2026-08-28** — and even that is
  programmatic column algebra (`(table.col)("Prop")`, method chaining), **not** cell
  formulas. Typst is a good *report* target and a poor *calculation* substrate. [V]
- **Quarto** computes via code chunks that *emit* a table; there are no formulas *in* the
  table. [V/R]
- **MultiMarkdown** and **Djot** define table syntax with no formula support. [R]

The practical consequence: whatever you build, the formula layer will be **your extension**.
That is an argument for adopting an existing shipped convention — Kova's `!sheet` — rather
than inventing a fourth one.


---

## 4. Calc engines — comparison

Licences below were verified from the raw `LICENSE` file and/or npm/PyPI/crates.io registry
metadata, **not** the GitHub API, which is wrong or unhelpful for five of these. [V]

| Engine | Licence (verified) | Last commit | ★ | Functions | Status | 2026 viability | Key gotcha |
|---|---|---|---|---|---|---|---|
| **HyperFormula** | **GPL-3.0-only OR proprietary** — `LICENSE.txt` + npm `"GPL-3.0-only"` | 2026-08-28 | 2,772 | **423** (350/515 Excel = 68%) | Healthy, corporate, v3.4.0 | ✅ most mature JS | 🔴 **GPL.** Price unpublished. No spill, no LAMBDA, no Tables, no 3D refs |
| **IronCalc** | **MIT OR Apache-2.0** — both LICENSE files; crates.io/npm/PyPI agree | 2026-08-28 | 4,125 | **495** (all with dispatch arms) | Very active, v0.8.3, 3 maintainers | ✅ **best licence/capability trade** | 🟡 pre-1.0; ~1% of HF's adoption; pin exact versions |
| **Univer** | **Apache-2.0** — LICENSE + npm on `engine-formula`/`core`/`sheets-formula` | 2026-08-28 | 14,233 | **~502** | Very active, v0.25.1 | ✅ safest permissive JS at scale | Full framework (canvas/DI/plugins); Pro tier is *performance*, not function set |
| **@formulajs/formulajs** | **MIT** — LICENSE + npm (API's `NOASSERTION` is a false alarm) | 2026-07-28 | 819 | 398 exports | Active, v4.6.1 | ⚠️ as a function pack only | 🔴 **not an engine** — no cell refs, no dependency graph, no recalc |
| **excelize** (Go) | **BSD-3-Clause** | 2026-08-26 | 20,871 | 456 | Very active | ✅ under-discussed | No incremental dependency graph; no array formulas |
| **Formualizer** (Rust) | MIT OR Apache-2.0 | 2026-08-25 | 171 | 400+ | Very active | 🟡 watch | 🔴 **bus factor 1** (1,117/1,200 commits, one author) |
| **formulas** (Python) | **EUPL-1.1+** ⚠️ | 2026-08-07 | 502 | **483/536 = 90.1%** | Slow (1 commit/90d) | ⚠️ legally hazardous | 🔴 EUPL has an **AGPL-style network trigger** — see below |
| **pycel** | GPL-3.0 | 2026-03-02 | 630 | ~110 | Life support | ❌ | `pip install pycel` gets **`1.0b30` from 2021** |
| **xlcalculator** | MIT | 2023-12-18 | 161 | ~100 | Dormant | ⚠️ | only non-copyleft pure-Python option, but thin and quiet |
| **koala2** (`anthill/koala`) | GPL-3.0 | — | 159 | — | **Abandoned** — last PyPI 2019-06-19 | ❌ | seven years stale |
| **fast-formula-parser** | MIT | 2025-09-10 (README only) | 521 | 280 | **EOL** — last code 2024-06; last npm **2020-11-26** | ❌ | README points to `@sheetxl/formulas`, which is **$745/dev/yr commercial** |
| **SheetJS `xlsx` CE** | **Apache-2.0 — unchanged** | GitHub frozen 2024-04-18 | 36,332 (stale mirror) | **0 — does not calculate** | Alive, **off GitHub** | ⚠️ I/O only | 🔴 npm frozen at **0.18.5 (2022)** with **two unpatched CVEs** |
| **ExcelJS** | MIT | 2025-01-21 | 15,454 | **0 — does not calculate** | **Dormant** — 0 commits since 2025-06 | ❌ | you must supply `result` yourself |
| **openpyxl** | MIT | active | — | **0 — does not calculate** | Healthy | ✅ I/O only | `data_only=True` returns **`None`** if Excel never opened the file |
| **Luckysheet** | MIT | 2025-08-19 | 16,647 | — | **ARCHIVED** | ❌ | superseded by Univer — the star count misleads |
| **LibreOffice headless** | **MPL-2.0** (not the GPL the API reports) | rolling | — | best-in-class Excel fidelity | Active | ⚠️ batch only | see §4.3 — **the defaults fail silently three ways** |

### 4.1 HyperFormula's licence — the correction that matters most

This project's own earlier `RESEARCH.md` says *"HyperFormula — MIT headless spreadsheet
engine."* **That is wrong**, and it is wrong in most blog posts too. Verified from
`LICENSE.txt` and npm:

> "This software is **dual-licensed**, giving you the option to use it under either a
> **proprietary license** or the **GNU General Public License version 3 (GPLv3)**. The
> specific license under which you use the software is determined by the license key you
> apply." — `LICENSE.txt`, Handsoncode sp. z o.o. [V]

npm `hyperformula@3.4.0` declares `"license": "GPL-3.0-only"`. [V] A `licenseKey` is
**mandatory** at runtime; GPL users pass the literal string `'gpl-v3'`.

It was **never MIT and never LGPL**. History from `LICENSE.txt` at each tag: [V]

| Period | Licence |
|---|---|
| v0.1.0 – v0.6.2 (2020-06 → 2021) | **Triple**: non-commercial / commercial / **AGPL-3.0** |
| v1.0.0 – v2.0.x (2021 → 2022) | **Dual**: commercial / **GPL-3.0** — *AGPL dropped* |
| 2024-07-17 (PR #1422) → today | current dual GPLv3 / proprietary preamble |

The one substantive change is **AGPL-3.0 → GPL-3.0 at v1.0.0**, which matters: pure
server-side SaaS no longer triggers source disclosure by itself. **Commercial price is
published nowhere** — sales contact only. For calibration, sibling product Handsontable
lists $999–$1,299/dev/yr. Treat it as a negotiated, long-lead item.

**Handsontable itself went non-free at v7.0.0 on 2019-03-06** (v6.2.2 and earlier were MIT).
Current terms are free only for *"strictly personal or solely for evaluation purposes"*,
with **no GPL escape hatch at all**, plus an explicit non-compete: *"you must not make any
such use of this software as to develop software which may be considered competitive with
this software."* [V] **For a git-backed spreadsheet product, that clause bars the use case
directly.**

### 4.2 Four widely-cited "engines" do not calculate

**SheetJS CE, ExcelJS, openpyxl and Formula.js** all fail to evaluate formulas. [V]

- **SheetJS** stores the formula string in the cell's `f` field and stops. Their docs:
  *"If the actual results are needed in JS, **SheetJS Pro offers a formula calculator
  component**."* Calculation is a paid add-on, never in CE.
- 🔴 **SheetJS security, act on this**: the licence never changed (still Apache-2.0), but
  the project **left GitHub for a self-hosted Gitea** (final commit "exit stage left",
  2024-02-01) and **stopped publishing to npm**. npm `xlsx` is frozen at **0.18.5
  (2022-03-24)** carrying **CVE-2023-30533** (prototype pollution, CVSS 7.8) and
  **CVE-2024-22363** (ReDoS). **Both fixes exist only on `cdn.sheetjs.com`.** The GitHub
  repo is not archived, so it still reads as alive at 36k stars — it isn't. If `xlsx` is
  anywhere in your tree, including transitively, it needs a `package.json` `overrides`
  entry pointing at the CDN tarball.
- **openpyxl**'s `data_only=True` returns the value cached *the last time Excel opened the
  file*. If the file was written by openpyxl and never opened in Excel, **you get `None`**.
- **Formula.js** is genuinely MIT (398 exports) but has no cell references, no dependency
  graph and no recalculation. It is a function pack for someone else's evaluator.

### 4.3 `formulas` (Python) is EUPL — with an AGPL-style network trigger

The best pure-Python coverage (483/536 = 90.1%) comes with the trap most people miss.
EUPL-1.1 defines distribution as including *"providing access to its essential
functionalities at the disposal of any other natural or legal person"*, **"on-line or
off-line"**. [V] Putting it behind a web API is therefore a communication that triggers the
copyleft — it behaves like AGPL, not GPL. Note too that EUPL-1.1's compatibility appendix
lists GPL v2, OSL, CPL, EPL and CeCILL, but **neither GPLv3 nor AGPL**; those arrived only in
EUPL 1.2, which this project has not adopted. Get counsel before shipping commercially.

**The clean Python answer in 2026 is `pip install ironcalc`** — MIT/Apache-2.0, 495
functions, spill support, xlsx read/write, actively developed.

### 4.4 LibreOffice headless — a fidelity backstop, not an embeddable engine

**Licence: MPL-2.0** (TDF authoritative), not the GPL-3.0 the GitHub API reports off a
legacy `COPYING` file. Shelling out to a separate process carries **no copyleft into your
code**. [V] **Shell out; do not link LibreOfficeKit.**

Measured: **~0.4 s fixed cost per invocation warm** (0.85 s cold), then ~7 µs per formula
cell — 200,000 formulas recalc in 1.77 s; peak RSS 285 MB. On my own box, a 10,000-cell
`.fods` recalculated and exported in **0.31 s against a 0.27 s process floor**, i.e. the
calculation itself was ~40 ms. [V-LOCAL] Fine for save-time or commit-time batch work;
**not viable on a synchronous request path, and useless for per-keystroke interactivity.**

🔴 **The defaults fail silently in three independent ways** — every one of these ships wrong
numbers with a zero exit code: [V]

1. **Stale cache passthrough on OOXML.** `--convert-to` does **not** recalculate `.xlsx`.
   `OOXMLRecalcMode` defaults to **`1` = never**. The widely-circulated advice to "set it to
   1" is a no-op; **you want `0`**. There is no `-env:` switch for it — you need a
   `registrymodifications.xcu` in a throwaway profile, or a Basic macro calling
   `calculateAll()`.
   *Why naive pipelines appear to work*: LibreOffice hard-recalcs when the generator string
   is unrecognised **and** no formula cell carries a non-zero cached result — which is
   exactly what openpyxl writes. Hand it a real Excel workbook and the heuristic flips off.
2. **Concurrency fails silently.** Four concurrent conversions sharing a `UserInstallation`
   produced **1 of 4 outputs**; with a unique profile per worker, 4 of 4. On a 3-way
   collision, **two of three failures exited 0**. Never trust the exit code — stamp
   `(mtime, size)` before and after and treat unchanged as failure.
3. **Dynamic arrays truncate without error.** Calc has **no SPILL** (tdf#127808 still NEW).
   Single-cell dynamic-array formulas return **only the first element, silently**:
   `FILTER(A1:A3,A1:A3>15) → 20` where the answer is `{20,30}`. A validator counting
   `#VALUE!/#N/A/#NAME?` reports **zero errors**. This is the most dangerous failure mode in
   the stack. `LAMBDA`/`MAP`/`REDUCE`/`BYROW` are in **no released LibreOffice** — they
   landed on master after the 26.8 branch point, so ≈ LO 27.2, early 2027.

Also note: **`unoserver` has no recalculation option**, and **Gotenberg does not
recalculate** (source-verified; its `registrymodifications.xcu` template only sets SSRF
hardening). Long-lived processes leak — JODConverter hard-codes
`DEFAULT_MAX_TASKS_PER_PROCESS = 200` with the comment *"some OOo installation is known to
have memory leaks."* Treat it as a bounded, recycled worker pool, never a daemon.

---

## 5. Diff and merge for tabular data

### 5.1 daff — the best generic CSV merge driver, and still not safe unattended

`paulfitz/daff`: MIT, 923★, pushed 2026-05-27 — but the last *substantive* commit was
**2025-05-04**; the 2026 push was Dependabot. Maintained-but-dormant. [V]

**It does do cell-level three-way merge**, and its key design decision is right: a conflict
is written **in-cell** so the merged file **stays valid CSV**:

    1,apple,((( 10 ))) 11 /// 55

No `<<<<<<<` markers to corrupt the table. It ships a real git driver (`daff git csv`, which
writes to `git config --global`).

**Row identity is guessed, not declared.** `CompareTable.hx` ranks columns by distinct-value
count, keeps the **top 5**, enumerates all **32 subsets**, builds a hash index per subset and
scores each by the fraction of rows whose key is present-and-unique in both tables. `--id
COL` overrides it. This heuristic is the documented weak spot — open issues **#217** *"Fix
row alignment when column selection heuristic excludes distinguishing columns"* (2026-03-05)
and **#216** *"Daff gives incorrect results, but correct results when file is truncated"*
(2026-01-28). [V]

**Three classes of silent data corruption, reproduced by running it:** [V]

| Scenario | Result |
|---|---|
| Both sides insert a row with the **same primary key** | **exit 0, no conflict, two rows with `id=7`** — and `--id id` does not fix it |
| Local **deletes** a row, remote **edits** that row | **exit 0, row silently deleted** — no delete/modify conflict |
| Both sides add a new column with the **same name** | **exit 0, header becomes `id,name,qty,note,note`** |
| Same cell edited differently | ✅ conflict, exit 1 |
| Reorder on one side, cell edit on the other | ✅ clean |

`Merger.hx` contains the candid comment `// row/col movement -- ignore for now`.

**Debunked**: several 2026 blog posts claim "GitHub renders CSV diffs with daff out of the
box." **False.** daff's own README points to a third-party Chrome extension,
`theodi/csvhub` (38★, dead since 2022). [V]

### 5.2 The rest of the tooling

- **csvmerge3** (`sctweedie/csvdiff3`, MIT, **10★**, last real commit 2023-02) is daff's
  mirror image: it **catches** every case daff misses (duplicate-key insert, delete/modify)
  because `-k/--key` is mandatory — but its conflict markers **destroy CSV validity**, it has
  three undeclared dependencies, it isn't on PyPI, and it prints a raw Python object repr
  instead of a filename. [V]
- **csvdiff** (Go, MIT, 585★, 2024-03) and **csv-diff** (Python, Apache-2.0, 340★, 2024-09)
  are **diff-only**, both stale, both require an explicit primary key. Neither merges. [V]
- **Git XL** — correct repo is `xltrail/git-xl` (MIT, 605★). **VBA only** — worksheet cells
  and formulas are not diffed. Windows only. **No merge.** Last release 2023-02-19; open
  issue #89 (2026-06) is *"Outdated dependencies, Installer does not work."* Effectively
  unmaintained. [V]
  The **company is alive** (xltrail.com, "© 2026 Pathio Limited"), and the hosted product
  does track cell formulas, defined names and Power Queries — but it is **diff and audit
  only**. Their own post concedes git *"will **always** give you a merge conflict"* on xlsx.
- **`git diff --textconv`** gives readable diff/log/show/blame and **nothing for merge** —
  `man 5 gitattributes`: *"diffs generated by textconv are not suitable for applying… only
  `git diff` and the `git log` family will perform text conversion."* [V] There is no
  textconv-equivalent for merge. The one live converter is `dilshod/xlsx2csv` (MIT, pushed
  2026-08-21); use `--all` or you only see the first sheet.
- **GitHub's native CSV rendering is blob-view only.** `.csv`/`.tsv` render as an
  interactive table with row permalinks and a filter box, **up to 512 KB**, and fail on
  mismatched column counts or semicolon delimiters. **There is no rich CSV diff in pull
  requests** — a CSV change in a PR is a raw text line diff. Community discussion #203750
  (2026-08-02) is still unanswered. [V]

### 5.3 Dolt — right answers, wrong substrate

`dolthub/dolt`: Apache-2.0, 24,286★, pushed same-day. **It is a separate VCS with a
git-shaped CLI**, not a git-compatible file. [V] Storage is a **prolly tree** — a
content-addressed, *history-independent* B-tree whose chunk boundaries are cut by a rolling
hash (~4 KB average). History independence means the same logical table always yields the
same tree, so diffing is a parallel walk comparing node hashes: **diff cost scales with the
size of the change, not the table.**

It is the only thing that gets three-way merge *right*, and it does so by **refusing to be a
CSV tool**: the primary key is declared in the schema rather than guessed, merges are
**cell-wise**, and conflicts land in `dolt_conflicts_<table>` system tables exposing
base/ours/theirs — no text markers in the data. [V]

**2026 development worth knowing**: Dolt now supports **git repositories as Dolt *remotes***
(announced 2026-02-13), storing its data under a custom ref, **`refs/dolt/data`**. So Dolt
data can be *hosted* in a GitHub repo — as an opaque blob under a non-standard ref that
`git clone` does not fetch. It is still not git-readable content, and there is still no
git-side diff or merge of it. [V] `.dolt/` on disk is mostly binary (`noms/` chunk store);
only `config.json` and `repo_state.json` are readable.

**DoltHub's own argument** (2022-07-15) is honest and self-serving in equal measure: Google
Sheets and Excel have *version history but not version control* — no branch-and-merge, no
asynchronous parallel work; xltrail is the only dedicated player and has no merge; therefore
true spreadsheet version control does not exist. **My testing agrees with the diagnosis.**

I confirmed the corollary locally: **plain SQLite in git is a dead end.** A 10,000-cell
SQLite file costs about the same repo space as `.fods` (292 K vs 268 K over 21 commits), but
`git diff` reports only `Bin 303104 -> 303104 bytes`, and two edits to **completely
different rows** produce an **unresolvable binary conflict**. [V-LOCAL] That is exactly why
Dolt had to become a separate VCS, and it disqualifies the Grist-style `.grist`-in-git model.

### 5.4 Merging formulas is unsolved — and my testing shows why

**Nothing merges spreadsheet formulas correctly.** [V] Every file-diff-based tool is
*structurally incapable* of it, because by the time it sees the two files the reference has
already been rewritten to a value that looks identical on both sides.

The only two designs that could work are **operation-log replay** (LibreOffice's
`Edit ▸ Track Changes ▸ Merge Document`, which requires both files to carry recorded changes
from a common original; and Grist's action log) or **parsing formulas to an AST with
structural rather than positional references and re-resolving after merge** — which nobody
has built. Excel's cloud co-authoring gets it right only because it is **operational
transform over live edits, not a merge of two files**, and therefore requires a single shared
authority — the opposite of branching. [V]

**This is precisely the problem that named-column addressing dissolves rather than solves**
— see §6.

---

## 6. The core finding: A1 addressing is what breaks git, and two shipped products threw it out

### 6.1 The claim, tested

Hypothesis: *"A1 references are the thing that makes spreadsheets un-diffable."*

I built the same 8-row sheet twice — once with A1 references (`=B2*C2`, `=SUM(D2:D9)`),
once with Kova-style named columns (`=qty * unit`, `=sum(total)`) — and put identical
concurrent edits through `git merge`. **The claim is verified, and the real failure is not
"un-diffable". It is "silently wrong".** [V-LOCAL, §A12]

**Failure mode 1 — text-level edit, no renumbering** (what an LLM, a script, or a text
editor does). Branch A inserts a row near the top; branch B inserts one near the bottom; far
enough apart that git auto-merges.

    >>> git merge: CLEAN, NO CONFLICT on either file

The named-column markdown is **correct**. Every row still reads `=qty * unit`; the footer
still reads `=sum(total)` and covers all ten data rows.

The A1 CSV is **silently corrupt**. Fed to LibreOffice, the merged file computes:

| row | shows | should be |
|---|---|---|
| item1 | **100** | 20 |
| item2 | 20 | 30 |
| … | shifted by one | |
| NEW_B | **70** | 200 |
| **TOTAL** | **480** | **660** |

A **27% error in the total**, with no conflict, no error and no marker anywhere.

**Failure mode 2 — app-level edit, with renumbering** (what Excel and LibreOffice actually
do). Re-running with the trailing references rewritten on insert:

- **Inserting one row into an 8-row sheet changes 17 lines** — the whole tail plus the
  footer range. A one-row insert is a whole-file rewrite.
- Two inserts **six rows apart** now **conflict**, across a 7-line block.

The same two operations on the named-column table: **one added line each, clean merge,
correct result.**

### 6.2 Why, stated precisely

An A1 reference encodes **position**, and position is a function of every row above it. So
the same *logical* edit produces different *text* on different branches, and git — which
merges lines, not meaning — combines two incompatible renumberings into a third numbering
that matches neither branch's intent. Either the renumbering is absent (mode 1: clean merge,
wrong numbers) or present (mode 2: everything churns, everything conflicts).

**There is no version of A1 addressing that is well-behaved under a distributed merge.**

A named-column relative reference encodes **meaning**. `=qty * unit` is true of its row
wherever that row sits, and stays true when other rows move. The formula text is
**invariant under row insertion, deletion and reordering** — exactly the property that makes
line-based merge safe. It is not that named columns merge *better*; it is that there is
nothing left to merge incorrectly.

### 6.3 The honest limits of named-column addressing

This is strictly better for **merge safety**, not strictly better overall. Named-column
relative references **cannot express what A1 exists for**: pointing at one specific other
cell (`=B7`), a rectangular block, or a value on a *different row* of the same table.

Kova's answer is to have exactly two scopes — **this row**, or **this whole column** — and
to defer cross-table references entirely. That covers bills of materials, line-item tables,
budgets and invoices. It does **not** cover a financial model with a time axis, where "last
period's closing balance" is inherently a reference to another row. Any serious version of
this needs a row-relative operator (something like `prev(balance)`), and that is a real
design problem, not a detail.

### 6.4 Kova's implementation, from the source

`KovaMD/Kova`: **GPL-3.0, 283★, created 2026-05-04, pushed 2026-08-23**, TypeScript. [V]

The engine is `src/engine/sheet/`: **555 lines** across `lexer.ts` (49), `parser.ts` (128),
`evaluate.ts` (164), `sheet.ts` (162), `constants.ts` (52), with **63 tests**. [V]

**Architecturally real, not a toy.** Proper tokenizer; recursive-descent parser with seven
precedence levels; strings, booleans, `and`/`or`/`not`, ternary `? :`, right-associative
`^`; memoised evaluation with **cycle detection** (`circular reference in column 'x'`).

**Coverage is a toy.** Eleven functions total: aggregates `sum, avg, min, max, median`;
scalars `round, abs, floor, ceil, if, concat`. [V] No lookups, no dates, no text functions
beyond `concat`, no ranges, no cross-table references. Compare IronCalc's 495.

The safety design is unusually thoughtful and worth copying:

- A **footer row with no formula** is an explicit error, because misreading a data row whose
  label happens to start with `!` *"would quietly deflate the totals below it"*. The source
  comment: *"a wrong total with no error is the one outcome this design refuses."*
- **Failures are deliberately not memoised**, because `null` is the empty-cell sentinel and
  caching it *"would make a broken cell look merely empty to every dependent and turn a
  visible `#ERR` into silent blanks."*
- Duplicate column names are a table-wide error reported in **every** formula cell, since no
  single cell is to blame.
- `\=` and `\!` escape the two markers, and remark renders `\!` as a plain `!` — so the
  escape costs nothing in a non-Kova viewer.
- `!include`, `!fmt` and `!code` are **reserved and error out today**, so decks written now
  will not collide with them later.

**Cross-table references are not implemented.** `parseSheetDirective` accepts and ignores a
bare word in `!sheet bom precision=3`, commented *"a table name, for the deferred
cross-table references."* [V] The syntax slot is reserved; the feature is not there.

**Graceful degradation is the quiet win.** Open a `!sheet` file in any markdown viewer that
has never heard of Kova and you get a valid GFM table, with `=qty * unit` in the derived
cells and a stray `!` on footer labels. Nothing is unreadable, nothing is lost.

### 6.5 `.calc.md` and its unacknowledged prior art

Nimbalyst's `.calc.md` (see `08-nimbalyst-formats.md`) takes the same insight further: named
*variables* instead of named columns, no addressing of any kind, plus unit-aware arithmetic
and `assert`. I verified it merges as advertised — two branches editing two different
assumptions merged cleanly, each change a single line pair. [V-LOCAL]

**But the "nothing else does this" framing would be wrong.** [V]

**Numbat** (`sharkdp/numbat`, **MIT + Apache-2.0**, 2,669★, pushed 2026-08-25) already
combines plaintext line-oriented files (`.nbt`), named variables, units, and assertions —
and its dimensional checking is **stronger**: a static type system where physical dimensions
*are* types, checked before evaluation (`fn speed(len: Length, dur: Time) -> Velocity`,
generics `fn my_sqrt<T: Dim>(q: T^2) -> T`), explicitly inspired by F# units of measure. It
has `assert(cond)`, `assert_eq(a, b)` and **`assert_eq(a, b, ε)` with an explicit
tolerance** — the last of which `.calc.md` should steal, because float equality assertions in
a units context are a footgun without it. Numbat also has user-defined units and dimensions
(`unit pixel`, `dimension Deceleration = Length / Time^2`).

What `.calc.md` genuinely owns is the **document framing**: markdown headings as sections,
YAML frontmatter for display config, gutter-only results. No tool combines *that* with units
and assertions. That specific slot is empty. [V]

Two useful contrasts:

- **Calca** (proprietary, macOS, effectively abandoned — iOS app delisted, one 2025 build)
  is the anti-pattern: plain-markdown files with heading-scoped variables, but the `=>`
  operator makes it **write results back into the document**. Change one input and every
  downstream line rewrites. The file becomes its own cache. `.calc.md`'s strict
  never-write-back rule is the right call. [V]
- **Obsidian Numerals** (MIT, 642★, pushed 2026-07-18) is the sleeper: ordinary `.md`,
  ```` ```math ```` blocks, named variables, **frontmatter properties as inputs**, units via
  mathjs, gutter-only results — plus an **opt-in labelled writeback** (`@[profit]` →
  `@[profit::1550.00 USD]`) that scopes diff churn to lines the author explicitly marked. No
  assertions. [V]
- **Frink** is the units benchmark (interval arithmetic, historical currency, thousands of
  units) and is actively maintained in 2026 — but it is **closed source** by the author's own
  explicit choice, and it has **no `assert`**. Do not cite it as open prior art. [V]
- ⚠️ Two citation traps: **insect is archived** and redirects to Numbat; and
  `github.com/nikolaeu/numi` shows **MIT, 6,493★** but contains only a README, changelog and
  plugins — **the Numi app itself is closed source**. [V]

### 6.6 The column-rename problem — the mirror image, and what every mature system does about it

Named-column addressing trades one fragility for another. A1 references break when **rows
move**; name references break when **a column is renamed**. This is not hypothetical: every
mature named-column product hit it, and their solutions are instructive — because **none of
them is available to a plaintext format.**

**Strategy A — store an ID, render a name.** The formula on disk never contains the name at
all.

- **Airtable** — the API docs, verbatim: *"The formula including fields referenced by their
  IDs. For example, `LEFT(4, {Birthday})` in the Airtable.com formula editor will be
  returned as `LEFT(4, {fldXXXXXXXXXXXXXX})` via API."* [V]
- **Notion** — verbatim: *"`prop("Name")` matches a property by its current name, but the
  **saved formula references the property by ID**, so renaming the property later doesn't
  break the formula."* [V]
- **Teable** converts between the two representations explicitly —
  `convertExpressionIdToName()` in `formula.field.ts`. [V]
- **NocoDB** stores **both**: a `formula` field and a `formula_raw` field on
  `FormulaColumn.ts`. [V]

**Strategy B — store the name, and rewrite every formula on rename.** **Baserow** does this,
in `rename_field_references_in_formula_string()` (`formula/handler.py`). [V]

**Strategy C — decouple the identifier from the label entirely.** **Grist** has
`untieColIdFromLabel` (`FieldConfig.ts`): the displayed label and the `$ColumnId` used in
formulas are separate, and the user chooses whether they track each other. [V]

**Why this matters here.** Strategies A and C both work by **hiding an identifier the user
never types**. In a database-backed product that is free. In a **plaintext git format it is
fatal** — a `.sheet.md` containing `=fld_a7Kx91 * fld_Qm22b` destroys the readability that is
the entire reason for choosing the format. You cannot have both an opaque stable ID and a
human-legible diff.

So a plaintext named-column format is forced into **Strategy B: renaming a column rewrites
every formula that mentions it.** Be honest that this is a real cost — a column rename is a
whole-file diff, exactly the churn that A1 suffers on a row insert.

**But the two are not equally bad, in three ways that all favour named columns:**

1. **Frequency.** Rows are inserted constantly; columns are renamed rarely.
2. **Failure mode.** A rename rewrite is *deterministic, local and reviewable* — the diff
   shows `qty` → `quantity` on every line that used it, and a human or a reviewer can see
   exactly what happened. An A1 row-shift merge is a *silent semantic corruption* with no
   diff signal at all (§6.1). A noisy-but-correct diff beats a clean-but-wrong merge.
3. **Concurrency.** Two branches renaming the same column produce an honest conflict on
   every affected line. Two branches inserting rows produce a clean merge and a wrong total.

There is also a cheap mitigation with no downside: **treat a rename as a rename.** Emit it as
its own commit, separate from data edits, and `git merge` handles the rest — the same
discipline that makes large code refactors survivable.


### 6.7 Named-column addressing is not exotic — Excel already shipped it

The strongest legitimacy argument for the model, and the one that changes the interop story:
**Microsoft's own Excel Tables use named-column relative references**, and have for years.
From Microsoft's structured-references documentation: [V]

- *"Rather than `=SUM(C2:C7)`, you write `=SUM(DeptSales[Sales Amount])`. That combination of
  table and column names is called a **structured reference**."*
- `[Column]` = the whole column's data; **`[@Column]`** = **this row's value** in that column.
  A calculated column reads `=[@[Sales Amount]]*[@[% Commission]]`.
- Item specifiers: `#All`, `#Data`, `#Headers`, `#Totals`, **`#This Row`** (of which `@` is
  the shorthand).
- *"Excel automatically creates a calculated column and copies the formula down the entire
  column for you"*, and *"cell references for structured references adjust automatically"*
  when rows are added.

Map that onto Kova's design and the correspondence is nearly exact:

| Kova `!sheet` | Excel structured reference |
|---|---|
| `=qty * unit` (data row) | `=[@Qty]*[@Unit]` |
| `=sum(total)` (footer row) | `=SUM(Table1[Total])` |
| `!Total` footer row | the table's **Totals** row (`#Totals`) |
| header → slugified column name | the table's column header |

Three consequences:

1. **The model is proven at scale.** This is not a markdown-tool invention; it is how the
   most-used spreadsheet in the world recommends you write table formulas, precisely because
   it survives row insertion.
2. **The Excel export can preserve formula *meaning*, not just values.** A `.sheet.md`
   `!sheet` table maps onto an Excel **ListObject** with structured references — so the
   round-trip does not have to degrade into A1 and does not have to ship dead values. This
   is a much better interop story than "export a CSV of numbers."
3. **Google Sheets has no equivalent.** It has named ranges, but no structured references
   and no ListObject concept, so a Sheets export must fall back to A1 or values. Worth
   knowing before promising parity.

Note the direction of travel: Excel added structured references *on top of* A1 because A1
does not survive row edits. Kova and `.calc.md` simply refuse to ship the A1 layer
underneath. Given that the whole point here is git, that is the correct amputation.


---

## 7. Design analysis — what to actually build

### 7.1 Candidate designs, scored

Scoring: **human readability**, **git diff quality**, **merge behaviour**, **formula
fidelity**, **Excel/Sheets interop**, **AI-agent legibility** (can Claude read and edit it
with no tool?).

---

**Candidate 1 — `sheet.csv` + `sheet.formulas.yaml` sidecar**

| | |
|---|---|
| Human readability | ✅✅ best — the CSV is the data, unadorned |
| Git diff | ✅ good for values, ✅ good for formulas, **but split across two files** |
| **Merge** | 🔴 **broken by construction** |
| Formula fidelity | ✅ whatever you choose to encode |
| Interop | ✅✅ the `.csv` opens anywhere |
| AI legibility | ✅✅ |

🔴 **Reject.** I demonstrated the failure. [V-LOCAL, §A8] A sidecar keyed by A1 addresses has
a key space (`B4`) that is **a function of the other file's line count**, and git merges
files independently with no cross-file invariant. In my test, branch A inserted a row and
rewrote the sidecar; branch B made an unrelated price edit. Result: **`sheet.csv` conflicted
while `sheet.formulas.yaml` merged "cleanly"** — to branch A's row numbering. Whichever way
the human resolves the CSV, nothing keeps the two consistent. The sidecar now describes a
row layout that may not exist. This is the worst failure mode available: a corruption that
looks like a successful merge. GridHub's `formulas.csv` / `values.csv` split has exactly the
same defect.

---

**Candidate 2 — single flat XML `.fods`**

| | |
|---|---|
| Human readability | ⚠️ verbose XML, but line-oriented and greppable |
| Git diff | ✅ 2 lines for a cell edit, 6 for a row insert [V-LOCAL] |
| **Merge** | ✅✅ **cell-level three-way merge from stock git, no merge driver** [V-LOCAL] |
| Formula fidelity | ✅✅ full ODF: formulas, styles, number formats, multi-sheet, charts |
| Interop | ⚠️ Excel/Sheets need a one-command convert (verified lossless for formulas/sheets/styles) |
| AI legibility | ⚠️ works, but **~38 tokens per cell vs CSV's ~1.9** |

✅ **Accept, as the fidelity format.** The decisive property is §A7: two branches editing
different **columns of the same row** merge cleanly, because LibreOffice emits ~3 lines per
cell. CSV structurally cannot do this. **Do not minify** — my compact one-line-per-cell
hand-written variant *conflicted* in the same scenario, because git will not auto-merge
adjacent lines. The verbosity is the feature.

Costs are real but mechanical: printer-blob churn, auto-style renaming, RLE run-splitting
(§3.1) — and I have a working zero-churn clean filter (§7.2). The one cost that is *not*
mechanical is **token weight**: a 10,000-cell sheet is ~417 K tokens of `.fods` against ~19 K
of CSV. [V-LOCAL, §A9] Fine for a 200-cell budget; hostile for a 10,000-row dataset. Give
agents a CSV projection (`soffice --convert-to csv`, optionally with formulas) rather than
the raw XML.

---

**Candidate 3 — markdown table + named-column formulas (Kova `!sheet`)**

| | |
|---|---|
| Human readability | ✅✅ **best of any format here** — it is a markdown table |
| Git diff | ✅✅ one row = one line; a row insert is **one added line** |
| **Merge** | ✅✅ **correct**, and correct *after* merge, which A1 never is (§6.1) |
| Formula fidelity | 🔴 11 functions today; no lookups, dates, ranges, or cross-table refs |
| Interop | 🔴 none — but degrades to a valid markdown table everywhere |
| AI legibility | ✅✅ **best**, by a wide margin — it is the format LLMs are most fluent in |

✅ **Accept, as the primary format.** The addressing model is the whole argument (§6). It is
also the only candidate that is *already legible* to every markdown tool, every reviewer, and
every model, with no conversion.

The gap is function coverage, and it is a gap you close by **swapping the evaluator, not the
format**. Kova's 555-line engine proves the *format* works; nothing stops you parsing the
same `!sheet` table and evaluating with IronCalc's 495 functions. The addressing model and
the function library are independent choices.

---

**Candidate 4 — SQLite / Dolt**

| | |
|---|---|
| Human readability | 🔴 none without a tool |
| Git diff | 🔴 `Bin 303104 -> 303104 bytes` [V-LOCAL] |
| **Merge** | 🔴 **two edits to entirely different rows = unresolvable binary conflict** [V-LOCAL] |
| Formula fidelity | ✅ (Grist: Python, named-column) |
| Interop | ⚠️ export only |
| AI legibility | 🔴 needs `sqlite3` |

🔴 **Reject for a git-backed suite.** Dolt gets the *semantics* right — declared primary
keys, cell-wise merge, conflicts in system tables — but achieves that by **not being git**.
Its 2026 git-remote support stores an opaque blob under `refs/dolt/data`; the data is hosted
in a GitHub repo but is not git-readable, diffable or mergeable. If git is your drive, this
isn't a file in it.

---

**Candidate 5 — line-oriented `.calc.md`** (Nimbalyst; see `08-nimbalyst-formats.md`)

| | |
|---|---|
| Human readability | ✅✅ reads like an engineer's notes |
| Git diff | ✅✅ one statement = one line; **the diff names the assumption that changed** [V-LOCAL] |
| **Merge** | ✅✅ clean — no addressing at all, so nothing to shift |
| Formula fidelity | ✅ for models; **units + dimensional checking + assertions**; ❌ not a grid |
| Interop | 🔴 none |
| AI legibility | ✅✅ |

✅ **Accept, as the third format.** It is not a competitor to the other two — it serves a
different job (§7.3). Borrow `assert_eq(a, b, ε)` and user-defined units from Numbat (§6.5).

---

**Candidate 6 — CSV with a JSON metadata comment** (Nimbalyst `csv-spreadsheet`)

🔴 **Reject the metadata-line mechanism specifically.** The idea — one artifact, no sidecar
to desynchronise — is right, and it is a genuine improvement on Candidate 1. But minified
JSON contains commas, so a standard CSV parser splits line 1 into three fields and
**widens the entire sheet to three columns**; I reproduced this with both Python's `csv`
module and LibreOffice. [V-LOCAL, §3.4] It breaks plain-CSV interop precisely where CSV's
whole value lies. If you want in-band metadata, put it in **YAML frontmatter above the
table in a markdown file** — which is Candidate 3.

### 7.2 The `.fods` canonicalisation filter (working, tested)

The printer-blob problem is the main practical objection to `.fods` in git, and it is
solvable. This filter takes churn from 11 lines per no-op save to **zero, stably, across
repeated LibreOffice saves**, shrinks the file 25% (333 → 239 lines), and the result still
loads and computes correctly. [V-LOCAL]

    # .gitattributes
    *.fods filter=fods diff

    # .git/config
    [filter "fods"]
        clean = python3 tools/fods-clean.py
        smudge = cat

```python
#!/usr/bin/env python3
"""git clean filter: canonicalise a LibreOffice .fods for version control."""
import re, sys
s = sys.stdin.read()
# 1. machine-local view + printer state, and volatile document statistics
s = re.sub(r'\s*<office:settings>.*?</office:settings>', '', s, flags=re.S)
s = re.sub(r'\s*<office:meta>.*?</office:meta>',         '', s, flags=re.S)
# 2. master-page header/footer blocks carry a live clock and drift between saves;
#    they are print decoration only.
s = re.sub(r'\s*<office:master-styles>.*?</office:master-styles>', '', s, flags=re.S)
# 3. LO-version-dependent style attribute noise
s = re.sub(r'\s*loext:tab-stop-distance="[^"]*"', '', s)
# 4. cached formula results — LibreOffice recalculates ODF on load (verified),
#    so drop them: no redundant state, no stale-value diff noise.
s = re.sub(r'(<table:table-cell[^>]*?table:formula="[^"]*")'
           r'[^>]*?(?:/>|>\s*<text:p>[^<]*</text:p>\s*</table:table-cell>)',
           r'\1 office:value-type="float"/>', s)
sys.stdout.write(s)
```

Still to add for production: stable auto-style names (or adopt `fods_minimizer`), and a
decision on run-length-encoded empty rows.

### 7.3 The recommendation: three formats, because "spreadsheet" is three jobs

The single strongest conclusion from this research is that **the question "which one file
format" is the wrong question.** What people call a spreadsheet is at least three unrelated
artifacts, and the formats surveyed map onto them almost suspiciously well:

| Job | What it really is | Format | Why |
|---|---|---|---|
| **Tabular data** — lists, inventories, CRM exports, line items | rows of records, order mostly irrelevant, few or no formulas | **`.csv`** (plus `.sheet.md` when it needs a total) | already universal; GitHub renders it; daff can diff it |
| **A model** — budgets, pricing, unit economics, engineering calcs | named quantities and the relationships between them; a grid is incidental | **`.calc.md`** line-oriented, named variables, units, assertions | the diff names the assumption that changed; merges perfectly |
| **A document that computes** — invoices, BOMs, quotes, reports | a table that must *look* right and *add up* | **`.sheet.md`** (`!sheet`, named columns) → **`.fods`** when it needs real formatting or Excel round-trip | readable, mergeable, degrades to a plain markdown table |

This mirrors what the rest of the suite already does: nobody stores a document and a slide
deck in the same format. Trying to make one spreadsheet format serve a 50,000-row export, a
five-year financial model, and a printable invoice is what produces `.xlsx`.

**Concretely, if I were building this:**

1. **`.sheet.md` is the default and the flagship** — GFM table, `!sheet` directive,
   named-column relative formulas, footer rows for aggregates, `!let` constants. Adopt
   Kova's syntax rather than inventing one; it is shipping, thought through, and degrades
   gracefully. **Do not adopt its 11-function evaluator** — parse the table and evaluate with
   **IronCalc** (MIT/Apache-2.0, 495 functions, wasm + Python + Node bindings), resolving
   column names to a synthetic addressing space internally. Users never see A1; the engine
   never sees column names.
2. **Add a row-relative operator early.** `prev(balance)` or equivalent. Without it,
   named-column addressing cannot express a time-series model and you will be forced back to
   A1 by your first serious user. This is the known hole in Kova's design (§6.3).
3. **Export to Excel as a real Table with structured references**, not as A1 and not as dead
   values. `=qty * unit` → `=[@Qty]*[@Unit]`, `=sum(total)` → `=SUM(Table1[Total])` (§6.7).
   This makes the round-trip preserve formula *meaning*, which no competitor does. Google
   Sheets has no equivalent — plan to degrade there, and say so.
4. **Treat a column rename as its own commit.** A plaintext format cannot use the
   store-an-ID trick that Airtable, Notion and Teable rely on without destroying its own
   readability, so a rename necessarily rewrites every formula that mentions the column
   (§6.6). Keeping renames out of data commits makes that diff reviewable instead of
   alarming.
5. **`.fods` is the escape hatch**, reached by an explicit "convert to full spreadsheet"
   action when someone needs charts, conditional formatting or an Excel hand-off. Ship the
   clean filter from §7.2 on day one — without it the format leaks the user's printer name
   into every commit. Use **LibreOffice headless as a batch converter and fidelity backstop
   only**, out of process (MPL-2.0, no copyleft reach), with a unique `-env:UserInstallation`
   per invocation, an explicit forced recalc, and **mtime+size verification instead of the
   exit code** (§4.3).
6. **`.calc.md` for models.** Steal Numbat's `assert_eq(a, b, ε)` and user-defined units.
7. **Never ship a formula sidecar** (§7.1 C1), **never ship a `#`-comment metadata line in a
   `.csv`** (§7.1 C6), and **never put SQLite in git** (§7.1 C4).
8. **On engines: HyperFormula's GPL-3.0 is a real constraint**, and Handsontable's licence
   contains an explicit non-compete that bars this product category outright. IronCalc is
   the answer; Univer (Apache-2.0, ~502 functions, documented headless Node) is the
   conservative fallback if pre-1.0 risk is unacceptable.

### 7.4 What is genuinely still unsolved

- **Cross-sheet and cross-table references in a named-column world.** Kova reserves the
  syntax and hasn't built it. Nobody has.
- **Row-relative references** (`prev(...)`) — the hole that keeps named-column formats out of
  financial modelling.
- **Formula merge in *any* A1 format.** Structurally impossible for file-diff tools (§5.4).
  Only operation-log replay or AST-with-structural-references could work; neither exists.
- **Key inference for tabular merge.** daff's top-5-cardinality / 32-subset search is the
  state of the art and has open correctness bugs (#216, #217). Everything else punts to the
  user.
- **Charts in any diffable format.** Untested by me (no UNO bindings on this machine, §A11);
  Univer serialises them as escaped JSON one-liners; nobody has a good answer.
- **A tabular standard with formulas.** Frictionless, CSVW, CSVY and `.csvs` all decline to
  specify one (§3.5). The gap has been open for a decade.

---

## Appendix A — First-party experiments (run 2026-08-28)

All of the following are **VERIFIED** by running them locally.
Environment: `LibreOffice 25.2.3.2 520(Build:2)`, `git`, Debian 13 (Linux 6.12.101).
Scripts and artefacts under a scratch dir; every claim below is a reproduced observation,
not a citation.

### A1. `.fods` is one pretty-printed XML file, and it holds real formulas

Converting a 4x5 CSV containing `=B2*C2` / `=SUM(...)` via

    soffice --headless \
      --infilter='CSV:44,34,76,1,,0,false,true,true,false,false,-1,true' \
      --convert-to fods:'OpenDocument Spreadsheet Flat XML' in.csv

produced a **single 25,583-byte file of 333 lines** (longest line 2,197 chars — that
is the `<office:document>` namespace declaration line; everything else is short).
LibreOffice **pretty-prints** flat ODF: roughly **3 lines per cell**, one element per line.

Formulas survive as an attribute in ODF OpenFormula syntax:

    table:formula="of:=[.B2]*[.C2]"
    table:formula="of:=SUM([.B2:.B4])"

with the computed result cached alongside as `office:value="25"`.

### A2. LibreOffice recalculates on load — cached values are optional

Two separate tests:

1. Edited **only** the input `office:value="10"` -> `"12"` in the XML with `sed`/Python,
   deliberately leaving every cached formula result stale (`25`, `21`, `61.7`).
   Converting to CSV produced `30`, `23`, `66.7` — i.e. **LO ignored the stale cache and
   recalculated**.
2. Stripped the cached value and text from every formula cell entirely, leaving bare
   `<table:table-cell table:formula="of:=[.B2]*[.C2]" office:value-type="float"/>`.
   The file loaded and computed correctly.

I then hardened this against a contradicting report that LibreOffice does *not* recalculate.
Both are true, of **different formats**. With a falsified cache (`B1 = A1*21`, cached `999`,
true value `42`), `.fods` returned **42** in every configuration I tried: with a LibreOffice
generator string, with an alien one (`SomeOtherTool/1.0`), and in a fresh throwaway
`-env:UserInstallation` profile. The equivalent `.xlsx` path returns the stale `999` unless
`OOXMLRecalcMode=0` is forced. Both registry keys default to `1`; the ODF key's own
description scopes it to *"non-LibreOffice-generated ODF documents"*.

**Consequence:** emit a *canonical, cache-free* `.fods` in which each formula cell is a
single self-closing tag. There is then no cached value to go stale, so recalculation is
forced by construction and the ODF-vs-OOXML distinction stops mattering. No redundant state,
no stale-value diff noise, and an LLM editing the XML never has to maintain a second copy of
the answer. Verified end to end: a cache-free formula cell, alien generator, fresh profile
→ correct result.

### A3. A hand-written `.fods` is small and an LLM can author it

47 lines / 2,401 bytes of hand-written XML gave: two sheets (`Sales`, `Summary`),
a bold header style, arithmetic formulas, a **cross-sheet** `SUM([Sales.D2:.D3])`, and
an `IF(...)`. LibreOffice computed `54` and `"small"` correctly.

One sharp gotcha, found the hard way: the `of:` prefix inside the `table:formula`
attribute *value* is a real namespace prefix. Omit
`xmlns:of="urn:oasis:names:tc:opendocument:xmlns:of:1.2"` from the root element and every
formula silently becomes `Err:510`. Also note ODF uses **`;`** as the argument separator,
not `,`.

### A4. Diff quality

| Change | Diff size |
|---|---|
| One cell value edited | **2 lines changed** (the `office:value` attr line + the cached `<text:p>` line) |
| One row inserted (4 cells) | **6 added lines, zero deletions** — a pure-addition hunk |

These are exactly the diffs you want. Compare against unzipped `.xlsx` (A6).

### A5. Round-trip is *not* byte-stable — LibreOffice injects machine state

`in.fods` -> `soffice --convert-to fods` -> `in.fods`, with **no content change**, produced
an 11-line diff. The offenders:

- `<config:config-item config:name="PrinterName">` gained **`Generic Printer`**
- `<config:config-item config:name="PrinterSetup" config:type="base64Binary">` gained a
  **~700-char base64 blob naming the local printer, paper size (`PageSize:Letter`) and driver**
- `SyntaxStringRef` config item appeared
- `loext:tab-stop-distance` appeared on a default style
- child elements of `<office:meta>` were reordered

So a stock `.fods` commits **local machine configuration** to the repo and produces
spurious diffs between collaborators on different machines. This is the single biggest
practical objection to naive `.fods`-in-git.

**It is fixable.** Deleting `<office:settings>` and `<office:meta>` wholesale (335 -> 281
lines, 25.6 KB -> 20.9 KB) yields a file that LibreOffice loads and computes from without
complaint. But LO **re-adds the printer junk on every save**, so the strip must run as a
git `clean` filter (`.gitattributes` + `filter.fods.clean`), not as a one-off.

### A6. Unzipped `.xlsx` diffs are unusable

Unzipping a LibreOffice-written `.xlsx`, every XML part is **one single line**:

    docProps/app.xml            412 B   1 line
    xl/sharedStrings.xml        458 B   1 line
    xl/styles.xml              4839 B   1 line
    xl/worksheets/sheet1.xml   2810 B   1 line
    xl/workbook.xml             956 B   1 line

Any edit therefore renders as "the entire file changed". A pretty-print step is mandatory,
which then breaks byte-identical repacking. On top of that, `sharedStrings.xml` is an
indirection table: cell text is stored as an integer index, so editing one label changes two
files and can renumber every later index. (LibreOffice does not emit `calcChain.xml`;
Excel does, and it churns.)

### A7. Git 3-way merge: `.fods` gets **cell-level merge for free**, CSV does not

Real `git merge` runs, no custom merge driver.

| Scenario | `.csv` | `.fods` (LO pretty-printed) |
|---|---|---|
| Branch A edits a value; branch B appends a row | clean | clean |
| **Branch A edits `Qty`, branch B edits `Price` of the *same row*** | **CONFLICT** | **CLEAN MERGE** |

The CSV conflict is structural and unavoidable: a row is one line, so two edits to one row
are two edits to one line. In `.fods` the two cells live ~3 lines apart, so git's diff3
resolves them independently. The merged file was then fed back to LibreOffice, which
**recalculated the dependent formula correctly** (`77 x 3.99 = 307.23`) — the whole chain
works end to end.

**Important caveat discovered:** this only holds because LibreOffice emits ~3 lines per cell.
My *compact* hand-written variant put each cell on **one** line, and the same scenario
**conflicted** — git will not auto-merge changes on adjacent lines. So the line-per-cell
verbosity that looks like a flaw is precisely what buys cell-granular merging. **Do not
minify the format.**

### A8. `csv + formula sidecar` desynchronises silently — demonstrated

Layout: `sheet.csv` (values) + `sheet.formulas.yaml` (`D2: "=B2*C2"`, ...).
Branch A inserts a row (and dutifully rewrites the sidecar, shifting `B4`->`B5` etc.).
Branch B makes an unrelated price edit on an existing row.

`git merge` result: **`sheet.csv` conflicts, `sheet.formulas.yaml` merges "cleanly"** — to
branch A's row numbering. Whichever way the human resolves the CSV conflict, git has no
mechanism to keep the two files consistent. The formula addresses now describe a row layout
that may not exist.

This is the fundamental flaw of any A1-keyed sidecar: **the key space (`B4`) is a function of
the other file's line count**, and git merges files independently. Nothing enforces the
cross-file invariant. A single-file format keeps a cell's value and its formula on adjacent
lines, so they move together or conflict together.

### A9. Size and repo growth — `.fods` is cheap where it counts

1,000 rows x 10 cols = 10,000 cells, ninth column a `SUM` formula:

| | raw bytes | lines | gzip'd |
|---|---|---|---|
| `.csv` | 76,954 | 1,001 | 33,766 |
| `.fods` | **1,667,686** (21.7x) | 32,289 (3.23 lines/cell) | **89,352 (2.6x)** |
| `.xlsx` | 80,471 | 261 | 78,783 |

The raw 21.7x blow-up is the scary number and it is the wrong number. Git stores zlib-
compressed, delta-compressed objects. Actual `.git` size after **21 commits each changing one
cell**:

| format | `.git` after 21 commits |
|---|---|
| `.csv` | **212 K** |
| `.fods` | **268 K** (+26% over CSV) |
| `.xlsx` | **1012 K** (3.8x *worse* than `.fods`) |

`.xlsx` is 20x smaller as a single file yet costs 4x more in the repo, because a zip archive
delta-compresses against its predecessor essentially not at all. **Verbose text is cheaper in
git than compact binary.**

### A10. Interop, tested

- `.fods` -> `.xlsx` -> `.fods`: formulas, both sheet names, and the bold style all survived
  (`fo:font-weight="bold"` present; `<f aca="false">B2*C2</f>` written into
  `xl/worksheets/sheet1.xml`).
- `.fods` -> `.ods` -> `.fods`: formula set **byte-identical**.
- LibreOffice can also export **CSV containing formulas** (`Widget,10,2.5,=B2*C2`) via the
  "save cell formulas instead of values" filter flag — a useful human-review projection.
- Microsoft's own supported-formats page lists `.ods` but **has no entry for `.fods`**
  (VERIFIED by fetching the page). No evidence Google Sheets imports `.fods` either.
  So Excel/Sheets interop is a **one-command conversion**, not native open.

### A11. Not tested locally

Charts in `.fods`. This machine has no `python3-uno` and no GUI, and I would not install
packages ad hoc. Flat ODF represents embedded objects inline, but I did not reproduce a
chart round-trip and will not claim it.

### A12. The A1-reference claim, tested — and it is worse than claimed

The hypothesis under test: *"A1 references are what make spreadsheets un-diffable."*
I built the same 8-row sheet twice — once with A1 references (`=B2*C2`, `=SUM(D2:D9)`),
once with Kova-style named columns (`=qty * unit`, `=sum(total)`) — and ran identical
concurrent edits through `git merge`. **The claim is verified, and the real failure is
not "un-diffable" — it is "silently wrong".**

**Failure mode 1 — text-level edit, no renumbering (what an LLM or a text editor does).**
Branch A inserts a row near the top; branch B inserts a row near the bottom. Far enough
apart that git auto-merges.

    >>> git merge: CLEAN, NO CONFLICT on either file

The named-column markdown is **correct**: every row still reads `=qty * unit`,
the footer still reads `=sum(total)`, and it covers all ten data rows.

The A1 CSV is **silently corrupt**. Feeding the merged file to LibreOffice:

| row | shows | should be |
|---|---|---|
| item1 | **100** | 20 |
| item2 | 20 | 30 |
| item3 | 30 | 40 |
| … | …shifted by one… | |
| NEW_B | **70** | 200 |
| item7 | 70 | 80 |
| **TOTAL** | **480** | **660** |

A **27% error in the total**, with no conflict, no error, no marker — nothing anywhere in
the workflow says something went wrong. This is the worst possible failure class.

**Failure mode 2 — app-level edit, with renumbering (what Excel/LibreOffice actually do).**
A real spreadsheet app rewrites the trailing references when a row is inserted. Re-running
with that behaviour:

- **Inserting one row into an 8-row sheet changes 17 lines** — the entire tail of the
  file plus the footer range. A one-row insert is a whole-file rewrite.
- Two inserts **six rows apart** now **CONFLICT**, across a 7-line-wide block, because both
  branches rewrote the same trailing lines.

The same two operations on the named-column table: **one added line each, clean merge,
correct result.**

**Why this happens, stated precisely.** An A1 reference encodes *position*, and position is
a function of every row above it. So the same logical edit produces different text on
different branches, and git — which merges lines, not meaning — combines two incompatible
renumberings into a third numbering that matches neither branch's intent. Either the
renumbering is absent (mode 1: clean merge, wrong numbers) or it is present (mode 2: every
line churns, everything conflicts). **There is no version of A1 addressing that is
well-behaved under a distributed merge.**

A named-column relative reference encodes *meaning*: `=qty * unit` is true of its row no
matter where that row sits, and stays true when other rows move. The formula text is
**invariant under row insertion, deletion and reordering**, which is exactly the property
that makes line-based merge safe.

**Honest caveat.** This makes named-column addressing strictly better for *merge safety*,
not strictly better overall. It cannot express what A1 exists for: referring to one
specific other cell (`=B7`), a rectangular block, or a value on another row. Kova's own
answer is to have only two scopes — this row, or this whole column — with cross-table
references explicitly deferred (see §Kova). That covers bills of materials, line-item
tables and budgets; it does not cover a financial model with a time axis, where "last
period's closing balance" is inherently a reference to another row.


---

## Sources

**Standards & specs**
- OASIS ODF v1.3 part 3 (schema, §3.1.2 single XML) — https://docs.oasis-open.org/office/OpenDocument/v1.3/os/part3-schema/OpenDocument-v1.3-os-part3-schema.html
- OASIS ODF v1.2 part 1 — https://docs.oasis-open.org/office/v1.2/os/OpenDocument-v1.2-os-part1.html
- Excel supported file formats (no `.fods` entry) — https://support.microsoft.com/en-us/office/file-formats-that-are-supported-in-excel-0943ff2c-6014-4e8d-aaea-b83d51d46247
- Excel structured references / Tables — https://support.microsoft.com/en-us/office/using-structured-references-with-excel-tables-f5ed2452-2337-4f71-bed3-c8ae6d2b276e
- Airtable field model (formulas store field IDs) — https://airtable.com/developers/web/api/field-model
- Notion property object (`prop("Name")` saved by ID) — https://developers.notion.com/reference/property-object
- Frictionless Data Package v2 — https://datapackage.org/standard/data-package/ · https://datapackage.org/blog/2024-06-26-v2-release/
- CSVW (W3C RECs, 2015-12-17; `w3c/csvw` archived) — https://github.com/w3c/csvw
- CSV Schema 1.2 (`.csvs`) — https://digital-preservation.github.io/csv-schema/csv-schema-1.2.html
- GFM tables extension — https://github.github.com/gfm/#tables-extension-
- `man 5 gitattributes` (git 2.47.3, local)

**Formats**
- Kova — https://github.com/KovaMD/Kova · engine `src/engine/sheet/` · https://raw.githubusercontent.com/KovaMD/Kova/main/examples/sheet-basics.md · `examples/sheet-reference.md`
- Nimbalyst — https://github.com/nimbalyst/nimbalyst (see `08-nimbalyst-formats.md`)
- sc-im — https://github.com/andmarti1424/sc-im · `examples/sc/a.sc`, `examples/sc/sheets/a.sc`
- fods_minimizer — https://github.com/yurablok/fods_minimizer
- ooxml-git-hooks — https://github.com/scholer/ooxml-git-hooks
- xlsx2csv — https://github.com/dilshod/xlsx2csv
- Grist — https://github.com/gristlabs/grist-core · `documentation/database.md`
- GridHub — https://github.com/decisive-wizard/GridHub
- Univer `IWorkbookData` — https://github.com/dream-num/univer/blob/dev/packages/core/src/sheets/typedef.ts · https://docs.univer.ai/guides/sheets/model/workbook-data
- org-mode spreadsheet — https://orgmode.org/manual/The-spreadsheet.html · https://orgmode.org/manual/References.html
- md-advanced-tables — https://github.com/tgrosinger/md-advanced-tables/blob/main/docs/formulas.md
- tableframe (Typst) — https://github.com/patrick-kidger/tableframe
- ses.el sample — https://github.com/emacs-mirror/emacs/blob/master/etc/ses-example.ses
- marimo — https://github.com/marimo-team/marimo · Pluto.jl — https://github.com/JuliaPluto/Pluto.jl · Observable Notebook Kit — https://github.com/observablehq/notebook-kit

**Engines**
- HyperFormula — https://github.com/handsontable/hyperformula · `LICENSE.txt` · https://registry.npmjs.org/hyperformula/latest
- Handsontable LICENSE.txt — https://github.com/handsontable/handsontable/blob/master/LICENSE.txt
- IronCalc — https://github.com/ironcalc/IronCalc · https://docs.ironcalc.com/
- Univer — https://github.com/dream-num/univer
- Formula.js — https://github.com/formulajs/formulajs
- SheetJS — https://git.sheetjs.com/sheetjs/sheetjs · CVE-2023-30533 · CVE-2024-22363
- formulas (EUPL) — https://github.com/vinci1it2000/formulas · pycel — https://github.com/dgorissen/pycel
- excelize — https://github.com/qax-os/excelize
- LibreOffice recalc reference — https://github.com/anthropics/skills (`skills/xlsx/scripts/recalc.py`)
- unoserver — https://github.com/unoconv/unoserver · JODConverter — https://github.com/sbraconnier/jodconverter

**Diff / merge / versioning**
- daff — https://github.com/paulfitz/daff · spec v0.8 https://paulfitz.github.io/daff-doc/spec.html · https://specs.frictionlessdata.io/tabular-diff/ · issues #215 #216 #217
- csvdiff3 / csvmerge3 — https://github.com/sctweedie/csvdiff3
- csvdiff — https://github.com/aswinkarthik/csvdiff · csv-diff — https://github.com/simonw/csv-diff
- git-xl — https://github.com/xltrail/git-xl · https://www.xltrail.com/blog/merge-excel-workbooks-with-git
- GitHub CSV rendering — https://docs.github.com/en/repositories/working-with-files/using-files/working-with-non-code-files · community discussion #203750
- Dolt — https://github.com/dolthub/dolt · https://www.dolthub.com/docs/concepts/dolt/git/ · prolly trees https://www.dolthub.com/blog/2024-03-03-prolly-trees/ · git remotes https://www.dolthub.com/blog/2026-02-13-announcing-git-remote-support-in-dolt/ · https://www.dolthub.com/blog/2022-07-15-so-you-want-spreadsheet-version-control/
- Semantic merge background — arXiv 1802.06551

**Calculator / units lineage**
- Numbat — https://github.com/sharkdp/numbat · https://numbat.dev/docs/ · `book/src/basics/testing-debugging.md` · `book/src/comparison.md`
- insect (archived) — https://github.com/sharkdp/insect
- Frink — https://frinklang.org/ · https://frinklang.org/faq.html
- Calca — http://calca.io/reference
- Obsidian Numerals — https://github.com/gtg922r/obsidian-numerals
- SoulverCore (closed binary) — https://github.com/soulverteam/SoulverCore · Soulver-CLI (MIT wrapper) — https://github.com/soulverteam/Soulver-CLI
- Qalculate — https://qalculate.github.io/manual/qalc.html · Calcpad CE — https://github.com/imartincei/CalcpadCE
- pint — https://github.com/hgrecco/pint · handcalcs — https://github.com/connorferster/handcalcs
