# W3 — Interop: getting data in and out of `.tbl`

Everything below was run. Tools in `experiments/W3-interop/tools/`, inputs in
`in/`, outputs in `out/`, corpora in `corpus-hunt/`. No packages installed:
no `openpyxl`, no `pandas`. All OOXML is parsed and written with stdlib
`zipfile` + `ElementTree`. LibreOffice 25.2.3.2 is present and is used as an
independent oracle — it both *produces* the test workbook and *reads back*
the one this design writes.

> **Superseded in part by E1 (differential evaluation).** The cell-weighted
> "mechanically translated" figure of 11.4% below counts formulas that fit
> `.mdtbl`'s *surface*. E1 measured the stricter question — translatable **and
> the evaluator implements it** — and the figure is **~7.9%**. The gap is
> `SUM` (5,309 cells), `IF` (12,643), `ROUND` (921), `INT` (621), `MIN`/`MAX`
> (581), unary `+` (384) and `&` (76): 21,165 translatable cells outside §4.2's
> grammar. `CLEAN` here always meant "fits the surface", never "rowspec can
> compute it"; read every number below with that scope.

---

## 0. Verdict up front

**Import is a blocker, not a task. Export is a task, and it is the strongest
adoption argument the design has.**

The asymmetry is the finding. Writing a real `.xlsx` from a `.tbl` is
essentially lossless and was verified end to end against LibreOffice. Reading
a real `.xlsx` into a `.tbl` loses the great majority of every workbook that
contains formulas, and the loss is *structural* — the function library is not
what is missing, the address space is.

    .tbl -> .xlsx -> .tbl        BYTE-IDENTICAL (direct)
    .tbl -> .xlsx -> LibreOffice -> .xlsx -> .tbl
                                 identical but for numeric lexical form
                                 (12.00 -> 12), formulas fully preserved
    .xlsx -> .tbl                5-6% of real formulas translate mechanically
                                 (778,418 cells / 4,130 distinct, SpreadsheetBench)

---

## 1. THE CENTRAL QUESTION: can A1 formulas be mechanically translated?

Yes, and the translator is small. But on real spreadsheets it almost never
fires, and the reason is not the one I expected.

### 1.1 The translator

`tools/a1trans.py`. It normalises each formula to R1C1 relative to its own
cell (so a fill-down column is detected as *one* formula rather than N), then
rewrites every reference that is **same-row, same-sheet and relative** to the
header name of its column. Four verdicts:

    CLEAN           every ref is same-row/same-sheet/relative and every
                    function is in the total, pure, deterministic subset
    CLEAN-WIDE      translates, but only by expanding a horizontal range
                    (SUM(B4:F4) -> SUM(b, c, d, e, f)) -- i.e. the source is
                    wide, which the long/tidy rule says it should not be
    AGGREGATE       a whole-column range over exactly the data rows, in a
                    trailer cell -> `name := sum(col)`
    NEEDS-HUMAN     structurally translatable, semantics absent from .tbl
                    (VLOOKUP/INDEX/MATCH = a join; SUMIF = a filtered
                    aggregate over other rows; TEXT/date functions)
    UNTRANSLATABLE  no mechanical translation at any price

### 1.2 Corpus

No public corpus of *extracted* Enron/FUSE/EUSES formula strings could be
found. EUSES, VFUSE and the SheetJS Enron mirror are all legacy `.xls`, whose
formulas are BIFF RPN token streams, not strings — unreadable without a
decompiler. What was obtained:

| corpus | source | workbooks | formula cells |
|---|---|---|---|
| **SpreadsheetBench 912** | HF `KAKA22/SpreadsheetBench`, real `.xlsx` from Excel help forums | 5,458 | 779,499 |
| SpreadsheetBench verified-400 | same, curated subset | 800 | 27,657 |
| **TmplEnron** | figshare 5838600, real Enron business workbooks | 68 | 817,370 |

**Bias, stated plainly.** SpreadsheetBench is harvested from *help-forum
questions*, so it over-samples hard formulas; TmplEnron is 817k cells but only
**88 distinct** formulas after R1C1 normalisation — template fill-down, so its
cell-weighted number is one formula repeated. Both numbers are therefore
reported, and both cell-weighted and deduplicated.

### 1.3 Results — all figures from one final code revision

**A correction that belongs in the record.** An earlier pass of these numbers
read 2.2% CLEAN and 16.8% NO-HEADER on SpreadsheetBench-912. That was an
importer bug, not a property of the corpus: `sheet_cells` read only `<v>` and
not `<is><t>`, so every sheet whose header row is stored as an inline string
looked headerless. After the fix, NO-HEADER falls to 3.0% and CLEAN rises to
11.3%. Every figure below is from the fixed revision, and the sensitivity —
one XML element changed the headline by 5x — is itself a warning about how
fragile these measurements are.

**SpreadsheetBench 912** — 5,458 workbooks, 778,418 formula cells, under the
`.tbl` language as designed:

    NEEDS-HUMAN        440,842   56.6%
    UNTRANSLATABLE     225,567   29.0%
    CLEAN               88,287   11.3%
    NO-HEADER           23,043    3.0%
    CLEAN-WIDE             531    0.1%
    AGGREGATE              148    0.0%
    ------------------------------------
    MECHANICALLY TRANSLATED         11.4%

Cell-weighting is dominated by a handful of large fill-down workbooks, so the
same corpus deduplicated by R1C1-normalised formula string (n=4,130 distinct):

    UNTRANSLATABLE   2,126   51.5%
    NEEDS-HUMAN      1,784   43.2%
    CLEAN              180    4.4%
    CLEAN-WIDE          30    0.7%
    AGGREGATE           10    0.2%
    ------------------------------
    TRANSLATED                5.3%

