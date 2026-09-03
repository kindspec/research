<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# M3 — what the registries actually built, and where rowspec's boundary sits

Read-only research pass, 2026-08-29. Four repositories shallow-cloned to `/tmp`,
their real validation code read and quoted, and `rowspec check` run against their
real data. **Nobody was contacted; no outreach material exists.** Task 5 of the
original brief (draft an outreach message) was withdrawn mid-pass and no draft
was written.

Clones: `iptv-org/database` @ `9c6f01e`-era HEAD, `datasets/country-codes`,
`toolleeo/awesome-cli-apps-in-a-csv` @ `cb254f2`,
`ccao-data/data-architecture` @ `ee49d81` (2026-08-28).

---

## 0. Verdict

**The addressable surface is the file-shape layer, and on these four
repositories it is between 0% and 19% of what their validation code does.**
Everything else is domain validation — that a country code is in their own
`countries.csv`, that a URL has an `http` scheme, that a level of assessment is
below 0.38 — which rowspec deliberately cannot express and should not try to.

Three results carry the pass:

1. **One live defect found, with full provenance, in `ccao-data`** — a
   twelve-month-old ragged row in a dbt seed, introduced by a bulk
   column-removal edit that was correct for 118 rows and wrong for the one row
   whose last field was empty. Their entire validation stack runs *after* the
   file is loaded into Athena and therefore cannot see file shape at all. §4.1.
2. **Zero refusals on `iptv-org/database`'s real `data/`** — 11 files, 40,834
   channel rows — even with a sidecar declaring eight keys and a date order.
   That is the tool's floor, reported flatly. §4.2.
3. **One premise of W2 is wrong and is corrected here.** W2 §5 says "four
   public reference-data registries had each independently written a CI check."
   `toolleeo/awesome-cli-apps-in-a-csv` has **no CI, no validator, and no
   `.github/` directory at all** — its `Makefile` only regenerates the README.
   The behavioural-demand claim rests on three registries, not four. §2.3.

---

## 1. What each one actually checks

### 1.1 `iptv-org/database` — the largest hand-rolled validator found

Three separate layers, in three files.

**Layer 1 — the file-shape gate, `scripts/core/db.ts` `loadData()`.** This is
the entire structural check in the project, 26 lines, and it runs before any
model is constructed:

```ts
const rows = csv.split(/\r\n/)
const headers = rows[0].split(',')
for (const [i, line] of rows.entries()) {
  if (!line.trim()) continue
  if (line.indexOf('\n') > -1) {
    errors.add({ line: i + 1, message: 'row has the wrong line ending character, should be CRLF' })
  }
  if (line.split(/,(?=(?:(?:[^"]*"){2})*[^"]*$)/).length !== headers.length) {
    errors.add({ line: i + 1, message: 'row has the wrong number of columns' })
  }
}
```

Two checks: **line ending must be CRLF**, and **field count must equal the
header's**. Note the field split is a hand-rolled lookahead regex, not a CSV
parser.

**Layer 2 — uniqueness, `scripts/commands/db/validate.ts`.** Eleven
`findDuplicatesBy` calls, one per file. Eight are single-column
(`channel.id`, `category.id`, `country.code`, `language.code`, `region.code`,
`subdivision.code`, `city.code`, `timezone.id`); `cities.csv` gets a *second*
independent uniqueness check on `wikidata_id`; and three are **composite**:

```ts
findDuplicatesBy<Feed>(data.feeds, (feed: Feed) => `$${feed.channel}${feed.id}`.toLowerCase())
findDuplicatesBy<BlocklistRecord>(…, r => `${r.channel}${r.ref}`.toLowerCase())
findDuplicatesBy<Logo>(…, l => `${l.channel}${l.feed}${l.url}`.toLowerCase())
```

Every one is **case-folded** (`.toLowerCase()`).

**Layer 3 — domain validation, `scripts/models/*.ts`, 1,265 lines.** Eleven Joi
schemas covering **56 fields with 120 rule invocations**, plus **20
referential-integrity methods**. A sample from `channel.ts`:

