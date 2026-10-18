# Pre-registration 4: the run

blockspec `spike/PRE-REGISTRATION-4.md` (merged as `08ef724`, amended by
blockspec#52 as `80ef549`) fixes what this measures and what each result
means. This directory is what its §3 publishes. The harness ran at research
`735091e`, against the blockspec reference resolver at `d38a6bc`, on the
four verdict arms at their `arms.json` pins.

    replay-ARM.txt     replay.py's stdout, one run per arm (--arm ARM --dump)
    dump.jsonl.gz      the four dumps, concatenated in arms.json's order
    kinds-gap5.txt     kinds.py's stdout on the dump at gap 5
    sample.txt         sample.py's stdout (--gap 5 --cap placed/resolves=100)
    key.jsonl          sample.py's key: each packet's comment, stratum and truth
    strata.json        sample.py's stratum sizes, caps and profile counts
    batches.json       each labeller's packet ids, in the order given
    pass-a.jsonl       the first pass of labels
    pass-b.jsonl       the second pass of labels
    score.txt          score.py's stdout on the key and both passes
    wrongs.txt         every WRONG at every gap, listed from the dump

## Verdict

**Refusals too high.** `score.txt`'s pooled line: with labels for truth,
the refusal rate at gap 5 over the four verdict arms is **17.0%**, from
16.3% to 18.7% with every stratum at the end of its interval, among
comments on versions the profile accepts. The whole range is above the 5%
bar (pre-registration §0 choice 1, read as §4 says).

**No resolver defect.** No comment at any gap is `WRONG` (`wrongs.txt`),
and the labels put no resolving comment anywhere other than where it
resolved (`score.txt`, which lists none). So there is nothing for §5 to
classify.

## Figures

From `score.txt`, gap 5, among comments on versions the profile accepts:

| arm | refusal rate | range |
| --- | --: | --: |
| rust-book | 22.1% | 21.1% to 22.8% |
| obsidian-help | 17.6% | 16.8% to 19.7% |
| k8s-en | 8.1% | 8.1% to 8.1% |
| cncf-toc | 10.4% | 10.4% to 11.5% |
| pooled | 17.0% | 16.3% to 18.7% |

Besides those, 595 comments sit on versions the profile refuses (509 on
rust-book, 86 on k8s-en); counting each as a refusal of surviving text,
the pooled rate is 29.1%. The oracle's error where it places a comment is
0 of the 585 labelled, and 4.8% with every stratum at the upper end of its
interval.

The refusals by cause, pooled over the four arms (`kinds-gap5.txt`, 570
loud comments at gap 5): 275 `REFUSED(near-copy)`, of which 268 are on
paragraphs whose text is unchanged; 168 `DETACHED`; 94
`REFUSED(crowded-gap)`; 31 `ORPHANED`; 2 `REFUSED(repeat)`. Per arm, the
`loud` lines of each `replay-ARM.txt` give the same by status and reason.
Which rule to revisit is not decided here (§4): it is the following
adjudication's.

## Labelling

629 packets, each labelled twice: pass A by 37 labellers, pass B by 37
more, each a fresh instance of Claude Opus 5.5 (`claude-opus-5-5`) with no
other context, given `../labelling-brief.md` at `735091e` with its packet
directory, its output file and its packet ids filled in (`batches.json`).
The two passes agree on all 629, so no third label was needed.

Choice 6 deals pass B "from the key's middle onward, wrapping round, so a
labeller's batch differs between the passes". With 629 packets and 37
labellers of 17, the rotation by 314 is 18 places modulo 37, so each pass-B
batch holds the same packets as one pass-A batch, in a different order;
the procedure was followed as written. Every label in the two passes still
comes from a different instance.

## Running it

From `experiments/D8-anchor-replay/` at `735091e`, with each clone at its
pin and `BLOCKSPEC` a checkout of `d38a6bc`:

    python3 -I replay.py --blockspec BLOCKSPEC --clone CLONE=PATH --arm ARM --dump ARM.jsonl > replay-ARM.txt
    cat rust-book.jsonl obsidian-help.jsonl k8s-en.jsonl cncf-toc.jsonl > dump.jsonl
    python3 -I sample.py --blockspec BLOCKSPEC --clone ... --dump dump.jsonl --gap 5 \
        --cap placed/resolves=100 --packets PACKETS --keydir KEY
    python3 -I score.py --keydir KEY --labels pass-a.jsonl --labels pass-b.jsonl
    python3 -I kinds.py --blockspec BLOCKSPEC --clone ... --dump dump.jsonl --gap 5

`score.py` reproduces `score.txt` from `key.jsonl`, `strata.json` and the
two passes here.