The curated verified-400 subset (800 workbooks, 27,657 cells) independently
agrees on the deduplicated figure and is much harsher cell-weighted:

    cell-weighted   CLEAN 1.8% + WIDE 0.2% + AGG 0.0%  =  2.0%
    deduplicated    CLEAN 5.2% + WIDE 0.6% + AGG 0.3%  =  6.1%   (n=1,420)

TmplEnron (68 real Enron business workbooks, 817,370 cells but only 88
distinct formulas):

    cell-weighted   UNTRANSLATABLE 98.3%, NEEDS-HUMAN 1.3%, CLEAN 0.3%
                    (97.7% of ALL cells are one cross-sheet pattern)
    deduplicated    UNTRANSLATABLE 87.5%, NEEDS-HUMAN 11.4%, CLEAN 1.1%

**The robust number is the deduplicated one, and it is 5-6%.** Two independent
subsets of SpreadsheetBench agree (5.3% and 6.1%); real Enron business
workbooks are worse (1.1%).

Top failure reasons on SB-912, as % of all formula cells:

    30.3%  SUMIF/COUNTIF/SUMIFS...  a filtered aggregate over OTHER ROWS
    16.1%  VLOOKUP/INDEX/MATCH      a JOIN; .tbl has no join vocabulary
    11.2%  cross-sheet reference    .tbl has no cross-sheet address
     5.6%  constant formula, no references
     ~9%   further cross-sheet forms (absolute, ranged, column-anchored)
     0.8%  range spans rows other than this one

### 1.4 The ceiling: what if the function library were unlimited?

Re-run with every function permitted, so that **only the addressing rules
apply** (`GWS_CEILING=1`). This separates "the `.tbl` function subset is too
small" (fixable by work) from "the `.tbl` address space cannot express this"
(fixable only by unmaking I2).

    SB-912 cell-weighted   CLEAN 30.1% + WIDE 0.1% + AGG 0.0%  =  30.2%
    SB-912 deduplicated    CLEAN  9.5% + WIDE 1.0% + AGG 0.2%  =  10.7%
    SB-400 cell-weighted   CLEAN  9.7% + WIDE 0.5% + AGG 0.0%  =  10.2%
    SB-400 deduplicated    CLEAN 11.9% + WIDE 0.9% + AGG 0.3%  =  13.1%

**So, on the robust deduplicated measure: 5-6% translate today, and the
absolute ceiling with an unlimited function library is 11-13%.** Growing the
function library roughly doubles the yield and then stops dead. The remaining
~87-89% fails on **addressing**: cross-sheet references, ranges spanning rows,
absolute row anchors, 2-D ranges, and headerless sheets — precisely the
constructs `.tbl` forbids on purpose. They cannot be recovered without
abandoning I2.

Under the ceiling, `UNTRANSLATABLE` *rises* (68.9% deduplicated vs 51.5%),
because formulas previously stopped at "unknown function" now proceed to the
addressing check and fail there instead. That reclassification is the finding:
**the function library was hiding the address space.**

### 1.5 On the hand-built adversarial workbook

`in/book.fods` was authored by hand and converted by LibreOffice to a genuine
engine-written `in/book.xlsx` (3 sheets, 39 formulas, merged cells, defined
names, a comment, cross-sheet and absolute refs, VLOOKUP, INDIRECT, OFFSET,
TODAY, a 2-D range and an array-shaped aggregate). Verdicts on its 21 distinct
formulas:

    UNTRANSLATABLE  12  57.1%
    AGGREGATE        4  19.0%
    CLEAN            3  14.3%
    NEEDS-HUMAN      2   9.5%

The three CLEAN ones are the ones a design document would have written:

    C2*D2                      ->  qty*unit
    G2+H2                      ->  line_total+tax
    IF(C2>10,"BIG","small")    ->  IF(qty>10,"BIG","small")

and the four aggregates land in the `:=` block:

    SUM(C2:C5) -> sum(qty)     SUM(G2:G5) -> sum(line_total)
    SUM(H2:H5) -> sum(tax)     SUM(I2:I5) -> sum(net)

---

## 2. Import fidelity

### 2.1 CSV → `.tbl`

`tools/csvtbl.py`. Input `in/messy.csv` (9 data rows) carries BOM, CRLF,
quoted commas, an embedded newline, ragged rows short *and* long, leading
zeros, five date formats, thousands separators, decimal commas, `(45.00)`,
Excel's `-` null, scientific notation, and four cells that look like formulas.

Real output (`out/messy.rep`):

    NOTE   bom-stripped         file        UTF-8 BOM stripped (C4: no BOM)
    NOTE   crlf-normalised      file        CRLF -> LF (C4)
    NOTE   leading-zero         sku:2       '00123' kept as text
    WARN   thousands-sep        unit_price:2 '1,234.50' -> 1234.50
    REJECT embedded-newline     description:3 one-row-per-line is the merge
                                            invariant (I6) and cannot hold it
    REJECT decimal-comma        unit_price:3 '1.234,50' is 1234.50 under de-DE
                                            and 1.23450 under en-US
    REJECT ambiguous-date       ordered:3   '05/01/2026' is 5 Jan under en-GB
                                            and 1 May under en-US
    WARN   excel-dash-null      notes:3     Excel '-' read as EMPTY
    WARN   formula-looking-cell notes:4     '=SUM(A1:A9)' stored as literal
    REJECT ragged-row           row 6       3 fields, header has 6
    REJECT ragged-row           row 7       8 fields, header has 6
    WARN   accounting-negative  unit_price:9 '(45.00)' -> -45.00
    -- 5 REJECT, 9 WARN, 13 NOTE
    == IMPORT REFUSED: 5 reject(s) ==

**4 of 9 rows (44%) were unimportable without a human decision.** The
rejects are principled, not fussy: each is a case where degrading would
produce a *plausible wrong value*, which is exactly the I7 line. `latin1.csv`
is rejected outright (`byte 18: invalid continuation byte`) — C4 mandates
UTF-8 and there is nothing to guess.

