# Academic literature on spreadsheet addressing, diffing and abstraction

Relayed from a sub-agent research pass, 2026-08-28. Verification labels and the
"could not confirm" list are that agent's own and are preserved.

**Read this before committing to the named-addressing thesis.** It contains the
strongest empirical evidence *against* it that exists.

## 1. References vs names — the folk wisdom is contradicted by the data

**The case for structural references.** Miller, Hermans, Braun, "Gradual
structuring", ITHET 2016 (open PDF: opus.lib.uts.edu.au/bitstream/10453/102111/4/),
with a companion at VL/HCC 2016. Directly compares A1 vs R1C1 vs named ranges vs
header-path references. Verbatim: enhanced referencing is "designed to be readable
as with A1 referencing, yet have the invariant quality of R1C1 referencing"; and
on Excel names, "This is superior to named ranges as there is no indirection with
enhanced referencing, whereas a named range is not much more than an alias for a
reference." It calls Excel tables / structured references "weak forms" of the idea.

**The case against — and this is the part that matters.** McKeever & McDaid, three
EuSpRIG papers, all on arXiv:

- arXiv:0908.0935 (2009) — "novice users debug on average significantly fewer
  errors if the spreadsheet contains named ranges"
- arXiv:1009.2765 (2010) — "How do Range Names Hinder..."
- arXiv:1111.6872 (2011) — "formulas developed by non-experts using range names
  are more likely to contain errors and take longer to develop", significant
  across two iterations

So the empirical record says named references made non-expert users *slower and
more error-prone*. The proposed mechanism is indirection cost: on a grid, the
referent is already visible, so a name adds a lookup rather than removing one.
Miller & Hermans' rebuttal is that this indicts *Excel's* name mechanism — a
global alias with no visible binding — rather than structural addressing as such.
That rebuttal is plausible and is exactly what Kova's column names and
`.calc.md`'s adjacent variable definitions do differently (the binding is local
and on-screen). But it is a rebuttal, not a replication.

**Honest read for this project:** named addressing is defensible primarily on
*diff and merge* grounds, which is a version-control argument, not a usability
one. Do not claim it is easier for users — the only direct evidence points the
other way.

**A further complication.** Hermans, ICSM 2012 (OA at repository.tudelft.nl, file
`File_565ad6fe-2b4e-4dc7-b1b3-a80e7e6f3a1b`): the "Multiple References" smell is
the most prevalent in the EUSES corpus at 23.8%, and the proposed refactoring is
*positional* — "place the values in B7;C18;C19;F19 in A6 until A10, and rewrite as
SUM(A1:A10)." In the A1 model, **layout is the abstraction mechanism.** A format
that discards coordinates discards that mechanism and must replace it.

## 2. Version control, diff and merge — the row-insertion problem is formally hard

Headline: Chambers, Erwig, Luckey, "SheetDiff", VL/HCC 2010
(web.engr.oregonstate.edu/~erwig/papers/SheetDiff_VLHCC10.pdf). A single row
deletion yields "changes in all cells A2, A3, ..., A20". They infer row/column
insert-delete by thresholding and concede it "is generally ambiguous and not
straightforward. For example, in the case that the majority of the cells in a row
are changed, does this signify that a row has been added or simply that many of
the cells have been changed?" Also documents that Excel track-changes "can not
show differences between arbitrary versions".

Supporting work: Hunt, "DiffXL", EuSpRIG 2009 (arXiv:0908.3022) — structure must
be reconstructed before diffing. Harutyunyan et al., VL/HCC 2012 — planted-model
benchmark showing structural edits are the hard class. Dou et al., VEnron, ICSE
2016 and Xu et al., SpreadCluster, MSR 2017 (arXiv:1704.08476) — in practice
"different versions of a spreadsheet coexist as individual and similar
spreadsheets", i.e. real users version by copying files. Ferreira & Visser
arXiv:1211.7100. Macedo et al., CIbSE 2019 (metadata only). Luckey/Erwig/Engels,
JVLC 2012, model-based evolution.

Also Paine's **Excelsior** (arXiv:0803.0163, 0803.2027), which "separates them
from layout, and allows both components and layout to be changed without breaking
dependent formulae" — prior art for exactly the separation this project needs.

