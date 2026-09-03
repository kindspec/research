# E2 — ergonomics, round 2

Newcomer trial. Sources allowed: `README.md`, `SPEC.md`, `AGENTS.md`,
`CONTRIBUTING.md`, and whatever the tool printed. Nothing under `reference/`,
`conformance/`, `docs/`, or `design-findings/` was opened. (One accidental
exposure: two uncaught tracebacks printed `reference/rowspec/cli.py` and
`table.py` source lines at me. I did not open the files.)

Work lives in `experiments/E2-ergonomics/` — 17 commits, three merges.

## (a) What I built, and how long the first valid table took

A PCB bill of materials, `bom.mdtbl`. Final shape: 14 rows, 9 columns —
`id`, `part`, `vendor`, `qty`, `unit_cost`, computed `ext_cost = qty *
unit_cost`, computed `running = cumulative(ext_cost)`, plus `lead_days` and
`moq` added later. Declarations: `key := id`, `order := by(part)`,
`grand := sum(ext_cost)`, `lines := count(id)`, and three per-vendor
subtotals. Real prices for real parts; a wrong total here costs money.

**The first table was valid on the first `check`**, about five minutes after
opening the README — and four of those five were reading SPEC.md's 567 lines.
I guessed nothing. The README's 7-line example plus §5/§6/§7 was enough to
write a header formula, a key, and two aggregates correctly on the first
attempt. That is a genuinely good result and it should be said first.

## (b) Where the documentation failed me

1. **`add-row` is undocumented.** It exists in `--help`'s choice list and
   nowhere else — not the README, not the SPEC. It is the only answer to
   "where do opaque row ids come from", which the spec insists on
   (§6: "opaque, machine-generated") without saying how.
2. **There is no per-subcommand help.** `rowspec eval --help` and
   `rowspec add-row --help` both print `check`'s help verbatim, and the usage
   line always reads `usage: rowspec check` no matter what you invoked.
3. **The `where` predicate has no grammar.** The ABNF says
   `arg = ident [ 1*WSP "where" 1*WSP predicate ]` with `; predicate: §7`,
   and §7 shows examples but no production. Whether a literal is
   double-quoted, whether numbers may be literals, whether `and` chains
   arbitrarily — all inferred from two examples. My `"lcsc"` guess worked.
4. **The ABNF and the implementation disagree on a bare aggregate in a header
   cell.** `arg`'s `where` clause is optional, so `| t = sum(qty) |` is
   grammatical. The tool refuses it (see the message in (c)). I could not tell
   from the docs which is correct.
5. **Nothing says whether a computed column may be an aggregate's argument.**
   `cumulative(ext_cost)` works. `sum(ext_cost where ...)` in a header cell
   silently returns 0. This is (d).
6. **The CSV sidecar schema is in neither README nor SPEC.** §13 says refusal
   5 "requires a sidecar declaring which column is the key"; README says it is
   "five lines" and links `docs/csv.md`, which was out of bounds. I guessed
   `{"key":"sku"}` and it worked — but that was luck.
7. **`#REF!(ext empty)` is an undocumented diagnostic form.** §8 documents
   `#REF!(name)` only.
8. **`--strict` is a no-op for `.mdtbl`.** Help says "treat warnings (CRLF,
   BOM) as refusals". In `.mdtbl`, CRLF is spec-accepted (§3) and BOM is
   already a hard refusal (§9.14), so the flag only does anything in CSV mode
   and the help never says so.
9. **No `--version`.** `rowspec --version` prints usage and an argparse error.

## (c) Error messages, each marked

### ACTIONABLE — fixed without reopening the spec

> `bom.mdtbl: expected 4 value(s) for part, vendor, qty, unit_cost; got 0`

Names the columns it wants, in order, and correctly omits the key and the
computed column. I supplied the right arity immediately.

> `bom.mdtbl: alignment row has 6 fields, header has 7`
> `bom.mdtbl: row has 6 fields, header has 7: '| r_0001 | ATmega328P-AU | digikey | 5 | 2.31 |  |'`

