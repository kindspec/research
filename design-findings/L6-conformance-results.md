# L6 — the conformance suite, which is the actual deliverable

`experiments/L6-conformance/`. Pass 4 argued the substrate's most important
artifact is an executable test suite rather than a program, on the CommonMark
spec-tests model. This is that suite, running against a **stock git binary**
with no drivers, no `.gitattributes`, and none of our tooling installed.

## What it checks

    I1  round-trip     render(parse(b)) == b over a corpus
    I1  idempotence    canon(canon(x)) == canon(x)
    I6  stock-git      for each concurrent-edit scenario, assert the outcome is
                       the DECLARED one (clean or conflict) -- and when clean,
                       EVALUATE the merged artifact and assert the value is
                       correct. A clean merge with a wrong value is reported as
                       "SILENTLY WRONG", which is the category that matters.
    I3  loud failure   break a reference; assert the error propagates

The harness is ~60 lines. It creates a real repo per case, commits two
branches, runs `git merge`, and inspects both the exit code and the semantics.

## Results

    === .tbl (nominal addressing) ===
      I1 round-trip                          PASS
      I1 idempotence                         PASS
        two distant row inserts              clean     ok
        same-row concurrent cell edit        conflict  ok
        column-name collision (namespace)    conflict  ok
        disjoint cell edits in different rows clean    ok
      I6 stock-git                           PASS
      I3 loud failure                        PASS

    === .md (boundary-parsed) ===
      I1 round-trip                          PASS
      I1 idempotence                         PASS
        edits to different paragraphs        clean     ok
        both edit the same paragraph         conflict  ok
        scattered namespace: dup link label  clean     MISMATCH
      I6 stock-git                           FAIL

**The designed format passes every invariant. Markdown fails at exactly one
point — the scattered-namespace defect — and that is the correct result.** A
conformance suite that could not fail the incumbent would not be measuring
anything.

## It caught two bugs in its own test cases first

Worth recording, because it is evidence the suite has teeth:
1. The namespace-collision case built both branches with an identical no-op
   edit, so a clean merge was correct and the "failure" was mine.
2. The disjoint-edit case asserted an arithmetically wrong expected total
   (396 vs the correct 516). The suite flagged a correct merge as SILENTLY
   WRONG — because I had told it the wrong answer.

Both were my errors, found within minutes of the suite existing. This is the
third time in this project that writing down an invariant and then testing it
caught something discipline alone did not (see L2's alignment-row bug and L3's
hash-identity duplication).

## Why this is the deliverable rather than a supporting artifact

- It is what makes the design FALSIFIABLE. Any proposed format either passes
  or does not, and "SILENTLY WRONG" is a machine-checkable verdict.
- It is what makes implementations REPLACEABLE. CommonMark has independent
  implementations because it shipped an executable spec; org-mode has none
  because its spec is descriptive of `org-element.el`.
- It runs against stock git, so it tests the property that actually matters in
  deployment rather than the property that is convenient to implement.
- It is small enough to be maintained for decades by people who did not write
  it.
