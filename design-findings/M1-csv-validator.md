<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# M1 — the validator, on files people already have

Status: implemented. `reference/rowspec/csvmode.py`, `reference/rowspec/sidecar.py`,
`reference/rowspec/cli.py`, `tests/test_csv.py` (40 tests), `docs/csv.md`,
`docs/ci/rowspec-check.yml`. Standard library only. `.mdtbl` parsing untouched.

---

## 1. The sidecar

```jsonc
// data/channels.csv.rowspec.json
{
  "key":   "id",
  "order": "launched",
  "order_type": "date",
  "columns": { "width": "number" },
  "delimiter": ","
}
```

Five optional fields, and the file itself is optional. Two locations,
distinguished by **filename and never by content sniffing**:
`<file>.rowspec.json` for one file, and one `.rowspec.json` per directory
mapping globs to the same object.

**JSON, not TOML.** The argument is not ergonomics, it is the dependency
budget of the *second* implementation. JSON parses with nothing installed in
Go, JavaScript, Java, Ruby, Python and C#; TOML is stdlib only in Python 3.11+
and needs a crate/module everywhere else. `reference/` is stdlib-only precisely
so an independent implementation inherits no dependencies, and a sidecar the
reference can read but a Go implementation cannot would break that rule from
the outside. TOML's one real advantage is comments; the trade is comments
against a dependency in four languages.

**Appending the extension, not replacing it.** `data.csv.rowspec.json` sorts
adjacent to `data.csv`, cannot collide with the `data.json` that already exists
in most data repositories, and keeps a `.json` suffix so editors, forges and
JSON linters handle it with no configuration.

**Why a directory form exists at all.** `iptv-org/database` has 11 CSVs in one
directory and `owid/covid-19-data` has 1,485. Eleven sidecars is a reason not
to adopt; one file with `{"*.csv": {"key": "id"}}` is not.

**Fields I refused to add.** No aggregates (that is `.mdtbl`'s job and would
make the sidecar a second format). No `encoding` (UTF-8 or refuse). No
`skip_rows`/`comment` (a preamble means the file is not a table; saying so is
the useful answer). No `required`/`unique`/`regex` — that is Frictionless
Table Schema, it exists, and competing with it loses.

**Absent-sidecar behaviour** is the whole adoption story: six checks still run,
listed below.

**One design consequence worth recording.** JSON's rule for a repeated object
key is last-one-wins — precisely the silent overwrite §9.4 exists to forbid. So
the sidecar reader uses `object_pairs_hook` and refuses `{"key":"id","key":"name"}`.
Refusal 4 is not vacuous in CSV mode; the sidecar reintroduced the exact hazard
and had to re-close it.

## 2. The refusal split — the real number

| | bare CSV | needs sidecar | `.mdtbl` only |
| --- | --- | --- | --- |
| | 1 conflict markers | 4 dup `key`/`order` decl | 3 dup aggregate name |
| | 2 duplicate column name | 5 duplicate row id | 7 alignment row fields |
| | 6 field count ≠ header | 10 `order` col absent/mixed | 8 alignment-style data row |
| | 13 no table | 12 malformed declaration | 9 row-relative, no order |
| | | | 11 unknown aggregate fn |
| **4** | **4** | **5** |

**Four, four, five.** The prototype's "six of thirteen need no format change"
was counting §3's encoding rules alongside §9's numbered refusals: invalid
UTF-8, and a `Cf` format character inside a column name, are both checkable on
a bare CSV and both implemented. So *six checks* on a bare CSV, of which *four*
are numbered refusals. The estimate was right about the number and imprecise
about what was being counted.

The five `.mdtbl`-only refusals are not a gap. Three concern an alignment row
and formulas, which CSV does not have; two concern aggregate declarations,
which the sidecar deliberately does not grow. A CSV cannot violate them.

Refusal 12 is the one that changed shape: with no sidecar there are no
declarations, so it is vacuous; with one it covers malformed JSON, an unknown
field (with a `difflib` suggestion), a bad type name, and `order` without
`key`. Refusal 10's "is computed" clause is permanently vacuous in CSV.

Beyond the thirteen, the sidecar also buys **declared column types** — which is
the check the four hand-rolled registry validators were actually written to do.

## 3. Real public datasets — false positives first