Both name the two counts and the second quotes the offending line.

> `bom.mdtbl: the second table line is not a valid alignment row: '| --- | --- | --- | --: | --: | --:  --: |'. Cells must be one of ---, :--, --:, :-:`

Quotes the line and enumerates every legal spelling. Model message.

> `probe/b.mdtbl: duplicate column name 'qty'`
> `probe/b.mdtbl: duplicate key id='r_0009'`
> `probe/b.mdtbl: line 21: duplicate aggregate name 'grand'`

Name the entity. Nothing more is needed.

> `probe/b.mdtbl: computed column 'ext_cost' has a value '1.10' in a data row; computed cells must be empty`

Says what is wrong and what the rule is. Does **not** name the row — with ten
rows I grepped for `1.10`. Half a mark off.

> `probe/b.mdtbl: line 15: order must be by(<column>); omit the line entirely for an unordered table`

**Best message in the tool.** Names the rule *and both* valid states.

> `probe/b.mdtbl: line 8: this is a valid table line, but the table already ended above it. A table is a CONTIGUOUS run of lines beginning with '|' (§4.1.2), and an annotation or blank line between two rows ends it. Move the annotation above the table or below the declarations.`

Equal first. Explains the rule inline *and* tells me the two places to move
the note. The §4.1.2 citation is a bonus, not a substitute — which is the
right way round.

> `probe/b.mdtbl: table line lacks its closing pipe: '| r_0006 | ... | 0.003 |  | 0.3'. §4.1.3 requires both, because only the closing pipe reveals a row truncated inside its final cell`

Names the defect, quotes the line, gives the reason.

> `probe/b.mdtbl: column name 'unit cost' contains whitespace U+0020; two identifiers must not render identically`

Names the character by codepoint. The trailing clause is rationale that does
not help, but the first half is sufficient.

> `probe/b.mdtbl: unknown aggregate function 'total' in 'grand'`

Actionable, but note the contrast with the `order` message above: it does not
list the five legal functions. One more clause and I would not have needed
§7.

> `row r_0004, ext_cost = #REF!(unitcost)` … `grand = #REF!(unitcost)  <-- ERROR`

For a misspelled column in a formula this is exactly right: it names the
identifier that does not exist, I see `unitcost` vs `unit_cost` instantly, and
the poison propagates to every aggregate with an `<-- ERROR` marker. This is
the headline feature working.

> `parts.csv: duplicate key sku='S1' — 2 rows share it`
> `    A key must name exactly one row. When two rows share one, a merge can apply an edit to the wrong one and never report a conflict.`

Best-in-class: entity, count, and the consequence. The CSV BOM and CRLF
warnings have the same two-line shape and are equally good.

> `probe/pad.mdtbl: not in canonical form (run --fmt)`

Tells me the exact command.

### PARTIALLY ACTIONABLE

> `probe/b.mdtbl: line 16: not a table line, an annotation, or a declaration: 'grand = sum(ext_cost)'`

I typed `=` where `:=` belongs. The message quotes the line and lists the
categories, so I got there — but it never says "did you mean `:=`". The
one-token fix is not named. (Also: this gives a line number, which AGENTS.md
forbids — "Errors name entities, never offsets." For a declaration line that
may be unavoidable, but the rule is stated absolutely.)

### NOT ACTIONABLE

> `probe/p2.mdtbl: unsupported expression: Call`

**The worst message in the tool.** `Call` is a Python AST node class name. It
names no file position, no column, no header cell, no rule, and no fix. My
table had four new header formulas; I had to bisect them one at a time to find
that a header-cell aggregate with no `where` clause is refused — a form the
published ABNF says is legal.

> `row r_0008, ext_cost = #REF!(unit_cost)`  (cell contained a pasted `1,299.00`)
> `row r_0004, ext_cost = #REF!(qty)`        (cell contained `1<U+00A0>000`)

