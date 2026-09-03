# D0 — dogfooding rowspec as a newcomer

Sources read: `README.md`, `SPEC.md`, `AGENTS.md`, `CONTRIBUTING.md`, and tool
output only. `reference/`, `conformance/`, `docs/rationale.md`, `DESIGN.md`,
`PLAN.md`, `RESEARCH.md` and `design-findings/` were **not** read. Uncontaminated.

Artifact: `experiments/D0-ergonomics/parts.mdtbl`
— bench PSU parts inventory. 9 rows, 11 columns, 2 computed
(`line_total = qty * unit_cost`, `vendor_total = sum(line_total where vendor = @vendor)`),
4 aggregates, `key := id`, `order := by(ordered)`. 13 commits over 6 editing rounds,
two merges, two engineered conflicts.

## 1. Time to first valid table

~15 minutes. Under a minute of that was typing. The rest was hunting §4, §5, §6
and §7 for things the README example implies but does not state, and then
discovering that "0 refused" does not mean "the numbers are right".

## 2. The headline problem: the tool cannot show me a number

`rowspec check` has exactly one output axis: refused or not. `--help` lists
`--fmt`, `--strict`, `--format`. **There is no way to print `grand`.**

The format's entire premise is a computed column and an aggregate that stay
correct across merges. I built one, edited it six times, merged it twice — and
never once saw its value. I computed `grand = 1402.83` in Python to know what
the answer should be, and still cannot confirm the tool agrees.

Worse, three separate silent-wrong cases pass with `0 refused`:

| input | result |
| --- | --- |
| `line_total = qty * unitcost` (misspelled column) | `1 file(s) checked, 0 refused` |
| `1,299.00` pasted from a spreadsheet | `1 file(s) checked, 0 refused` |
| `1 189.00` with U+00A0 (the case §4 and §8 argue at length) | `1 file(s) checked, 0 refused` |

Per §8 all three become `#REF!` and poison `grand`. Per §9 none is a refusal —
that is consistent with the spec. But the shipped validator has no mode that
reports value errors, so the CI recipe in the README is green on a table whose
total is broken. The claim "never quietly wrong" is a property of the *format*
that the *tooling* does not surface. A newcomer will ship a `#REF!` table.

`--strict` is advertised as "treat warnings (CRLF, BOM) as refusals". On a
CRLF `.mdtbl` it printed `1 file(s) checked, 0 refused` and no warning at all.
From the outside the flag does nothing and says nothing.

## 3. Documentation gaps — questions I could not answer from README + SPEC

1. **The column-formula expression grammar does not exist.** §4.1's ABNF has no
   production for a header cell. §9.20 refuses "not a well-formed expression"
   without defining well-formed. §7 says "arithmetic over column names" and
   shows only `qty * unit`. Are literals allowed? Parentheses? Division?
   I probed empirically. Accepted: `+ - * / % ** ^`, `(qty + 1) * unit`, a bare
   `1.13`, `-qty`, `"text"`. That is Python's expression grammar, not a
   specified one, and two implementations will not agree on `^` or `%`.
2. **`x = qty * unit # note` is accepted.** §4.1.10 says `#` inside a table line
   is data, never an annotation, so the RHS is `qty * unit # note`, which is not
   a well-formed expression, so §9.20 should refuse it. It does not — the `#`
   is eaten as a Python comment. Spec/implementation divergence.
3. **Predicate literals are never specified.** `arg = ident [where predicate]`
   defers to §7, which shows `region = "EU"` in one example and
   `region = @region` in another. I wrote `vendor = aliex` and was refused. I
   only knew to quote because one example happened to.
4. **Row ids: who makes them?** §6 says "opaque, machine-generated". Nothing in
   the tool generates one. I hand-typed `r_0001`…`r_0102` and hand-picked
   `r_0101`/`r_0102` on two branches specifically to avoid colliding. The one
   thing the spec insists must not be human-authored is the one thing there is
   no command for.
5. **File shape rigidity.** §4 shows table / blank / declarations. Must
   declarations follow the table? Must there be exactly one blank line? Can a
   declaration precede the table? Unanswered; I copied the example.
