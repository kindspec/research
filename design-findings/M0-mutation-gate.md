# M0 — Mutation gate: repair and hardening

Scope: `rowspec/conformance/mutants.py`. No conformance case was added or
modified; `reference/rowspec/table.py` was not touched.

## Final counts

Snapshot at the end of the session (`cd conformance && python3 mutants.py`):

    32 killed, 2 survived, 2 equivalent, 0 stale

Before: **10 killed, 23 stale** — and staleness had only just been promoted
from a `??` note to a hard failure. Every one of the 23 now applies again.

`python3 run_cases.py` → **0 failures**.

## What was wrong, and why it matters

The mutants were exact source-text patches. `ruff format` rewrote quotes,
rewrapped lines and renamed `l` to `line`, and 23 of 36 patterns silently
stopped matching. That is the failure this project exists to eliminate: a
verification tool that keeps exiting 0 after it has stopped verifying.

A second, subtler instance of the same failure was found and fixed during this
work. The gate counted a mutant as *killed* whenever the suite reported any
non-zero failure count. The fixture tree is written adversarially and runs
ahead of the implementation, so at times during this session the reference
itself failed 15–20 cases. Under the old rule **every mutant looked killed,
including ones that change nothing observable.** The gate now runs the suite
against the unmutated reference first and counts a kill only as a case that
fails *under the mutant and not without it* — a set difference, not a count.
The pre-existing baseline failures are printed by name so they cannot hide.

## How the patterns were made durable

`apply_mutant()` now matches a **normalised token stream** rather than source
bytes. Three properties, in priority order:

* **Precise.** A pattern must match *exactly one* token run. An ambiguous
  pattern raises rather than patching the first hit — a mutant that lands on
  the wrong line is worse than one that does not apply. (`ALL` is an explicit,
  per-mutant opt-in for patterns that must hit every occurrence, e.g.
  `no-nfc-normalisation`, which appears in both `parse` and `structure`.)
* **Durable.** Layout is erased before comparison: `NL`/`NEWLINE`/`INDENT`/
  `COMMENT` dropped; string tokens compared by *value*, so `'x'` == `"x"`;
  f-string delimiters canonicalised; magic trailing commas deleted
  (`f(a, b,)` == `f(a, b)`) except where they make a one-tuple; and
  parentheses that wrap a whole clause deleted (`if (\n a\n and b\n):` ==
  `if a and b:`), restricted to pairs that run to the end of the clause, where
  they are always redundant — so erasing them cannot make two semantically
  different constructs compare equal. `_ANY` / `_ANY2` in a pattern match any
  single identifier and are substituted back into the replacement, so a mutant
  anchored on a distinctive identifier survives the rename of an incidental
  one (`l` → `line` would no longer have staled anything).
* **Checked.** The mutated source must compile and must differ from the input.

Why this and not an AST transformation: the mutants are line-level defect
injections, and several must patch a *fragment* (`c.strip().strip(...)`) or a
run of statements. A token stream handles fragments natively, keeps exact
character offsets for splicing, and — crucially — is easy to audit. The AST
route would have needed its own subtree-matching language to express the same
patches, with more code to be wrong in.

Measured durability (all 36 patterns re-applied against reformatted sources):

| reformat                          | patterns applying |
|-----------------------------------|-------------------|
| as-is (repo setting, `-l 100`)    | 36/36 |
| `ruff format -l 79`               | 36/36 |
| `ruff format -l 120`              | 36/36 |
| `ruff format quote-style=single`  | 36/36 |
| `ruff format indent-style=tab`    | 36/36 |
| `ruff format skip-magic-comma`    | 36/36 |
| `ruff format -l 60`               | 34/36 |

The two `-l 60` failures (`delta-*`) are the one known gap: at a line length
short enough that ruff must parenthesise a conditional expression to wrap it,
the added parens fall outside the matched span. The compile check turns that
into a loud failure, never a silent wrong patch. `-l 60` is not a
configuration this repo uses (`pyproject.toml` pins 100).

