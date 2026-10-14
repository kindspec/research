# D8-block-definitions: within-file uniqueness under candidate block definitions

D8's uniqueness measurement (`D8-identity/e4_uniqueness.py`,
`design-findings/D8-identity.md` §3.3) re-run under each candidate answer to
kindspec/blockspec#4, "what is a block?". It counts the same thing under every
definition: how many blocks share their exact content with another block in the
same file, and how many distinct contents do.

It measures and does not argue. Whether a list is one block or many is a
modelling choice that this output informs but does not decide.

    measure.py       the measurement
    arms.json        the seven arms: blockspec spike/PRE-REGISTRATION-2.md §6.2, verbatim
    results.txt      measure.py's stdout over all seven arms
    red_states.sh    every refusal measure.py makes, one case per die() call, shown to fire
    red-states.txt   red_states.sh's stdout

## Why a parser, and which

e4 splits a file with D8's boundary-only splitter: chunks separated by blank
lines, with fences respected. It cannot tell a list from its items, and a list
whose items are separated by blank lines comes out as one chunk per item. So
"a list as one block" and "each item as a block" are not available under it.
This parses each file as CommonMark with **markdown-it-py 3.0.0**, preset
`commonmark` with GFM tables enabled, so that a paragraph, a top-level node, a
list, a list item and a section are each a node. `measure.py` refuses any other
version of the parser, because a different parser draws different boundaries.

On Debian 13 the parser is the `python3-markdown-it` package, version
`3.0.0-3`. Elsewhere, `pip install markdown-it-py==3.0.0`, or run with
`uv run --with markdown-it-py==3.0.0 python3 measure.py ...`.

## The definitions

Leading YAML frontmatter is stripped before parsing and is a block under no
CommonMark definition. `a0` and `f0` run D8's own splitter over the whole file,
frontmatter included, as D8 did; D8's `btype()` types frontmatter as `prose`
(D8 §11 item 8).

