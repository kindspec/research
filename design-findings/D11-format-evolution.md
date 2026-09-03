# D11 — Format evolution, longevity and compatibility over decades

Research date 2026-08-28. Sources are primary where quoted. Local experiments
live in `experiments/D11-evolution/` and every number below is reproducible by
running the scripts there.

This is a policy document. Sections 0–3 are the decision; sections 4–9 are the
evidence that produced it; section 10 is what it changes.

---

## 0. The headline

The design's stated invariant I7 — *"a parser must REJECT input it does not
understand, never skip it"* — is **correct in its motivation and wrong as
stated**. Taken literally it makes the format unable to evolve: a v1 reader
would reject a v2 file that differs only by an inert comment, which forks the
ecosystem on the first release. Measured below: strict-everything rejects 6 of
12 corpus files that had a correct answer available.

The resolution is not a compromise between strict and permissive. It is that
**strictness is the right default and the format must ship, in v1, a lexically
marked channel that is guaranteed inert** — a place where future versions can
put things that provably cannot change a computed value. This is PNG's
ancillary bit, RTF's `\*` destination, and OOXML's `mc:Ignorable`, and it is
the single mechanism that all three long-lived extensible formats have in
common.

The rule, in one line:

> **Reject by default. Ignore only what the format's own grammar has
> pre-declared inert, and preserve it byte-exact on write.**

---

## 1. The strict-parsing vs must-ignore resolution

### 1.1 The conflict, stated precisely

I7 came from a measured failure. A permissive `.tbl` parser that collected
lines beginning with `|` and ignored everything else met a git conflict and
summed **both sides**, producing 960 when the two candidate answers were 480
and 720 — a number neither author ever wrote. Leniency converted a loud
failure into a silent-wrong.

But must-ignore is how formats evolve without forking. If a v1 reader rejects
every file containing anything it has not seen, then the day v2 ships, every
v2 file is unreadable by every deployed v1 reader, and the ecosystem splits.
This is not hypothetical — it is exactly what XHTML's draconian error handling
did, and why the WHATWG was founded to replace it.

These are in direct conflict and both are load-bearing.

### 1.2 The tension is partly an illusion, and naming why matters

