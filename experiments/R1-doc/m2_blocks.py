#!/usr/bin/env python3
"""M2: the block-identity scheme in blocks.py is POSITIONAL and UNSTABLE.
Block names are content hashes, disambiguated by ORDINAL. Both halves violate
I2 (names, not places)."""
import sys, os
H = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [os.path.join(H,'..','R1-common'), os.path.join(H,'..','L3-block-roundtrip')]
from gw import git_merge
import blocks

DOC = """# Report

TBD

## Revenue

Revenue grew.

## Costs

TBD

## Outlook

Outlook is good.
"""
print('--- M2a two identical blocks get names by ORDINAL, i.e. by POSITION ---')
for name, raw in blocks.parse(DOC):
    if raw.strip(): print(f'    {name:12s} {raw.strip()[:24]!r}')
print('  the two "TBD" paragraphs are `h` and `h.1`. `.1` means SECOND, which is a')
print('  coordinate. I2: "Nothing may be referenced by a coordinate that a')
print('  concurrent edit can change."')

print()
print('--- M2b inserting a third copy above renames the others ---')
NEW = DOC.replace('## Revenue\n', '## Scope\n\nTBD\n\n## Revenue\n')
before = {n for n, r in blocks.parse(DOC) if r.strip() == 'TBD'}
after  = {n for n, r in blocks.parse(NEW) if r.strip() == 'TBD'}
print(f'  before: {sorted(before)}   after: {sorted(after)}')
print('  the block previously called `X.1` (under Costs) is now `X.2`. A stored')
print('  reference to `X.1` silently retargets to a DIFFERENT paragraph.')

print()
print('--- M2c editing a block changes its NAME (content-hash identity) ---')
ED = DOC.replace('Revenue grew.', 'Revenue grew by 9%.')
b0 = dict((r.strip(), n) for n, r in blocks.parse(DOC))
b1 = dict((r.strip(), n) for n, r in blocks.parse(ED))
print(f'  "Revenue grew."      -> {b0["Revenue grew."]}')
print(f'  "Revenue grew by 9%."-> {b1["Revenue grew by 9%."]}')
print('  Every reference to that block breaks on a typo fix. PASS5 R1 already')
print('  measured this for rows ("content hash: SPLIT ROW") and chose opaque ids.')
print('  The .md side of the same design still uses content hashes.')

print()
print("--- M2d blocks.py mis-boundaries a VALID CommonMark nested fence ---")
NEST = "# Guide\n\nIntro.\n\n````\n```sh\nmake build\n```\n````\n\nDone.\n"
import subprocess
html = subprocess.run(['pandoc','-f','markdown','-t','html'], input=NEST,
                      capture_output=True, text=True).stdout
print(f'  pandoc sees {html.count("<code")} code block(s) and keeps "Done." a paragraph: '
      f'{"<p>Done.</p>" in html}')
bl = blocks.parse(NEST)
print(f'  blocks.py block count: {len(bl)}')
for i_, (nm, raw) in enumerate(bl): print(f'    block[{i_}] {nm}: {raw!r}')
print(f'  round-trip exact: {blocks.render(bl) == NEST}   <-- I1 holds BY CONSTRUCTION')
print('  ==> but the boundaries are WRONG: one code block became three blocks, and')
print('      one fenced code block became TWO blocks with two different names. I1')
print('      (render.parse==id) is satisfied by a parser that has no idea what the')
print('      blocks are: the round-trip law tests nothing about entity correctness.')

print()
print("--- M2e a blank line added by one author reformats every item in a list ---")
LIST = ("# Doc\n\nIntro.\n\n- alpha\n- beta\n- gamma\n- delta\n\nOutro.\n")
# Alice expands one bullet into two paragraphs. Bob edits an unrelated bullet.
O = LIST.replace('- beta\n', '- beta\n\n  more about beta\n\n')
T = LIST.replace('- delta\n', '- delta (revised)\n')
rc, txt, n = git_merge(LIST, O, T, 'a.md')
print(f'  git merge exit={rc} ({"CLEAN" if rc==0 else "CONFLICT"}) markers={n}')
h0 = subprocess.run(['pandoc','-f','markdown','-t','html'], input=LIST,
                    capture_output=True, text=True).stdout
h1 = subprocess.run(['pandoc','-f','markdown','-t','html'], input=txt,
                    capture_output=True, text=True).stdout
print(f'  before: <li> items wrapped in <p>: {h0.count("<li><p>")} of {h0.count("<li")}')
print(f'  after : <li> items wrapped in <p>: {h1.count("<li><p>")} of {h1.count("<li")}')
print('  ==> one blank line changed the rendering of every OTHER item. That is')
print('      PASS4\'s own listed defect ("one line encodes a property of every other')
print('      line"), present in the markdown the design adopts unchanged.')

print()
print("--- M2f ordered-list numbering ---")
OL = "# Doc\n\n1. first\n2. second\n3. third\n4. fourth\n\nEnd.\n"
O = OL.replace('1. first\n', '1. first\n2. inserted by Alice\n')
T = OL.replace('4. fourth\n', '4. fourth\n5. appended by Bob\n')
rc, txt, n = git_merge(OL, O, T, 'a.md')
print(f'  git merge exit={rc} markers={n}')
print('  source list markers:', [l.split(".")[0] for l in txt.splitlines() if l[:1].isdigit()])
h = subprocess.run(['pandoc','-f','markdown','-t','html'], input=txt,
                   capture_output=True, text=True).stdout
print(f'  rendered items: {h.count("<li>")}  (CommonMark renumbers from the FIRST marker,')
print('  so the source numbers become decorative and the diff shows numbers nobody')
print('  can trust.) Legitimate-but-terrible, not silent-wrong.')