1,564 CSVs across three repositories, 19 seconds, **16 refused (1.0%)**.

**False positives: zero.** Every refusal is a defect or a shape the format
genuinely cannot read. The two results that matter:

- **`iptv-org/database` — 72 files, 1 refused, and it is their own deliberately
  broken fixture**, `tests/__data__/input/db/validate/wrong_num_cols/categories.csv`.
  The validator independently found the case whose *directory is named after the
  check*, in the registry whose CONTRIBUTING file warns contributors in bold
  about column counts. Their real `data/` (11 files, 40,834 channel rows) is
  clean. With a directory sidecar declaring keys for 8 files and
  `order: launched, order_type: date` for `channels.csv` — 9,820 real date
  values — still zero refusals. Not a vacuous pass: injecting one duplicate id
  into a copy of the 41k-row file was caught by key, by name.
- **`owid/covid-19-data` — 1,485 files, 15 refused, 13 of them a real live
  defect.** `scripts/input/cdc/vaccinations/cdc_data_2020-12-20.csv` and twelve
  siblings each declare a 14-column header in which `Doses_Administered`
  appears **twice**, over a single data row carrying **6 fields**. `pandas`
  reads these without complaint: columns 7–14 become NaN and
  `df["Doses_Administered"]` is ambiguous. This is input data to a repository
  that fed global COVID dashboards, sitting there today. Two independent
  refusals (§9.2 and §9.6) both fire on it.
- `datasets/country-codes` — 7 files, 0 refused, 1 BOM warning.

**The one near-miss, and what it taught.** WHO's `cases.csv` and `deaths.csv`
are Excel exports with a *grouped two-row header*: row 1 repeats `Europe` 51
times across its span, row 2 holds the country names. Reporting that as seven
separate `duplicate column name` refusals is technically correct and useless.
That is the false-positive-shaped failure — not a wrong verdict, a wrong
*explanation*. It is now detected as one finding naming the shape:

```
who/cases.csv: the first row is not a row of column names: 'Africa' and 6 other
label(s) repeat across 161 columns, while the row below holds 161 distinct names
    This is a grouped or two-row header, the shape a spreadsheet produces from
    merged cells. There is no single row that names the columns, so no column can
    be referred to by name at all. Flatten it to one header row.
```

Twelve confusing lines became two actionable ones. I would not have found this
shape by reasoning about the spec.

**The measurement that changed a rule.** 71 of 72 `iptv-org` CSVs use CRLF, and
92 of 1,564 files across the corpus warn on CRLF or a BOM. Had SPEC.md §3's
"LF, no BOM" been enforced as a refusal in CSV mode, the validator would have
**rejected 98.6% of a well-maintained public registry on its first run**. Both
are warnings, promotable with `--strict`; §9's own test licenses this — neither
can change a value once the BOM is stripped.

Two false-positive sources found and closed before they fired:

- A lone `=======` line is only reported when a `<<<<<<<` opened the block.
  Git never emits one without the other; a CSV cell legitimately can.
  `.mdtbl` matches any line merely *starting* with a marker character, which is
  right for a format where a data line must start with `|`; CSV needed git's
  actual output format.
- A file with a conflict marker reports **only** that. The marker manufactures
  ragged rows and duplicate keys out of lines nobody wrote; the smoke test
  produced 9 findings for 1 cause before this, and 3 after.

## 4. Error-message design

Three rules, in order of how much they earned:

**Name the entity, never the offset.** A line number is wrong the moment
anyone else edits the file and a reviewer cannot act on it; a key can be
searched for. The row is named by its declared key, else by its first field,
else — only as a last resort — as `record 7`, labelled *record* rather than
*line* because a quoted field containing a newline makes those differ. A test
asserts no `line <digit>` ever reaches stderr.

**When two things render identically, print the codepoints.** This is the only
class of error where the message is not merely convenient but load-bearing —
the maintainer physically cannot see the difference otherwise.

```
data/people.csv: duplicate key id='café' — 2 rows share it
    These ids render identically but are different bytes: 'café' = U+0063 U+0061
    U+0066 U+00E9  vs  'café' = U+0063 U+0061 U+0066 U+0065 U+0301. Unicode
    normalisation makes them one id, so one of these rows will be lost.
```

