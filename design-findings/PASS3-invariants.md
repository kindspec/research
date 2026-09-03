# Pass 3 — collapsing the invariants (after L1–L4)

Four experiments produced four failures that looked unrelated and are one
defect. Naming it correctly shrinks the design.

## The four failures

    L1  A1 cell references            insert a row -> 480 instead of 660
    L2  markdown alignment row `--:`  my renderer silently dropped it
    L3  block trailing blank lines    moving a block defeated its identity
    L4  absolute canvas coordinates   adding a node rewrote every element

## The one defect

**Coupled representation: state whose bytes must change when unrelated content
changes.**

A range that must widen when a row is inserted. A coordinate that must shift
when a sibling appears. A separator that belongs to a position rather than to
the thing it follows. Each is a value in the file that is not about the thing
it is stored on.

Coupled state is what destroys diffs, and destroyed diffs are what makes a
git-backed system pointless. Everything else follows.

## The invariant set, reduced to four

    I1  LOCALITY
        A semantic edit of bounded size produces a byte diff of bounded size.
        Enforced by: render(parse(b)) == b, and canon(canon(x)) == canon(x),
        as property tests over a corpus -- NOT as a coding guideline.
        (L3 shows how to get the first one free: parse boundaries, never
        re-emit content. L2 shows what happens without the test: I broke my own
        law within an hour of writing it down.)

    I2  NOMINAL ADDRESSING
        Nothing may be referenced by a coordinate that a concurrent edit can
        change. Names, not places. This is the design RULE that produces I1;
        the address grammar enforces it by having no coordinates in it.
        Corollary: a value's own geometry is fine (it is data, not a
        reference); what is forbidden is anything ELSE addressing it by that
        geometry.

    I3  LOUD FAILURE
        A broken reference fails visibly and locally. Never zero, never empty,
        never stale, never plausible. Errors propagate through aggregates
        rather than being summed around. (L1 result 2.)

    I4  NO HIDDEN STATE
        Everything affecting a rendered result is in the files. Derived values
        are not authoritative and by default are not committed.

## A fifth, forced by the evidence

    I5  THE WORKING TREE ALWAYS CONTAINS VALID ARTIFACTS

Three separate experiments produced a conflicted file that its own format could
no longer parse:

    L1 case 5  conflicted table  -> no longer a table
    L4 case B  conflicted JSON   -> JSONDecodeError, tool cannot open it

Git's `<<<<<<<` markers are a line-oriented answer imposed on structured data.
They are the reason "just open it in your editor and fix it" is not available
to a non-developer, and they make the substrate's own tools unable to help at
exactly the moment help is needed.

**Therefore: conflicts are DATA STORED BESIDE THE ARTIFACT, never markers
inside it.** The file on disk always holds one coherent version; the competing
version and the conflict record live out-of-band. This is jujutsu's first-class
conflicts applied to documents, and it is the difference between "your
spreadsheet is broken" and "your spreadsheet has two proposed values for one
cell".

## What the invariants have already bought

- I1 via boundary-only parsing: byte-exact round-trip on a torture file that
  pandoc mangles 42 lines of. No serializer needed. (L3)
- I2 via named columns: correct 660 merge from stock git, no driver. (L1)
- I2 via named overrides: clean canvas merge where coordinates conflict AND
  corrupt the file. (L4)
- I3 via error propagation: a renamed column produces #REF! everywhere rather
  than a smaller, plausible total. (L1)

## What is still unproven and must be attacked

- Whether a core this thin does enough work to justify existing at all.
- Whether type-aware merge can actually be DEPLOYED (git merge drivers need
  local config; forges may ignore .gitattributes entirely). If not, I5 and the
  generic merge are fiction outside our own client. This is the single biggest
  live risk in the design.
- Whether similarity-matched block identity holds up on real documents rather
  than three-paragraph fixtures.
- Whether any of this beats simply composing existing tools.

---

# I7 — added after a measured failure in my own prototype

    I7  STRICT PARSING
        A parser must REJECT input it does not understand, never skip it.
        Permissive parsing converts a loud failure into a silent-wrong.

`experiments/L1-nominal-merge`, my own evaluator fed a conflicted file:

    <<<<<<< HEAD
    | gadget   |  20 |  6.00 |
    | sprocket |   8 | 15.00 |
    =======
    | gadget   |  40 |  6.00 |
    | sprocket |  16 | 15.00 |
    >>>>>>> branch

    grand = 960.0        candidates were 480 and 720

It summed BOTH SIDES of an unresolved conflict and produced a number neither
author ever wrote. The cause is one line of leniency: my parser collected lines
beginning with `|` and ignored everything else, so the markers were invisible
to it.

This generalises past conflict markers. Postel's law — be liberal in what you
accept — is actively harmful for a substrate organised against silent-wrong.
Every lenient branch in a parser is a place where a corrupted, conflicted or
half-migrated file yields a plausible number instead of an error.

I3 (loud failure) was scoped to reference resolution. It must be scoped to
PARSING, which is earlier and covers more:

    - unknown lines inside a known structure     -> error, not skip
    - conflict markers anywhere                  -> error, always
    - duplicate names in one namespace           -> error, not last-wins
    - a cell that fails to coerce to its type    -> error, not zero

Corroboration from the reactive-notebook world: given the same class of
concurrent edit that git auto-merges clean, a plain Python notebook silently
last-wins, an A1 spreadsheet gives 480 instead of 660 — and **marimo refuses to
run and names both cells**. The mechanism that produces the loud failure is a
SINGLE-ASSIGNMENT NAMESPACE, not reactivity: order-independence removes
"later", so a collision has nowhere to hide.