The reference was rewritten twice by another agent *while this work was in
progress*. The gate caught both rewrites — 2 then 5 patterns went STALE with
a non-zero exit, and were repaired. That is the mechanism working in anger,
not in a drill.

## Genuine holes — work for the case author

Both are proven by running the mutant and the reference side by side, not by
argument. **Do not let me write these cases; the suite is not written by
whoever maintains the implementation.**

### 1. `strip-only-ascii-spaces`

Cell padding is trimmed with `" "` only — no tabs, no non-breaking spaces.
The suite has `eval/nbsp-refused`, but its NBSP is *inside* a value
(`1<NBSP>500`), which `.strip()` never touches. Nothing exercises padding.

Distinguishing input — a numeric cell padded with U+00A0 (a TAB behaves
identically):

    | id | qty | unit | total = qty * unit |
    | --- | --: | --: | --: |
    | r_0001 | <U+00A0>10<U+00A0> | 12.00 |  |

    key := id
    grand := sum(total)

* reference: `grand = 120.0`
* mutant:    `grand = "#REF!(qty)"`

An `eval` case asserting `grand == 120.0` kills it. Worth covering U+00A0,
U+202F, U+2007 and TAB, since the reference strips all four and each is a
separate way for a paste from a spreadsheet to arrive.

*Note on the mutant itself:* the pattern targets
`c.strip().strip("   ")`. Simply deleting the second `.strip()`
would be a **no-op** — bare `.strip()` already removes all three, because each
is `isspace()`. The mutant therefore replaces the whole expression with
`c.strip(" ")`, which is what the mutant's name actually claims.

### 2. `order-none-is-ignored`

`order = arg if fn == "by" else None` becomes `order = arg`. For
`order := none()` the declaration regex yields `arg == ""`, which is falsy, so
`evaluate` behaves identically — but `parse` tests `order is None`, and `""`
is not `None`. **No case in the tree uses `none()` at all**; the three
`*-no-order` cases omit the declaration entirely, which does not reach the
mutated line.

Two distinguishing inputs, the second at accept/refuse level:

**A.** `order := none()` together with a row-relative column:

    | id | amount | run = cumulative(amount) |
    | --- | --: | --: |
    | r_0001 | 100 |  |
    | r_0002 | 50 |  |

    key := id
    order := none()
    final := max(run)

* reference: refuses — `column 'run' uses row-relative cumulative() but the
  table declares no row order.`
* mutant: refuses — `order := by() but there is no column ''`

A `parse` case with `refusal_contains: "row order"` kills it.

**B.** `order := none()` followed by `order := by(date)`:

* reference: **accepts**, `grand = 150.0`, rows sorted by `date`
* mutant: refuses `line 8: duplicate order declaration`

B also exposes a **reference bug worth filing separately**: the duplicate-order
check is `if order is not None`, so `none()` followed by `by(date)` is silently
accepted and the second declaration wins. `parse()` sets a local
`order_declared = True` that is **never read** — ruff reports it as `F841` — so
the check that was meant to catch exactly this was written and then not wired
up. `key` has no such gap.

## Equivalent mutants

Equivalent mutants are **still applied and still run**. A stale "equivalent"
pattern is just as blind as any other, and an equivalence claim the suite
refutes is a hard failure (`FALSE EQUIVALENCE`, non-zero exit). That check
earned its keep immediately: it refuted **both** of the entries that were in
`EQUIVALENT` when I started.

### Refuted (removed from `EQUIVALENT`, now killed)

* **`unknown-aggregate-function-silently-becomes-sum`** — claimed unreachable
  behind the explicit unknown-function raise. It was not: the mutation belongs
  *on* that raise, not after it. Rewritten so the guard downgrades to
  `fn = "sum"` instead of raising. Killed by `parse/unknown-aggregate`.
* **`order-none-is-ignored`** — claimed equivalent because `arg == ""` is
  falsy. False: `parse` compares against `None`, not truthiness. It is a
  genuine hole (above).

