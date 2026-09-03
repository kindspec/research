<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# Naming: the org, and the family of kinds

Decided 2026-08-30. Clearance run the same way `rowspec`'s was — every name
checked against the GitHub handle, PyPI, crates.io and npm, not one of them.

## The org: `kindspec`

    github.com/kindspec        claimed 2026-08-30
    pypi / crates.io / npm     all clear

**A specification and conformance suite per artifact kind.**

The word is the project's own. `DESIGN.md` says "Tables are the beachhead";
`PLAN.md` scopes v0 as "the document and canvas kinds ... specified as future
kinds, not implemented"; `SPEC.md` §13 is "Conformance profiles". *Kind* was
already the noun for the thing `rowspec` is one of, so the org name required no
new vocabulary.

The only pre-existing use of the string anywhere on GitHub is a 0★ Rust
life-sim using `KindSpec` as an internal type name. No conflict.

**What was rejected, and why it is worth writing down.** `plainspec`,
`textspec` and `conformal` are taken GitHub orgs. `diffable` is a dormant user
plus taken on crates and npm. `reviewable` is an active 35-repo org whose
product is *code review* — the one collision that would have actively hurt,
since this project's value proposition is review. `artifactspec` cleared
everywhere and was dropped anyway: on GitHub, "artifact" means build output.

Considered and not chosen, all clear on all four: `nominalform` (names the
thesis — nominal rather than positional addressing, held in a canonical form —
and is the most distinctive, but opaque without a sentence), `loudspec` (names
I3, the invariant that actually differentiates the work, but lets one of seven
invariants stand for all of them), `conformspec` (names the method, which is
the only part with no prior art, but redundant morphemes).

## The kinds: named after the unit of identity

    rowspec     rows      opaque row ids                exists
    blockspec   blocks    deliberately NO minted ids
    nodespec    nodes     named, not positional

`rowspec` is not named after tables. It is named after the **row**, and the row
is where that format's identity decision lives. Identity is the axis every one
of these formats turns on — `DESIGN.md` settles it as "minted artifact UUID;
opaque row ids; **no** minted ids for prose blocks; quote-anchoring for
annotations" — so naming each kind after its unit names the hard part rather
than the subject matter.

The rejected alternative, `rowspec` / `prosespec` / `canvasspec`, mixes three
kinds of noun: a unit, a content type, and a container. It reads more easily
and it is less true.

**Registry status.** `rowspec` and `blockspec` are clear on PyPI, crates.io and
npm. **`nodespec` is taken on npm** and clear on the other two — the one open
item, and it only binds if a JS package is ever published under that name. A
repo name needs only to be free *inside* the org, so the GitHub handle being
taken for `blockspec` and `nodespec` is irrelevant; it was the org handle that
had to be globally unique.

`docspec` is the one name genuinely lost: taken on the GitHub handle **and** all
three package registries. It is why the document kind is not called that, and
the unit-based scheme is a better answer to that constraint than a workaround
spelling like `docuspec` would have been.

## Transfer note

`rowspec` contains **no hardcoded owner references** — no `CameronBrooks11` in
any tracked file, and `pyproject.toml` declares no project URLs. Moving it into
the org changes nothing inside the repository. GitHub redirects the old URL and
carries the issues across; only a local `git remote set-url` is needed.
