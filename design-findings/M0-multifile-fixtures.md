# M0 — multi-artifact conformance fixtures

Making SPEC §7 `lookup()` and §8 `#REF!(file[key])` testable. Scope: extend
the fixture format, add the cross-artifact cases, verify both implementations.
`SPEC.md` was not touched.

---

## 1. The format extension

**One sentence: the case directory *is* a one-artifact git repository, and the
runner tells the implementation where it is.**

Concretely, two rules and zero new `expect.json` fields:

1. **The case directory is the referring artifact's directory.** `input.mdtbl`
   sits in it. A companion is an ordinary file beside it, addressed by the
   relative path §7 already defines. `lookup(customers.mdtbl, …)` finds
   `<case>/customers.mdtbl`; a lookup *inside* `<case>/sub/b.mdtbl` written
   `lookup(c.mdtbl, …)` finds `<case>/sub/c.mdtbl`, because §7 resolves
   relative to **b**, not to the case root.
2. **The case directory is also the repository root**, so §7's "confined to
   the repository" has an edge to test. `cases/_outside/` holds a real,
   readable artifact above every case root, so a non-enforcing implementation
   fails *with a value* rather than quietly with a missing file.

Runner change (`conformance/run_cases.py`): one helper, `ev_at(ref, text,
base)`, and every `ref.evaluate(...)` call now passes the case directory.
`reference/rowspec/table.py` already had `evaluate(text, base=".")`, so no new
entry point was invented. An implementation whose `evaluate` takes no base is
called without one — it then reports every lookup as unresolved and *fails*
the resolving cases, which is the signal wanted, not a crash.

**Why this shape.** The alternatives all put the repository in the metadata:
a `files: {...}` map inside `expect.json`, a `companions` list, a `primary`
field. Each makes an independent implementer parse a manifest describing a
filesystem, in order to reconstruct… a filesystem. A cross-artifact reference
is a path; the only faithful fixture for a path is a file at that path. The
directory already carried the second table (`run_cases.py` was reading every
`*.mdtbl` into `f` and then throwing all but `f["input"]` away) — the missing
piece was never storage, it was *telling the evaluator where it stood*. A
runner in another language needs exactly one extra line to consume this tree.

Documented in `conformance/cases/README.md` (new, CC0), which also writes down
the previously-undocumented `expect.json` kind/field table, and the convention
`refusal_contains: ""` — *refuse, for any stated reason* — used where the spec
mandates a refusal but names no message. Asserting invented wording would test
the reference implementation's phrasing rather than the format.

**A directory is a case iff it contains `expect.json`.** That was already true
and is what makes companion subdirectories and `_outside/` free.

## 2. Cases added (12) and how they land

Baseline at time of writing. `reference/rowspec/table.py` was being edited by
another agent *during* this work, so the reference column moved twice; the
`rowspec_alt` column did not.

| case | kind | ref | alt |
| --- | --- | --- | --- |
| `rowrel/lookup-resolves` | rowrel | pass | **FAIL** `#REF!(customers.mdtbl[c001])` |
| `rowrel/lookup-absent-row` | rowrel | pass | pass |
| `rowrel/lookup-target-without-key` | rowrel | **FAIL** `#REF!(customers.mdtbl#name)` | pass |
| `rowrel/lookup-column-absent-from-target` | rowrel | **FAIL** `#REF!(customers.mdtbl#nickname)` | **FAIL** `#REF!(customers.mdtbl[c001])` |
| `rowrel/lookup-target-file-missing` | rowrel | **FAIL** `#REF!(customers.mdtbl)` | pass |
| `parse/lookup-target-duplicate-keys` | parse | pass (refuses) | **FAIL** accepts |
| `rowrel/lookup-self` | rowrel | pass | **FAIL** |
| `rowrel/lookup-chain` (A → `sub/b` → `c`) | rowrel | **FAIL** `''` | **FAIL** `#REF!(sub/b.mdtbl[b1])` |
| `parse/lookup-cycle` (A ↔ B) | parse | pass | pass |
| `parse/lookup-path-escape` (`../../_outside/…`) | parse | pass *(now — see §3)* | **FAIL** accepts |
| `parse/lookup-computed-path` (`stem + ".mdtbl"`) | parse | pass (refuses) | **FAIL** accepts |
| `eval/lookup-ref-poisons-aggregate` | eval | pass | **FAIL** |

Reference: 4 failures. `rowspec_alt`: 8.

### The reference invents three error forms §8 does not define

