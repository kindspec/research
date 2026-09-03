# D1 — The Prosecution: why the git-backed productivity substrate should not be built

Adversarial review, 2026-08-28. This document is deliberately one-sided. It is a
prosecution brief, not a survey. Its job is to state the strongest available case
for **do not build this**, with primary sources and locally reproduced evidence.
The single narrowest thing I could not kill is stated at the end, and only there.

Prior landscape work (`RESEARCH.md`, `findings/00`–`11`) is taken as given and not
redone. Where I re-ran one of its experiments I say so and show my own output.

---

## 0. The charge sheet

The proposal is a foundational, open-source, git-native substrate for three
primitives — sequential (documents), structured (tables/models/spreadsheets),
spatio-visual (canvases/diagrams/slides) — from which office applications
"emerge". Git supplies history, branching, merge, attribution, sync,
reproducibility.

Six of those seven claimed benefits are either already available without a new
substrate, or are not actually delivered by git on this data. I demonstrate both
below, on this machine.

| Claimed benefit of the substrate | Verdict |
|---|---|
| History | Already free, on binary Office files, with 3 lines of config (§1.2) |
| Diff | Already free, semantically, on `.docx`/`.xlsx`/`.pptx` (§1.2) |
| Attribution | **git actively destroys it on prose** (§5.4) |
| Merge | **git silently corrupts prose, or conflicts on every co-edit; the CRDT alternative interleaves it into nonsense** (§5.2–5.3, §5.6) |
| Branching | **Ink & Switch built it for writers, tested it, and deleted it**; 8/8 mainstream products are linear (§5.7, §5.11) |
| Sync / collaboration | **Structurally impossible: 12/12 pushes rejected** (§1.5) |
| Reproducibility | Already free, in 6 lines of `make` (§1.1) |
| "Plain text is durable/open" | Markdown is *less* standardised than OOXML (§4) |
| "Agents want plaintext" | A 444 ms `pandoc` call, and the plaintext is 5× larger (§6) |

---

## 1. THE COMPOSITION ARGUMENT

**Thesis: a competent user already has all three primitives today, in git, with
better properties than any unified substrate can offer — and the missing glue is
a weekend, not a system.**

The strongest stack I can assemble:

| Layer | Tool | Why it wins |
|---|---|---|
| Storage / history / sync | **git** + any forge | Unchanged. This is the substrate. |
| Sequential | **Markdown / Typst / LaTeX** edited in **VS Code / Obsidian / SilverBullet / Emacs org-mode** | Editor is a free market; the file is inert |
| Structured | **CSV / Parquet / SQLite** + **DuckDB / Datasette / csvkit / marimo** | Real query engine, not a toy formula lexer |
| Spatio-visual | **D2 / Graphviz / Mermaid / draw.io (uncompressed XML) / Excalidraw** | Text-source diagrams that genuinely diff |
| Slides | **Marp / reveal.js / Quarto / pandoc `-t pptx`** | Deck is a build artefact, not a document |
| Render / interop | **pandoc** (44 input, 65 output formats) + **LibreOffice headless** | 20 years, 645 contributors, every format on earth |
| Build / reproducibility | **make / just / Quarto** | Ordinary, debuggable, cacheable |

### 1.1 The whole thing, working, in 6 lines of `make`

Built from scratch on this machine. Sources tracked in git; every artefact
derived.

```
$ git ls-files | xargs wc -l
  1 .gitignore
  6 Makefile
 11 src/deck.md
  4 src/metrics.csv
  1 src/pipeline.dot
 10 src/report.md
 33 total

$ time make -s all
real    0m0.272s

$ ls build/
deck.pptx  metrics.md  pipeline.svg  report.docx  report.html
```

Six lines of `Makefile` take a markdown document, a CSV, a Graphviz source and a
slide deck source — **all three primitives** — and emit `.docx`, `.pptx`, `.html`
and `.svg` in 272 ms. Zero lines of new software were written. The build is
reproducible, cacheable and inspectable. **This is the reproducibility the
proposal promises, and it already exists.**

### 1.2 Kill-shot: git does not need plain text. Three lines of config.

The proposal's load-bearing premise is that git-native history requires
git-native *plain text* files. This is false, and it is trivially false.

```
$ git config diff.docx.textconv "pandoc -f docx -t plain --wrap=none"
$ git config diff.docx.cachetextconv true
$ echo '*.docx diff=docx' > .gitattributes
```

Then, after editing a **binary** Word document (heading changed, one table cell
changed):

```
$ git diff -- report.docx
diff --git a/report.docx b/report.docx
@@ -1,4 +1,4 @@
-Quarterly Report
+Q3 Board Report

 A paragraph with emphasis, strong, code, and a link.
@@ -11,7 +11,7 @@
   North                   10                      12

-  South                   8                       15
+  South                   8                       1500
```

I extended this to all three Office formats. `.xlsx` (a 14-line stdlib Python
extractor that also surfaces formulas):

```
$ git diff -- data.xlsx
-C3 15
+C3 1500
```

`.pptx` (a 5-line extractor):

```
$ git diff -- deck.pptx
 ## ppt/slides/slide1.xml
-Quarterly Report
+Q3 Board Report
```

**Total glue: 22 lines.**

```
$ wc -l xlsx2txt.py pptx2txt.py .gitattributes
  14 xlsx2txt.py
   5 pptx2txt.py
   3 .gitattributes
  22 total
```

And I wrote those 22 lines from nothing. Production-grade versions already ship:
`git-xlsx-textconv`, `docx2txt`, pandoc itself.

