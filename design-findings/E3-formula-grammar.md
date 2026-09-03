# E3 — the formula language gets a grammar (SPEC.md §4.2)

**What was done.** A new normative section, `SPEC.md` §4.2 *Expression grammar*,
covering the language of every computed column and every table-level aggregate:
operator set, precedence and associativity, string literals, the `@` reference
and its binding rule, whitespace, division by zero, bare numeric tokens,
evaluation order, and cycles. Supporting amendments in §4.1 (one cross-ref), §5
(the header-cell split), §7 (a pointer), §8 (the complete set of `#REF!`
shapes) and §9.20 (what a malformed column formula now covers). `SPEC.md` is
the only file changed: +305 / −5 lines.

**Live-edit note.** `reference/rowspec/table.py` is being edited concurrently by
another author. It was at 0 failures when this work started and when the §4.2
text was finalised; a later in-flight change (explanatory `#REF!` text such as
`#REF!(qty='1e3' uses exponent notation…)`) has taken it to 7 failures. That is
not caused by this edit — `SPEC.md` is not read by any runner — but it is worth
recording that the 7 failing fixtures and the new §8 sentence agree with each
other and against the in-flight code: §8 now says there are **exactly three**
`#REF!` shapes and no fourth, and the fixtures pin `#REF!(qty)`. The diagnostic
belongs in a message channel, not inside the value.

**Conformance.** `run_cases.py` reported **0 failures** before this edit and
immediately after it, and
`run_cases.py rowspec_alt.table` reports **12** before and after. The 12 are
pre-existing and unrelated: `rowspec_alt` predates the `\|` escape amendment
(8 cases), `count`'s poisoning rule (2), the hyphen removal from `ident` (1),
and one predicate case. A prose edit cannot move either number; both were
measured before the first edit and again after the last.

---

## 1. The operator set

Binary `+ - * /`, unary `-`, parentheses. Nothing else. Precedence tightest
first: parentheses, unary `-`, then `* /`, then `+ -`; binaries left-associative
(`8 - 4 - 2` is `2`, `8 / 4 / 2` is `1`).

The deciding case is `^`. It is exponentiation in Excel, Sheets and Lotus, and
bitwise XOR in C, Python, Java and Go. Both are total functions over numbers,
neither raises, and `3 ^ 2` is `9` under one and `1` under the other — one file,
two totals, no diagnostic. `%` (modulo vs. percent-of) and `//` (floor division
vs. a line comment) fail the same test. `**` fails a weaker one: it has a single
agreed meaning and is simply capability the format does not have, so admitting
it is a proposal rather than a clarification.

The section states that the *rule* is "`expr` is what the ABNF generates", not
the list of banned operators — otherwise an implementation rejects the eight
named ones and accepts the ninth nobody wrote down.

`/` is real division (`7 / 2` is `3.5`). Integer division when both operands are
integral would make `qty / 2` depend on whether a cell is spelled `7` or `7.0`,
which §4.1.6 spent a paragraph making impossible.

## 2. The bare numeric token, in both positions

Resolved by **position**, where the position is fixed by the grammar and never
by the table:

- **Name positions** — the argument of a `rowrel-call`/`group-call`, §4.1's
  `arg`, either side of a predicate equality, the argument of `key`/`order` —
  admit `ident` and have no literal alternative. `sum(123)` is the column named
  `123`. So is `sum(1)`.
- **Operand position** (`primary`) tries `literal` first, so `| c = 123 * 2 |`
  is `246` and `| c = 123 |` is the number.

`literal` is deliberately **unsigned** (`1*DIGIT [ "." 1*DIGIT ]`) while §4.1.6's
`number` is signed: inside an expression a `-` is always an operator, so `a -1`
has one parse instead of two.

Stated cost: a column whose name matches `literal` is unreachable from
arithmetic. It stays reachable from every name position, which is where a
machine-generated numeric column name is used.

The alternative every implementer reaches for first — *a column if one exists,
else a literal* — is refused because it makes the grammar a function of the
table: adding a column named `2` silently changes `qty * 2` from doubling to a
reference, in a diff touching only the header.

**`sum(1)` is `#REF!(1)`.** Not a refusal, and the section says why it looks like
an oversight and is not: `sum(nope)` is `#REF!(nope)` by §8, pinned by
`eval/count-over-a-missing-column-is-ref` and `eval/missing-agg-col`, and `1` is
a name like any other. Refusing it would mean refusing an aggregate over any
absent column, and would make a formula's *acceptance* depend on the header
rather than on its own bytes. `parse/all-digit-column-name` independently
forecloses "refuse an all-digit name".