§8 defines exactly two: `#REF!(name)` for an absent name, `#REF!(file[key])`
for an absent lookup row. The reference emits `#REF!(path)` for a missing
target file and `#REF!(path#col)` for a target with no `key` or without the
wanted column. Both are legible; neither is in the format. Two
implementations that pick different spellings produce different bytes for the
same table — §2's "undocumented degree of freedom [that] becomes an
interoperability bug". My cases assert the spec's forms, so they fail; the fix
is a spec amendment, not necessarily an implementation change.

### The one real bug: `rowrel/lookup-chain`

The reference `parse()`s the target but never `evaluate()`s it, so a lookup
that lands on a *computed* column of the target reads the empty stored cell
and returns `''`. §8: *"A broken reference never evaluates to zero, empty, or
a stale value."* A chained lookup silently yields blank — the exact
silently-wrong-value class this project exists to prevent, and it survives
into aggregates (a `sum` over such a column gets the blanks it can read).
`parse/lookup-cycle` shows why this is not simply "evaluate the target too":
that is the same edge a naive fix would hang on.

This case also carries the *relative-to-the-referring-artifact* assertion:
`b.mdtbl` lives in `sub/` and names its target as bare `c.mdtbl`. That
property is currently unobservable in the reference, because hop 2 is never
taken at all.

## 3. Is path confinement enforced? Now yes; when I wrote the case, no.

At the start of this session, `evaluate` did `full = os.path.join(base, path)`
with no check. `parse/lookup-path-escape` demonstrated a genuine read: the
reference resolved `../../_outside/secret.mdtbl`, two directories above the
artifact, and returned the real value `'Ada'` — not a `#REF!`, a value from
outside the repository. Mid-session another agent added a `realpath`-based
containment check plus an absolute-path refusal, and the case now passes.

Two caveats that keep this a live finding:

- **`rowspec_alt` does not enforce it**, and cannot: it never resolves a path
  at all, so it silently accepts an artifact the reference now refuses. An
  escape attempt is therefore *refused by one implementation and accepted by
  the other* — a divergence in the refusal set, which §2 calls out as the
  category that produces silent corruption rather than an argument.