```ts
id: Joi.string().regex(/^[A-Za-z0-9]+\.[a-z]{2}$/).required(),
country: Joi.string().regex(/^[A-Z]{2}$/).required(),
closed: Joi.date().format('YYYY-MM-DD').raw().allow(null).min(Joi.ref('launched')),
website: Joi.string().regex(/,/, { invert: true }).uri({ scheme: ['http', 'https'] }).allow(null)
```

plus checks that no format can express: `hasValidId()` asserts the id is
*derived* from the name and country (`createChannelId(name, country) === id`);
`hasMainFeed()` and `hasMoreThanOneMainFeed()` assert a cardinality constraint
across two files; `hasValidReplacedBy()` follows a `channel@feed` pointer into
`feeds.csv` and forbids self-reference.

A twelfth file, `scripts/core/validator.ts` (123 lines), holds 14 named rules
for the **issue-form bot** — `noSpacedHyphen`, `noDoubleSpace`, `validWikidataId`
(`/^Q\d+$/`), `validLocode` (a 400-character country-prefix regex) — so
contributors never open the CSV.

**Where it runs.** `.github/workflows/check.yml` on every PR touching `data/`,
plus `kforeverisback/check-crlf-extended@v2` with `continue-on-error: false`,
plus a `.husky/pre-commit` hook running `db:validate` locally.

### 1.2 `datasets/country-codes` — Frictionless, not hand-rolled

Their `Makefile` is two targets deep:

```make
test:
	frictionless validate datapackage.yml

diff:
	daff previous-country-codes.csv data/country-codes.csv > daffdiff.csv
	daff render daffdiff.csv > daffdiff.html
```

