# Pre-registration 5: the run

blockspec `spike/PRE-REGISTRATION-5.md` (merged as `04a612f`) fixes what
this measures and what each result means. This directory is what its §3
publishes. The harness ran at research `8ecb0e7`, against the blockspec
reference resolver at `ae1d274` (adjudication 0004's), on the four verdict
arms at their `heldout-arms.json` pins, and on the five arms 0004 was tuned
on as a regression check (choice 7).

    replay-ARM.txt         replay.py's stdout for each verdict arm (--arm ARM --dump)
    dump.jsonl.gz          the four verdict arms' dumps, in heldout-arms.json's order
    kinds-gap5.txt         kinds.py's stdout on that dump at gap 5
    sample.txt             sample.py's stdout (--gap 5 --cap placed/resolves=100)
    key.jsonl              sample.py's key: each packet's comment, stratum and truth
    strata.json            sample.py's stratum sizes, caps and profile counts
    batches.json           each labeller's packet ids, in the order given
    pass-a.jsonl           the first pass of labels
    pass-b.jsonl           the second pass of labels
    adjudicated.jsonl      the third label on the packets the two passes split
    score.txt              score.py's stdout on the key and all three
    wrongs.txt             every WRONG at every gap, listed from the dump
    regression/            the same replay, dump, kinds and wrongs for the five tuned arms

## Verdict

**Pass.** `score.txt`'s pooled line: with labels for truth, the refusal
rate at gap 5 over the four verdict arms is **2.9%**, from 2.8% to 4.2%
with every stratum at the end of its interval, among comments on versions
the profile accepts. The whole range is within the 5% bar (choice 1, read
as choice 2 says).

**No resolver defect.** No comment at any gap on any verdict arm is
`WRONG` (`wrongs.txt`), and the labels put no resolving comment anywhere
other than where it resolved (`score.txt`'s section for that is empty).
So there is nothing for §5 to classify.

## Figures

From `score.txt`, gap 5, among comments on versions the profile accepts:

| arm | refusal rate | range |
| --- | --: | --: |
| github-docs | 3.4% | 3.4% to 4.4% |
| vscode-docs | 3.2% | 3.0% to 4.7% |
| docker-docs | 1.8% | 1.8% to 2.4% |
| mdn-en | 2.9% | 2.9% to 4.4% |
| pooled | 2.9% | 2.8% to 4.2% |

Besides those, 33 comments sit on versions the profile refuses (3 on
github-docs, 30 on vscode-docs); counting each as a refusal of surviving
text, the pooled rate is 3.3% (3.2% to 4.6%). The oracle's error where it
places a comment is 0.1%, and 4.5% with every stratum at the upper end of
its interval.

The refusals the oracle places, by cause, pooled over the four arms
(`kinds-gap5.txt`, 213 loud comments at gap 5; the rate also counts
refused comments the oracle does not place and the labels find
surviving): 96 `REFUSED(crowded-gap)`, 52
`REFUSED(near-copy)` (22 on paragraphs whose text is unchanged), 40
`ORPHANED`, 23 `DETACHED`, 1 `REFUSED(repeat)` and 1
`REFUSED(unaccounted-copy)`.

**What it cannot see** (pre-registration 5 §4). The word oracle grades a
comment that lands on its span's surviving words as correct, so an edit
beside a span (`SPEC.md` §11.12) and R3 within one leaf are counted
correct. At gaps 1 and 25,
resolving comments the oracle does not count are checked by neither the
oracle nor the labels: 19 at gap 1 (github-docs 2, vscode-docs 8,
docker-docs 6, mdn-en 3) and 14 at gap 25 (all vscode-docs), counted from
the dump's rows with no verdict whose status resolves.

## The regression arms

`regression/` holds the same replay on rust-book, obsidian-help, k8s-en,
cncf-toc and site-policy, at 0004's resolver, into its own dump. They are
not sampled or labelled, and not pooled into the figures above. No comment
at any gap is `WRONG` (`regression/wrongs.txt`). With the oracle for truth,
at gap 5, 299 of 6,279 comments whose span survives are loud (4.8%), the
figure 0004 records; `regression/kinds-gap5.txt` gives them by cause.

## Labelling

743 packets. Pass A dealt them round-robin, in `key.jsonl`'s order, to 44
labellers of at most 17; pass B dealt them as 44 contiguous runs of the
key's order (39 of 17, then 5 of 16), so no pass-B batch repeats a pass-A
batch. Each labeller was a separate agent of Claude Opus 5.5
(`claude-opus-5-5`) with file tools, started with none of the context of
the session that ran the replay (it carries its harness's own system
context), and told to read `../labelling-brief.md` at `8ecb0e7`, with its
packet directory, its output file and its packet ids filled in
(`batches.json`). The two passes agree on 738 of 743. The five they split
went to one more such labeller (`C00`), whose labels decide them
(`adjudicated.jsonl`).

The key was kept in a directory no labeller was given or told of. Every
labeller's output went to one shared directory. Before pass B started,
pass A's outputs, and the files pass-A labellers had left in the shared
scratch directory, were moved out of reach. The same was done with pass B's
before the third label.

What the labellers could have seen beyond their packets:

- **Each other's helper scripts.** Labellers in the same pass wrote small
  search scripts into one shared scratch directory, and several reported
  another labeller overwriting a script of the same name while they used
  it. Each said its labels rest on the packet text it read. The scripts
  hold no labels.
- **Pre-registration 4's labels.** Copies of pre-registration 4's
  `pass-a.jsonl` and `pass-b.jsonl` were on the same machine, and 215 of
  this sample's packet ids are also ids there (`sample.py` draws ids from
  its generator seeded 11, as it did then), for different comments on
  different arms. A labeller that read one would have taken another
  comment's answer. By this check none did: of the 215, comparing either
  pass here with either pass there, no label that says the words survive
  gives the same later paragraph, and three labels match, all three saying
  they do not survive (403b322a, 7bc63c97 and c9657c6e), where chance gives
  about four and a half (16.6% of labels here say not surviving, 12.7%
  there). Between two and three notes are the same, depending on the
  passes compared, each "paragraph unchanged" or "sentence unchanged".

## Running it

From `experiments/D8-anchor-replay/` at `8ecb0e7`, with each clone at its
pin and `BLOCKSPEC` a checkout of `ae1d274`:

    python3 -I replay.py --blockspec BLOCKSPEC --clone CLONE=PATH --arm ARM --dump ARM.jsonl > replay-ARM.txt
    cat github-docs.jsonl vscode-docs.jsonl docker-docs.jsonl mdn-en.jsonl > dump.jsonl
    python3 -I sample.py --blockspec BLOCKSPEC --clone ... --dump dump.jsonl --gap 5 \
        --cap placed/resolves=100 --packets PACKETS --keydir KEY
    python3 -I score.py --keydir KEY --labels pass-a.jsonl --labels pass-b.jsonl --adjudicated adjudicated.jsonl
    python3 -I kinds.py --blockspec BLOCKSPEC --clone ... --dump dump.jsonl --gap 5

The clone keys are `github-docs`, `vscode-docs`, `docker-docs` and
`mdn-content`. `score.py` reproduces `score.txt` from `key.jsonl`,
`strata.json` and the three label files here. The regression arms run the
same `replay.py` and `kinds.py` with `arms.json`'s clone keys, concatenated
in its order.

The quoted words and labellers' notes remain under their repositories'
terms; `../../../NOTICE` lists them, for these arms and for the regression
arms, two of which have no licence. The blockspec verdict record beside
0004 follows this pull request.
