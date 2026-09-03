# M0 — lexical grammar (§4.1) and the completion of §9

Amends `rowspec/SPEC.md` only. New `### 4.1 Lexical grammar — normative` between
§4 and §5 (one ABNF-ish block plus twelve numbered rules), and a rewritten §9
list of 20 refusals with an explicit precedence statement.

## What the grammar now determines that the prose did not

An ABNF-ish block gives productions for `file`, `line`, `eol`, `blank`,
`conflict`, `annotation`, `table-line`, `cell`, `declaration`, `rhs`, `arg`,
`ident`, `align-cell`, `number`, `date`, and then twelve numbered rules that say
what each means and why the wrong alternative is wrong.

Newly determined:

- **Line classification is ordered, and the order is normative.**
  `conflict / annotation / table-line / blank / declaration`, first match wins.
  Two of those orderings carry the whole rule: `|||||||` is itself a well-formed
  seven-cell table line, and `# | r_9999 | ghost | 100 |` is a comment, not a
  row. A line matching nothing is refused, never skipped.
- **The table is the maximal contiguous run of table lines**; annotations and
  blanks may precede and follow it, never appear inside it; one table per file.
- **Both pipes required**, and **a cell can never contain `|` because no escape
  exists and none may be invented**, with the field-count consequence spelled
  out.
- **Trimming**: leading/trailing `WSP` = SP + HTAB only, cross-referenced to §8's
  thousands-separator argument, plus the second reason (`r_01` vs `\tr_01` must
  be one duplicate row id, not two rows that render identically).
- **Alignment row**: four spellings, hyphen run ≥ 1, `| - |` minimal; empty cell,
  `::`, `-- -`, en dash all refused. And the rule that decides §9.8: a data row is
  alignment-style **iff every** cell matches — one `---` beside real values is data.
- **Numbers**: `[-] 1*DIGIT [ "." 1*DIGIT ]`, `DIGIT` = U+0030–U+0039 only, with
  the `\d`/Arabic-Indic hazard named. Refused and therefore text: leading `+`,
  `1e3`, `.5`, `5.`, `1_000`, `1,000`, `(500)`, `0x10`, `inf`/`nan`/`infinity`.
- **Dates**: shape, one separator character per date, no calendar validation, and
  **`(y, m, d)` integer comparison, never string** — with the `2026-2-1`/`55.0`
  vs `5.0` overdraft example as the stated failure mode.
- **Text order**: Unicode code point over the NFC-normalised trimmed value, for
  a `text` order column and for the key tiebreak; locale collation refused
  because it makes interpretation a function of the reader's ICU version rather
  than of the bytes, contradicting §12.
- **Identifiers**: positive allowlist `L* / M* / N* / _ / - / .`, which excludes
  whitespace and `Cf` by construction and also `| = : # ( ) , " @`.
- **Annotations**: two forms only. Whole-line (first non-`WSP` char `#`, outside
  the table) is inert whatever it contains, so `# key := id` is a comment and not
  a malformed declaration; inline is `WSP "#"` to end of line **on a declaration
  line only**; `#` inside a table line is data.
- **Declarations**: `name := fn(arg)`, `key := col` the sole bare form, malformed
  = contains `:=` and does not match.
- **Conflict markers**: all four seven-character prefixes, `|||||||` included.

## Where I chose rather than described — every one tagged [CHOICE] in the spec

1. **A `#` line inside the table ends the table**, so the following table line is
   a table line after the table and the file is refused. Rejected: skip and
   continue (changes the row count silently), or start a second table.
2. **The closing `|` is required** (GFM makes it optional). Reason given: it is
   the only thing that catches a row truncated *inside* its final cell, which the
   field-count refusal cannot see.
3. **Exponents, leading `+`, and one-sided decimal points are refused**, not
   accepted. Reason: each is a second spelling of a value that already has one,
   and a second spelling compares equal as a number and unequal as text, which
   splits `where` predicates and key identity from arithmetic.
4. **A date's two separators must be the same character** (`2024-01/05` refused).
5. **No calendar validation** — `2024-13-45` is a date and orders as written,
   because a lexical layer that rejected it would need leap-year rules to be
   consistent.
6. **`ident` is an allowlist, not a denylist**, so an unforeseen character is
   refused rather than decided by an implementation's punctuation table.
7. **§9's numbering is NOT a precedence order**, stated explicitly with the
   reason: "exactly one defined outcome" means accept-with-values or refuse, the
   diagnostic identity is not part of the outcome, and pinning an order would
   outlaw a streaming reader that refuses at the first offending line. What is
   required instead is **determinism** — same bytes, same refusal every run — and
   the observation that a case asserting a message substring must be a case where
   exactly one refusal applies. The three `parse/two-refusals-*` fixtures are
   named as the ones that decline to pin it.