## 3. Every other [CHOICE]

| # | Choice | Why the alternative loses |
|---|---|---|
| 1 | operator set `+ - * /`, unary `-` | `^`/`%`/`//` have two silent readings |
| 2 | `/` is real division | integer division depends on `7` vs `7.0` |
| 2 | division by zero is `#REF!(/0)` | a refusal would make validity turn on a cell's value; `inf`/`nan` are spellings §4.1.6 and §9.10 refuse everywhere else, so `canon` could not round-trip its own output. `/` is outside `ident`, so `#REF!(/0)` can never read as a broken column reference |
| 3 | a call is the whole formula or nothing | measured: `\| x = cumulative(a) * 2 \|` under a declared order leaves every cell blank in the reference and reports `sum(x) = 0` |
| 4 | the eight function names are not reserved words; recognised only immediately before `(`, no space | reserving them refuses a table with a column called `count`; the no-space rule mirrors §4.1's `rhs = ident "("` |
| 5 | `@` only as the RHS of a predicate equality, header cells only | in a header formula a bare `ident` already means this row, so `@c` in arithmetic is a second spelling of `c`; a declaration has no current row |
| 5 | `@` binds to the **row being computed**, held fixed while the column is scanned | binding to the candidate row makes every predicate trivially true and turns every group aggregate into a grand total — a plausible number in every cell |
| 5 | both idents of an equality must name **stored** columns | a computed column has no cell text; the only reading compares rendered numbers, and §2 leaves formatting to the implementation, so two readers match different rows |
| 6 | `"` only; no escape inside; may not contain `"` | a second escape in a format with exactly one (§4.1.3); `'…'` is a second spelling |
| 6 | predicate equality compares **text**, never numbers | numeric comparison makes `3` and `3.0` match, splitting `where` from key identity — §4.1.6's own argument |
| 7 | bare numeric token: position decides (above) | context-sensitive resolution makes the grammar depend on the header |
| 8 | `WSP` optional everywhere except: required around `where` and `and`, forbidden between a function name and `(` | `sum(awhereb = "x")` lexes as one ident |
| 8 | `#` in a formula is not a comment; the cell is refused | an implementation borrowing a host parser reads `#note` as a comment and accepts — verified: the reference evaluates `\| x = a * 2 #c \|` to `12.0` |
| 9 | evaluation is by **dependency**; header order is not an input | left-to-right makes `\| gross = net * 1.2 \| net = qty * unit \|` a `#REF!` and the swapped order a number, making column order a coordinate |
| 9 | a cycle is `#REF!(cycle)` in every column on it and every column depending on one; the file is **accepted** | `parse/self-referential-column` and `parse/mutually-recursive-columns` require acceptance; and a cycle is a property of the whole header, so refusing lets one author's new column invalidate another author's line in a merge where both are individually fine |
| 9 | `#REF!(cycle)` collides with a broken ref to a column named `cycle`, and that is accepted | both are error values, both poison identically under §8, nothing branches on which; a non-`ident` spelling would change a conforming implementation's output for no gain in any number |

§8 now states there are **exactly three** `#REF!` shapes — `#REF!(name)`,
`#REF!(/0)`, `#REF!(cycle)` — and no fourth.

## 4. Fixtures that contradicted the draft — one, and it won

**`parse/all-digit-column-name`.** The first draft refused an all-digit token in
a name position, on the reasoning that `sum(1)` is a typo and a format should
not answer a typo with a silent broken reference. The fixture requires the file
**accepted** with `g := sum(123)` meaning the column `123`. The fixture wins;
the grammar was rewritten to the position rule in §2 above, and `sum(1)` is
`#REF!(1)`. `parse/all-digit-column-name/WHY.md` had already diagnosed this as a
spec gap rather than an implementation fault, and agrees with the resolution.

No other fixture contradicted the draft. Every header formula and declaration in
the tree was extracted and checked against the grammar: `b + a`, `a * 2`,
`net * 1.2`, `cumulative(amt)`, `prior(amt)`, `delta(amt)`,
`sum(amount where region = @region)`,
`sum(amount where region = @region and rep = @rep)`,
`sum(amt where region = "KS TV | Action")`, `x = y`, `y = x`, `b = b + a`, and
all 90-odd declarations. All are generated; the four `parse/formula-*` garbage
cases are not.

## 5. Where reference and spec have now drifted

