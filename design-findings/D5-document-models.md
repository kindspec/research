# D5 — Document and markup models for a decades-scale git-backed substrate

Research date 2026-08-28. Brief: challenge the markdown choice that `RESEARCH.md`
§2 made on *editor-architecture* grounds, on *markup-model* grounds.

Every claim below is either quoted from a primary source with a URL, or produced
by a command run locally on this machine (pandoc 3.1.11.1, `@djot/djot` 0.3.2,
node 24.15, git 2.x). Commands and their real output are shown. Claims I could
not verify are marked **UNVERIFIED**.

---

## 0. The answer, first

**Canonical artifact: a text syntax that is parsed. Not a serialized AST.
Not both-with-one-derived.**

But the syntax must be chosen for *parseability and attribute-carrying capacity*,
not for familiarity, and the substrate must stop pretending the syntax is the
model. Concretely:

1. **The canonical artifact is UTF-8 text, one document per file, hand-editable.**
   This is forced by git, not by taste — see §7, where a serialized AST loses the
   merge experiment catastrophically and the Pandoc AST loses the *archival*
   experiment outright.
2. **The in-memory/interchange model is an AST with an attribute triple on every
   node** (`id`, `classes`, `key=value`), Pandoc-shaped. The AST is a *derived,
   disposable* artifact — never committed.
3. **The syntax should be djot, not markdown — but only if you own a parser
   dependency you are willing to maintain.** See the honest risk in §3.
4. **Do not use one syntax for documents + tables + slides.** JATS learned this
   in 2003 and encoded the lesson in its architecture (§6.2). "One syntax" is a
   trap; "one *model*, several grammars" is the sound version.
5. **The tree is not sufficient.** Comments, annotations and tracked changes
   provably do not nest (§5). Anything spanning structure must live in *standoff*
   with stable IDs — which is the real reason attributes/IDs are non-negotiable,
   and the real reason markdown is disqualified rather than merely unfashionable.

---

## 1. Markdown, prosecuted

### 1.1 The author of CommonMark on CommonMark

John MacFarlane, *Beyond Markdown*, April 2018
(<https://johnmacfarlane.net/beyond-markdown.html>, originally
<https://talk.commonmark.org/t/beyond-markdown/2787>):

> "But this respect for the past has made the CommonMark spec a very complicated
> beast. There are 17 principles governing emphasis, for example, and these rules
> still leave cases undecided. The rules for list items and HTML blocks are also
> very complex. All of these rules lead to unexpected results sometimes, and they
> make writing a parser for CommonMark a complex affair. **I despair, at times, of
> getting to a spec that is worth calling 1.0.**"

He then enumerates six structural defects. Verbatim highlights:

- **Emphasis.** `**this* text**` "is consistent with both of these readings"; a
  run of `***` mid-word "might be any of the following" — he lists **eight**
  possible parses.
- **Reference links.** "The usual treatment of reference links makes it
  impossible to classify any syntax element until the whole document has been
  parsed… This makes syntax highlighting very difficult, and it also complicates
  writing parsers. For example, you can't parse links, then resolve references in
  the AST after the document is parsed."
- **Indented code + lists.** "most of the complexity in the rules for list items
  is motivated by the need to deal with indented code blocks."
- **Raw HTML.** "how do we identify the end of an HTML block? Given that tags can
  be nested, this requires nontrivial HTML parsing… But the result is rather
  complex: seven distinct pairs of start and end conditions."
- **Lists and blank lines.** CommonMark's rule violates its own "principle of
  uniformity"; they mitigated "with an ugly heuristic (we only allow an ordered
  list to interrupt a paragraph when the list number is 1)."
- **Attributes.** "**Markdown offers no general way to add attributes** (such as
  classes or identifiers) to elements. This deprives it of a native way of
  creating internal links to sections of a document… It also deprives it of a
  **natural extension mechanism**… Currently, though, the only way to attach
  attributes to an element is to drop down to raw HTML."

That last one is the one that matters for this substrate. **Markdown has no
stable-identity mechanism and no extension mechanism, and its own designer says
so.** Everything downstream — anchors, comments, transclusion, per-block
provenance — has to be bolted on out of band.

### 1.2 Measured: the spec never converged

<https://spec.commonmark.org/> lists every release. Verified by fetch:

```
Latest version (0.31.2) (2024-01-28)
0.30 (2021-06-19) · 0.29 (2019-04-06) · 0.28 (2017-08-01) …
0.5 (2014-10-25)
```

**Twelve years from 0.1 to today; still 0.x; last release 2 years 7 months ago.**
For a format meant to hold your organisation's memory for decades, the incumbent's
spec has neither reached 1.0 nor been touched since January 2024.

The ambiguity is quantifiable. From the machine-readable conformance suite:

```
$ curl -sL https://spec.commonmark.org/0.31.2/spec.json | python3 -c "..."
CommonMark 0.31.2 conformance examples: 652
[('Emphasis and strong emphasis', 132), ('Links', 90), ('List items', 48),
 ('HTML blocks', 44), ('Fenced code blocks', 29), ('Setext headings', 27),
 ('Link reference definitions', 27), ('Lists', 26)]
```

**132 of 652 conformance tests — 20% of the entire spec's test surface — exist to
pin down what `*` and `_` mean.**

### 1.3 The extensibility non-model, and the fatal archival consequence

Every extension is a fork. Measured locally, inside a *single tool*:

```
$ pandoc --list-extensions | wc -l
73
$ pandoc --list-extensions=markdown  | grep -c '^+'   # on by default
46
$ pandoc --list-extensions=gfm       | grep -c '^+'
12
$ pandoc --list-extensions=commonmark| grep -c '^+'
1
```

Pandoc alone defines **73 boolean markdown extensions**, and its three built-in
"markdown" dialects differ by ~45 of them. The diff between `markdown` and `gfm`
defaults includes `bracketed_spans`, `header_attributes`, `fenced_divs`,
`grid_tables`, `definition_lists`, `citations`, `raw_attribute`, `link_attributes`
— i.e. **precisely the features you would need for a semantic substrate are
dialect-dependent.**

Concrete incompatibilities across the wider family:

| Dialect | Breaks CommonMark how |
|---|---|
| **GFM** | Adds tables/strikethrough/tasklists/autolinks. GFM tables cannot express cell spans, block content in a cell, or captions (demonstrated in §4.2). |
| **MDX** | *Removes* CommonMark features. Its docs: "Indented code does not work in MDX"; autolinks disabled because "they can be indistinguishable from JSX (for example: `<svg:rect>`)"; HTML replaced by JSX so `<img>` must be `<img />`; **"HTML comments" are unavailable**; `<` and `{` must be escaped. (<https://mdxjs.com/docs/what-is-mdx/>) Valid MDX is *not* valid markdown. |
| **Markdoc** (Stripe) | "largely a superset of the CommonMark specification", except setext headings. Its own FAQ says the org is "seriously considering" formalising the AST's JSON representation — i.e. **it is not formalised**. (<https://markdoc.dev/docs/faq>) |
| **MyST** | Imports reStructuredText's roles/directives wholesale onto markdown syntax. |
| **Obsidian** | `[[wikilinks]]`, `![[embeds]]`, `> [!callout]`, block refs `^id`. None portable. |
| **Pandoc-markdown** | 73 switches; `#`-heading attributes, fenced divs, bracketed spans, grid tables — none of which GFM parses. |

**Now the fatal part.** The IETF's own guidance document for `text/markdown` —
RFC 7764, *Guidance on Markdown: Design Philosophies, Stability Strategies, and
Select Registrations*, March 2016, <https://www.rfc-editor.org/rfc/rfc7764.txt> —
addresses exactly the question "can a markdown file declare its own dialect?" and
answers **no**:

> "there is no such thing as 'invalid' Markdown, there is no standard demanding
> adherence to the Markdown syntax, and there is no governing body that guides or
> impedes its development." (§1.2)

> "tagging Markdown internally is simply out of the question. Once tags or
> metadata are introduced, the content is no longer 'just' Markdown.
>
> Some commentators have suggested that an in-band signaling mechanism, such as
> in Markdown link definitions at the top of the content, could be used to signal
> the variant. Unfortunately, this signaling mechanism is incompatible with other
> Markdown variants (e.g., [PANDOC]) that expect their own kinds of metadata at
> the top of the file. **Markdown content is just a stream of text; the semantics
> of that text can only be furnished by context.**" (§2)

The RFC's recommended workarounds are all *out of band*: a MIME `variant`
parameter; a filename convention ("a file could be named
`example.pandoc.markdown`"); or filesystem extended attributes / alternate data
streams / resource forks.

**This is the disqualifying fact for a decades-scale archive.** A `.md` file
recovered from a git repo in 2046 carries no in-band statement of which of the
eight IANA-registered (and dozens of unregistered) grammars it was written in.
The RFC's own answer is "put it in the filename or an xattr" — a convention git
does not preserve for xattrs and which no tool enforces. Every other format in
this report — TEI, JATS, DITA, DocBook, ODF, OOXML, djot, Typst — declares its own
grammar in-band or by a mandatory root element/version. Markdown alone cannot.

### 1.4 The round-trip problem, measured

`RESEARCH.md` §2 reported this from a prior pass. Independently reproduced here on
a 43-line torture file (`design-findings/../scratch d5/t.md`):

```
$ pandoc -f markdown -t markdown t.md > rt1.md
changed lines: 46  of 43
```

What changed, verbatim from the diff:

- **YAML frontmatter (`title`, `author`) silently deleted** — parsed into `meta`,
  never written back.
- `_italic_` → `*italic*`; `* item` → `-   item`; `1.` → `1.  `
- Reference link `[link][ref]` → inlined `[link](https://example.com "Title")`,
  and the `[ref]: …` definition deleted.
- The pipe table → pandoc's *simple table* syntax (a different table syntax
  entirely).
- The blockquote's hard line break was reflowed onto one line.
- ` ```python ` → ` ``` python `
- `<!-- comment -->` → a ` ```{=html} ` raw block; `<div class="raw">` → a
  pandoc fenced div `::: raw`.

`gfm → gfm` is better but still **28 of 43 lines changed**, still deletes the
frontmatter, still inlines the reference link, still drops the definition list.

There is no "just configure the serializer" escape. This is the same conclusion
`RESEARCH.md` reached, now with the mechanism named: **the writer serializes the
AST, and the AST does not remember the syntax.**

---

## 2. What markdown *cannot represent* — the decisive experiment

The strongest single argument in this report. Pandoc's AST has been able to
represent merged table cells since the Table type rewrite (pandoc 2.10). Test:

```
$ cat span.html
<table>
<tr><td rowspan="2">A</td><td colspan="2">B</td></tr>
<tr><td>C</td><td>D</td></tr>
</table>
```

The AST is faithful:

```
$ pandoc -f html -t native span.html
… Cell ("",[],[]) AlignDefault (RowSpan 2) (ColSpan 1) [Plain [Str "A"]]
  Cell ("",[],[]) AlignDefault (RowSpan 1) (ColSpan 2) [Plain [Str "B"]] …
```

and HTML → AST → HTML is exact (`rowspan="2"`, `colspan="2"` preserved).

Now serialize through *any* markdown:

```
$ pandoc -f html -t gfm span.html
|     |     |     |
|-----|-----|-----|
| A   | B   |     |
|     | C   | D   |

$ pandoc -f html -t commonmark_x span.html     # identical
$ pandoc -f html -t markdown span.html         # pandoc's own grid/simple tables
  --- --- ---
  A   B
      C   D
  --- --- ---
```

Round-trip through markdown and back:

```
$ pandoc -f html -t markdown span.html | pandoc -f markdown -t html
<tr><td>A</td><td>B</td><td></td></tr>
<tr><td></td><td>C</td><td>D</td></tr>
```

**The merged cells are gone. Silently. And the resulting table is not a degraded
version of the original — it is a *different table with different data*:** an
empty cell has appeared under `A`, `B` now occupies one column instead of two,
and no warning was emitted on either leg.

This is the markup-model analogue of the A1-reference merge corruption in
`RESEARCH.md` §3: *not a diff-quality problem, a silent-wrongness problem*. Any
office suite whose canonical form is markdown cannot represent a merged table
cell — which is table stakes for the "Docs" leg, let alone the "Sheets" leg.

Corollaries that fall out of the same gap: no captions on tables, no block content
in cells, no figure/caption association, no column widths, no cell-level ids for
comments to anchor to.

---

## 3. Djot — the successor, assessed honestly

Djot is jgm's own implementation of *Beyond Markdown*. Repo
<https://github.com/jgm/djot>, site <https://djot.net/>, MIT.

### 3.1 What it fixes (and it genuinely does fix them)

From the README's Rationale, the design goals are exactly the six defects above:
linear-time parsing with **no backtracking**; **local** inline parsing independent
of later reference definitions; `_` for emphasis and `*` for strong so the
doubled-delimiter ambiguity vanishes; **no expressive blind spots**; no indented
code blocks; raw HTML only in explicitly marked contexts; **arbitrary attributes
on any element**; **generic containers** for extensibility.

From the syntax reference (<https://github.com/jgm/djot/blob/main/doc/syntax.md>):

> "As in commonmark, block structure can be discerned prior to inline parsing and
> takes priority over inline structure. Indeed, **blocks can be parsed line by
> line with no backtracking. The contribution a line makes to block-level
> structure never depends on a future line.**"

That property alone is worth a great deal for an incremental editor over a
CodeMirror buffer: it means a block-level reparse is bounded.

Attributes, verbatim:

> "**Inline attributes.** Attributes are put inside curly braces and must
> *immediately follow* the inline element to which they are attached (with no
> intervening whitespace)."
>
> "**Block attributes.** To attach attributes to a block-level element, put the
> attributes on the line immediately before the block."

```
{#water}
{.important .large}
Don't forget to turn off the water!
```

Plus: `%comments%` inside attribute braces (a *real* comment syntax that survives
non-HTML output — markdown has none, it borrows HTML's, and MDX removed even
that); `::: div` generic containers; `[span]{.cls}`; raw blocks with `{=format}`;
and implicit `section` wrappers around headings, which markdown does not have at
all (`t.md` parsed to a flat block list; the same document in djot parsed to a
`section` containing a `heading`).

Verified locally, djot's AST:

```
$ node -e '…d.parse(src)…'
VERSION 0.3.2
section children tags: heading,para,para,bullet_list,ordered_list,table,
                       block_quote,div,code_block
bullet_list attrs: {"id":"mylist","class":"compact"}
div attrs: {"class":"note"}
references: {"ref":{"tag":"reference","label":"ref",
                    "destination":"https://example.com"}}
footnotes: [ '1' ]
```

Note `table` is a first-class AST node with a `caption` node type, and the node
type list includes `insert`, `delete`, `mark` (i.e. tracked-change and
highlight *inlines*, natively) — 60 node types total, all attribute-bearing.

### 3.2 What I found wrong with it, empirically

**(a) The djot writer is not byte-stable and not idempotent.** Same test as §1.4:

```
=== ROUNDTRIP src==out? false
=== IDEMPOTENT out==out2? false
changed lines: 20 of 36
```

The idempotency failure is a **trailing-whitespace bug**: pass 1 emits
`# Heading with _emphasis_ ` (trailing space), pass 2 strips it. Tables are
reflowed from aligned to minimal (`| Bolt  |    10 |` → `|Bolt|10|`). `::: note`
is rewritten to `{.note}\n:::`. Footnote and reference definitions are reordered
to the end. So djot buys you nothing over markdown on round-trip — which
*reinforces* `RESEARCH.md` §2's decision (the editor buffer must be the file;
never serialize on save) rather than undermining it.

**(b) Silent attribute loss on the most natural authoring mistake.** This is the
sharpest practical finding about djot:

```
### attrs on line before heading  input="{#intro .lead}\n# Heading\n"
doc → section ATTR={"id":"intro","class":"lead"} → heading → str     ✓ correct

### attrs trailing after space   input="# Heading {#intro}\n"
doc → section → heading → str                                        ✗ ID GONE
   render->"# Heading \n"

### attrs trailing no space      input="# Heading{#intro}\n"
doc → section → heading → str ATTR={"id":"intro"}                    ✗ WRONG NODE
```

`# Heading {#intro}` is the pandoc/kramdown habit every markdown author has.
In djot it is spec-conformant to drop it — the attribute doesn't immediately
follow an inline — and djot.js **drops it with no diagnostic, and re-emits the
file with a trailing space where the ID used to be.** The no-space form attaches
the ID to the `Str` inline rather than the heading, which is semantically wrong
and equally silent. For a substrate whose whole premise is stable identity, an
ID mechanism with a silent-failure mode is a hazard that must be met with a
linter, not with trust.

**(c) There is no formal grammar.** `grep -icE "grammar|BNF|EBNF|production"` over
`doc/syntax.md` returns **0**. Djot's spec is prose plus examples, exactly like
CommonMark's. It is a *simpler* informal spec, not a formal one. Do not buy djot
believing you are buying a grammar.

**(d) djot.net's own status line:** "Djot isn't completely stable yet, minor
future changes to the syntax are expected."

### 3.3 The ecosystem risk, quantified

This is where the decision actually gets made. Measured 2026-08-28:

| | stars | last push | downloads |
|---|---|---|---|
| `jgm/djot` (spec) | 2,033 | 2026-07-01 | — |
| `jgm/djot.js` (reference impl) | 206 | 2026-08-19 | **1,332/week (npm)** |
| `jgm/djot.lua` | 80 | 2026-04-27 | — |
| `hellux/jotdown` (Rust) | 229 | 2026-08-13 | 123,026/90d (crates.io) |
| — vs — | | | |
| `marked` | — | — | **71,970,387/week** |
| `remark-parse` | — | — | **50,948,894/week** |
| `markdown-it` | — | — | **30,053,020/week** |
| `pulldown-cmark` (Rust) | — | — | 42,424,827/90d |

**@djot/djot: 1,332 weekly npm downloads against remark's 50.9 million. A ratio
of 1 : 38,250.** In Rust, jotdown vs pulldown-cmark is 1 : 345.

`@djot/djot@0.3.2` was last published **2024-12-19** (npm `time.modified`) — 20
months stale — even though the git repo is active. Zero runtime dependencies
(good), MIT (good), 118 open issues on the spec repo.

Bus factor: the spec, the JS reference implementation, and the Lua implementation
are all jgm. The Rust, Go, PHP, Prolog and Haskell ports are single-maintainer
side projects. Pandoc has been jgm for 16 years and is fine — but pandoc has
46,052 stars and institutional adoption; djot.js has 206.

**No production adopter found.** I could not identify a shipping note app, static
site generator, or documentation platform whose primary format is djot.
**UNVERIFIED** as an absence — I searched but a negative is hard to prove.

### 3.4 Verdict on djot

**Djot is right and markdown is wrong, on the merits, and jgm's own six-point
indictment is the proof. But djot is not a format you can bet a decades-scale
archive on in 2026 — 1,332 weekly downloads is not an ecosystem, it is a
prototype with a famous author.**

The resolution is that **you don't have to choose the ecosystem — you choose the
syntax and own the parser.** djot.js is MIT, zero-dependency, ~7k LOC, with a
complete AST and a published test suite; jotdown is MIT Rust. Vendoring one of
these is a smaller and *far* better-specified maintenance liability than
maintaining a markdown dialect (which is what you are doing the moment you add
wikilinks, callouts, or `.sheet.md` tables — see §8).

The mitigating fact that makes this survivable: **djot's AST is close enough to
pandoc's that mechanical conversion exists in both directions** — djot.js exports
`fromPandoc` and `toPandoc` (verified in `types/index.d.ts`). So a djot corpus is
one `pandoc` invocation from being a markdown corpus, forever. The lock-in is
bounded.

---

## 4. Pandoc's AST as the universal model

### 4.1 What it is

`pandoc -t json` emits `{"pandoc-api-version":[1,23,1],"meta":{…},"blocks":[…]}`.
The model is ~20 `Block` and ~20 `Inline` constructors, and crucially an
`Attr = (id, [class], [(key,val)])` triple on `Header`, `Div`, `Span`, `Code`,
`CodeBlock`, `Link`, `Image`, `Table`, `Row`, `Cell`, `Figure`. Verified:

```
$ printf '# H {#id .cls key=val}\n\nText with [span]{.warn}.\n' | pandoc -t native
[ Header 1 ( "id" , [ "cls" ] , [ ( "key" , "val" ) ] ) [ Str "H" ]
, Para [ …, Span ( "" , [ "warn" ] , [] ) [ Str "span" ], … ] ]
```

It reads 38 formats and writes 60 (`pandoc --list-input-formats` / `-output-`).
As a *lingua franca* it is unmatched and should absolutely be the interchange
model.

### 4.2 What it cannot represent

Documented gaps, ordered by how much they matter here:

1. **Comments and annotations.** There is no `Comment` node and no annotation
   node. `--track-changes=accept|reject|all` on the docx reader is a *reader
   flag*, not a model feature: it resolves revisions at parse time. Word comments
   are dropped by default. There is nowhere in the AST to put "this range is
   commented by Bob".
2. **Anything spanning a block boundary.** `Span` is an `Inline`; it cannot cross
   `Para`. This is the OHCO problem (§5) and it is structural, not an oversight.
3. **Layout and presentation.** No pages, columns, floats, positioning, or
   explicit breaks. `ColWidth` is the only geometry in the model.
4. **Bidirectional fidelity to OOXML/ODF.** Numbering definitions, styles as
   first-class objects, fields, content controls, section properties — all lost.
5. **Source positions.** Not in the AST (readers can attach them via extensions,
   but they are not part of the committed model).

### 4.3 The archival killer: `pandoc-api-version` refuses to load old ASTs

Tested:

```
$ python3 -c "…set pandoc-api-version to [1,22,2]…"; pandoc -f json -t plain t_old.json
JSON parse error: Error in $: Incompatible API versions:
  encoded with [1,22,2] but attempted to decode with [1,23,1].

$ …[1,23,0]…   →  parses fine
$ …[1,24,0]…   →  Incompatible API versions
```

**A Pandoc JSON AST written by pandoc 2.14 (pandoc-types 1.22, 2021) is a hard
parse error in pandoc 3.1.11 today.** The tolerance window is exactly
`major.minor`; the patch component is free. pandoc-types has shipped 1.20, 1.21,
1.22, 1.23 (hackage version list, verified) — roughly one AST-format break every
18 months, each one *refusing* rather than degrading.

Compare TEI (P1 1990 → P5, still parseable by any XML tool), JATS (NLM DTD 1.0
2003 → NISO 2015, still parseable), or plain text (parseable forever).

**Therefore: "the Pandoc AST is the canonical stored form" is not viable for a
decades-scale archive.** It is an excellent *runtime* model and an excellent
*interchange* model. Committing `.json` ASTs to git buys you a corpus that needs
a version-matched binary to open. That is the OOXML problem with extra steps.

---

## 5. OHCO — the finding that constrains everything else

### 5.1 The thesis and its authors' own retraction

DeRose, Durand, Mylonas & Renear (1990) proposed **OHCO-1: "Text is an ordered
hierarchy of content objects."** Three years later the same authors published the
refutation: Renear, Mylonas & Durand, *Refining our Notion of What Text Really Is:
The Problem of Overlapping Hierarchies* (ALLC/ACH92; Oxford UP, 1996). Full text:
<https://xml.coverpages.org/ohco1.html>.

They weaken it twice and it still fails:

> "**OHCO-1: Text is an ordered hierarchy of content objects.**" … "OHCO-1 is
> false."

> "**OHCO-2: An analytical perspective on a text determines an ordered hierarchy
> of content objects.**"

> "**OHCO-3: For every distinct pair of objects x and y that overlap in the
> structure determined by some perspective P(1), there exists diverse perspectives
> P(2) and P(3)…** (or: objects may overlap in a perspective, but if they do then
> they belong to different sub-perspectives of that perspective)"

> "Unfortunately **even OHCO-3, the weakest version of the OHCO thesis … does not
> seem immune from counterexample.**"

Their list of counterexamples — objects that overlap *with themselves*, so no
re-classification can save the tree — is worth reading as a requirements document
for this product:

> - "Text critical objects such as **strike outs and variant readings**"
> - "Narrative objects such as stories"
> - "Reference structures such as **hypertext link anchors and targets**"
> - "Poetic objects such as tropes and allusions"
> - "Discourse objects such as topics"
> …and discontiguous objects: "Lists broken across paragraphs", "Songs or choral
> odes broken across other text"

Their conclusion, verbatim:

> "4. Perspectives do not always determine hierarchies
>  5. Non-hierarchical perspectives cannot always be decomposed into hierarchical
>     sub-perspectives"

**Translate to this product: "strike outs and variant readings" is *tracked
changes*. "Hypertext link anchors and targets" is *comments and annotations*.
The 1993 paper names, as its two leading counterexamples to the tree model of
text, the two features that every office suite must ship.**

### 5.2 Demonstrated, in the substrate's own terms

A comment anchored from mid-paragraph-1 to mid-paragraph-2:

```
$ cat ohco_try.md
The first paragraph [ends here.

And the second]{.comment ref=c1} paragraph begins here.

$ pandoc -f markdown -t native ohco_try.md
[ Para [ …, Str "[ends", Space, Str "here." ]
, Para [ …, Str "second]{.comment", Space, Str "ref=c1}", … ] ]
```

The bracketed span is **not parsed at all** — it degrades to literal text, no
error. Try raw HTML instead:

```
$ pandoc -f markdown -t html ohco_try2.md
<p>The first paragraph <span class="comment">ends here.</p>
<p>And the second</span> paragraph begins here.</p>
```

**Non-well-formed output.** The `<span>` and `<p>` tags cross. This is not a
pandoc bug; it is the OHCO problem arriving on schedule.

### 5.3 What TEI does about it, after 30 years

TEI Guidelines, ch. "Non-hierarchical Structures"
(<https://tei-c.org/release/doc/tei-p5-doc/en/html/NH.html>). Its own summary:

> "no current solution combines all the desirable attributes of formal
> simplicity, capacity to represent all occurring or imaginable kinds of
> structures, suitability for formal or mechanical validation."

> "representation of non-hierarchical information is thus necessarily a matter of
> trade-offs."

The five mechanisms and TEI's own stated costs:

| Mechanism | Cost, per the Guidelines |
|---|---|
| **Milestones** (`<lb/>`, `<pb/>`, `<milestone/>`) — empty markers, no containment | "meaning of the milestone elements must be preserved" (they carry no structure a validator can check) |
| **Fragmentation** (`@part="I\|M\|F"`) | creates "more elements claiming to represent a feature than there are actual instances" and "can be semantically misleading" |
| **Virtual joins** (`<join>`) | "privileges one hierarchy over the others, requires special processing" |
| **Redundant encoding** | "requires maintenance of multiple copies of identical textual content"; no "explicit indication that the various views…are related" |
| **Stand-off markup** (`<standOff>`) | "information may be difficult to access using generic methods" |

**TEI makes no recommendation.** After three decades and the deepest thinking
anyone has done about representing text, the answer is "pick your poison."

Related prior art worth knowing exists: SGML's `CONCUR` feature (multiple
concurrent hierarchies — cited in the OHCO paper as the hoped-for fix; it was
essentially never implemented), and Huitfeldt & Sperberg-McQueen's **GODDAG**
(Generalized Ordered-Descendant Directed Acyclic Graph) / **TexMECS**, which
replace the tree with a DAG so ranges may overlap. **UNVERIFIED in detail** — I
did not read the GODDAG papers in this pass; flagging as the highest-value
follow-up reading if annotations become a headline feature.

### 5.4 What OHCO forces on this design

1. **The tree is the right model for the 90% and provably wrong for the rest.**
   Do not try to fix the syntax. Every attempt (fragmentation, joins, redundant
   encoding) is worse than the standoff answer, and TEI says so.
2. **Comments, annotations, suggestions and tracked changes MUST live outside the
   document tree**, in a standoff layer, anchored by stable IDs into it. This is
   not an implementation convenience; it is forced by a 1993 proof.
3. **Therefore stable per-block identity in the canonical text is mandatory, not
   optional.** A standoff layer needs something to point at. Markdown cannot
   provide it (§1.1). Djot can (`{#id}`), org can (`:ID:`), TEI does
   (`@xml:id`), Portable Text does (`_key`).
4. **Sub-block anchoring needs a fallback.** Character offsets into a mutable file
   rot on every edit. The realistic design is *block ID + quoted anchor text +
   offset hint*, re-resolved fuzzily on load, degrading to "orphaned comment on
   block X" rather than to silence. (This is what Google Docs, Hypothesis and
   every annotation system converges on. **UNVERIFIED** as to their exact
   algorithms in this pass.)