Before resolving it, dissolve the half of it that is a category error. RFC 9413
(*Maintaining Robust Protocols*, Thomson & Oku, IAB, 2021) says this directly,
and it is the single most useful paragraph found in this research
(https://www.rfc-editor.org/rfc/rfc9413.txt §2.2):

> "The ability to extend a protocol is sometimes mistaken for an application of
> the robustness principle. … **A well-designed extensibility mechanism
> establishes clear rules for the handling of elements like new messages or
> parameters. This depends on specifying the handling of malformed or illegal
> inputs so that implementations behave consistently in all cases that might
> affect interoperation. New messages or parameters thereby become entirely
> expected.** … **In contrast, relying on implementations to consistently
> handle unexpected input is not a good strategy for extensibility.**"

There are two distinct questions, routinely conflated:

    Q1  RECOGNITION     is this input a well-formed member of the language?
    Q2  INTERPRETATION  given a well-formed document, what does a
                        well-formed-but-unknown construct mean to THIS reader?

**Strict parsing is a Q1 discipline. Must-ignore is a Q2 policy. They do not
conflict.** The 960 failure was a Q1 failure misdiagnosed as a Q2 policy
question: the parser did not "tolerantly ignore an unknown extension", it
failed to *frame* `<<<<<<<` / `=======` / `>>>>>>>` as structure at all, and so
read a document that was not in the language as though it were. No must-ignore
rule in any format surveyed here would have licensed that. PNG's ancillary bit
does not permit ignoring an unknown chunk *length* field; Avro's "the writer's
value for that field is ignored" does not permit ignoring bytes it could not
delimit.

So: **framing is unconditionally must-understand, and this is compatible with
unlimited extensibility, because framing and meaning are different layers.**
The W3C TAG says the same thing from the other side — an ignorable extension
must still have been successfully delimited: *"'accepted' or 'ignored' doesn't
mean that unrecognized extensions can't be processed; only that they can't be
the grounds for failure to process."*
(https://www.w3.org/2001/tag/doc/versioning-compatibility-strategies §5.1.1)

What genuinely remains in tension is narrower and is the subject of §1.3–1.6:
of the constructs that *are* well-framed but unknown, which may be ignored?

RFC 9413 also supplies the empirical claim that strictness is a *stable* state
rather than merely a virtuous one (§4.2):

> "**it appears there are two stable points on the spectrum between being strict
> versus permissive** in the presence of protocol errors: If implementations
> predominantly enforce strict compliance with specifications, newer
> implementations will experience failures if they do not comply … **This
> ensures that most deployments are compliant over time.** Conversely, if
> non-compliance is tolerated by existing implementations, non-compliant
> implementations can be deployed successfully … **This ensures that most
> deployments are tolerant of the same non-compliant behavior.**"
>
> "**Tolerating unexpected input instead conceals problems, making it harder,
> if not impossible, to fix them later.**"

A format has to pick a basin. This one should pick strict, and the whole of
§1.4–1.8 is about making that survivable.

### 1.3 What the wrong framing is

The tempting line is **"reject unknown STRUCTURE, ignore unknown ANNOTATION."**
It is close but it is not the real variable, for two reasons.

First, it is not decidable by a reader. A v1 reader meeting `!filter qty > 15`
cannot tell whether that is structure or annotation; it has never heard of it.
Any rule that requires the reader to classify an unknown construct by what it
*means* is unimplementable, because not knowing what it means is the premise.

Second, "annotation" is not actually safe. Tested (`corpus.py`, case
*v2 semantic annotation*): if a future version gives an annotation semantics —
`%unit-scale 1000` meaning "quantities are in thousands" — then a v1 reader
that dutifully ignores it computes 240.00 where the truth is 240000.00, with
no error. Ignoring is only safe if the thing ignored is *guaranteed* inert, and
nothing about being syntactically an annotation guarantees that.

This is not a novel observation; I constructed the case and then found the W3C
TAG had written down the identical example in 2008
(https://www.w3.org/2001/tag/doc/versioning-compatibility-strategies), as the
*Preserve existing information Rule*:

> "An extension that affects an existing component in an incompatible way is an
> incompatible change because a consumer that is unaware of the extension will
> produce Information from the text that is incompatible with the intended
> Information. …
> **Preserve existing information Rule: An Extensible Language SHOULD require
> that any texts with extensions SHOULD be processible as a text without the
> extensions.**
> An example of an incompatible extension because of a violation of this rule
> is **a purchase order with a payment amount that is in US dollars that is
> extended by an element that specifies the payment amount is in Euros. An
> older consumer that ignores the extension element will incorrectly assume
> that the payment amount is still in US dollars when in fact it is in
> Euros.**"

USD/EUR is `%unit-scale` with different units. The independent rediscovery is
worth noting because it means the hazard is structural rather than an artifact
of my test corpus — and because the TAG's phrasing gives the enforceable form:
*a document with extensions must be processible as a document without them.*
That is a property the conformance suite can test directly, by stripping every
ignorable construct and asserting every derived value is unchanged (§7.4).

Avro states the same rule as a flat prohibition, which is the form to copy
(https://avro.apache.org/docs/1.12.0/specification/):

> "**Attributes not defined in this document are permitted as metadata, but
> must not affect the format of serialized data.**"

### 1.4 The actual variable: the derivation closure

The failure mode this substrate is organised against is **a wrong number with
no error**. So the question a reader must answer is not "is this structure or
annotation" but:

> Can this construct I do not understand affect a value I am about to report?

That is a question about the **derivation closure** of the requested value —
the same closure PASS5's `refs` function already computes for caching. An
unknown construct is safe to ignore exactly when it is outside that closure.
Prose has an empty closure, which is why markdown gets away with unlimited
tolerance and `.tbl` does not.

But a reader cannot compute the closure of a construct whose semantics it
lacks. So the closure membership has to be **declared in the syntax, by the
writer, at the moment the construct is written** — and declared in a way a
reader that has never heard of the construct can still read.

### 1.5 The mechanism: PNG's chunk bits, transplanted to line prefixes

PNG solved exactly this in 1996 and it is still solved. From the PNG
specification (https://www.w3.org/TR/png-3/), the chunk type's four letters
each carry a property bit in the case of the letter:

> **Ancillary bit:** "0 (uppercase) = critical, 1 (lowercase) = ancillary."
> **Private bit:** "0 (uppercase) = public, 1 (lowercase) = private."
> **Reserved bit:** "0 (uppercase) in this version of PNG. If the reserved bit
> is 1, the datastream does not conform to this version of PNG."
> **Safe-to-copy bit:** "0 (uppercase) = unsafe to copy, 1 (lowercase) = safe
> to copy."

And the decoder rules:

> "A decoder trying to extract the image, upon encountering an unknown chunk
> type in which the ancillary bit is 0, shall indicate to the user that the
> image contains information it cannot safely interpret."
>
> "A decoder encountering an unknown chunk type in which the ancillary bit is
> 1 can safely ignore the chunk and proceed to display the image."

Three properties make this the right model:

1. **It is lexical.** The rule is legible from the bytes of the name alone. No
   registry lookup, no version negotiation, no network. A decoder written in
   1996 correctly classifies a chunk type invented in 2026.
2. **The writer declares, not the reader.** The party that knows whether the
   construct is load-bearing is the one that emitted it. Same design as SOAP's
   `mustUnderstand` and JOSE's `crit`, and it is the only assignment of
   responsibility that can work.
3. **The safe-to-copy bit is a separate axis from the ancillary bit**, and this
   is the part usually missed. Ancillary answers *may I ignore this when
   reading*; safe-to-copy answers *may I carry this forward when I write a
   modified file*. Those are different questions and PNG gives them different
   bits. This design needs both, for the reason in §1.7.

### 1.6 The rule, concretely, for this substrate

Every line-initial construct in every type carries its class in its first
character. The classes ship in v1, before there is anything to extend:

    |  row / structural content    CRITICAL   unknown shape -> reject
    :=  binding into the namespace CRITICAL   unknown function -> reject
    !   pragma, affects evaluation CRITICAL   unknown pragma -> reject, always
    %   annotation, provably inert IGNORABLE  unknown -> ignore + preserve
    ?   alternation (see §1.7)     CRITICAL   the mechanism itself must be v1

The whole of the extensibility contract is: **`%` is the only ignorable
channel, and the format promises, permanently and testably, that no `%` line
may ever be an input to a derived value.** A future version that wants
`%unit-scale` to mean something must spell it `!unit-scale`, which old readers
reject loudly and correctly.

That promise is the load-bearing part, and it is enforceable rather than
aspirational: it is a property of the *evaluator's environment construction* —
the environment is built from cells and bindings and there is no syntactic path
by which a `%` line enters it — and it is a conformance test (§7.4).

### 1.7 Ignoring is not enough; you must also preserve

Protocol Buffers learned this the expensive way: proto3 originally **dropped**
unknown fields, and preservation was restored in 3.5 because proxies doing
read-modify-write were silently deleting data they had merely failed to
understand. Ignoring on read plus discarding on write is data loss with extra
steps.

Tested (`roundtrip.py`). A v1 reader meets a v2 file carrying `%owner alice`
and `%reviewed 2031-04-02`, and edits one cell:

    Writer A: re-emit from the parsed model
        annotations surviving: NONE  <-- DATA LOSS
        (and all 6 lines reformatted)

    Writer B: boundary splice -- locate the line, splice, re-emit the rest verbatim
        annotations surviving: ['%owner alice', '%reviewed 2031-04-02']
        lines changed vs input: 1

**This is free.** PASS5 already mandates boundary-only parsing ("the parser
finds block boundaries and never re-emits content") to satisfy I1 locality.
The same discipline is exactly protobuf's unknown-field preservation. One
design choice buys locality *and* forward compatibility, and the natural
implementation — reconstruct from the model — destroys both simultaneously.

### 1.8 The downgrade path must ship in v1 or it does not exist

Tested (`altcontent.py`). A v2 writer wants to emit a new construct with a
v1-readable fallback — OOXML's `mc:AlternateContent` idea:

    v1 WITHOUT an alternation construct    -> REJECT: line '? runningsum'
    v1 WITH   an alternation construct     -> OK, took the fallback branch

An alternation mechanism cannot be retrofitted, because a v1 reader meeting
`?` for the first time has no rule saying "this means: try the next branch" —
it is just another unknown critical construct, and it is rejected. ECMA-376
shipped Markup Compatibility and Extensibility as Part 3 *alongside* Part 1
for precisely this reason.

**Caveat specific to this design, and it is a real one.** An alternate-content
fallback is a materialised derived value in the file, which collides head-on
with R4: *"a derived value may not be committed if its dependency set spans
more than one mergeable entity."* So alternation is admissible here **only for
row-local values**, where R4 already permits committed derivation. For
cross-entity aggregates the correct v1 behaviour is to reject, not to fall back
— because the fallback would be exactly the stale committed aggregate that R4
showed producing a file asserting `99 x 12.00 = 120.00`.

Recommendation: **ship `?` in v1, restrict its use to row-local values, and
expect to use it rarely.** Its value is that it exists; a mechanism you have
and don't need is cheap, and one you need and don't have is a fork.

### 1.9 Measured: the four policies

`experiments/D11-evolution/drive.py`, 12 inputs a v1 reader plausibly meets
over decades — 6 forward-compatibility cases (a v2 file) and 5 corruption
cases (conflict markers, truncation, duplicate binding from a bad merge, stray
prose, dropped cell) plus a baseline. Each case declares ground truth: either
the value the format's semantics demand, or "no correct answer exists, the only
correct outcome is reject".

```
case                                                truth  permissive      strict-all      hybrid          demand-driven
----------------------------------------------------------------------------------------------------------------------
v1 baseline                                        240.00  CORRECT         CORRECT         CORRECT         CORRECT
v2 adds inert annotation (%owner)                  240.00  CORRECT         REFUSE          CORRECT         CORRECT
v2 adds unreferenced new binding (median)          240.00  CORRECT         REFUSE          REFUSE          CORRECT
v2 adds evaluation pragma (!filter)                120.00  SILENT-WRONG    REFUSE          REFUSE          REFUSE
v2 adds evaluation pragma (!round-half-even)       240.00  CORRECT         REFUSE          REFUSE          REFUSE
v2 unknown fn feeds the aggregate                  225.00  SILENT-WRONG    REFUSE          REFUSE          REFUSE
v2 semantic annotation (%unit-scale)            240000.00  SILENT-WRONG    REFUSE          SILENT-WRONG    SILENT-WRONG
git conflict markers                               reject  SILENT-WRONG    SAFE-REJECT     SAFE-REJECT     SAFE-REJECT
truncated mid-row                                  reject  SILENT-WRONG    SAFE-REJECT     SAFE-REJECT     SAFE-REJECT
duplicate binding from bad merge                   reject  SILENT-WRONG    SAFE-REJECT     SAFE-REJECT     SAFE-REJECT
stray prose line (paste accident)                  reject  SILENT-WRONG    SAFE-REJECT     SAFE-REJECT     SAFE-REJECT
row with a dropped cell                            reject  SILENT-WRONG    SAFE-REJECT     SAFE-REJECT     SAFE-REJECT

policy               CORRECT  SILENT-WRONG   SAFE-REJECT        REFUSE
permissive                 4             8             0             0
strict-all                 1             0             5             6
hybrid                     2             1             5             4
demand-driven              3             1             5             3
```

Readings:

- **Permissive is indefensible.** 8 silent-wrongs out of 12, including all five
  corruption cases. I7's motivation is fully vindicated.
- **Strict-everything has zero silent-wrongs but refuses 6 files that had a
  correct answer**, including one that differs from v1 only by a comment. That
  is the ecosystem-fork cost of I7-as-written, quantified. Note especially the
  second row: *this is the retrofit failure* — a format with no ignorable
  channel in v1 cannot add one later without every deployed reader rejecting
  every new file.
- **Hybrid** — reject unknown critical, ignore unknown annotation — recovers
  the inert-comment case at the cost of one silent-wrong, and that one is
  *the trap*: a future spec author who breaks the inertness promise. It is a
  governance failure, not a parser failure, and no parser change fixes it.
  This is the price of having an ignorable channel at all, and it is why the
  inertness promise must be a conformance test rather than a convention.
- **Demand-driven** (ignore unknown constructs outside the closure of the
  value actually requested) recovers one more case — an unreferenced binding
  using a function v1 lacks — with no additional risk. It is a strictly better
  reader strategy and costs one extra graph walk over machinery the design
  already has. Its extra rule: **a reader that did not fully understand a file
  may read it but may not write it**, which is the safe-to-copy bit again.

### 1.10 A bug in my own harness, which is the point

Revision 1 of the parser checked for unknown functions with
`re.match(r"^(\w+)\(", expr)`. Against `grand := sum(total) - median(qty)` this
matched `sum(` — a *known* function — and passed. Every policy, including
"strict", then fell through and returned the expression string instead of a
number. The buggy version is kept at `tbl_v0_buggy.py`.

**A spot check is not strictness.** Strictness is a property of a *total
recognizer*: every byte of the input must be consumed by a production of the
grammar, and anything else is an error. This is the LangSec position and it is
not a stylistic preference — a partial recognizer has exactly the leniency hole
that produced the 960 in the first place, just moved somewhere less obvious.
The conformance suite must therefore include *residue tests*: for each type,
inputs that differ from valid ones only in unparsed tail material.

### 1.11 The ignore path rusts shut unless you exercise it

The most counter-intuitive finding in this research, and the one most likely to
be skipped. An ignorable channel that nobody ever puts anything in stops
working, because implementations quietly acquire intolerance and nothing
reveals it until the day you need the channel.

TLS hit this hard enough to standardise a countermeasure. RFC 8701 (GREASE),
https://www.rfc-editor.org/rfc/rfc8701.txt:

> "**The responding side must ignore unknown values so that new capabilities may
> be introduced to the ecosystem while maintaining interoperability. However,
> bugs may cause an implementation to reject unknown values. It will
> interoperate with existing peers, so the mistake may spread through the
> ecosystem unnoticed. Later, when new values are defined, updated peers will
> discover that the metaphorical joint in the protocol has rusted shut and the
> new values cannot be deployed without interoperability failures.**
> To avoid this problem, this document reserves some currently unused values
> for TLS implementations to advertise at random. **Correctly implemented peers
> will ignore these values and interoperate. Peers that do not tolerate unknown
> values will fail to interoperate, revealing the mistake before it is
> widespread.**"

And RFC 9170 (IAB), the general statement:

> "**Only by using the extension capabilities of a protocol is the availability
> of that capability assured.** … **The longer an intolerant implementation is
> deployed, the more difficult it is to correct.** … The definition of
> mechanisms alone is insufficient; it is the assured implementation and active
> use of those mechanisms that determines their availability."

**Policy: the reference writer must emit a GREASE annotation.** Reserve a name
prefix (`%x-` followed by random hex) and have the canonical writer emit one on
some small fraction of files. Any tool that rejects it is discovered in weeks
rather than in the release where it matters. Cost: one line in a minority of
files. This is the cheapest insurance in the document, and it is the difference
between having an extensibility mechanism and believing you have one.

Note the interaction with the conformance suite: the suite should include a
`%x-` case in every type's corpus, so a conforming implementation is *required*
to tolerate it on day one.

### 1.12 Why not just specify the error recovery, like HTML5 did?

HTML5's genuine innovation was not permissiveness — it was making the recovery
*deterministic*, so that all parsers agree on what a malformed document means.
That is the right move for a format whose output is pixels, because a
deterministic wrong-looking page is still a page, and the alternative (XHTML's
yellow screen of death) was rejected by the market.

It is the wrong move here, and the reason is R4's asymmetry: **for prose,
recovery produces something visibly imperfect; for arithmetic, recovery
produces something invisibly false.** A deterministic recovery rule for a
conflicted `.tbl` would specify exactly which of 480 and 720 to take, and would
be exactly as wrong as picking at random — because the file records that nobody
knows.

So: **specify the recovery for `.md`, specify the rejection for `.tbl` and
`.canvas`.** The line falls where the derivation closure is non-empty, which is
the same line as everything else in §1.

---

## 2. The format-evolution policy — the rules, stated as rules

These are written to be pasted into the spec. Each is traceable to evidence in
§1 and §4–§9, or to an experiment in `experiments/D11-evolution/`.

### The parsing rules

    P1  TOTAL RECOGNITION
        Every byte of an artifact must be consumed by a production of the
        grammar. A parser that extracts constructs by pattern and discards the
        remainder is not a parser of this format; it is a parser of a weaker
        language, and the difference is where wrong numbers come from.
        Conformance: residue tests -- valid inputs with unparsed tail material
        appended must be REJECTED, not silently truncated.

    P2  FRAMING IS NEVER IGNORABLE
        No flag, sigil, version or option may cause a framing failure to be
        tolerated. Conflict markers, truncation, and unbalanced delimiters are
        always fatal. (This is the whole of I7's real content.)

    P3  ONE IGNORABLE CHANNEL, DECLARED IN V1
        `%` line-initial is the only ignorable construct class. Unknown `%`
        lines are ignored on read and preserved byte-exact on write. Every
        other unknown construct is fatal.

    P4  THE INERTNESS PROMISE
        No `%` construct may ever be an input to a derived value, in this or
        any future version. This is a permanent commitment of the format, not
        of an implementation. A future feature that needs to affect evaluation
        must be spelled `!`, which old readers reject.
        Conformance: strip every `%` line from every corpus file; assert every
        derived value is unchanged. (W3C TAG's "Preserve existing information
        Rule"; Avro's "must not affect the format of serialized data".)

    P5  POISON, DO NOT REJECT, WHERE THE SCOPE IS KNOWN
        An unknown construct inside the derivation closure of a value poisons
        THAT VALUE -- reported as an error naming the construct -- rather than
        failing the whole artifact, when the closure is computable. Values
        outside the closure are still reported. This is HTTP's status-class
        degradation: reduce resolution, never fake precision.
        A reader that poisoned any value MUST NOT write the artifact back.

    P6  PRESERVE WHAT YOU IGNORE
        Read-modify-write must be a boundary splice, never a re-emit from the
        model. Measured: re-emit destroyed both unknown annotations and changed
        6 lines; splice preserved both and changed 1.
        (protobuf 3.5's restored unknown-field preservation; PNG's
        safe-to-copy bit; the lens GetPut law.)

    P7  EXERCISE THE IGNORE PATH
        The reference writer emits a random `%x-<hex>` annotation on a small
        fraction of writes. Any implementation that rejects it is found early.
        (RFC 8701 GREASE.)

### The evolution rules

    E1  APPEND ONLY; NEVER REDEFINE
        Within a file type, a new version may ADD constructs. It may never
        change what existing bytes mean. A 2026 file must mean in 2056 exactly
        what it meant in 2026.
        (FITS's "once FITS, always FITS"; SQLite's on-disk compatibility
        promise; the reason no per-file version field is needed -- see §3.)

    E2  NEW CRITICAL CONSTRUCTS ARE ALLOWED AND ARE EXPECTED TO BREAK OLD READERS
        Adding a `!` pragma or a new binding form is legal. Old readers will
        reject files using it. That is correct: the alternative is that they
        compute a wrong number. Feature adoption is therefore a deployment
        decision with a visible cost, which is the honest shape of the
        tradeoff.

    E3  A BREAKING CHANGE GETS A NEW SUFFIX, NOT A VERSION BUMP
        If a change cannot be expressed as an addition, the type is renamed:
        `.tbl` -> `.tbl2`. Old and new coexist in one repository at no cost,
        because PASS5 already makes the suffix the type. Old files keep working
        forever; nothing is migrated by force.
        (Raku's rename over Perl 6; Rust editions' coexistence property; Rich
        Hickey's "don't break, make a new name".)

    E4  MIGRATION IS AUTOMATED AND CHECKED BY TWO ASSERTIONS
        A migration tool ships with each break. It is not trusted; it is
        checked (§7):
          (a) every derived value is unchanged, and
          (b) every input byte not matched by a declared rewrite rule appears
              verbatim in the output.
        Measured: each assertion catches a failure class the other misses.

    E5  NO CONSTRUCT MAY BE REMOVED
        Deprecated constructs stay in the grammar and stay readable. Writers
        may stop emitting them; readers may never stop accepting them.
        (protobuf's `reserved`; the reason OOXML "transitional" exists -- and
        §9 on why it must be a read-only concession, never a write target.)

    E6  THE EXTENSIBILITY MECHANISM SHIPS BEFORE IT IS NEEDED
        `%`, `!` and `?` all exist in v1 with no members. A channel cannot be
        retrofitted: measured, a v1 reader with no ignorable channel rejects
        a v2 file that differs only by a comment.

    E7  MIGRATION MUST BE REVERSIBLE
        Every suffix migration ships with a CHECKED INVERSE, and the suite
        asserts forward(back(x)) == x over the corpus. An irreversible
        migration is not adopted however good the new format is, because the
        first mover loses interoperability with everyone who has not moved.
        (MARC has outlived every argument against it for sixty years because
        BIBFRAME->MARC does not exist; the same asymmetry kept ODF from
        displacing .doc. The question is never "can you convert them" but
        "can you convert them BACK". See §9.2.)

### The specification rules

    S1  THE CONFORMANCE SUITE IS NORMATIVE; PROSE IS EXPLANATORY
    S2  THE REFERENCE IMPLEMENTATION IS NOT NORMATIVE, AND MUST NOT BE THE ONLY
        DEFINITION OF ANY BEHAVIOUR
    S3  NO CONSTRUCT MAY REQUIRE AN UNSPECIFIED PROGRAM TO EVALUATE
        (the org-mode `#+TBLFM:` failure -- §4.4)
    S4  THE SUITE MUST BE ABLE TO FAIL THE INCUMBENT
        A suite that every existing tool passes is measuring nothing. L6's
        markdown FAIL on scattered namespaces is the evidence that this one
        has teeth.

---

## 3. Versioning: the recommendation, with exact syntax

### 3.1 The recommendation

**No per-file version field. Ever.** The dialect of a file is determined by the
constructs present in it, and E1 (append-only, never redefine) is what makes
that sufficient. A repository-level `.format` file pins what *writers* emit; it
has no effect on what *readers* accept.

    myrepo/
      .format          <- one line, one file, whole repo
      docs/…           <- no version field in any artifact
      data/…

`.format` contents, exactly:

    edition 2026

Reader rules, exactly:

    R-a  A reader NEVER consults .format to decide how to interpret an
         artifact. Interpretation is a function of the artifact's bytes alone.
         `.format` may be absent, stale, or wrong; nothing breaks.

    R-b  On meeting a construct it does not know:
           `%`-class  -> ignore, preserve, report in diagnostics
           any other  -> poison the affected value (P5), or reject the
                         artifact if the closure is not computable
         In no case does the reader guess, substitute a default, or skip.

    R-c  There is no "unknown version" case, because there is no version to be
         unknown. The equivalent situation -- "written by something newer" --
         is handled per-construct by R-b, at the granularity of the feature
         actually used rather than the granularity of the whole file.

Writer rules, exactly:

    W-a  A writer emits only constructs permitted by `.format`'s edition. If
         `.format` is absent, it emits the oldest edition it supports.

    W-b  A writer that must downgrade -- emit for an older edition -- may do so
         only for ROW-LOCAL values, using the `?` alternation construct
         (§1.8). It must never materialise a cross-entity aggregate as a
         fallback, because R4 shows a committed aggregate merges to a false
         value with no marker.

    W-c  A writer that could not fully understand what it read must not write.

    W-d  Bumping the edition in `.format` is a one-line commit. It does not
         rewrite artifacts. Existing files are already valid in the new edition
         by E1.

### 3.2 Why not a per-file version field — measured

The obvious alternative is a version in every file (PDF's `%PDF-1.7`, ODF's
`office:version`, GIF's `GIF89a`). It costs more than it looks, and the cost
lands precisely on this design's locality invariant.

`experiments/D11-evolution/verrepo`, 500 markdown artifacts, bump v1→v2 by
inserting one line of frontmatter into each:

    500 files changed, 500 insertions(+)

One unreviewable commit, and an entry added to `git log` for every file in the
repository, permanently.

Two things I expected and **did not** find, reported because they weaken my own
argument:

- *Blame survives.* A pure insertion does not reattribute neighbouring lines;
  `git blame` still credits the original author for every content line.
- *Merges across the bump do not conflict.* A branch forked before the bump,
  editing three files, merged cleanly. 0 conflicted files. The
  version-bump-breaks-every-branch fear is not borne out for a field placed in
  its own region.

What **is** measured is the failure that matters here
(`experiments/D11-evolution/v2`): a version line placed at **line 1** conflicts
with any concurrent edit to line 1 — and a `.tbl`'s line 1 is its header row,
the single most-edited line in the file.

    $ git merge edit
    CONFLICT (content): Merge conflict in t1.tbl
    CONFLICT (content): Merge conflict in t2.tbl

    <<<<<<< HEAD
    #!tbl 2
    | id | item | qty |
    =======
    | id | item | quantity |
    >>>>>>> edit
      | -- | ---- | --: |

The two changes are semantically independent — adding a version, renaming a
column — and the conflict is entirely spurious. Worse, the conflicted file is
no longer a valid `.tbl`, violating I5. This is Pass 3's coupled-state defect
appearing one more time: a version field is state whose bytes must change when
unrelated content changes.

**So: no per-file version field.** If one were forced, it would go at the *end*
of the file, not the beginning — but the right answer is not to have one.

### 3.2a The best version field anyone designed, and why this design still can't have it

Honesty requires engaging the strongest form of the opposing case, which is
neither PDF's nor ODF's. It is **GIF's**, and it is genuinely good
(https://www.w3.org/Graphics/GIF/spec-gif89a.txt §17):

> "Version — Version number used to format the data stream. **Identifies the
> minimum set of capabilities necessary to a decoder to fully process the
> contents of the Data Stream.**"
>
> "**ENCODER: An encoder should use the earliest possible version number that
> defines all the blocks used in the Data Stream.** … DECODER: A decoder should
> attempt to process the data stream to the best of its ability; if it
> encounters a version number which it is not capable of processing fully, it
> should nevertheless attempt to process the data stream to the best of its
> ability."

This defeats the whole-repo-diff objection: the version is a **function of the
content**, so a spec bump touches only files that actually use the new feature.
A repo of 500 files where three adopt a 2031 construct gets a three-file diff,
not a 500-file one. EBML/RFC 8794 generalises it to two numbers —
`DocTypeVersion` ("the version of DocType interpreter used to create the
document") and `DocTypeReadVersion` (**"the minimum DocType version an EBML
Reader has to support to read this EBML Document"**) — and SQLite has the same
split at header offsets 18 and 19, where the read floor has moved **once in 21
years** (WAL, 2010).

So why not adopt it? Because **this design's own R4 forbids it**:

> "A derived value may not be committed if its dependency set spans more than
> one mergeable entity."

A GIF-style version line is precisely a committed derived value whose
dependency set is *every entity in the file*. R4 was derived from a measurement
— committing aggregates flipped L1's correct 660 into a clean merge with every
derived value false, and a conflict offering 580 and 560 when the truth was 660.
A version line has exactly that shape: two branches each adding a different new
construct both bump it, and git offers a two-way choice where the correct answer
is "both".

The benefit a read-floor buys — *a reader can know it cannot cope before doing
the work* — is recovered without the coupled state, because the per-construct
sigil of §1.6 delivers the same signal at **construct granularity instead of
file granularity**, which is strictly finer. A reader meeting `!filter` knows
immediately that it is out of its depth, and knows exactly which feature is
responsible, which a file-level integer never tells you.

**Summary of the trade, stated plainly:** GIF's rule is the best per-file
version design in the survey and would be the right answer for a format without
R4. A line-oriented mergeable format cannot have it, and does not need it.

### 3.3 What the long survivors actually do

The formats with the longest unbroken read compatibility are the ones with the
weakest version signalling, and this is not a coincidence.

| Format | Version field | Compatibility record |
|---|---|---|
| PNG (1996) | none — signature only | every PNG ever written still decodes |
| FITS (1979) | none — `SIMPLE = T` | 1979 files still read; "once FITS, always FITS" |
| SQLite (2000) | header field, never bumped in practice | on-disk format promised compatible to 2050 |
| HTML5 | version **removed** — `<!DOCTYPE html>` | living standard, no versions since 2014 |
| PDF | `%PDF-1.x` header | readers ignore it and duck-type anyway |
| ODF | `office:version` | four versions, fragmented anyway (§9) |

SQLite's promise is the clearest statement of the E1 discipline by anyone
shipping (https://www.sqlite.org/lts.html):

> "**The intent of the developers is to support SQLite through the year 2050.**
> … In addition to 'supporting' SQLite through the year 2050, the developers
> also promise to **keep the SQLite C-language API and on-disk format fully
> backwards compatible.** … Database files created today will be readable and
> writable by future versions of SQLite decades in the future. … **Our goal is
> to make the content you store in SQLite today as easily accessible to your
> grandchildren as it is to you.**"

Note what that promise actually is: not "we version carefully" but "**we will
never redefine existing bytes**". That is E1, and once you have E1 a version
field has nothing to do. Conversely, a format that *needs* a version field to
be read correctly has already admitted it redefines bytes — which is the thing
that kills formats.

Go's is the same promise for a language, and the exceptions list is worth
copying wholesale because it is the honest set
(https://go.dev/doc/go1compat):

> "**It is intended that programs written to the Go 1 specification will
> continue to compile and run correctly, unchanged, over the lifetime of that
> specification.**"

with reserved rights only for: security, previously-**unspecified** behaviour,
specification errors, and bugs. The second is the operative one for a format
spec: **anything you leave unspecified, you have not promised.** That is the
argument for the conformance suite being large (§9) — the suite is the extent
of the promise.

### 3.4 The edition mechanism, and its precedent

`.format`'s `edition` line is Go's `go.mod` `go` line and Rust's
`edition = "2024"`, applied to a repository rather than a module. The property
being borrowed is not versioning; it is **coexistence**: old and new artifacts
live in one repository, readable by one toolchain, with no migration event.
Here that property is free, because PASS5 already makes the file suffix the
type, so `.tbl` and `.tbl2` coexist the way two file types always have.

The constraint that makes this sound, and it is stronger than Rust's: **an
edition may change only what a writer emits and what a linter warns about. It
may never change the meaning of existing bytes.** Rust editions may change
keyword meanings; this format's may not. Give that up and R-a fails, and every
file needs to carry its edition again.

---

## 4. What the historical record says causes survival

### 4.1 The independent-implementation hypothesis is false in both directions

The rule normally cited is the IETF's. RFC 2026 §4.1.2
(https://www.rfc-editor.org/rfc/rfc2026.txt):

> "A specification from which **at least two independent and interoperable
> implementations from different code bases** have been developed, and for
> which sufficient successful operational experience has been obtained, may be
> elevated to the 'Draft Standard' level."
>
> "The requirement … applies to all of the options and features of the
> specification. **In cases in which one or more options or features have not
> been demonstrated in at least two interoperable implementations, the
> specification may advance to the Draft Standard level only if those options
> or features are removed.**"

Read the second paragraph carefully: **the penalty for a feature only one
codebase implements is that the feature is deleted from the spec.** The
implementations are a test instrument for the prose, not an end in themselves.
The W3C says the purpose out loud (Process §6.3.2,
https://www.w3.org/policies/process/20231103/):

> "Implementation experience is required **to show that a specification is
> sufficiently clear, complete, and relevant to market needs**, to ensure that
> independent interoperable implementations of each feature of the
> specification will be realized."

Tested against the record, the hypothesis fails both ways:

**Not sufficient.** XHTML 2.0 had a separable spec and plural conforming XML
parsers and died anyway — on implementer *refusal*, not implementer *absence*.
Its own epitaph (https://www.w3.org/TR/xhtml2/): *"The XHTML2 Working Group's
charter expired before it could complete work on this document."* RSS had
dozens of independent implementations and a published spec, and fragmented
because its author froze it and invited the fork in the same paragraph
(https://www.rssboard.org/rss-specification): *"the RSS spec is, for all
practical purposes, frozen at version 2.0.1 … Subsequent work should happen in
modules, using namespaces, and in **completely new syndication formats, with
new names**."* MathML has been a W3C Recommendation since 1998 with many
implementations and waited until Chrome 109 (January 2023) for the browser that
mattered.

**Not necessary.** TeX has one implementation, no separable spec, and 35 years
of bit-stable output. SQLite has one canonical engine and a compatibility
promise to 2050.

### 4.2 What the two counterexamples actually did: a conformance suite

TeX and SQLite both replaced the plural-implementation oracle with a precise
one. Knuth, *TUGboat* 11(4) 1990 p.489
(https://tug.org/TUGboat/tb11-4/tb30knut.pdf):

> "I strongly believe that an unchanging system has great value, even though it
> is axiomatic that any complex system can be improved. … Let us regard these
> systems as fixed points, which should give the same results 100 years from
> now that they produce today."
>
> "**nobody is allowed to call a system TeX or METAFONT unless that system
> conforms 100% to my own programs, as I have specified in the manuals for the
> TRIP and TRAP tests.**"
>
> "At the time of my death … all 'bugs' will be permanent 'features.'"
>
> "I welcome continued research that will lead to alternative systems that can
> typeset documents better than TeX is able to do. **But the authors of such
> systems must think of another name.**"

Two things to take from Knuth, in opposite directions.

*What the freeze bought:* documents compile identically decades later, and the
conformance definition is an executable test (TRIP/TRAP), not prose.

*What it cost:* the engine could not evolve, so every capability TeX lacked —
Unicode, OpenType, PDF output — arrived as a **fork of the engine**
(pdfTeX, XeTeX, LuaTeX), not as a version. Freezing the implementation did not
prevent change; it relocated change into forks and made the fork boundary the
compatibility boundary. That is the cost of "never change" and it is why E1
(append-only) is the right rule rather than E0 (no change).

And note the last quote: **Knuth's answer to an incompatible change is a new
name.** That is E3, from 1990.

SQLite's version of the same substitution
(https://www.sqlite.org/testing.html):

> "As of version 3.42.0 (2023-05-16), the SQLite library consists of
> approximately 155.8 KSLOC of C code. … **By comparison, the project has 590
> times as much test code and test scripts — 92053.1 KSLOC.**"
>
> "The SQLite core, including the unix VFS, has **100% branch test coverage**
> under TH3 in its default configuration as measured by gcov."
>
> "TH3 consists of about 76.9 MB or 1055.4 KSLOC of C code implementing 50362
> distinct test cases."

And the file-format document opens (https://www.sqlite.org/fileformat2.html):

> "This document **describes and defines** the on-disk database file format used
> by all releases of SQLite since version 3.0.0 (2004-06-18)."

~14,100 words, byte-exact down to `offset 0, 16 bytes, "SQLite format 3\000"`,
the varint encoding, the record serial-type codes, and the WAL checksum
*algorithm*. **"Defines", not "describes".**

The claim that SQLite has one implementation is false *for the format*. Third
parties have written independent readers from that document, including the US
DoD Cyber Crime Center's `sqlite-dissect` (*"opens the file as read only and
acts as a read only interpreter when parsing and carving"*), SQLJet (*"an
independent pure Java implementation"*), and Turso (*"compatible with SQLite at
the SQL dialect, file format, and C API levels"*). That is the hypothesis's real
prediction confirmed: **a document good enough that strangers succeed without
the code.**

The Library of Congress's assessment of SQLite (FDD 000461) scores exactly the
variables that matter and does *not* score implementation count: disclosure
(*"Openly documented … dedicated to the public domain"*), transparency,
self-documentation (*"incorporates technical and structural metadata needed to
interpret and manipulate the data itself"*), and **external dependencies:
"None"**.

### 4.3 The sharpened rule

> A format survives when its meaning is **decidable from a durable artifact
> that is not a running program** — a document, a conformance suite, or
> published literate source — such that a competent stranger can produce a
> conforming reader without access to the original authors or their runtime.
> Independent implementations are the standard *evidence* that this holds, not
> the condition itself; a conformance suite is a valid and sometimes stronger
> substitute. **Adoption by parties who control distribution is a separate and
> equally necessary condition** (§9).

### 4.4 Org-mode fails this test irreparably, and the reason is precise

Org's syntax document says what it is, in its first sentence
(https://orgmode.org/worg/dev/org-syntax.html):

> "This document describes and comments on Org syntax **as it is currently read
> by its parser (`org-element.el`)** and, therefore, by the export framework."

Compare SQLite's "describes **and defines**". Org's document indexes to a
codebase; SQLite's stands alone. Worse, org's syntax is parameterised by *live
Emacs Lisp variables* (§2.6): `org-link-parameters`,
`org-element-parsed-keywords`, `org-todo-keywords-1`,
`org-emphasis-regexp-components`. Its own footnote 5: *"todo keywords cannot be
hardcoded in a tokenizer, the tokenizer must be configurable at runtime."* A
spec whose terminals are runtime variables of one program is not separable in
principle, not merely in practice.

`#+TBLFM:` is where it becomes unrecoverable. The syntax document's *entire*
normative content for it:

> "An Org table can be followed by a number of `#+TBLFM: FORMULAS` lines, where
> FORMULAS represents a string consisting of any characters but a newline."

The semantics live in the manual: *"The table editor makes use of the Emacs Calc
package"* and *"It can also evaluate Emacs Lisp forms to derive fields from
other fields."* Measured from a fresh Emacs checkout:

    lisp/calc/          43 files    55,567 lines    Emacs Calc
    lisp/org/org-element.el          8,785 lines
    lisp/org/org-table.el            6,467 lines

**Specifying `#+TBLFM:` requires specifying a 55,567-line computer algebra
system — with non-standard operator precedence, where `a/b*c` means
`a/(b*c)` — plus an Emacs Lisp interpreter.** For scale, SQLite's entire
library is 155.8 KSLOC and is fully specified as a file format in 14,100 words.

The predicted consequence is observed. Across every non-Emacs implementation
surveyed — orgize, org-rs, org-parser, uniorg, go-org, org-ruby, organice,
orgzly, pandoc — **not one evaluates `#+TBLFM:`.** They uniformly parse it as an
opaque string and round-trip it. Pandoc's org reader source contains no
`TBLFM` code at all, and of 131 issues labelled `format:Org-mode`, zero mention
it. org-rs's README gives the diagnosis:

> "since Org does not have a formal specification they rely on observed Org's
> behavior in Emacs or author's intuition. **As a result they rarely get
> finished.**"

and org-parser's:

> "The spec is not machine readable. Hence, there can be drift between
> documentation and implementation. **In fact … we have encountered drift.** …
> Most implementations are only partial, and more importantly **each of them
> creates another island.**"

Org will not die — text with headline stars degrades gracefully. But **org's
30-year survival is Emacs's survival, not the format's.** Its own document says
an org file means "whatever the then-current `org-element.el` does". SQLite says
the inverse, in four words (https://www.sqlite.org/appfileformat.html):

> "**Data lives longer than code.**"

This is the direct justification for rules S1–S3, and specifically for S3: **no
construct of this format may require an unspecified program to evaluate.** It
is why wrapping IronCalc is acceptable *only* if the formula language accepted
by `.tbl` is specified independently of IronCalc and tested by the conformance
suite — otherwise `.tbl` reproduces `#+TBLFM:` exactly, with IronCalc in the
role of Calc.

---

## 5. Graceful degradation: which mechanism, and the ones that failed

### 5.1 The pattern in the record

Sorting the mechanisms by whether they survived contact with implementers gives
a sharp and unexpected split.

**Survived: a fallback *payload* carried inside the document.**

- OOXML `mc:AlternateContent` / `mc:Choice` / `mc:Fallback` (ECMA-376 Part 3
  §7.5–7.7): a `Choice` is selected if every namespace in its `Requires` is
  supported and no earlier `Choice` was selected; otherwise `Fallback`.
- RTF's dual representation: `\uN` Unicode characters are *"followed immediately
  by equivalent character(s) in ANSI representation. In this way, old readers
  will ignore the `\uN` keyword and pick up the ANSI representation properly."*
  Same trick for Word 97 numbering via `\listtext`.
- MIME `multipart/alternative` (RFC 2046 §5.1.4): *"the alternatives appear in
  an order of increasing faithfulness to the original content … Receiving user
  agents should pick and display the last format they are capable of
  displaying."*

**Survived: a must-ignore bit in the identifier itself.**

- PNG's case bits (§1.5).
- RTF's `\*`, which is PNG's ancillary bit in one character. From the RTF
  specification: *"**This control symbol identifies destinations whose related
  text should be ignored if the RTF reader does not recognize the
  destination.** … Destinations whose related text should be inserted into the
  document even if the RTF reader does not recognize the destination should not
  use `\*`."* and *"**All RTF readers must implement the `\*` control symbol so
  that they can read RTF files written by newer RTF writers.**"*
- ID3v2.4 frame flags, which split PNG's safe-to-copy bit into two axes:
  *"Tag alter preservation"* and *"File alter preservation"*, plus a read-only
  integrity bit.
- Atom RFC 4287 §6.3, which derives the same distinction from *position* rather
  than a declaration, at zero syntax cost: *"Atom Processors that encounter
  foreign markup in a location that is legal according to this specification
  MUST NOT stop processing or signal an error"*; as a child of `atom:entry` the
  markup MAY be bypassed, while inside a Text Construct *"software SHOULD ignore
  the markup and process any text content of foreign elements as though the
  surrounding markup were not present."*

**Failed: an abstract capability declaration a reader must resolve.**

This is the finding worth the most. SVG 2 killed `requiredFeatures` and said why
(https://www.w3.org/TR/SVG2/struct.html):

> "Previous versions of SVG included a third conditional processing attribute,
> **requiredFeatures**. This was intended to allow authors to provide fallback
> behavior for user agents that only implemented parts of the SVG specification.
> **Unfortunately, poor specification and implementation of this attribute made
> it unreliable as a test of feature support.**"

And OOXML's MCE decayed the same way in the largest independent implementation.
LibreOffice's DOCX *export* writes `mc:Ignorable` unconditionally
(`sw/source/filter/ww8/docxexport.cxx`):

    pAttr->add( FSNS( XML_mc, XML_Ignorable ), "w14 wp14 w15" );

but its *reader* (`oox/source/core/contexthandler2.cxx`) resolves
`mc:Choice Requires=` against a hardcoded prefix whitelist, with the reason in
the comment:

    // At this point we can't access namespaces as the correct xml filter
    // is long gone. For now let's decide depending on a list of supported
    // namespaces like we do in writerfilter
    static constexpr std::u16string_view aSupportedNS[] =
    { u"p14", u"p15", u"x12ac", u"v", u"cx1", u"cx2", u"cx4" };

and elsewhere:

    if( getNamespace( nElement ) == NMSP_mce ) // TODO for checking 'Ignorable'
    // TODO: Check & Get the namespaces in "Ignorable"

**So MCE's alternative-content half works in practice and its capability-
declaration half decayed into a hardcoded list.** Two independent mechanisms,
two decades apart, failed identically. The mechanism-level reason: a
declaration whose vocabulary is a *registry of feature strings* invites
implementers to answer "yes" rather than audit themselves, and nothing detects
the lie. A mechanism whose vocabulary is *the identity of the thing itself* —
PNG chunk names, RTF control words, EBML DocTypes — cannot be lied about,
because you cannot claim support for a name you have never seen.

**Direct consequence for this design:** the `?` alternation construct of §1.8
must key its branches on *the construct actually used*, never on a capability
name. Not `? requires=advanced-aggregates` but `? runningsum` — the name of the
function itself. This costs nothing and removes the failure mode.

### 5.2 DITA's class ancestry: the cheapest structural idea, and its exact limit

DITA is the only mechanism found where the **semantic fallback path travels
inside the instance**. From the OASIS DITA TC's specification source:

> "The specialization hierarchy of each DITA element is declared as the value of
> the `class` attribute. … **All specialization-aware processing can be defined
> in terms of `class` attribute values.**"

Syntax rules, verbatim: an initial `-` (structural module) or `+` (domain
module); *"A sequence of one or more tokens of the form `modulename/typename` …
**Tokens are ordered left to right from most general to most specialized**"*;
and *"**At least one trailing space character. The trailing space ensures that
string matches on the tokens can always include a leading and trailing space in
order to reliably match full tokens.**"* Giving:

    <!ATTLIST step  class  CDATA "- topic/li task/step ">

And it demonstrably works — the DITA Open Toolkit's stylesheets dispatch on the
ancestry, never on element names, with the leading/trailing spaces doing exactly
their specified job:

    match="*[contains(@class, ' topic/topic ')]"
    match="*[contains(@class, ' topic/section ')]"
    match="*[contains(@class, ' topic/body ')]"

A processor that has never heard of `<step>` matches `' topic/li '` and renders
a list item. No registry, no negotiation, no version.

**But it does not transplant wholesale, and the reason is the derivation
closure again.** Tested (`ancestry.py`):

    PROSE  v1 renders a v2 `warning` block via ancestry to `blockquote`:
        <blockquote>Do not deploy on a Friday.</blockquote>
        Is the result TRUE?  yes -- a warning IS a blockquote. Loses emphasis,
        states nothing false.

    COMPUTATION  `running :=[is=sum] runningsum(total)`, column [120, 120, 60]:
        v2 (understands runningsum):  ['120.00', '240.00', '300.00']
        v1 degrading via ancestry  :  300.00
        Is the result TRUE?  NO. v1 prints a single scalar where the document
        asserts a per-row series. Same type, wrong value, no error.

**Ancestry fallback is sound exactly when the ancestor's claim is *implied by*
the descendant's claim — i.e. when the specialization is a subtype.**
Presentation specializations satisfy this essentially always: a `warning` IS-A
blockquote, a `step` IS-A list item. Function specializations satisfy it
essentially never: a `runningsum` is NOT-A sum.

**Recommendation: adopt DITA ancestry for `.md` and `.canvas` node kinds; forbid
it for anything in a derivation closure.** Concretely:

    ::: warning {is=blockquote}      allowed  -- prose, presentational
    node gateway {is=service}        allowed  -- canvas, presentational
    running := [is=sum] runningsum(total)     FORBIDDEN

This is the same line as §1.4, arrived at from a completely different direction,
which is the main reason to believe it.

### 5.3 Markdown's tolerance, measured — and it is worse than reported

The brief's counter-evidence understates the problem. Against a **real** `git
merge` conflict (not a hand-typed approximation), rendered through four
installed engines:

    input (git's own output):
        # Doc

        <<<<<<< HEAD
        Our version of the line.
        =======
        Their version of the line.
        >>>>>>> feat

        Tail.

    pandoc 3.1.11.1 -f commonmark -t html:
        <h1>Doc</h1>
        <h1>&lt;&lt;&lt;&lt;&lt;&lt;&lt; HEAD Our version of the line.</h1>
        <p>Their version of the line.</p>
        <blockquote><blockquote><blockquote><blockquote>
        <blockquote><blockquote><blockquote>
        <p>feat</p>
        </blockquote>…</blockquote>
        <p>Tail.</p>

    exit codes:  pandoc 0   markdown-it-py 0   markdown_py 0   pandoc -f gfm 0

Three corrections to the folk version of this story:

1. `<<<<<<< HEAD` is **not** a heading. Seven `<` are literal text, escaped to
   `&lt;`.
2. `=======` on the line after text **is a setext H1 underline**, so the marker
   is **consumed entirely** — it does not appear in the output at all — and the
   *ours* side is silently promoted to a top-level heading. This is strictly
   worse than rendering the marker, because the corruption becomes invisible
   while changing the document's structure.
3. `>>>>>>> feat` is seven nested blockquotes, as reported.

And python-markdown diverges from the other three (no setext underline after a
multi-line paragraph), swallowing the whole conflict into one paragraph — so
**four conforming-ish readers produce three different documents from a corrupt
file, and all four exit 0.**

The general statement, and it is the reason `.md` alone cannot be the substrate:

> There is no lexical class of bytes a markdown document can contain that a
> conforming processor is obliged to reject. Therefore no corrupt state can be
> made loud, by anyone, ever, without leaving the format.

This is what I5 and P2 are buying, and it is why the `.md` type in this design
must be a *profile* with an added rejection rule (conflict markers are fatal),
not stock CommonMark.

Corroborating the same point from the other end, my own test of two readers on
a v2 document (`unknown.md`):

    markdown-it-py (CommonMark):
        <h2>Findings {#findings .important vocabulary=&quot;finance&quot;}</h2>
        <p>::: warning
        A v2 block construct.
        :::</p>

    pandoc (understands the attribute syntax):
        <h2 class="important" data-vocabulary="finance" id="findings">Findings</h2>
        <div class="warning"><p>A v2 block construct.</p></div>

Markdown has exactly **one** degradation mode — "show the source" — and no way
to say a construct is load-bearing. For prose that is tolerable and even
somewhat virtuous: the reference `{{ budget.tbl#grand }}` rendered as its own
literal text in *both* readers, which is accidentally I3-compliant. For anything
that feeds a number it is not tolerable, because "renders as its own source" is
loud to a human and silent to a program.

---

## 6. The migration problem: how to move without killing the ecosystem

### 6.1 The failure mode, named

Python 2→3 is the canonical disaster and the diagnosis is not "the changes were
too big". Python 3.0 shipped 2008-12-03; 2.7 was to end in 2015 and was extended
to 2020-01-01 — **eleven years of dual maintenance**. The specific defects:

1. **Old and new could not coexist in one process.** A program was 2 or 3, never
   both, so migration was atomic per program and therefore per dependency tree.
   One holdout dependency blocked everything downstream.
2. **The change was semantic, not syntactic** (`str`/`bytes`), so `2to3` could
   not finish the job, and the part it could not do was the part that produced
   silent wrong behaviour rather than syntax errors.
3. **No forcing function for a decade**, so the cost was deferred until it
   compounded.

Every one of those is avoidable, and the avoidance is the same trick three
times: **let old and new coexist**.

### 6.2 Rust editions — the best available model

Rust's stated constraint (https://doc.rust-lang.org/edition-guide/editions/):

> "When creating editions, there is **one most consequential rule: crates in one
> edition must seamlessly interoperate with those compiled with other
> editions.**"
>
> "Since editions are opt-in, existing crates won't use the changes unless they
> explicitly migrate into the new edition." / "Each crate chooses its edition
> within its `Cargo.toml` file." / "**each crate can decide when to migrate to a
> new edition independently. This decision is 'private' — it won't affect other
> crates in the ecosystem.**"
>
> "All Rust code — regardless of edition — will ultimately compile down to the
> same internal representation within the compiler."
>
> "this required compatibility implies some limits on the kinds of changes that
> can be featured in an edition. As a result, **changes found in new Rust
> editions tend to be 'skin deep'**."
>
> "**Cargo's automatic migrations aren't perfect**: there may still be corner
> cases where manual changes are required. **It aims to avoid changes to
> semantics that could affect the correctness or performance of the code.**"

Four properties, all worth copying: opt-in per unit; coexistence in one build;
one implementation not two; automated migration whose *stated* limit is that it
will not touch semantics.

Go does the same per module. From https://go.dev/blog/compat:

> "A program's GODEBUG settings are configured to match the Go version listed in
> the main package's `go.mod` file."
>
> "**If your program's `go.mod` file says `go 1.20` and you update to a Go 1.21
> toolchain, any GODEBUG-controlled behaviors changed in Go 1.21 will retain
> their old Go 1.20 behavior until you change the `go.mod` to say `go 1.21`.**"

with the underlying promise (https://go.dev/doc/go1compat):

> "**It is intended that programs written to the Go 1 specification will
> continue to compile and run correctly, unchanged, over the lifetime of that
> specification.**"

### 6.3 The counter-model: what happens when coexistence is only partial

**Node's ESM/CJS split** is the negative control. Two module systems that cannot
call each other synchronously produced a permanent fork: `--experimental-modules`
in 8.5.0 (2017), unflagged in 13.2.0, `require()` of synchronous ESM graphs only
in 22.0.0, on by default in 23.0.0 — and still able to throw
`ERR_REQUIRE_ASYNC_MODULE`. Seven-plus years. TypeScript 4.7's release notes
concede it: *"Interoperating between the two brings large challenges."*

**C++'s ABI** is the other negative control, and its lesson is the sharpest one
here. Titus Winters, P1863R0 (2019,
https://open-std.org/jtc1/sc22/wg21/docs/papers/2019/p1863r0.pdf):

> "**The aggregate cost of an ABI break across the entire C++ ecosystem should
> conservatively be estimated in engineer-millenia.**"

and, on why a *silent* dual representation is worse than a loud break:

> "Building one translation unit with the COW string and then passing a COW
> string to a function that accepts std::string built with the SSO
> implementation **may link (the mangled name has not changed, necessarily), but
> will fail spectacularly at run time... Run time bugs and memory errors are
> practically guaranteed.**"

That is silent-wrong at the ABI layer — two representations of one type meeting
inside one process, with no error. It is precisely what Rust's editions avoid by
carrying the edition in the compiler's own bookkeeping rather than hoping the two
sides agree, and precisely what E3's suffix rename avoids by making the two
representations *different file types* that cannot be confused.

Winters' closing line to WG21 is the one to keep:

> "**I call on WG21 to make a conscious and explicit choice here, with the clear
> awareness that status quo is an endorsement of indefinite ABI stability.**"

Restated for a format: **a format that never writes down what a version change
is allowed to do has, by default, promised never to change anything — and will
discover that promise only when it tries to break it.** That is why E1/E2/E5
must be written into the spec on day one, not decided later.

### 6.4 Raku, and why renaming is the honest move

Perl 6 was renamed Raku in 2019 rather than shipped as a Perl version, after a
decade of the name implying a compatibility that did not exist. Knuth reached the
same conclusion in 1990 (*"the authors of such systems must think of another
name"*) and Rich Hickey reached it again in 2016 (*Spec-ulation*):

> "But what about the major component? What does it mean? **It means you are
> screwed.** … It is an absolute catastrophe, because it does not tell you in
> what way. … What it really says is 'you might be screwed'."
>
> "**Breaking changes are broken. It is just a terrible idea. Don't do it.**
> … **You might as well just change the name.** Going to 2.0 is not helping
> anybody. … **this method of renaming turns breakage into accretion**… this
> coexistence means that people can just freely proceed."
>
> "So that helps us in the small, as long as we do not do something like **try to
> version specs**. … If you say you cannot do X, it means you can never do X.
> And if you are going to try to make it OK to do X later, then you need a new
> name."

The three long-lived formats that faced an incompatible change all did exactly
this rather than bump a number: OOXML's strict vocabulary took **new namespace
URIs** (`purl.oclc.org/ooxml/…`) rather than a version attribute; PNG adds a new
**chunk type**, never a new version; TeX's successors took **new engine names**.

### 6.5 The recommendation

    A change that fits E1 (pure addition) needs no migration at all.
    A change that does not gets a NEW SUFFIX, and the old suffix keeps working
    forever. Both live in one repository. Nothing is migrated by force.
    A migration tool ships with the break, and is CHECKED, not trusted.

The coexistence property that Rust had to engineer into a compiler is **free
here**, because PASS5 already makes the file suffix the type. `.tbl` and `.tbl2`
coexist in one repository the way `.md` and `.csv` always have; no build system
needs to know.

**Migration is verified by two assertions, and neither alone is sufficient.**
Measured (`experiments/D11-evolution/migrate.py`), running three candidate
migrations of the same file:

    migration          value   check1 values   check2 bytes  verdict
    correct           240.00            True           True  ACCEPT
    wrong-column          30           False           True  REJECT
    lossy             240.00            True          False  REJECT

    baseline grand = 240.00

- *check 1* — every derived value is unchanged — catches a rewrite that changed
  the arithmetic.
- *check 2* — every input byte not matched by a declared rewrite rule appears
  verbatim in the output — catches a rewrite that preserved every value while
  **deleting the annotations**. Value-equivalence alone reports `True` for a
  migration that destroyed data, which is exactly the read-modify-write hazard
  of §1.7 wearing a different hat.

This is also the honest form of Rust's caveat: `cargo fix` *"aims to avoid
changes to semantics"* is an aim. Check 1 makes it a test.

---

## 7. What must be specified, what may be left open, and what the spec must ship

### 7.1 The general lesson: specify the failures, not just the successes

The single largest specification win in the history of document formats was
HTML5's decision to specify the **error recovery algorithm** exhaustively. Before
it, every browser recovered differently from malformed markup and the recovery
behaviour was reverse-engineered folklore; after it, a conforming parser is
writable from the spec alone, and several were — html5ever, parse5, Gumbo, jsoup,
lol-html — none by the spec's authors.

The reason this matters here is that it inverts the usual framing. HTML5 did not
win by being permissive; XHTML lost by being strict *without* specifying what
strictness meant operationally, and HTML5 won by making the **handling of
malformed input** a normative algorithm. RFC 9413 makes the same point for
protocols: extensibility *"depends on specifying the handling of malformed or
illegal inputs so that implementations behave consistently."*

Go's compatibility promise reserves the right to break *"unspecified behavior"*
and *"specification errors"*. Read as a rule for spec authors: **anything you
leave unspecified, you have not promised**, and the size of your promise is the
size of your spec. HTTP is the cautionary case — its underspecified interaction
between `Content-Length` and `Transfer-Encoding` did not stay a curiosity; it
became request smuggling, an entire vulnerability class, and RFC 9112 had to
close it retroactively.

**So the rule is not "specify everything" but "specify every input, including the
ones you reject, and specify what rejection means."** For this design that is:
the grammar (total, per P1), the classification of every unknown construct (P3),
the poisoning semantics (P5), the write rules (P6, W-c), and the encoding profile
(T1–T3). Everything else — rendering, layout, performance, UI, which engine
computes the arithmetic — is implementation latitude.

### 7.2 What may be left open, concretely

    SPECIFIED (normative, conformance-tested)
      the byte grammar of every type, totally
      the classification of unknown constructs and what each implies
      identifier normalization, code-point profile, encoding, line endings
      the derivation semantics of every function in the formula language
      what a reader does with input it cannot fully understand
      what a writer may not do (W-b, W-c)
      the merge outcome DECLARED for each concurrent-edit scenario

    OPEN (implementation latitude)
      rendering, typography, layout, colour, pagination
      which layout/formula/typesetting engine is wrapped
      performance, caching strategy, index structures
      editor affordances, conflict presentation, UI vocabulary
      structural merge algorithms (D3 already put these outside correctness)

The line is: **anything that can change a value or a byte is specified; anything
that can only change an appearance is open.** Note this is the derivation-closure
rule for the third time, now applied to the spec rather than the parser.

The one thing that must *never* be left open is S3: no construct may require an
unspecified program to evaluate. Org's `#+TBLFM:` is the counterexample and it
cost the format every independent implementation (§4.4). Wrapping IronCalc is
fine; *defining `.tbl`'s arithmetic as "whatever IronCalc does"* is the org
mistake with a different dependency.

### 7.3 What the spec must ship with, ranked by evidence

**1. An executable conformance suite. This is the primary artifact.**

The evidence is convergent from three independent directions:

- **TeX**: *"nobody is allowed to call a system TeX … unless that system conforms
  100% to my own programs, as I have specified in the manuals for the TRIP and
  TRAP tests."* Conformance is defined by a test, not by prose.
- **SQLite**: 590× as much test code as library code, 100% branch coverage under
  TH3, 50,362 distinct test cases — and a documented file format that third
  parties (including a DoD forensic lab) have re-implemented from.
- **RFC 2026**: the penalty for a feature that two implementations cannot
  interoperate on is that **the feature is removed**. The implementations are an
  instrument for measuring the prose.
- **This project**: L6 caught two errors in its own test cases within minutes,
  and §7.4 below caught two more in the reference parser — written by the person
  who wrote the strictness rule.

**1a. What the CommonMark model actually delivered, and where it fell short.**
This matters because L6 proposes the same model. CommonMark's spec *is* its test
suite — the examples are delimited in the source and extracted mechanically by
`spec_tests.py`. Current release **0.31.2, dated 2024-01-28**: 204,857 bytes,
**652 examples**, 21 constructs.

*What it delivered:* the thing it was built for. CommonMark's own homepage states
the problem it solved — *"John Gruber's canonical description of Markdown's
syntax does not specify the syntax unambiguously"*, *"Because there is no
unambiguous spec, implementations have diverged considerably over the last 10
years"*, *"There's no standard test suite for Markdown."* After the suite, a
genuinely plural implementation ecosystem exists (cmark, commonmark.js,
markdown-it, comrak, pulldown-cmark, goldmark, and others), which is the RFC 2026
criterion met by an executable artifact rather than by committee.

*Where it fell short — four failures, all instructive:*

1. **Still 0.x after 12 years** (0.5 in 2014 → 0.31.2 in 2024). The reason,
   from the CommonMark forum in 2014, is structural rather than procedural:
   *"CommonMark has a single input … and a single output … Every change to the
   spec will result in a output that is different from the previous version,
   given the input stays the same. In my understanding that makes every change a
   breaking change."* — which is why semver cannot be applied to a format, and
   why this document uses E1/E3 instead of version numbers. jgm in 2019:
   *"1.0 implies stability. We're not there yet."*; in Feb 2025: *"I'm open to
   calling it 1.0, though. **I'm not sure it matters greatly for anything.**"*
2. **It cannot express a table** — nor a footnote, comment, definition list, or
   strikethrough (verified by section count). So every real deployment runs
   CommonMark *plus* extensions, and those extensions have no single normative
   spec. That is the CSV failure mode reappearing one level up, and it is the
   direct argument for `.tbl` being its own specified type rather than a
   markdown extension.
3. **The suite tests markdown→HTML only, so it under-constrains the AST.** Two
   conforming implementations can produce entirely different internal
   structures. For CommonMark that is acceptable; for a substrate whose
   `resolve` and `refs` functions operate on the entity map, it is not.
   **L6's suite must assert on the entity map and the computed value, not only
   on a rendering** — which it already does, and which is its genuine advance
   over the model it copies.
4. **The raw-HTML passthrough is an unbounded hole**: `Raw HTML` and `HTML
   blocks` make the whole of HTML reachable from inside a conforming document,
   so "21 constructs" understates the grammar a correct reader must handle.
   This design's types must have **no escape hatch of this kind** — every
   construct is in the grammar or it is rejected (P1).

**2. A prose spec that stands alone.** Necessary but not sufficient, and its
sufficiency is testable by exactly one question: *does it define, or does it
describe?* SQLite's opens *"describes and defines"*; org's opens *"describes …
as it is currently read by its parser (`org-element.el`)"*. The first produced
independent readers; the second produced nine partial ones, none of which
evaluates a formula.

**3. A corpus of real files, with declared expected outcomes.** L6's innovation
over CommonMark's model is that its cases declare a *merge* outcome and a
*computed value*, not just a rendering — so "clean merge, wrong number" is a
machine-checkable verdict. That category has no analogue in CommonMark's suite
and it is the category this substrate exists to eliminate.

**4. A validator, shipped as a program.** Cheap, and it is what makes P1 real for
users rather than aspirational for implementers. It is the GREASE emitter's
counterpart: one tool that says yes or no.

**5. A reference implementation — explicitly NOT normative (S2).** Useful,
dangerous, and the danger is documented: org's reference implementation *became*
the spec. Mitigation: the reference implementation must pass the same suite as
everyone else, and the suite must be authored against the prose, not extracted
from the implementation's behaviour.

**6. A formal grammar.** Ranked last, deliberately. It is valuable for P1 (a
total recognizer is easiest to build from a grammar) but it cannot express the
things that actually kill this format — merge outcomes, derivation semantics,
poisoning, normalization. A grammar proves well-formedness; it says nothing about
whether the number is right.

### 7.4 The evolution tests the suite must add to L6

L6 already covers round-trip, idempotence, stock-git merge outcomes and loud
failure. This document adds seven categories, implemented and run in
`experiments/D11-evolution/suite.py`:

```
residue rejected: '\x00'                 PASS
residue rejected: 'garbage'              PASS
residue rejected: '| unclosed'           PASS
residue rejected: '\t\t'                 PASS
residue rejected: '%'                    PASS
inertness: stripping % changes no value  PASS
GREASE %x- tolerated                     PASS
unknown ! pragma is fatal                PASS
preservation on write                    PASS
non-NFC identifier rejected              PASS
Cf (ZWSP) in identifier rejected         PASS
NFC-equal names are the same name        PASS
conflict marker at line 0 is fatal       PASS
conflict marker at line 2 is fatal       PASS
conflict marker at line 5 is fatal       PASS

15/15 pass
```

**Two of those were FAIL on the first run**, against a parser written by the
author of P1, minutes after writing P1:

    residue rejected: '\t\t'   FAIL   [value]
    residue rejected: '%'      FAIL   [value]

A whitespace-only line was silently skipped by `if not line.strip(): continue`,
and a bare `%` parsed as an annotation with an empty key. Both are exactly the
class of leniency that produced the 960 — a production not in the grammar,
accepted because it looked harmless. The fixes were three lines each; finding
them without the suite would have taken years and a wrong number.

(JOSE forbids an empty `crit` array for the same reason: no ambiguity between
"nothing is critical" and "this field is unset".)

This is now the fourth time in this project that writing an invariant down and
then testing it caught something discipline alone did not — after L2's alignment
row, L3's hash identity, and L6's two test-case bugs. **That rate is the argument
for S1.**

---

## 8. Binary vs text for longevity, honestly

The claim under test is "plain text is more durable". **It is roughly 30% true
and 70% folklore**, and getting the 30% right matters because it is not the part
usually cited.

### 8.1 The preservation community's criterion is not text vs binary

The Library of Congress's *Sustainability Factors*
(https://www.loc.gov/preservation/digital/formats/sustain/sustain.shtml) lists
seven, and "transparency" is one of them, defined carefully:

> **Disclosure** — "the degree to which complete specifications and tools for
> validating technical integrity exist and are accessible … **what is most
> significant for this sustainability factor is not approval by a recognized
> standards body, but the existence of complete documentation**, preferably
> subject to external expert evaluation."
>
> **Transparency** — "**the degree to which the digital representation is open
> to direct analysis with basic tools, including human readability using a
> text-only editor.**"
>
> **Self-documentation** — "Digital objects that are self-documenting are likely
> to be easier to sustain over the long term…"
>
> **External dependencies** — "the degree to which a particular format depends
> on particular hardware, operating system, or software for rendering or use…"

Note "disclosure" does not mention encoding at all, and the LoC explicitly
accepts compression despite it inhibiting transparency: *"compression inhibits
transparency. However, for practical reasons … **Archival repositories must
certainly accept content compressed using publicly disclosed and widely adopted
algorithms.**"*

The decisive evidence is what they actually recommend. The LoC's *Preferred*
formats for datasets (https://www.loc.gov/preservation/resources/rfs/data.html)
list, in the same tier: line-oriented text (TSV, CSV, fixed-width) **and**
`.sqlite`. And the per-format assessments run against the folklore:

| | SQLite (fdd000461) | CSV (fdd000323) |
|---|---|---|
| Disclosure | "Openly documented … dedicated to the public domain" | "**A simple *de facto* format, for which no single, official specification exists**" |
| Transparency | partial — "the use of the b-tree structure and binary formats … obscures much of the data" | "very transparent, being both human-readable and easily machine-processable" |
| Self-documentation | "**incorporates technical and structural metadata needed to interpret and manipulate the data itself**" | "**Poor.** … For preservation, an associated codebook is desirable" |
| External dependencies | "**None**" | — |

**The binary format scores better on the two factors that predict survival and
worse on the one that predicts convenience.** Both are recommended. Text wins
transparency; binary wins self-description.

FITS states the mechanism outright, and it is not "text" (FITS Standard 4.0 §1):

> "**One important feature of the FITS format is that its structure, down to the
> bit level, is completely specified in documents … Given these documents …
> future researchers should be able to decode the stream of bytes in any FITS
> format data file. In contrast, many other current data formats are only
> implicitly defined by the software that reads and writes the files. If that
> software is not continually maintained so that it can be run on future
> computer systems, then the information encoded in those data files could be
> lost.**"

That last sentence is a description of org-mode (§4.4), written in a standards
document about a binary format. Its epigraph is the National Research Council's:
*"An archival format must be utterly portable and self-describing, on the
assumption that, apart from the transcription device, neither the software nor
the hardware that wrote the data will be available when the data are read."*

### 8.2 Where text genuinely wins: localized corruption

This is the real 30%, and it is measured. A 145,584-byte prose markdown file,
one byte flipped at the 50% mark, versus the same flip in its gzip:

    PLAIN TEXT, 1 byte flipped at offset 72792:
        file still opens: True
        undecodable chars: 1 of 145584
        context: b'...a checksum canonical\x96zation by durability...'
        bytes after damage still intact: 72791 (50.00% of file)

    GZIP, 1 byte flipped at offset 14032 of 28064:
        gzip: invalid compressed data--crc error       exit=1
        first divergence at byte 70657 of 145584 (48.5%)
        similarity of next 4000 chars after damage: 0.015

One bit-flip in text damages exactly one character and leaves the remaining 50%
byte-perfect, with the damage visible to a human. The same flip in deflate makes
everything past 48.5% into text that is **1.5% similar** to the original —
structurally plausible word salad, produced with only a CRC error to warn you.

This compounds badly for ZIP-container formats, which is what OOXML and ODF are:

    zip container, one byte flipped in the deflate stream:
        d.txt   bad CRC c0aef4e5  (should be 8651e1fe)
        unzip -t exit=2

If bytes will sit on unverified media for decades, this is worth real money. It
is also the *only* argument in this section that survives scrutiny intact.

### 8.3 Where "text is more durable" is false

**Interpretability is a separate property from openability.** RFC 4180 is the
canonical demonstration, and it indicts itself:

> "Category: Informational … **It does not specify an Internet standard of any
> kind.**"
> "Surprisingly, while this format is very common, **it has never been formally
> documented.**"
> "**there is no formal specification in existence, which allows for a wide
> variety of interpretations of CSV files.** This section documents the format
> that **seems to be followed by most implementations**"

Measured consequences: one logical record in three real dialects through one
default parser produced a 3-column header yielding 4 fields with no error; the
European `;`/`1.234,56` dialect was destroyed; and `1.234,56` vs `1.234` `56`
are the *same bytes* meaning different numbers depending on locale.

**Encoding is metadata that lives outside a text file.** chardet 5.2.0 on the
same visible string written six ways, with no declaration anywhere:

    written as      chardet guess       conf  correct?
    utf-8           utf-8               0.99  YES
    latin-1         ISO-8859-9          0.48  NO
    cp1252          ISO-8859-9          0.48  NO
    iso-8859-15     ISO-8859-9          0.48  NO
    cp437           Windows-1254        0.51  NO
    mac_roman       MacRoman            0.59  NO

**5 of 6 wrong**, and the three 8-bit Western encodings are indistinguishable in
principle. SQLite, by contrast, records its text encoding in its 100-byte
header. **The binary format is self-describing about its text encoding; the text
format is not.**

**Unicode normalization is the underrated hazard, and it is worse than
expected.** Measured:

    NFC bytes: b'caf\xc3\xa9'      6 bytes   blob 572eb43f…
    NFD bytes: b'cafe\xcc\x81'     7 bytes   blob c3a132d4…
    visually:  café / café

    git diff (zero visible change):
        -café
        +café
        1 file changed, 1 insertion(+), 1 deletion(-)

    grep for NFC-typed é in the NFD file: 0 matches (exit=1)
    grep for NFD-typed é in the NFC file: 0 matches (exit=1)

The merge hazard, which is the one that matters here:

    Auto-merging notes.md
    CONFLICT (content): Merge conflict in notes.md

    <<<<<<< HEAD
    author: Renée Café
    =======
    author: Renée Café
    >>>>>>> branch-b

**Both sides of the conflict marker are pixel-identical.** Resolving it requires
`od`. And git's only mitigation covers filenames on macOS only —
`core.precomposeUnicode`: *"This option is only used by Mac OS implementation of
Git. … Git reverts the unicode decomposition of filenames done by Mac OS."*
There is no `.gitattributes` normalization filter for content.

I ran a further test of the case that actually happens in a mixed-platform team
(`experiments/D11-evolution/nfc2`): an editor on one machine re-normalises the
whole file to NFD on save, while the author edits one word.

    branch mac: one word edited, editor re-normalised the file to NFD
        git diff --numstat:   4   4   doc.md

**A one-word edit produced a four-line diff — a direct I1 violation caused
entirely by the encoding layer, with no visible change on three of those lines.**
Then, merging that against an unrelated edit to a *different paragraph*:

    $ git merge mac
    CONFLICT (content): Merge conflict in doc.md
    conflicted files: 1

    @@@ -1,7 -1,7 +1,11 @@@
    - # Café Résumé {#cafe}
    + # Café Résumé {#cafe}

    - Première section über naïve façade.
    + Première section über naïve façade.
    ...
    ++<<<<<<< HEAD
     +Troisième section: cooperate fully.
    ++=======
    + Troisième section: coöperate.
    ++>>>>>>> mac

Two edits to different paragraphs, which this design's whole merge story says
must merge cleanly, **conflicted** — and the diff shows three pairs of lines
that are byte-different and pixel-identical. This is the L1/L4 coupled-state
defect arriving through the character encoding rather than through the format,
and neither nominal addressing nor semantic line breaks defends against it.

**And it breaks this design's nominal addressing.** A typical `[^\w\- ]`
slugifier drops the combining acute (category `Mn`, not `\w`):

    NFC heading 'Café Résumé' -> slug 'café-résumé'   (14 bytes)
    NFD heading 'Café Résumé' -> slug 'cafe-resume'   (11 bytes)
    slugs render identically? False   <- SILENT DUPLICATE ANCHOR
    lookup of NFD-typed link in NFC-built index: *** BROKEN LINK ***

Two entries in a namespace that I2 requires to be unique, rendering identically.
This is a **direct attack on I2 and I3** and it is invisible in review.

**Policy consequence, and it is mandatory:** the format specifies **NFC as the
only conforming normalization for all identifiers, and canonicalisation to NFC
is part of `canon`**, tested by the idempotence property `canon(canon(x)) ==
canon(x)`. Two names that are NFC-equal are the same name; a file containing a
non-NFC identifier is rejected under P1. Content outside identifiers may be any
normalization (it is data), but identifiers may not.

**Line endings.** Git's own documentation on `core.safecrlf`:

> "**CRLF conversion bears a slight chance of corrupting data.** … **A file that
> contains a mixture of LF and CRLF before the commit cannot be recreated by
> Git.** … **Unfortunately, the desired effect of cleaning up text files with
> mixed line endings and the undesired effect of corrupting binary files cannot
> be distinguished. In both cases CRLFs are removed in an irreversible way.**"

Measured: a pure line-ending change produced `1 file changed, 4 insertions(+),
4 deletions(-)` for zero semantic change — an I1 violation caused entirely by
the encoding layer.

**BOM.** A UTF-8 BOM destroys a shebang while exiting 0:

    ./bom.sh: line 1: ﻿#!/bin/sh: No such file or directory
    hello
    exit=0

and poisons the first CSV column name (`['﻿name', 'city']`, so
`row["name"]` is missing), while Excel *requires* one to detect UTF-8.

**Adversarial safety — the sharpest point against text.** Trojan Source
(Boucher & Anderson, USENIX Security 2023, CVE-2021-42574/42694,
https://trojansource.codes/) is an attack *on human readability itself*:
*"Compilers and interpreters adhere to the logical ordering of source code, not
the visual order."* Reproduced locally, along with NBSP/ZWSP/ZWJ/soft-hyphen and
Cyrillic homoglyph confusables — all byte-distinct, all rendering identically,
and all invisible in `git diff`:

    -password = "hunter2"
    +pass​word = "hunter2"
    (same diff with cat -A:)
    +passM-bM-^@M-^Kword = "hunter2"$

**A text format's fallback reader is also its attack surface.** For a substrate
whose whole error-reduction argument is *code inspection* (R7), an attack that
defeats inspection is a direct hit. Policy: identifiers are restricted to a
declared code-point profile, and `Cf` characters are rejected in identifiers
under P1.

### 8.4 The prosecution's two data points, assessed

**The size claim collapses inside git.** Measured on a 145,584-byte markdown
file — exactly the prosecution's figure:

| Representation | Bytes |
|---|---|
| Markdown in the working tree | 145,584 |
| The prosecution's `.docx` | 28,457 |
| `gzip -9` of the markdown | 28,071 |
| **git loose object, `core.loosecompression 9`** | **28,069** |
| **git packfile (whole repo)** | **28,560** |

**A dead heat, within 0.4%.** The 5.1× figure is a compressed-vs-uncompressed
comparison, not a property of markdown; `.docx` is a ZIP of XML and git stores
every blob zlib-deflated. The 145 KB is disk in the working tree, which you
already have, and it is what buys the diffs. And across *history* — the case the
prosecution would press next — packfile delta compression cuts hard the other
way, because a one-word edit rewrites an entire deflate stream in a `.docx` and
one line in a markdown file. **On size, in a version-controlled substrate, the
argument runs the other way.**

**The complexity claim is real, reproducible, and overstated by ~5×.** The 3,180
figure is exactly `grep -c '<xsd:element name='` across the 21 OOXML Strict
schemas (verified: 3,180 declarations, 1,868 distinct names, 1,369 complexTypes,
2,852 attributes; ECMA-376 Part 1 is **5,039 pages**). CommonMark 0.31.2 is
204,857 bytes, 652 examples, and **21 constructs** (verified by section count).

But three things make 3,180-vs-21 the wrong comparison:

1. **Scope.** 3,180 covers word processing *plus* spreadsheets (618) *plus*
   presentations (313) *plus* DrawingML (1,220) *plus* equations (177). The
   like-for-like number against a document format is `wml.xsd`: **704**.
2. **Capability.** CommonMark's 21 constructs verifiably include no table, no
   footnote, no comment, no definition list, no strikethrough. Every real
   substrate therefore runs CommonMark **plus extensions with no single
   normative spec** — which is the CSV failure mode one level up.
3. **Escape hatch.** `Raw HTML` and `HTML blocks` make the whole of HTML
   reachable from inside a conforming document, so 21 understates the grammar a
   correct reader must handle.

Honest version: **~21 fully-specified constructs that cannot express a table,
plus an unspecified extension surface and an HTML escape hatch, versus 704
fully-specified WordprocessingML elements.** Still a large and real simplicity
win — a factor of ~30 on a partly-specified format, not ~150 on a fully-
specified one. And it is an argument for *this project's designed formats*, not
for markdown: `.tbl`'s grammar is small **and** closed **and** expresses a table.

### 8.5 Verdict, and what it changes

> Durability comes from **specification completeness and self-description**, not
> from the encoding being text. Text buys a cheap universal fallback reader and
> human-inspectable corruption — genuinely valuable, and the reason to keep it —
> but it is not durability, and a well-specified binary format
> (SQLite, FITS, PNG, PDF/A) beats a loosely-specified text one
> (CSV, markdown-plus-extensions) on every factor the preservation community
> actually scores.

Ranked by the criterion that predicts survival — is the bit-level meaning
written down independently of any implementation? —

    SQLite > TIFF ~ PNG ~ FITS > CommonMark-strict > OOXML > CSV
           > markdown-with-unspecified-extensions

**Note where the incumbent lands.** This is not an argument against text; it is
an argument that choosing text obligates you to write the spec, because text
does not supply one. Which is precisely what §7.3 is for.

**Three concrete mandates fall out of this section:**

    T1  NFC is the only conforming normalization for identifiers; canon()
        normalizes; non-NFC identifiers are rejected.
    T2  Identifiers are restricted to a declared code-point profile; `Cf`
        (format/invisible) characters are rejected.
    T3  Files are UTF-8, LF, no BOM -- and this is ENFORCED by the parser
        under P1, not left to .gitattributes, because .gitattributes is not
        consulted in a bare repo (R5).

---

## 9. Format mortality: the mechanism in each case

All quotes below were retrieved from primary documents this session (several via
the Wayback Machine, since `mass.gov`'s ETRM and Microsoft's RTF pages are gone).

### 9.1 Survivors

**Unicode / plain text.** Survival by *binding the standards body*, not the
implementers (https://www.unicode.org/policies/stability_policy.html):
*"Once a character is encoded, it will not be moved or removed."*; and the
Normalization Stability Policy — *"If a string contains only characters from a
given version of Unicode, and it is put into a normalized form in accordance
with that version of Unicode, then the results will be identical to the results
of putting that string into a normalized form in accordance with any subsequent
version of Unicode"*, enforced by *"Once a character is encoded, its canonical
combining class and decomposition mapping will not be changed in any way."*
The price is frozen errors: `U+FEFF` is still named ZERO WIDTH NO-BREAK SPACE
forever. This is E1 at the character level, and it is what makes T1 (NFC
identifiers) safe to commit to for thirty years.

**TeX.** Knuth, TUGboat 11(4) 1990 (https://tug.org/TUGboat/tb11-4/tb30knut.pdf):
*"Let us regard these systems as fixed points, which should give the same results
100 years from now that they produce today."* … *"At the time of my death …
all 'bugs' will be permanent 'features.'"* … *"nobody is allowed to call a system
TeX or METAFONT unless that system conforms 100% to my own programs, as I have
specified in the manuals for the TRIP and TRAP tests."* … *"the authors of such
systems must think of another name."*

It held. TUGboat 42(1) 2021, *The TeX tuneup of 2021*: *"As in 2008 and 2014,
both TeX and METAFONT have changed slightly … But again there's good news,
because **the changes are essentially invisible.**"* and *"one of TeX's principal
advantages is the fact that it does not change — except for serious flaws whose
correction is unlikely to affect more than a very tiny number of archival
documents."*

**And it cost exactly what E1-vs-E0 predicts.** Knuth's architecture sentence —
*"Improved macro packages can be added on the input side; improved device drivers
can be added on the output side"* — is the constraint that forced everything
else outward. Unicode could not be a macro package (tokenisation is in the frozen
binary), so it arrived as **engine forks that had to change the name**: pdfTeX,
XeTeX, LuaTeX. And the LaTeX Project's own surrender
(https://www.latex-project.org/latex3/): *"we made the decision to drop the idea
of a separate LaTeX3 format that would exist in parallel to LaTeX2e, but instead
decided to gradually modernize LaTeX."*

**Freezing does not prevent change; it relocates change into forks and makes the
fork boundary the compatibility boundary.** This is precisely why this document
recommends E1 (append-only) rather than E0 (never change) — and why E3 makes the
rename cheap and *inside* the system rather than expensive and outside it.

**PDF/A — the model for an archival subset.** ISO 19005-1 clause text, taken from
veraPDF, the PDF Association's own reference validator
(https://github.com/veraPDF/veraPDF-validation-profiles):

| Clause | Requirement |
|---|---|
| 6.1.3 | "The keyword **Encrypt** shall not be used in the trailer dictionary" |
| 6.1.7 | "A stream object dictionary shall not contain the **F, FFilter, or FDecodeParms** keys" (the external-file-reference keys) |
| 6.1.10 | "**The LZWDecode filter shall not be permitted**" |
| 6.2.3.3 | "If an **uncalibrated colour space** is used … that file shall contain a PDF/A-1 **OutputIntent**" |
| 6.3.4 | "**The font programs for all fonts used within a conforming file shall be embedded within that file**" |
| 6.6.1 | "**The Launch, Sound, Movie, ResetForm, ImportData and JavaScript actions shall not be permitted.**" |
| 6.7.2 | "**The document catalog dictionary of a conforming file shall contain the Metadata key**" (mandatory XMP) |
| — | "A content stream shall not contain any operators not defined in PDF Reference **even if such operators are bracketed by the BX/EX compatibility operators**" |

**The pattern, stated precisely: an archival subset is defined by one test —
does rendering this construct require anything not inside the file?** Code
(JavaScript, Launch), references (F/FFilter, external fonts), host state
(DeviceRGB without an OutputIntent), access control (Encrypt), legal permission
(LZW), and renderer guesswork (undefined operators, *even under BX/EX*) all fail
it. Plus one *addition*: mandatory self-description.

Two failure modes are already visible. **PDF/A-3 (2012) reopened the hole** by
allowing arbitrary embedded files — the archival container became a smuggling
envelope. And conversion is lossy in practice. Note the first one against §1.6:
an ignorable channel with no inertness rule is how a subset stops being a subset.

**TIFF.** Survival by a mandatory floor (TIFF 6.0,
https://download.osgeo.org/libtiff/doc/TIFF6.pdf): *"The document was divided
into two parts—Baseline and Extensions—to help developers make better and more
consistent implementation choices… those features that **all general-purpose
TIFF readers should support**"* and *"**A Baseline TIFF 6.0 reader is not required
to support any extensions.**"*

And the confession that names the trade: *"**The goal is that TIFF files should
never become obsolete**… **However, TIFF 6.0 files that use one of the major new
extensions … will not be successfully read by older software. In such cases, the
older applications must gracefully give up and refuse to import the image**,
providing the user with a reasonably informative message."*

That is **E2, in the words of a format that shipped it in 1992**: a new critical
feature is *expected* to break old readers, and the correct old-reader behaviour
is a loud, informative refusal. The "Thousands of Incompatible File Formats"
joke is real, and its cause is the unregistered private-tag range — *"Tags
numbered 32768 or higher … **You do not need to tell the TIFF administrator what
you plan to use them for**"* — but the damage was **bounded by the baseline**.

**HTML.** W3C HTML Design Principles (https://www.w3.org/TR/html-design-principles/):
*"**Evolution Not Revolution**: It is better to evolve an existing design rather
than throwing it away. This way, authors don't have to learn new models and
**content will live longer**."* and *"**Handle Errors**: Error handling should be
defined so that interoperable implementations can be achieved."*

The normative payoff, HTML Standard §13.2.2: *"**The error handling for parse
errors is well-defined** (that's the processing rules described throughout this
specification)."* Pre-HTML5, "permissive" meant *unspecified* — N browsers, N
DOMs. HTML5 wrote the tolerance down as an algorithm, so any conforming parser
produces the identical DOM from identical bytes, valid or not.
**Permissive + deterministic beats strict + brittle, and it also beats
permissive + undefined.**

**FITS — the strongest immortality clause found anywhere.** FITS Standard 4.0
§3.7, *Restrictions on changes*
(https://fits.gsfc.nasa.gov/standard40/fits_standard40aa-le.pdf):

> "**Any structure that is a valid FITS structure shall remain a valid FITS
> structure at all future times.** Use of certain valid FITS structures may be
> deprecated by this or future FITS Standard documents."

with the loophole closed in §2: *"**Deprecate** To express disapproval of. This
term is used to refer to obsolete structures that should not be used in new FITS
files, **but which shall remain valid indefinitely.**"* That is **E1 and E5,
verbatim, from 1993.**

Extensions (§3.4) are added by three rules this design should copy outright:
*"Each extension type shall have a unique type name … **To preclude conflict,
extension type names must be registered with the IAUFWG.**"*; *"The total number
of bits in the data of each extension **shall be specified in the header for that
extension**"* — i.e. **self-delimiting**, so an unknown extension can be skipped
exactly; and the anti-proliferation rule TIFF lacked: *"**Only one extension
format shall be approved for each type of data organization.**"*

And the thesis sentence, which is the whole of S1–S3 (§1 of the Standard):

> "**One important feature of the FITS format is that its structure, down to the
> bit level, is completely specified in documents** … future researchers should
> be able to decode the stream of bytes in any FITS format data file. **In
> contrast, many other current data formats are only implicitly defined by the
> software that reads and writes the files. If that software is not continually
> maintained … then the information encoded in those data files could be lost.**"

Its epigraph, from the US National Research Council: *"An archival format must be
utterly portable and self-describing, on the assumption that, apart from the
transcription device, **neither the software nor the hardware that wrote the data
will be available when the data are read.**"*

Governance is the other half. IAU FITS Working Group Rules
(https://fits.gsfc.nasa.gov/iaufwg/iaufwg_rules.html): 4-week public comment,
3/4 quorum, demonstrated interoperability across *"independent software
implementations running on different types of computer platforms"*, and — the
remarkable clause — *"**If any of the members are considering a 'No' vote … the
voting process will be suspended for up to 3 months to try to negotiate a
compromise that will lead to a unanimous vote**."* Six versions in 25 years.
**Expensive governance is not a bug; it is the load-bearing member.**

The honest cost: FITS cannot fix its 80-column headers or its lack of chunked
parallel I/O, *because* §3.7 forbids it. The exit is a new format, not a new
version — Knuth's answer again, and E3.

### 9.2 Deaths

**PostScript — the format was a program.** Adobe's own successor spec, ISO
32000-1 §Introduction: *"**Unlike Postscript, which is a programming language,
PDF is based on a structured binary file format that is optimized for high
performance in interactive viewing.**"* No random access to page *n*, no
guaranteed termination, no page count without interpretation. **Archives and
viewers must be able to answer questions about a file without running it.** This
is the direct argument for S3, and the reason `.tbl`'s formula language must be
specified and total rather than "whatever the engine does".

**SGML.** Killed by optionality that made parsing depend on the DTD. XML deleted
DATATAG, OMITTAG, RANK, LINK, CONCUR, SUBDOC, FORMAL and SHORTREF
(https://www.w3.org/TR/NOTE-sgml-xml), under design goal 5: *"The number of
optional features in XML is to be kept to the absolute minimum, **ideally
zero**."*

**XHTML / XML-on-the-web.** Killed by draconian error handling — XML 1.0 §1.2:
*"Once a fatal error is detected … the processor **MUST NOT continue normal
processing**."* W3C's own epitaph, HTML Standard §1.6: *"**XML's deployment as a
web technology was limited to entirely new technologies (like RSS and later
Atom), rather than as a replacement for existing deployed technologies (like
HTML).**"* and the XHTML2 WG's charter *"expire[d] at the end of 2009"*.
**Strictness works where you control the producer and fails where you do not** —
which is why P5's poisoning rule matters: it keeps strictness at value
granularity rather than document granularity.

**RTF — good design, no constituency.** RTF's `\*` must-skip flag is one of the
best mechanisms in this survey (§5.1) and RTF files from 1990 still open. It is
listed in Microsoft's Open Specification Promise, in the *legacy* bucket — and
has received **no revisions**. Meanwhile `[MS-DOC]`, for the *deader* binary
format, was first published 2008-06-27 and is at **revision 12.5, 17 February
2026 — roughly 50 revisions over 18 years.** **A format still being specified is
alive to its vendor; one that is only being licensed is not.** Technical
survivability is necessary and not sufficient; institutional survivability is
binding.

**WordPerfect, Lotus 1-2-3.** The format's definition existed only inside a
product. FITS names this exact class. Lotus is worse than WordPerfect for the
same reason PostScript is worse than PDF: a spreadsheet's cell values are
outputs of a dead evaluator — function set, error semantics, date epoch,
recalculation order — so preserving the bytes preserves nothing you can trust.
**This is the sharpest possible warning for `.tbl`.**

**Word `.doc`.** Documented under the OSP: *"Microsoft irrevocably promises not
to assert any Microsoft Necessary Claims against you…"*, with Office binary
formats published **2008-02-15** and the `[MS-*]` series **2008-06-30** — eleven
years after Word 97, simultaneous with the OOXML ISO ballot. It genuinely helped
(LibreOffice, Apache POI, every forensic tool). But note the timing rule:
**documentation is what happens to a format after it stops being strategic**, so
archival policy cannot rely on it.

**OOXML transitional — compatibility mode eats the standard.** ECMA-376 **Part 4,
"Transitional Migration Features", 5th edition, December 2016**, Introduction:

> "**The intent of this Part of ECMA-376 is to enable a transitional period during
> which existing binary documents being migrated to ECMA-376 can make use of
> legacy features to preserve their fidelity, while noting that new documents
> should not use them.**"
>
> "**This Part of ECMA-376 is normative for the current edition of ECMA-376, but
> is not guaranteed to be included in future revisions of that Standard. The
> intent is to enable the group responsible for maintenance … to choose, at a
> later date, to remove this set of features.**"

Ten years later it has not been removed, and Part 4 is still at its 5th edition.
**A transitional period with five editions and no end date is not a transitional
period.** Microsoft maintains a permanent divergence document, `[MS-OI29500]`,
covering *"areas where the product is known to vary from or extend the
specification"* — first published 2009-12-15, at **revision 25.0, 18 August
2026**.

The mechanism is mechanical: producers write what round-trips the corpus;
consumers must read what producers write; therefore the compatibility class is
the real interop surface. **TIFF avoided this by making the floor mandatory and
the extensions optional. OOXML inverted the polarity.** The countermeasure here
is E5 + W-a: keep the old readable forever, but make the *new* thing what a
writer emits by default.

**ODF — the most important case, because it should have won.** Retrieved from the
Wayback Machine: Massachusetts **ETRM v4.0, Information Domain, effective
2007-08-01**. The Technology Areas are headed *"Open Formats"* and *"Other
Acceptable Formats"*, and the operative wording for **both** is identical:

> "OASIS OPEN DOCUMENT FORMAT … Guidelines – **The OpenDocument format may be
> used** for office documents…"
>
> "ECMA-376 OFFICE OPEN XML … **This XML-based document format was designed to
> ensure the highest levels of fidelity with legacy documents created in
> proprietary Microsoft Office binary document formats such as .doc, .xls, and
> .ppt.** Guidelines – **The Open XML format may be used** for office
> documents…"
>
> "Migration – All agencies are expected to migrate away from **proprietary,
> binary** office document formats to open, XML-based office document formats."

And the ITD's *Statement on ETRM v4.0 Public Review Comments*, 2007-08-01:

> "**460 individuals and organizations** … **Most of the comments addressed
> revisions made to the Data Formats section, specifically the inclusion of
> Ecma-376 Office Open XML as an acceptable document format for office
> applications along with the Open Document Format (ODF).** … **Therefore, we
> will be moving forward to include both ODF and Open XML as acceptable document
> formats.**" … "**Document formats play a part in this vision by serving as
> containers for the information rather than being the end goal.**"

The mechanism, now precisely evidenced. The *only* surviving obligation is
"migrate away from **binary**" — and OOXML satisfies it trivially, **by design**,
since its stated purpose is fidelity with the binary corpus. **The escape hatch
was not an oversight; it was the alternative's design goal.** The last quoted
sentence is the reversal in miniature: once the objective is restated as
"XML-based containers" rather than one format, the mandate has dissolved.

(The v3.5 "must" wording is widely reported and I could not retrieve it — the
Wayback CDX index has only the v3.5 *vendor response* PDFs. The v4.0 permissive
wording above is verified verbatim, and the ITD statement establishes that the
prior state was ODF-only, which is sufficient for the mechanism.)

Two aggravators, both verified: a procurement mandate governs *new files*, not
the 100M-document corpus where switching cost lives; and ODF's own version
sprawl — Microsoft's OSP table alone lists **six** distinct ODF versions (1.0
OASIS, 1.0 ISO/IEC 26300:2006, 1.1 OASIS, 1.1 ISO with COR1/COR2/Amd1, 1.2
OASIS, 1.3 OASIS) with the OASIS and ISO tracks diverging — while the incumbent
shipped one thing everyone called "docx".

**MARC — survival by mutual hostage-taking, and the mechanism that keeps it
alive is the one this design must not reproduce.** LC's BIBFRAME FAQ:

> "**Are my MARC records convertible into BIBFRAME?** Yes."
> "**Can I get MARC records from BIBFRAME resources? Not at this time.** … Only
> after those elements have sufficiently stabilized would attention turn to a
> BIBFRAME-to-MARC transformation."

**Migration is one-way.** Any library that moves loses access to the shared MARC
exchange economy that made cataloguing affordable. So nobody moves first, and a
1960s tape format is still *"the foundation of most library catalogs used
today."* The identical asymmetry — lossless out, lossy back — is what kept ODF
from displacing `.doc`. **The question is never "can you convert them"; it is
"can you convert them back".**

### 9.3 The mechanisms that recur — and the one that changes the policy

**Survival:** (1) a clause binding the *standards body* never to invalidate an
existing file (Unicode, FITS §3.7, Knuth) → **E1**; (2) a mandatory floor with
optional extension *above* it, never below (TIFF Baseline, HTML) → **E5, W-a**;
(3) self-delimiting structure so unknowns can be skipped exactly (FITS's
mandatory byte count, TIFF's typed IFD, RTF's groups) → **P3, and the argument
for line-orientation itself**; (4) the definition lives in a document, not a
program (FITS's thesis) → **S1–S3**; (5) inertness — no computation, no external
dependencies (PDF/A) → **S3, P4**; (6) expensive consensus governance (IAU-FWG's
3-month single-No suspension); (7) specify the error behaviour, don't merely
permit it (HTML5) → **§1.12**.

**Death:** the format is a program (PostScript, Lotus); defined by one vendor's
binary (WordPerfect, `.doc`); no independent constituency (RTF); the
compatibility class becomes the format (OOXML transitional); the mandate has an
escape hatch (ODF/Massachusetts); unregistered unbounded extensibility (TIFF's
private tags, bounded only by the baseline); strictness applied to inputs you do
not control (XHTML); **and migration that only runs one way (MARC/BIBFRAME).**

**That last one is new, and it amends the policy.** Nothing in §2 required a
migration to be reversible. The MARC case shows why it must be:

    E7  MIGRATION MUST BE REVERSIBLE   (added to §2 as a result of this case)

This is cheap here and expensive elsewhere: E1 forbids redefining bytes, so a
`.tbl2` that is a pure superset has a trivial inverse for any document not using
new constructs — and for documents that do, the honest answer is a loud refusal
rather than a lossy downgrade. It is also the reason E3's rename beats an
in-place version bump: **both formats keep existing, so "moving back" is not a
migration at all.**


## 10. What this changes in the design

### 10.1 Amendments to the existing invariants

    I7  STRICT PARSING -- AMENDED
        Old: "a parser must REJECT input it does not understand, never skip it."
        New: "a parser must RECOGNISE every byte of its input. It must reject
              any construct it does not understand, EXCEPT constructs in the
              annotation class, which it must ignore and preserve byte-exact.
              The annotation class is permanently guaranteed inert."
        Reason: I7 as written cannot survive its own v2. Measured: it rejects
        6 of 12 corpus files, including one that differs only by a comment.

    I1  LOCALITY -- EXTENDED TO THE ENCODING LAYER
        A one-word edit produced a 4-line diff purely from NFD renormalisation,
        and two edits to different paragraphs conflicted. I1 is not achievable
        without T1-T3.

    I3  LOUD FAILURE -- EXTENDED WITH A POISONING RULE
        A value whose derivation closure contains something unknown is reported
        as an error naming the construct, not withheld and not guessed. Other
        values in the same artifact are still reported.

    I5  VALID ARTIFACTS -- UNCHANGED, BUT NOW LOAD-BEARING FOR EVOLUTION
        The conflicted-file cases are the same cases as the future-version
        cases, from the parser's point of view: input it cannot fully account
        for. One mechanism serves both.

### 10.2 New content for the type contract

The four-function contract (`parse`/`render`/`resolve`/`refs`) needs one
addition and one clarification:

    parse : bytes -> EntityMap + IgnoredSpans
        The ignored spans must be carried, not discarded, or read-modify-write
        destroys them (measured).

    render : EntityMap + IgnoredSpans -> bytes
        Already required to be a boundary splice by I1. Now also required by
        P6. This is the same requirement, discovered twice.

`refs` already computes the derivation closure, which is what P5 needs. No
fifth function.

### 10.3 The open questions this leaves

1. **Who governs the format?** Every death mechanism in §9 that was not
   technical was governance, and this document has no answer for that. A
   conformance suite in a public-domain repository with a written amendment
   procedure is the minimum; SQLite's model (public-domain documentation, not
   open-contribution) is worth studying as a deliberate choice rather than an
   accident.
2. **Is `?` alternation worth its complexity given R4 forbids most uses of it?**
   It costs one construct in v1 and cannot be added later. I recommend shipping
   it, but the case is "insurance", not "utility", and a reasonable person could
   decline.
3. **Does the poisoning rule (P5) confuse users more than a whole-file
   rejection?** Untested. It is better *engineering*; whether "3 of your 4
   totals are shown and one says #UNKNOWN(!filter)" beats "this file needs a
   newer version" is a UX question this research did not touch.
4. **The `%` inertness promise is unenforceable against a future spec author.**
   The conformance test (strip all `%`, assert no value changes) catches a
   violating *implementation*; nothing catches a violating *specification*
   except the discipline of the people maintaining it. This is the one
   remaining silent-wrong in the measured table and it does not have a
   technical fix.

### 10.4 The sharpest facts

1. **The size argument for markdown does not survive git.** A 145,584-byte
   markdown file is **28,069 bytes** as a git loose object and **28,560** in a
   packfile, against the prosecution's **28,457-byte** `.docx` — a dead heat
   within 0.4%, because `.docx` is a ZIP and git deflates every blob. Across
   history the argument reverses, since a one-word edit rewrites an entire
   deflate stream in a `.docx`.

2. **Ignoring is not enough — you must preserve, and the natural implementation
   does not.** Protobuf 3.5 restored unknown-field preservation because
   read-modify-write proxies were silently deleting data
   (https://github.com/protocolbuffers/protobuf/releases/tag/v3.5.0). Measured
   here: re-emitting from the parsed model destroyed both unknown annotations
   and reformatted 6 lines; a boundary splice preserved both and changed 1.
   PNG has a dedicated bit for this — *"safe-to-copy … not of interest to pure
   decoders, but it is needed by PNG editors"* — and so does the lens GetPut
   law, independently derived.

3. **Capability declarations decay; self-describing payloads do not.** SVG 2
   deleted `requiredFeatures` because *"poor specification and implementation of
   this attribute made it unreliable as a test of feature support."* Twenty
   years later LibreOffice's OOXML reader resolves `mc:Choice Requires=` against
   a hardcoded prefix whitelist — *"we can't access namespaces as the correct
   xml filter is long gone"* — while its exporter writes `mc:Ignorable`
   unconditionally. Two independent mechanisms, identical failure. What survives
   is PNG's case bits, RTF's `\*`, and DITA's `class="- topic/li task/step "`,
   which DITA-OT genuinely dispatches on.

4. **Org-mode's `#+TBLFM:` cannot be specified, and the number is 55,567.**
   The syntax document's entire normative content for it is *"a string
   consisting of any characters but a newline"*; the semantics are Emacs Calc
   (43 files, **55,567 lines**) plus an Elisp evaluator. Across nine non-Emacs
   implementations, **zero** evaluate it. FITS's standard names this failure
   class directly: *"many other current data formats are only implicitly defined
   by the software that reads and writes the files."*

5. **A mandate that permits an alternative is not a mandate.** Massachusetts
   ETRM v4.0 (2007-08-01, retrieved via Wayback) gives ODF and OOXML the
   *identical* operative wording — "**may be used**" — and the only surviving
   obligation is to "migrate away from **proprietary, binary**" formats, which
   OOXML satisfies trivially because its stated design goal is *"the highest
   levels of fidelity with legacy documents created in proprietary Microsoft
   Office binary document formats."* **The escape hatch was the alternative's
   design goal.** ISO standardisation, IBM/Sun backing and a state law lost to
   installed base plus a lossless compatibility path.

6. **The strongest immortality clause anyone has written is FITS §3.7**, and it
   is two sentences: *"Any structure that is a valid FITS structure shall remain
   a valid FITS structure at all future times."* plus the definition that closes
   the loophole — deprecated structures *"shall remain valid indefinitely."*
   Compare ECMA-376 Part 4, which reserved the right to *remove* its
   compatibility class and, five editions later, has removed nothing. **A
   promise not to break outperforms a promise to clean up, in both
   directions.**

7. **Markdown's tolerance is worse than "conflict markers render".** Against a
   real `git merge` conflict, `=======` is **consumed** as a setext underline —
   the marker vanishes from the output and silently promotes the *ours* side to
   `<h1>` — while `>>>>>>> feat` becomes seven nested blockquotes. Four engines,
   three different documents, **all exit 0**. There is no byte sequence a
   markdown document can contain that a conforming processor is obliged to
   reject, so no corrupt state can ever be made loud without leaving the format.

### 10.5 The one-sentence version

**Recognise every byte or fail; ignore only what the grammar pre-declared inert
and preserve it byte-exact; never redefine existing bytes; rename rather than
break; and ship the conformance suite, because the spec is only as large as the
tests that hold it.**

---

## Sources

Primary sources quoted above, by section:

- RFC 9413 *Maintaining Robust Protocols* — https://www.rfc-editor.org/rfc/rfc9413.txt
- RFC 8701 *GREASE* — https://www.rfc-editor.org/rfc/rfc8701.txt · RFC 9170
- RFC 9110 *HTTP Semantics* · RFC 7515 §4.1.11 *JOSE `crit`* · RFC 3597 *unknown DNS RR types* · RFC 4287 §6.3 *Atom* · RFC 2046 §5.1.4 · RFC 4180 *CSV* · RFC 2026 §4.1.2 · RFC 6410 · RFC 2083 §12.11 *PNG* · RFC 8794 *EBML*
- W3C TAG, *Extending and Versioning Languages* — https://www.w3.org/2001/tag/doc/versioning-compatibility-strategies · https://www.w3.org/2001/tag/doc/versioning-xml · https://www.w3.org/2001/tag/doc/leastPower.html
- PNG (Third Edition) — https://www.w3.org/TR/png-3/
- SVG 2 §5.7.1 — https://www.w3.org/TR/SVG2/struct.html
- HTML Standard — https://html.spec.whatwg.org/ · WHATWG FAQ — https://whatwg.org/faq
- SOAP 1.2 Part 1 §2.4 — https://www.w3.org/TR/soap12-part1/
- Protocol Buffers — https://protobuf.dev/programming-guides/proto3/ · https://protobuf.dev/best-practices/dos-donts/ · v3.5.0 release notes
- Apache Avro 1.12.0 Specification, *Schema Resolution*
- Cap'n Proto — https://capnproto.org/language.html · https://capnproto.org/faq.html
- JSON Schema 2020-12 Core §8.1.1, §10.3.2.3, §11.3
- SQLite — https://www.sqlite.org/lts.html · fileformat2.html · testing.html · appfileformat.html · locrsf.html · copyright.html
- Go — https://go.dev/doc/go1compat · https://go.dev/blog/compat
- Rust — https://doc.rust-lang.org/edition-guide/editions/
- Knuth, *The Future of TeX and METAFONT*, TUGboat 11(4) 1990 — https://tug.org/TUGboat/tb11-4/tb30knut.pdf · Mittelbach, TUGboat 11(3) 1990
- Hickey, *Spec-ulation*, Clojure/conj 2016 — https://www.youtube.com/watch?v=oyLBGkS5ICk
- Winters, P1863R0 / P2028R0, WG21 — https://open-std.org/jtc1/sc22/wg21/docs/papers/2019/p1863r0.pdf
- ECMA-376 Part 3 (MCE) §7.2–7.7, §9.2–9.4 · Microsoft `[MS-OI29500]` · RTF Specification 1.9.1
- OASIS DITA, `specification/archSpec/base/specialization-class-attribute.dita`
- FITS Standard 4.0 — https://fits.gsfc.nasa.gov/standard40/fits_standard40aa-le.pdf
- Library of Congress *Sustainability Factors* — https://www.loc.gov/preservation/digital/formats/sustain/sustain.shtml · FDD 000461 (SQLite) · FDD 000323 (CSV) · Recommended Formats Statement
- Org — https://orgmode.org/worg/dev/org-syntax.html · https://orgmode.org/manual/The-Spreadsheet.html
- Foster, Greenwald, Moore, Pierce, Schmitt, *Combinators for Bidirectional Tree Transformations*, TOPLAS 2007
- Litt, van Hardenberg, Henry, *Project Cambria* — https://www.inkandswitch.com/cambria/
- Sassaman, Patterson, Bratus, *The Halting Problems of Network Stack Insecurity*
- Boucher & Anderson, *Trojan Source*, USENIX Security 2023 — https://trojansource.codes/
- CommonMark — https://spec.commonmark.org/ · https://talk.commonmark.org/t/semantic-versioning/567
- git documentation: `core.safecrlf`, `core.precomposeUnicode`, `blame.ignoreRevsFile`

Local experiments: `experiments/D11-evolution/` —
`tbl.py` (reference parser, four policies) · `tbl_v0_buggy.py` (the prefix-check
bug, kept as evidence) · `corpus.py` + `drive.py` (12-case policy comparison) ·
`suite.py` (15 evolution conformance tests) · `roundtrip.py` (preservation) ·
`ancestry.py` (DITA transplant) · `altcontent.py` (downgrade path) ·
`migrate.py` (two-assertion migration check) · `verrepo/`, `v2/` (version-field
locality) · `nfc/`, `nfc2/` (Unicode normalization)