- **The confinement root is whatever the caller passes as `base`.** The only
  shipped caller, `reference/rowspec/cli.py`, calls `evaluate(text)` — default
  `base="."`, the process working directory. So `rowspec check
  sub/a.mdtbl` resolves `a.mdtbl`'s lookups relative to the *cwd*, not to the
  artifact (violating §7's "relative to the referring artifact"), and confines
  to the cwd rather than to the repository. The check is real; the CLI hands
  it the wrong root. That is worth a follow-up in whoever owns `cli.py`.

`parse/lookup-computed-path` (`lookup(stem + ".mdtbl", …)`) covers the
*literal* half of the constraint. The reference refuses it. `rowspec_alt`
**accepts it and silently discards the `+ ".mdtbl"`**, looking up a file
literally named `stem` — a computed path partially evaluated, quietly. That is
an `alt` bug against a sentence the spec states plainly.

## 4. Divergence between the two implementations, and who is at fault

Six of `alt`'s eight failures share one root cause, and I read it as **the
specification's fault, not `rowspec_alt`'s**. Its source says so explicitly:

> §7 defines `lookup()`; §8 forbids I/O and `evaluate()` is handed only this
> artifact's bytes, so the target row is always absent and the defined result
> is `#REF!(file[key])`.

That is a defensible reading of a genuine contradiction the previous
adversarial pass already filed (M0-adversarial-cases §3 gap 2): §7 defines a
cross-artifact file reference, §8 says *"Constructs that would read … a path
are not blocked — they are unparseable"* and *"The evaluator is total,
terminating, deterministic and free of input/output."* `alt` resolved the
contradiction in favour of §8 and made every lookup a defined `#REF!`; the
reference resolved it in favour of §7 and reads files. **Both conform to a
consistent reading of the prose, and they produce different values for the
same table** — which is precisely the failure mode §2 says the spec exists to
prevent. `alt` is not wrong; the spec is under-determined, and §8's
"free of input/output" needs an explicit carve-out naming §7's lookup as the
one and only read, performed before evaluation, over a set of paths statically
visible in the artifact.

The remaining two `alt` failures are its own bugs: the computed-path
acceptance above, and `parse/lookup-target-duplicate-keys`, where the
reference propagates the target's §9.5 refusal to the referring artifact and
`alt` accepts — a consequence of the same no-I/O reading, but the *right*
answer is contestable either way (see §5).

## 5. What the spec leaves undetermined about cross-artifact references

1. **Whether a lookup reads a file at all** (§7 vs §8). The root cause above.
   Nothing else in this list matters until this is settled.
2. **A target with no `key` declaration.** §7 says "resolved by the target's
   own declared key"; if there is none, the spec does not say whether the
   result is `#REF!`, a refusal, or fallback to some other column.
3. **A column absent from the target.** §8's `#REF!(name)` and §8's
   `#REF!(file[key])` both have a claim; the reference invents a third form.
4. **A target file that does not exist.** Not in §9's refusal list, and not
   obviously "the target row is absent" either.
5. **A malformed target.** If B violates §9, is A refused, or is A's lookup
   column `#REF!`? A refusal means one artifact's corruption can make an
   unrelated, valid artifact unreadable; `#REF!` means a §9 violation goes
   unreported to anyone not opening B directly. Both are defensible; neither
   is stated. I filed the refusal reading because §1 prefers refusing to
   guessing.
6. **Whether a lookup sees *computed* columns of the target.** Undefined, and
   the reference's answer is a silent blank (§2 above). This is the one that
   needs settling first because it is currently silently wrong, not merely
   ambiguous.
7. **Cycles.** §8 promises termination and nothing else. `parse/lookup-cycle`
   asserts only that A ↔ B terminates with a *defined outcome*, because the
   spec does not determine the value: the reference yields `''` (a consequence
   of gap 6, not a decision) and `alt` yields `#REF!(b.mdtbl[b1])`. I did not
   invent an answer. Recommended: `#REF!(cycle)`, matching the reference's
   existing intra-table cycle handling, so the two cycle kinds agree.
8. **What "the repository" means.** §7 confines the target to it and never
   says how a reader finds its root — nearest `.git`? nearest `.rowspec`? a
   caller-supplied base? The reference answers "whatever `base` the caller
   passed", which makes a security property a caller responsibility (§3).
9. **Symlinks and absolute paths.** The reference's new check happens to
   handle both (`realpath` + an `isabs` refusal). Neither is mentioned in the
   spec, so a second implementation has no reason to.

## 6. Regression status

- **Existing cases: unchanged, and unaffected by the runner change.** Verified
  by re-running with a mechanically de-based copy of `run_cases.py`: identical
  failure sets before and after. The only behavioural difference is which
  directory a lookup resolves in, and no pre-existing case resolves one.
- **Mutation gate: 0 survivors.** `33 killed, 0 survived, 2 equivalent`.
- **1 stale mutant, not mine.** `is-align-matches-any-dashed-cell` went stale
  when another agent edited `is_align()` in `table.py` during this session
  (dropping the `if c != ""` guard). Immediately after my runner change the
  gate reported **0 stale**; it went stale on their edit, several minutes
  later. Repair, for whoever owns that change — in both halves of the pattern:

      'return bool(cells) and all(_ANY.fullmatch(c) for c in cells if c != "")'
      ->
      'return bool(cells) and all(_ANY.fullmatch(c) for c in cells)'

- **`pytest`'s `test_conformance_suite_passes` asserts exit 0**, so it now
  fails on the 4 spec-derived lookup cases. That assertion contradicts
  `mutants.py`'s own stated model ("The reference itself does not pass every
  case — the suite is written adversarially and runs ahead of the
  implementation"). Someone should decide which is the project's position; the
  mutation gate already handles a non-empty baseline correctly and does not
  need the suite to be green.

### Two new mutants worth adding (verified, not applied)

`conformance/mutants.py` is not mine to edit and is being edited concurrently.
Both were applied out-of-tree and confirmed **killed by cases that pass at
baseline**:

- `lookup-absent-row-is-blank` —
  `r[nm] = tgt.get(valcol) if tgt else f"#REF!({path}[{r.get(keycol)}])"`
  → `… else ""`. Killed by `rowrel/lookup-absent-row` and
  `eval/lookup-ref-poisons-aggregate` (which then reports `total = 10.0`: a
  broken reference summed as if it were readable, exactly §8's prohibition).
- `lookup-resolves-by-row-position` —
  `idx = {str(o.get(okey)): o for o in orows}`
  → `idx = {str(i): o for i, o in enumerate(orows)}`. Killed by
  `rowrel/lookup-resolves`, `rowrel/lookup-self` and
  `eval/lookup-ref-poisons-aggregate`. This is the coordinate bug the whole
  format exists to exclude, reintroduced across an artifact boundary; until
  now nothing in the suite could see it.
