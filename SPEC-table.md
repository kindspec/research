# The tabular artifact format — normative specification (draft 0)

Status: draft. This document DEFINES the format. Where it and the conformance
suite disagree, **the suite wins** and this document is in error — that ordering
is deliberate, and is the lesson of CommonMark's founding grievance that early
implementers had to consult a buggy reference program because no spec existed.

Conformance is a claim about a **version of the suite**, not about this prose.
An implementation states: *conforms to table-format suite 0.x*.

---

## 1. Scope, and what is deliberately left open

This format stores tabular data with computed columns in a plain text file, such
that an unmodified `git` merges it correctly or fails loudly.

**Deliberately unspecified**, and an implementation may do as it likes:

- how values are RENDERED (alignment, number formatting, locale display)
- the function library beyond the small set in §7
- indexing, caching, and storage of derived values
- editor behaviour of every kind
- how a conflict is presented to a human

**Deliberately specified**, because two implementations that disagree here
produce silent corruption:

- the exact set of inputs that must be REFUSED (§8)
- row ordering semantics (§6)
- the canonical byte form (§9)
- reference resolution and error propagation (§7)

An undocumented degree of freedom becomes an interoperability bug the moment two
implementations meet in one repository. Where this document is silent by
intention, it says so.

---

## 2. Encoding

UTF-8. LF line endings. No BOM. Identifiers are compared after Unicode NFC
normalisation, and `Cf` format characters are rejected in identifiers.

These are enforced by the PARSER, not by `.gitattributes`, because a bare
repository never reads `.gitattributes` and a fresh clone never has local
config. Measured: NFD renormalisation turns a one-word edit into a four-line
diff and makes two edits to different rows conflict with both sides
pixel-identical.

## 3. File shape

    <table>
    <blank line>
    <declarations>

The table is a contiguous run of lines beginning with `|`. The first is the
HEADER, the second is the ALIGNMENT row, the remainder are DATA rows.

## 4. Columns

A header cell is either a NAME, or a name and a formula separated by `=`:

    | id | item | qty | unit | total = qty * unit |

- Column names are a namespace. Duplicates are refused (§8).
- The header is ONE LINE, which co-locates the namespace so that a collision is
  a line collision stock git can see. This is the only namespace in the format
  with that property; the rest rely on §8.
- A column with a formula is COMPUTED. Its data cells are empty. Writing a
  value into a computed cell is an error.

## 5. Rows and identity

Every table SHOULD declare a key:

    key := id

The key column holds an opaque, machine-generated row identifier. It is not an
address: **a human writes column names into formulas and never writes a row id
into anything.** Row ids exist so that a three-way merge can tell which row is
which.

Rationale, measured: across four identity functions and four concurrent-edit
scenarios, natural keys lose an edit on rename and overwrite a row on
duplication; content hashes split a row into two; only an opaque id survives all
four. Every failure was silent.

## 6. Row order — the only ordering semantics

    order := by(<column>)     ordering is derived from that column's values
    order := none             the table is a SET (default)

Under `order := none`, the row-relative operators of §7 are **refused**.

Under `order := by(c)`, the total order is `(value of c, key)`. The physical
position of a row in the file is NEVER an input to any computation.

This is the format's central rule and the reason a row-relative operator is safe
here where a "previous row" operator is not: *the previous row* means the row
with the next-lower key, not the line above. Measured: physically shuffling
every row leaves all computed values identical, and a backdated row appended
last correctly leads a running total.

## 7. Formulas

Arithmetic over column names, referring to the current row. Row-relative
operators, legal only under a declared order:

    cumulative(c)   running total in order
    prior(c)        that column's value in the preceding row
    delta(c)        c minus prior(c)

Aggregates are declared below the table, one per line:

    grand := sum(total)

**Error propagation is normative.** A reference to a name that does not exist
evaluates to `#REF!(name)`. An aggregate over any column containing a `#REF!`
is itself `#REF!` — it MUST NOT sum the values it can read. A broken reference
never evaluates to zero, empty, or a stale value.

