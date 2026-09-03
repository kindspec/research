#!/usr/bin/env python3
"""M1: markdown has FOUR scattered namespaces, not one. PASS4 catalogued the
link-label case. Here are the rest, each merging clean and each silently
picking one binding. Resolved with real tools: pandoc and python-markdown."""
import sys, os, subprocess, yaml, re
H = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(H, '..', 'R1-common'))
from gw import git_merge

def doc(n=12): return '# Doc\n\n' + '\n'.join(f'## S{i}\n\nBody {i}.\n' for i in range(1, n+1))
D = doc()

def pandoc(md, *args):
    return subprocess.run(['pandoc', '-f', 'markdown', '-t', 'html', *args],
                          input=md, capture_output=True, text=True).stdout

print('--- M1a duplicate FOOTNOTE label ---')
O = D.replace('Body 2.',  'Body 2 with a note.[^n]\n\n[^n]: Alice\'s footnote.')
T = D.replace('Body 10.', 'Body 10 with a note.[^n]\n\n[^n]: Bob\'s footnote.')
rc, txt, n = git_merge(D, O, T, 'a.md')
print(f'  git merge exit={rc} ({"CLEAN" if rc==0 else "CONFLICT"}) markers={n}')
print(f'  definitions present in file: {txt.count("[^n]:")}')
html = pandoc(txt)
notes = re.findall(r'<li id="fn1">.*?</li>', html, re.S)
print(f'  pandoc rendered footnote bodies: '
      f'{re.findall(r"footnote.>(.*?)<", pandoc(txt))[:3] if False else ""}')
print('  rendered footnote text:', [t.strip() for t in
      re.findall(r'<li id="fn\d+"[^>]*>\s*<p>(.*?)(?:<a|</p>)', html, re.S)])
print(f'  both markers point at: {sorted(set(re.findall(r"href=\"#fn(\d+)\"", html)))}')
print('  ==> two authors, two footnotes, one survives. Clean merge, no marker.')

print()
print('--- M1b duplicate HEADING ANCHOR {#id} -- the address grammar\'s own target ---')
O = D.replace('## S2\n',  '## S2 {#findings}\n')
T = D.replace('## S10\n', '## S10 {#findings}\n')
rc, txt, n = git_merge(D, O, T, 'a.md')
print(f'  git merge exit={rc} ({"CLEAN" if rc==0 else "CONFLICT"}) markers={n}')
print(f'  headings carrying {{#findings}}: '
      f'{[l for l in txt.splitlines() if "findings" in l]}')
html = pandoc(txt)
print(f'  ids emitted by pandoc: {re.findall(r"<h2 id=\"([^\"]+)\"", html)}')
print('  ==> `q3-review.md#findings`, the design\'s own worked example, now names two')
print('      blocks. The reference resolves to whichever the resolver reaches first.')

print()
print('--- M1c duplicate block id {#foo} arriving by copy-paste ---')
O = D.replace('Body 3.', 'Body 3. {#total}')
T = D.replace('Body 9.', 'Body 9. {#total}')
rc, txt, n = git_merge(D, O, T, 'a.md')
print(f'  git merge exit={rc} markers={n}  occurrences of {{#total}}: {txt.count("{#total}")}')

print()
print('--- M1d duplicate YAML FRONTMATTER keys (frontmatter is "co-located") ---')
FM = '---\nid: 01J8ZQ4K7X\ntitle: Q3 Review\nstatus: draft\n---\n\n' + D
O = FM.replace('title: Q3 Review\n', 'title: Q3 Review\nowner: alice\n')
T = FM.replace('status: draft\n', 'status: draft\nowner: bob\n')
rc, txt, n = git_merge(FM, O, T, 'a.md')
print(f'  git merge exit={rc} ({"CLEAN" if rc==0 else "CONFLICT"}) markers={n}')
fm = txt.split('---\n')[1]
print(f'  frontmatter:\n{"".join("      "+l+chr(10) for l in fm.strip().splitlines())}', end='')
try:
    print(f'  yaml.safe_load -> {yaml.safe_load(fm)}')
    print('  ==> PyYAML applies LAST-WINS to duplicate keys with no warning. Being on')
    print('      adjacent lines is not co-location; git needs the SAME line.')
except Exception as e:
    print(f'  yaml.safe_load raised {type(e).__name__} (loud, held): {e}')

print()
print('--- M1e the artifact UUID is not unique under the commonest editing act ---')
print('  PASS5: "Frontmatter carries the minted artifact UUID" and .notes/ is keyed')
print('  by it. `cp q3-review.md q4-review.md` duplicates the UUID. Nothing in the')
print('  format or in git detects it, and every standoff annotation now attaches to')
print('  two documents. No experiment needed; the format has no uniqueness mechanism.')