6. **No date arithmetic.** I wanted `days_on_shelf`. §7's function list is
   `sum count min max avg` plus `cumulative prior delta`. Dates are a first-class
   type with a total order but nothing consumes them. Dropped the column.
7. **`python -m rowspec` with `--directory` silently changes cwd**, so a
   relative path yields a raw `FileNotFoundError` traceback, not an error
   message. First thing I hit.

## 4. Error messages, quoted, marked

### Actionable — names the entity, tells me what to change

- `duplicate column name 'qty'` — **actionable**.
- `computed column 'line_total' has a value '14.20' in a data row; computed cells must be empty` — **actionable**, best message in the set. Names the column, quotes the value, states the rule.
- `duplicate key id='r_0004'` — **actionable**.
- `line 18: duplicate aggregate name 'grand'` — **actionable**.
- `unknown aggregate function 'median' in 'median_cost'` — **actionable**.
- `line 16: malformed declaration: 'grand := sum(line_total'` — **actionable**.
- `line 15: order must be by(<column>); omit the line entirely for an unordered table` — **actionable**, tells me the fix including the do-nothing option.
- `` `order := by(line_total)` names a COMPUTED column; ordering must be derived from stored data `` — **actionable**.
- `column name 'unit cost' contains whitespace U+0020; two identifiers must not render identically` — **actionable**, and naming the codepoint is right.
- `row key id= 'r 0004' contains whitespace U+0020; …` — **actionable**, though `id= 'r 0004'` has a stray space that made me think the space was in the wrong place.
- `order column 'ordered' mixes types ['date', 'text']; an ordering column must have a single type` — **actionable**, but it does not say *which row* is the text one. In 9 rows I found it; in 900 I would grep.
- `column 'since_last' uses row-relative delta() but the table declares no row order. Add `order := by(<column>)`.` — **actionable**, model message: names the column, the operator, and the fix.
- `` `order := by(...)` requires a `key :=` declaration: without one, tied order values fall back to physical file position, which is a coordinate `` — **actionable**.
- `line 3: not a table line, an annotation, or a declaration: 'TODO: get the mouser invoice number'` — **actionable**.
- `line 8: unresolved conflict marker` — **actionable**.
- `the second table line is not a valid alignment row: '| —————— | --- | …'. Cells must be one of ---, :--, --:, :-:` — **actionable**; quoting the bad line plus the four legal spellings is exactly enough.
- `column 'x': cannot parse 'qty *': invalid syntax` — **actionable**, though "invalid syntax" is a leaked Python parser string.

### Not actionable