Everything below is unfixtured. **The grammar now forbids what
`reference/rowspec/table.py` accepts**, in each case because the reference
exposes Python's grammar through `ast.parse` rather than a specified one:

1. `**`, `^`, `%`, `//`, `&`, `@` (as matmul) parse and evaluate to
   `` #REF!(<class 'ast.Pow'>) `` — a Python class name leaked into a value.
   Now §9.20 refusals.
2. `a * 2 #note` evaluates to `12.0`: Python reads `#note` as a comment. Now
   refused.
3. `'EU'`, `1e3`, `1_000`, `.5`, `1.`, `True`, `None` are accepted as literals in
   a header formula, all of them spellings §4.1.6 refuses as cell values. Now
   refused. Conversely `007` is *refused* by the reference (Python forbids a
   leading zero in an int literal) and is a valid `literal` under §4.2 — the one
   place the grammar is more permissive.
4. `g := sum(a where b = @c)` is accepted and evaluated as a per-row
   self-comparison. Now a malformed declaration.
5. `g := sum(a-b)` and `g := sum(a*2)` yield `#REF!(a-b)` / `#REF!(a*2)` rather
   than refusing. §4.1.11 already required a refusal here; §4.2 restates it.
   Pre-existing drift, not introduced by this edit.
6. `sum(a\twhere\tb = "x")` — tab-separated — is a malformed declaration in the
   reference, but §4.1 has always written `1*WSP`, which includes HTAB. Same
   formula in a *header* cell works, because that path uses `\s+`. Pre-existing.

**The reference is outright wrong, not merely narrower, in four places:**

7. **`a / 0` raises an uncaught `ZeroDivisionError`.** Neither accept nor
   refuse, so §9's "every byte sequence has exactly one defined outcome" does not
   hold today. §4.2 rule 2 makes it `#REF!(/0)`.
8. **A group aggregate over a computed column silently reported `0`** —
   *fixed mid-session by a concurrent edit to `reference/rowspec/table.py`,
   made by another author while this section was being written.* In
   `| total = qty * unit | rt = sum(total where region = @region) |` with two EU
   rows of 20 and 30, `rt` was `0` in both rows and `sum(rt)` was `0.0`, because
   the group phase ran before the arithmetic phase and aggregated a column with
   no values yet. It now returns `50.0` / `100.0`, which is what §4.2 rule 9
   independently requires. Recorded because it is the strongest evidence that
   the dependency rule is the right one: two authors reached it separately,
   from opposite ends, and the prose had never stated it.
9. **Arithmetic over a row-relative column is `#REF!`.** `| run = cumulative(a)
   | twice = run * 2 |` gives `twice = #REF!(run)`, because the arithmetic phase
   runs before the row-relative one. Under rule 9 it must be `run * 2`.
10. **A call composed into arithmetic is silently blank.** Item 3 in the table
    above; `sum(x)` over it is `0.0`. §4.2 rule 3 refuses the formula instead.

Items 7, 9 and 10 are the highest-value fixtures to add next: division by zero
(`a / 0` still raises), arithmetic over a row-relative column, and
`x = cumulative(a) * 2`. Each is a free variable today; two produce a plausible
wrong number and one produces a traceback. Item 8 should be fixtured too, now
that it is fixed, so it cannot regress — it had no fixture, which is why it went
wrong in the first place.

## 6. Judged out of scope

- **The numeric model.** Nothing in the format says whether arithmetic is binary
  float or decimal, so `0.1 + 0.2` may differ between implementations. Real, and
  not a grammar question; it belongs with §2's "number formatting" boundary,
  which currently leaves *display* open and says nothing about *arithmetic*.
  Flagged, not decided.
- **`prior`/`delta` on the first row.** Fixture-pinned to `""`, and §8's "a
  broken reference never evaluates to … empty" points the other way. A real
  spec/fixture contradiction, but it is semantics of a row-relative operator,
  not surface syntax, and it is not one of the eight ambiguities this pass owns.
- **Blanks under `sum`/`min`/`max`/`avg`, and `avg`'s denominator.** M2's
  largest untested hole across both passes. Not grammar.
- **The row sequence `evaluate` returns**, `structure`/`render`/`set_cell`,
  `canon` versus CRLF, and the `lookup` closure. All still open; none is the
  formula language.
- **New operators.** No exponent, no modulo, no comparison, no `if`, no string
  concatenation, no second escape. Every one of them was easier to add than to
  leave out, and the format's argument for refusing is stronger than its
  argument for any of them.
