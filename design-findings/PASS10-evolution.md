# Pass 10 — format evolution, and the resolution of the strict-parsing tension

## The tension

I7 says: reject unknown input, never skip — because a permissive parser summed
both sides of a conflict and produced a number neither author wrote. But
must-ignore semantics is how formats evolve without forking. These appear to be
in direct conflict.

## The resolution: HTML5's third position, "specified permissiveness"

XHTML chose STRICTNESS — a fatal error on malformed input — and lost.
HTML4/SGML chose UNSPECIFIED PERMISSIVENESS and produced a decade of
per-browser quirks. HTML5 chose neither:

    Every input has exactly ONE defined outcome, and a parse error is
    DETECTED and REPORTED separately from being HANDLED.

WHATWG: "Certain points in the parsing algorithm are said to be parse errors.
The error handling for parse errors is well-defined." A browser and a
conformance checker run the same algorithm and differ only in whether they
*report*.

The counter-example is decisive and expensive. RFC 2616 (1999) left
Transfer-Encoding vs Content-Length ambiguous; RFC 7230 (2014) said such a
message "ought to be handled as an error" — which is not a conformance
requirement; only RFC 9112 (2022) mandated "the recipient MUST treat it as an
unrecoverable error." **Twenty-three years, and the gap was the HTTP request
smuggling vulnerability class.**

    An ambiguity that is harmless for one implementation becomes a
    vulnerability the moment two implementations of the same spec meet in one
    data path.

That is the normal case for any successful format, not an exotic one.

## The principled line for THIS design

Reject versus ignore is decided by what the alternative would produce:

    If degrading gracefully could yield a plausible VALUE   -> REJECT
      conflict markers, duplicate names in a namespace, a cell that will not
      coerce, an unparseable aggregate declaration

    If degrading could only lose DECORATION                 -> PRESERVE, WARN
      an unknown attribute, an unrecognised annotation, a future block type

This is I3 lifted to the parser: anything that could produce a wrong number
must fail loudly; anything that could only lose an ornament may degrade with a
signal. I7 is therefore not "reject everything unknown" — it is "never let an
unknown thing contribute to a computed result."

## The near-controlled experiment for the whole thesis

CommonMark and djot share an author. djot is the better language design — jgm
wrote it precisely because "there are 17 principles governing emphasis... and
these rules still leave cases undecided", and "I despair, at times, of getting
to a spec that is worth calling 1.0."

    CommonMark   655 executable examples in the spec   ~45 implementations,
                 (9,811 lines)                          25+ languages
    djot         NO conformance suite, no test/ dir     6 implementations,
                 releases stop at 0.2.0                  4 years in

Same designer. Better design. No suite. **An order of magnitude fewer
implementations.** This is as close to a controlled experiment as this
literature offers, and it is the strongest single piece of evidence that the
conformance suite is the deliverable rather than a supporting artifact.

Independent corroboration of the mechanism: every serious CommonMark
implementation states conformance as a *version number of the test suite* —
"compliant with CommonMark 0.31.2" — which is a testable assertion. And
python-markdown's "This is not a CommonMark implementation; nor is it trying to
be!" is only a meaningful statement because there is something to fail.

## But copy the mechanism and fix its central defect

CommonMark's own spec concedes it: "not every feature of the HTML samples is
mandated by the spec." Two implementations at 100% conformance can build
structurally different trees.

    Testing input -> HTML constrains ONE PROJECTION of the model,
    not the model.

**The suite must constrain the data model.** For this design that means the
suite asserts on parsed entity maps, resolved addresses, and evaluated values —
not only on rendered output. L6 already does this by accident (its I6 cases
evaluate the merged artifact), and R1 showed the cost of the half that does
not: the `.tbl` round-trip test is a tautology because `parse` and `render` are
identity functions.

Two further CommonMark warnings worth heeding: it is **still 0.x after twelve
years**, and a commenter on its own 1.0 thread notes extension authors held off
writing specs while waiting for it — the 0.x label imposed real ecosystem cost
even while the format was de facto stable. And **it cannot express a table**;
the single most-used feature after headings lives in a vendor document.

## Versioning: editions, not a version field in every file

A version field in every artifact is tempting and wrong here — a version bump
would touch every file, which is a direct I1 (locality) violation.

Rust's editions are the model, and the transferable insight is an
implementation detail rather than a policy: **edition is a property of the
source location, not of the compilation.** rustc marks spans with the edition
of the crate they came from, so a macro defined under one edition expands
correctly inside another. That is exactly the capability Python lacked.

The hard rule Rust states and never breaks: "crates in one edition **must**
seamlessly interoperate with those compiled with other editions." Node built a
dual-dialect system *without* that guarantee and produced the dual package
hazard — nine years, still incomplete, with `instanceof` failing across the two
loaders. Python had no coexistence at all: one interpreter, one language
version, so migration was all-or-nothing across an entire dependency tree.
Eleven years of dual maintenance, a sixteen-year long tail, and `six` was the
community hand-building a per-file edition system on a runtime that refused to
provide one.

Concretely for this design:

    - edition declared ONCE per repository, not per file
    - artifacts of different editions must coexist in one repository and one
      build, with no ceremony
    - migration tooling rewrites to the INTERSECTION -- valid under both the
      old and new edition -- so migration is incremental, never atomic.
      `cargo fix --edition` guarantees exactly this, and it is why Rust's
      migration story is not Python's.
    - escape hatches are DATED. Go publishes a minimum lifetime for its GODEBUG
      compatibility settings (two years, four releases); Rust makes no
      time-bounded promise, and Go's is the better practice.

## And the honest naming rule

Three unconnected communities converged on the same conclusion: past a certain
size of change, a new name is more honest than a version bump. Mattijsen on
Raku ("only differ in what many perceive to be a version number, is hurting the
image of both"), MacFarlane on djot ("it should probably be an entirely new
project under a new name"), and Hickey generally ("Breaking changes are broken.
It is just a terrible idea... this coexistence means that people can just
freely proceed").

## Ranked: what a format spec must ship with

    1. AN EXECUTABLE CONFORMANCE SUITE -- decisively first, per the djot
       experiment. It converts "conforming" from a claim into a measurement,
       and that is the only thing that reliably produces independent
       implementations. Version the SUITE, not just the spec.
    2. FULLY SPECIFIED ERROR RECOVERY -- exactly one outcome per input, with
       errors signalled separately from handled.
    3. A REFERENCE IMPLEMENTATION, but only as a suite companion, never as the
       definition. CommonMark's founding grievance is precisely this failure:
       "early implementers consulted Markdown.pl... but Markdown.pl was quite
       buggy."
    4. A VALIDATOR -- cheap, high-leverage, and meaningless until (2) exists.
    5. A PROSE SPEC -- necessary, least sufficient. Its distinctive job is
       stating what is DELIBERATELY LEFT OPEN. JSONTestSuite's third category
       `i_` ("parsers may freely accept or reject") measures underspecification
       directly; SQLite ships a whole `quirks.html`.
    6. A FORMAL GRAMMAR -- worth shipping for lexical structure, but the
       interesting parts are not context-free and a grammar cannot express
       them.
    7. A CORPUS of real files -- lowest for correctness, highest for
       DISCOVERING what the suite is missing.

SQLite is the calibration point for how much of this is enough: 155.8 KSLOC of
library against **590 times as much test code**. Its promise to support the
file format through 2050 is credible only because that ratio exists.
