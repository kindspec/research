You are labelling comments on documents, for a measurement. Work only from
the packet files named below; do not open any other file or directory, and
do not try to work out what software produced the packets. Judge the text
alone.

Each packet `PACKETS/<id>.md` shows two versions of one Markdown file, as
numbered paragraphs ([P0], [P1], ...), one paragraph per line with line
breaks shown as spaces. A comment was left on three words of one paragraph
of the earlier version; they are marked ⟦like this⟧.

For each packet, decide: **do the marked words survive in the later
version, as the same passage?**

- **Survives**: the same three words, in the same order and adjacent
  (spacing and line breaks aside), and recognisably the same piece of the
  document. The paragraph around them may have been edited, reworded
  elsewhere, moved to another place, merged with another paragraph, or
  split. Punctuation attached to a word counts as part of the word:
  `limit` and `limit,` differ.
- **Does not survive**: any of the three words was changed, removed or
  reordered, or another word now sits between two of them; the paragraph
  was deleted; or the words appear in the later version only in an
  unrelated passage that happens to use them (a coincidental repeat, not
  the same passage).
- If it survives, give the later paragraph number that holds that passage.
  If several later paragraphs hold the words, pick the one that is the same
  passage, judging by the surrounding text; if you cannot tell, pick your
  best choice and start the note with `ambiguous:`.

Searching the packet for the marked words (e.g. with grep) finds the
candidates quickly; then read the paragraphs around each candidate, in both
versions, to judge whether it is the same passage.

Write one JSON object per line to OUT, one per packet, in any order:

    {"id": "<id>", "survives": true, "paragraph": 12, "note": "short reason"}
    {"id": "<id>", "survives": false, "paragraph": null, "note": "short reason"}

Write OUT with a file-writing tool, not a shell heredoc. Label every packet
in your list; do not skip one. Your final message: how many you labelled,
and the ids of any you found hard, with one line each on why.

Your packets (PACKETS = DIR):
