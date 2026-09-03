# Spec amendments forced by the adversarial suite author

74 new cases written from SPEC.md alone; 20 fail. The failures are the point.

## Two silent-data-loss bugs, and they share one cause

**1. A table with no alignment row loses a row of data.** §4 says the second
line is the alignment row and the rest are data. Given a table whose second line
is a data row, the implementation accepts it and **silently consumes that row as
the alignment row**: `sum(qty)` returns `5.0` where the file plainly says
`15.0`. A clean merge, a plausible number, a missing row — the exact failure the
project exists to prevent, in the reference implementation.

**2. `canon` is not idempotent on GFM alignment spellings.** Given `:-:` or
`-:`, `canon` emits **no alignment row at all**, and the second pass then eats a
data row. `canon(canon(x)) == canon(x)` fails, and data disappears.

Both are one defect: **the alignment recogniser demands a spelling the format
never specified, and "not an alignment row" degrades to "is a data row."**

And the root cause is in the spec, not the code: **§4 and §5 never define what an
alignment row looks like, nor whether it is optional.** The bugs live in that
gap. A reader that cannot recognise a construct must refuse, never
reinterpret it as a different construct — degrading a failed recognition into a
*different successful* recognition is how a parser manufactures silent-wrong.

## The spec is wrong about CRLF, and the suite wins

§3 says the parser enforces LF. But the pre-existing `roundtrip/crlf` case
requires byte-exact CRLF round-trip, and the preamble says the suite wins.
So §3 is wrong as written.

The correct rule, which also preserves I1: **line endings are preserved; only
the canonical form is LF.** A lone `\r` is a different matter and must be
refused — it makes two rowspec rows share one git line, which breaks the
format's founding rule that one line is one row.

## A contradiction between §7 and §8

§7 defines `lookup(customers.mdtbl, ...)`, which reads a path. §8 says
constructs that would read a path are unparseable. Both cannot stand. The
resolution: §8's prohibition is about *arbitrary* paths computed at evaluation
time; a lookup target is a literal, resolved relative to the artifact, and
declared in the formula where a reader can see it. The spec must say so.

## The fixture format cannot express what §7 requires

`run_cases.py` passes only `input.mdtbl` to `evaluate`, so a second table is
unreachable — **`lookup()` and `#REF!(file[key])` are untestable in the current
suite.** Over half of §7 had no case at all: filtered aggregates, `@`-group
aggregates, `lookup`, and `avg` (which returns `None`).

This is the suite's own coupled-state defect: a fixture format that can only
express single-file cases silently bounds what the spec can assert.

## Recognition is not total, as §9 claims

Nine cases produce uncaught Python tracebacks rather than refusals. The sharpest
is a table-level `sum` over a raw column holding `1,000` — `ValueError`, not
`#REF!`. The existing suite only ever routed a bad value through a *computed*
column, so this is live shipped behaviour, not a missing feature. Similarly
`time.time()` and `__import__(...)` do not execute — good — but surface as
`AttributeError`, so a validator cannot report them.

## Mandated refusals that were never implemented

- §5 "Writing a value into a computed cell is an error" — accepted, and the
  hand-written value is silently discarded. Note the asymmetry the author
  spotted: the *API* refuses it (`mutate/computed-col-refused` passes) while the
  *parser* does not, **and a merge can produce one.**
- §3 `Cf` characters rejected in identifiers — a zero-width joiner is accepted,
  so two visually identical column names coexist.

## Spec gaps where no case could be written

Alignment-row syntax and optionality; blank cells in the order column;
aggregates over zero rows; evaluation order and forward references among
computed columns (a mutant already exists for a rule the spec never states);
what a cycle *evaluates to*; coercion beyond the three named refusals (`+5`,
`1e3`, `inf`, `nan`, unicode digits); `count` semantics against §8's poisoning
rule; duplicate ids when no key is declared; and §12 editions, which currently
have **no observable behaviour at all**.

## A contamination vector to close

The author disclosed that it did not read `reference/`, but that
`conformance/mutants.py` stores mutants as literal source-patch pairs, so
reading the mutant list exposed roughly thirty fragments of implementation
source. It derived no expectation from them and said so.

That is a real leak in the standing rule's enforcement: **the gate's own file
leaks the implementation to whoever is meant not to read it.** Expressing
mutants semantically rather than as source patches — already required to stop
them going stale — closes this too. One change, two reasons.