**Say why once, not every time.** Each finding carries a headline and an
explanatory `detail`; the detail prints on the *first* occurrence of each rule
per run. Thirteen ragged rows give thirteen headlines and one explanation.
Occurrences are capped at three per rule per file plus `… and N more`.

```
data/channels.csv: row id='r_04' has 3 field(s), the header declares 4
    A row with the wrong number of fields silently shifts every value after the
    missing or extra comma into the wrong column. This is the check maintainers
    write by hand.
data/countries.csv: unresolved conflict marker '<<<<<<< HEAD'
    A merge was committed before it was finished. Every CSV reader in wide use,
    including Python's, parses these lines as ordinary data rows without
    complaining, so this file currently has rows nobody wrote.
```

`--format github` emits `::error file=<path>,title=rowspec::<message> — <detail>`,
folding the detail in because an annotation is one line and is the *only* thing
a reviewer sees. It carries no line number, deliberately.

Declaration errors suggest: `unknown declaration 'kye'; did you mean 'key'?`,
`declares order by 'joned' but the file has no such column; did you mean 'joined'?`

## 5. What made me doubt the zero-migration premise

**Two things, one serious.**

*Not serious:* CRLF and the BOM. §3's encoding rules are wrong for CSV and the
corpus says so at 98.6%. Demoting them to warnings costs nothing — neither can
change a value — but it means CSV mode is **not** a strict subset of the spec's
refusals, and the spec should say so rather than leaving an implementer to
discover it against a public registry.

*Serious:* **the two highest-value checks both need the sidecar.** Duplicate
row id (§9.5) is the refusal that motivates opaque keys, the whole identity
argument, and every silent-wrong merge in the design record — and a bare CSV
cannot run it, because nothing in the file says which column is the key. So the
adoption pitch splits: *zero* migration buys the conflict marker (real, and
genuinely invisible to every CSV reader) and the field count (real, and the one
maintainers hand-write); the check that the format exists for costs a
five-line file. That is still small, but "no migration at all" oversells it and
the pitch should say "five lines" honestly.

I looked hard for a way to infer the key — first column, a column named
`id`/`code`, a column that happens to be unique — and rejected all of them. A
heuristic key would produce exactly the false positive that makes a validator
worse than none: `iptv-org`'s `blocklist.csv` has `channel` first and it is
legitimately non-unique. Guessing here would have cried wolf on real data.

**One premise that held better than expected.** Every check is O(rows) with no
type inference beyond a regex, and 1,564 files including a 1.6 GB repository
took 19 seconds on one core, so the CI cost is not an adoption objection.

**Deliberate divergence from Python, recorded.** Numbers are matched by regex,
not `float()`: Python accepts `1_0`, `nan`, `inf` and surrounding whitespace as
floats, and an independent implementation should not have to reproduce those
quirks to agree with this one. §8 already refuses thousands separators; this is
the same principle applied to the host language.

## 6. State of the tree

`tests/test_csv.py` — 40 tests, all passing. Fixtures are byte literals, not
checked-in files: a CRLF, a BOM and an NFD identifier are exactly the three
things a git checkout, an editor and a whitespace hook each silently normalise,
so an on-disk fixture would stop testing what it claims to.

**Two pre-existing failures I did not cause and did not touch**, both from
other agents' concurrent work in this tree:

- `just check` fails `ruff format --check` on `conformance/mutants.py` (a
  two-line wrap) and `reference/rowspec_alt/table.py`, and `ruff check` reports
  ~50 findings in `rowspec_alt/` and 4 in `reference/rowspec/table.py`. Every
  file I added or edited is clean under both.
- `just conform` reported 0 failures at 16:24 and 15 at 17:10 — new cases
  (`parse/no-alignment-row` and others) landing ahead of the reference
  implementation, plus `rowspec_alt` under active edit. `table.py` is
  byte-identical to how I found it; my changes cannot affect `.mdtbl` parsing.

One trap for whoever fixes `reference/rowspec/table.py`'s lint: adding
`strict=True` to `dict(zip(cols, v))` on line 133 **breaks two mutants**
(`drop-every-third-row` and its control), because `mutants.py` anchors on that
exact token run. Fix the `F841` and leave the `zip` alone, or update the
pattern in the same change.
