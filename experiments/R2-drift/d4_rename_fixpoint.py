#!/usr/bin/env python3
"""D4: the rename fixpoint. NEGATIVE RESULT, mostly.

The loop is bounded by len(od)+1, so it cannot hang. It IS a greedy first-match
over an unordered dict, so an ambiguous rename converges arbitrarily (D4a) --
but I could not turn that into a numeric error, because two columns with
identical definitions denote the same value. D4b and D4c are attempts to make
the rename map ABSORB a real rebinding; both are caught."""
import drift

A = """| id     | qty | unit | x = qty * unit | y = qty * unit | z = x + y |
| ------ | --: | ---: | -------------: | -------------: | --------: |
| r_0001 |  10 |    2 |                |                |           |

key := id
g := sum(z)
"""
# rename x->p and y->q. Both had the identical definition, so the matcher
# cannot know which went where -- and it silently picks one.
B = A.replace('x = qty * unit', 'p = qty * unit').replace('y = qty * unit', 'q = qty * unit') \
     .replace('z = x + y', 'z = p + q')
f, notes = drift.check(A, B)
print('--- D4a two columns with the SAME definition, both renamed')
for n in notes: print('   ', n)
print('    findings:', len(f), '(a coin-flip rename map; no ambiguity is reported)')

print()
print('--- D4b ATTEMPT: make the rename map absorb a definition swap  (HELD)')
C = """| id     | a | b | m = a + 1 | n = b + 1 | t = m * n |
| ------ | -: | -: | --------: | --------: | --------: |
| r_0001 |  3 |  7 |           |           |           |

key := id
g := sum(t)
"""
# `m` keeps its name but is rebound to b+1; `n` keeps its name, rebound to a+1.
D = C.replace('m = a + 1 | n = b + 1', 'm = b + 1 | n = a + 1')
f, notes = drift.check(C, D)
print('    C: m = a + 1, n = b + 1     D: m = b + 1, n = a + 1   (a swap of DEFINITIONS)')
for n in notes: print('   ', n)
print('    findings:', len(f))
for x in f: print('       ', x.splitlines()[0])
print('    The matcher records renames m->n and n->m, then step 2 asks whether')
print('    norm(before, rename) == after.  norm("a + 1", {m:n, n:m}) == "a + 1"')
print('    -- the rename map does not touch a or b -- so `m` IS reported. Good.')
print()
print('--- D4c ATTEMPT: literal name swap under computed references  (HELD)')
E = """| id     | p | q | m = p + 1 | n = q + 1 | t = m * n |
| ------ | -: | -: | --------: | --------: | --------: |
| r_0001 |  3 |  7 |           |           |           |

key := id
g := sum(t)
"""
# rename p->q and q->p (a literal swap) AND leave m,n textually identical.
F = E.replace('| p | q |', '| q | p |')
f, notes = drift.check(E, F)
print('    swap the two LITERAL names p,q; m = p + 1 and n = q + 1 unchanged.')
print('    g:', __import__('otbl').evaluate(E)[1], '->', __import__('otbl').evaluate(F)[1])
for n in notes: print('   ', n)
print('    findings:', len(f))
for x in f: print('       ', x.splitlines()[0])
