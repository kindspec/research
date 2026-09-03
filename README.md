# research

The design record behind [kindspec](https://github.com/kindspec) — the passes,
the measurements, and the experiments that produced
[rowspec](https://github.com/kindspec/rowspec) 0.1.0 and the design briefs for
[blockspec](https://github.com/kindspec/blockspec) and
[nodespec](https://github.com/kindspec/nodespec).

**This is a record, not a specification.** Nothing here is normative. Where this
repository and a published `SPEC.md` disagree, the spec wins and this is the
history of how it got there.

It is published for one reason: the specs cite these measurements by name, and a
citation that resolves to nothing is not evidence.

## How to read it

    DESIGN.md              the overall verdict — start here
    RESEARCH.md            the prior-art survey the design pass began from
    SPEC-table.md          the table kind's spec as it stood before rowspec
    design-findings/       one file per pass: what was asked, measured, decided
    findings/              the competitive and market teardowns
    experiments/           the code that produced the numbers, and its output

`design-findings/STATE-OF-PLAY.md` and `design-findings/X-open-problems-closed.md`
are the closest thing to a summary. `ADJUDICATION.md` records where two
independent passes disagreed and how it was settled.

## What is deliberately not here

**The corpora.** 1.9 GB of cloned repositories, downloaded benchmark archives
and generated git histories are excluded, along with virtualenvs and build
artifacts. Every one is named in [CORPORA.md](CORPORA.md) with its source, so a
run can be reproduced rather than trusted.

**A third-party product teardown.** One experiment disassembled a shipped
competitor's bundle to see how it stored documents. Neither the vendored bundle
nor the write-up is published: the write-up identifies a named individual and
their private infrastructure, and the project's argument does not need it. What
it concluded is recorded in `findings/00-pithy-teardown.WITHHELD.md`, and
`findings/01-direct-competitors.md` covers the same ground from public sources.

**Two raw output files over 2 MB** — `D0-dogfood/ledger-iptv-channels.jsonl` and
`E4-if-sum/out/noteval.json`. Both are regenerable from the scripts beside them;
the aggregated results that the findings actually quote are tracked.

## The method, in three lines

Every substantive defect this project found was found by **two independent
implementations disagreeing**, by a **mutation gate** that had to notice a
deliberate break, or by a **mechanical check catching a check that could not
fail**. None was found by review. That is the transferable result, and it has
nothing to do with tables.

## Licensing

Prose — `*.md`, `design-findings/`, `findings/` — is **CC-BY-4.0**.
Experiment code and its output — `experiments/` — is **MIT**.
Full texts in `LICENSES/`. See [LICENSE](LICENSE).
