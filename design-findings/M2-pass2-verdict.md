# M2, pass two: did the lexical grammar close the gap?

Pass one's verdict was that **the architecture transmitted and the surface
syntax did not**. §4.1 was written because of that sentence. The same author,
still forbidden to read the reference implementation, re-implemented against the
amended spec.

## The measurement

    pass 1   7 inferred behaviours wrong   (57/57 then 9 of 74 later cases failed)
    pass 2   1                             (a larger rewrite, against a larger suite)

And the fixture's own `WHY.md` agrees the remaining one is a spec gap rather
than an implementation error. Final: **190/190 on both implementations.**

Of the 22 items pass one listed as "never stated at all", §4.1 closes
**fifteen outright**, and the author implemented every one from the prose
correctly on the first attempt.

## The three sentences that did work no other formulation would

- **The normative classification order, with its reasoning.** The author would
  have guessed `|||||||`; they say they would *not* have guessed `annotation`
  before `table-line`, and would then have had to invent what a `#` between two
  data rows does.
- **"MUST NOT degrade a failed recognition into a different successful one."**
  Settles a dozen questions §4.1 never individually enumerates.
- **The `[CHOICE]` tags** — they tell an implementer where *not* to look for a
  deeper reason.

That is a useful result on its own: what transmitted was not the volume of
prose but three sentences that each carried a rule, its wrong alternative, and
why the alternative is wrong.

## What still does not transmit, and an amendment made it worse

**The header-cell formula language has no grammar anywhere.** §4.1 defines
`declaration`, `rhs` and `arg` and defers predicates to §7; §7 has no grammar
either. Neither covers the language every computed column is actually written
in. Every serious remaining ambiguity lives there.

And §4.1 made two of them worse by fixing `ident` without fixing the grammar
`ident` appears in:

- **`ident` admitted `-`, and the formula language uses `-` as subtraction.**
  `a-b` was a well-formed column name that could never be referenced, and two
  readers would silently total different columns. Fixed by dropping `-` and `.`
  from the identifier set — the cost is the ability to name a column `a-b`.
- **An all-digit token means different things in different positions.**
  `g := sum(123)` is the column; `| c = 123 * 2 |` is the literal; and
  `g := sum(1)` is a silent broken reference rather than a refusal. Still open.

## Contradictions the amendments introduced, now fixed

Seven sections changed in one pass under three different authors, which is
exactly how contradictions get in.

- **§9 claimed "This list is complete" and was missing three refusals the suite
  enforces** — a malformed column formula, a computed lookup path, and a target
  outside the repository. The completeness claim is load-bearing: it is what
  lets an implementer stop looking, so a false one is worse than none. Now 23
  entries and true.
- **§8's carve-out was right and its closing paragraph then overreached** — it
  still said constructs reading "a path" are unparseable, while `lookup` reads
  one. Now excepted explicitly.
- **§9.16 became unreachable** once §4.1.9 made identifiers an allowlist, so
  §3's `Cf` rule was decorative. It now says it is a consequence, and keeps only
  the *reason*, which the allowlist does not carry.

## Still open, and worth naming

`canon` on a CRLF file: §3/§10 say only the canonical form is LF, §4.1.1 says
declarations are left byte-verbatim, and for a CRLF file those give different
bytes. Both are idempotent, so the existing case passes either way — verified
by mutation. §2 names the canonical byte form as deliberately specified
*because* disagreement causes silent corruption, and here are two `canon`s that
would fight in a pre-commit hook, each producing a whole-file diff.

Also: a self-referential lookup reads the file on disk rather than the bytes
handed to `evaluate`, so a tool that merges and validates a buffer before
writing computes answers from the pre-merge file. And validity is therefore not
a function of an artifact's own bytes but of **bytes plus lookup closure**,
which §12 and §4.1.8 both currently deny.

## What this says about the method

The suite did not find these. A second implementer reading the prose did, and
the difference between pass one and pass two — seven wrong inferences down to
one — is the only direct measurement anyone has of whether a specification
improved.
