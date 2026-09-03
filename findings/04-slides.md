# SLIDES layer: markdown-presentation prior art

Research date: **2026-08-28**. All GitHub numbers pulled from `api.github.com` on that date.

**Labelling convention used throughout:**
- **VERIFIED** — I read the primary source (repo file, official doc page, API response) myself.
- **REPORTED** — secondhand (press, blog, forum, search summary). Treated as weaker.

**Bottom line up front:** the deck *engine* layer is solved several times over — wrap Marp, do not
build. The *editable-PPTX* layer is solved only by the Pandoc/OOXML family, and Marp's own docs
disclaim its PPTX quality. The *WYSIWYG-over-markdown-slides* layer is genuinely, verifiably empty.

---

## A. The comparison table

Stars / license / last push are VERIFIED from the GitHub REST API on 2026-08-28.
"Last push" is `pushed_at` (last commit to any branch), not release date.

| Tool | Separator | Outputs | Embeddable? | License | Stars | Last push | Verdict |
|---|---|---|---|---|---|---|---|
| **Marpit** (`marp-team/marpit`) | `---` (also `___`, `***`, `- - -`); `headingDivider` for none | HTML + CSS (framework only) | **Library** (JS, `Marpit.render()`) | MIT | 1,369 | 2026-08-03 | The engine underneath Marp. Pure md→HTML/CSS, no browser. **This is the embeddable core.** |
| **Marp Core** (`marp-team/marp-core`) | inherits Marpit `---` | HTML + CSS | **Library** (extends Marpit) | MIT | 1,148 | 2026-08-09 | Marpit + official themes, auto-scaling, emoji, math, Mermaid, Shiki. v5 splits into lean core + opt-in plugins. |
| **Marp CLI** (`marp-team/marp-cli`) | inherits Marpit `---` | HTML, PDF, **PPTX**, PNG, JPEG | CLI **and** Node API | MIT | 3,784 | 2026-07-20 (v4.5.0 2026-07-17) | The batteries. PDF/PPTX/image need a Chromium/Firefox install. |
| **Marp for VS Code** | inherits Marpit `---` | HTML/PDF/PPTX/images (wraps CLI) | VS Code extension | MIT | 2,079 | 2026-08-11 | Preview + IntelliSense + diagnostics. **Not WYSIWYG** — see §C. |
| **Slidev** (`slidevjs/slidev`) | `---` padded by newlines; per-slide YAML frontmatter between rules | HTML (SPA), PDF, **PPTX (images)**, PNG, MD | CLI + Vite app; theme/addon plugin API | MIT | **48,317** | 2026-08-25 (v52.19.1 2026-08-19) | Most expressive. Vue components in slides. Has `v-drag`, an integrated side editor, and a built-in MCP server. Heavy (full Vite/Vue runtime). |
| **reveal.js** (`hakimel/reveal.js`) | `^\r?\n---\r?\n$` (h-slides), `----` (v-slides), `notes?:` (notes) | HTML; PDF via print/DeckTape | **Library** (JS, browser) | MIT | **72,225** | 2026-08-24 | The de-facto HTML deck runtime. Markdown is an optional *plugin*, not the native format. |
| **reveal-md** (`webpro/reveal-md`) | `\n---\n` (configurable), vertical `\n----\n` | Static HTML site, PDF (Puppeteer) | CLI | MIT | 3,910 | 2026-02-14 | Thin, well-worn reveal.js wrapper. Slowing down (6 months since last push). |
| **MkSlides** (`MartenBE/mkslides`) | regex, default `^\s*---\s*$`; vertical `^\s*-v-\s*$`; notes `^Notes?:` | Static HTML site | CLI (Python) | MIT | 471 | 2026-08-03 | MkDocs-shaped reveal.js SSG. Multi-file decks + index page. Active but small. |
| **remark** (`gnab/remark`) | `---` slides, **`--` incremental**, `???` notes | HTML (in-browser, no build) | **Library** (single JS file) | MIT | 12,999 | **2024-06-19** | Historically important, effectively frozen 2+ years. Zero-build appeal remains. |
| **Quarto** (`quarto-dev/quarto-cli`) | `##` headings, or `---` rules; `--slide-level` | revealjs HTML, **PPTX**, beamer PDF, + docs/books/sites | CLI | NOASSERTION (MIT+GPL mix) | 5,965 | 2026-08-28 | Wraps Pandoc. Best if you also want executable code cells. Heavy install. |
| **Pandoc** (`jgm/pandoc`) | horizontal rule or slide-level heading | revealjs, S5, DZSlides, Slidy, Slideous, **beamer PDF**, **PPTX** | CLI + Haskell lib | GPL-2.0 | 46,051 | 2026-08-28 (3.10.2, 2026-08-12) | The only path to genuinely editable PPTX and to LaTeX beamer. See §B. |
| **Kova** (`KovaMD/Kova`) | `---` | **PPTX (native shapes)**, PDF, HTML | Desktop app (Tauri; TS + Rust) | GPL-3.0 | 283 | 2026-08-23 (v0.7.9) | **The closest thing to the thesis.** Editor+preview, PptxGenJS-based real PPTX, and `!sheet` computed tables. Created **2026-05-04** — 4 months old. |
| **Deckset** | `---` (blank line above & below) | PDF (+ live present) | Commercial Mac/iOS app | Proprietary | — | site © 2026 | **Richest layout DSL of any md-slides tool** (§D). Mac/iOS only, no PPTX. |
| **presenterm** (`mfontanini/presenterm`) | `---` | Terminal render; PDF, HTML | CLI (Rust) | BSD-2-Clause | 8,798 | 2026-05-22 | Terminal decks. Columns, transitions, notes, mermaid/d2/LaTeX. Not for business users. |
| **patat** (`jaspervdj/patat`) | `---` / slide-level heading (Pandoc-parsed) | Terminal only | CLI (Haskell) | GPL-2.0 | 2,740 | 2026-06-25 | Pandoc-backed terminal decks. Same audience note as presenterm. |
| **Spectacle** (`FormidableLabs/spectacle`) | JSX `<Slide>` components (MDX mode exists) | React app; PDF via print | **React library** | MIT | 10,155 | 2026-04-12 | JSX-first, not markdown-first. Not a fit for a `---`-md file store. |
| **mdx-deck** (`jxnblk/mdx-deck`) | `---` in an `.mdx` file | React app | React library | MIT | 11,500 | **2023-01-04** | Dead ~3.5 years. Popularity is historical. |
| **Obsidian Advanced Slides** (`MSzturc/…`) | `---` (+ `--` vertical) | reveal.js HTML, PDF | Obsidian plugin | MIT | 1,256 | 2024-06-29 | **Discontinued by author** (announced on Obsidian forum; successor below). |
| **Obsidian Slides Extended** (`ebullient/…`) | `---` / `--` | reveal.js HTML, PDF | Obsidian plugin | MIT | 269 | 2026-08-26 | Live maintained fork of the above. Live preview while editing. Still text-first. |
| **Landslide** (`adamzap/landslide`) | Pandoc/`---` style | HTML5 | CLI (Python) | Apache-2.0 | 2,092 | **2024-01-01** | Dormant. |
| **GitPitch** | `---` in `PITCHME.md` | Hosted HTML | SaaS + repo | none declared | 5,475 | **2021-03-01** | **Dead.** Service gone; repo frozen 5.5 years. |
| **Hacker Slides** (`msoedov/hacker-slides`) | `---` (reveal.js) | HTML | Self-hosted web app | MIT | 347 | 2021-05-12 | **Archived on GitHub.** Dead. |
| **Slidoc** (`mitotic/slidoc`) | `---` | HTML | CLI (Python) | BSD-3-Clause | **8** | **2019-06-04** | Abandoned research artifact. 8 stars. Ignore. |
| **sent** (suckless) | **blank line** — plain text, *not* markdown; `@img`, `#comment` | X11 window only, no export | C program | MIT/ISC | — | last commit **2023-01-10** | Takahashi-method toy. Not markdown, no export. Not relevant. |
| **Slides.com** | markdown is **import only** | PDF, self-contained HTML, reveal.js | SaaS (by reveal.js's author) | Proprietary | — | © 2026, active | Stores decks **as HTML documents**, not markdown. See §C. |
| **Logseq slides** | — | — | — | AGPL-3.0 | 44,663 | 2026-08-27 | **VERIFIED absent:** `package.json` on `logseq/logseq` main has **no reveal.js dependency**, and there is no slide extension in `src/main/frontend/extensions/`. Slide mode existed in the older file-based Logseq (REPORTED); it is not in current main. Do not count on it. |
| **Typora** | — | PDF/HTML/image; docx etc. via Pandoc | Commercial editor | Proprietary | — | active | **No native slide mode.** reveal.js only via a hand-rolled custom Pandoc export. Notable as proof that WYSIWYG-over-md works *for documents*. |
| **Zenn / Docswell** | — | — | — | — | — | — | **Not deck engines.** VERIFIED from Zenn's own markdown guide: `@[docswell](url)`, `@[speakerdeck](id)`, `@[slideshare](key)` are **embed directives** for externally hosted decks. Docswell is a Japanese slide *hosting* service, the SpeakerDeck analogue. |
| **Slidebeamer** | — | — | — | — | — | — | **Does not exist.** `slidebeamer.com` redirects to `chapelscreen.com` (unrelated); `slidebeamer.app` does not resolve. No product found. Likely a conflation of "slides" + Pandoc "beamer". |
| **Presentic** | — | — | — | — | — | — | **Does not exist.** `presentic.com`, `.io`, `.app` all fail DNS. No product found in search. |

### Adjacent tools discovered during this survey (not on the original list, but load-bearing)

| Tool | What it is | License | Stars | Last push |
|---|---|---|---|---|
| **`MartinPacker/md2pptx`** | Markdown → PPTX built on python-pptx, `template: X.pptx` metadata line, `#`/`##`/`###` slide levels, trailing paragraph → notes. **Real editable shapes.** | MIT | 511 | 2026-08-25 |
| **`gitbrent/PptxGenJS`** | JS library emitting OOXML: text, tables, shapes, images, charts, slide masters, `addNotes()` | MIT | 6,076 | 2025-11-28 (v4.0.1, 2025-06-26) |
| **`scanny/python-pptx`** | The de-facto Python OOXML library. PyPI 1.0.2 uploaded 2024-08-07; **no commits in 2 years**, 534 open issues; still ~63M downloads/month. Dormant-but-dominant. | MIT | 3,502 | 2024-08-07 |
| **`astefanutti/decktape`** | Universal HTML-deck → PDF exporter (handles reveal, remark, Deck.js, …) | MIT | 2,422 | 2026-07-13 |
| **`presenton/presenton`** | Self-hostable open-source Gamma clone. Accepts `slides_markdown[]` as API **input**; stores in SQLAlchemy/SQLite; drag-edit UI; "fully editable PPTX" export. | Apache-2.0 | 9,895 | 2026-08-27 |
| **W3C b6+ slide editor** | A real WYSIWYG editor — but for **HTML** slides, not markdown. Presented at W3C 2026-03-25 ("Two editors for HTML slides"): "WYSIWYG & source editor", "Edit local or online slides (HTTP GET/PUT)". A separate "Markdown editor for b6+" exists but is a text editor with preview. | W3C | — | 2026-03-25 |

---

## B. The PPTX question — how good is markdown → PowerPoint really?

**Short answer: it depends entirely on which pipeline, and the difference is enormous. Marp's PPTX
is a slideshow of flat images. Pandoc's is real, editable PowerPoint.**

### Marp CLI `--pptx` — images, by its own admission (VERIFIED)

From `marp-team/marp-cli` README on `main`, retrieved 2026-08-28:

> "A converted PPTX usually consists of pre-rendered background images, that is meaning
> **contents cannot to modify or re-use** in PowerPoint."

Default `--pptx` embeds one rendered image per slide. The only real text that survives is the
speaker notes. Mechanically it uses PptxGenJS purely as an image-wrapping envelope (CHANGELOG:
"Use PptxGenJS v3 instead of `@marp-team/pptx`", PR #205).

### Marp CLI `--pptx-editable` — real, but disclaimed (VERIFIED)

- Added in **v4.1.0, released 2025-01-15**. CHANGELOG: "_[Experimental]_ `--pptx-editable` option
  to convert Markdown into editable PPTX (#166, #298, #626)".
- **Still labelled `_[EXPERIMENTAL]_` on `main` as of v4.5.0 (2026-07-17)** — 19 months without
  promotion to stable. That is a signal.
- Usage: `marp --pptx --pptx-editable slide-deck.md`
- README's own caveats, verbatim:
  > "The experimental `--pptx-editable` option requires installing both of the browser and
  > LibreOffice Impress. If the theme and inline styles are providing complex styles into the
  > slide, **`--pptx-editable` may throw an error or output the incomplete result.** (e.g. `gaia`
  > theme in Marp Core)"
  > "Conversion to the editable PPTX results in **lower slide reproducibility** compared to the
  > conversion into regular PPTX and other formats. Additionally, **presenter notes are not
  > supported.** _We do not recommend to export the editable PPTX if maintaining the slide's
  > appearance is important._"
- **How it works** (VERIFIED, PR #626 body, merged 2025-01-15): "LibreOffice has a conversion
  feature with headless `soffice --headless`, that can use the PDF input filter and the PPTX
  output filter… This implementation will convert Markdown into PDF first, and try converting
  that into PPTX with the headless LibreOffice." The author adds: "The almost part of this
  conversion process is depending on upstream tools… so it is difficult to fix these limitations
  in Marp."

So `--pptx-editable` is a **PDF→PPTX vectoriser**. You get selectable, retypeable text, but as
absolutely-positioned PDF-derived boxes — not semantic placeholders bound to a layout. A colleague
can retype a bullet; they cannot restyle the deck by changing the master.

### Slidev `--format pptx` — images too (VERIFIED)

From `slidevjs/slidev` `docs/guide/exporting.md`:

> "Note that all the slides in the PPTX file will be exported as images, so the text will not be
> selectable. Presenter notes will be conveyed into the PPTX file on a per-slide basis."

Unambiguous. Slidev is not a PPTX story.

### Pandoc's pptx writer — the real thing (VERIFIED)

Native PowerPoint objects dropped into **real layout placeholders**. The writer selects from a
fixed set of seven layouts (MANUAL, "PowerPoint layout choice"):

| Layout name | Chosen when |
|---|---|
| **Title Slide** | the initial slide, filled from `date`, `author`, `title` metadata |
| **Section Header** | slides starting with a heading above the slide level |
| **Two Content** | a `div` with class `columns` containing ≥2 `div`s with class `column` |
| **Comparison** | a two-column slide where ≥1 column is text followed by non-text |
| **Content with Caption** | a non-two-column slide with text followed by non-text (image/table) |
| **Blank** | slides containing only blank content |
| **Title and Content** | everything else |

`--reference-doc` is the styling hook, and the only one — MANUAL notes bluntly that "pptx has no
template". The requirement is that your corporate `.pptx`/`.potx` contain layouts with **exactly
those seven names**; "For each name, the first layout found with that name will be used. If no
layout is found with one of the names, pandoc will output a warning and use the layout with that
name from the default reference doc instead."

Bootstrap a template with:
```
pandoc -o custom-reference.pptx --print-default-data-file reference.pptx
```

**Supported into PPTX:** speaker notes (`::: notes`, plus a `notes:` YAML field for the title
slide), two columns, incremental lists (`-i` or `::: incremental`), per-slide background images
(`## Heading {background-image="…"}`), tables, images.

**Documented limits (VERIFIED):**
- Pauses are out: the `. . .` syntax — "Note: this feature is not yet implemented for PowerPoint
  output."
- Column widths are out: "Note: Specifying column widths does not currently work for PowerPoint."
- No arbitrary positioning at all. Everything lands in a placeholder of the chosen layout.

### Quarto → pptx (VERIFIED)

Quarto is a wrapper over Pandoc's pptx writer, so it inherits the same seven layouts and the same
ceiling. Its own page states: "PowerPoint presentations support core presentation features like
incremental bullets, 2-column layouts, and speaker notes, and can also be rendered using custom
PowerPoint templates." Configured as `format: pptx: reference-doc: template.pptx`. Bonus over raw
Pandoc: executable code cells produce real charts. Caveat on backgrounds: "only the 'stretch' mode
is supported."

### PptxGenJS / python-pptx / md2pptx — full control (VERIFIED)

- **PptxGenJS** README: "The library outputs standards-compliant Open Office XML (OOXML) files";
  "Create all major slide objects: **text, tables, shapes, images, charts**"; "Define custom
  **Slide Masters**". Notes via `slide.addNotes('TEXT')`. Absolute positioning `{x, y, w, h}`.
  **No official markdown front-end** — the only importer is `pptx.tableToSlides()` for HTML tables.
- **python-pptx** docs: "Round-trip any Open XML presentation… Add slides; Populate text
  placeholders… Add image to slide at arbitrary position and size; Add textbox…; Add table…; Add
  auto shapes…; Add and manipulate column, bar, line, and pie charts." Fully native. Maintenance
  model, quoted from its own docs: "New features are generally added via sponsorship."
- **md2pptx** is the ready-made markdown front-end over python-pptx, and unlike its dependency it
  is actively maintained (last push 2026-08-25).
- **Kova** ships `pptxgenjs@^4.0.1` as a direct dependency (VERIFIED from its `package.json`), and
  `src/engine/export/exportPptx.ts` (2,204 lines) calls `s.addText(...)`, `s.addShape('rect', …)`,
  `s.addNotes(...)`, `tryAddImage(...)` per element. **That is native shapes, not a screenshot** —
  the only rasterised elements are Mermaid diagrams and display math, which degrade with an
  explicit warning ("Mermaid diagram could not be rendered and was skipped").

### Editability ranking

1. **PptxGenJS / python-pptx (+ md2pptx) / Kova** — fully native shapes, masters, charts, tables,
   notes. The colleague edits everything normally. Cost: you write generator code, or adopt a
   specific markdown dialect.
2. **Pandoc or Quarto with `--reference-doc`** — real placeholder-bound text with a corporate
   template applied; editable *and* restylable via the master. Ceiling: seven layouts, no
   positioning, no column widths, no pauses. **Best effort-to-editability ratio for a markdown repo.**
3. **Marp `--pptx --pptx-editable`** — text is editable but absolutely positioned; no notes;
   "lower slide reproducibility" by its own docs; still experimental after 19 months; needs
   LibreOffice *and* a browser.
4. **Marp `--pptx` / Slidev `--format pptx`** — flat images. Only the notes are text.

**Answer to the question as posed:** yes, a git-backed markdown suite *can* hand a colleague a
genuinely editable deck — but only by exporting through the OOXML family (Pandoc, or PptxGenJS
directly). If you wrap Marp for rendering, you must **not** use Marp's own PPTX path for handoff.

---

## C. The WYSIWYG gap — confirmed real

**The question:** is there ANY tool where a non-technical user drags and edits visually, and the
file on disk stays `---`-separated markdown?

**Answer: essentially no.** One partial exception exists, and it is narrow.

### The one partial exception: Slidev `v-drag` (VERIFIED)

Slidev's `docs/features/draggable.md` describes moving, resizing and rotating elements with the
mouse, with positions persisted **back into the markdown**:

```md
---
dragPos:
  square: Left,Top,Width,Height,Rotate
---

<img v-drag="'square'" src="https://sli.dev/logo.png">
```

or inline:

```md
<img v-drag="[Left,Top,Width,Height,Rotate]" src="https://sli.dev/logo.png">
```

Write-back is confirmed by the doc's own warning:

> "Slidev use regex to update the position value in the slide content. If you meet problems,
> please use the frontmatter to define the values instead."

Controls: "Double-click the draggable element to start dragging it… arrow keys to move… Hold
`Shift` while dragging to preserve its aspect ratio." There is also `<v-drag-arrow />`.

**Why this is only a partial exception:** `v-drag` positions *existing* elements you already
declared in HTML/Vue. You cannot create a slide, insert a text box, retype a bullet, pick a layout,
or restyle by direct manipulation. It is a positioning nudge tool for authors who already write
Slidev markdown by hand. The regex-based write-back is also self-declaredly fragile. It is the
strongest evidence anywhere that md-round-tripping direct manipulation is *possible* — and the
clearest evidence that nobody has built the full thing.

### Everything else, checked

| Candidate | What it actually is | Round-trips to `---` md? |
|---|---|---|
| **Slidev integrated editor** (VERIFIED, `docs/features/side-editor.md`) | "Slidev comes with an integrated editor that will instantly reload and save the changes to your file." A **text** editor pane beside the preview. | Text editing, not WYSIWYG |
| **Marp for VS Code** (VERIFIED, README) | Preview + IntelliSense autocomplete for directives + hover help + diagnostics (incl. an experimental `slide-content-overflow` warning) + export. Explicitly a Markdown-preview experience. | No — text only |
| **Kova** (VERIFIED, README + repo) | CodeMirror editor + live preview, side by side. Deps confirm: `@codemirror/*`, no drag/canvas library. | No — text only |
| **Obsidian Slides Extended** (VERIFIED, README) | "Live Preview while editing your slides". Obsidian markdown source + reveal.js preview. | No — text only |
| **Deckset** (VERIFIED, site + docs) | "Your presentation stays a plain-text Markdown file". You edit the markdown in your own text editor; Deckset renders. Deliberately not an editor. | No — it isn't an editor at all |
| **reveal.js "built-in editor"** | **Does not exist.** VERIFIED: `hakimel/reveal.js/plugin/` contains only `highlight`, `markdown`, `math`, `notes`, `search`, `zoom`. | N/A |
| **Slides.com** (VERIFIED, /features) | The reveal.js author's commercial WYSIWYG. Markdown is an **import** tool ("Import from Markdown"). Storage: "Decks are stored as HTML documents". Exports PDF/HTML/reveal.js, no PPTX. | **No — markdown is one-way in** |
| **Presenton** (VERIFIED, README) | Open-source AI deck generator with a real drag-and-edit UI and editable PPTX export. Accepts `slides_markdown: string[] \| null` — "Provide custom slide markdown instead of auto-generation." Storage: `DATABASE_URL` SQLAlchemy, "falls back to SQLite under app data". | **No — markdown is one-way in, state is a DB** |
| **Gamma** (VERIFIED by sub-research) | Generate API takes `inputText` with `cardSplit: 'inputTextBreaks'` — "You can control where cards are split by adding `\n---\n` to the text." But that is **API input only**. The in-app importer accepts .pptx/Google Slides/Docs/.docx/PDF/Notion/URL/pasted text — **`.md` is not in the list**, and its documented splitter is `/split`. Exports: "PDF, PNG, and PowerPoint (PPTX)" — no markdown out. | **No** |
| **Tome / Beautiful.ai / Canva / Pitch / Google** | All proprietary cloud state. Tome's deck product **shut down 2025-04-30** (REPORTED). Beautiful.ai's entire import/export section is PPTX/Google Slides/PDF — no markdown article exists. | **No** |
| **W3C b6+ slide editor** (VERIFIED, W3C talk 2026-03-25) | A genuine WYSIWYG + source editor that GET/PUTs the file it edits — but the file is **HTML**, not markdown. | No (wrong format) |
| **Typora** (VERIFIED, support.typora.io/Export) | Excellent WYSIWYG over markdown — **for documents**. No native slide mode; reveal.js only via a hand-configured Pandoc export. | Proves the pattern works for docs; nobody did it for slides |

### The killer datapoint

Gamma's own community board (community.gamma.app), post dated **2026-02-11**: a user requests `.md`
file upload because they generate slide files with Claude Code. Gamma staff reply "Will boost this
with the team! Just curious how you're using these with Gamma?" and file it to Canny. **As of
February 2026, markdown import is an open feature request at the $2.1B category leader.**

### Verdict on the gap

**The gap is real and specific.** Every WYSIWYG deck editor stores proprietary state (cloud JSON,
a DB, or HTML). Every markdown-native deck tool is a text editor with a preview pane. The single
crossing point — Slidev's `v-drag` — moves boxes and nothing else, and warns that its own
write-back mechanism is regex and may break.

Note the shape of the gap carefully: it is *not* "nobody can render markdown slides nicely" (many
can) and it is *not* "nobody can drag things" (Presenton, Gamma, Pitch all can). It is that **no
one has made direct manipulation the editing surface over a plain `---`-separated file on disk.**
Typora shows this is achievable for documents; Pithy and Nimbalyst (see `RESEARCH.md`) show it is
achievable for docs+sheets. The slides equivalent has not been built.

---

## D. Layout expressiveness — markdown is linear, slides are 2D

Every tool solves this the same way: **an escape hatch that is not markdown.** They differ in which
escape hatch, and how far it goes before you're writing HTML/CSS by hand. All syntax below is
quoted from docs I read on 2026-08-28.

### Marp / Marpit — YAML directives + image-keyword DSL + CSS

**Directives** (VERIFIED, `marpit/docs/directives.md`). Two spellings, both valid markdown:

```markdown
<!--
theme: default
paginate: true
-->
```

or YAML front-matter:

```markdown
---
theme: base-theme
style: |
  section {
    background-color: #ccc;
  }
---
```

Local directives apply to "defined page and following pages"; the `_` prefix makes them one-slide
("spot") directives:

```markdown
<!-- _backgroundColor: aqua -->
```

Global directives: `theme`, `style`, `headingDivider`, `lang`.
Local directives: `paginate`, `header`, `footer`, `class`, `backgroundColor`, `backgroundImage`,
`backgroundPosition`, `backgroundRepeat`, `backgroundSize`, `color`.

**No slide-separator markdown at all** is possible via `headingDivider`, which is how you keep a
file readable as a normal document:

```markdown
<!-- headingDivider: 2 -->

# 1st page
The content of 1st page

## 2nd page
Hello, world!
```

**Two-column** is done through the *image alt-text DSL* — Marp's most distinctive idea
(VERIFIED, `marpit/docs/image-syntax.md`):

```markdown
![bg left](https://picsum.photos/720?image=29)

# Split backgrounds

The space of a slide content will shrink to the right side.
```

With a size: `![bg left:33%](https://picsum.photos/720?image=27)`
Multiple backgrounds tile: `![bg vertical](a.png)` then `![bg](b.png)`.
Sizing: `![w:32 h:32](image.jpg)`, `![width:200px height:30cm](image.jpg)`.
Note: split/multiple backgrounds "will work only in experimental inline SVG slide" mode.

**Fragments** are encoded in the *list marker* (VERIFIED, `fragmented-list.md`): `-` is a normal
bullet, `*` is a fragmented one; `1.` normal, `1)` fragmented.

```markdown
* One
* Two
* Three
```

**Speaker notes** are HTML comments that aren't directives.

**Auto-scaling** (VERIFIED, marp-core `docs/markdown.md`): `# <!-- fit --> Fitting header` scales a
heading to slide width; code blocks and KaTeX blocks auto-shrink. Caveat quoted: "Auto scaling is
only horizontal. Content may still overflow the bottom of a slide."

**Slide size**: `size: 4:3` global directive; built-in themes ship `16:9` (1280×720, default) and
`4:3` (960×720).

**Themes** are plain CSS files with a required metadata comment: `/* @theme name */`.

**What can't be expressed:** arbitrary element positioning, non-half column splits without custom
CSS, per-element animation timing, transitions between slides. **The escape hatch is CSS** — the
`style:` directive or a theme file — and beyond that, raw HTML in the markdown.

### Slidev — per-slide YAML frontmatter + named layouts + Vue

Separator: "Use `---` padded with a new line to separate your slides." Frontmatter blocks *between*
those rules configure individual slides; the first block ("headmatter") configures the deck.

```md
---
theme: seriph
title: Welcome to Slidev
---

# Slide 1

---
layout: center
background: /background-1.png
class: text-white
---

# Slide 2
```

**Two columns** use a named layout plus `::slot::` markers (VERIFIED, `docs/builtin/layouts.md`):

```md
---
layout: two-cols
---

# Left

This shows on the left

::right::

# Right

This shows on the right
```

`two-cols-header` adds a spanning row above:

```md
---
layout: two-cols-header
---

This spans both

::left::
# Left

::right::
# Right
```

Built-in layouts: `center`, `cover`, `default`, `end`, `fact`, `full`, `image-left`, `image-right`,
`image`, `iframe-left`, `iframe-right`, `iframe`, `intro`, `none`, `quote`, `section`, `statement`,
`two-cols`, `two-cols-header`.

**Animations** (VERIFIED, `docs/guide/animations.md`):

```md
<div v-click> Hello </div>
<div v-after> World </div>
<v-click hide> Hidden after 2 clicks </v-click>
```

**Notes** are the trailing comment block:

```md
# Slide 2

The second page

<!--
This is _another_ note
-->
```

The doc is explicit that position matters: "This is NOT a note because it is not at the end of the
slide."

**Styling escape hatch** is deeper than Marp's: UnoCSS utility classes inline, scoped `<style>`
blocks, and optional **Comark** (formerly MDC) syntax enabled with `comark: true`:

```mdc
This is [red text]{style="color:red"} :inline-component{prop="value"}

![](/image.png){width=500px lazy}

::block-component{prop="value"}
The **default** slot
::
```

**What can't be expressed:** nothing, really — and that's the problem. The escape hatch is *Vue
components*, so a Slidev deck can stop being markdown entirely. Great for developers, disqualifying
for a file format normal users are supposed to own.

**Also notable:** Slidev ships a built-in **MCP server** since **v52.17.0 (released 2026-07-10)**,
at `http://localhost:<port>/__mcp`, so agents can read slides, update content and notes, and
insert/remove/reorder slides "through structured tools instead of raw text edits."

### Deckset — the richest DSL, and it's all bracket-commands (VERIFIED)

From Deckset's own first-party authoring reference at
`docs.deckset.com/skills/deckset-markdown-authoring/SKILL.md`. Global commands go at the top of the
file, consecutive, no blank lines; per-slide commands use `[.command: value]`.

- **Columns:** "Start each column with `[.column]`. Add each additional column by repeating
  `[.column]`" — N columns, not just 2.
- **Notes:** prefix a paragraph with `^`. Or globally, `paragraphs-as-presenter-notes: true`.
- **Fit headings:** `# [fit] Heading text`
- **Images** — a genuinely expressive alt-text DSL: `![](image.jpg)` full background,
  `![fit](image.jpg)`, `![left](image.jpg)` / `![right](image.jpg)` split, `![original 250%](…)`
  zoom, `![right alpha(0.6)](…)` opacity, `![inline](…)`, `![inline 50%](…)`,
  `![inline corner-radius(16)](…)`. Multiple inline images in sequence form a grid.
- **Builds:** `build-lists: true` / `all` / `notFirst`, and per-slide `[.build-lists: …]`.
- **Code highlighting steps:** stack `[.code-highlight: none]`, `[.code-highlight: 2]`,
  `[.code-highlight: 6-8]`, `[.code-highlight: all]` above the fence.
- **Transitions:** `fade`, `fadeThroughColor(#000000)`, `push(horizontal|vertical|top|right|bottom|left)`,
  `move(…)`, `reveal(…)`; e.g. `[.slide-transition: push(horizontal, 0.3)]`.
- **Other:** `autoscale: true`, `slidenumbers: true`, `slidecount: true`, `footer:` (with a `<<<` /
  `>>>` block form), `slide-dividers: #, ##, ###, ####`, `time-budget: 20`, `theme: Fira, 3`,
  `image-corner-radius: 12`, video/audio with `autoplay`/`loop`/`mute`/`![autoadvance](video.mov)`,
  Mermaid and Pikchr fences with `[.graph: …]` colour control.

This is the most complete answer anyone has shipped to "markdown is linear, slides are 2D" — and it
is Mac/iOS-only, closed-source, and PDF-out only. **It is the best available spec to steal from.**

### reveal.js / reveal-md / MkSlides — HTML comments as attribute carriers

reveal.js's markdown plugin (VERIFIED, revealjs.com/markdown) has the most awkward escape hatch,
because attributes must ride inside HTML comments:

```md
<!-- .slide: data-background="#ff0000" -->
```
```md
<!-- .element: class="fragment" data-fragment-index="1" -->
```

Separators are regex-configurable: default h-slide `^\r?\n---\r?\n$`, vertical slides via
`data-separator-vertical` (disabled by default), notes via `data-separator-notes` (defaults to
`notes?:`). External files load with `data-markdown="example.md"`.

reveal-md exposes these as flags — `--separator "^\n\n\n"`, `--vertical-separator "^\n\n"` — or as
per-file YAML front-matter (`separator: <!--s-->`, `verticalSeparator: <!--v-->`). MkSlides exposes
the same as YAML config: `separator: ^\s*---\s*$`, `separator_vertical: ^\s*-v-\s*$`,
`separator_notes: "^Notes?:"`.

No two-column primitive at all. **Two columns means writing a `<div>` grid yourself.**

### Pandoc / Quarto — fenced divs

The most portable escape hatch, and the only one that survives into PPTX and beamer (VERIFIED,
pandoc MANUAL):

```
:::::::::::::: {.columns}
::: {.column width="40%"}
contents...
:::
::: {.column width="60%"}
contents...
:::
::::::::::::::
```

```
::: notes

This is my note.

- It can contain Markdown
- like this list

:::
```

```
::: incremental

- Eat spaghetti
- Drink wine

:::
```

Quarto adds per-slide attributes on the heading: `## Title {.smaller}`, `{.scrollable}`,
`{footer=false}`, `{background-color="black"}`, `{background-image="…"}`, `{background-video="…"}`,
`{background-iframe="…"}`.

Slide carving rules, quoted: "A horizontal rule always starts a new slide. A heading at the slide
level always starts a new slide. Headings below the slide level… create headings within a slide…
Headings above the slide level… create 'title slides'."

**What can't be expressed:** column widths into PPTX (documented), pauses into PPTX (documented),
any absolute positioning anywhere.

### Summary of the expressiveness ladder

| Need | Marp | Slidev | reveal/reveal-md | Pandoc/Quarto | Deckset |
|---|---|---|---|---|---|
| Two columns | `![bg left]` (halves) or CSS | `layout: two-cols` + `::right::` | hand-written HTML | `::: {.columns}` w/ widths | `[.column]`, N columns |
| Image placement | alt-text keywords (`bg`, `left:33%`, `w:`, `h:`) | layouts + `v-drag` + UnoCSS | HTML | limited; `background-image` | richest alt-text DSL |
| Speaker notes | HTML comment | trailing `<!-- -->` block | `Note:` line | `::: notes` | `^ ` prefix |
| Fragments | list marker `*` / `1)` | `v-click` / `v-after` | `.element: class="fragment"` | `::: incremental` | `build-lists` |
| Transitions | ✗ (CSS only) | theme/addon | reveal config | reveal config | full DSL, per-slide |
| Sizing/overflow | `size:`, `<!-- fit -->`, auto-shrink | canvas size + UnoCSS | manual | manual | `autoscale`, `[fit]` |
| **Escape hatch** | **CSS theme** | **Vue components** | **raw HTML** | **fenced divs** | **bracket commands** |

The trade-off is stark: Marp's escape hatch (CSS) keeps the markdown file readable as a document;
Slidev's (Vue) does not.

---

## E. The AI-deck market, 2025–2026

Grounded, brief. Verification labels from the sub-research pass.

**Who's alive:**
- **Gamma** — the category winner. REPORTED (businesswire, 2025-11-10): **$68M Series B at a $2.1B
  valuation, ~$100M ARR, ~70M users, ~600k paying subscribers, ~50 employees, profitable since
  early 2024**, a16z-led.
- **Tome** — **dead as a deck tool.** REPORTED: pivot announced Oct 2024, presentation product shut
  down **2025-04-30**; team now builds Lightfield, an AI-native CRM. Users who hadn't exported lost
  their decks — a clean argument for file-based ownership.
- **Pitch** — alive, not acquired. VERIFIED changelog (pitch.com/whats-new): Pitch Agent
  **2026-05-27**, Teamspaces/SCIM 2026-06-30, "Introducing Pitch's MCP and API" **2026-08-12**.
  REPORTED: returned most VC to investors and cut ~78% of headcount in Jan 2024; survived smaller.
- **Presentations.ai** — REPORTED: **$3M seed led by Accel, ~2025-02-03**; claims 5M+ users.
- **Beautiful.ai, Canva, Google, Plus AI, Decktopus, SlidesAI** — all alive.

**What they store (the part that matters here): every one is proprietary cloud state. None stores a
file you own. None exports markdown.**
- Gamma (VERIFIED, help.gamma.app): "The available export formats are PDF, PNG, and PowerPoint
  (PPTX)."
- Beautiful.ai (VERIFIED): the entire import/export documentation section is PPTX in, PPTX/Google
  Slides/PDF out. No markdown article exists.
- Plus AI is the interesting counter-case (VERIFIED, plusai.com/free-tools): it writes **natively
  into Google Slides and PowerPoint**, so the artifact is a real file you own — but the format is
  OOXML, not markdown. Its 29 free converters include Word→PPT, PDF→PPT, HTML→PPT, URL→PPT,
  Wikipedia→PPT, YouTube→PPT — **and not one markdown tool.** They shipped an HTML converter before
  a markdown one.
- **Git story across the entire market: zero.** No branches, no diffs, no merge. Linear cloud
  version history is a restore-point list, not version control.

**Three directional signals:**
1. **Prompt-to-deck won commercially.** Gamma's numbers are the proof; Pitch Agent (2026-05) and
   Prezi Swoop (REPORTED, 2026-03) are followers.
2. **The bigger 2026 move is AI going *into* the incumbent file format, not away from it.**
   REPORTED: Claude for PowerPoint shipped as research preview **2026-02-05**, to all paid tiers
   **2026-02-20**, reading slide masters/layouts/fonts and emitting native editable elements;
   OpenAI shipped a PowerPoint-native sidebar; Google Workspace (workspaceupdates.googleblog.com,
   **2026-06-30**) has Gemini generating "fully native and editable" Slides from slides.new.
   **The industry's answer to "what should an agent write a deck into" was OOXML, not markdown.**
3. **The new interop surface is MCP and APIs, not file formats.** Gamma's public API (2025-11),
   Pitch's MCP + API (2026-08-12), Beautiful.ai's MCP. Vendors are letting agents *drive their
   cloud* while deliberately not letting the document out as text.

**Does markdown-native matter to this market? Today, barely — outside developers, essentially not
at all.** Slidev/Marp/reveal.js are framed consistently in 2026 as *developer* tooling. But the
demand signal is real and new: the pitch has shifted from "git-versioned slides, no more
`deck_final_v3_FINAL.pptx`" to **agent-friendliness** — text is a format an LLM edits with near-zero
error, which is exactly why Slidev shipped an MCP server and why a Claude Code user filed that
Gamma `.md` request.

**Slop backlash is real but doesn't push toward markdown.** REPORTED: Merriam-Webster's 2025 word
of the year was "slop"; CNN (2025-12-16) called 2026 "the year of anti-AI marketing". The backlash
rewards *authored* content and brand control, which incumbents answer with brand kits and template
fidelity — not with plain text.

---

## Recommendation for the project

**Wrap Marp (specifically Marpit + Marp Core as libraries, not the CLI).** Reasons:

1. **It is a library, not just a CLI.** `Marpit.render()` returns HTML + CSS from a string. That is
   the only way to drive a live editor. Slidev is a Vite dev-server architecture and reveal.js is a
   browser runtime — both are much harder to embed in an editing surface.
2. **The markdown stays a document.** Marp directives are YAML in HTML comments or front-matter, and
   the escape hatch is CSS. A Marp file still reads as prose in any editor — that's the point of
   `headingDivider`. A Slidev file with Vue components does not.
3. **MIT, four coordinated repos, all pushed within the last 3 weeks**, backed by a stable team
   (yhatt) since 2018.
4. **Its image-keyword layout DSL is the right shape for a visual editor** — `![bg left:33%](…)` is
   a small, closed vocabulary that a properties panel maps onto cleanly. Deckset's DSL is the
   richer superset to grow toward.

**Do not use Marp for PPTX export.** Its own README says the default is images and that
`--pptx-editable` has "lower slide reproducibility", drops speaker notes, requires LibreOffice, and
is still experimental after 19 months. For the "colleague opens it in PowerPoint" path, either shell
to **Pandoc with `--reference-doc`** (seven named layouts, real placeholders, notes and columns
intact) or generate directly with **PptxGenJS** — which is precisely what **Kova** already does.

**Watch Kova closely** (`KovaMD/Kova`, GPL-3.0, created 2026-05-04, v0.7.9 on 2026-08-23). It is the
nearest thing to this project's thesis that exists: `---` markdown on disk, PptxGenJS native-shape
PPTX out, and `!sheet` computed tables reaching into the spreadsheet problem. It is 4 months old,
GPL-3.0 (a licensing consideration if you intend to embed anything), and still a split-pane text
editor — not WYSIWYG. It is a competitor to study, and its exporter is the reference implementation
for markdown→editable-PPTX.

**Build the WYSIWYG layer.** That is the gap, and it is verified empty.
