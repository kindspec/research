# Pass 2 — the unification attempt (supersedes H1)

H1 said "don't unify the content models". On reflection that is a cop-out, and
the brief specifically asks whether the three primitives are projections of a
deeper model. They are. Here is the attempt.

## Two primitives, not three

    TEXT           a sequence of characters
    ENTITY MAP     an ordered set of named entities, each a map of
                   attribute -> value, where a value is a scalar, a formula,
                   a geometry, or TEXT

That is the whole model. The brief's three "primitives" are configurations:

    document  = ordered entity map; entities are blocks;
                the principal attribute is TEXT
    table     = ordered entity map; entities are rows;
                attributes are typed scalars and formulas
    canvas    = entity map; entities are shapes;
                attributes are geometry + TEXT; order is z-order
    slides    = ordered entity map; entities are slides;
                each slide's content is itself an entity map
    outline   = entity map with a parent attribute
    tasks     = entity map with status/date attributes
    calendar  = entity map with time attributes

The suite's apps stop being architectural categories and become *attribute
vocabularies over one algebra*. That is the result the brief was asking for.

## Why exactly two, and why text is separate

Rich text does not decompose into entities without violence. The interesting
edits inside a paragraph are intra-sequence (insert a word, bold a phrase), and
marks overlap block structure. This is the OHCO problem and Peritext exists
because of it. So text stays a leaf primitive with its own algebra rather than
being forced into the entity model.

Everything ABOVE the paragraph is entity-shaped. Everything BELOW it is
sequence-shaped. The boundary is the block.

## The merge algebra falls out for free

    entity set   -> merge by name; insert/delete/move are clean
    attribute    -> per-key; conflict only if the same key changed on both sides
    text leaf    -> three-way text merge (or a text CRDT in a live session)

This is deliberately the same shape as Automerge's map/list/text. The
convergence is a good sign. The DIFFERENCE is the important part:

    Automerge:  the model IS the storage; storage is binary and opaque
    Here:       the model is a discipline; storage is plain text

We take the CRDT's clean merge SEMANTICS without the CRDT's opacity, and pay
for it by allowing merge to fail.

## Convergence is not correctness

A CRDT guarantees that everyone ends up with the same document. It does not
guarantee that anyone wrote it. For artifacts a human is accountable for, a
forced convergence is worse than a conflict, because it is silently wrong --
the failure mode this whole design is organised against.

The resolution is a time horizon:

    within a session   (seconds, everyone is watching)  -> CRDT, always converge
    across sessions    (days, nobody is watching)       -> 3-way merge, may conflict

The algebra is chosen by whether a human is present to see the result. This
also explains why every product that picked one and applied it everywhere ended
up fighting its own model.

## Ordering needs no representation

In a text serialization, document order IS line order, and git's line merge
already handles concurrent insertion correctly (measured: result 1 of L1).
Therefore NO fractional index, NO `order:` attribute, NO sequence CRDT is
needed for the common case. Serialize entities in order and the problem
vanishes.

Fractional indices are needed only where order is genuinely an attribute
rather than a layout -- canvas z-order is the only clear case, and it is small.

This deletes a whole category of machinery that every block-based system
carries.

## What this changes about the core

The per-type contract shrinks, because parse/render no longer produce an
arbitrary Tree; they produce an ENTITY MAP. So diff and merge can be written
ONCE, generically, over entity maps -- not once per format. A new artifact kind
supplies only:

    parse   : bytes -> EntityMap
    render  : EntityMap -> bytes
    schema  : attribute names -> types

and inherits addressing, diff, merge, transclusion and derivation.

That is a much smaller core than H7, and it answers the objection that a
content-agnostic core does no real work: it does the merge, and the merge is
the hard part.