| code | label | a block is | content compared |
|---|---|---|---|
| a0 | d8-prose | a D8 chunk that `btype()` types `prose` (the design brief's figure) | the chunk, stripped |
| a1 | para-top | a top-level paragraph | the paragraph's inline source |
| a2 | para-any | a paragraph at any depth, inside list items and block quotes too | the paragraph's inline source |
| b | top-node | a top-level node; a list is one node | the node's source lines, stripped |
| b2 | top-node-text | (b), less code and raw-HTML nodes | as (b) |
| d | top-items | (b), with each top-level list replaced by its items | an item: its source lines, marker removed from the first, each line left-stripped |
| d2 | items-any | a list item at any depth; a parent item contains its sub-items | as (d); inside a block quote, the `>` prefix is removed from each line first |
| e | section | a top-level heading through the line before the next top-level heading of the same or higher rank, plus any text before the first heading | the section's source lines, stripped |
| e2 | section-flat | a top-level heading through the line before the next top-level heading of any rank, plus any text before the first heading | as (e) |
| f | leaf | a paragraph, heading, code block, HTML block, table or thematic break, at any depth | per type: inline source; `#` per rank plus the heading text; fence markup, info string and body; the HTML; the table's lines, each stripped; for a thematic break, its markup alone (`---`, `***`), so every break of one style is the same content |
| f0 | d8-chunk | a D8 chunk of any type | the chunk, stripped |

**Candidate (c), a list as one block, is (b).** A top-level list is one
top-level node, so the two are the same partition under a CommonMark parse.
The list question is (b) against (d), and (d2) for nested items. Under D8's
splitter the two could not be separated, which is why `f0` and `b` differ.

(e) is not a partition: a section contains its subsections, so one line can
be in several blocks. (e2) is a partition. A heading inside a list item or a
block quote does not start a section.

Content is compared exactly, as a quote anchor compares it. Two blocks
duplicate when their contents, as extracted above, are identical strings. Each
definition is compared only with itself.

## The columns

Every count is over the blocks whose content is at least `minlen` characters,
reported at `minlen` 1, 20, 40 and 120. e4 and the design brief use 40.

| column | what it counts |
|---|---|
| blocks | instances |
| dup in file | instances whose content occurs again in the same file: e4's `dup in same file` |
| distinct | distinct contents in the arm, keyed by sha256: a content repeated within a file or across files counts once. This is PRE-REGISTRATION-2 §6.1's unit, `(arm, sha256(block content))` |
| distinct, dup in file | distinct contents that occur twice or more in at least one file |
| local | distinct contents that occur in exactly one file of the arm |
| local, dup in file | local contents that occur twice or more in their file |

**What "authored" means here.** Instance counts are inflated by replication,
as rowspec's cell counts were. Two removals are applied:

- **Generated files are not read.** PRE-REGISTRATION-2 §6.3's `yaml-fence`
  rule: a file is excluded when its leading YAML fence holds
  `auto_generated: true`, or its text holds `THIS FILE IS AUTO-GENERATED`.
- **Replicated content counts once** (`distinct`), and **content replicated
  across files is dropped altogether** (`local`). A block that appears in more
  than one file is a template, an include or boilerplate, not something
  authored for the place it sits. `local` is the stricter of the two: it also
  drops a passage an author did write twice, in two files.

Neither removal can hide a within-file duplicate of an authored block.
`distinct, dup in file` counts a content once however many times it repeats.
`local, dup in file` keeps every content confined to one file.

`k8s-en` and `k8s-l10n` are never pooled. Translations of one paragraph are
different bytes, so `k8s-l10n` counts a translated paragraph once per language
(PRE-REGISTRATION-2 §6.4).

## Validation

Before anything is measured, `measure.py` re-runs D8's own procedure on D8's
three arms: `blocks()` from `anchor_eval.py`, `btype()` from `anchor_eval3.py`,
and e4's loop, copied, at 20, 40 and 120. The output must equal
`D8-identity/results-e4.txt` byte for byte, or it exits 1. `results.txt` records
both hashes. That ties the pins, the file lists and the reading of each file to
the figures the design brief cites.

The new arms' D8 rows were also compared with blockspec's own run of
the same splitter, `spike/results/cheap-arm/uniqueness-distinct-yaml-fence-rule.txt`
at kindspec/blockspec `1a969d0`. Its `n`, `dup in same file`, `distinct: n`
and `same file` columns for `k8s-website-en`, `cncf-toc` and `site-policy` at
≥40 equal this run's `f0 d8-chunk` rows by type, under "By type, minlen=40",
for `k8s-en`, `cncf-toc` and `site-policy`: 18 rows, six types in each of three
arms, none differing. That comparison is not in `measure.py`, because it needs a
blockspec checkout.

`uncovered` in the arms table counts non-blank lines, after frontmatter, that
no top-level node spans. A line-by-line classification of those lines, in
every arm where the count is not zero, found every one to be a link reference
definition, which CommonMark parses into no node. That classification is not
in `measure.py`.

`red_states.sh` has one case for each `die()` call in `measure.py`, including
the `git()` wrapper's, which an invalid pathspec reaches. It passes a case only
when both the exit
code and the message are the expected ones, so a case cannot pass on an earlier
refusal. That rule caught one: before the no-block check was moved ahead of the
D8-arms check, the no-block case exited 2 for the wrong reason and was reported
`UNEXPECTED`. The validation case alters `results-e4.txt` in a copy of
`D8-identity/` and checks that the alteration applied before running.

## Running it

The clones are not redistributed; `CORPORA.md` names each. Each must be a full
working tree at its pin with no tracked changes. `k8s-en` and `k8s-l10n` read
one kubernetes/website clone.

    python3 -I measure.py \
      --clone rust-book=PATH --clone obsidian-help=PATH --clone cmspec=PATH \
      --clone kubernetes-website=PATH --clone cncf-toc=PATH \
      --clone site-policy=PATH > results.txt

    ./red_states.sh rust-book=PATH obsidian-help=PATH cmspec=PATH \
      kubernetes-website=PATH cncf-toc=PATH site-policy=PATH > red-states.txt

It reads the work trees and writes nothing outside its stdout. It takes under
a minute. `results.txt` was produced twice, from two separate sets of clones at
the same pins, and the two outputs were byte-identical.

`--show DEF:ARM` prints, in place of the report, each content of that
definition that repeats within a file in that arm, most repeated first. It
quotes the corpus, so its output is not committed. Two examples of what it
explains:

    python3 -I measure.py --clone ... --show a1:rust-book
    python3 -I measure.py --clone ... --show f0:rust-book

The first shows that rust-book's top-level paragraphs of ≥40 characters, which
repeat within a file where D8's prose did not, are the filename captions
`<span class="filename">Filename: src/main.rs</span>` and three like it.
CommonMark starts an HTML block at a `<span>` only when the tag is alone on its
line, so these are paragraphs; D8's `btype()` calls any chunk starting with `<`
`html`. The second accounts for all 197 of rust-book's in-file `html` repeats
at ≥40 in D8's split: 54 are those captions and 143 are HTML comments, 125 of
them one comment, `<!-- Old headings. Do not remove or links may break. -->`.

## What this does not measure

- **Edits.** This is uniqueness at one tree. It says nothing about whether a
  block, under any definition, still resolves after the document is edited.
  That is D8 §3.1–3.2's measurement, and it was run only under D8's splitter.
- **djot.** The parse is CommonMark, and djot's block boundaries are not
  CommonMark's. blockspec#3, djot or markdown, is open.
- **Shortcodes and dialects.** kubernetes/website writes Hugo shortcodes, which
  CommonMark reads as text. The parser cannot see a `{{< highlight >}}` region
  as code, so a line starting with `#` inside one becomes a heading and starts
  a section. How many of the k8s arms' sections that creates is not measured. Obsidian's callouts are parsed as block
  quotes, and its `^id` block references as text.
- **Cross-file uniqueness.** A quote anchor resolves within one file, so
  within-file duplication is what this reports. Distinct and local counts use
  the whole arm only to remove replicated content.