5. **A standoff layer is a separate file, and that is a feature**: it can be
   `.gitignore`d, permissioned separately, or synced through a different channel
   — which matters given `RESEARCH.md` §4's single-writer constraint and §6's
   finding that no forge has per-file read ACLs.

---

## 6. What the archival formats already learned

### 6.1 TEI — 36 years, and the extensibility model that works

TEI P1 1990 → P5 2007 → still released. Its extensibility mechanism, **ODD** ("One
Document Does it all"), is the thing to steal conceptually: a customization is
itself a TEI document that *declares* which modules and elements are in play, and
from which a schema (RELAX NG / DTD / XSD) and documentation are both generated.
The result: **a TEI file states, in band, which grammar it conforms to, and that
grammar is machine-checkable.** That is precisely what RFC 7764 says markdown can
never do.

TEI also gives every element `@xml:id`, and has `<app>`/`<rdg>` for variant
readings — a *native* model for "this text has two versions", i.e. tracked
changes as first-class data rather than as an editor feature.

### 6.2 JATS — the lesson that kills "one syntax for everything"

JATS is ANSI/NISO Z39.96, mandated by PubMed Central. It ships **three tag sets**
over one model (<https://jats.nlm.nih.gov/archiving/rationale.html> and the
Publishing/Authoring rationales):

- **Archiving & Interchange ("Green")** — the most *permissive*. Its intent is
  "to provide a single format into which content from many providers can be
  translated easily. This focus on being a conversion target for multiple sources
  has made this Tag Set a large and inclusive one."
- **Journal Publishing ("Blue")** — "tighter rules than Green about what a valid
  document must contain… the model includes fewer elements and tagging choices…
  and imposes element sequence more often."
- **Article Authoring ("Orange"/"Pumpkin")** — the most *restrictive*: "designed
  to allow as few tagging options as possible while enabling the expression of
  the full content of a journal article."

**This is the direct, load-bearing answer to "is one syntax for documents +
tables + slides sound?"**

It is not. What JATS shows is that **the archival grammar and the authoring
grammar have opposite objectives** — one must accept everything, the other must
permit as little as possible — and that the sound architecture is *one model,
several grammars, each validated*. Trying to make a single syntax do both jobs is
how you get markdown: permissive enough to be un-validatable, restrictive enough
to be un-expressive, and with no way to tell which you are holding.

### 6.3 DITA — the best extensibility mechanism in the field

DITA's `@class` specialization (OASIS DITA 1.3 §2.5.3.6, "class attribute rules
and syntax", <https://docs.oasis-open.org/dita/dita/v1.3/errata02/os/complete/part2-tech-content/archSpec/base/specialization-class-attribute.html>):

> "A sequence of one or more tokens of the form `"modulename/typename,"` with each
> token separated by one or more spaces"
> "Use `-` for element types that are defined in structural vocabulary modules,
> and use `+` for element types that are defined in domain modules."
> "**Tokens are ordered left to right from most general to most specialized.**"
> "At least one trailing space character. The trailing space ensures that string
> matches on the tokens can always include a leading and trailing space in order
> to reliably match full tokens."

Literal examples from the spec:

```xml
<!ATTLIST step class CDATA "- topic/li task/step ">
<wintitle  class="+ topic/keyword ui-d/wintitle ">A specialized keyword</wintitle>
<windowname class="- topic/keyword task/keyword guitask/windowname ">…</windowname>
```

**Read that first line carefully. A processor that has never heard of `<step>`
reads `- topic/li task/step ` and knows, from the document itself, that a `step`
IS-A `li`. It renders it as a list item.** Unknown extensions degrade gracefully
and *automatically*, with no registry, no negotiation, and no version handshake —
because the ancestry travels in-band with every element.

This is the single most transferable idea in the entire report. It is exactly what
markdown-world has failed to invent for twenty years: markdown's answer to an
unknown extension is "render the raw source as literal text" or "crash."

**Adoption reality, verified.** The OASIS standards index
(<https://www.oasis-open.org/standards/>) lists DITA v1.0 (approved 01 May 2005),
v1.1 (01 Aug 2007), v1.2 (01 Dec 2010) and **v1.3 (17 Dec 2015)**. There is no
approved DITA 2.0 on that page. **DITA's most recent approved OASIS Standard is
over ten years old.** Borrow the mechanism; do not mistake it for a growing
ecosystem. (The same index carries a further irony: several OASIS deliverables
are now published with "Editable source (md)" / "Editable source (markdown)" —
the standards body that gave us DITA and DocBook authors some of its own
specifications in markdown.)

Djot's generic containers give you the *hook* for this — `::: warning` is a `div`
with `class="warning"` and any processor knows a div is a div. The missing piece
is the *ancestry*: `{.callout .admonition .blockquote}` as an ordered
general→specific class list, with a linter enforcing that every custom class
declares its base. **That is a cheap, in-band, tool-agnostic extension mechanism
you can adopt on day one.**

DITA also contributes **keyref/keys indirection** — references resolve through a
key defined in a map, so reorganising files does not break links. Direct prior art
for "stable identity survives reorganisation".

### 6.4 ODF / OOXML as archival formats

Both are ZIP containers of XML, which is the wrong shape for git (`RESEARCH.md`
§3 already established `.fods` — the *flat*, single-file ODF variant — gets
cell-level three-way merge free from stock git at +26% repo size, where `.xlsx`
costs 3.8×). The flat variants (`.fodt` / `.fods` / `.fodp`) are the archival
sweet spot: real XML in one file, diffable, and written by LibreOffice.

ODF's lineage, verified from the OASIS standards index: ODF **1.2** and ODF
**1.3** (Committee Specification 01, 25 December 2019, edited by Patrick Durusau,
four parts — Introduction, Packages, Schema, and **Part 4: Recalculated Formula
(OpenFormula)**). That fourth part matters directly for the Sheets leg: ODF is the
only mainstream office format with a *separately specified, publicly standardised
formula language*, which is what makes `.fods` a credible fidelity escape hatch
rather than merely a diffable blob.

OOXML's ISO/IEC 29500 **Strict vs Transitional** split is the cautionary tale:
Transitional exists to encode legacy binary-Word behaviours and was explicitly
meant to be deprecated, yet remained the practical default for over a decade.
**UNVERIFIED for 2026**: I did not confirm what Word's current default is, or
fetch the Library of Congress format-sustainability assessments for ODF and
OOXML. Flagged as follow-up.

The lesson that *is* verified and transferable: **a format that ships a
"compatibility" mode alongside its "correct" mode will find that everything is
written in the compatibility mode forever.** Do not ship a legacy dialect switch.

### 6.5 DocBook

Long-lived (1991–), large element vocabulary, OASIS-maintained, and now largely
superseded in its niche by DITA (enterprise) and markdown/AsciiDoc (software
docs). Verified from the OASIS standards index: the most recent **approved OASIS
Standard** is **DocBook v5.0, approved 01 Nov 2009** (v4.5 in 2006, v4.1 in
2001). Later 5.x revisions exist only at Committee Specification stage. Its
durable contribution is the same one as TEI's: a *validated* semantic vocabulary
with no presentation in it — but as a living ecosystem it is finished.

---

## 7. THE CENTRAL QUESTION: syntax, serialized AST, or both?

### 7.1 The merge experiment — the decisive evidence

I built the same three-paragraph document as (a) markdown and (b) Portable Text
JSON (pretty-printed, `_key` on every block and span), then ran the concurrent
edits git will actually see.

**Case 1 — one-word edit, far apart.** Both fine:

```
one-word edit: PORTABLE TEXT   changed lines: 2  (of 72)
one-word edit: MARKDOWN        changed lines: 2  (of  9)
```

**Case 2 — insert a paragraph.** JSON pays the structural tax:

```
PT changed lines: 14 of 72     MD changed lines: 2 of 9
```

**Case 3 — the real test. Two branches each insert a block at the same
position, then merge:**

```
$ git merge B
Auto-merging doc.json
CONFLICT (content): Merge conflict in doc.json
Auto-merging doc.md
CONFLICT (content): Merge conflict in doc.md
```

Both conflict — correct in both cases. But look at *what a human has to resolve*:

```markdown
Paragraph 1.

<<<<<<< HEAD
Insert from alice.
=======
Insert from bob.
>>>>>>> B

Paragraph 2.
```

versus

```json
  {
    "_type": "block",
<<<<<<< HEAD
    "_key": "alice",
=======
    "_key": "bob",
>>>>>>> B
    "style": "normal",
    "markDefs": [],
    "children": [
      {
        "_type": "span",
<<<<<<< HEAD
        "_key": "s_alice",
        "marks": [],
        "text": "Insert from alice."
=======
        "_key": "s_bob",
        "marks": [],
        "text": "Insert from bob."
>>>>>>> B
      }
    ]
  },
```

```
### is doc.json parseable? ###
json.decoder.JSONDecodeError: Expecting property name enclosed in double quotes:
  line 18 column 1 (char 259)
```

**Git's line-matcher aligned the JSON *scaffolding* — `{`, `"_type": "block",`,
`"style": "normal",` — and split ONE logical insertion into TWO independent
conflict hunks inside a single block.** The obvious "keep both" resolution
produces a block with Alice's `_key` and Bob's text. The file does not parse until
resolved. And unlike markdown, you cannot resolve it in the product's own editor,
because the product's editor cannot open an unparseable file.

**This is the general law: the boundaries a line-based merger can see are the
boundaries of the *serialization*, and in a serialized AST those boundaries do not
coincide with the boundaries of the *structure*.** In a text syntax they very
nearly do — a paragraph is a paragraph is a line-run.

Every serialized-AST format inherits this. It is not fixable by pretty-printing;
pretty-printing is what *created* the misalignment (it manufactured shared lines
for git to match on). Minified JSON is worse: one line, every change is a
whole-file conflict.

### 7.2 The tradeoff table

| | (a) Text syntax, parsed | (b) Serialized AST (JSON/XML/sexp) | (c) Both, one derived |
|---|---|---|---|
| **Diff** | Excellent; hunks are semantic units | Poor→OK; 7× line amplification measured (14 vs 2) | Worst: two diffs per change, one meaningless |
| **Merge** | Conflicts are legible and editable in-product | **Conflicts split logical units; result is unparseable** (measured §7.1) | Undefined — which side wins? |
| **Human editing** | The file IS the buffer; no serializer in the save path (`RESEARCH.md` §2) | Not hand-editable; forces a projectional editor (§8) | Derived file drifts; the classic `.pyc` problem |
| **Tooling** | grep, sed, ripgrep, every editor, every LLM | Needs the schema and a version-matched reader | Two toolchains |
| **Extensibility** | The hard problem — needs attributes + ancestry (§6.3) | Trivial: add a field | Trivial in AST, undefined in text |
| **Evolution / archive** | Best: text is readable in 2046 with no software | **Worst: pandoc refuses ASTs one minor version old (§4.3)** | Inherits the AST's fragility |
| **Expressiveness** | Bounded by the syntax (markdown fails §2; djot mostly passes) | Unbounded | Bounded by the text leg anyway |

### 7.3 Real systems that chose each, and what went wrong

- **(a) Text syntax — org-mode.** Won on longevity and ubiquity of tooling. Lost
  on interoperability: the syntax grew to 40 constructs and the spec became
  descriptive of one implementation (§9).
- **(a) Text syntax — markdown.** Won everything, then discovered it cannot carry
  attributes, cannot declare its dialect (§1.3), and cannot represent a merged
  table cell (§2).
- **(b) Serialized AST — JetBrains MPS.** Stores models as XML and consequently
  **ships its own diff and merge tooling**, because standard text tools are
  unusable on them. That is the whole projectional-editing story in one sentence:
  the moment your canonical form is a serialized tree, you inherit responsibility
  for the entire version-control stack. **UNVERIFIED**: I could not fetch the MPS
  documentation page to quote it directly; the claim that MPS ships its own
  merge driver is from memory and should be re-verified.
- **(b) Serialized AST — Pandoc JSON.** Refuses to load across minor versions
  (§4.3, measured).
- **(b) Serialized AST — Portable Text.** The best-designed one, and still
  **"v0.0.1 - WORKING DRAFT"** on its own README after seven years
  (<https://github.com/portabletext/portabletext>). See §8.1.
- **(c) Both — Pithy.** `RESEARCH.md` §1 documents the outcome: markdown file →
  HTML → Tiptap → `getHTML()` → turndown → markdown file, with no reconciler, so
  first touch rewrites the whole file. The derived form won and the canonical form
  became a lossy projection of it.
- **(c) Both — Nextcloud Text.** Six years, a hand-maintained `keepSyntax.js`
  regex patch, a data-loss bug filed 2026-08-26, and now building semantic diffing
  because byte diffs stopped meaning anything.

**Conclusion: (a). Unambiguously, and the failure modes of (b) and (c) are
documented in shipping products, not theorised.**

The AST is not banished — it is *demoted*. It is the runtime model, the
interchange model, and the thing your semantic diff/merge tool reconstructs on the
fly. It is never the thing in the repository.

---

## 8. The other candidates, briefly

### 8.1 Portable Text (Sanity) — the serious alternative, and why it still loses

Genuinely well designed, and the closest thing to a correct answer among the
JSON models. From its README:

> "Portable Text is a JSON based rich text specification for modern content
> editing platforms." … "an agnostic abstraction of rich text that can be
> serialized into pretty much any markup language" … "designed to be efficient
> for real-time collaborative interfaces."

Three ideas worth stealing outright:

1. **It is a FLAT ARRAY of blocks, not a tree.** Nesting is expressed as data
   (`listItem: "bullet"`, `level: 2`), not as containment. This makes every block
   independently addressable and makes list-restructuring a property edit rather
   than a re-parenting.
2. **`_key` on every block and every span** — stable identity, by construction.
3. **`markDefs` is standoff-shaped.** Annotations are keyed data structures
   referenced from spans by `_key`. The README's own example of a markDef is
   literally a comment:

   ```json
   { "_key": "some-other-random-key", "_type": "comment",
     "text": "Change to https://", "author": "some-author-id" }
   ```

   Overlapping marks are handled the only way a flat model can: **spans are split
   at every mark boundary**, so overlap never has to nest. That is exactly the
   right answer to the Peritext anomaly cited in `RESEARCH.md` §2.

Why it still loses here:

- **`markDefs` is block-scoped.** A comment spanning two paragraphs still cannot
  be expressed as one markDef. OHCO reappears one level up.
- **The merge experiment (§7.1) was run on Portable Text and it failed.**
- **"v0.0.1 - WORKING DRAFT"**, seven years after first commit (repo created
  2018-11-28, 1,440 stars, last push 2026-07-15).
- It is not human-editable, so it forces the whole projectional-editor stack.

**Take the ideas (`_key`, flat blocks, standoff markDefs); leave the format.**

### 8.2 AsciiDoc

Asciidoctor's own comparison page (<https://docs.asciidoctor.org/asciidoc/latest/asciidoc-vs-markdown/>) makes the case better than I can:

> "You start out with Markdown. Then it's Markdown + X. Then Markdown + X + Y.
> And down the rabbit hole you go."

> "X and Y often require you to sprinkle in HTML, unnecessarily coupling content
> with presentation and wrecking portability."

> its "syntax was designed to be extended as a core feature", whereas Markdown is
> "stuck in a game of whack-a-mole trying to satisfy publishing needs."

It also cites the RFC 7764 finding independently: "The IETF has declared 'there is
no such thing as "invalid" Markdown.'"

AsciiDoc has attributes, includes, conditionals, real tables (with spans), and a
formal specification effort at the Eclipse Foundation with an Abstract Semantic
Graph. **Promote to "serious runner-up."** Against it: the syntax is markedly
heavier than markdown, the single dominant implementation is Ruby (Asciidoctor),
and **UNVERIFIED** — I could not confirm the ASG spec's 2026 status. If djot's
bus factor is judged unacceptable, AsciiDoc is where to go next.

### 8.3 reStructuredText / docutils

Attributes and a real directive/role extension model, a documented doctree, and
30 years of Python-ecosystem service. Dismissed on ergonomics: significant
indentation and directive syntax make it strictly harder than markdown for
non-developers, which is `RESEARCH.md` §8's stated target audience. Its
*directives* concept, though, is exactly djot's generic container by another name.

### 8.4 MyST

rST's roles and directives grafted onto markdown syntax. Solves expressiveness,
does not solve dialect declaration (a `.md` MyST file is silently mis-parsed by
any CommonMark reader). Dismissed.

### 8.5 Markdoc (Stripe)

Excellent *philosophy* — "a strict separation between code and content (think:
docs as data)", explicitly rejecting MDX because MDX "affords users more power and
flexibility, but at the cost of complexity–content can quickly become as complex
as regular code." Ships a **schema and validation**, which almost nothing in
markdown-world does. But: its AST JSON representation is admittedly not
formalised ("seriously considering" it), and it is a CommonMark superset, so it
inherits §1's problems. **Steal the schema-and-validation idea; it is the JATS
lesson rediscovered.**

### 8.6 MDX

Actively disqualifying for an archive: it is a *program*, not a document.
Rendering it requires executing JavaScript, which means a 2046 reader needs a 2026
JS runtime and the exact component library. Dismissed with prejudice.

### 8.7 Notion's block model / ProseMirror / Lexical / Slate

All are *editor* document models: a tree (or flat block list, for Notion) with
node types, attributes, and stable ids, designed for transactional editing. They
are the right shape for the in-memory model and the wrong shape for storage, for
exactly the reasons in §7. ProseMirror's *schema* concept — a declared, validated
node/mark vocabulary that the editor cannot violate — is genuinely worth copying
as the runtime contract.

### 8.8 Scribble, Texinfo, Subtext

- **Scribble** (Racket): documents *are* programs; same disqualifier as MDX, plus
  a smaller runtime. Its `@`-syntax uniformity is elegant. Dismissed.
- **Texinfo**: 40+ years, GNU-wide, one semantic source → info/HTML/PDF. Proof
  that "one semantic source, many outputs" works and lasts. Dismissed on syntax
  weight and ecosystem.
- **Subtext** (Jonathan Edwards): research; no adoption. Its interest is the
  *editor* question, not the format question. **UNVERIFIED** — not investigated
  in this pass.

### 8.9 Projectional / structured editors

MPS, Hazel, Lamdu, Dion, Unison. The historical record is uniform: projectional
editing repeatedly produces better *semantics* and repeatedly fails to displace
text. The durable lesson for this project is narrower and more useful than "don't
do it":

> **A projectional editor must own its entire version-control stack**, because
> the moment the canonical form is a serialized tree, `git diff`, `git merge`,
> `grep`, `sed`, code review, and every LLM's ability to read the file all stop
> working and must be rebuilt in-house.

For a product whose *entire pitch* is "git is the drive" (`RESEARCH.md` §1), that
is a self-refuting architecture. `RESEARCH.md` §2 already reached the right
conclusion by a different road — "byte-stability isn't something you achieve by
picking a better serializer — it's free when the editor buffer *is* the file."
That is the anti-projectional principle, and it should be stated as a first
principle of the product, not as an editor implementation detail.

---

## 9. Org-mode — the most successful "one format for everything", and why it stayed

### 9.1 The model

Org's syntax reference (<https://orgmode.org/worg/dev/org-syntax.html>) defines a
four-level stratification: **headings → sections → greater elements → lesser
elements**, plus **objects** below the paragraph. Verbatim:

> "Elements are syntactic components that exist at the same or greater scope than
> a paragraph, i.e. which could not be contained by a paragraph. Conversely,
> objects are syntactic components that exist with a smaller scope than a
> paragraph, and so can be contained within a paragraph."

> "**Only headings, sections, property drawers, and planning lines are
> context-free**, every other syntactic component only exists within specific
> environments. This is a core concept of the syntax."

Roughly **40 distinct syntactic constructs**: 9 greater elements (greater blocks,
drawers, dynamic blocks, footnote definitions, inlinetasks, items, plain lists,
property drawers, tables), 12 lesser elements, 17 objects.

### 9.2 `#+TBLFM:` — direct prior art for formulas in plaintext

This is the part `RESEARCH.md` §3 needed and did not have. Org has shipped a
named-column, row-relative spreadsheet in plaintext since ~2004.

**Addressing** (<https://orgmode.org/manual/References.html>), verbatim:

> "`@ROW$COLUMN`" … "Column specifications can be absolute like `$1`, `$2`, …,
> `$N`, or relative to the current column, i.e., the column of the field which is
> being computed, like `$+1` or `$-2`. `$<` and `$>` are immutable references to
> the first and last column, respectively, and you can use `$>>>` to indicate the
> third column from the right."

> "The row specification **only counts data lines and ignores horizontal separator
> lines**" … "`@I` refers to the first hline, `@II` to the second… `@-I` refers to
> the first such line above the current line" … "You can also write `@III+2` which
> is the second data line after the third hline in the table."

> "Org's references with **unsigned numbers are fixed references** … Org's
> references with **signed numbers are floating references** because the same
> reference operator can reference different fields depending on the field being
> calculated."

**Column formulas are implicitly row-relative** — the key merge-safety property
(<https://orgmode.org/manual/Column-formulas.html>):

> "When you assign a formula to a simple column reference like `$3=`, the same
> formula is used in **all fields of that column**, with the following very
> convenient exceptions: (i) If the table contains horizontal separator hlines …
> everything before the first such hline is considered part of the table header
> and is not modified by column formulas … (ii) Fields that already get a value
> from a field/range formula are left alone by column formulas."

**Named columns** (<https://orgmode.org/manual/Advanced-features.html>) — via
marker characters in a reserved first column:

- `!` — "The fields in this line define names for the columns, so that you may
  refer to a column as `$Tot` instead of `$6`."
- `^` — "This row defines names for the fields **above** the row." (`_` = below)
- `$` — "if a field in a `$` row contains `max=50`, then formulas in this table
  can refer to the value 50 using `$max`."
- `#` / `*` — per-row recalculation markers.

The canonical example, verbatim from the manual:

```
|---+---------+--------+--------+--------+-------+------|
|   | Student | Prob 1 | Prob 2 | Prob 3 | Total | Note |
|---+---------+--------+--------+--------+-------+------|
| ! |         |     P1 |     P2 |     P3 |   Tot |      |
| # | Maximum |     10 |     15 |     25 |    50 | 10.0 |
| ^ |         |     m1 |     m2 |     m3 |    mt |      |
|---+---------+--------+--------+--------+-------+------|
| # | Peter   |     10 |      8 |     23 |    41 |  8.2 |
| # | Sam     |      2 |      4 |      3 |     9 |  1.8 |
|---+---------+--------+--------+--------+-------+------|
|   | Average |        |        |        |  25.0 |      |
| ^ |         |        |        |        |    at |      |
| $ | max=50  |        |        |        |       |      |
|---+---------+--------+--------+--------+-------+------|
#+TBLFM: $6=vsum($P1..$P3)::$7=10*$Tot/$max;%.1f::$at=vmean(@-II..@-I);%.1f
```

Plus `#+CONSTANTS: c=299792458. pi=3.14`, and `remote(NAME,@3$3)` cross-table
references resolving through a `#+NAME:`.

**Where results are stored — the critical question, answered:**

> "the formula is stored as the formula for this field, evaluated, and **the
> current field is replaced with the result**." (Field and range formulas)

> "**Formulas are stored in a special `TBLFM` keyword located directly below the
> table.**"

So: **formulas live on one line below the table; results are written into the
cells.** The file carries both, and the file is what you read.

**Two failure modes Org documents about itself, and both are ours:**

1. > "When inserting/deleting/swapping column and rows **with the appropriate
   > commands**, absolute references (but not relative ones) in stored formulas
   > are modified in order to still reference the same field. … **Automatic
   > adaptation of field references does not happen if you edit the table
   > structure with normal editing commands—you must fix the formulas yourself.**"

   A git merge that inserts a row is, definitionally, "normal editing commands."
   **Org's absolute `@row` references break under merge exactly as A1 references
   do in `RESEARCH.md` §3.** Org's mitigation is the manual's own advice: "anchor
   ranges at the table borders (using `@<`, `@>`, `$<`, `$>`), or at hlines using
   the `@I` notation." That is a *convention*, unenforced.

2. > "**Recalculation of a table is normally not automatic**, but needs to be
   > triggered by a command." (Updating the table)

   **The file can therefore contain results that do not match its formulas, with
   no marker.** For a git-backed substrate this is severe: a merge produces a
   committed file that *looks* authoritative and is stale, and nothing in the
   bytes says so.

**Transferable, and important:** Org validates the named-column, row-relative
addressing model that `RESEARCH.md` §3 recommends — with 20 years of production
use, which the report treated as a bet. It also validates results-in-file
(readable without the tool). It warns, from its own manual, that (a) absolute
addressing must be *linted out*, not merely discouraged, and (b) **recalculation
must be automatic and staleness must be detectable**, or the file lies.

### 9.3 `:ID:` — stable identity in plaintext

Org's `org-id` stores a UUID in a property drawer:

```org
* A heading
  :PROPERTIES:
  :ID: 4f2a1c88-9b31-4a2e-8c11-8a3d2f0e77b1
  :END:
```

Real, in-band, survives moving the heading between files. **But resolution goes
through `org-id-locations`, an out-of-band cache file mapping IDs to files.**
That cache goes stale, and "org-id-locations is stale" is a perennial user
complaint. The lesson: **an in-band ID is only half a mechanism; the index must be
rebuildable from the corpus alone, and cheaply.** For this substrate that means
the ID index must be a `.gitignore`d, disposable artifact reconstructable by a
ripgrep pass — which is exactly what `RESEARCH.md` §6 already concluded for
search (SQLite FTS5, gitignored). Same rule, applied to identity.

### 9.4 Export backends — semantics → many layouts

`ox.el`: `org-element-parse-buffer` produces a Lisp nested-list AST; backends
(`ox-html`, `ox-latex`, `ox-odt`, `ox-md`, `ox-icalendar`) are transcoder tables
keyed by element type, and `org-export-define-derived-backend` lets a backend
inherit and override another's transcoders. **This is the right architecture and
it is 15 years old**: one semantic parse, N presentation backends, backends
composed by inheritance rather than by forking.

### 9.5 Why it never escaped Emacs

**The spec is the implementation, and the document says so.** From the syntax
reference's own introduction, verbatim:

> "This document **describes and comments on Org syntax as it is currently read by
> its parser (`org-element.el`)** and, therefore, by the export framework. This is
> intended as a technical document for developers…"

It describes; it does not normate. There is no conformance suite in the CommonMark
sense.

**The claim "there is no independent parser that is fully correct" — assessed.**
I checked the field:

| Parser | Lang | Stars | Last push | State |
|---|---|---|---|---|
| `PoiScript/orgize` | Rust | 340 | **2025-01-27** | stale 19 months |
| `nvim-orgmode/orgmode` | Lua | 3,870 | 2026-08-20 | active; an *editor*, tree-sitter based |
| `200ok-ch/org-parser` | Clojure | 371 | 2026-03-27 | active, AGPL-3.0 |
| `lua-vr/org-mode-hs` | Haskell | 24 | 2025-12-12 | active-ish |
| pandoc `org` reader | Haskell | — | active | partial by design |

`org-mode-hs` ships a **"Progress" table** in its README enumerating what it does
and does not implement — an explicit, self-declared conformance gap (e.g. Verse
Block: structure yes, parse no; BabelCall: "parsed as keyword"). That table is
itself the best evidence for the claim: the most careful independent
implementation tracks its incompleteness as a feature of its documentation.

**Verdict: the claim is substantially TRUE but should be stated precisely** —
*several independent parsers exist and are usable; none claims full conformance,
and there is no conformance suite against which such a claim could be made.* The
blockers are, in order: (1) the spec is descriptive of one implementation; (2) 40
syntactic constructs, most context-sensitive; (3) core features are *Emacs Lisp
semantics*, not syntax — `#+TBLFM:` formulas are **Emacs Calc expressions**, babel
blocks execute Emacs-hosted interpreters, and the agenda is a query over Emacs
buffer state. You cannot implement org-table's spreadsheet without reimplementing
Calc. That is the real moat, and it is unbridgeable.

**Steal:** the four-level element stratification; `:ID:`; named-column
row-relative table formulas; results-in-file; the derived-backend export
architecture; `#+CONSTANTS:` / per-table parameter rows.
**Refuse:** the size of the syntax, and above all the practice of letting the
implementation *be* the spec.

---

## 10. Typst and the presentation layer

`typst/typst`: **Apache-2.0** (verified against the `LICENSE` file and the
workspace `Cargo.toml`), 55,712 stars, created 2019-09-24, pushed 2026-08-28.
Crate **0.15.1** (2026-07-17), 961,130 downloads in 90 days. **1.0 has not
shipped and the roadmap names no 1.0 target.**

### 10.1 The content model, and a quote that settles §7 from another direction

From <https://typst.app/docs/reference/foundations/content/>:

> "A piece of document content. This type is at the heart of Typst. All markup
> you write and most functions you call produce content values."

From the compiler crate docs (<https://docs.rs/typst/>), describing the pipeline:

> "**Evaluation:** The next step is to evaluate the markup. This produces a
> module, consisting of a scope of values that were exported by the code and
> content, a hierarchical, styled representation of what was written in the
> source file. **The elements of the content tree are well structured and
> order-independent and thus much better suited for further processing than the
> raw markup.**"

Typst's own architecture documentation states the §7 conclusion in Typst's own
words: **the tree is better for processing; the markup is what you write and
store.** Typst is a syntax-canonical system with a derived content tree — exactly
the architecture recommended here — built by people who had a free hand.

The tree is machine-readable. Verified running 0.15.1:

```
$ typst eval 'query(heading).map(h => h.body.text)' --in content.typ
["Substrate Architecture","Storage layer","Query layer"]
```

```json
[{"func":"figure","body":{"func":"table","columns":["auto","auto"],…},
  "caption":{"func":"caption","body":{"func":"text","text":"Layer inventory"},
              "kind":"table","numbering":"1"},
  "label":"<tbl-layers>"}]
```

Note the `typst query` subcommand is now deprecated in favour of
`typst eval 'query(...)'`. Note also that this is the *post-evaluation content
tree*, not a syntax AST — the syntax AST lives only inside the `typst-syntax`
crate and there is no `typst ast` subcommand.

### 10.2 Content / presentation separation, tested

`set` and `show` rules (<https://typst.app/docs/reference/styling/>):

> "With set rules, you can customize the appearance of elements."
> "A top level set rule stays in effect until the end of the file. When nested
> inside of a code or content block, it is only in effect until the end of that
> block."
> "The most basic form of show rule is a show-set rule…"
> "For maximum flexibility, you can instead write a transformational show rule
> that defines how to format an element from scratch."

**Demonstrated:** a semantic `content.typ` whose only styling reference is
`#import "style.typ": *` / `#show: theme`. Swapping the import to a second theme
(dark page, uppercase block headings, `show emph: it => underline(it.body)`,
numbering off) produced the same document in an entirely different visual
language with **zero edits to the content file — only the import line changed.**

That is the seam this substrate needs, working, today.

**Two honest gaps**, both top-20 open issues:

- **#147, "Support for user-defined elements/types" (88 reactions).** You cannot
  yet define `#definition[…]` as a first-class queryable element with its own
  set/show rules. So Typst has no equivalent of DITA specialization (§6.3): a
  custom semantic type is a function, not an element, and `query()` cannot find
  it. This is the single feature that would make Typst a *semantic* substrate
  rather than a very good layout language.
- **#420, "Resetting `show`/`set` to default / Revoke rules" (82).** Styles
  cascade but cannot be revoked, so composing two themes has no clean story.

And the separation is a *convention*, not a guarantee: nothing stops a `.typ`
file inlining `#text(fill: red)`. It must be linted, like everything else in §11.

Ecosystem: 1,554 unique packages / 4,629 versions in the `@preview` namespace,
against CTAN's ~6,500.

### 10.3 Version control properties — unusually good

- Plain UTF-8 `.typ`; **no derived state at all** — no `.aux`, `.toc`, `.bbl`,
  `.fls`. (Compare LaTeX, which litters a repo with regenerable junk.)
- Clean prose diffs: a one-word edit produced `1 file changed, 1 insertion(+),
  1 deletion(-)`.
- **PDF output is byte-reproducible by default** — two consecutive
  `typst compile` runs produced identical MD5s, and `SOURCE_DATE_EPOCH` is
  honoured. For a substrate that commits artifacts, this is a genuinely
  underappreciated property: the PDF can be a *checked* build output rather than
  a blob that churns on every build.
- Compile speed: a 902-line, 300-section document → 234 KB PDF in **~260 ms**
  (40-run average).
- `comemo` (<https://github.com/typst/comemo>, MIT/Apache-2.0): "It implements
  _constrained memoization_ with more fine-grained access tracking… we can reuse
  the result of a `.calc` script evaluation as long as its dependencies stay the
  same—even if other files change." The project's stated principle: "Performance
  through Incrementality: All Typst language features must accommodate for
  incremental compilation." **No published incremental benchmark numbers found.**
- **`typst.toml` has no lockfile and no integrity hashes.** Imports pin exact
  versions by construction (`#import "@preview/name:1.2.3"`) but resolve against
  a central registry. **Vendor every package you intend to keep for decades.**

### 10.4 Weaknesses

- **HTML export is experimental and feature-gated.** `--format html` errors
  without `--features html`, and then warns "do not rely on this feature for
  production use cases." Issue #5512: "Our primary focus in this initial phase of
  work will be on generating semantic HTML with no CSS." The output that does
  emerge is genuinely good semantic HTML (`<figure id="tbl-layers">` with
  `<figcaption>`, `<a href="#tbl-layers">Table 1</a>`) — but `#emph[…]` currently
  degrades to a bare text node rather than `<em>`, a real semantic loss.
- **Tagged PDF, however, SHIPPED in 0.14 (Oct 2025)**: "PDF files created with
  Typst 0.14 are tagged by default, raising the bar for accessibility." All of
  PDF/A-1a…A-4e and PDF/UA-1 compile. **Typst shipped accessible PDF by default
  before LaTeX shipped it at all.**
- 1,215 open issues; notable: #721 HTML export (383 reactions), #1765 interactive
  forms (216), #188 EPUB (130), #276 CJK (64).
- **Pandoc is not a reliable semantic bridge to Typst.** Pandoc 3.1.11 ships both
  a `typst` reader and writer, but a md→typst→md round trip degraded the table to
  raw HTML inside a `<figure>` and lost header-row semantics.

### 10.5 LaTeX and ConTeXt, honestly

Knuth, "The Future of TeX and METAFONT", *TUGboat* 11(4), 1990
(<https://tug.org/TUGboat/tb11-4/tb30knut.pdf>):

> "Let us regard these systems as fixed points, which should give the same results
> 100 years from now that they produce today."
> "the next versions of TeX will be 3.14, then 3.141, then 3.1415…, converging to
> the ratio of a circle's circumference to its diameter"
> "At the time of my death… the final version numbers… should become `TeX,
> Version π` and `METAFONT, Version e`… From that moment on, all 'bugs' will be
> permanent 'features.'"

**But TeX's stability is not LaTeX's stability, and this distinction is the whole
ballgame.** From the LaTeX Project (<https://www.latex-project.org/latex3/>):

> "A while ago we made the decision to drop the idea of a separate LaTeX3
> format… instead decided to gradually modernize LaTeX."

expl3 folded into the kernel in 2020; LaTeX News 40: "it was meant to be an
intermediate version (hence the ε)… nominally, LaTeX 2ε is still with us today."
The kernel now ships dated releases twice yearly (latest 2026-06-01), and the
Project's own rollback machinery is the admission that documents break — LaTeX
News 28: "there is the off-chance that code that hooked into internals… needs
adjustment."

**So: a 1995 LaTeX document is reproducible by pinning a 1995 toolchain** (TeX
Live historical archives run 1996–2026), **not by compiling it on today's TeX
Live.** LaTeX's longevity is *archival* — freeze the whole stack — not
*forward-compatible*. That is a materially weaker guarantee than it is usually
credited with, and it is the same guarantee Typst can offer by pinning a
compiler binary.

**LaTeX cannot be parsed without being executed.** No single authoritative quote
was obtained, but the practitioner evidence is unanimous: LaTeXML (NIST) — "The
approach is to emulate TeX as far as possible (in Perl)"; TeX4ht "uses TeX to
parse the input document"; MacFarlane (TUG 2020) — "Pandoc is far from being able
to convert arbitrary tex files with high accuracy." **You cannot extract a
document tree from LaTeX without running LaTeX.** For a substrate that must index,
search, diff and query its own corpus, that is disqualifying on its own.

**Is LaTeX semantic markup?** Barely. `\emph` vs `\textit` is the one real
semantic distinction, and even l2tabu's rationale for preferring it is mechanical
("Obsolete commands do not support LaTeX 2ε's new font selection scheme"), not
semantic. No authoritative source frames LaTeX as semantic markup.

**ConTeXt: bus factor one, quantified.** The `contextgarden/context` source mirror
has **exactly two contributor identities, both Hans Hagen** (1,912 + 609
commits). CTAN lists "Maintainer: Hans Hagen." Pragma ADE's own download page
calls the MkII/MkIV distribution "an archival one" and LMTX "the recommended one."
Mailing list traffic: 39 discussions / 32 participants in 30 days. Dismiss.

### 10.6 Typst verdict

**Viable, and the best available answer for the presentation layer — with one
hard caveat and one mitigation that must actually be implemented.**

- **vs LaTeX**: Typst wins on everything that matters to a *substrate* — a
  queryable content tree obtainable without executing arbitrary macros, no
  derived-state files, byte-reproducible output, tagged PDF today, sub-second
  compiles, and a permissive licence with a public commitment ("We are committed
  to keep the Typst compiler open-source: We believe that you should have
  certainty that your investment in Typst is not jeopardized by a change in
  licensing", <https://typst.app/open-source/>). LaTeX wins on exactly one thing,
  and it is not small: a 30-year installed base with archived toolchains.
- **vs CSS/HTML + Paged.js**: HTML is the more durable *format* and will outlive
  both, but Paged.js is a browser + print-CSS + JS-runtime stack with far worse
  fidelity. Typst's (immature) HTML export is a path *from* semantic source to
  HTML, which is the right direction of travel.
- **vs doing nothing**: not an option if paginated, citable, accessible artifacts
  are required.

**Caveat:** 0.15.1, no 1.0, real breaking changes every minor release (0.15.0
alone removed the `path` element and the `pattern` type and changed `lr` sizing,
math class semantics and SVG class names). The evidence cuts both ways, though: a
test `content.typ` using set rules, `show…where`, figure, table, label and ref
**compiled unchanged on typst 0.11.0 (March 2024) and on 0.15.1 (July 2026)**.
The *semantic core is stable in practice*; the periphery (math, paths, SVG, HTML)
is not.

**Mitigation, non-optional:** commit semantic-only `.typ`; vendor `style.typ` and
every `@preview` package into the repo; pin the compiler binary version alongside
the content; and treat `typst eval 'query(...)'` JSON — **not** the PDF — as the
machine-readable artifact.

### 10.7 The architectural point, which stands regardless

It is the JATS point again: **the presentation layer must be a separate artifact
from the semantic layer.** Whatever fills the slot, the canonical document must
not contain layout. Djot's `{.class}` / `::: div` and Typst's `show` rules meet at
exactly the right seam: the document declares *what a thing is*, the theme file
declares *how that kind of thing looks*. The one thing to watch is that Typst
cannot yet declare user-defined elements (#147), so the semantic vocabulary must
live on the djot side and be *mapped into* Typst, not defined there.

---

## 11. Recommendations

1. **Canonical form: text syntax, parsed. Never a committed AST.** (§7, measured.)

2. **Adopt djot as the canonical syntax — with a vendored, MIT-licensed parser you
   are willing to maintain**, and with markdown import/export as a permanent
   first-class path (djot.js already ships `fromPandoc`/`toPandoc`). If the bus
   factor is judged unacceptable, AsciiDoc is the runner-up; markdown is the
   status quo and is defensible *only* if you accept that you can never carry
   attributes, IDs, comments, merged cells, or a dialect declaration.

3. **Ship an attribute linter on day one.** Djot's silent attribute-drop (§3.2b)
   and org's stale-`org-id-locations` (§9.3) are the same class of bug: an
   identity mechanism whose failure is silent. Make `# H {#id}` an *error*, not a
   drop. Make a reference to a missing ID fail loudly and locally — the same
   imperative `RESEARCH.md` §3 already set for missing column names.

4. **Adopt DITA-style class ancestry for extensions.** `{.callout .admonition}`,
   ordered general→specific, linted. Unknown extensions then degrade to their
   nearest known ancestor automatically, in-band, with no registry. This is the
   single cheapest structural idea in this report.

5. **Comments, suggestions and tracked changes go in a standoff sidecar file**,
   anchored by block ID + quoted text + offset hint, resolved fuzzily. This is
   forced by OHCO (§5), not chosen. Design the orphaned-anchor UX up front,
   because anchors *will* orphan.

6. **One model, several grammars — not one syntax for everything.** JATS's
   three-tag-set architecture (§6.2) is the proof. Documents get djot. Tables get
   the named-column `.sheet.md`-style grammar `RESEARCH.md` §3 specified, now
   validated by 20 years of `#+TBLFM:` (§9.2). Slides get a slide grammar. They
   share an *AST vocabulary*, not a parser.

7. **The AST is runtime-only, and its version is not your problem** — because you
   never store it. If you ever feel tempted to commit `pandoc -t json` output,
   re-read §4.3.

8. **Formulas: results in the file, recalculation automatic, staleness
   detectable.** Org proves results-in-file is right and that manual recalculation
   is a trap (§9.2).

9. **Do not ship a compatibility dialect switch.** OOXML Transitional (§6.4).

10. **Presentation layer: Typst, with the vendoring discipline of §10.6.** It is
    Apache-2.0, has a queryable content tree, produces byte-reproducible output,
    leaves no derived state in the repo, and already ships tagged PDF by default —
    which LaTeX still does not. It is pre-1.0 and the periphery churns, so vendor
    the theme and every package, and pin the compiler binary next to the content.
    Keep the *semantic vocabulary* on the djot side and map it into Typst; Typst
    cannot yet declare user-defined elements (issue #147).

---

## 12. Open questions and unverified claims

- **UNVERIFIED**: GODDAG / TexMECS (Huitfeldt & Sperberg-McQueen) in detail.
  Highest-value follow-up if annotations become a headline feature.
- **UNVERIFIED**: MPS's version-control documentation could not be fetched; the
  "MPS ships its own merge driver" claim needs direct confirmation.
- **UNVERIFIED**: Library of Congress format-sustainability assessments for ODF
  and OOXML; Word's default Strict/Transitional setting in 2026; whether ODF 1.4
  has reached OASIS Standard stage (the index confirms 1.3 CS01, 2019-12-25).
- **UNVERIFIED**: whether a DITA 2.0 exists at Committee Specification stage. The
  OASIS approved-standards index tops out at v1.3 (2015), which is what the
  specialization quotes are drawn from; the `@class` mechanism is unchanged since
  v1.0.
- **UNVERIFIED**: AsciiDoc Language spec / ASG status at the Eclipse Foundation
  in 2026.
- **UNVERIFIED (negative)**: no production adopter of djot was found, but a
  negative is hard to establish.
- **Open**: does a djot round-trip *with a minimal-edit writer* exist or can it be
  built? djot.js's `renderDjot` is not byte-stable (§3.2a), and
  `mdast-util-to-markdown`'s positional `Tracker` "isn't used yet"
  (`RESEARCH.md` §2). If the CodeMirror-buffer-is-the-file decision holds, this
  never matters. If it ever stops holding, it matters enormously.
- **Open**: the sub-block anchor-resolution algorithm for standoff comments.

---

## Sources

Primary sources fetched or run, in order of appearance:

- MacFarlane, *Beyond Markdown* — <https://johnmacfarlane.net/beyond-markdown.html>
- CommonMark spec index & `spec.json` — <https://spec.commonmark.org/>
- RFC 7764, *Guidance on Markdown* — <https://www.rfc-editor.org/rfc/rfc7764.txt>
- MDX, *What is MDX* — <https://mdxjs.com/docs/what-is-mdx/>
- Markdoc FAQ — <https://markdoc.dev/docs/faq>
- Asciidoctor, *AsciiDoc vs Markdown* — <https://docs.asciidoctor.org/asciidoc/latest/asciidoc-vs-markdown/>
- djot — <https://djot.net/>, <https://github.com/jgm/djot>,
  `doc/syntax.md`, `@djot/djot@0.3.2` (npm, MIT, 0 deps)
- Renear, Mylonas & Durand, *Refining our Notion of What Text Really Is* —
  <https://xml.coverpages.org/ohco1.html>
- TEI P5, *Non-hierarchical Structures* —
  <https://tei-c.org/release/doc/tei-p5-doc/en/html/NH.html>
- JATS rationale — <https://jats.nlm.nih.gov/archiving/rationale.html>
- OASIS DITA 1.3, class attribute rules and syntax —
  <https://docs.oasis-open.org/dita/dita/v1.3/errata02/os/complete/part2-tech-content/archSpec/base/specialization-class-attribute.html>
- Org manual: References, Field and range formulas, Column formulas, Updating the
  table, Advanced features — <https://orgmode.org/manual/>
- Org Syntax (Worg) — <https://orgmode.org/worg/dev/org-syntax.html>
- Portable Text spec — <https://github.com/portabletext/portabletext>
- pandoc-types version history — <https://hackage.haskell.org/package/pandoc-types>
- OASIS standards index (DITA/DocBook/ODF approval dates) —
  <https://www.oasis-open.org/standards/>
- Typst docs: content, styling, scripting, roadmap, open-source commitment —
  <https://typst.app/docs/>, <https://typst.app/open-source/>,
  <https://docs.rs/typst/>, <https://github.com/typst/comemo>
- Typst 0.14 release (tagged PDF by default) —
  <https://typst.app/blog/2025/typst-0.14/>
- Knuth, "The Future of TeX and METAFONT", *TUGboat* 11(4), 1990 —
  <https://tug.org/TUGboat/tb11-4/tb30knut.pdf>
- LaTeX Project on LaTeX3 — <https://www.latex-project.org/latex3/>

Local experiments are reproducible from the transcript; the scratch files
(`t.md`, `t.dj`, `span.html`, `pt_*.json`, `mt2/`) live under this session's
scratchpad and are not committed.