These name the row and the column and **not the reason**. As a person who has
just pasted from a spreadsheet, "unit_cost is #REF!" sends me to look at the
formula, which is fine. Nothing points at the comma. To fix it I had to go
read §4.1.6 and learn that digit grouping is refused — the definition of an
error that names a rule you have not read.

The U+00A0 case is worse, because **the offending character is invisible**. I
look at `| 1 000 |`, see a plausible number, and the tool has told me only
that the column is broken. `#REF!(qty: '1 000' is not a number — digit
grouping is not accepted)` would have cost one line and saved the trip. This
is the exact failure README advertises as a selling point ("a non-breaking
space in a number"), and the diagnostic does not mention the space.

> `/tmp/crlf.mdtbl: line 1: not a table line, an annotation, or a declaration: '﻿| id | qty |'`

A leading BOM. §9.14 is a dedicated refusal for precisely this and it is not
the one reported; instead I get the downstream consequence. The `﻿` in
the echoed string is the only clue and it is easy to miss. Say "the file
begins with a UTF-8 byte-order mark" — the CSV path already does exactly that.

> `/tmp/cr2.mdtbl: lone CR: two rows would share one line`

The cause is named, which is good, but there is no location — in a 2,000-row
file this is a grep. And see the conformance bug in (d): only `eval` emits
this. `check` passes the file.

> `FileNotFoundError: [Errno 2] No such file or directory: 'nope.mdtbl'`
> (full Python traceback, exit 1)

A mistyped path produces a stack trace. In CI this reads as a crash, not as
operator error.

> `rowspec.table.Malformed: row has 10 fields, header has 9: ...`
> (full Python traceback, from `add-row` on a malformed table)

Second uncaught traceback. `check` handles this same condition cleanly;
`add-row` does not.

> `  24 unresolved reference(s):` followed by six entries, no ellipsis

The count and the list disagree and nothing says the list was truncated. Seen
consistently (also "9 unresolved reference(s)" showing three). Minor, but it
made me briefly doubt the count.

## (d) Wrong numbers, and verification

### I could verify every total I asked for — except one, which was silently wrong.

I hand-checked the arithmetic at every commit. `grand`, the three per-vendor
subtotals, `cumulative`, and `count` all agreed with me, including across all
three merges. Two independent cross-checks were available and both held: the
per-vendor subtotals summed to `grand` (26.95 + 6.07 + 7.00 = 40.02), and the
final `cumulative` value equalled `grand`. That is a real, usable verification
loop and I want to be clear that it worked.

### The silent wrong number

The first column I tried to add three rounds in was the ordinary BOM
subtotal-by-vendor:

```
| vendor_total = sum(ext_cost where vendor = @vendor) |
```

Every row evaluated to **0**. `rowspec check` said `0 refused`, exit 0.
`rowspec eval` printed `vendor_total=0` for all ten rows, exit 0. No `#REF!`,
no warning, no marker. The truth was 17.75 / 4.87 / 7.00.

I committed that state before I noticed.

Isolated (`probe/p1`–`p4`), the rule is exact:

| expression | position | result | truth |
|---|---|---|---|
| `sum(qty where vendor = @vendor)` | header cell | correct | correct |
| `sum(qty where vendor = "lcsc")` | header cell | correct | correct |
| **`sum(ext where vendor = @vendor)`** | **header cell** | **0** | **20** |
| **`sum(ext where vendor = "lcsc")`** | **header cell** | **0** | **20** |
| `min/max/avg(ext where ...)` | header cell | `#REF!(ext empty)` | 10 |
| `count(ext where ...)` | header cell | correct | correct |
| `sum(ext where vendor = "lcsc")` | **declaration** | **20, correct** | 20 |
| `cumulative(ext)` | header cell | correct | correct |

`ext` is a computed column. The root cause is visible in the `min` message:
per-row group aggregates read the referenced column's **stored cell text**, and
a computed column's stored cells are empty by construction (§5). `min`/`max`/
`avg` then say `#REF!(ext empty)` — loud, correct behaviour. `sum` over an
empty set returns 0.

Three things make this the worst possible shape:

- **`sum` is the one everybody uses for money.** Of the five functions, the
  four that fail loudly are the four nobody reaches for first.
- **The same expression gives two different answers depending on where you
  write it.** As a declaration it is right; in a header cell it is 0. Nothing
  says a header cell and a declaration differ.
- **There is no workaround inside the format.** `arg = ident` — the aggregate
  argument must be a bare column name, so `sum(qty * unit_cost where ...)` is
  ungrammatical. A per-row subtotal of a computed money column is
  unobtainable. I fell back to one hand-maintained declaration per vendor,
  which does not scale and must be edited whenever a vendor is added.

§8 is unambiguous: "A broken reference never evaluates to zero, empty, or a
stale value." This is a broken reference evaluating to zero. If the intent is
that computed columns may not be group-aggregated, that is a §9 refusal and it
should fire. It currently does not, and the failure it produces is a plausible
number with no marker — the exact thing the project exists to prevent.

### Second conformance bug: `check` misses §9.15

A `.mdtbl` containing a lone `CR` between two data rows:

```
$ rowspec check /tmp/cr2.mdtbl
1 file(s) checked, 0 refused          exit 0
$ rowspec eval /tmp/cr2.mdtbl
/tmp/cr2.mdtbl: lone CR: two rows would share one line     exit 1
```

§9.15 lists a lone CR as a refusal and README says "`check` applies the
refusals in §9 — the structural ones". This is as structural as it gets: the
spec's own justification is that it "makes two rows share one git line". The
shipped CI recipe is built on `check`, so it passes a file that MUST be
refused.

### Third: `add-row` does not escape pipes

```
$ rowspec add-row bom.mdtbl 'KS TV | Action module' lcsc 2 3.50 14 1
bom.mdtbl: added id=r_d5fa38          exit 0
$ grep 'KS TV' bom.mdtbl
| r_d5fa38 | KS TV | Action module | lcsc | 2 | 3.50 |  |  | 14 | 1 |
$ rowspec check bom.mdtbl
bom.mdtbl: row has 10 fields, header has 9    exit 1
```

§4.1.3: "a writer escapes every literal `|` it emits **into a table line**."
`add-row` is the only writer that ships and it does not. It reported success
and corrupted the file. Writing `\|` by hand works perfectly — the format is
fine, the writer is not. This is pointed, because §4.1.3's [CHOICE] paragraph
justifies the escape's existence with the 26.95%-of-real-commits replay and
the ninety-three TV channels with pipes in their names.

### Fourth: `eval` fails on a valid CSV

README's recommended workflow, verbatim:

```
rowspec check .    # will this table survive being edited by several people?
rowspec eval  .    # does it currently say anything false?
```

Run on a directory containing a CSV that `check` passes:

```
$ rowspec eval parts.csv
parts.csv: no table found             exit 1
```

`no table found` is §9.13, a refusal, raised against a file that is valid. The
README's CSV pitch and the README's two-command workflow contradict each
other: adopt both and CI fails on every CSV in the tree.

## (e) What was annoying

**Float noise, everywhere, in a money table.** `grand =
21.450000000000003`. `ext_cost=3.4000000000000004` for 5 × 0.68.
`running=37.21999999999999`. `ext_cost=7` for 5 × 1.40 — a currency column
that drops its cents. §2 leaves formatting open, so this is spec-legal, but
for a tool whose entire proposition is *trust this number* it is corrosive.
It also breaks eval's own column alignment, so the output is ragged. Round to
the input's decimal places, or use `Decimal`.

**Adding a column is miserable and there is no `add-col`.** Every one of the
14 row lines has to be widened by hand. `check` reports **one** offending row
per run, so a naive fix loop is one round-trip per row. And because a column
add touches every line, two branches adding different columns produce **one
conflict hunk spanning the entire table** — 28 lines of markers for two
changes that are semantically orthogonal. Git refusing is correct and much
better than silence, but the format makes the most common schema change into
the most expensive merge. `add-row` exists; the harder operation has nothing.

**Two people appending a row always conflicts.** The single commonest
concurrent edit to a table — each person adds a row — conflicted every time,
because rows land adjacent at the end of a contiguous block. The README's
demo is careful to say the branches insert "far apart", and that qualifier is
carrying more weight than it looks. Resolution was trivial (keep both lines),
but "always conflicts" is not what a reader takes away from the README.

**`eval` is keyed on opaque ids only.** Output is `r_9f98a2 ext_cost=0.25`. The
whole argument for opaque ids (§6) is that humans never read them, and then
the only human-facing output addresses every row by one. I could not tell
which part a row was without cross-referencing the file. An `id` plus the
first text column would fix it.

**Two different id conventions in one file.** I wrote `r_0001`; `add-row`
generated `r_9f98a2`. Both legal, both now in my table, and the file looks
untidy. The tool should either match the existing convention or the docs
should tell me not to hand-write ids.

**No sort.** `--fmt` canonicalises bytes but does not reorder rows, so the
file stays in insertion order permanently while `eval` prints derived order.
Correct per §6, and still: the on-disk artifact and the reported artifact are
in different orders forever, and I have no command to reconcile them.

**Nothing cross-checks the subtotals against the grand total.** I did that
arithmetic by hand. A tool that owns the aggregates could have.

**`.rowspec` accepts anything.** I wrote `edition banana`; nothing complained.
§12 says a reader never consults it, so this is consistent — but a file with
zero validation is a file that will be wrong the day it matters.

## (f) Verdict against plain CSV

**For this BOM: yes, but narrowly, and I would not hand it to a colleague
today.**

What carried it, concretely. After resolving a 14-row whole-table conflict by
hand, one `rowspec eval` told me `lines = 14` and `grand = 40.02` —
unchanged — and I knew I had lost no row and corrupted no price. With a CSV I
would have had a diff and a hope. That single moment is the product. Behind
it: `#REF!` propagation turned a pasted `1,299.00` into a poisoned `grand`
with an `<-- ERROR` marker, where `pandas`, Excel and Python's `csv` all give
a number or a silent NaN; `check` refused a committed conflict marker, an
annotation between two rows, a duplicate key and a stray value in a computed
cell; and stock git genuinely did merge two divergent edits into an arithmetically
correct total, which I verified by hand. The format's central claim held every
time I tested it.

What stops me recommending it. The first column I reached for returned a
silent 0, and the tool told me `0 refused`, exit 0, twice. I committed the
wrong number. I only caught it because I was hand-checking totals — which is
the labour the tool is supposed to remove. A format sold on "never quietly
wrong" cannot be quietly wrong about `sum` of a computed column, because
`sum` of a computed column *is the table*. Plain CSV never promised me
anything, so I would have checked. rowspec promised, and was wrong, and my
guard was down.

To flip this to an unreserved yes:

1. **`sum(<computed> where ...)` must either work or refuse.** Not 0. If it is
   out of scope, make it §9.22 and fire it in `check`. This is the whole
   verdict.
2. **`check` must enforce §9.15.** A refusal that only `eval` catches is not a
   refusal, and the shipped CI recipe runs `check`.
3. **`#REF!` should name the value, not just the column.** `#REF!(unit_cost:
   '1,299.00' is not a number — digit grouping is not accepted)`. For the
   U+00A0 case this is the difference between a fix and a hunt.
4. **`add-row` must escape `|`.** It currently writes a file it will then
   refuse, and reports success.
5. **Replace `unsupported expression: Call`.** Name the header cell.
6. **Round the output**, or the numbers do not look trustworthy even when they
   are.
7. Then: `add-col`, per-subcommand `--help`, `add-row` in the README, no
   tracebacks, and report every bad row in one pass.

Items 1 and 2 are correctness. Items 3–5 are the difference between a tool a
newcomer can use and one they bounce off. Item 6 is cosmetic and it matters
more than it should.