The validation is **entirely delegated to Frictionless Table Schema**, declared
in `datapackage.yml` (340 lines): **57 field type declarations** (54 `string`,
2 `integer`, 1 `git`), **4 `unique: true` constraints**
(`ISO3166-1-Alpha-3`, `ISO3166-1-Alpha-2`, `M49`, `Geoname ID` — four unique
columns in **one** file), and **8 `minLength`/`maxLength` constraints`**.

This is the one registry that did *not* hand-roll, and it is a correction worth
recording: a mature, maintained standard for exactly this job already exists and
this registry adopted it. Note also that `make diff` is a **real, live user of
daff** — one of the 115 `.gitattributes` daff references W2 counted, here used
manually rather than as a merge driver.

There is no CI running `make test`; `.github/workflows/actions.yml` runs
`make update` monthly under Selenium/Xvfb and commits the regenerated file.
`.gitattributes` is `* text=auto eol=lf`.

### 1.3 `toolleeo/awesome-cli-apps-in-a-csv` — nothing

No `.github/` directory. No CI. No validator. No schema. The `Makefile` is four
lines and only regenerates `README.md` from the CSVs via `cli2md.py`, which uses
`csv.DictReader` with no checking whatsoever. `CONTRIBUTING.md` asks for prose
discipline and nothing structural:

> "To suggest a new program, check the existence of the program in the list."
> "Please make changes **to the CSV file only**, **not to the README file**."

**This corrects W2 §5.** The "four registries each wrote a CI check" claim is
true of three at most, and one of those three (country-codes) adopted an
existing standard rather than writing anything.

### 1.4 `ccao-data/data-architecture` — dbt tests, all of them post-load

20 seed CSVs under `dbt/seeds/`, governed by five `schema.yml` files (403
lines). The declared tests, counted exactly:

| Test | Count | Notes |
|---|---|---|
| `unique_combination_of_columns` | **16** | 11 single-column, **5 composite** (arity 2 or 3) |
| `not_null` | 4 | |
| `accepted_values` | 3 | e.g. `triad_name` ∈ {City, North, South} |
| `relationships` | 3 | seed → downstream model foreign keys |
| `accepted_range` | 2 | `loa < .38`; `version >= 1` |
| `column_types` declarations | 31 | `string` / `double`, forced to defeat dbt type inference |

Composite examples that no single-column key can express:
`ccao_loa_unique_by_year_class_code` (`year`, `class_code`),
`model_final_model_unique_by_year_type_is_final` (`is_final`, `type`, `year`),
`pinval_model_run_unique_by_assessment_year_type_and_run_id` (arity 3).

**The critical architectural fact: none of these is a check on the file.** They
are dbt data tests, executed by `dbt build --resource-types model seed` against
**Athena**, in a workflow that requires AWS OIDC credentials
(`build_and_test_dbt.yaml`). Their `.pre-commit-config.yaml` has hooks for
sqlfluff, sqlfmt, ruff, lintr, yamllint and a YAML-sort script — and **no CSV
hook of any kind**. Nothing in the repository ever reads a seed file as a file.

That is exactly why §4.1 happened.

---

## 2. The delta, both directions

### 2.1 Direction that matters — what their checks do that rowspec cannot

| Registry | Their checks | rowspec-expressible | **Share** |
|---|---|---|---|
| `iptv-org/database` | 2 shape + 12 uniqueness + 120 Joi rules + 20 referential = **154** | 2 shape (1 with inverted polarity) + 8 of 12 uniqueness = **10** | **6.5%** |
| `ccao-data` | 16 unique + 4 not_null + 3 accepted_values + 3 relationships + 2 range + 31 types = **59** | 11 of 16 uniqueness = **11** | **19%** |
| `datasets/country-codes` | 57 types + 4 unique + 8 length = **69** (Frictionless) | 1 of 4 unique = **1** | **1.4%** |
| `toolleeo` | **0** | 0 | n/a |

By source lines the picture is starker still: iptv-org's structural gate is **26
lines of 1,674 lines** of validation code.

**Specific things their scripts check that rowspec has no way to express, and
should not acquire:**

- **Composite keys.** rowspec's sidecar `key` is a single string
  (`reference/rowspec/sidecar.py`: `FIELDS = ("key", "order", "order_type",
  "columns", "delimiter")`, `key` validated as `str`). Five of ccao's sixteen
  uniqueness tests and three of iptv-org's twelve are composite. Forcing a
  single column produces a torrent of **false refusals on a valid file** —
  demonstrated in §4.4.
- **Two independent uniqueness constraints on one file.** `cities.csv` is unique
  by `code` *and* by `wikidata_id`; `country-codes.csv` declares four unique
  columns. rowspec has one `key` per file.
- **Case-folded uniqueness.** Every iptv-org duplicate check is `.toLowerCase()`.
  rowspec compares after NFC, not case-folding.
- **Referential integrity across files.** 20 methods in iptv-org, 3
  `relationships` tests in ccao. rowspec's `lookup()` exists only in `.mdtbl`
  formulas, not in CSV mode, and it is an evaluator not a validator.
- **Derived-value constraints.** `hasValidId()` — the id must equal
  `slug(name) + '.' + country`. Nothing in rowspec can state that.
- **Cardinality across files.** "exactly one main feed per channel."
- **Domain membership and format.** ISO country code shape, Wikidata `Q\d+`,
  UN/LOCODE, `http(s)` URL scheme, `YYYY-MM-DD` with `closed >= launched`,
  `loa < .38`, enumerated `triad_name`.
- **Rich column types.** rowspec's `columns` map accepts only
  `number`/`date`/`text`; Frictionless declares 57 typed fields and ccao forces
  31 warehouse types.

M1 §1 already recorded the decision that produced this boundary — no
`required`/`unique`/`regex`, because "that is Frictionless Table Schema, it
exists, and competing with it loses." `datasets/country-codes` is that decision
being validated from the outside: they run Frictionless, and Frictionless is a
**strict superset** of rowspec's CSV-mode checks for their file, save one
(§2.2).

### 2.2 Direction rowspec wins — narrow, and empirically confirmed

I re-implemented iptv-org's `loadData()` gate exactly (their split regex
included) and ran it against constructed cases:

| Case | Their gate | rowspec |
|---|---|---|
| duplicate column name (`id,name,name`) | **PASSES** | refuses §9.2 |
| conflict marker, multi-column file | caught, as "wrong number of columns" | refuses §9.1, named |
| conflict marker, single-column file | **PASSES** | refuses §9.1 |
| ragged row | caught | refuses §9.6 |
| clean file | passes | passes |

The duplicate-column-name gap is real and its consequence is the one M1 already
found in `owid/covid-19-data`: with `id,name,name`, Python's `csv.DictReader`
returns `{'id': 'a', 'name': 'B'}` — **two keys for a three-column header, one
column silently gone**. A field-count check cannot see it, because the field
count is correct.

The owid case is the sharpest illustration available and is used here **only as
illustration**: `Doses_Administered` at columns 6 and 14 of a 14-column header
over a 6-field row, in 13 of 547 `cdc_data_*.csv` files. Those are archived
*inputs* — the malformation is plausibly faithful preservation of what CDC
published, not a defect the repository introduced. It is a poor bug report and a
perfect demonstration of the class: **a structural validator catches it and no
domain validator can, because the domain is fine.**

The single-column conflict-marker gap is theoretical for these four (none has a
one-column CSV) and is recorded for completeness.

**One polarity inversion, and it is not in rowspec's favour.** iptv-org
*requires* CRLF and fails CI on its absence. rowspec **warns** on CRLF. Adopting
rowspec in place of their gate would silently drop a check they consider
load-bearing enough to spend a third-party action on. `--strict` promotes the
warning but cannot invert it.

---

## 3. The floor: what the validator found, false positives first

### 3.1 False positives

**Zero on data as shipped.** Every refusal below is a genuine structural defect
or a deliberately broken fixture.

**One class of false positive is easy to manufacture and worth stating**,
because it is a property of the sidecar rather than of the corpus. Declaring a
`key` that is not one produces confident, wrong refusals on a perfectly valid
file. On `ccao.loa.csv` (unique by `year`+`class_code`, 5,150 valid rows):

```
key: "year"        →  duplicate key year='2000' — 206 rows share it   (× 24 more)
key: "class_code"  →  duplicate key class_code='0' — 24 rows share it (× many)
```

Same for `toolleeo`'s `apps.csv`: declaring `key: "name"` refuses 14 names, and
they are mostly **legitimate collisions between distinct projects** — two
unrelated tools both called `choose`, `mdt`, `o`, `gg`, at different URLs. That
table has no key column at all; the correct rowspec answer is to declare none.
(A handful — `qsv` at both `jqnatividad/qsv` and `dathere/qsv`, `Himalaya` at
`soywod` and `pimalaya`, `vtm` at `netxs-group` and `directvt` — look like the
same project duplicated after a repository transfer, but distinguishing those
from the genuine collisions is a domain judgement rowspec cannot make and I did
not resolve.)

M1 §5 recorded refusing to *infer* a key for exactly this reason. The corpus
confirms the refusal was right and adds the sharper point: the sidecar makes it
easy for a maintainer to assert a key that is not one, and rowspec will believe
them.

### 3.2 Findings on real data

| Registry | Files | Refused | Warnings |
|---|---|---|---|
| `iptv-org/database` — **`data/` only, with sidecar** | **11** | **0** | 11 CRLF |
| `iptv-org/database` — whole repo incl. test fixtures | 72 | 1 | 70 CRLF |
| `datasets/country-codes` | 7 | 0 | 1 BOM (`tmp/UNSD-en.csv`, a build artifact) |
| `toolleeo/awesome-cli-apps-in-a-csv` | 5 | 0 | 0 |
| `ccao-data/data-architecture` | 20 | **1** | 8 CRLF/BOM |

The single `iptv-org` refusal is their own deliberately broken fixture,
`tests/__data__/input/db/validate/wrong_num_cols/categories.csv` — the directory
is named after the check.

**One spec/implementation divergence noticed in passing, not acted on.** SPEC.md
§9 was extended by concurrent work during this pass and refusal 14 now reads "a
leading BOM, or bytes that are not well-formed UTF-8." CSV mode emits BOM and
CRLF as *warnings*, which is what the runs above report and what M1 §5 argued
for on the evidence that enforcing them would have rejected 98.6% of `iptv-org`.
This corpus agrees: 70 of 72 `iptv-org` files and 8 of 20 `ccao` files would
become refusals under a literal reading of §9.14/§9.15. The divergence is
recorded here because it is now visible in the normative list rather than only
in prose; M1 §5 already flagged that the spec should say CSV mode is not a
strict subset of §9.

---

## 4. The one live defect, and the one flat zero

### 4.1 `ccao-data/data-architecture` — a ragged row, twelve months old

```
dbt/seeds/pinval/pinval.vars_dict.csv: row code='char_air' has 2 field(s),
the header declares 3
```

Verified independently of rowspec, with Python's own `csv` module: the header is
`display_name,code,description`; 118 data rows have 3 fields; **line 28 has 2**.
`csv.DictReader` yields `description: None` for that one row where the other 118
yield a string (12 of them the empty string).

**Provenance, from their own history.** The seed was created 2025-08-14 (#873)
with a trailing empty fourth column — every line ended `,`. On 2025-08-20, #879
stripped it. The diff of that commit, in full:

```
-display_name,code,description,
-Year Built,char_yrblt,Year the home was constructed.,
-Central Air Conditioning,char_air,,
-Attic Finish,char_attic_fnsh,,
+display_name,code,description
+Year Built,char_yrblt,Year the home was constructed.
+Central Air Conditioning,char_air
+Attic Finish,char_attic_fnsh,
```

`Attic Finish` lost one comma and is correct. `Central Air Conditioning` lost
**two** and is not. Both rows had an empty description; the edit handled one
correctly and one not, in the same commit, in the same file. It has since
survived three further PRs (#901 2025-09-09, #926 2025-12-01) and every CI run
between 2025-08-20 and HEAD on 2026-08-28 — **twelve months and two weeks**.

Why their stack cannot see it: `pinval.vars_dict` carries exactly one declared
test, `unique_combination_of_columns` on `code`, and that test runs in Athena
after agate has already loaded the file. Their pre-commit config has no CSV
hook. **The defect is invisible to every check they own**, and would have been
refused by `rowspec check` on the commit that introduced it, with no sidecar and
no configuration — this is one of the four bare-CSV refusals.

*Not reproduced, stated as a limit:* what dbt/agate does with the short row —
pad with `None` or raise — was not tested, because agate 1.9.1 is pinned but not
installed here and the brief forbids installing. The behavioural evidence is
that CI has been green for twelve months, so it evidently pads.

### 4.2 `iptv-org/database` — zero, and the zero is not vacuous

11 files in `data/`, 40,834 channel rows, with a directory sidecar declaring
eight keys and `order: launched, order_type: date` (9,820 real date values):
**0 refused.** M1 reported the same and this pass reproduces it against a fresh
clone one day newer.

Positive control, to prove the sidecar was live rather than ignored: duplicating
one row of the 40,834-row `channels.csv` produced

```
channels.csv: duplicate key id='10.au' — 2 rows share it
```

**Report this flatly: on the best-maintained registry in the corpus, running the
tool over their production data finds nothing.** That is the floor. Their gate
plus their bot plus their 1,265 lines of models keep the file structurally clean,
and a structural validator has nothing to add to a file that is already
structurally clean.

---

## 5. Per-registry verdict

**`iptv-org/database` — keep the script. Net loss to replace.**
Their gate catches everything rowspec's bare-CSV mode catches except duplicate
column names, and rowspec covers 10 of their 154 checks. Replacing the gate
would drop a CRLF *requirement* they enforce deliberately, break three composite
and twelve case-folded uniqueness checks, and lose the error messages their
contributors are directed to by CONTRIBUTING. The only defensible addition is a
duplicate-column-name check, which is four lines of TypeScript in the file that
already splits the header. Nothing here justifies a dependency.

**`ccao-data/data-architecture` — the only genuine fit, and it is additive, not
a replacement.** They have no file-level check at all, which is why a ragged row
survived twelve months. Their 59 dbt tests keep their meaning correct and say
nothing about their bytes. A pre-commit hook or CI step reading the seed files
as files would have caught this, and rowspec is one candidate for that. It is
not the only one, and it is not obviously the best: `csvlint`, a six-line Python
loop, or `frictionless validate` would each catch this row, and the last would
also express their composite keys and their 31 column types. **The finding here
is the gap in their architecture, not the tool that fills it.**

**`datasets/country-codes` — keep Frictionless. Adopting rowspec is a strict
downgrade.** Frictionless already checks encoding, header/row field counts,
duplicate labels, 57 field types, 4 uniqueness constraints and 8 length
constraints. rowspec expresses one of the four unique columns and none of the
types. The only thing rowspec would add is naming a conflict marker as a
conflict marker rather than as a cell-count error, which is a message-quality
difference on a file that is bot-regenerated monthly and has never had one.

**`toolleeo/awesome-cli-apps-in-a-csv` — no verdict available, and that is the
result.** There is nothing to compare against and rowspec found nothing in their
data. A 2,207-row table with no key column, no CI and one maintainer at 74% of
commits is not evidence for a validator; it is evidence that the maintainer's
review is the validator. Recorded chiefly as the correction to W2 §5.

---

## 6. What this pass changes about the design record

1. **The addressable surface is 1.4%–19% of these registries' validation
   effort, and 0% where they run Frictionless.** The structural layer is the
   whole of rowspec's claim, and it is genuinely small next to domain
   validation. That is not a weakness of the tool; it is the boundary, measured.
2. **The most valuable structural check is the one nobody hand-writes.**
   Everyone writes a field-count check — iptv-org wrote it, CONTRIBUTING bolds
   it, their fixture directory is named after it. **Nobody writes a
   duplicate-column-name check**, and it is the one whose failure is invisible to
   a field-count check *and* to every domain validator, because a file with a
   duplicated column name has correct field counts and correct values.
3. **The failure mode is a bulk edit, not a merge.** The ccao defect was not a
   concurrent-write collision — it was one person running one find-and-replace
   across 119 rows, correct 118 times. W2 §6 ranks the observed costs of
   table-in-git and puts silent-wrong-merge fourth at "not observed once." This
   pass adds a fifth cost that *is* observed: **a bulk structural edit that is
   right for the common row shape and wrong for the rare one.** rowspec catches
   it for the same reason it catches the merge case, without needing the merge
   case to be real.
4. **The sidecar's single `key` is the sharpest expressiveness gap**, and it is
   the one that can manufacture false positives. Eight of twenty-eight real
   uniqueness constraints across two registries are composite. Composite keys
   would be the single highest-value sidecar addition; whether they are worth the
   spec surface is a separate decision this pass does not make.
5. **W2 §5 item 2 is corrected**: three registries, not four, and one of the
   three delegated to Frictionless rather than hand-rolling.

## 7. Method and limits

Read-only throughout. Four shallow clones into `/tmp/m3` (one deepened by 400
commits to date the ccao defect); nothing written into the repository except
this file; nothing installed; **no third party contacted, and no outreach draft
written or left in the tree.** Sidecars used for the experiments were written
into the `/tmp` clones and deleted afterwards.

Limits:

- **`dbt`/agate behaviour on the short row was not reproduced** (agate 1.9.1
  pinned, not installed, install forbidden). The twelve-month green-CI record is
  behavioural evidence that it pads rather than raises, not proof.
- **`frictionless validate` was not run** for the same reason. Its coverage is
  stated from `datapackage.yml` and the Frictionless error taxonomy, and the four
  uniqueness constraints it declares were verified independently with Python
  (all four hold: 249 rows, no blanks, no duplicates).
- **iptv-org's gate was re-implemented, not executed** — their npm dependencies
  were not installed. The re-implementation is a line-for-line transcription of
  the 26-line block quoted in §1.1 and its results are labelled as simulation.
- Whether `qsv`/`Himalaya`/`vtm` in `toolleeo` are genuine stale duplicates was
  **not resolved** — doing so would require network lookups against third-party
  repositories, which this pass avoided.