Two CSV findings that bear on the format itself:

- **An embedded newline is unrepresentable.** One row per line is the merge
  invariant; a cell containing `\n` cannot be held without either breaking it
  or inventing an escape that reintroduces multi-line rows. This is a
  permanent CSV→`.tbl` hole, not an implementation gap.
- **`-` is Excel's null and `=`/`+`/`-`/`@` cells are the CSV-injection
  class.** Both are handled by policy, but both are *decisions*, and they
  differ per source application.

### 2.2 `.xlsx` → `.tbl`

Loss report on the real `book.xlsx`, verbatim:

    REJECT multi-sheet          workbook   3 sheets ['Orders','Rates','Archive']:
                                           .tbl is one table per file
    WARN   defined-names        workbook   ['OrderQty','taxrate'] dropped
    WARN   drawing-dropped      workbook   1 part dropped
    WARN   styles-dropped       workbook   25 cell formats, 3 custom number
                                           formats -> all dropped
    REJECT merged-cells-dropped Orders     1 merged cell -- no row-per-line form
    WARN   comments-dropped     workbook   1 cell comment dropped
    NOTE   region-boundary      Orders     data region inferred as rows 2-5;
                                           rows [6,7] read as trailer. THIS
                                           BOUNDARY IS A GUESS.

Lost, categorically, with no `.tbl` vocabulary to receive them: **charts,
pivot tables, drawings/images, conditional formatting, data validation,
frozen panes, autofilter, hyperlinks, all cell formatting, all number
formats, defined names, cell comments, VBA, and every sheet after the first.**
None of this is recoverable by better engineering; `.tbl` has no place to put
it. That is a deliberate design choice and it is the right one, but it must be
stated to users as *"this is a data migration, not a file conversion."*

Three specific hazards worth calling out:

**(a) Excel serial dates silently become integers.** Before adding
`styles.xml` number-format decoding, `2026-01-05` imported as `46027` — a
plausible number, no warning, exactly DESIGN.md's risk-1 shape. Fixed
(`style_datemap` + `serial_to_iso`, including the 1900 leap-year bug), but the
lesson is that **the date/number channel lives in a part an importer is
tempted not to read**, and getting it wrong is silent.

**(b) The data region boundary is undecidable from the bytes.** A sheet does
not say where its table ends. The importer infers it from row *shape* (which
columns hold literals vs formulas) and takes the maximal contiguous run. With
a naive "how many cells are filled" heuristic, the adversarial trailer row was
swallowed into the body and **every column then looked like an inconsistent
fill-down**: the measured translation rate on the same file went from 33% to
0%. The heuristic is load-bearing and it is a guess. It must be reported, and
in a strict tool it should be confirmable by the human.

**(c) Cached values of a rejected formula are a silent-wrong generator.**
Measured directly. Import `book.xlsx`, keeping the cached values of the
cross-sheet `tax` column, then edit `unit` in the `.tbl`:

    as imported:              unit=12  line_total=120.0  tax=9.6  tax_total=29.48
    after editing unit->24:   unit=24  line_total=240.0  tax=9.6  tax_total=29.48

`line_total` tracked the edit; `tax` did not, and there is no `#REF!` and no
warning. Its dependency (`Rates!$B$1`) left the artifact when the workbook was
split. **An importer that keeps cached values manufactures the exact defect
the whole design exists to remove.**

The implemented policy: an untranslatable formula column is a hard REJECT and
nothing is written, unless the human passes `--freeze Sheet.col`, in which
case the column is imported as inert data **and renamed `col_frozen`**, with
every dependent formula and aggregate rewritten to the new name. The freeze is
then legible in the bytes rather than in a log:

    | ... | line_total = qty*unit | tax_frozen | net = line_total+tax_frozen | ...
    tax_total := sum(tax_frozen)

### 2.3 Google Sheets → `.tbl` — **not tested**

No account, no published sheet to fetch, so nothing here was measured. What is
knowable from the formats: a CSV export has no formula channel at all, so it is
strictly the §2.1 path with every formula already collapsed to a value; and the
`gviz/tq` endpoint returns values and column types, not formulas. `values.get`
with `valueRenderOption=FORMULA` is the only route that returns A1 formula
strings, and it needs OAuth. **Untested and should be treated as unknown.**

---

## 3. Export fidelity

### 3.1 `.tbl` → `.xlsx` with a real Excel Table — THIS WORKS

`tools/tbl2xlsx.py` writes the OOXML by hand: `xl/tables/table1.xml` with a
`<table displayName>`, `<tableColumns>`, a `<calculatedColumnFormula>` on each
computed column, `<tableParts>` on the sheet, a totals row of `SUBTOTAL`, a
frozen header pane, and a `yyyy-mm-dd` number format for ISO date cells.

