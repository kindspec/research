
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
does not supply one. Which is precisely what §9 is for.

**Three concrete mandates fall out of this section:**

    T1  NFC is the only conforming normalization for identifiers; canon()
        normalizes; non-NFC identifiers are rejected.
    T2  Identifiers are restricted to a declared code-point profile; `Cf`
        (format/invisible) characters are rejected.
    T3  Files are UTF-8, LF, no BOM -- and this is ENFORCED by the parser
        under P1, not left to .gitattributes, because .gitattributes is not
        consulted in a bare repo (R5).

---