The evaluator is total, terminating, deterministic and free of input/output.
There is no escape hatch and no flag that adds one. Constructs that would read
the clock, the network, or a path are not blocked — they are unparseable. This
is simultaneously a security property and a correctness property: a
content-addressed cache is silently wrong if a formula can read the clock.

## 8. Refusals — normative, and the heart of the format

Recognition is total: every byte sequence has exactly one defined outcome. A
parse error is REPORTED separately from being handled, so a validator and an
evaluator run the same algorithm and differ only in what they print.

An implementation MUST refuse:

    conflict markers anywhere in the file
    a duplicate column name
    a duplicate aggregate name
    a duplicate key or order declaration
    a duplicate row id, where a key is declared
    a data row whose field count differs from the header
    an alignment row whose field count differs from the header
    a row-relative operator with no declared order
    `order := by(c)` where c is not a column
    a malformed declaration
    a file containing no table

**Reject when degrading could yield a plausible VALUE; preserve and warn when
it could only lose DECORATION.** Exactly one ignorable channel exists, and it
carries an inertness promise: nothing in it may ever contribute to a computed
value. That promise is testable by stripping every annotation and asserting no
value changes.

## 9. Canonical form

    | id | item | qty | unit | total = qty * unit |
    | --- | --- | --: | --: | --: |
    | r_0001 | widget | 10 | 12.00 |  |

Single-space delimiters. **No alignment padding.**

Padded input is VALID and round-trips byte-exactly; it is simply not canonical.
Canonicalisation is a separate explicit operation, and `canon(canon(x)) ==
canon(x)`.

Rationale, measured on 2,000 rows, one cell changed from `9` to `1000`:

    padded      2002 added / 2002 removed lines, 238,370 bytes of diff
    canonical      1 added /    1 removed line,      413 bytes

and, decisively, two **genuinely disjoint** edits conflict when padded and merge
cleanly when canonical. A widening cell reflows every row, so alignment
manufactures conflicts between edits that never touched each other. Alignment is
a rendered view.

## 10. What an implementation must ship with

A conformance run against a **stock git binary**, reporting per case. Merge
cases assert on the EVALUATED VALUE of the merged artifact, not merely on git's
exit code, because a clean merge with a wrong number is the failure that
matters.

An implementation SHOULD also run the mutation gate: a suite that cannot fail a
deliberately broken implementation is measuring nothing. The reference suite
ships 17 mutants; all must be killed.

## 11. Versioning

One repository-level file, `.format`, containing `edition <year>`.

- A READER never consults it. Interpretation is a function of the artifact's
  bytes alone, so there is no "unknown version" case to mishandle.
- A WRITER emits only what the edition permits.
- Artifacts of different editions coexist in one repository with no ceremony.
- Migration rewrites to the INTERSECTION — valid under both editions — so it is
  incremental rather than atomic.
- Escape hatches are dated.

A per-file version field is rejected: it would touch every file on a bump, which
violates the locality invariant, and a version line at line 1 conflicts with any
concurrent edit to the header row.

## 12. Prior art

**org-mode `#+TBLFM:`** has done nominal column addressing in a plaintext table
for roughly twenty years, including a `!` row that names columns. It is the
closest ancestor and the most useful negative control: its `@row$col` absolute
references do not adapt to structural edits, its recalculation is manual so a
committed file can contradict its own formulas, and its formula namespace is
scattered.

**daff/Coopy** has shipped id-keyed three-way tabular merge wired into
`git merge` since 2013. It works — and it is delivered as a merge driver, which
this design demonstrates cannot travel. That is the whole thesis in one
sentence: the mechanism was never the missing piece; the representation was.

Also: **ClassSheets** (ASE 2005), **Object Spreadsheets** (Onward! 2016),
**Grist**'s column formulas, and **Excel Tables**' structured references.
