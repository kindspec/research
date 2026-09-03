<!-- SPDX-License-Identifier: CC-BY-4.0 -->
> **HISTORICAL — superseded, and wrong in four places.**
>
> This was rowspec's bootstrap plan. Every milestone it describes (M0, M1, M2)
> is done, and its closing status section has since gone stale:
>
> | it says | actually |
> |---|---|
> | "a full lexical grammar (§4.1) is not written" | written — `SPEC.md` §4.1 |
> | 130 conformance cases | 410 |
> | "two mutation-gate holes are open" | 74 killed, 0 survived, 0 stale |
> | M0 remaining work: collapse duplicated implementations, retire `cases.py` | done |
>
> The live plan is [rowspec/ROADMAP.md](https://github.com/kindspec/rowspec/blob/main/ROADMAP.md).
> This file is kept because §7's two standing rules and §8's credit list were
> written here first and are still the ones being followed.

# rowspec — bootstrap plan

Name: **rowspec**. Verified clear on crates.io, npm, PyPI and the GitHub handle.
File extension: **`.mdtbl`** (0 files on GitHub, against `.tbl`'s 158,208).

Optimising for **design**, not adoption. That decision changes the plan in one
specific way: we settle the open questions rather than shipping around them, and
we do not gate design choices on demand evidence. The demand finding still
governs how the project is *described* — see §7.

---

## 1. What rowspec is

A specification for tabular data that must survive version control, with an
executable conformance suite and a reference implementation.

    the spec        defines the format and, more importantly, the REFUSALS
    the suite       checks out two branches, runs stock git merge, EVALUATES
                    the merged file, and asserts on the computed number
    the validator   the spec's refusals, runnable on a file you already have
    the reference   one implementation, deliberately boring

The suite is the contribution. It is the only part with no prior art, the only
part with observed (hand-rolled) demand, and the part the architecture depends
on in three unrelated places — the parser needs it for 9 of 11 namespaces, CI
needs it because nothing else travels, and the merge server needs it because
`git merge-tree` cannot see its own clean-but-wrong outcomes.

## 2. Settled, with evidence in `design-findings/`

- Two primitives: text, and ordered entity maps. Tables are the first kind.
- Seven invariants (I1–I7), I7 revised after measurement.
- Correctness lives in the representation; type-aware merge is an accelerator
  outside the correctness boundary.
- Canonical form is unpadded. Alignment is a view.
- Identity: minted artifact UUID; opaque row ids; no minted ids for prose.
- Row order is declared (`order := by(c)`), typed, and totalled by the key.
- Cross-table `lookup()`, filtered aggregates, per-row group aggregates with
  `@col`, and conjunctive predicates — all nominal, all verified under merge.
- Meaning drift fires only on a true rebinding; six false positives eliminated.
- Git is the distribution and durability format; the version control is ours.
- A GitHub App plus one org ruleset is a working deployment. Self-hosting is
  not required.

## 3. Repository layout and licensing

The licence split is not decoration: we want independent implementations, so the
spec and the fixtures must be maximally reusable, and CommonMark's example of
embedding its test cases inside a CC-BY-SA spec document is the mistake to
avoid.

    rowspec/
      SPEC.md                 CC-BY-4.0     the normative prose
      conformance/
        cases/*.toml          CC0-1.0       fixtures, their OWN tree, no prose
        runner.py             MIT           executes cases against any impl
        mutants.toml          CC0-1.0       the mutation gate
      reference/              Apache-2.0 OR MIT
      validator/              Apache-2.0 OR MIT
      .github/workflows/      the portable enforcement point
      NOTICE                  git is GPL-2.0-only; we invoke it as a subprocess
      CONTRIBUTING.md         DCO, not a CLA

**Fixtures must become language-neutral data.** They are Python today, which
silently makes the reference implementation privileged. TOML or JSON, consumed
by a runner in any language. This is a v0 blocker, not a nicety.

## 4. v0 scope

**In:** the table format; the eleven refusals; declared typed order;
`cumulative`/`prior`/`delta`; column formulas; filtered, group and cross-table
aggregates; canonicalisation; the conformance suite with the mutation gate; the
validator in CSV mode and native mode; the CI workflow.

**Out, explicitly:** the document and canvas kinds (specified as future kinds,
not implemented); the merge server; real-time collaboration; import from
`.xlsx`; any GUI. Export to `.xlsx` is out of v0 but is the strongest
downstream story and should be first after it.

## 5. Design questions still open

| Question | Direction | Cost |
|---|---|---|
| **Composite keys** — 31.5% of real INDEX usage; `key := col` takes one column | `key := (region, sku)`; row identity becomes a tuple | small, but touches merge |
| **Cross-artifact table→table column formulas** | `lookup()` covers it; fold into the single reference impl | small |
| **Comparison / range predicates** | measured at 0.1% of real usage — **do not build first** | defer |
| **2-D matrix lookups** (17% of INDEX) | wide by construction; no long-form equivalent. Probably out of scope forever — say so | decide |
| **`.mdtbl` vs a schema sidecar for CSV mode** | both; the sidecar is what makes zero-migration validation possible | small |

## 6. Milestones

**M0 — the spec is executable.** Fixtures converted to language-neutral data;
one reference implementation (the current copies have already diverged twice);
the suite green; the mutation gate at zero survivors; CI running all three steps
from a clean checkout.

**M1 — the validator runs on files people already have.** CSV mode: six of the
eleven refusals need no format migration, verified — including a committed
conflict marker, which Python's `csv` module parses as seven valid rows without
complaint.

**M2 — a second implementation, written by someone else, from the spec alone.**
This is the real test of M0 and the only way to find out whether the prose
defines or merely describes.

**M3 — export to `.xlsx`.** Verified essentially lossless with real structured
references and `SUBTOTAL` aggregates recalculating in LibreOffice.

## 7. Two standing rules

**The suite cannot be written by whoever writes the reference implementation.**
"11 namespaces, 0 unprotected" and "15 mutants, 15 killed" were both artifacts
of the enumerator being the implementer; an adversary then found 14 surviving
mutants and 7 silent-wrong cases. Three occurrences of one failure mode. An
adversarial suite author is a standing role, not a review step.

**Do not lead with the merge.** Demand for it is measurably absent — a 230:1
give-up-to-hack ratio, and GitHub archived its own version. Lead with the
validator and the spec. Correct merging is a property you get, not a reason
anyone will adopt it.

## 8. Credit, on the first commit

**Coopy/daff** — thirteen years of shipping row-ID-aware git-integrated CSV
merging. State the divergence explicitly: its author chose content-based
matching and treated IDs as optional; rowspec makes an opaque id mandatory.
**ClassSheets** (ASE 2005) and **Object Spreadsheets** (Onward! 2016) for
column-scoped formulas. **Lotus Improv** and **Javelin** for named-dimension
modelling. **org-mode `#+TBLFM:`** as the twenty-year negative control.

Do not cite Quantrix, Erwig's Gencel, or Subtext "Schematic Tables"
specifically — unverified by two research passes.

---

## M0 progress — the spec is now executable

**Fixtures are language-neutral.** 57 cases, 133 files, 8 categories. Each case
is a directory of real `.mdtbl` files plus one `expect.json`:

    cases/merge/distant-row-inserts/
      base.mdtbl  ours.mdtbl  theirs.mdtbl  expect.json

    { "kind": "merge", "git_outcome": "clean",
      "then": "evaluate", "aggregates": { "grand": 660.0 } }

Directories of real files rather than one JSON blob of embedded strings,
because fixtures should be openable in any tool and **diffable** — the
project's own thesis applied to itself.

**A runner that never imports the case definitions** (`run_cases.py`) produces
the same verdict as the Python one: 0 failures against the reference
implementation, and it correctly rejects a parser whose entire structure is
`{'raw': text}`. That is the test of whether the fixture tree is sufficient for
someone else to implement against, and it passes.

**The mutation gate now runs off the tree too.** 36 mutants, 27 killed, the
remainder correctly classified as equivalent, 0 surviving.

Converting the fixtures immediately caught a bug in the conversion itself: one
case checked row values rather than aggregates, and exported as an empty
aggregate assertion it asserted nothing. The gate found it. That is the fourth
time a mechanical check has caught something review did not.

**Remaining M0 work:** collapse the duplicated reference implementations into
one (they have now diverged twice, and both times the divergence was invisible
until something ran all copies against the same cases); retire `cases.py` and
`runner.py` once the tree is authoritative; move the `.md` and `.canvas`
validators out of the namespace-audit script into real modules.

---

## Status after the first build pass

    repository        rowspec/, scaffolded from dev-toolbox (Python profile)
    conformance       130 cases, 0 failures
    independent impl  0 failures — written from SPEC.md alone
    mutation gate     32 killed, 2 survived, 2 equivalent, 0 stale
    just check        passes
    just test         42 passed, 1 failed (the gate, honestly reporting 2 holes)

**M0 — done.** Fixtures are language-neutral directories of real files. A runner
that never imports the case definitions gives the same verdict. The gate runs
off the tree, and its patterns are now durable — they survived a full
`ruff format` that previously staled 23 of them.

**M1 — done.** CSV mode, run against 1,564 real public CSVs: 16 refused, **zero
false positives**, and 13 of the refusals are a live defect in
`owid/covid-19-data` that pandas reads silently.

**M2 — met.** A second implementation, by an author forbidden to read
`reference/`, passes all 130 cases. It got there only after its report forced
seven corrections to the prose.

### What is NOT done, and should not be claimed

- **The spec is not yet sufficient on its own.** M2's author passed 57/57 of the
  original tree and then failed 9 of the 74 cases added later — every failure a
  guess a fixture overturned. The three fixes it prescribed are partly applied:
  §3, §4, §7/§8 and §9's ignorable channel are amended; **a full lexical grammar
  (§4.1) is not written**, and that is the largest remaining spec gap.
- **Two mutation-gate holes are open**, with cases commissioned from the
  adversarial author rather than written by me.
- **`.mdtbl`-only refusals are untestable in CSV mode by construction**, and
  duplicate row id — the refusal the identity argument exists for — needs the
  sidecar. The pitch is "five lines", not "no migration".
- **§12 editions have no observable behaviour.** Specified, unimplemented,
  untested.
- Document and canvas kinds remain out of scope, as planned.

### Corrections this pass forced

1. The mutation gate disarmed itself on a reformat and reported it as a pass.
2. `canon = lambda x: x` scored 129/131 — a fixture with no runner branch.
3. Every `\r` was deleted before any implementation saw it.
4. A table with no alignment row silently ate a data row.
5. `canon` was not idempotent on GFM alignment spellings, and ate a row.
6. The spec documented §7 features the reference implementation never had.
7. §3's LF rule would have rejected 98.6% of a real public registry.

Six of the seven were found by someone other than their author. That is the
standing rule earning its keep in a single pass.
