# C. The mechanical namespace audit — `experiments/X3-namespaces/`

The red team's highest-yield recommendation was: *"mechanically apply PASS4's
co-location rule to every namespace in every format, as a conformance test."*
Nobody had done it. Seven breaks were known; nobody knew if that was the tail
or the head.

## Method

For every namespace in every format, construct a real collision — two branches
each introducing a colliding binding — then record what stock git does and what
the parser does with the merged result. A namespace is safe if EITHER holds:

    CO-LOCATED   all bindings sit on one line, so git sees the collision
    VALIDATED    the parser refuses the collision wherever it sits

## Result: 11 namespaces, 0 unprotected

    format   namespace         git merge   parser verdict                    protected by
    .tbl     column name       CONFLICT    -                                 co-location
    .tbl     aggregate name    clean       duplicate aggregate name          validation
    .tbl     row id            clean       duplicate key id='r_0009'         validation
    .tbl     key declaration   clean       duplicate key declaration         validation
    .md      link label        clean       duplicate link label 'api'        validation
    .md      footnote label    clean       duplicate footnote label 'n'      validation
    .md      heading anchor    clean       duplicate heading anchor          validation
    .md      frontmatter key   clean       duplicate frontmatter key         validation
    .canvas  node name         clean       duplicate node 'cache'            validation
    .canvas  layout key        CONFLICT    -                                 co-location
    .canvas  dangling edge     clean       edge references unknown node      validation

Note that writing this audit REQUIRED writing the `.md` and `.canvas`
validators, which did not previously exist. The audit is therefore also the
specification of what those parsers must do — which is what a conformance suite
is supposed to be.

## The finding that matters, and it corrects PASS4

**Only 2 of 11 namespaces are protected by co-location. Nine require the
validator to run.**

PASS4 stated co-location as the rule and treated validation as the fallback.
That is backwards. Most namespaces are *inherently* scattered — one row id per
row, one node per line, link labels wherever the prose puts them — and cannot
be co-located without deforming the format. Co-location is the lucky special
case; **validation is the general mechanism.**

## Which means those nine are NOT I6-compliant on their own

Under stock git with none of our tooling installed, a duplicate row id or a
duplicate link label merges clean and sits in the file. A person running `cat`
or another tool sees a silently duplicated binding. I6 as written — "correct or
loud under unmodified git" — does not hold for nine of eleven namespaces.

This is the honest gradation the report should carry:

    2 of 11   safe for everyone, unconditionally
    9 of 11   safe for anyone whose toolchain validates on load

## But there IS a portable enforcement point, and it is CI

Hooks are not cloned. Merge drivers need local config and are ignored by bare
repos. But **a CI workflow file is a tracked file in the repository and runs on
the forge with no local configuration whatsoever.**

    `gws check` in CI is the portable enforcement mechanism this design has
    been missing.

It catches all nine validated namespaces at pull-request time, on the forge,
for every contributor, with nothing installed locally. It is the one extension
point git-hosting offers that actually travels with the repository — and the
design had not identified it, having been focused on merge drivers and hooks,
both of which do not travel.

That also fits the evidence from the computation research: the only
error-reduction intervention with real evidence behind it is **code
inspection**, and CI is where code inspection is enforced.

## Consequence for the deliverable

The validator moves from "supporting tool" to **part of the format's
correctness story**, and shipping a ready-made CI workflow becomes a
first-class artifact rather than packaging convenience.

## Verified: CI is the only repo-resident config a forge executes

    CI workflow file present in a fresh clone : YES
    pre-commit hook present in a fresh clone  : no
    merge driver config in a fresh clone      : UNSET

Three mechanisms, one travels. That settles where enforcement lives.

## A twelfth namespace, of a different KIND: corpus-scoped

`cp doc.md copy.md` duplicates the minted artifact UUID that the annotation
sidecar is keyed by:

    DUPLICATE ARTIFACT ID 01J8ZQ4K7X in ['copy.md', 'doc.md']

**No single file is invalid**, so a per-file parser can never catch it. Only a
corpus-wide scan can. That makes it a distinct category from the eleven in-file
namespaces, and it reinforces the same conclusion: some correctness properties
of this design are only checkable in a whole-repository pass, and CI is the only
place such a pass runs portably.

    in-file namespaces      11   checked by the parser, on load
    corpus namespaces        1   checkable only by a repository-wide pass

Both categories land in `gws check`. Neither is reachable from a merge driver,
which is the mechanism the design spent the most effort on and which turns out
to matter least.
