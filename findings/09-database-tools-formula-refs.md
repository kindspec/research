# How the database/spreadsheet-hybrid tools address fields

Relayed from a sub-agent research pass, 2026-08-28. Covers Airtable, Notion, Coda,
Baserow, NocoDB, Teable, Grist. Verification labels are that agent's own; the
"NOT VERIFIED" list at the bottom is preserved deliberately.

## The headline: nobody uses A1

**None of the seven is positional/A1-style.** Coda states it outright:
"In Coda, all objects have names. No coordinates needed!"

This is independent corroboration of the pattern already seen in Kova (`!sheet`,
named columns) and Nimbalyst `calc-sheets` (named variables). Every serious
modern design has abandoned cell coordinates. A1 survives only in Excel/Sheets
lineage products — including Nimbalyst's own `csv-spreadsheet` extension.

## Name vs ID in storage, and what happens on rename

Three families:

**ID in storage, name shown in the editor (rename-safe by construction):**

- **Airtable** — VERIFIED. Field model docs: "The formula including fields
  referenced by their IDs. For example, `LEFT(4, {Birthday})` in the Airtable.com
  formula editor will be returned as `LEFT(4, {fldXXXXXXXXXXXXXX})` via API."
- **Notion** — VERIFIED. Property-object docs: `prop("Name")` matches by current
  name, "but the saved formula references the property by ID, so renaming the
  property later doesn't break the formula." Wire form
  `{{notion:block_property:...}}`, itself writable.
- **Teable** — VERIFIED from source. Stored expression is `{fldXXXXXXXX}`;
  `{Unit price}` is a display projection. `formula.field.ts` has
  `convertExpressionIdToName()` / `convertExpressionNameToId()` via a
  `ConversionVisitor`; the token reader is `extractFieldReferenceId()`.
- **NocoDB** — VERIFIED from source, dual storage. `FormulaColumn.ts` persists
  both `formula` (ID-keyed, via `substituteColumnAliasWithIdInFormula`) and
  `formula_raw` (names, for display).

**Name in storage, rewritten on rename (the outlier):**

- **Baserow** — VERIFIED, `formula/handler.py`. The user-facing `formula` stores
  NAMES; a derived `internal_formula` uses `field_{id}`. Rename rewrites the raw
  string via `rename_field_references_in_formula_string()`. Consequence: a rename
  that happens outside the app's rename path (a restore, a botched import) can
  strand a formula. Baserow's own documented remedy for a broken reference is
  "Rename another field to match the deleted field's name."

**ID in storage, derived from the label but explicitly untieable:**

- **Grist** — VERIFIED, `app/client/ui/FieldConfig.ts`. Panel section "COLUMN
  LABEL AND ID"; the `colId` input is readonly unless `untieColIdFromLabel` is
  set; while tied, editing the label recomputes `"$" + sanitizeIdent(edited)`.
  The only user-facing escape hatch in the set.

**Why this matters for a git-backed design.** These tools all keep an ID
indirection because their storage is a database nobody reads. A plaintext file in
git has the opposite requirement: the stored form has to be the *human* form, or
diffs are meaningless. Baserow's name-in-storage model is therefore the closest
analogue to what a git-backed suite must do — and Baserow's own failure mode
(rename outside the app strands the formula) is precisely the risk a file-based
product inherits, because in a git repo, edits outside the app are normal, not
exceptional. That risk is the price of a readable diff, and it should be designed
for rather than wished away.

## Whole-column aggregates

Only **Grist** can aggregate a whole column inside an ordinary cell formula. The
other six push it to a Rollup/Lookup field over a link or relation.

- **Airtable** — VERIFIED: impossible in a formula field. Requires a Rollup field
  over a linked-record field: `SUM(values)`, `AVERAGE(values)`,
  `ARRAYJOIN(values, "; ")`. `values` is a magic name for collected linked-record
  values, *not* a column reference.
- **Notion** — REPORTED: Rollup properties over relations; 2.0 formulas can
  traverse a relation and aggregate (`.map()` / `.sum()`).
- **Coda** — VERIFIED in shape:
  `[Groceries].Filter(Department.Contains("Produce")).Count()`.
- **Baserow** — `lookup()` VERIFIED in the grammar; `sum(lookup(...))` wrapping
  REPORTED only.
- **NocoDB** — VERIFIED: none in-formula; Rollup over a Links field. Conditional
  rollups are paid-tier.
- **Teable** — REPORTED only: Rollup field over a Link field.
- **Grist** — VERIFIED, the differentiator: `SUM(Materials.all.Price)`,
  `SUM(Incoming_Order_Line_Items.lookupRecords(SKU=$id).Received_Qty)`,
  `Materials.lookupOne(Quantity=52).Product`, `SUM($Requirements.Cost)`.
  Summary tables: `len($group)`, `SUM($group.AnnualPay)`, and arbitrary Python
  conditional aggregation —
  `SUM(r.AnnualPay for r in $group if r.EmploymentStatus == "Active")`.

Note how Kova's footer-row rule (`| !Total |` where a bare column name means the
whole column) is a compact solution to exactly the problem that forces six of
these seven products into a separate field type.

## Licence corrections — consequential

- **NocoDB is no longer open source.** Relicensed off AGPL-3.0 on **2026-01-08**
  to the Sustainable Use License v1.0: "You may use or modify the software only
  for your own internal business purposes or for non-commercial or personal use."
  Confirmed in git history — commit `d98ad39c` deletes the 661-line AGPLv3 file
  and adds `LICENSE.md`; `8264821b` (2026-01-29) extends the grant to `develop`.
  Despite 64.7k stars and a "Free & Self-hostable" tagline, do not group it with
  the open-source options.
- **Teable** is split: `apps/*` AGPL-3.0, `packages/*` MIT, plus §7(e) brand terms.
- **Baserow** is not plain MIT: MIT Expat for OSE + client JS, `premium/` and
  `enterprise/` proprietary, `docs/` CC BY-SA 4.0.
- **Grist** Apache-2.0 is the only clean single OSI licence at a repo root here.

Repo notes: Baserow migrated GitLab→GitHub (GitLab now self-describes as a
mirror; use the 5,742 GitHub stars, not 2,265). Teable's `develop` last moved
2026-07-29 though a release was cut 2026-08-19 and head commits are prefixed
"[sync]" — development is not fully in the open.

## Explicitly NOT verified — do not quote as confirmed

Coda rename stability (inferred from chip semantics only); a literal Coda
`.Sum()`; Teable and Notion rollup mechanics; Baserow's `sum(lookup(...))`
wrapping.

Retracted by the source agent: any claim that Baserow uses square brackets
(`[Quantity] * [Unit Price]`). A re-fetch of the raw user-docs page found zero
occurrences of `field(` and only nav chrome — the earlier summary was
confabulated. The ANTLR grammar and formula-field-overview both say `field('name')`.

Tooling note: `coda.io/formulas` now 307-redirects to a JS-rendered SPA that
WebFetch cannot read; the readable source is help.coda.io's Zendesk JSON API,
`https://help.coda.io/api/v2/help_center/en-us/articles/{id}.json`.