And this is not a hack I invented — it is git's own documented, first-class
answer to exactly this problem, using exactly this example.
`gitattributes(5)`, "Performing text diffs of binary files"
(<https://git-scm.com/docs/gitattributes>):

> "Sometimes it is desirable to see the diff of a text-converted version of some binary files. **For example, a word processor document can be converted to an ASCII text representation, and the diff of the text shown.** Even though this conversion loses some information, the resulting diff is useful for human viewing (but cannot be applied directly)."

Git's manual page reaches for *a word processor document* as its motivating case.
The proposal is arguing for a substrate to obtain a capability whose canonical
illustration in the git manual is the very file type the substrate wants to
abolish.

Stated honestly: `textconv` is one-way, so it powers `git diff`, `git log` and
`git show` but not `git apply` or merge. Per §5, however, git does not usefully
merge documents in *any* format, plain text included — so the substrate gains
nothing here either.

The proposal wants to change the world's file formats to obtain a feature that
git has shipped for nineteen years and that costs 22 lines to enable.

### 1.3 Kill-shot: the one thing only a "unified substrate" can do — 10 lines

The strongest remaining argument for a substrate is *cross-artifact reference*: a
document that cites a live computed value from a table. Ten lines of stdlib
Python:

```python
def q(sql, path):
    rows = list(csv.DictReader(open(path)))
    c = sqlite3.connect(':memory:'); cols = rows[0].keys()
    c.execute(f"create table t({','.join(cols)})")
    c.executemany(f"insert into t values({','.join('?'*len(cols))})",
                  [tuple(r.values()) for r in rows])
    return str(c.execute(sql).fetchone()[0])
txt = open(sys.argv[1]).read()
print(re.sub(r'\{\{([^|]+)\|([^}]+)\}\}',
             lambda m: q(m.group(2).strip(), m.group(1).strip()), txt))
```

Source document:

```markdown
Total Q3 throughput was {{src/metrics.csv | select sum(q3) from t}} units
across {{src/metrics.csv | select count(*) from t}} regions,
up from {{src/metrics.csv | select sum(q2) from t}} in Q2.
```

Output, verified:

```
Total Q3 throughput was 285 units
across 3 regions,
up from 240 in Q2.
```

…and it composes downstream with no further work: `pandoc` turns the resolved
document into a `.docx`. Quarto, R Markdown, Jupyter Book, Org-babel and Typst's
`#eval` all ship a hardened, maintained version of this same idea. The unique
selling point of a unified substrate is a `re.sub` and a `sqlite3` import.

### 1.4 Where the composition is architecturally *superior*, not merely adequate

1. **Independent failure domains.** Each component is separately maintained,
   separately funded, separately replaceable. Measured from the GitHub API today:

   | Component of the composition | Repo size | Contributors |
   |---|---:|---:|
   | pandoc (interop) | 69.7 MB | 645 |
   | IronCalc (formulas) | 16.7 MB | 35 |
   | Excalidraw (canvas) | 100.5 MB | 372 |
   | reveal.js (slides) | 34.8 MB | 363 |
   | Yjs (realtime sync) | 71.9 MB | 129 |
   | Typst (layout) | 139.2 MB | 462 |
   | DuckDB (tabular query) | 490.7 MB | 847 |
   | **subtotal** | **923.5 MB** | **2,853** |
   | LibreOffice core (Office fidelity) | 6,830 MB | 2,915 |
   | **total** | **7.75 GB** | **5,768** |

   The composition inherits 2,853–5,768 contributors of maintenance for free. A
   unified substrate either vendors these — and then owns the integration surface
   of all of them, forever — or reimplements them. There is no third option, and
   §7 prices both.

2. **Substitutability under vendor risk.** `RESEARCH.md` §2 already records that
   ProseMirror and CodeMirror archived every GitHub repo on 2026-04-01/04-15. In
   the composition, that is a swap of one editor. In a substrate that has built a
   bespoke live-preview decoration layer on CodeMirror 6, it is an existential
   dependency in the load-bearing component.

3. **The file formats are already the interface.** CSV, SVG, PNG, Markdown, DOT,
   `.mmd`, `.excalidraw`, `.drawio` — every one of these is consumed by dozens of
   independent tools. A new substrate's formats are consumed by exactly one tool:
   itself. This is the trap it claims to escape.

4. **Surface coverage is already complete.** GUI (VS Code, Obsidian, Excalidraw,
   LibreOffice). TUI (vim/emacs/helix). CLI (pandoc, duckdb, csvkit, d2, git).
   API (every one of these is a library). Agent (Filesystem + Git MCP servers —
   which, per `RESEARCH.md` §7, are the *only two* document-substrate reference
   servers the MCP steering group maintains, and it archived the Google Drive
   one). The substrate would ship one editor per primitive and lose four surfaces
   to gain zero.

5. **Local-first and self-host are properties of git, not of the substrate.** The
   proposal gets them by using git. So does the composition. Neither party can
   claim this.

### 1.5 The composition and the substrate share one fatal constraint — and only the composition is honest about it

Independently reproduced on this machine (this is `RESEARCH.md` §4's finding,
re-run from scratch by me, not copied):

```
TEST: two people save a shared document 12 times each
  second writer's pushes accepted: 0 / 12
  second writer's pushes REJECTED: 12 / 12

TEST: the standard fix (pull --rebase retry) when both edit the same line
  rebases that CONFLICTED: 8 / 8
  second writer's work that landed: 0/8

index.lock: 8 concurrent 'git add' in one worktree -> failures: 3 of 8
```

Git cannot host concurrent writers on one document. The composition never
promised it could, and users reach for Google Docs when they need it. The
substrate's pitch is *collaboration*, and it must therefore build a sync server,
a CRDT layer and a single-writer arbitration protocol **on top of** git — at
which point git is a serialisation format for an operational-transform system,
i.e. exactly the architecture the proposal claims to be an alternative to. See
§7.

### 1.6 What glue is genuinely missing — and how big it is

Honest inventory. I am not going to pretend the composition is seamless.

| Missing glue | Real size | Is a substrate the answer? |
|---|---|---|
| Cross-artifact live references | 10 lines (§1.3); or use Quarto | No |
| Semantic diff/blame of Office files | 22 lines (§1.2) | No |
| Cell-level 3-way CSV merge | `daff` (MIT), exists, works (`RESEARCH.md` §4) | No |
| One-click "publish this folder" | `make` + a CI workflow, ~20 lines | No |
| A single GUI shell over all three legs | **Real work — weeks to months** | Maybe |
| Realtime multi-writer collaboration | **Real system — years** | **No: git cannot, §1.5** |
| Per-file / per-block access control | **Real system — needs an auth server** (`RESEARCH.md` §6: no forge has per-file read ACLs) | **No: orthogonal to storage format** |
| Mobile | **Unsolved** — libgit2 and isomorphic-git implement neither partial clone nor sparse checkout; libgit2's sparse issue has been open 12 years (`RESEARCH.md` §4) | No |

Exactly **one** row — "a single GUI shell" — is a genuine product opportunity, and
it is a *shell*, not a substrate. The three rows that are genuinely hard
(realtime, ACLs, mobile) are **not solved by changing the file format**, and are
in fact made harder by insisting on git as the transport. The proposal's core
technical bet buys nothing on any of the three.


### 1.7 The spatio-visual leg is already solved by the composition

draw.io is Apache-2.0 and, per `RESEARCH.md` §6, defaults `compressXml` to false
— i.e. it is a full WYSIWYG canvas GUI whose native file is plain XML, one
`<mxCell>` per shape. Renaming one node:

```diff
-        <mxCell id="warehouse" value="Warehouse" style="rounded=0;" vertex="1" parent="1">
+        <mxCell id="warehouse" value="Lakehouse" style="rounded=0;" vertex="1" parent="1">
```

Graphviz, same edit:

```diff
-  warehouse [label="Warehouse"];
+  warehouse [label="Lakehouse"];
```

One-line diffs, stable ids, no version nonces, a free WYSIWYG editor, an
Apache-2.0 licence, and a 1.4 KB SVG out of the build. The third primitive is
done. It was done before the proposal was written.

**Verdict on axis 1: the composition wins on every axis the proposal claims,
except a unified GUI — and a unified GUI is an app, not a substrate.**

---

## 2. THE GRAVEYARD OF SUBSTRATES

**Thesis: this exact idea has been attempted, with vastly more money and talent,
at least a dozen times over sixty-six years. The failure mechanism is consistent,
architectural, and applies unchanged to this proposal.**

### 2.1 Xanadu (Ted Nelson, 1960–present, 66 years, never shipped)

Backed personally by Nelson, then by **Autodesk** (John Walker acquired ~80% in
1988) with a PARC-calibre team — Mark Miller, Dean Tribble, Roger Gregory, Marc
Stiegler. Cut off 1992. `OpenXanadu` demoed in 2014, fifty-four years in.

Gary Wolf, "The Curse of Xanadu", *Wired* 3.06, June 1995
(<https://www.wired.com/1995/06/xanadu/>):

> "Xanadu… is **the longest-running vaporware story in the history of the computer industry.** … **Xanadu has set a record of futility that will be difficult for other companies to surpass.**"

The mechanism, stated exactly:

> "**The Xanadu philosophy had always held that if a perfect back end could be created, the front end would take care of itself.** … in their quest for a 21st-century model, **they created a Byzantine maze.**"

And from Rob Jellinghaus, a Xanadu programmer, the single most transferable
sentence in this entire document:

> "'**The front end is the most important thing.** If you don't have a good front end, it doesn't matter how good the back end is. Moreover, **if you do have a good front end, it doesn't matter how bad the back end is.**'"

> "'There were links, you could do versions, you could compare versions, all that was true, **provided you were a rocket scientist**… **The more I worked at it, the more pessimistic I got.**'"

> "'What was I doing? **This is silly. This was silly all along.**'"

"A perfect back end and the front end will take care of itself" is a precise
restatement of "find the smallest set of primitives from which Docs, Sheets and
Slides emerge." It has a sixty-six-year track record and it is 0-for-66.

### 2.2 OpenDoc (Apple / IBM / Novell / SunSoft via CI Labs, 1992–1997)

The best-funded attempt at exactly this: documents composed of interchangeable
parts, no monolithic application, the document itself as the only interface.

**Mechanism A — the parts economy never existed.** Greg Maletic, OpenDoc Product
Marketing Manager at Apple
(<https://gregmaletic.wordpress.com/2006/11/12/opendoc/>):

> "**It didn't create a new economy around tiny bits of application code, and the document-centered model was never allowed to bloom as we had hoped.**"

> "Most folks at Claris, Apple's application group, didn't want it at all, **seeing it as an enabler for competition** to Claris's office suite product."

The consumer-side statement of the same problem (HN, `twoodfin`,
<https://news.ycombinator.com/item?id=27106195>):

> "For developers, the idea of being able to build and sell a little specialized widget of functionality… had obvious appeal. **But where would you find a customer excited about assembling their own word processor out of a dozen independently purchased components?**"

And the structural version (`mschaef`,
<https://news.ycombinator.com/item?id=27107735>), which transfers verbatim:

> "**The market didn't gravitate to hand-curated sets of best-of-breed office software. The market gravitated to MS Office with specific add ons for specific use cases.**"

**Mechanism B — the substrate's own API was the barrier.** Jens Alfke, OpenDoc
engineer at Apple 1993–1997
(<https://lobste.rs/s/tzhcnm/why_opendoc_failed_then_failed_3_more>):

> "OpenDoc's architecture was nicely divided up into components like Storage, Layout, Binding and Graphics, but **they were all pretty tangled up with each other. There was no hierarchy, there were no abstract interfaces separating them.**"

> "A 'Part Editor' had to implement an interface with something like **25 methods, all abstract**. This was really intimidating… Many of us argued for a 'DefaultPart' base implementation… but **the architect Kurt Piersol felt that would make OpenDoc a framework, and he didn't like frameworks.**"

**Mechanism C — the web won with less structure, not more.** Ex-Apple engineer on
OpenDoc's predecessor (HN, `twoWhlsGud`):

> "A world in a which a sea of interlinked richly structured documents existed would have likely been a world where the advantages of OpenDoc-like architectures would have mattered. **As it was the WWW… turned out to do just fine with loosely structured text and bitmap images.**"

**Mechanism D — Jobs, WWDC 1997**, on the record:

> "What about OpenDoc? What about it? **It's dead**, right? … **I think it was great technology but it didn't fit. The rest of the world isn't going to use OpenDoc.**"

> "**The hardest thing is: how does that fit in to a cohesive, larger vision, that's going to allow you to sell 8 billion dollars, 10 billion dollars of product a year?** And, one of the things I've always found is that **you've got to start with the customer experience and work backwards for the technology. You can't start with the technology and try to figure out where you're going to try to sell it. And I made this mistake probably more than anybody else in this room. And I got the scar tissue to prove it.**"

Apple's own VP and Chief Scientist, Larry Tesler, Computer History Museum oral
history (CHM Ref X6762.2013, p.45):

> "…**all the OpenDoc people said we should cancel the operating system and all the operating system people said we should cancel OpenDoc.** So I came back and I said… '**I think we should probably cancel both**'… **they died a slow death. We probably should have canceled them.**"

### 2.3 OLE / ActiveX compound documents (Microsoft, 1990–2001)

The compound-document paradigm shipped, by the vendor that won, with universal
distribution. The decisive exhibit is **Microsoft Binder** (Office 95/97/2000) —
compound documents as an actual product:

> "Microsoft Binder was an application originally included with Microsoft Office 95, 97, and 2000 that allowed users to include different types of OLE 2.0 objects… in one file. Originally a test host for OLE 2.0, **it was not widely used, and was discontinued after Office 2000.**"

Microsoft also shipped `unbind.exe`, a utility whose entire purpose was to take
compound documents apart back into ordinary files. **That is the paradigm's
epitaph, written by its own vendor.**

Microsoft then retired the words. MS Learn, "OLE Background"
(<https://learn.microsoft.com/en-us/cpp/mfc/ole-background>):

> "**OLE was originally an acronym for Object Linking and Embedding. However, it is now referred to as OLE.**"

The plumbing (COM, structured storage, automation) survived and won. **The
user-facing compound document — which is what a universal substrate is — is the
part they stopped naming.** And in practice, per `AndrewStephens` on lobste.rs:

> "**Even if everything worked perfectly, the use experience was weird. Different parts of your documents have different UIs.**"

Joel Spolsky, then at Microsoft, "Don't Let Architecture Astronauts Scare You",
2001 (<https://www.joelonsoftware.com/2001/04/21/dont-let-architecture-astronauts-scare-you/>):

> "**Remember that the architecture people are solving problems that they think they can solve, not problems which are useful to solve.**"

### 2.4 Chandler (OSAF, 2001–2009) — the closest analogue, and it is very close

Funded by **Mitch Kapor personally (~$5M)** plus **$1.5M + $98K from Mellon** and
**$1.25M from 25 universities** — roughly **$8M**, peak staff **27**.

Its own vision document
(<http://web.archive.org/web/20150220054247/http://www.osafoundation.org:80/Chandler_Compelling_Vision.htm>)
should be read as if it were the proposal under review:

> "Chandler will have a rich ability not only to associate and interconnect items, but also to gather and collect related items in a single place… **mixing-and-matching email, mailing lists, instant messages, appointments, contacts, tasks, free-form notes, blogs, web pages, documents, spreadsheets, slide shows, bookmarks, photos, MP3's, and so on**… Data in Chandler is stored on repositories on the user's local machine, on others' machines, and on shared resources such as servers."

> "**Chandler's decentralized, server-optional architecture**, which permits easy self-management of collaborative environments…"

> "Besides being a powerful application, **it's also an extensible platform.**"

Universal primitives, local-first, decentralized, extensible. **It shipped a
calendar.** Scott Rosenberg, who embedded with the team for three years and wrote
*Dreaming in Code*
(<https://networkcultures.org/geert/2008/09/25/interview-with-scott-rosenberg-about-dreaming-in-code/>):

> "**It's important to remember, too, that Chandler didn't start out as a calendar — it began as a much more ambitious project for organizing personal information and sharing all sorts of stuff. The calendar was what emerged when the ambitions had to be scaled back.**"

Contemporaneous diagnosis, LWN (<https://lwn.net/Articles/264385/>):

> `emk`: "**Even in the commercial world, I've seen very few organizations dedicated to such generalized and abstract software. This is a pretty risky path to take — it's nice to have a clean architecture, but if you can make enough simplifying assumptions, you'll get a product out the door much sooner.**"
>
> `hazmat` (contributor): "**it had the feel of abstract java apis in python.**"
>
> Bruce Perens: "**OSAF was a classic example of how not to do an Open Source project, by applying big-company software engineering practices and spending lots of money, over lots of years.**"

**And the "server-optional" architecture grew a server.** The Mellon and CSG money
"primarily funded work on the CalDAV standard, including the initial work on the
**Chandler Server** and work to make the Desktop application a CalDAV client."
The decentralized substrate shipped as a client for a centralised calendar server
(<https://www.chandlerproject.org/osaffaq/>).

Finally, OSAF's own diagnosis of the category, written in 2001 as an argument
*for* the project (<https://www.chandlerproject.org/osafhistory/>) — read it in
2026 as the argument against:

> "**Development costs are high, distribution channels are limited, and barriers to entry are significant. The chance is small that the traditional venture-capital-backed model of software development will fill this need.**"

### 2.5 Groove and Lotus Notes (Ray Ozzie) — universality achieved, and still fatal

**Groove**: founded 1997; Microsoft invested $51M at a $250M valuation (Oct 2001),
then bought the company for **$120M in March 2005** — a ~50% down round in four
years. Office Groove 2007 → SharePoint Workspace 2010 → **removed in Office 2013**.

The kill shot is Microsoft's own deprecation table
(<https://learn.microsoft.com/en-us/previous-versions/office/office-2013-resource-kit/cc178954(v=office.15)>),
which lists the **peer-to-peer layer as a separate End-of-Life item** from the
product:

> **"SharePoint Workspace Peer-to-Peer Functionality — End of life:** All functionality related to the peer-to-peer aspects of SharePoint Workspaces are removed."
>
> **Replacement for the product:** "**OneDrive for Business client for Windows… lets users take doc libraries offline for SharePoint and sync them.**"

**The vendor amputated the peer-to-peer topology and kept the sync engine.** The
winning shape was a canonical copy on a server plus a dumb offline cache — which
is, precisely, what git-as-a-document-substrate is not.

Ray Ozzie — the only person who built two universal document substrates and got
both to mass adoption — "Dawn of a New Day", 2010
(<http://web.archive.org/web/20101026080811/http://ozzie.net/docs/dawn-of-a-new-day/>):

> "**Complexity kills. Complexity sucks the life out of users, developers and IT.** … And as time goes on and as software products mature – even with the best of intent – **complexity is inescapable.**"

> "**even when superhuman engineering and design talent is applied, there are limits to how much you can apply beautiful veneers before inherent complexity is destined to bleed through.**"

> "Those who build and deploy application fabrics targeting connected devices understand **how challenging it can be to simply & reliably just 'sync' or 'stream'.**"

And the sentence that voids a files-and-folders substrate outright:

> "The early adopters among us have decidedly begun to **move away from mentally associating our computing activities with the hardware/software artifacts of our past such as PC's, CD-installed programs, desktops, folders & files.**"

**Lotus Notes** is the strongest exhibit precisely because it *succeeded*:
hundreds of millions of seats, IBM's enterprise machine behind it, bought for
$3.5B in 1995 — and sold to HCL in 2018 inside a ~$1.8B bundle, as a punchline.
Universality was achieved. It was not sufficient.

### 2.6 Fossil SCM — the live control experiment, and D. Richard Hipp's own verdict

Fossil is the cleanest natural experiment available: a genuinely excellent
integrated substrate (SCM + wiki + tickets + forum + chat in one SQLite file),
maintained for twenty years by the author of the world's most-deployed database.
Stack Overflow Developer Survey 2022: **Git 93.87%** of all respondents, **96.65%**
of professionals — "No other technology is as widely used as Git." **Fossil is not
an answer option.**

**Warren Young**, co-author of Fossil's own *Fossil Versus Git*
(<https://fossil-scm.org/forum/forumpost/2f63cce407d3d49c>):

> "**Git effectively has a global monopoly on DVCSes, and I don't see how you replace such a thing.** … **Replacing Git with something better looks impossible.**"
> "**It's really easy to set up a basic Fossil server, but it's not as easy as signing up for a GitHub account.**"

**Stephan Beal**, core developer, "Lessons from 13+ Years of Fossil"
(<https://fossil-scm.org/forum/forumpost/2eb86fc758ea3322>):

> "**Though DVCS inherently promises us the ability to work independently, in practice we simply don't do so. We still collectively like to have a central authority, an 'official upstream.'**"

**And the single most damaging technical citation in this document — D. Richard
Hipp, in the same thread:**

> "**Git/Fossil works well for source code files. They do not work as well for large binary artifacts such as images, sound files, and audio files. In particular, there are no good ways (at present) to do concurrent editing or merging of these kinds of binary artifacts. As far as I know, this is still an open problem. Nobody has come up with a good solution. If you solve this problem, you will likely become famous.**"

Documents, tables and canvases are exactly that class of artifact. §5 of this
document is the empirical demonstration of Hipp's claim on markdown prose. **The
proposal is a bet that a problem the author of SQLite calls open, unsolved and
fame-making gets solved incidentally, en route to shipping an office suite.**

### 2.7 Beaker Browser (Paul Frazee, 2016–2022) — the richest post-mortem available

Archived 2022-12-27. Frazee's `archive-notice.md`
(<https://github.com/beakerbrowser/beaker/blob/master/archive-notice.md>) reads
like a pre-registered failure analysis of this proposal:

> "**On the APIs, I quite simply failed. The pure P2P model gives you a set of really great wins — no backend/frontend separation, local data, offline-first, easily-forked apps, and so on — but then hits you with a cavalcade of challenges.** Without some logically centralized repository of data or router of messages, you struggle with discovery and delivery. Users don't stay consistently online and connections will randomly fail, so you struggle with availability and performance… **Debugging is quite hard. Managing resource usage on the device is hard.**"

Note the structure: he lists the exact benefits this proposal leads with, then
itemises the costs that consumed them.

**He tried the "files plus a local index" data model twice and killed it twice:**

> "We went through at least two very significant API designs that never got released. Both of them were modeled as a local 'crawling indexer' which would gather views of data published in hyper sites (**via json and md**) and then could be queried by apps… **However I was never satisfied with the results because they couldn't patch over the core problems I listed above, and I tanked the releases.**"

On adoption:

> "**actual usage stalled** … we were failing to give users something they wanted, and the flailing was just adding bloat instead of solving the real problem: **that Beaker didn't solve a problem for people.**"
> "In hindsight, **Beaker's MVP was a tool for making static websites. That's it.**"

And the go/no-go rule, usable directly:

> "**The trick, you see, is that every % that isn't 'easy' is not just difficult: it's *hard*.** … **That means a project needs to feel 80-90% easy to actually succeed, and frankly I'd caution against anything that's not '90% easy.'** … When I look at Beaker, I think it was probably 50% easy."

His trajectory since is the argument in miniature: pure P2P (Beaker, dead) → P2P
home server (Atek, dead, domain no longer resolves) → **federated servers with
P2P-shaped data (Bluesky, alive)**:

> "**The pure p2p tech out there still has a lot of potential, but I think it's a bad fit for large scale social networks and sticking with it for Bluesky would've been a mistake.**"
> "**Pay more attention to the market than I did.**"

### 2.8 Solid / Inrupt (Tim Berners-Lee, 2016–present) — the best-credentialed version, and the numbers

~**$46M raised**, including a $30M round in 2021, led by the inventor of the World
Wide Web. Adoption, from the Solid community's own forum, May 2024
(<https://forum.solidproject.org/t/statistics-about-the-solid-community/7531>):

> **bourgeoa**, maintainer of the flagship pod host: "**As of today there are 62209 accounts versus 61023 accounts about one year ago.**"

**+1,186 accounts in twelve months — about three sign-ups a day, worldwide, in
year eight.** The next-largest providers were counted by another maintainer thus:

> "on solidweb.org we have **3145 users**. on solidweb.me we have **573 users**. (evaluated with a `ls | wc -l` in the pod directories.)"

**After eight years, the ecosystem measures itself with `ls | wc -l`.**

The structural critique is the direct hit on "documents, tables and canvases as
plain files". Leigh Dodds, former Director of Delivery at the Open Data Institute
— a friendly, semantic-web-native critic
(<https://blog.ldodds.com/2024/03/12/baffled-by-solid/>):

> "**The API to a Solid Pod is essentially a document store that supports capturing additional metadata about the stored resources. But it doesn't provide me with a way to query or search over the data that my application has stored? If I need that… then I'll still need to build a separate data store. This means that I'm still going to have to deal with security, privacy, GDPR, etc. It's not saving me any implementation time in building a secure system.**"

> "**Solid has no built in understanding of any specific schemas or formats. Or recommended ways to structure data.**"

> "**It still all feels very much like an idea trying to find a solution.**"

And from Solid's most prolific independent app developer, in a post *defending*
Solid (<https://noeldemartin.com/blog/why-solid>):

> "**Solid's vision is so broad and all-encompassing, that it doesn't have the same meaning to everyone.**"
> "**In 4 years, we've only had 3 versions of the core specification… And we're still lacking essential features for any developer used to traditional databases like modification timestamps, pagination, or search.**"

Finally, the pivot. inrupt.com today sells "**Enterprise Wallet Infrastructure**"
and "**AI That Actually Knows Your Customers**", under the heading:

> "**Own the Customer Relationship** — When you know your customers this well, **they won't switch to generic AI alternatives. Lock in loyalty in ways that they can't possibly match.**"

**The company founded to break vendor lock-in over personal data now markets
lock-in.** "Solid" survives on the site as a nav item under Resources.

### 2.9 Also in the ground

- **WinFS** (Microsoft, ~1998–2006): the universal typed object store meant to
  replace files and folders. Cancelled 2006-06-23; Quentin Clark's own notice:
  "**we are not pursuing a separate delivery of WinFS**… with most of our effort
  now working towards productizing mature aspects of the WinFS project into SQL
  and ADO.NET." Counting Cairo/OFS, Microsoft spent ~15 years and shipped **no**
  universal object store to any user, ever.
- **Google Wave** (2009–2010): a universal collaborative document substrate with
  an open federation protocol, an open-sourced core, and the inventors of
  operational transform. Killed in 15 months. "**Wave has not seen the user
  adoption we would have liked.**"
- **Fission** (2019–2024, VC-backed, authors of UCAN and **WNFS — literally a
  files-as-substrate project**): "**In Q4 of 2023, it was clear that our
  hypothesis of getting paid directly for protocol research wasn't going to
  work.**" `fission.codes` no longer resolves — *a substrate whose own vendor's
  archive 404s is poor evidence for durability.*
- **Textile** (2017–2023): ~100,000 developer accounts, ~113,000 databases, then
  shut down and deleted, with the honest finding: "**We're sad to let the Hub go,
  but it was never meant to be a long-term solution… As it turns out,
  centralized on-ramps tend to be sticky!**"
- **Bento** (Apple's OpenDoc container format): died with OpenDoc. Per Alfke, the
  engineer next door: "**the guy who implemented the Bento structured-storage
  engine had ignored error handling beyond calling a generic 'panic' hook when
  any allocation or file I/O returned an error.**" A universal container format
  with no error recovery.
- **Project Oberon** (Wirth & Gutknecht, ETH Zürich, 1985–): the purest
  integrated substrate ever built — OS, language, compiler, GUI in ~10,000
  lines, by a Turing Award winner, still published and still maintained. Adoption
  outside ETH Zürich over forty years: effectively nil. **Proof that
  architectural coherence, minimality and a Turing-Award-winning designer are
  jointly insufficient.**

### 2.10 The six recurring mechanisms

Every project above died of at least three of these. **None died of "too early".**

1. **The substrate has no user; only applications have users, and they never
   arrive.** Wolf on Xanadu: *"if a perfect back end could be created, the front
   end would take care of itself."* Jellinghaus: *"if you do have a good front
   end, it doesn't matter how bad the back end is."* Frazee: *"Beaker didn't
   solve a problem for people."* Dodds on Solid: *"an idea trying to find a
   solution."* Jobs on OpenDoc: *"you've got to start with the customer
   experience and work backwards for the technology."*
2. **The parts economy never materialises; nobody wants to assemble their own
   tool.** *"where would you find a customer excited about assembling their own
   word processor out of a dozen independently purchased components?"*
3. **Files-plus-metadata is not a data layer; every app rebuilds the index
   anyway.** Dodds: *"it's not saving me any implementation time."* Frazee tanked
   two json-and-markdown crawling-indexer designs. This is the direct hit on
   "three primitives as plain git-native files."
4. **Concurrent editing and merging of non-line-oriented artifacts is an open
   problem** — per D. Richard Hipp, *"Nobody has come up with a good solution."*
   §5 demonstrates it empirically on markdown.
5. **Someone always pays for availability; decentralising relocates that bill
   onto a party with no revenue.** Groove's P2P layer amputated in favour of
   server sync; Chandler's "server-optional" architecture grew a server; Textile
   deleted 113,000 databases; Fission ran out of money; Fossil: *"not as easy as
   signing up for a GitHub account."*
6. **The incumbent's network effect is terminal, and the challenger's own
   maintainers say so.** *"Replacing Git with something better looks
   impossible."* The same sentence, with `Git` replaced by `Microsoft 365`, is
   the sentence that ends this proposal.

**Not verified in this pass, and named as a gap:** Subtext/Subconscious/Noosphere
(Gordon Brander), Anytype, Muse/Fermat, and Ink & Switch's abandoned prototypes
(Capstone, Pushpin, Farm, Cambria). These are the most contemporary and
rhetorically relevant cases and they are unresearched here. They should be closed
before this brief is relied upon — though note that the prosecution does not need
them: the six mechanisms above are already established from ten independent
projects across sixty-six years.

---

## 3. SUBSTRATE WITHOUT APPS IS WORTHLESS

**Thesis: every substrate that won, won attached to an application that was
already indispensable. This one has no such app, and its candidate apps are
worse-than-Google clones.**

- **git** shipped in 2005 because the Linux kernel — the largest and most
  politically fraught codebase on earth — lost BitKeeper and needed a successor
  *that week*. Git's first user was a captive audience of a thousand kernel
  developers with no alternative. Adoption was not persuasion; it was necessity.
- **SQLite** won by being embedded where the user never chose it: Android, iOS,
  Firefox, Chrome, Python's stdlib. Its distribution was other people's
  applications.
- **PostgreSQL** won by speaking SQL — i.e. by being *compatible with the
  incumbent interface*, not by proposing a better one.
- **Unix** had C and the phone company.

### 3.1 The primary record on every substrate that won

**Unix — kept alive by one department's word processing.** Dennis Ritchie, *The
Evolution of the Unix Time-Sharing System* (<https://9p.io/cm/cs/who/dmr/hist.html>):

> "At the time of the placement of the order for the PDP-11, it had seemed natural, or perhaps **expedient**, to promise a system dedicated to word processing."
>
> "In early summer, editor and formatter in hand, we felt prepared to fulfill our charter by offering to supply a text-processing service to the Patent department… **Not only did the Patent department adopt Unix, and thus become the first of many groups at the Laboratories to ratify our work**, but we achieved sufficient credibility to convince our own management to acquire one of the first PDP 11/45 systems made."

The most influential substrate in computing history survived because one internal
customer needed to file patents.

**Git — a crisis tool its author wrote for himself, and explicitly *not* a
general system.** Linus Torvalds, LKML, "Re: Kernel SCM saga..", 2005-04-07
(<https://marc.info/?l=linux-kernel&m=111288700902396&w=2>), days after the
BitKeeper licence withdrawal:

> "Anyway, the reason I can do it quickly is that **my scripts will not be an SCM**, they'll be a very specific 'log Linus' state' kind of thing."

And in retrospect, GitHub Blog, 2025-04-07
(<https://github.blog/open-source/git/git-turns-20-a-qa-with-linus-torvalds/>):

> "I'll do something that works for me, and **I won't care about anybody else**."
>
> "I did it for my own very selfish reasons."

Git had a thousand captive kernel developers with no alternative, that week.
Adoption was not persuasion; it was necessity. The proposal has neither the
crisis nor the captive audience.

**SQLite — positioned *below* the incumbent, distributed inside other people's
apps.** <https://www.sqlite.org/about.html>:

> "Think of SQLite not as a replacement for Oracle but as a **replacement for `fopen()`**"

<https://www.sqlite.org/mostdeployed.html>: "SQLite is likely used more than all
other database engines combined" — via Android, iOS, macOS, Windows 10/11,
Firefox, Chrome, Safari, PHP and Python. **SQLite did not acquire a billion
users; it rode inside other people's killer apps.** The proposal is asking users
to *replace* their tools, which is the opposite move.

**PostgreSQL — won by surrendering its own superior interface.**
<https://www.postgresql.org/docs/current/history.html>:

> "In 1994, Andrew Yu and Jolly Chen added an SQL language interpreter to POSTGRES… **The query language PostQUEL was replaced with SQL.**"

Berkeley POSTGRES had a technically interesting query language and went nowhere
with it. It became the world's most popular open-source RDBMS only after it
adopted the incumbent standard. The vestigial `libpq` name is the fossil of the
language it gave up. This is the exact trade in front of the proposal — a
better-designed interface versus an entrenched one — and the case study says the
entrenched one wins.

### 3.2 And the record on substrates that shipped without apps

**Google Wave.** Urs Hölzle, SVP, official Google Blog, 2010-08-04:

> "Wave has not seen the user adoption we would have liked."

Wave was technically extraordinary: operational transformation, character-level
realtime, an **open federation protocol**, an open-sourced core. It shipped a
protocol and a substrate and asked the world to bring the applications. Nobody
did. **Wave is the exact shape of this proposal — and it had Google's
distribution.**

**Windows Phone.** Joe Belfiore, Microsoft CVP, 2017-10-08 (reproduced verbatim
across contemporaneous coverage; the original tweets are gone):

> "We have tried VERY HARD to incent app devs. Paid money.. wrote apps 4 them.. but **volume of users is too low for most companies to invest**."

Microsoft had the capital, the OS, the OEM relationships, the retail channel and
a well-reviewed product. It lost on application volume alone. That is the purest
available statement that a technically sound platform dies without the apps.


### 3.3 Now the proposal

Its candidate killer apps are: a markdown editor (Obsidian,
VS Code, Typora, SilverBullet already exist and are better), a spreadsheet
(Excel), and a deck tool (PowerPoint, Google Slides, Gamma). Per `RESEARCH.md` §8,
"the build is no longer the moat… **Distribution is the binding constraint, and
every project in this space has failed at it.**" That is the correct diagnosis and
it is fatal, because a substrate's *only* route to distribution is an app people
must have.

The most instructive data point is Nimbalyst's own history. Its ancestor
`stravu/crystal` — "run multiple Codex and Claude Code AI sessions in parallel git
worktrees" — reached **3,113 stars**. The rebranded suite,
"the open-source visual workspace… markdown, mockups, and diagrams,"
sits at **1,596 stars**, less than half. The killer app was the *agent
orchestrator*. The office suite is the part that came after, and it is the part
that did not travel.

And on the demand side, `RESEARCH.md` §7 records the trend line: Penflip 181 HN
points (2013) → Moment.dev 29 → Perchpad **2** (2026). Enthusiasm for this exact
pitch has declined by two orders of magnitude in thirteen years while the
technology got easier. That is a market saying no with increasing confidence.

---

## 4. THE FORMAT-LOCK ARGUMENT

**Thesis: OOXML is already the durable, open, standardised, inspectable format.
"Plain text" is a developer aesthetic. And on the specific axis the proposal cares
about — *being a specified format* — Markdown is strictly worse than `.docx`.**

### 4.1 `.docx` is a ZIP of XML. Verified locally, not asserted.

```
$ pandoc src.md -o report.docx && unzip -l report.docx
  1933  [Content_Types].xml
   722  _rels/.rels
  4659  word/document.xml
  1366  word/_rels/document.xml.rels
  3345  word/numbering.xml
 21408  word/styles.xml
  1133  word/footnotes.xml
   625  word/comments.xml
   583  docProps/core.xml
  ...   16 files
```

```xml
<w:p>
  <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
  <w:r><w:t xml:space="preserve">Quarterly Report</w:t></w:r>
</w:p>
```

That is the Open Packaging Conventions. It is inspectable with `unzip` and
`grep`. It has a published ISO standard (ISO/IEC 29500 / ECMA-376). It has
first-class read/write libraries in every language in production use. The
proposal's format has none of these and would need to earn all of them.

### 4.2 Kill-shot: Markdown is not one format. It is at least nine.

pandoc, the most authoritative implementation in existence, treats Markdown as
**nine mutually distinct output formats**:

```
$ pandoc --list-output-formats | grep -E '^(markdown|commonmark|gfm|markua)'
commonmark  commonmark_x  gfm  markdown  markdown_github
markdown_mmd  markdown_phpextra  markdown_strict  markua
```

I converted **one** source document to all nine. All nine outputs are byte-distinct:

```
$ md5sum out.*.md | awk '{print $1}' | sort -u | wc -l
9
```

Sizes ranged from 338 to 654 bytes for the same content — a 1.9× spread, because
the dialects disagree about what is expressible at all.

### 4.3 Kill-shot: the only *ratified* Markdown spec cannot express a table

CommonMark is the sole standardisation effort. It has no tables. Asked to emit
the source document's table in CommonMark, pandoc gives up and emits raw HTML:

```html
<table>
<thead><tr class="header"><th>Region</th>
<th style="text-align: right;">Q1</th>...
```

And the definition list degraded silently to a hard-wrapped paragraph — semantics
destroyed, no warning.

This is fatal to the proposal on its own terms. The proposal's thesis is that
three primitives compose. In the actual standardised plain-text document format,
**the sequential primitive cannot contain the structured primitive.** The bridge
is a vendor extension (GFM tables), and GFM tables have no colspan, no rowspan, no
cell types, no number formats, no formulas. Meanwhile `word/document.xml` embeds a
fully specified table model, and `xl/worksheets/sheet1.xml` embeds a fully
specified formula model, both in an ISO standard, both `unzip`-able.

**The proposal would replace a single 6,000-page ISO standard with nine unspecified
dialects, none of which can express a table, and then invent a tenth.**

### 4.4 The precedent: ODF was better, standardised, government-mandated, and lost

ODF (ISO/IEC 26300) is XML-in-ZIP, vendor-neutral, ISO-standardised, and was
backed by Sun, IBM, and multiple national governments with procurement mandates.
It lost. If a technically clean, ISO-ratified, IBM-and-Sun-backed, legally
mandated open document format could not displace `.doc`, the prior probability
that a new unspecified plain-text format displaces `.docx` is not low, it is
negligible. The proposal must explain what it has that ODF did not, and "it is in
git" is not an answer to a distribution problem.

### 4.5 The binary format is *smaller* than the plaintext

Same 50-page document, measured here:

```
markdown source : 145,584 bytes
docx (zipped)   :  28,457 bytes
```

**The "bloated binary" is 5.1× smaller than the "lean plain text."** Because it is
a ZIP. The plain-text durability argument is aesthetic, and on the one
quantitative axis available it points the other way.

### 4.6 The spec is free, and I am not the first to check

- **ECMA-376, "Office Open XML file formats"**, 5th edition (Dec 2021), four
  parts, direct-linked ZIPs, no login, no paywall:
  <https://ecma-international.org/publications-and-standards/standards/ecma-376/>.
  Part 1 (Fundamentals and Markup Language Reference) is 5,039 pages; Part 2
  (**Open Packaging Conventions**) 95; Part 3 (Markup Compatibility) 43; Part 4
  (Transitional) 1,553. **Total 6,730 pages**, plus machine-readable **W3C XSD
  and RELAX NG schemas**.
- **ISO/IEC 29500-1:2016**, Fourth edition 2016-11-01, downloaded free (29.7 MB)
  from ISO's Publicly Available Standards portal; 5,036 pages. Title page:
  *"Information technology — Document description and processing languages —
  Office Open XML File Formats — Part 1"*. ISO's own catalogue states the latest
  version of each part is made available **at no charge**.

The 6,730 pages will be waved as evidence of bloat. It is the opposite. **That
page count is the measured size of the problem domain.** Documents, spreadsheets
and presentations *are* that complicated. Replacing 6,730 specified pages with
~60 pages of CommonMark does not simplify the domain — it **declines to address
99% of it** and pushes the difference onto every downstream consumer as undefined
behaviour. Complexity you refuse to specify does not vanish; it becomes each
implementer's private guess. That is exactly how Markdown got into the state
below.

A `.docx` produced by pandoc **machine-validates against the official ECMA
schema**. There is no equivalent operation for a Markdown file, because there is
nothing to validate against.

### 4.7 CommonMark's own homepage is a confession

<https://commonmark.org/>, verbatim:

> "**John Gruber's canonical description of Markdown's syntax does not specify the syntax unambiguously.**"
>
> "**Because there is no unambiguous spec, implementations have diverged considerably over the last 10 years.**"
>
> "users are often surprised to find that a document that renders one way on one system (say, a GitHub wiki) renders differently on another"
>
> "**because nothing in Markdown counts as a 'syntax error,' the divergence often isn't discovered right away.**"

**Markdown has no failure mode.** A malformed document does not error; it silently
renders wrong. That is the single worst property a version-controlled storage
format can have, and it is the property the proposal's substrate would inherit for
all three primitives.

The CommonMark spec has been at **0.x for twelve years** — 0.5 (2014-10-25)
through **0.31.2 (2024-01-28)**, no release since. **GFM's spec is "Version
0.29-gfm", dated 2019-04-06** — seven years stale, still 0.x, and it concedes that
GitHub "**perform[s] additional post-processing and sanitization after GFM is
converted to HTML**", i.e. **even GFM's spec does not describe what GitHub
actually renders.** Note the irony the proposal must swallow: **GFM is a
single-vendor format controlled by Microsoft.** The proposal escapes Microsoft's
ISO-standardised format by adopting Microsoft's un-standardised one.

**And the format's author refused standardisation on the record.** When the
CommonMark team launched as "Standard Markdown" in Sept 2014, Gruber called the
name "infuriating" and demanded a rename, a domain shutdown and an apology;
Atwood's account records that **no form of the word "Markdown" was acceptable**.
Gruber had been invited to participate in Nov 2012 and again on 2014-08-19 with a
spec link, and did not respond either time. His position was that standardisation
was wrong in principle: *"Different sites (and people) have different needs. No
one syntax would make all happy."*

Compare: ECMA-376 is on its 5th edition, ISO/IEC 29500 on its 4th, both under
formal revision processes.

### 4.8 Divergence, reproduced across three parsers

Same input, three mainstream parsers (Python-Markdown 3.7, markdown-it-py 3.0.0 in
CommonMark mode, Pandoc 3.1.11.1). **6 of 8 cases diverged.** The two that matter
most:

| Input | Python-Markdown | markdown-it (CommonMark) | Pandoc |
|---|---|---|---|
| a GFM pipe table | `<p>\| a \| b \|…</p>` — **literal pipe soup** | `<p>\| a \| b \|…</p>` — **literal pipe soup** | `<table>…</table>` |
| `- a` / `  - b` (2-space sublist) | **flat list of 2** — tree structure destroyed | nested list | nested list |
| `*foo *bar* baz*` | `<em>foo </em>bar<em> baz</em>` | `<em>foo <em>bar</em> baz</em>` | `<em>foo </em>bar* baz*` |

**A table — the single most load-bearing artifact in any "sheets" proposal —
renders as a table in one parser and as literal text in two others. Silently. With
no error.** And an indented sublist silently *flattens*, destroying the document
tree, with no diagnostic.

An entire diagnostic tool exists because of this. Babelmark's FAQ
(<http://babelmark.github.io/faq/>):

> "**The official markdown syntax documentation is silent or vague on many issues, and implementations have diverged in their interpretations of the syntax.**"

There is no Babelmark for OOXML, because OOXML has a schema.

### 4.9 The structured and spatio-visual primitives are not specified at all

**Core CommonMark has 22 constructs and no table type.** Its own §1.1 concedes
tables were never Markdown's: "Some **extended** the original Markdown syntax with
conventions for footnotes, **tables**, and other document elements."

**GFM's table extension, verbatim** (<https://github.github.com/gfm/> §4.10):

> "**Block-level elements cannot be inserted in a table.**"
> "The header row must match the delimiter row in the number of cells. **If not, a table will not be recognized.**"
> "If there are a number of cells fewer than the number of cells in the header row, empty cells are inserted. **If there are greater, the excess is ignored.**"

**"The excess is ignored."** Extra columns of user data are silently discarded.
The words `colspan`, `rowspan`, `merge`, `formula` and `nested table` **do not
appear anywhere in the GFM specification.**

**And "Markdown tables" is not one thing.** Pandoc alone implements four mutually
incompatible table syntaxes — `simple_tables` (one line per row),
`multiline_tables` ("cells that span multiple columns or rows of the table are
not supported"), `grid_tables` ("may contain arbitrary block elements… cells can
span multiple columns or rows"), and `pipe_tables` ("cannot contain block
elements… cannot span multiple lines"). Add MultiMarkdown, reStructuredText and
org-mode and *"store the table as Markdown"* is an undefined instruction. The one
syntax with real structural power (grid tables) is Pandoc-only and is not what
GitHub, GitLab, Slack, Notion or Obsidian parse.

**Slides have no specification at all**, and the four implementations disagree on
the two most basic concepts in a deck:

| Tool | Slide break | Speaker notes |
|---|---|---|
| reveal.js | regex `^\r?\n---\r?\n$`; vertical slides **off by default** | `notes?:` |
| Marp | `---` — **which is also the YAML frontmatter delimiter** | HTML comment |
| Slidev | `---` + frontmatter | HTML comment |
| Pandoc | "**A horizontal rule always starts a new slide. A heading at the slide level always starts a new slide**" — slide level **inferred from the document** | `::: notes` |

Pandoc's rule is not even syntactic: "the slide level is **the highest heading
level in the hierarchy that is followed immediately by content**… somewhere in the
document." **Add a heading elsewhere and your deck silently re-paginates.**

### 4.10 The measured asymmetry: 3,180 specified elements versus 22

Counted from the 21 XSD files shipped with `OfficeOpenXML-XMLSchema-Strict.zip`:

| Schema | Elements | Complex types | Attributes |
|---|---:|---:|---:|
| `wml.xsd` (WordprocessingML) | 704 | 279 | 426 |
| `sml.xsd` (SpreadsheetML) | 618 | 366 | **1,507** |
| `dml-main.xsd` (DrawingML) | 475 | 231 | 349 |
| `pml.xsd` (PresentationML) | 313 | 148 | 224 |
| …+17 more | | | |
| **TOTAL** | **3,180** | **1,369** | **2,840** |

**3,180 specified elements against CommonMark's 22 constructs — a 145× ratio.**
Named elements verified present in the official schemas:

- SpreadsheetML: `mergeCell`, `conditionalFormatting`, `dataValidation`,
  `definedName`, `calcChain`, `pivotCacheDefinition`, `numFmt`, `f` (formula,
  `CT_CellFormula`); a closed cell-type enumeration `ST_CellType` = `b d n e s
  str inlineStr`; formula kinds `normal array dataTable shared`.
- WordprocessingML: `ins`/`del` (tracked changes), `comment`, `footnote`,
  `sectPr`, `numbering`, **`gridSpan`** (colspan), **`vMerge`** (rowspan).
- PresentationML: `sldMaster`, `sldLayout`, `transition`, `timing`,
  `notesMaster`, `ph`, `xfrm`.

**Markdown has zero of these — not a lesser version, zero.** No dialect has syntax
for a formula, a cell type, a merged cell, a tracked change, a slide master or an
animation. **A substrate that stores sheets and decks as Markdown does not store
sheets and decks; it stores a lossy transcript of their text content.**

Gruber himself, in Markdown's defining document
(<https://daringfireball.net/projects/markdown/syntax>):

> "**Markdown is not a replacement for HTML, or even close to it. Its syntax is very small, corresponding only to a very small subset of HTML tags.**"
> "**For any markup that is not covered by Markdown's syntax, you simply use HTML itself.**"

**His own worked example of markup Markdown cannot express is a table.**

### 4.11 Tooling: ~700M downloads a month against zero

Current monthly downloads: **openpyxl 347.2M**, **python-docx 115.7M**,
**python-pptx 63.2M**, **exceljs 56.4M**, **SheetJS `xlsx` 51.4M**, **`docx`
23.8M**, PhpSpreadsheet 9.6M. NuGet lifetime: DocumentFormat.OpenXml 421.4M,
ClosedXML 213.3M, EPPlus 205.8M, NPOI 116.9M. Apache POI shipped 1.0.0 on
**2001-12-30** — it predates OOXML by five years.

A new format starts at **zero** libraries, zero downloads, zero StackOverflow
answers, zero LLM training data and zero integrations.

*Conceded honestly:* three of the highest-traffic libraries are effectively
unmaintained — openpyxl (last release 2024-06-28), ExcelJS (last commit
2024-01-12, 802 open issues), npm `xlsx` (frozen at a 2022 build carrying
CVE-2024-22363). That is ~450M downloads/month riding stale code. But that proves
the ecosystem is **load-bearing enough to survive neglect**. A new format gets the
neglect without the gravity that eventually attracts a fix.

### 4.12 ODF: the control experiment was run, with force of law, and lost

ODF had everything the proposal wants: **ISO/IEC 26300-1:2015** (852 pages, free
from the same ITTF portal), XML-in-ZIP, true vendor neutrality, an active OASIS TC
(ODF 1.4 approved 2025-10-06), IBM/Sun/Google backing — **and binding government
mandates.** All three mandates reversed or froze.

**Massachusetts — reversed by one word, in the primary documents.**
ETRM v3.5 (2005-09-21):

> "The OpenDocument format **must** be used for office documents… As of January 1, 2007 all agencies… will be required to… **Configure the applications to save office documents in OpenDocument format by default.**"

ETRM v4.0 (effective 2007-08-01):

> "The OpenDocument format **may** be used for office documents…"

…and OOXML was added as co-equal, on the explicit ground that it *"was designed to
ensure the highest levels of fidelity with legacy documents."* The stated reason
for abandoning ODF-native tools is the most damaging line in the record:

> "**there are no office applications that natively support ODF that also provide sufficient accessibility for persons that use assistive technology devices.** … the only implementation option available to agencies is the use ODF through the use of translator software."

**UK — mandated 2014, never repealed, abandoned by neglect.** The policy page,
updated 2026-01-29, is still pinned to **ODF 1.2** — two OASIS versions behind —
and carries the escape hatch that voids it:

> "Government organisations should publish information for users online, **using browser-based editing by default**… **If this is not possible**, government organisations must save documents in the Open Document Format (ODF) by default."

Microsoft satisfied the mandate by reconfiguring Office, not by anyone leaving it.
Microsoft's UK Government blog, 2014-11-03: *"**Setting up Office 2013 to default
to using ODF 1.2 is a simple configuration exercise using Group Policy.**"* and
*"**Microsoft Office makes it easy to comply with government file mandates with
the technology you already use.**"* Meanwhile the Cabinet Office is migrating
**onto** Microsoft 365, and ~**£1.9 billion** went to Microsoft licences via CCS
agreements in FY2024/25.

**A mandate that is never repealed, satisfied by a Group Policy flag, frozen a
decade behind the standard it names, and coexisting with £1.9bn/yr of the
incumbent's licences, is what winning a standards argument and losing the market
looks like.**

**Munich — repealed outright.** Council decision, 2017-02-15: for standard
functions, *"stadtweit einheitlich **marktübliche Standardprodukte**… die eine
**höchst mögliche Kompatibilität** gewährleisten"* — market-standard products
ensuring the highest possible compatibility. The compatibility argument is written
into the resolution. Final decision 2017-11-23: uniform Windows client for ~29,000
PCs, **>€89m**.

**The outcome.** Microsoft FY2026 revenue **$331.8bn**; Q4 Productivity and
Business Processes **$37.8bn, +14%**; M365 Copilot **">30 million paid seats"**.
The UK CMA, using compulsory information-gathering powers (Invitation to Comment,
2026-05-14): *"**There were [20-30] million UK organisational users of Microsoft's
productivity software in FY25.**"* The Document Foundation's own estimate for
LibreOffice, 2026-08-28: *"**even a very conservative estimate puts the number of
LibreOffice users worldwide at over 100 million**"* — on total 2025 revenue of
**~€2.2 million**.

And verified on this machine: LibreOffice 25.2.3.2's filter registry still carries
`DEFAULT`/`PREFERRED` on `writer8`, `calc8` and `impress8` — **the world's leading
ODF producer still writes ODF by default, and ODF still lost.**

**If a technically clean, ISO-ratified, IBM-and-Sun-backed, legally mandated open
document format could not displace `.doc`, the prior probability that a new,
unspecified, single-implementation plain-text format displaces `.docx` is not
low — it is negligible.** The proposal must say what it has that ODF did not, and
"it is in git" is not an answer to a distribution problem.

### 4.13 The counter-evidence, stated fully

I will not hide the strongest fact against this section. **NARA prefers plain text
over OOXML** (<https://www.archives.gov/records-mgmt/policy/transfer-guidance-tables.html>):
for permanent electronic records, *Preferred* is ASCII/Unicode text, ODT, PDF/A
for textual works; **CSV**, ODS, JSON, XML for spreadsheets; ODP for
presentations. DOCX/XLSX/PPTX are merely *Acceptable*.

Three answers, in order of force:

1. **Markdown appears on neither list.** NARA prefers **`.txt`** — *unstructured
   character data*, with no headings, no lists, no emphasis, no tables and no
   links. That is an endorsement of throwing away exactly the structure the
   proposal exists to preserve. **An endorsement of plain text is not an
   endorsement of Markdown.** The moment you add `##` and pipe tables, you have
   left the format NARA named and entered §4.7–4.9.
2. **Preservation format ≠ production format.** NARA's other top preferences are
   **PDF/A** and **CSV**. Nobody proposes PDF/A as a collaborative editing
   substrate, and CSV cannot express a formula, a second sheet, a merged cell or
   a number format. These lists describe *terminal deposit of frozen records for
   century-scale custody* — deliberately lossy but stable. Citing them to justify
   a live editing substrate confuses the archive box with the desk.
3. **Both bodies list OOXML as at least acceptable for permanent records.** The
   Library of Congress goes further: its *Recommended Formats Statement* for
   Textual Works ranks, in order of preference, "**XML-based document formats…
   Includes DOCX/OOXML 2012 (ISO 29500), ODF (ISO/IEC 26300)**" **third**, and
   **plain text ninth — below Rich Text Format.** Markdown is not named anywhere.

Also conceded: **OOXML has two conformance classes** (Strict and Transitional)
with different namespaces, and real-world files are overwhelmingly Transitional
with legacy baggage. That is a versioning wart *in a specified format* — not the
absence of a specification. And **Schleswig-Holstein is genuinely migrating to
LibreOffice** (~80% of workplaces by 2025-12-04, ~30,000 seats, >€15m/yr saved).
Against the CMA's 20–30 million UK Microsoft productivity users, that is roughly
0.1%. It proves migration is *possible*. It does not show the incumbent is
displaceable.

---

## 5. THE MERGE ARGUMENT

**Thesis: git does not merge documents. On prose it either conflicts on every
co-edit, or it silently produces a semantically corrupt document. Both were
reproduced here in under a minute.**

### 5.1 The proposal already knows this about spreadsheets

`RESEARCH.md` §3 records the finding: two branches inserting rows far enough
apart that **git auto-merged with zero conflicts**, producing a sheet that
totalled **480 instead of 660** — a 27% error with no marker anywhere. That
finding was treated as an argument for named-column addressing. It is better read
as an argument that git's merge is not a document merge at all.

### 5.2 The same failure exists in the *documents* leg — the leg assumed solved

Test A. Two writers change two **different, non-overlapping words** in the same
paragraph of a plain markdown file. This is the single most common concurrent
edit in the history of writing.

```
$ git merge alice
Auto-merging memo.md
CONFLICT (content): Merge conflict in memo.md
```

```markdown
<<<<<<< HEAD
We should hire two engineers in Q3 ... the on-call rotation is understaffed.
=======
We should hire three engineers in Q3 ... the on-call rotation is thin.
>>>>>>> alice
```

Neither writer touched the other's words. Git's merge unit is the **line**; prose's
unit is the **paragraph**; a paragraph is one line. Plain text buys nothing.

### 5.3 The documented workaround produces a *silently wrong* document

The standard answer is "semantic line breaks" — one sentence per line, so git can
merge. I applied it. Two writers, one legal document:

- `legal` branch tightens the refund window: 30 days → 14 days.
- `support` branch appends a clarifying sentence about the 30-day window.

```
$ git merge legal
 policy.md | 2 +-
 1 file changed, 1 insertion(+), 1 deletion(-)
```

Clean merge. No conflict. Result:

```markdown
# Refund policy

Customers may request a refund within 14 days.
Refunds are issued to the original payment method.
Shipping costs are not refunded.
Customers may request a refund within 30 days of delivery, not purchase.
```

**Git reported success and produced a refund policy that contradicts itself in two
places.** This is the document-primitive analogue of the 480-vs-660 spreadsheet
result, and it is worse, because a wrong number can be spotted by a reviewer
looking for numbers, whereas a contradictory clause five lines apart cannot.

The proposal's central promise — "git provides merge" — is, on its own primary
data type, either a conflict or a corruption. There is no third outcome I could
construct.

### 5.4 Git *destroys* attribution on prose

The proposal lists "attribution" as a benefit of git. Test: Alice writes a
paragraph. Bob changes one word — `five` → `three` — and his editor reflows the
paragraph. Every WYSIWYG-over-markdown editor reflows. So does Prettier. So does
turndown, which `RESEARCH.md` §2 already establishes rewrites whole files.

```
$ git blame -w -M -C doc.md
^5593c2f (alice ...) # Design doc
^5593c2f (alice ...)
f0b8755b (bob   ...) The scheduler assigns work to the pool. It retries on failure with
f0b8755b (bob   ...) exponential backoff. Dead-lettered jobs go to the audit queue after three
f0b8755b (bob   ...) attempts. Operators can replay them from the console.
```

Bob is credited with 100% of Alice's paragraph, **even with git's strongest
detection flags** (`-w -M -C`). Word's tracked changes and Google Docs' revision
history both attribute correctly at sub-word granularity. **On attribution, the
incumbent binary formats beat git.** This is a benefit the proposal claims that
git does not merely fail to provide — it actively regresses it.

### 5.5 The spatio-visual leg does not diff either

The market-leading open-source canvas is Excalidraw (130,701 stars). Its file
format is "plaintext JSON". From Excalidraw's own source
(<https://github.com/excalidraw/excalidraw/blob/master/packages/element/src/types.ts>,
lines 55–79), every element carries:

> `seed: number;` — "Random integer used to seed shape generation…"
> `version: number;` — "Integer that is sequentially incremented on each change. Used to reconcile elements during collaboration or when saving to server."
> `versionNonce: number;` — "**Random integer that is regenerated on each change.** Used for deterministic reconciliation of updates during collaboration…"
> `updated: number;` — "epoch (ms) timestamp of last element update"
> `isDeleted: boolean;`

I moved one rectangle five pixels — the smallest meaningful canvas edit — and
committed:

```diff
       "id": "el20",
-      "x": 700,
+      "x": 705,
       "seed": 798461319,
-      "version": 1,
-      "versionNonce": 1272987056,
-      "updated": 1756400000000,
+      "version": 2,
+      "versionNonce": 1216703156,
+      "updated": 1756400020000,
```

**Three of the four changed lines are non-deterministic bookkeeping.** And the
reason those fields exist is decisive: Excalidraw's own comments say they are for
*"reconcile elements during collaboration"*. The leading open-source canvas
independently concluded it needs per-element version vectors and tombstones —
i.e. a CRDT — and did **not** conclude it needs git. `isDeleted` means canvas files
grow monotonically: deleted shapes are never removed. A substrate adopting this
format inherits a format that already has its own, non-git, sync mechanism.

### 5.6 And the alternative to git-merge is broken too

The standard rebuttal is "then don't use git's line merge — use a CRDT." That
does not rescue the proposal, because CRDT merge of prose has a published,
named, unsolved anomaly. Kleppmann, Gomes, Mulligan & Beresford, **"Interleaving
anomalies in collaborative text editors", PaPoC '19** (Dresden, 2019-03-25),
abstract, verbatim from the paper:

> "**Several published algorithms for collaborative text editing exhibit an undesirable anomaly in which concurrently inserted portions of text with a well-defined order may be randomly interleaved on a character-by-character basis, resulting in an unreadable jumble of letters.** Although this anomaly appears to be known informally by some researchers in the field, **we are not aware of any published work that fully explains or addresses it.**"

Their Figure 2 is the whole problem in one line. User 1 inserts `` Alice`` and
User 2 concurrently inserts `` Charlie`` at the same position in `Hello!`. Both
replicas converge — to:

```
Hello Al Ciharcliee!
```

The paper also states the framing that matters here, in its own words:

> "Merge operations can either be performed manually—**the approach used by version control systems such as git**—or can be automated."

So the menu is: git's manual merge (§5.2 conflicts on every co-edited paragraph;
§5.3 silently corrupts when it does not), or an automated CRDT merge that can
produce `Hello Al Ciharcliee!`. `RESEARCH.md` §2 already documents the rich-text
version of the same problem (Peritext: concurrent overlapping marks merging to
`**The **fox** jumped.**`, rendering "fox" *not bold*).

**There is no third option on the menu, and the proposal's headline feature is
the menu.**

### 5.7 Nobody wants to branch a document — and this is now a negative result, not an argument from absence

**The controlled experiment was run, by the most sympathetic possible
researchers, and they deleted the feature.**

Ink & Switch, **Upwelling** (2023) — <https://www.inkandswitch.com/upwelling/>. A
funded research lab with no revenue pressure, a purpose-built CRDT, and Martin
Kleppmann and Poetica's founder on the team. They built git-style dependent
branches for writers, user-tested them, and removed them:

> "In Git, branches can be dependent on each other… **We experimented with 'Git-like' dependent drafts in Upwelling and found that it made the model more difficult for users to understand and did not add meaningful value. Moreover, it encouraged the use of long-lived branches, which in turn increases the risk of conflicts.**"

And on cherry-pick:

> "**we decided that adding similar features to Upwelling would introduce too much complexity and add too little value.** When reviewing a draft, if an editor finds that they want to use some but not all of the edits it contains, **they can simply edit the draft to change the unwanted edits back to what they were before. We believe that this approach is much simpler to understand than a cherry-picking interface, and is equally effective.**"

Their user research found the revealed preference is a **linear handoff**, not a
DAG:

> "**My preferred workflow for Word would be to pass it around one by one—a linear order, rather than having two people working simultaneously.**" — Educational Writer
>
> "In the magazine article we wrote, it got to the point where we eventually created our own version history. After a round of comments, we duplicate the document, save v1, and create v2." — Academic Researcher
>
> "…otherwise **you have 17 canonical documents and people are editing the wrong thing**." — Newspaper Editor

They also cite Wang et al. (2017), *"Why Users Do Not Want to Write Together When
They Are Writing Together."*

### 5.8 The founder of "GitHub for Writers" wrote the prosecution into his own launch post

Loren Burton, "GitHub for Writers", 2013-08-29
(<https://web.archive.org/web/20130831071209/http://madebyloren.com/github-for-writers>).
He sells the workflow — *"Jacob clicks a button and branches off onto his own
version of the document… he creates a pull request… the changes are merged into
the main document"* — and then, **in the same post**, names the failure mode:

> "**Tech jargon: non-developers don't understand branches, forks, commits, rebasing, cloning, etc.. and they don't care to learn.**"

What Penflip shipped was branching **under euphemism**: branch → "version",
pull request → "submit changes for approval". Its help docs:

> "You can **think of a version like a copy of the project**… When collaborators join your project, **a new version is created for each of them, automatically**."

The archived version dropdown renders roughly **150 per-collaborator branches**
(`0atman`, `11ten`, `16april`, `Ad115`, `Airun`, `Albert`…). **That is what
branching in a writing tool degenerates into: an unmanageable list of stale
forks.**

Burton on HN, 2014-02-14 (<https://news.ycombinator.com/item?id=7236886>), to a
user saying *"It's too much like Git. Writing should be made easy"*:

> "**Usability is definitely not a trivial task to solve, especially while trying to maintain all of the version control power that comes with git.** That said… I've received lots of similar feedback (too technical, too hard to use, cluttered UI) so I'm continually stripping down the interface and simplifying everything."

**And the retreat is precisely dated.** The Penflip homepage on **2014-05-06**:
*"**Built on Git** — If you'd rather use your own text editor, you can. Each
writing project has a git repository with full access."* On **2014-06-03**, and
identically through the final capture in 2020, that tile is renamed
*"**Command-line friendly**"* and a new tile appears: *"**Accept or reject
changes — Like MS Word 'Track Changes'.**"*

**Nine months after launching "GitHub for Writers," the founder deleted git from
his own homepage and adopted Microsoft Word's metaphor.** Penflip's last public
mention by its founder is 2014-09-12. There is no shutdown post. By 2020 its
public project directory had been overrun by SEO spam. He now uses Notion.

The launch thread itself (311 points,
<https://news.ycombinator.com/item?id=6296630>) is a corpus of the objection:

> "**Writers don't need branches. They don't code features in.**" — `guard-of-terra`
>
> "**I would seriously consider not allowing arbitrary branches. Most people just get confused managing multiple independent outstanding branches**… **keeping track of dependencies is precisely what's hard for people.**" — `nwhitehead` — to which **Burton replied "Yep, absolutely true… Heavily considering this approach,"** and shipped exactly that: one branch per user.
>
> "**When do writers need to branch their stories/articles into two forks? If they do that, why not just copy the document and work on it there?**" — `gcr`
>
> "using git for collaborative writing? **That's like using nukes to get rid of mosquitoes.**" — `iSnow`

### 5.9 A member of the Editorially team wrote the thesis sentence

Paul Lloyd, Smashing Magazine, 2014-04-17
(<https://www.smashingmagazine.com/2014/04/after-editorially-alternative-collaborative-online-writing-tools/>),
writing as "we" about the product he helped build:

> "In Editorially, we had a product for editors, by editors. In surveying the landscape of its competitors, we see many that provide wonderful, easy to use and distraction-free writing interfaces, but fail to understand the editing process. **Mapping programming metaphors like branching and diffs seems like great ideas in abstract, but in practice impede the less structured act of review and refinement.**"

On Penflip specifically: *"**This enforced Git-like workflow prevents more
piecemeal collaboration, however, instead preferring an all-or-nothing affair
with regards to editing.**"* **His requirements list for a writing tool —
distraction-free, Markdown, in-document annotation, status, import/export — does
not contain branching at all.**

Editorially's shutdown post (<http://stet.editorially.com/articles/goodbye/>):

> "**Editorially has failed to attract enough users to be sustainable**, and we cannot honestly say we have reason to expect that to change. We wish that were not the case — **we've spent much of the past two years working on the hypothesis that the reverse was true.**"

Its version model was linear milestones, with a tell: *"the app will
automatically save a version for you; notably, **when the editor changes
hands**"* — sequential single-writer handoff, exactly what Upwelling's users
described.

### 5.10 Overleaf — the one mainstream git-backed writing product — hard-codes the branch count to one

The natural steelman is *"scientific writers do need branches"*, and Overleaf is
precisely the product serving them. Overleaf's own advanced-git-operations
documentation:

> "**Please note that Overleaf only supports one linear history for each project. The Git integration enforces this limitation by limiting the number of branches to one. That one branch is currently hard-coded to be called `main`.**"

That is not a missing feature. It is an **enforced constraint**, in the product
built for the exact audience that supposedly wants branching. Two further
first-party admissions:

> "**the Overleaf Git integration is essentially a translation from Overleaf's history and versioning mechanism to Git… it doesn't allow you to work within Overleaf as if it was a complete Git implementation.**"

> "if your collaborator changed a line in Overleaf and you changed the same line in the GitHub repository, Overleaf may not be able to choose which version to keep. When that happens, **instead of merging into your main branch, we push a new branch to your repository**… **To get back in sync, you need to merge the Overleaf branch into your main (default) branch. You can do this on your computer.**"

**Overleaf's conflict-resolution UX is "go use GitHub."** The only branch Overleaf
will ever create is an error-recovery artifact. And its only fork primitive
amputates history: *"A copied project starts with a completely new, fresh
history."*

### 5.11 The eight-product survey: 8/8 linear, 0 merge, 0 branching

| Product | History model | Compare? | Merge? | Branch? |
|---|---|---|---|---|
| Notion | Linear snapshots, restore | Yes | **No** | **No** |
| Confluence | Linear version chain | Yes | **No** | **No** |
| Coda | Linear activity log | Partial | **No** | **No** |
| Craft | Hourly backups | No | **No** | **No** |
| Dropbox Paper | Linear versions | Yes | **No** | **No** |
| Scrivener | Snapshots | Yes | **No** | **No** |
| Ulysses | **Backups only — no version history at all** | No | **No** | **No** |
| Overleaf | Linear, git branch count hard-coded to 1 | Yes | **No** | **No** |

Two of these go further than absence, into active rejection.

**Coda's FAQ**, verbatim (<https://help.coda.io/hc/en-us/articles/39555752074637>):

> "**Can I revert my doc to a previous version on my own? Currently, no. You need to reach out to the Coda team for assistance reverting your doc. This is to prevent accidental changes that could result in permanent data loss.**"

A modern document platform judges that **self-service rollback is too dangerous
to expose to users.** That is the opposite end of the spectrum from
branch-and-merge, and it is a considered product decision, not an oversight.

**Ulysses** — a best-in-class professional long-form writing app — ships **no
version history whatsoever**, only hourly/daily/weekly library backups. Writers
are not paying for version semantics.

**Scrivener's "merge"** is destructive replace or copy-paste: *"just copy the
text of the snapshot and paste it into the current document, replacing its text.
**This is quick, but it does delete the latest version.**"* **Confluence** cannot
even attribute within a version: *"It is not possible to view the individual
changes made by each person in a single page version."* **Quip** markets the
absence as the feature: a living document *"beats silly document versioning
issues that can result in multiple files saved to your computer with ironic names
like 'BizPlan_FINAL_v9.doc.'"*

And the retreat is a genre. **Authorea's own `<title>` tag**, 2014-04-01:
*"Authorea | Online collaborative editor. Write papers in LaTeX and Markdown.
**Track changes in Git.** Open Science!"* By 2016-06-01: *"Write research
documents online, together."* — **every mention of git deleted**, replaced with
*"Work on documents together in real time."* **Leanpub** exposes exactly two
branch-name text fields and nothing else — no branch list, no diff, no merge, no
PR; its answer to real branching is "go use GitHub." **Forestry.io** died in 2023
into a successor whose pitch is the opposite direction of travel: *"We're
bringing a **drag and drop, visual editing** experience to a
developer-controlled, open-source, Git-backed CMS."* **Decap CMS** does
branch-per-entry, with machine-generated branch names, surfaced to editors as a
three-column kanban — Draft / In review / Ready. The word "branch" appears only in
a config note.

**The pattern across a decade: every product that put git's vocabulary in front of
writers either renamed it, hid it, or died.**

### 5.12 The counterexample, stated before the defence finds it

**GitBook ships branching to end users, with a real merge-conflict UI, and is
alive.** <https://gitbook.com/docs/collaborate/change-requests>:

> "**A change request is a copy of your main content. It's based on the concept of branching, and feels familiar to anyone who uses pull requests in GitHub or merge requests in GitLab.**"

And it ships genuine conflict resolution: *"a conflict is a piece of content that
could not be merged automatically. You have two options… selecting a version to
merge or manually editing the content."*

This is a real counterexample and I will not pretend otherwise. Four rebuttals,
all first-party:

1. **The audience is engineering-adjacent by GitBook's own description.** Its Git
   Sync page: *"Git Sync allows **technical teams** to sync GitHub or GitLab
   repositories… This allows **developers** to commit directly from GitHub or
   GitLab and **technical writers, instructional designers, and product
   managers** to edit."* It is a documentation tool for software organisations,
   not a writing tool for writers.
2. **Even here the word "branch" is scrubbed from the user-facing noun.** It is a
   *"change request."* The docs explain branching by analogy rather than assume
   it — which is itself the concession.
3. **GitBook's own git sync is single-branch**: *"Select the branch that GitBook
   syncs with."* One space ↔ one branch, exactly like Overleaf.
4. **Its ordinary version history is the same linear restore model as everyone
   else**: *"Rolling back allows you to revert a section's content to the way it
   was at a previous point in time."*

**GitBook proves the rule by its exception: branching ships only to
engineering-adjacent users, only under a euphemism, and only one branch deep at
the git layer.** It is also, notably, a *documentation* product — which is the
one genre where the audience already lives in pull requests. That is not the
proposal's stated audience.

### 5.13 And the users who *do* use git cannot drive it

`RESEARCH.md` §7 already records Poetica's pitch: collaboration *without* "arcane
tools like git". The MIT conceptual-design analyses of git (Perez De Rosso &
Jackson, Onward! 2013; OOPSLA 2016) concluded git's conceptual model is a misfit
for its users. The research pass supporting this brief also surfaced figures that
only 15% of developers hold git's actual model of a branch and that daily-driver
git users fail basic branch tasks ~45% of the time. **Provenance note: I did not
retrieve those two figures' primary sources myself, and they should be verified
before being quoted in a room. Nothing in §5 depends on them.**

The point stands without them, from the products alone: **the industry did not
fail to solve async document merge. It looked at it, built it, tested it, and
chose not to have it.**

---

## 6. THE AGENT ARGUMENT, INVERTED

**Thesis: "agents want plaintext" was a 2023 constraint. In 2026 it costs 444 ms
to satisfy, and the market has already chosen the converter and the renderer over
the new substrate — by a factor of 34.**

### 6.1 The cost of giving an agent plaintext, measured

```
$ time pandoc -f docx -t markdown big.docx -o view.md
real    0m0.444s
recovered markdown: 145,583 bytes   (source was 145,584 bytes)
$ # word-level vocabulary comparison, md -> docx -> md
IDENTICAL vocabulary after md -> docx -> md
```

444 milliseconds, lossless at the word level, on a 50-page document, using a tool
that has been in Debian for fifteen years. That is the entire size of the problem
the substrate proposes to solve by changing the world's file formats.

Whatever the agent wants to read, the answer is a **view**, not a **storage
format**. Views are cheap; storage migrations are civilisational.

### 6.2 The market already ran this experiment. The converter won by 34×.

Star velocity, computed from the GitHub API today (2026-08-28):

| Project | Approach | Stars | Age | ★/day |
|---|---|---:|---:|---:|
| `microsoft/markitdown` | **converts** Office → markdown for LLMs | 176,825 | 653 d | **270.8** |
| `iOfficeAI/OfficeCLI` | **keeps OOXML**, gives agents a render loop | 29,449 | 166 d | **177.4** |
| GenOffice | byte-preserving `.docx` edits | 3,860 | 149 d | 25.9 |
| `stravu/crystal` (Nimbalyst's ancestor) | agent orchestrator in git worktrees | 3,113 | 449 d | 6.9 |
| `nimbalyst/nimbalyst` | **git + markdown suite** | 1,596 | 302 d | 5.3 |
| `KovaMD/Kova` | markdown decks + formulas | 284 | 116 d | 2.4 |
| `andes90/collabmd` | realtime markdown in git | 268 | 177 d | 1.5 |

**OfficeCLI is accumulating adoption 33.6× faster than the best git-backed
plaintext suite in existence.** Not 33% faster. Thirty-three times.

And it is not one project — it is a *category*. In a single GitHub search today:
`iOfficeAI/OfficeCLI` (29,449★), `officecli/officecli` (96★),
`dream-zjk/officekit` (106★), `RainLib/OfficeCLI-rust` (16★), `onecer/AIOffice`
(8★). **Every one of them keeps `.docx`/`.xlsx`/`.pptx`. Zero of them adopt a new
plaintext substrate.** When five independent teams solve the same problem the same
way in five months, that is not an oversight to be corrected. That is the answer.

### 6.3 OfficeCLI's README states the refutation directly

From <https://github.com/iOfficeAI/OfficeCLI> (Apache-2.0, created 2026-03-15):

> **"OfficeCLI is the world's first and the best Office suite designed for AI agents."**
>
> **"OfficeCLI's built-in HTML rendering engine reproduces documents with high fidelity — and that's what gives AI eyes. It renders `.docx` / `.xlsx` / `.pptx` to HTML or PNG, closing the *render → look → fix* loop."**

The pro-case is "agents cannot see binary documents, therefore change the format."
The market's answer is "give the agent eyes." A renderer is a library. A format
migration is a generation.

Note also the distribution mechanic, which is the whole game:

> `curl -fsSL https://officecli.ai/SKILL.md`
> "Paste this into your AI agent's chat — it will read the skill file and install everything automatically."

Adoption cost: one line, zero migration, zero file conversion, zero retraining.
The substrate's adoption cost is: convert every document you own into a format
only one program reads.

### 6.4 The token-cost argument does not survive contact with tool use

`RESEARCH.md` §7 cites 410,053 tokens to read a 500×20 Excel sheet as JSON. That
number is an argument against **naïve JSON serialisation**, not against `.xlsx`.
The correct fix is to give the agent a sandbox. My `xlsx2txt.py` — **14 lines of
stdlib Python, written in this session** — reduces that sheet to a compact
cell-per-line listing including formulas, and an agent that can run `duckdb` or
`pandas` reads *the answer*, not the sheet. Cost: one tool call.

The substrate proposes a permanent, global format change to avoid a cost that a
14-line script and a code-execution tool already eliminate.

### 6.5 The incumbents closed the gap, to GA, on the same day

- **Microsoft, 2026-04-22** — "Copilot's agentic capabilities in Word, Excel, and
  PowerPoint are generally available"
  (<https://www.microsoft.com/en-us/microsoft-365/blog/2026/04/22/copilots-agentic-capabilities-in-word-excel-and-powerpoint-are-generally-available/>):

  > "Today, I am excited to share that agentic capabilities in Word, Excel, and PowerPoint are now generally available."
  >
  > "Copilot can take multi-step, app-native actions directly in your documents, worksheets, and presentations"
  >
  > "**Taking action matters.** Copilot creates the most value when it performs the work—formatting, restructuring, building visuals, and transforming data"

  Pre-GA engagement deltas Microsoft published: Excel +67% tries/user/week, +50%
  retention, +65% satisfaction.

- **Google, 2026-04-22** — Workspace Intelligence, the same day: Gemini across
  Gmail, Docs, Sheets, Slides, Drive, Meet, Chat; prompt-driven spreadsheet
  population and *fully editable* decks from company templates.

- **Anthropic** — Claude for Excel (preview Oct 2025, Pro tier 2026-01-24),
  Claude for PowerPoint (2026-02-05), shared context and one-click Skills across
  both (2026-03-11). The Marketplace description is the damaging part: Claude
  *"reads complex multi-tab workbooks, explains calculations with cell-level
  citations, and safely updates assumptions while preserving formula
  dependencies."* Cell-level citation and dependency preservation are properties
  of the **`.xlsx` object model**. Flattening to plaintext destroys exactly the
  structure that makes them possible.

- **Anthropic, 2025-09-09**, "Claude can now create and edit files" — Excel
  documents, Word documents, PowerPoint decks and PDFs, produced inside
  *"a private computer environment where it can write code and run programs."*

That last sentence is the whole inversion in one line: **the industry's answer to
"agents cannot handle binary formats" was "give the agent a computer," not "change
the format."**

### 6.6 GenOffice already shipped the diffability the proposal is asking for

`genspark-ai/genoffice`, Apache-2.0, created 2026-07-31, **3,865 stars in under
four weeks**. From its README:

> "**Microsoft Word–compatible, byte-preserving `.docx` editing** — only what you touched changes; Word never notices."
>
> "**Word-faithful pagination** — page breaks land where Word puts them."

"Only what you touched changes" is *precisely* the property `RESEARCH.md` §2
identifies as the central technical problem (Pithy's turndown reserialisation
producing whole-file diffs on first touch), and *precisely* the property the
proposal claims is obtainable only by abandoning binary formats. Someone shipped
it **for `.docx`**, under a permissive licence, in a month. There is now an
`mcp-genoffice` server advertising byte-preserving docx/pptx editing.

The proposal's differentiator has been implemented on the incumbent format by a
competitor, and the incumbent format keeps its 6,000-page ISO spec, its library
ecosystem and its billion-seat installed base.

### 6.7 The capability trend line the proposal is betting against

| Benchmark | Then | Now (Aug 2026) | Human baseline |
|---|---|---|---|
| OSWorld (agent drives a real desktop from **screenshots**) | 12.24% (2024) | **85.4%** | 72.36% |
| DocVQA (reading **rendered document images**) | 88.5 (Claude 3.5 Sonnet) | **97.1 ANLS** | 94.36 |
| SpreadsheetBench v1 (real `.xlsx` manipulation) | 57.2% (Sep 2025) | **89.3%** | not published |

Sources: <https://leaderboard.steel.dev/leaderboards/osworld/>,
<https://llm-stats.com/benchmarks/docvqa>,
<https://llm-stats.com/benchmarks/spreadsheetbench-v1>.

Agents now drive graphical desktop applications **13 points above the human
baseline** and read rendered documents **above** the human baseline. "Agents
cannot see a `.docx`" is not a technical claim in 2026; it is a nostalgia claim.
Committing to a multi-year format migration against a capability that went
12% → 85% in twenty-four months is betting against the steepest trend line in the
industry.

**Stated honestly, because the defence will raise it:** SpreadsheetBench 2 (Aug
2026) tops out at 34.8% — agents still fail multi-step spreadsheet *workflows*.
That is real. It is also irrelevant to this proposal: a model that cannot build a
financial model in `.xlsx` cannot build one in TOML either. V2 measures workflow
reasoning; the *representation* barrier — the only barrier a new file format could
remove — is the one that fell.

### 6.8 The token argument, priced

Anthropic's code-execution tool ships with `openpyxl`, `python-docx`,
`python-pptx`, `pandas`, `pyarrow` and `xlsxwriter` **pre-installed**
(<https://platform.claude.com/docs/en/agents-and-tools/tool-use/code-execution-tool>).
Pricing, verbatim:

> "Each organization receives **1,550 free hours** of usage per month"
> "Additional usage beyond 1,550 hours is billed at **$0.05 USD per hour, per container**"

Plus: every current frontier Claude model except Haiku 4.5 has a **1M-token
context window**; prompt-cache reads cost ~0.1× base input; the Batch API is a
further 50% off; frontier list prices fell from GPT-4's $30/$60 per MTok (Mar
2023) to Opus 5's $5/$25 and Sonnet 5's $2/$10.

The 410,053-token Excel read is an artefact of naïve JSON serialisation. The fix
costs five cents an hour and is already in the vendor's own sandbox. **You do not
change the world's file formats to save tokens that no longer cost anything.**

### 6.9 markitdown proves the opposite of what the pro-case says

`microsoft/markitdown`: **176,825 stars**, MIT, created 2024-11-13. From its own
README:

> "MarkItDown is a lightweight Python utility for converting various files to Markdown for use with LLMs and related text analysis pipelines."
>
> "While the output is often reasonably presentable and human-friendly, it is meant to be consumed by text analysis tools — and **may not be the best option for high-fidelity document conversions**."

Three readings, all hostile to the proposal:

1. The market's answer to "agents need text" was a **converter**, not a substrate
   — and *Microsoft, the owner of the binary formats, shipped the adapter itself*.
2. markitdown is **explicitly lossy and explicitly one-way**. It is a read path
   for machines. Nobody proposed it as a place to keep documents. The pro-case
   takes a read-path optimisation and promotes it to a storage architecture.
3. Its own framing is dated — it cites GPT-4o and "text analysis pipelines," a
   late-2024 worldview. The 2026 stack reads the `.docx` directly, edits it
   byte-preservingly, and renders it back to check its work.

---

## 7. ECONOMIC AND MAINTENANCE REALITY

**Thesis: the substrate must own, forever, a component set whose existing
open-source equivalents represent thousands of contributor-years — against an
observed revenue of $0.00 in the comparable project.**

### 7.1 The permanent ownership inventory

Everything below is code the substrate *must* own, because no existing project
provides it for a bespoke format:

| Component | Why it cannot be borrowed | Nearest OSS analogue (contributors) |
|---|---|---|
| Markdown parser + **byte-stable** serialiser | `RESEARCH.md` §2: no serialiser is byte-stable; `mdast-util-to-markdown`'s own README says its positional `Tracker` *"isn't used yet"*; Nextcloud has failed at this for six years | remark / mdast (—) |
| Live-preview editor (sequential) | Bespoke decoration layer over CodeMirror 6, whose upstream **archived its GitHub repos 2026-04-15** | CodeMirror (—) |
| Spreadsheet grid editor + named-column reference layer | The named-column per-row reference is, per `RESEARCH.md` §8, *"genuinely unclaimed"* — i.e. must be invented | — |
| Formula engine | IronCalc is Apache-2.0 but must be bound to a bespoke addressing scheme | IronCalc (35) |
| Canvas editor + format | tldraw is proprietary (`NOASSERTION`); Excalidraw's format carries its own CRDT metadata (§5.5) | Excalidraw (372) |
| Slide renderer + WYSIWYG slide editing | `RESEARCH.md` §5: **"The WYSIWYG-slides gap is real"** — nobody has built it | Marp (—) / reveal.js (363) |
| Merge drivers ×3 (prose, table, canvas) | §5: git's default merge corrupts all three | `daff` (partial, CSV only) |
| Layout / pagination engine | Required the moment anyone prints | Typst (462) |
| Office import/export at fidelity | Required for every real user's existing corpus | LibreOffice core (2,915) / pandoc (645) |
| Sync server + single-writer arbitration | §1.5: 12/12 pushes rejected without it | Yjs (129) |
| Auth server for per-file ACLs | `RESEARCH.md` §6: **no forge has per-file read ACLs** | — |
| Mobile git | `RESEARCH.md` §4: libgit2's sparse-checkout issue open **12 years**; obsidian-git's README: *"highly unstable… I don't know how to fix this"* | — |
| CLI, agent surface, format specifications ×3 | The specs do not exist and must be written and maintained | — |

Aggregate scale of the *existing* equivalents, measured from the GitHub API
today: **7.75 GB of repository, 5,768 contributors** (§1.4). Excluding Office
fidelity, still **923 MB and 2,853 contributors**.

Even assuming an agent-assisted team is 10× more productive than those
communities were — a generous assumption that Eigen's 14-apps-in-17-months
datapoint arguably supports for *building* — the residual is hundreds of
contributor-years, and **maintenance does not benefit from the 10×**. Bug reports,
format-spec stability, security, compatibility with every version of every Office
file a user drags in, and the mobile story are all ongoing obligations that scale
with users, not with build velocity.

### 7.2 The revenue side

- **Kova**: best-in-class engineering, 67 releases in 3.7 months, its own
  apt/rpm/AUR/Nix/Flatpak distribution estate — and **$0.00 raised from 0
  contributors on Open Collective**, verified against Open Collective's GraphQL
  API (`RESEARCH.md` §7).
- **Editorially**, on shutting down: *"even if all of our users paid up, it
  wouldn't be enough."*
- **Stashpad**: *"did not reach business viability."*
- **Pithy**: frozen since 2026-03-28.
- And the structural point: git-backing **deletes the closest analogue's revenue
  line.** Obsidian's largest SKU is Sync at $48/user/yr. Git gives sync away. The
  proposal's core feature is the competitor's business model, donated.

So: a permanent obligation of hundreds of contributor-years, funded by a market
that has demonstrated a willingness to pay of exactly zero, while structurally
foreclosing the one monetisation the category has proven.

### 7.3 The opportunity cost

The 22 lines in §1.2 and the 10 lines in §1.3 took me under an hour. Publishing
those as `git-office-textconv` and a Quarto extension would deliver most of the
proposal's *user-visible* value this week, to users who keep every file they own,
with zero migration and zero maintenance obligation beyond a few hundred lines.
The substrate delivers the same value in year three, to users who must first
convert their entire corpus into a format one program reads.

---

## 8. THE VERDICT

**Do not build it.**

Not "not yet", not "descope it". The proposal's causal chain is:

> plain text → git works on it → git gives history, merge, branching, attribution,
> sync → therefore a substrate → therefore apps emerge.

Every link in that chain broke under test, on this machine, in an afternoon.

1. **Git does not need plain text.** 22 lines gave git semantic diffs of
   `.docx`, `.xlsx` and `.pptx`. Git's own manual page uses a word processor
   document as the example. (§1.2)
2. **Git does not merge documents.** Two writers changing two different words in
   one paragraph → conflict. The documented workaround → a clean merge that
   produced a self-contradictory legal document. (§5.2, §5.3) And the escape
   hatch is closed: automated CRDT merge of prose has a published, unaddressed
   anomaly that converges `Hello Alice!` + `Hello Charlie!` to
   `Hello Al Ciharcliee!` (§5.6).
3. **Git does not attribute prose.** A one-word edit that reflowed a paragraph
   transferred authorship of the whole paragraph, even with `-w -M -C`. The
   binary incumbents do this *better*. (§5.4)
4. **Git cannot sync concurrent writers.** 12/12 pushes rejected; 8/8 rebases
   conflicted; 0% of the second writer's work landed. (§1.5)
5. **Nobody wants branches on documents — and this is now a negative result, not
   an absence.** Ink & Switch built git-style branches for writers, user-tested
   them, and removed them: *"it made the model more difficult for users to
   understand and did not add meaningful value."* Overleaf — the one mainstream
   git-backed writing product, serving the exact steelman audience — **hard-codes
   the branch count to one.** 8/8 surveyed writing products are linear with zero
   merge. The founder of "GitHub for Writers" named the failure mode in his own
   launch post and deleted git from his homepage nine months later. (§5.7–5.12)
6. **Plain text is not the durable standard.** Nine mutually incompatible
   Markdown dialects; the only ratified one cannot express a table; the `.docx`
   was 5.1× *smaller*. (§4)
7. **The agent argument is inverted.** 444 ms to produce the plaintext view; the
   incumbents shipped in-place agentic editing to GA on 2026-04-22; a competitor
   already ships byte-preserving `.docx` diffs; OfficeCLI is compounding
   **33.6× faster** than the best git-backed plaintext suite. (§6)
8. **There is no killer app, and every substrate that won had one.** Wave is the
   precedent, and Wave had Google. (§3)
9. **The economics are worse than zero.** Hundreds of contributor-years of
   permanent obligation, a category revenue of $0.00, and git-backing donates
   away the only monetisation the category has proven. (§7)
10. **The graveyard is 60 years deep and the failure mechanism is always the
    same.** (§2)

The three genuinely hard problems in this space — realtime multi-writer, per-file
access control, and mobile — are *all orthogonal to the file format*, and
insisting on git as the transport makes each of them harder rather than easier.
The proposal's one technical bet buys nothing on any of the three.

The honest reframing: **what the proposal actually wants to build is a
non-developer GUI shell over the composition in §1.** That is a product, possibly
a good one. It is not a substrate, it is not foundational, and calling it
foundational is how the next ten years get spent on parsers instead of users.

---

## APPENDIX A — Provenance and self-criticism

A prosecution that overstates gets impeached. These are the weak points in my own
case, stated before anyone else finds them.

**Reproduced locally in this session** (commands and outputs are in the body):
the 22-line `textconv` setup across `.docx`/`.xlsx`/`.pptx`; the 6-line `make`
pipeline; the 10-line cross-artifact transclusion; the nine byte-distinct
Markdown dialects and CommonMark's table failure; the prose merge conflict; the
silently-corrupt clean merge; the `git blame` attribution transfer; the
Excalidraw nonce churn; the draw.io/Graphviz one-line diffs; the 12/12 push
rejections and 8/8 rebase conflicts; the 3-of-8 `index.lock` failures; the
`docx` being 5.1× smaller than its markdown; the 444 ms lossless docx→markdown
conversion. Repo sizes, stars, contributor counts and creation dates were pulled
from the GitHub REST API on 2026-08-28.

**Genuine counter-evidence I did not suppress:**

- **NARA prefers plain text and ODF over OOXML** for permanent records (§4.13).
  The rebuttals are strong but the fact is real.
- **Schleswig-Holstein is migrating ~30,000 seats to LibreOffice.** Migration is
  possible. It is ~0.1% of the UK's Microsoft productivity users alone.
- **Three of the most-downloaded OOXML libraries are effectively unmaintained**
  (openpyxl, ExcelJS, npm `xlsx` with CVE-2024-22363), ~450M downloads/month
  riding stale code (§4.11).
- **OOXML has a Strict/Transitional split** with different namespaces, and
  real-world files are overwhelmingly Transitional (§4.6).
- **SpreadsheetBench 2 tops out at 34.8%** — agents still fail multi-step
  spreadsheet workflows (§6.7). Irrelevant to the format question, but real.
- **The per-row named-column reference is genuinely unclaimed** — this is the
  residual gap and I could not kill it.

**Claims I deliberately did not make, because I could not source them:** any
office-suite market-share percentage (no defensible source exists — Statcounter
does not measure office suites, and 6sense/Enlyft contradict each other);
"Microsoft has 400M paid Office seats" (unsourceable to any earnings release —
Microsoft publishes seat *growth* only); "LibreOffice has 200M users" (TDF's own
figure is "over 100 million"); Google Workspace paying-customer counts (Alphabet
does not disclose them).

**Corrections to premises I was handed, which would have impeached the brief:**

- Massachusetts CIO **Louis Gutierrez resigned in October 2006 over IT bond
  funding, not over ODF**, and a spokesman stated "the resignation will have no
  effect on the state's ODF policy." Do not draw a causal line from the
  resignations to the 2007 ETRM reversal.
- **Bruce Schneier is Inrupt's Chief of Security Architecture**, not an
  independent Solid critic.
- Inrupt's 2021 round was **$30M Series A**, not Series B.
- The IBM→HCL **$1.8bn was a bundle price**, not Notes/Domino alone.

**Unverified or unretrieved, and named as such:** Larry Tesler's widely-quoted
"how little we had thought about the benefits" line is **not** in the CHM
transcript that was read — secondary attribution only. No verbatim Wirth quote
was obtainable (the source PDFs are page images). The Library of Congress pages
are Cloudflare-gated to automated fetchers and were read from a mirror — verify
the RFS wording by hand before quoting it in a room. The Belfiore Windows Phone
tweets are gone; they survive only in contemporaneous coverage.

**Merge axis — what is and is not verified.** The Kleppmann PaPoC '19 interleaving
paper (§5.6) I extracted and quoted from the PDF myself. The Upwelling, Penflip,
Editorially, Overleaf, GitBook, Coda, Ulysses, Scrivener, Confluence, Authorea,
Leanpub, Forestry and Decap citations in §5.7–5.12 come from the research pass
and carry first-party URLs. **Not retrieved:** the formal software-merge
literature in full text (Mens, IEEE TSE 2002; Lippe & van Oosterom; Horwitz,
Prins & Reps 1989 on undecidability; Apel 2011 on structured merge) — abstracts
only; the MIT conceptual-design critiques of git (Perez De Rosso & Jackson,
Onward! 2013, OOPSLA 2016) — cited but not read here; and the "15% of developers
hold git's model of a branch / 45% branch-task failure rate" figures, whose
primary sources I did not see (§5.13 flags this inline). **Quip's official
version-history documentation is unretrievable** (JS-rendered Salesforce shell,
no Wayback capture) — do not assert Quip's version model as verified. **No
Notion, Google or Microsoft PM statement on why they do not ship branching exists
on the record**; §5.11 argues from revealed preference only. **No first-party
Overleaf explanation of *why* branching is absent** — only the constraint itself,
which is unambiguous.

**One correction carried in from the research pass:** it is *not* true that
Penflip never used branch/merge language. That holds for its homepage only. The
founder's launch manifesto sold branch → pull request → merge explicitly, and the
shipped product had GitLab-derived branch and merge-request routes under the
euphemisms "version" and "submit changes for approval" (§5.8). The corrected
story is stronger, not weaker. The marketing retreat is bounded to
**2014-05-06 → 2014-06-03**, not "by 2016".

**Not researched, and named as a gap (graveyard):** Subtext / Subconscious / Noosphere
(Gordon Brander), Anytype, Muse / Fermat, and Ink & Switch's abandoned
prototypes (Capstone, Pushpin, Farm, Cambria). These are the most contemporary
and most relevant graveyard cases and this brief does not cover them. The
prosecution does not depend on them — the six mechanisms in §2.10 are established
from ten independent projects across sixty-six years — but the gap is real and
should be closed.

---

## WHAT I COULD NOT KILL

One thing survived, and it is much smaller than the proposal.

**The residual gap is a merge-correct addressing scheme for tabular data — the
per-row named-column reference — and its merge driver. Nothing else.**

Precisely stated:

> Positional (A1-style) cell references cannot be merged. This is not an
> engineering gap; it is a formal one. Abiteboul, Hull & Vianu establish that
> named and unnamed relational perspectives have equal expressive power but
> different primitive operators — positional addressing costs no expressiveness,
> it costs *cheap correspondence*, and correspondence is exactly what merging is.
> Chambers, Erwig & Luckey (VL/HCC 2010) concede the consequence directly:
> inferring structural change from positional cells *"is generally ambiguous and
> not straightforward."* `RESEARCH.md` §3 then demonstrates the cost empirically:
> two branches, an auto-merge with **zero conflicts**, and a total of **480
> instead of 660** — a 27% error with no marker anywhere.
>
> Every attack in this document leaves that intact. `textconv` gives diffs, not
> merges. GenOffice's byte-preserving `.docx` editing solves the *document* leg
> and has no spreadsheet analogue — and could not have one, because the problem
> is the reference semantics, not the serialisation. `daff` merges CSV cells but
> not formulas. Excel Tables, Airtable, Notion, Coda, Baserow, NocoDB, Teable and
> Grist all use named references — so the design is mainstream, not exotic — but
> **Google Sheets shipped Tables in May 2024 and explicitly declined the per-row
> case** (*"Tip: #This Row currently is not supported."*). The world's
> second-largest spreadsheet looked at this exact primitive and did not ship it.
>
> So the unclaimed artefact is: **one file format for tabular data with row-relative
> named-column references, one three-way merge driver for it, and one binding to
> an existing Apache-2.0 formula engine (IronCalc).** Three deliverables. No
> editor, no canvas, no slides, no sync server, no suite, no substrate.

Scope limits I am imposing on my own concession, so it is not smuggled back into
a suite:

- It is **one primitive, not three.** The sequential leg is solved (pandoc,
  Typst, GenOffice, every editor on earth). The spatio-visual leg is solved
  (draw.io's plain `<mxCell>` XML, D2, Graphviz, Mermaid — one-line diffs, §1.7).
- It is a **format plus a merge driver**, not an application. It should ship as a
  `git merge` driver and a library, the way `daff` did — the thing `RESEARCH.md`
  §4 already identifies as "the cheapest large win available."
- Its audience is **people who version-control models**: finance, research,
  config-as-data, and agents proposing changes to spreadsheets for human review.
  That is a real population and a small one.
- Its usability is **unproven and the evidence leans against it.** McKeever &
  McDaid's three EuSpRIG papers found non-experts using range names slower and
  more error-prone. `RESEARCH.md` §3 is right that the rebuttal (a column header
  is not indirection) is plausible **and unreplicated**. This is defensible on
  merge grounds only — a version-control argument, never a usability one.

If the ambition is Git/Postgres/Unix, this is not it. It is a merge driver. Build
the merge driver.
