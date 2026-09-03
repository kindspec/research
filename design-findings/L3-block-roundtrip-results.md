# L3 — the document leg: boundary-only parsing (my own work, reproducible)

`experiments/L3-block-roundtrip/`. Tests whether the entity-map model works for
prose without the reserialization catastrophe that defined the prior research.

## The trick

A parser that must RE-EMIT content needs a byte-perfect serializer, and nobody
has one: pandoc changed 42 of 53 lines on a torture file; `mdast-util-to-
markdown`'s positional Tracker "isn't used yet"; Pithy's turndown path rewrites
whole files on first touch.

A parser that only finds block BOUNDARIES needs no serializer at all. Each
block retains its raw bytes; render is concatenation. Round-trip is exact **by
construction, for every input, including inputs the parser misunderstands.**

    render(parse(b)) == b        holds trivially, not aspirationally

Measured on a 664-byte torture file (frontmatter, setext + ATX headings, three
bullet markers, two ordered-list styles, indented code, ``` and ~~~ fences with
blank lines inside, GFM table, definition list, raw HTML, hard breaks, trailing
whitespace, entities, escapes, emoji, CJK, link reference, thematic break, and
a final paragraph with NO trailing newline):

    blocks=18  bytes_in=664  bytes_out=664   ROUND-TRIP EXACT: True
    (also exact on the no-trailing-newline variant)

**This is the single most important structural result of the design.** It
converts byte-stability from a serializer-quality problem — which is unsolved —
into a parser-scope decision, which is free.

## Negative result: content-hash identity is NOT identity

First merger keyed blocks by content hash. Both sides edit the SAME paragraph:

    git merge-file      -> conflict (correct)
    hash-identity merge -> BOTH VERSIONS SILENTLY CONCATENATED

    # Beta
    Beta body text, BOB version.
    Beta body text, ALICE version.

Editing a block changes its hash, so two concurrent edits look like two
independent insertions. This is precisely the silent-wrong class the whole
design is organised against, reproduced in my own code. Recorded rather than
quietly fixed.

## The repair: similarity matching, which is what git already does

Correspond blocks to their base counterparts by exact hash first, then by
`difflib` ratio above 0.5 — the same mechanism and roughly the same threshold
git uses for rename detection. Identity is COMPUTED, not stored, so no IDs
pollute the file.

## Second refinement: a block is CONTENT plus SEPARATOR

With similarity matching alone, case B regressed: Alice MOVES a section while
Bob EDITS it. Reported a conflict where there is none — because a moved block's
raw bytes include its trailing blank line, so `ours != base` on whitespace
alone.

Fix: split each block into content and trailing separator. Identity and
three-way comparison use content only; render re-attaches the separator
appropriate to the new position.

**Generalisation: in any text serialization, separators are a property of
POSITION, not of the entity. Comparing them is a category error.** This is the
prose analogue of the alignment-row bug in L2 and of A1 references in L1 — the
same mistake in three costumes.

## Final behaviour, all three cases

    A  both sides edit the same paragraph      -> 1 conflict   (correct)
    B  one side MOVES a section, other EDITS   -> 0 conflicts, both applied
                                                  (git merge-file: CONFLICT)
    C  torture-file round-trip                 -> byte-exact

Case B is the one that matters: line-based merge conflicts on move-plus-edit,
which is among the commonest things two people do to a document. ~50 lines of
generic block merge fixes it.

## What this establishes for the design

- The document leg needs NO byte-perfect serializer and NO embedded IDs.
- The parser's only obligation is to find boundaries and never re-emit.
- Identity for merge is computed by similarity; identity for REFERENCES is a
  separate, on-demand concern. Conflating them is what broke the first merger.
