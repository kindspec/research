# Two implementations, seven disagreements, same bytes

The adversarial case author wrote 17 cases for the annotation channel, CRLF and
the alignment grammar. Seven failed — and **the two failure sets are disjoint.**

    case                                          reference   alt
    parse/annotation-containing-a-declaration     FAIL        pass
    eval/annotation-with-declaration-syntax-inert FAIL        pass
    parse/annotation-line-inside-the-table        FAIL        pass
    parse/alignment-empty-cell-refused            FAIL        pass
    parse/crlf-accepted                           pass        FAIL
    eval/crlf-evaluates                           pass        FAIL
    canon/crlf-preserves-values                   pass        FAIL

Every one is a place where two independent implementations of the same sentence
produce **opposite outcomes on the same bytes**. In all seven the prose
determines the answer and one implementation did not follow it. None is a spec
defect — which is the strongest evidence so far that the spec is converging.

## The four that were mine, and what they were

**1–2. The inertness promise was broken by content.** My parser refused any
annotation line *containing* `:=`, whatever its first character. §9's definition
is positional and total — "a line whose first non-space character is `#`" — and
exempts nothing based on what the rest of the line resembles. The two things a
human is most likely to write in an annotation are a note about the declaration
below it and **an old declaration commented out rather than deleted**. Both were
refused.

**3. A `#` line inside the table, and this is the sharp one.** §4 says the table
is a *contiguous* run of lines beginning with `|`; §9 places the channel
"outside the table". My parser collected every pipe line anywhere in the file,
so a `#` between two data rows silently extended the table across it. **The two
implementations disagreed about how many rows the file has.**

**4. An empty alignment cell was skipped rather than refused** — the same defect
shape that once consumed a data row: an unrecognised construct degraded into a
successful parse instead of a refusal.

Fixed, plus the totality rule that follows: after the table run, a line is
blank, an annotation, or a declaration — anything else is refused rather than
silently ignored.

## The three that were the other implementation's, and why they matter more

`rowspec_alt` refused CRLF outright, citing §3 **as it read before the
amendment**. Nothing had ever asked a CRLF file to *parse* or *evaluate* —
`roundtrip/crlf` only exercised `render(structure(x))`.

> A whole implementation was sitting on a retired rule with all 133 cases green.

"Accepted" is not "round-trips", and no case had ever asked the difference. That
is the clearest demonstration yet of what the suite is for and of how a gap in
it hides a real divergence.

## A claim neither implementation satisfies, which no check can currently express

§3 says only the canonical form is LF. Measured:

    reference   canon retains 3 of 7 CRs -- table lines stripped, blank and
                declaration lines keep theirs, producing MIXED line endings
    alt         canon retains all 7

**Both wrong**, and nothing catches it: `idempotent` holds on a mixed-ending
file, `preserves-values` ignores bytes, `already-canonical` demands the
opposite, and `removes-padding` inspects `splitlines()` output, which discards
the `\r` before it looks.

The fix is a golden-file case form — an `expect.mdtbl` beside `input.mdtbl`,
asserting `canon(input) == expect` byte-for-byte — which would let a case pin
exact canonical bytes rather than a property of them.

## Also enforced: lookup path confinement

§7 states the lookup target is "confined to the repository" and nothing enforced
it. Now refused:

    lookup in 'who' targets '../../../etc/passwd', which escapes the repository

## Two things to decide rather than discover

- **`|||||||` is a seven-pipe run, and so is a data row of six empty cells.**
  The diff3 conflict marker is indistinguishable from a legal empty row by shape
  alone. Position and required trailing content are the levers.
- **Text collation is `str` ordering in both implementations**, but the only
  case distinguishes ASCII lowercase words. `Ápple` vs `apple` vs `Apple` is
  undetermined, so two implementations can order the same table differently
  while both stay green.
