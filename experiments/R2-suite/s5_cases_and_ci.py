#!/usr/bin/env python3
"""S5: merge cases that pass for the wrong reason, corpus_check holes, and
whether CI -- the design's "portable enforcement point" -- actually enforces."""
import os, subprocess, sys, tempfile, shutil, runner, cases as C, ref_tbl as R

print('--- S5a merge/column-name-collision passes on a conflict it did not test ---')
base, ours, theirs = C.T, C.addcol(C.T,'code','A'), C.addcol(C.T,'code','B')
print('    addcol() appends a cell to EVERY line, so ours and theirs differ on')
print('    every row, not only on the header. The conflict is guaranteed by the')
print('    row edits. Same collision with IDENTICAL row cells:')
def addcol_same(t, name):
    L=[]
    for i,l in enumerate(t.splitlines()):
        if not l.startswith('|'): L.append(l)
        elif i==0: L.append(l+f' {name} |')
        elif i==1: L.append(l+' --- |')
        else: L.append(l+' x |')
    return '\n'.join(L)+'\n'
st, m = runner.git_merge(C.T, addcol_same(C.T,'code'), addcol_same(C.T,'kode'))
print(f'    two DIFFERENT new column names, identical row cells: git -> {st}')
print('    (co-location does hold; the case as written just cannot show it.)')

print()
print('--- S5b MUST_REFUSE cases assert the parser refuses, never WHY ---')
st, m = runner.git_merge(*[C.T,
   C.ins(C.T,'r_0001', C.ROW.format(id='r_0009',item='alpha',qty=1,unit=' 1.00')),
   C.ins(C.T,'r_0004', C.ROW.format(id='r_0009',item='beta', qty=2,unit=' 1.00'))])
try: R.evaluate(m)
except R.Malformed as e: print('    merge/duplicate-row-id refusal reason:', e)
print("    The runner only checks `except ref.Malformed`. An implementation that")
print("    refuses EVERY merged file for any reason passes both MUST_REFUSE cases.")
src = open('ref_tbl.py').read()
open('para_impl.py','w').write(src.replace("    tbl = [l for l in lines if l.strip().startswith('|')]",
    "    tbl = [l for l in lines if l.strip().startswith('|')]\n"
    "    if len(tbl) > 6: raise Malformed('paranoid: too many rows')"))
r = subprocess.run([sys.executable,'runner.py','para_impl'], capture_output=True, text=True)
print('    a "refuse any table with >6 lines" implementation:',
      [l for l in r.stdout.splitlines() if l.startswith('TOTAL')][0])
print('    -> it still passes both MUST_REFUSE cases; it fails only on unrelated ones.')
os.remove('para_impl.py')

print()
print('--- S5c corpus_check.py: what it does not check ---')
d = tempfile.mkdtemp()
open(os.path.join(d,'a.tbl'),'w').write('| id | qty |\n| -- | --: |\n| r_1 | 1 |\n| r_1 | 2 |\n\nkey := id\n')
open(os.path.join(d,'b.tbl'),'w').write('this is not a table at all\n')
open(os.path.join(d,'c.md'),'w').write('```\nid: 01J8\n```\n')
open(os.path.join(d,'d.md'),'w').write('---\nid: 01J8\n---\n')
os.makedirs(os.path.join(d,'.notes'))
open(os.path.join(d,'.notes','01JDOESNOTEXIST.json'),'w').write('{}\n')
r = subprocess.run([sys.executable, os.path.abspath('corpus_check.py'), d], capture_output=True, text=True)
print('   ', r.stdout.strip().replace('\n','\n    '), f'(exit {r.returncode})')
print('    In that tree: a .tbl with a DUPLICATE ROW ID, a .tbl that does not')
print('    parse at all, and a .notes/ sidecar keyed to an artifact id that does')
print('    not exist. corpus_check reports one duplicate id -- and it found it')
print('    inside a FENCED CODE BLOCK in c.md, which is not an artifact id.')
print('    It never invokes the parser on any file. The nine namespaces the audit')
print('    says are "protected by validation" are not validated by this pass.')
shutil.rmtree(d)

print()
print('--- S5d check.yml, the "portable enforcement point", as written ---')
print(open('check.yml').read().strip())
print()
root = os.path.abspath('..'+os.sep+'..')
r = subprocess.run([sys.executable,'conformance/runner.py'], cwd=root, capture_output=True, text=True)
print(f'    step 1  runner.py            -> exit {r.returncode}: '
      f'{[l for l in r.stdout.splitlines() if l.startswith("TOTAL")]}')
print('            it runs the FIXTURES in cases.py. It never opens a single')
print('            .tbl / .md / .canvas in the repository being checked.')
r = subprocess.run([sys.executable,'conformance/mutants.py'], cwd=root, capture_output=True, text=True)
print(f'    step 3  mutants.py           -> exit {r.returncode}: '
      f'{r.stderr.strip().splitlines()[-1] if r.stderr.strip() else r.stdout[:60]}')
print('            the workflow runs it from the repository root; it opens')
print("            'ref_tbl.py' relative to the CWD. The gate never ran.")
subprocess.run(['rm','-rf','__pycache__'])
