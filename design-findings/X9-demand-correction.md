# Correction: the demand evidence for the validator pivot was overstated

The pivot from "correct merging" to "the validator" rested on one sentence I
have repeated in every summary since:

> Four public reference-data registries had each independently built a CI
> check, a bespoke `db:validate`, and a CONTRIBUTING file warning contributors
> in bold to "make sure that the number of columns in the file has not
> changed."

Reading their actual code, that is wrong in three of the four cases.

    iptv-org/database       hand-rolled -- and the ENTIRE structural check is
                            26 lines of TypeScript inside 1,674 lines of
                            validation. The other 1,648 are domain rules.
    ccao-data               NO file-level check of any kind. 59 dbt tests, all
                            running in Athena AFTER load, behind AWS OIDC.
                            Their pre-commit has hooks for five languages and
                            none for CSV.
    datasets/country-codes  did NOT hand-roll. `make test` is one line:
                            `frictionless validate datapackage.yml`.
    toolleeo/...-in-a-csv   NOTHING. No CI, no validator, no schema. The
                            Makefile only regenerates the README.

**So the claim reduces to: one registry hand-rolled 26 lines of structural
checking, and a second adopted an existing tool rather than writing one.** The
bolded CONTRIBUTING warning is iptv-org's, singular.

That is still evidence — the check people write by hand is exactly the
field-count check, and iptv-org named a fixture directory after it — but it is
one data point dressed as four, and I dressed it.

## The addressable surface, measured

    registry          their checks   rowspec-expressible   share
    iptv-org                   154                    10    6.5%
    ccao-data                   59                    11     19%
    country-codes               69                     1    1.4%
    toolleeo                     0                     0     n/a

Inexpressible by rowspec: **composite keys** (8 of 28 real uniqueness
constraints are composite, and `key` takes one column), two unique columns in
one file, case-folded uniqueness, cross-file referential integrity, cardinality,
and every domain membership rule.

## Verdicts, which are mostly negative and should stay that way

- **iptv-org — keep the script.** rowspec covers 10 of 154 checks, would drop a
  CRLF requirement they enforce *deliberately*, and cannot express 3 composite
  and 12 case-folded uniqueness checks. The one defensible addition is a
  duplicate-column-name check: four lines of TypeScript in the function that
  already splits the header.
- **country-codes — keep Frictionless.** rowspec is a strict downgrade.
- **ccao — the only genuine fit, and additive rather than a replacement.** But
  `frictionless validate` would catch the same defect *and* express their
  composite keys and 31 column types. **The finding is the architectural gap,
  not this tool.**
- **toolleeo — no verdict available.** They validate nothing, which is its own
  answer.

## The one real defect found, with provenance

`ccao-data`, `dbt/seeds/pinval/pinval.vars_dict.csv` line 28: two fields against
a three-column header. Commit `00d8064` (2025-08-20) stripped a trailing empty
column and got 118 rows right and this one wrong in the same commit. It has
survived three later PRs and every CI run since — **twelve months** — and is
invisible to every check they own, because their checks run after load.

## The strongest argument that survives, and the weakest

**Strongest.** Nobody hand-writes a duplicate-column-name check. Everyone writes
the field-count check. And a duplicated column name has **correct field counts
and correct values**, so it is invisible to the check everyone writes *and* to
every domain validator simultaneously. That is a genuinely unoccupied niche.

**Weakest, and it is very weak.** The addressable surface is 1.4%–19% of what
these teams actually do, and 0% where Frictionless already runs. On the
best-maintained registry in the corpus, running against 40,834 production rows,
the tool finds **nothing**. A validator that adds one check to a mature stack
does not earn a dependency, a sidecar, and loss of control over error messages.

## Two hazards this surfaced

**The sidecar lets a maintainer assert a key that is not one, and rowspec
believes them.** Declaring `key` on a non-unique column produces confident wrong
refusals on valid files — 206×24 rows refused on one, fourteen legitimate
name collisions on another. M1's refusal to *infer* keys was right; the sharper
point is that asserting one is equally dangerous in the other direction.

**§9 has grown to 20 refusals, and refusal 14 makes a leading BOM a MUST.**
Under a literal reading that refuses 70 of 72 iptv-org files. CSV mode
deliberately demotes BOM and CRLF to warnings, and the spec does not yet say
that CSV mode is a separate conformance profile. It must.