### Confirmed equivalent

* **`float-accepts-thousands-separators`** — `return float(v)` becomes
  `return float(str(v).replace(",", ""))`. `ev()` reaches that line only for an
  `ast.Name`, and only after a guard that raises `KeyError` for any string
  matching `[,  ]|^\(|\)$`. So no string carrying a separator ever
  arrives. The only other reachable value is a `float` from an
  already-computed column, and `str(float)` never contains a comma. (`ev()` no
  longer has an `ast.Call` branch, so the `("CALL", ...)` tuple that used to
  reach here — and would have differed only in *which* uncaught non-`Malformed`
  exception escaped — no longer exists.) The replacement is a no-op on every
  reachable input.

* **`computed-columns-evaluated-in-reverse-header-order`** — iterating
  `pending` in reverse. The plain-formula loop is a bounded **fixpoint**: a
  formula whose dependency is still pending raises `KeyError`, is left in
  `pending` and retried next round; a formula whose dependency is absent
  resolves to `#REF!(name)` and leaves. Each round therefore resolves at least
  one column or breaks, so the bound `len(plain) + 1` suffices in either
  direction, and every column ends in the same state — resolved, `#REF!(name)`,
  or `#REF!(cycle)` — regardless of visit order. Order-dependence would require
  a formula whose *result* depends on when a sibling was visited, and the only
  cross-formula channel is `pending` membership, which the retry loop makes
  order-free. This mutant is a live assertion that the fixpoint keeps working:
  if someone replaces it with a single pass, the mutant stops being equivalent
  and the gate says `FALSE EQUIVALENCE` rather than going quiet.

## Evidence the gate can still fail

1. **A pattern that matches nothing** → `STALE`, exit 1.
   `{"NONSENSE-pattern": ("if quux_does_not_exist(zork):", "if False:")}`
   → `STALE NONSENSE-pattern  pattern no longer matches the source`,
   `0 killed, 0 survived, 0 equivalent, 1 stale`, **exit 1**.

2. **A pattern that matches more than one place** → refused, never applied
   to the first hit. `("float(v)", ...)` →
   `pattern is AMBIGUOUS: matches lines 144, 166, 205, 233, 257`,
   **exit 1**.

3. **A near-vacuous fixture tree.** The gate run against a copy of the repo
   whose `cases/` holds a single trivial parse case reports
   `0 killed, 34 survived, 2 equivalent, 0 stale` and **exit 1**, naming every
   mutant as a hole. A suite that measures nothing cannot make this gate green.

4. **Live.** Two independent rewrites of `reference/rowspec/table.py` by
   another agent mid-session were both caught as STALE with exit 1
   (`skip-alignment-check`, `is-align-matches-any-dashed-cell`; then the five
   patterns covering the aggregate block after it was refactored into `_agg`;
   then `drop-every-third-row` after the row loop grew a computed-cell check).
   Not one degraded quietly.

5. **The false-equivalence check fired for real**, refuting both pre-existing
   `EQUIVALENT` entries (above).

6. `mutants.py` itself was run through `ruff format` mid-session, and every
   mutant was re-verified afterwards — that being the exact bug under repair.

## Other observations (not acted on — outside this remit)

* `tests/test_conformance.py::test_mutation_gate_has_no_survivors` fails, and
  should, while the two holes above are open. It is failing for the right
  reason. Closing it is case-authorship work.
* `just check` is red repo-wide for pre-existing reasons: `reference/
  rowspec_alt/table.py` is unformatted and trips ~45 `UP031`, and
  `reference/rowspec/table.py` (`F841` on the dead `order_declared`, `B905`)
  and `run_cases.py` (`B023`, `E501`) also fail lint. `conformance/mutants.py`
  is format- and lint-clean.
* The fixture tree and the reference were both being edited by other agents
  throughout this session; the counts above are a snapshot, and the gate is
  the thing that will tell you when they move.