A named `.tbl` column maps 1:1 onto an Excel structured reference:

    total = qty * unit
      ->  Orders[[#This Row],[qty]]*Orders[[#This Row],[unit]]
    grand := sum(total)
      ->  SUBTOTAL(109,Orders[total])

**Verified against LibreOffice, which recalculated the hand-written file:**

    $ libreoffice --headless --convert-to csv out/clean.xlsx
    id,sku,item,qty,unit,total
    r_8f47e7,A-1,widget,10,12,120
    r_ec123b,A-2,gadget,20,6,120
    r_298b7d,A-3,sprocket,5,3.5,17.5
    Total,,,,,257.5

The formulas are live, not baked. Converting the file back to `.xlsx` with
LibreOffice shows the ListObject and the structured references survive
verbatim:

    <f aca="false">Orders[[#This Row],[qty]]*Orders[[#This Row],[unit]]</f>
    <f aca="false">SUBTOTAL(109,Orders[total])</f>

**This is the design's strongest interop asset and it should be built first.**
Structured references are the exact same idea as named-column formulas — Excel
already has the target language. "Edit in `.tbl`, hand your colleague a real
Excel file with live formulas that fill down on insert" is true, tested, and
requires no plugin on their side.

Two caveats measured, not assumed:
- LibreOffice **drops `<calculatedColumnFormula>`** from `tableColumns` on
  re-save while keeping the per-cell formulas. Excel's auto-fill-on-insert
  therefore may not survive a LibreOffice round trip. Untested in Excel proper.
- `key := sku` and aggregate *names* have no OOXML home. Solved by writing them
  into `docProps/custom.xml` as a `gws.tbl` custom property — an inert channel
  the spreadsheet ignores and the importer restores. Verified.

### 3.2 Round trips

    .tbl -> .xlsx -> .tbl                     BYTE-IDENTICAL   (diff empty)
    .tbl -> .xlsx -> LibreOffice -> .xlsx -> .tbl
        identical except  12.00 -> 12 and 3.50 -> 3.5

The only residual loss is **numeric lexical form**: a spreadsheet stores an
IEEE double, so trailing zeros are gone forever. Byte-stability across a
spreadsheet is therefore impossible in principle, and the design should say so
rather than promise it. Everything semantic — formulas, aggregate names, key
declaration, row ids — survives.

    CSV -> .tbl -> CSV     identical to the source CSV once the derived
                           column is dropped

### 3.3 `.tbl` → CSV — what is lost

Three things, all of them structural:

1. **Formulas.** CSV has no formula channel. Either the header carries
   `total = qty*unit` (and the file is no longer a CSV any consumer
   understands) or the column is materialised as values (and the formula is
   gone). Materialising is right; it is one-way.
2. **Aggregates.** `grand := sum(total)` has nowhere to go. A trailing row
   would make the CSV ragged and would be re-imported as data.
3. **Row ids become an ordinary column** — visible, sortable, deletable, and
   therefore no longer machine-managed. `--drop-id` is offered, but dropping it
   is what breaks re-import (§4).

**CSV → `.tbl` → CSV is not and should not be byte-stable.** The `.tbl` is the
canonical artifact; the CSV is a projection. Promising byte-stability here
would force the `.tbl` to carry the CSV's quoting, line-ending and numeric
lexical decisions, which is coupled representation (I1) by another name.

### 3.4 `.tbl` → markdown / HTML

`tools/tblrender.py`: evaluate, then emit. The id column is presentation noise
and is dropped by default (it moves to `data-id` in HTML, which is where a
comment anchor or a diff link would attach).

    | sku | item     | qty | unit  | total |
    | --- | -------- | --- | ----- | ----- |
    | A-1 | widget   | 10  | 12.00 | 120   |
    ...
    grand = 257.5

---

## 4. Row-id stability across re-import — designed and tested

This is the hard one. Month 1 a spreadsheet is imported and committed; month 2
the colleague re-exports it with rows added, edited, deleted and reordered.
If the ids move, the git history means nothing.

`tools/idstab.py` builds a real git repo and compares five identity functions
across three scenarios. Scenario 1: one cell edited, one row deleted, two rows
added, one text field changed, **and all rows reordered**.

    M1 positional     id = row number
    M2 content-hash   id = hash(all cells)
    M3 natural-key    id = hash(key column)
    M4 three-tier     carriage -> declared key -> exact-content match -> mint
    M5 M4 + stable order (matched rows keep the previous file's line order,
                          new rows appended)

### Scenario 1 — edits + delete + 2 inserts + reorder, key stable

    method        kept  of  wrong-new reused-wrong  git diff +/-  dup-ids
    M1 position      2   5          3            1  +5/-4         0
    M2 content       3   5          2            0  +5/-4         0
    M3 natkey        5   5          0            0  +5/-4         0
    M4 three-tier    5   5          0            0  +5/-4         0
    M5 M4+order      5   5          0            0  +4/-3         0

M1 reassigns 3 of 5 stable rows and **re-uses a dead row's id for a new row**
(`reused-wrong=1`) — a silent identity collision. M2 splits a row on any edit.
M4/M5 keep every id. The result is the same whether or not the re-export
carried the id column back, because the declared key catches it either way.

M5's actual diff, which is the whole point:

    @@ -5,3 +5,2 @@
    -| r_f1d175 | A-3 | sprocket | 5 | 3.50 |
    -| r_7420d5 | A-4 | flange | 12 | 9.25 |
    -| r_36f93e | A-5 | bolt | 100 | 0.15 |
    +| r_f1d175 | A-3 | sprocket | 8 | 3.50 |
    +| r_36f93e | A-5 | bolt M6 | 100 | 0.15 |
    @@ -8,0 +8,2 @@
    +| r_070a46 | A-7 | washer | 50 | 0.05 |
    +| r_beab3b | A-8 | rivet | 25 | 0.30 |

Two edits, one deletion, two insertions — the semantic change, exactly. **Row
order in the source is noise and the importer must own it**; without M5's
stable ordering the same change reads as five rewritten rows.

### Scenario 3 — the source now contains a duplicate row

    method        kept  of  wrong-new reused-wrong  git diff +/-  dup-ids
    M2 content       7   6          0            0  +1/-0         1
    M3 natkey        7   6          0            0  +1/-0         1
    M4 three-tier    6   6          1            0  +1/-0         0
    M5 M4+order      6   6          1            0  +1/-0         0

Content-hash and natural-key both **emit two rows with the same id** — an I2/I5
violation that no downstream tool would notice. Only the used-set discipline in
M4/M5 (an id may be claimed once) avoids it. A duplicate row id must be a hard
parse error, and the importer must be structurally incapable of producing one.

### A separate defect this test exposed: padded alignment is coupled state

Scenario 2 changes exactly one cell — a sku corrected from `A-3` to `A-3X`,
one character longer. With the padded rendering that DESIGN.md §7 shows:

    all five methods:  +8/-8    (the entire file rewritten)

With unpadded rendering:

    all five methods:  +1/-1

**Column-alignment padding is state whose bytes must change when unrelated
content changes** — DESIGN.md §4's own definition of the defect the design is
organised against, present in the format's own worked example. Widening one
cell rewrites every row, destroys the diff, and turns two disjoint edits into a
conflict. The `.tbl` renderer must not pad, or padding must be a view-time
concern only.

### The recommended mechanism, stated

    T0  CARRIAGE.     If the source carries an `id` column matching `r_[0-9a-f]+`,
                      reuse it verbatim. Every exporter this project writes
                      emits the id column, so the common case is exact.
    T1  DECLARED KEY. Else, if `key := col` is declared and the value matches a
                      previous row's key, reuse that row's id.
    T2  EXACT CONTENT. Else, if the row's cell-tuple exactly matches an unclaimed
                      previous row, reuse that id.
    T3  MINT.         Else mint a fresh opaque id. Never reuse a claimed id.
    T4  STABLE ORDER. Emit matched rows in the previous file's order; append new
                      rows. Source row order is not semantic and is discarded.
    T5  REPORT.       Print `carried=/by_key=/by_content=/minted=` on every run.
                      A re-import whose `minted` count is near the row count is
                      a failed match, not a rewritten spreadsheet, and should
                      require confirmation.

Note T2 is the same two-stage exact-then-refuse shape as the design's 92.9%
quote-anchoring result, and for the same reason: an exact match is the only
match that can never be silently wrong. No fuzzy row matching is proposed —
a wrong fuzzy match silently transfers one row's history to another row.

**Honest limit.** If the source loses the id column *and* has no stable natural
key *and* rows have been edited, T2 misses and T3 mints. Nothing recovers this;
the information is not in the file. The design answer is to make the id column
survive — which is why every exporter here emits it and why `--drop-id` should
carry a warning that it makes the next re-import non-continuous.

---

## 5. Recommended import/export design

### 5.1 What the import tool does when it hits something untranslatable

Not "refuse the whole workbook", and not "import and hope". Three tiers, and
the boundary is I7's: *could degrading yield a plausible VALUE?*

    STRUCTURE that cannot be represented and could change a value
      (untranslatable formula column, ragged row, decimal comma, ambiguous
       date, merged cell, embedded newline, duplicate column name)
        -> REJECT.  Nothing is written.  The report names the sheet, the
           cell, the formula and the reason, and offers the one escape.

    STRUCTURE that cannot be represented and could only lose DECORATION
      (styles, number formats, charts, pivots, conditional formatting,
       data validation, frozen panes, comments, drawings)
        -> WARN and drop.  Counted in the report, never silent.

    A REJECT the human explicitly accepts
        -> `--freeze Sheet.col` imports the cached values as inert data AND
           RENAMES the column `col_frozen`, rewriting dependents.  The
           acceptance is recorded in the bytes, not in a log that is thrown
           away.  A reader seeing `tax_frozen` knows the number is not live.

So: **a workbook with an `INDIRECT` formula does not import.** The tool exits
non-zero, writes nothing, and prints the cell. If the human decides that column
is dead data, `--freeze` makes it dead data *visibly*. That is the only
behaviour consistent with I3 and I7, and §2.2(c) shows what the alternative
costs.

One gap found and not fixed: the translator emits `IF(qty>10,"BIG","small")`,
which the reference evaluator in `experiments/L1-nominal-merge/tbl.py` cannot
parse (it handles `+ - * /` only). **The import target language is
under-specified relative to what translation produces.** The `.tbl` function
set must be pinned in the spec before an importer can claim a success rate.

### 5.2 One-shot or continuous?

**One-shot for import; continuous for export.** Argued, not asserted:

- Continuous import requires the spreadsheet to remain authoritative, which
  means the `.tbl` is a cache. A cache cannot be reviewed, and review is the
  design's entire stated value (§1 of DESIGN.md: "Not authoring. Storage and
  review"). Two-way sync would also need the untranslatable 88-94% to survive
  a round trip through `.tbl`, which §1 shows it cannot.
- Continuous import is also unsound under the design's own rules: re-importing
  a workbook whose derived columns were computed elsewhere commits derived
  values whose dependency set spans more than one entity — the I4 violation
  measured in §2.2(c).
- But **re-import must still work**, because migration is not one commit. A
  three-month migration re-imports the same source repeatedly while columns
  are fixed one at a time. §4's mechanism exists for that: repeated import
  during migration, converging on a `.tbl` that is authoritative, after which
  the source is retired.
- Export, by contrast, should be continuous and cheap: `.tbl` → `.xlsx` is
  lossless and verified, so a colleague can be handed a fresh live workbook on
  every commit. That is the shareable artifact, and it is a build output, not
  a source.

The user-facing sentence should be: **"Import migrates a spreadsheet once.
Export regenerates a spreadsheet every time."**

### 5.3 What to build, in order

1. **`.tbl` → `.xlsx` with structured references.** Verified working, small,
   and it is the entire adoption story. Ship it first.
2. **`.tbl` → CSV / markdown / HTML.** Trivial, done here in 40 lines.
3. **CSV → `.tbl`** with the report and the reject policy. This is the
   realistic import path, because ~93% of spreadsheets have no formula at all
   (DESIGN.md §1: only ~7% do) and for those a CSV export loses nothing.
4. **`.xlsx` → `.tbl`** as a *migration assistant*, not a converter. Its
   primary output is the loss report; the `.tbl` is secondary. Sell it as
   "tells you what will not survive", never as "converts your workbook".
5. Google Sheets: untested here. `values.get?valueRenderOption=FORMULA` is the
   only route that returns formulas and it needs OAuth.

---

## 6. Where interop is a blocker rather than a task

Five, in descending severity.

**1. Formula import is not viable and should not be promised.** 5-6% of real
formulas translate; the ceiling with an unlimited function library is 11-13%.
Any messaging that implies "bring your spreadsheets" is false. The honest
framing — *"bring your data; formulas are rewritten by a human, and the tool
tells you exactly which ones"* — is defensible and is what the report supports.
This does not sink the design, because ~93% of spreadsheets have no formulas,
but it does sink the demo where a real workbook is converted on stage.

**2. `.tbl` is one table; a workbook is a graph.** The single most common
failure at 11%+ of cells is the cross-sheet reference, and it is not an
oversight — it is I2 applied across files. Splitting a workbook into one
`.tbl` per sheet severs every cross-sheet edge, and there is no cross-artifact
address in the design that could receive them. Either a cross-artifact
reference exists (and I2 must be extended to it, with the merge consequences
worked out) or multi-sheet workbooks are permanently out of scope. **This is
an unresolved design question, not an implementation gap.**

**3. `.tbl` has no join and no filtered aggregate, and together those are 46%
of real formulas.** *(WITHDRAWN AS ARGUED — see the addendum, §A.6. Both were
subsequently implemented in `experiments/X6-joins/ref_tbl.py`; neither is
forbidden by row-independence, because neither is positional. The measured
effect is 5.3% -> 6.9% deduplicated. The remaining gap is conjunction,
group-by and composite keys, not the constructs themselves.)* `VLOOKUP`/`INDEX`/`MATCH` (16.1%) and
`SUMIF`/`COUNTIF`/`SUMIFS` (30.3%) are the two most common things people
actually do. Both are *cross-row* operations, which is the one thing the
row-independence that makes `.tbl` merge correctly forbids. There may be a
safe, order-independent, declarative form of each — a join on a declared key,
and a grouped aggregate — but neither exists in the design and both need the
merge analysis done before they are added.

**4. The padded rendering in DESIGN.md violates I1.** One character in one cell
rewrote 8 of 8 lines. This is the eighth instance of the pattern in the report's
own appendix and it is in the format's flagship example. Cheap to fix, but it
must be fixed in the spec and in the conformance suite, not in a renderer.

**5. Two smaller things that will bite.** (a) The data-region boundary is a
guess and a bad guess collapsed the measured translation rate from 33% to 0% on
the same file — a conformance suite needs region-detection cases. (b) The
example `.tbl` in DESIGN.md §7 does not parse with the design's own reference
implementation: `key := id` is rejected as a malformed aggregate declaration
(`experiments/L1-nominal-merge/tbl.py:38`). The `key` declaration is in the
prose and not in the grammar.

---

## 7. What could not be tested, and why

- **Microsoft Excel itself.** Not available. Every "does it open" claim is
  LibreOffice 25.2.3.2 only. `<calculatedColumnFormula>` auto-fill on row
  insert is declared in the file this design writes and is *not* verified in
  Excel; LibreOffice drops the element on re-save.
- **Google Sheets.** No account and no published sheet. Nothing measured.
- **Charts, pivot tables, conditional formatting, data validation.** The
  importer detects and reports these parts, but LibreOffice's `.fods` → `.xlsx`
  filter did not carry the conditional-format block through, so only merged
  cells, comments, defined names, drawings and styles were exercised against a
  real part. The conclusion is unaffected — `.tbl` has no vocabulary for any of
  them, so the loss is 100% by construction — but the *detection* code for
  charts and pivots is untested against a file that has them.
- **`.xls` (BIFF).** Three of the candidate corpora (EUSES, VFUSE, the SheetJS
  Enron mirror, ~6.5 GB) are legacy `.xls`, whose formulas are RPN token
  streams rather than strings. Not parseable with stdlib. Any claim about
  pre-2007 spreadsheets is unmeasured.
- **Array formulas and spill ranges.** The fixture's array-shaped construct was
  flattened by the ODF→OOXML conversion, so the `t="array"` / `ref=` path in
  the importer is unexercised.
- **Scale.** The largest `.tbl` written here is 7 rows. Nothing is known about
  importing a 200,000-row sheet, and `git diff` behaviour at that size is
  untested.

---

## 8. Files

    tools/csvtbl.py     CSV <-> .tbl, report, reject policy, id assignment
    tools/a1trans.py    A1 -> named-column translator; OOXML reader;
                        R1C1 normaliser; structured-reference reader;
                        Excel serial-date decoding
    tools/xlsx2tbl.py   .xlsx -> .tbl with the loss report and --freeze
    tools/tbl2xlsx.py   .tbl -> .xlsx: real ListObject, structured references,
                        SUBTOTAL totals row, gws.tbl sidecar property
    tools/tblrender.py  .tbl -> markdown / HTML
    tools/corpus_run.py the corpus harness (GWS_CEILING=1 for the ceiling run)
    tools/idstab.py     row-id stability, 5 methods x 3 scenarios, real git
                        (GWS_PAD=0 for the unpadded comparison)
    in/messy.csv        BOM/CRLF/ragged/quoted/5-date-format torture CSV
    in/book.fods,.xlsx  the adversarial workbook (LibreOffice-produced OOXML)
    out/*.json,*.txt    raw corpus results

---
---

# ADDENDUM — re-measured against the X6-joins extended grammar

Added after the coordinator implemented filtered aggregates and cross-table
lookup in `experiments/X6-joins/ref_tbl.py`. **My §6 blocker 3 was wrongly
argued and is withdrawn as stated.** I wrote that joins and filtered aggregates
are "cross-row, which is the one thing row-independence forbids." That
conflates *cross-row* with *positional*, and the coordinator is right: both
constructs are nominal and neither is forbidden. The corrected claim is
narrower and is measured below — the constructs are expressible, but the
**shapes real spreadsheets use** mostly do not fit the forms implemented.

## A.0 Comparability

Same corpora, same harness, same `translate()` entry point. The extension is
behind `GWS_EXT=1`, so both arms run the identical code path. Verified: with
the flag off, the refactored harness reproduces the baseline exactly
(SB-400: 27,657 cells, CLEAN 1.8% / WIDE 0.2% / AGG 0.0%). Two things that
make the arms *not* perfectly comparable, both stated:

- The extension **intercepts** same-row horizontal `COUNTIF(B4:F4,…)` shapes
  that the baseline ceiling had counted as `CLEAN-WIDE`. This is why the
  ceiling arm goes very slightly *down*.
- I also verified the emitted strings against the coordinator's own evaluator
  rather than only against my classifier (§A.4).

## A.1 New rates, side by side — SpreadsheetBench-912 (5,458 workbooks, 778,418 cells / 4,130 distinct)

| measure | baseline | **extended** | change |
|---|---|---|---|
| cell-weighted | 11.4% | **11.5%** | +0.1 pt |
| **deduplicated** (robust) | 5.3% | **6.9%** | **+1.6 pt (+30% relative)** |
| ceiling, cell-weighted | 30.2% | 29.5% | −0.7 pt |
| ceiling, deduplicated | 10.7% | **11.3%** | +0.6 pt |

Extended breakdown, cell-weighted / deduplicated:

    CLEAN              88,287  11.3%   |   180   4.4%
    CLEAN-LOOKUP          681   0.1%   |    55   1.3%
    CLEAN-WIDE            531   0.1%   |    30   0.7%
    AGGREGATE-FILTER      126   0.0%   |    11   0.3%
    AGGREGATE             148   0.0%   |    10   0.2%
    ---------------------------------------------------
    TRANSLATED                 11.5%   |         6.9%

**The extension is real but small.** `lookup()` is the larger of the two: it
roughly triples the deduplicated non-arithmetic yield (0.2% → 1.6%). Filtered
aggregates contribute 0.3 points. Neither moves the order of magnitude.

## A.2 How much of the SUMIF-family 30.3% becomes translatable? — 0.5%

23,376 SUMIF/COUNTIF/AVERAGEIF/SUMIFS/COUNTIFS/MINIFS/MAXIFS formulas were
attempted. **126 translated (0.5%).** Every rejection is instrumented:

    14,861  63.6%  MULTI-PREDICATE (SUMIFS/COUNTIFS with 2+ criteria pairs)
     5,322  22.8%  range is in ANOTHER WORKBOOK FILE ([n]Sheet!...)
     1,504   6.4%  range spans SEVERAL COLUMNS of one row (wide row-wise count)
       576   2.5%  aggregating a column with no header name
       489   2.1%  criterion is a CELL REFERENCE -> a per-row GROUP aggregate
       309   1.3%  range is not a plain range (defined name, structured ref)
        72   0.3%  criterion range on another sheet
        66   0.3%  criterion is a bare number, not a quoted literal
        21   0.1%  criterion is a computed expression
        12   0.1%  criterion is a COMPARISON (">100")
         3   0.0%  literal criterion but the cell is inside the data region
    -------------
       126   0.5%  CLEAN

**My a-priori worries were the wrong ones.** I expected numeric comparisons and
wildcards to dominate the miss. They are *negligible* — 12 comparisons and
zero wildcards in 23,376 formulas. The gap is **conjunction**: two-thirds of
real SUMIF-family usage is `SUMIFS` with more than one predicate. `where col =
"lit"` is a single equality and cannot express `region = "EU" AND year = 2026`.

Second: **the group-by case is missing and it is a different construct.** 489
formulas use a cell reference as the criterion — `SUMIF($A$2:$A$100, A2,
$B$2:$B$100)`, "the total for *this row's* category". That is not a table
scalar declared in the `:=` block; it is a **column formula** whose value is a
grouped aggregate. The grammar has no `groupsum(col by pcol)` and cannot
express it. It is also the most `.tbl`-shaped of all the misses, because it is
per-row and fully nominal.

Concrete SUMIF-family shapes from the corpus that the grammar does not reach:

    SUMIFS(C3:C8,A3:A8,I3,B3:B8,J3)      two predicates, both cell refs
    COUNTIF($B6:$AF6,$AG$5)              31 columns of ONE row (wide)
    SUMIF(A:A,A2,B:B)                    group total for this row's key

## A.3 Does `lookup()` cover real VLOOKUP usage? — 3.1%, and fewer than half of targets are keys

21,815 lookup-family formulas (14,037 INDEX, 7,775 VLOOKUP, 3 HLOOKUP).
**681 translated (3.1%).**

    12,264  56.2%  INDEX shapes that are not a 2-arg INDEX/MATCH key lookup
     4,767  21.9%  target is ANOTHER WORKBOOK FILE
     1,686   7.7%  table_array is not a resolvable range (defined name, #REF!)
       966   4.4%  the matched column is NOT UNIQUE -> cannot be a declared key
       959   4.4%  the returned column has no header name
       402   1.8%  key is not a same-row relative reference
       120   0.6%  VLOOKUP column index is computed, not a literal
        81   0.4%  APPROXIMATE match (VLOOKUP 4th arg TRUE/omitted, MATCH type≠0)
     -----
       681   3.1%  CLEAN

**Again my a-priori worry was wrong.** Approximate match is 81 of 21,815 —
**0.4%**, not a problem. Positional column indexing is not a problem either:
`col_index` resolves against the target's header row mechanically, and only 120
cases use a computed index.

**The two answers that matter:**

1. **What fraction of real lookups target a column that could be a declared
   key?** Of the lookups that resolved far enough to test it, 681 were unique
   and 966 were not: **41.3% key-ness on SB-912** (27.5% on SB-400). *Fewer
   than half of real lookup targets are keyed at all.* The rest look up on a
   column with repeated values — a one-to-many relation, which `lookup()`
   cannot express and which arguably should not silently pick a row.

2. **INDEX/MATCH is mostly not a key lookup.** Breaking down 4,506 INDEX
   formulas in SB-400 by why they fail:

        32.1%  return range is not a range -- 1,342 of these are literally
               `#REF!`: the formula is ALREADY BROKEN in Excel
        31.5%  MATCH key is a computed expression (composite key `A17&C17`)
        17.0%  3-arg INDEX = a 2-D MATRIX lookup (row AND column index)
         9.3%  reaches the key test
         4.9%  2nd arg is not MATCH (array/SMALL/ROW filtered extraction)
         2.4%  external workbook
         2.1%  MATCH type != 0

   The 17.0% matrix lookups are wide-table by construction and have no
   long-form equivalent. The 31.5% composite keys (`MATCH(A&B, X&Y, 0)`) are a
   **two-column key**, which `.tbl`'s single `key := col` cannot declare.

### Three adversarial findings against the extension

**(a) `.tbl` permits ONE declared key per table; a workbook may look up the
same sheet on several columns.** `lookup()` resolves by the *target's* declared
key, so a second lookup into the same table on a different column is
untranslatable no matter how unique that column is. Measured on SB-400: only
8 distinct lookup targets were reached and all 8 were matched on a single
column — **n=8 is far too small to conclude anything**, and this remains an
open risk rather than a measured one.

**(b) Composite keys are unrepresentable.** `MATCH(A17&C17, $A$5:$A$10&$B$5:$B$10, 0)`
is 31.5% of INDEX usage in SB-400. `key := col` takes one column.

**(c) 21.9% of lookups already point at another workbook FILE.** This is the
strongest *positive* result for the design in the whole addendum. A fifth of
real lookups are already cross-artifact, not cross-sheet — which is exactly the
shape `lookup(other.tbl, …)` has. The design's cross-artifact address is
validated by real usage; it simply cannot fire during a single-file migration
because the referenced file is not in the corpus.

## A.4 The emitted syntax evaluates in the reference implementation

Not merely classified — round-tripped through `experiments/X6-joins/ref_tbl.py`
using two translations taken verbatim from the corpus run:

    | id | sku | region | total | who = lookup(Sheet2.tbl, sku, name) |
    key := id
    eu := sum(total where region = "EU")

    {'id':'r1','sku':'A-1','region':'EU','total':'100','who':'Acme'}
    {'id':'r2','sku':'A-2','region':'US','total':'250','who':'Borax'}
    {'id':'r3','sku':'A-9','region':'EU','total':'40',
     'who':'#REF!(Sheet2.tbl[A-9])'}
    eu = 140.0     all = 390.0

A dangling key fails loudly and the filtered aggregate is correct. Real corpus
translations, verbatim:

    INDEX(Sheet1!B$2:B$17,MATCH($A2,Sheet1!$D$2:$D$17,0))
        -> lookup(Sheet1.tbl, Existing_Data_Fields, Deal_Name)
    COUNTIF(S:S,"Y")
        -> count(Matches_ where Matches_ = "Y")

## A.5 A corpus caveat that cuts both ways

**5.4% of formula cells in SB-400 contain a literal `#REF!`** — they are
already broken in Excel and were silently carried in the saved file. They
inflate the untranslatable bucket in both arms equally, so the before/after
comparison is unaffected. But they are also evidence *for* the design: Excel
stored, saved and redistributed 1,519 broken formulas without ever refusing.

## A.6 The corrected headline

The sentence stands, and the number that supports it barely moved: **5.3% →
6.9% deduplicated, 11.4% → 11.5% cell-weighted.** What changes is the
*diagnosis*, which was wrong and is worth correcting because it points at the
next work.

> **Before (my §6, withdrawn):** "No join, no filtered aggregate = 46% of real
> formulas. Both are cross-row, which is the thing row-independence forbids."
>
> **After:** Joins and filtered aggregates are *not* forbidden — both are
> nominal and both merge correctly. They are implemented and they work. But
> the forms real spreadsheets use are conjunctive (`SUMIFS`, 63.6% of the
> filtered-aggregate miss), grouped per-row (`SUMIF(A:A, A2, B:B)`),
> composite-keyed (`MATCH(A&B, …)`, 31.5% of INDEX), matrix-shaped (17.0% of
> INDEX), or aimed at another workbook file (21.9% of lookups). Adding
> conjunction and group-by is the highest-yield remaining work; nothing
> reaches the majority of real formulas.

**Recommended user-facing sentence, unchanged in substance and sharpened:**

> *"Bring your data. Formulas are rewritten by a human — the tool translates
> the arithmetic, the column totals, the filtered totals and the keyed lookups,
> and tells you cell by cell which of the rest need you."*

And the honest internal number, which should not be softened: **the importer
mechanically translates about 7% of real spreadsheet formulas, with a ceiling
near 11%.** That is a migration assistant, not a converter, and the report's
§5.3 build order is unchanged by this addendum.

## A.7 Highest-yield next extensions, ranked by measured miss

    1. CONJUNCTIVE predicates   `sum(t where a = "x" and b = "y")`
                                63.6% of the filtered-aggregate miss
    2. GROUP-BY column formula  `share = total / groupsum(total by region)`
                                the SUMIF-with-cell-ref case; per-row and
                                fully nominal, so it fits the model exactly
    3. COMPOSITE keys           `key := (region, sku)`
                                31.5% of INDEX usage; also removes the
                                single-declared-key risk in A.3(a)
    4. COMPARISON predicates    measured at 0.1% -- DO NOT BUILD THIS FIRST