## Fixtures that contradicted a draft: none — and four that arrived to confirm it

No fixture contradicted the grammar. Four fixtures landed in the tree from
another agent *while I was drafting*, and each independently confirms a choice I
had already made from the reference's behaviour plus the prose:

- `parse/annotation-line-inside-the-table` (refuse) → choice 1.
- `parse/annotation-containing-a-declaration` and
  `eval/annotation-with-declaration-syntax-is-inert` (accept, inert) → the
  whole-line annotation rule, against the reference's then-behaviour of refusing
  `# g := sum(v)` at column 0.
- `parse/alignment-empty-cell-refused` (refuse) → the strict `align-cell` rule.

Also confirming, already in the tree: `parse/alignment-minimal-hyphen`,
`alignment-colon-only-refused`, `alignment-interior-space-refused`,
`alignment-long-runs`, `parse/dashed-value-is-data` vs `dashed-data-row`,
`rowrel/order-date-single-digit`, `order-date-mixed-separators`,
`eval/hash-in-a-cell-is-not-an-annotation`, `canon/idempotent-trailing-spaces`.

**Where the grammar now exceeds `reference/rowspec/table.py`**, on inputs no
fixture covers — each a latent divergence, reported not fixed (I own SPEC.md
only):

| Input | Reference | §4.1 |
|---|---|---|
| `\| r1 \| 1` (no closing pipe) | accepted | refused |
| `\|\| r1 \| 1 \|\|` | accepted, pipes stripped | refused |
| a table line after a blank line | absorbed into the table | refused |
| arbitrary prose before the table | silently ignored | refused |
| `٥` in a numeric cell | `5.0` (Python `float`) | text → `#REF!` |
| `1_000` | `1000.0` | text → `#REF!` |
| `1e3`, `+5`, `.5`, `5.` | coerced | text → `#REF!` |
| `inf` / `nan` in a non-order column | `inf` / `nan` | text → `#REF!` |
| `2024-01/05` | a date | text |
| a column name containing a space or `(` | accepted | refused |
| a blank key-column cell | accepted | refused (`ident` is `1*`) |

The `٥` and `1_000` rows are the two worth acting on: both are *silent plausible
values* produced by `float()`, and `1_000` is a thousands separator that coerces
— the exact case §8 says must be refused.

## What §9 gained

Seven entries and a precedence statement. Folded in: **14** BOM / not-well-formed
UTF-8, **15** lone `CR`, **16** identifiers (whitespace, `Cf`, or outside
`ident`) — all three previously argued in §3/§4 and absent from the list §2 calls
"the exact set"; **17** a value in a computed cell (§5 said "are empty", a
description, not a MUST); **18** a table line not matching `table-line`; **19** a
line that is none of the four constructs, including a table line after the table
ends; **20** a second table line that is not a valid alignment row, table shorter
than two lines included — §4 stated this refusal in prose and §9 never listed it,
which nobody had noticed. Entries 1, 8, 10 and 12 gained the definitions that
make them decidable (the marker set including `|||||||`; alignment-style = every
cell; non-finite spellings; malformed = contains `:=` and does not match). The
list is now prefixed "This list is complete", which §2 has been claiming.

## Left undetermined, deliberately

- **Expression grammar for §7 formulas.** `arg`/`predicate` are hooked into §4.1
  but the operator set, precedence, division-by-zero, and cycles stay §7/§8's
  problem. A lexical section that grew an expression grammar would be a rewrite
  of §7 under another name, and §7 has its own unresolved contradiction with §8
  over `@` coercion (M2 §1.1) that must be settled first.
- **`canon`'s exact output.** §4.1 states only the trailing-newline rule and that
  `canon` leaves annotations and declarations byte-verbatim. The alignment-cell
  mapping, the two-space blank cell, and an exact-output fixture kind are §10's
  work and `canon/removes-padding` is still a dead fixture in the runner.
- **`structure` / `render` / `set_cell` as a documented contract.** Still runner-only.
- **Whether NFC normalisation applies to cell values or only to identifier
  comparison.** §3 says identifiers; the reference normalises the whole document.
  §4.1 says text collation compares NFC-normalised values, which is true under
  either reading, and does not settle the byte-preservation question. It should be
  settled in §3, and it is a real round-trip hazard for an NFD file.

## Suite status

Spec-only edit; the runner cannot see it. Recorded for honesty: the tree was
**not** at 0 failures before or after, and it moved under me while I worked
(fixtures and the reference are being changed concurrently by other agents).
Before: 8 failures (`rowspec.table`) / 8 (`rowspec_alt.table`), including four
annotation and alignment cases. After: 5 / 11, all of them `lookup/*` or `crlf/*`
— the annotation and alignment failures were fixed in `reference/` during the
same window, in the direction §4.1 specifies. No lexical case fails.
