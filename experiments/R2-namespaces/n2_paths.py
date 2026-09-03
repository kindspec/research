#!/usr/bin/env python3
"""N2: the namespace the audit could not see, because it is not inside a file.

Every audited namespace is in-file, plus one corpus-scoped (the artifact UUID).
But the design's own address grammar is `artifact#namepath`, and the artifact
half of that address is A FILE PATH. Paths are a namespace, they are scattered
across the tree by construction, and nothing validates them.
"""
import os, subprocess, tempfile, shutil, unicodedata, sys
def sh(*a, cwd=None): return subprocess.run(a, cwd=cwd, capture_output=True, text=True)

T = "| id | qty |\n| -- | --: |\n| r_1 |  {} |\n\nkey := id\ngrand := sum(qty)\n"

d = tempfile.mkdtemp()
sh('git','init','-q',d)
for k,v in [('user.email','t@e'),('user.name','t'),('core.precomposeunicode','false')]:
    sh('git','config',k,v,cwd=d)
open(os.path.join(d,'README.md'),'w').write('x\n')
sh('git','add','-A',cwd=d); sh('git','commit','-qm','b',cwd=d); sh('git','branch','-M','main',cwd=d)

NFC = unicodedata.normalize('NFC', 'café.tbl')      # 8 code points
NFD = unicodedata.normalize('NFD', 'café.tbl')      # 9 code points
print(f'--- N2a two branches add an artifact at the "same" path, NFC vs NFD')
print(f'    NFC {NFC!r}  bytes={len(NFC.encode())}')
print(f'    NFD {NFD!r}  bytes={len(NFD.encode())}')
sh('git','checkout','-qb','x',cwd=d)
open(os.path.join(d,NFD),'w').write(T.format(20)); sh('git','add','-A',cwd=d); sh('git','commit','-qm','x',cwd=d)
sh('git','checkout','-q','main',cwd=d)
open(os.path.join(d,NFC),'w').write(T.format(10)); sh('git','add','-A',cwd=d); sh('git','commit','-qm','o',cwd=d)
r = sh('git','merge','x','-m','m',cwd=d)
print(f'    git merge exit={r.returncode}')
print('    tracked files:', sorted(x for x in sh('git','ls-files',cwd=d).stdout.split('\n') if x))
print('    Two artifacts. They render identically in every UI, in `ls`, and in a')
print('    PR diff. The reference `{{ café.tbl#grand }}` resolves to 10 or to 20')
print('    depending on which normalisation the reader applies to its own source.')
print('    C4 mandates NFC normalisation INSIDE the parser -- which cannot see a')
print('    path. And on macOS or Windows one of the two checkouts overwrites the')
print('    other, so the working tree loses an artifact with no conflict.')

print()
print('--- N2b the same for case: Budget.tbl vs budget.tbl ---')
sh('git','checkout','-qb','y',cwd=d)
open(os.path.join(d,'Budget.tbl'),'w').write(T.format(99)); sh('git','add','-A',cwd=d); sh('git','commit','-qm','y',cwd=d)
sh('git','checkout','-q','main',cwd=d)
open(os.path.join(d,'budget.tbl'),'w').write(T.format(1)); sh('git','add','-A',cwd=d); sh('git','commit','-qm','o2',cwd=d)
r = sh('git','merge','y','-m','m',cwd=d)
print(f'    git merge exit={r.returncode}  tracked:',
      [x for x in sh('git','ls-files',cwd=d).stdout.split('\n') if 'udget' in x])
print('    Clean on Linux; a checkout collision on the two filesystems most')
print('    users have. Neither the parser nor corpus_check.py looks at paths.')

print()
print('--- N2c the .notes/ sidecar KEY namespace ---')
os.makedirs(os.path.join(d,'.notes'), exist_ok=True)
open(os.path.join(d,'.notes','01JGONE.json'),'w').write('{"quote":"..."}\n')
open(os.path.join(d,'doc.md'),'w').write('---\nid: 01JHERE\n---\n\nBody.\n')
r = sh(sys.executable, os.path.abspath('../../conformance/corpus_check.py'), d)
print('   ', r.stdout.strip().replace('\n','\n    '), f'(exit {r.returncode})')
print('    A standoff annotation keyed to an artifact id that does not exist, and')
print('    an artifact with no annotation. corpus_check only looks for DUPLICATE')
print('    ids; the sidecar key space -- the other half of the same relation -- is')
print('    not enumerated in the audit at all. Deleting an artifact orphans its')
print('    notes silently; the audit found the cp case and stopped there.')
shutil.rmtree(d)