**This is the strongest single argument for the whole thesis.** The row-insertion
ambiguity that SheetDiff has to *guess* at is not a hard problem in a
line-oriented or named-column text file: the diff is exact because the identity
of a row is its content, not its ordinal. A git-backed format doesn't solve
spreadsheet diffing better than SheetDiff — it dissolves the problem SheetDiff
was written to attack.

## 3. Error taxonomy — reference errors are a named, measured category

Panko, "Revisiting the Panko-Halverson Taxonomy", EuSpRIG 2008 (arXiv:0809.3613),
read in full: "Mechanical errors are typing errors, pointing errors, and other
simple slips"; "A slip is an error during a sensory-motor action, such as typing
the wrong number or **pointing to the wrong cell**." It reproduces the
Powell/Lawson/Baker 2007 taxonomy, which has an explicit top-level type:
"**Reference** — A formula contains one or more incorrect references to other
cells", and redefines Omission as "pointing to a blank cell".

Latent-error point: hardcoding instead of a cell reference "does not cause errors
then, but it makes errors more likely later" (confirmed by Teo & Tan 1997).

Field data: Powell, Lawson, Baker (arXiv:0801.0715) — "errors in 0.8% to 1.8% of
all formula cells" across 50 organizations.

Practical note: eusprig.org 403s to WebFetch, but EuSpRIG proceedings 2005–2013
are mirrored individually on arXiv under cs.SE.

## 4. Why spreadsheets lack abstraction at all

Peyton Jones, Blackwell, Burnett, ICFP 2003, Uppsala
(microsoft.com/en-us/research/wp-content/uploads/2016/07/excel-1.pdf), read in
full. Framing: "spreadsheets lack the most fundamental mechanism that we use to
control complexity: the ability to define re-usable abstractions... Can you
imagine programming in C without procedures, however clever the editor's
copy-and-paste technology?" Design: user-defined functions defined *in the grid*,
with the signature taken from a subset of cells as parameters.

The maintainability argument runs through the Cognitive Dimension of **viscosity**:
"a language that lacks procedural or functional abstraction is highly viscous,
because code must be repeated"; and "A named function encapsulates the formula,
thereby protecting against that source of risk. It also reduces the user's
attentional cost by reducing viscosity... because the encapsulated formula needs
to be changed in only one place."

They also use the *abstraction gradient* dimension and *Attention Investment* to
explain why end users rationally decline to abstract — which is the honest
counterweight to reading McKeever/McDaid as a verdict against names. Follow-on:
Sarkar, Gordon, Peyton Jones, Toronto, "Calculation View", VL/HCC 2018 — add a
structural representation over the grid "without altering the conventional grid
representation or its formula syntax". That dual-representation idea is directly
applicable: keep the grid as a *view*, keep the text as the file.

## 5. Theory: positional vs named is a known formal dichotomy

Abiteboul, Hull, Vianu, *Foundations of Databases*, Ch.3 §3.2 "Named versus
Unnamed Perspectives" (free at webdam.di.ens.fr/Alice/ — note webdam.inria.fr has
a broken certificate). Formalizes exactly this dichotomy: the named perspective
views tuples as functions, the unnamed as elements of a Cartesian product. They
are interconvertible, but "the named perspective permits easy and natural
specification of correspondences between columns of different relations whereas
the unnamed perspective does not... this leads to different but equivalent sets of
natural primitive algebra operators."

Equal expressive power, different primitives. **Positional addressing is not less
expressive — it is less composable.** That is the precise claim to make, and it is
narrower than "named addressing is better".

Standards: ODF v1.3 Part 4 OpenFormula §4.8 defines a reference purely
geometrically ("the smallest cuboid that..."), with named expressions in a
separate §5.11 that is tiered out of base conformance. Microsoft's own
structured-references documentation claims "The names in structured references
adjust whenever you add or remove data".

## Could not confirm — do not cite as verified

ECMA-376 Part 1 normative prose on structured-reference grammar (standard PDF
unfetchable, MS-OI29500 URLs 404); ODF Part 3 §9.4.12/9.4.13 body text (document
too large for the fetcher); RefBook's specific seven refactorings (PDF 404, closed
access); abstracts for several IEEE papers where IEEE elides them from Semantic
Scholar and OpenAlex (VEnron, Gradual Structuring VL/HCC, planted-model,
inter-worksheet smells); Codd 1970 itself.
