<!-- SPDX-License-Identifier: CC-BY-4.0 -->
# 00 — competitor teardown (withheld)

A binary teardown of a shipped competitor in this space was performed and is
cited elsewhere in this repository. **It is not published here.**

The analysis identifies a named individual, two of their private repositories,
a CI build path and a live telemetry endpoint, all read out of a public release
artifact. Every one of those facts is obtainable by anyone who downloads the
same file, and none of it is a vulnerability — but republishing them as a
dossier is a different act from finding them, and it is not one this project
needs in order to make its argument.

**What it concluded, which is the part that matters here:** the product is a
competent single-author git-backed markdown editor. It does not attempt the
thing kindspec exists for — it stores documents so they round-trip, not so that
a merge of two edits is correct or refused. It is not a prior implementation of
this format's thesis.

`findings/01-direct-competitors.md` covers the competitive landscape from public
sources and is sufficient for every claim the specs make.