- **`line 10: not a table line, an annotation, or a declaration: '| r_0004 | Panel meter | aliex | … |'`** — I inserted `# waiting on backorder` between two data rows. The message blames the *next* line, and that line is plainly a well-formed table line. The real rule is §4.1.2 (a `#` ends the table's contiguous run), which the message never mentions. A newcomer stares at an obviously-fine row. This is an extremely plausible mistake — annotating a row is the first thing anyone tries — and it is the worst message in the tool. It should say: *annotations may not appear inside the table; line 9 ends the table's run*.
- **`unsupported expression: Call`** for `x = sum(qty)`. **Not actionable.** No column name, no line, and "Call" is a Python AST node type. Writing `sum()` in a column formula is a natural mistake because aggregates use `sum()`. Should be: *column 'x': aggregate functions are not allowed in a column formula; use a table-level declaration*.
- **`unsupported predicate 'vendor = aliex'`** — **not actionable**. Quotes the predicate but never says what is unsupported. The fix (quote the literal) is not discoverable from the text.
- **`row has 7 fields, header has 8: '| r_0002 | Heatsink 25mm | … |     3.10 |                    |'`** for a dropped closing `|` — **misleading**. The quoted row visibly ends with a pipe (it lost only its final, empty cell), so the message tells me to add a field when the fix is to add the terminator. §4.1.3 says this refusal exists precisely because field count cannot see the truncation; here field count *is* what fired, and it points at the wrong thing.
- **Silence** on `1,299.00`, `1 189.00` (NBSP), `qty * unitcost`, and CRLF-with-`--strict`. Silence is the least actionable message there is.

Inconsistency worth noting: some messages carry `line N`, others do not.
AGENTS.md says "Errors name entities, never offsets"; the tool does both,
unpredictably. I want the line number every time.

## 5. What was annoying

- **Typing row ids.** Nine hand-invented opaque identifiers. I had to remember
  the highest one, and on two branches I deliberately jumped to `r_0101`/`r_0102`
  to dodge a collision — reasoning about a namespace by hand, which is the exact
  work the format claims to take away.
- **Empty cells for every computed column.** Two computed columns means every
  row carries `|  |  |` of nothing. Adding a row means counting pipes.
- **Canonical form versus readability.** Padded is what I wanted to read; §10
  proves padded is what makes disjoint edits conflict. So I ran `--fmt` and lost
  the aligned table. There is no editor support to have both, and no
  `--fmt --check` mode that fails CI on non-canonical, so files drift back out
  of canonical on every hand edit and nothing tells you.
- **`--fmt` rewrites in place with no preview and no diff.** I only trusted it
  because I had it committed first.
- **Adding a column touches every line.** Eleven-column rows are long enough
  that a two-column header no longer fits in a terminal, and adding `location`
  meant editing 11 lines to add one field.
- **No aggregate output** — covered above, but it is also the thing that most
  made me want a CSV plus a three-line Python script, because that script at
  least prints the number.

## 6. Branch and merge

**Disjoint inserts (README's claim).** Two branches inserted rows at opposite
ends. `git merge` twice, no driver, no `.gitattributes`: clean, 9 rows, all
present, validator green. Works exactly as advertised. I cannot verify the
"and `grand` is correct" half of the claim, because nothing prints `grand`.

**Same-row conflict.** Both branches edited `r_0006` — one the price, one the
quantity. The conflict was three lines:

```
<<<<<<< HEAD
| r_0006 | Chassis 3U | mouser | 2026-07-21 | 1 | 1189.00 |  |  | floor |
=======
| r_0006 | Chassis 3U | mouser | 2026-07-21 | 2 | 1299.00 |  |  | floor |
>>>>>>> price-b
```

This was the best moment of the exercise. Both sides are complete, self-labelled
rows; I could see the whole disagreement without opening another file, and the
resolution (`2` and `1189.00`) was obvious. Committing the markers by mistake is
caught: `line 11: unresolved conflict marker`. That is a real improvement over
CSV, where Python's `csv` module happily parses the markers as rows.

**Two branches each add a column.** Brutal. A column addition rewrites every
line, so it collides with any concurrent edit: 25 of 35 lines conflicted — the
entire table twice — for two changes that touched *different columns and no
shared data*. `git rebase` conflicted identically. The only practical resolution
was to abort and re-apply the second change by hand on top of the first. This is
inherent to a line-per-row layout and CSV behaves the same way, so it is not a
regression — but the README's framing invites you to expect merges to be a
solved problem, and schema changes are emphatically not.

## 7. Would I use it over a plain CSV for this table?

**As it ships today, no.** For *this* table I would use a CSV and a short script.

What rowspec gives me over CSV that I actually felt: refusal of committed
conflict markers, refusal of duplicate column names and duplicate row ids, and
the formula living next to the data instead of in a separate script. Those are
real.

What it costs me: hand-authored row ids, mandatory empty computed cells, a
canonical form that fights readability, an undocumented expression grammar, and
— decisively — **no way to see the number the format exists to protect**. A CSV
plus twelve lines of Python prints `grand` and dies loudly on `1,299.00`.
rowspec prints `0 refused` and lets it through.

What would flip me to yes, in order:

1. **`rowspec eval FILE` that prints the computed columns and aggregates**, and
   a non-zero exit when any value is `#REF!`. This is the whole thing. Without
   it the safety argument is unverifiable by the person relying on it.
2. **`rowspec add-row FILE`** that mints the id and emits the right number of
   empty cells.
3. **Specify the column-formula expression grammar in §4.1**, and make
   `sum()`-in-a-column and unquoted predicate literals say what to do instead.
4. **Fix the annotation-inside-table message** to blame the annotation, not the
   innocent row after it.
5. `--fmt --check` for CI, so canonical form actually holds.

Give me (1) and (2) and I would move this table to `.mdtbl` tomorrow. The
format's reasoning is sound and the merge behaviour delivered what it promised.
The tooling around it currently withholds the evidence.
