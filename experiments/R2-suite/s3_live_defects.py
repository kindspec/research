#!/usr/bin/env python3
"""S3: defects the missing cases are hiding in the reference implementation
ITSELF -- not mutants, live behaviour of conformance/ref_tbl.py."""
import ref_tbl as R

def show(label, t, note=''):
    try:
        rows, a = R.evaluate(t); print(f'  {label:44} -> {a}   {note}')
    except R.Malformed as e: print(f'  {label:44} -> REFUSED: {e}')
    except Exception as e:  print(f'  {label:44} -> *** UNHANDLED {type(e).__name__}: {e}')

H = '| id     | qty | unit  | total = qty * unit |\n| ------ | --: | ----: | -----------------: |\n'
D = 'key   := id\ngrand := sum(total)\nlow   := min(total)\nn     := count(id)\n'
print('--- S3a an EMPTY table (header + alignment, no rows) ---')
show('min() over zero rows', H + '\n' + D)
print('    I3 says errors are loud and local. This is an uncaught ValueError from')
print('    inside the aggregate loop: the whole file fails to evaluate.')

print()
print('--- S3b a single-row table with delta()/prior() ---')
S = ('| id     | day | v   | d = delta(v) |\n| ------ | --: | --: | -----------: |\n'
     '| r_0001 |   1 | 5.0 |              |\n\nkey := id\norder := by(day)\nmx := max(d)\n')
show('max(delta) over one row', S)
print("    the only row's delta is '', filtered out by `if v != ''`, so max() sees")
print('    an empty sequence. A one-row ledger is not exotic.')

print()
print('--- S3c a table with ONLY computed columns ---')
C = ('| a = 1 + 1 | b = a * 3 |\n| --------: | --------: |\n| | |\n\ng := sum(b)\n')
show('two computed columns, one chained', C)

print()
print('--- S3d numeric coercion: what float() does and does not accept ---')
for v in ('1,500.00', '(500)', 'nan', 'inf', '1_000', '１２', '12.5e2', '-0.0'):
    t = H + f'| r_0001 |   1 | {v} |                    |\n\n' + D
    show(f'unit = {v!r}', t)
print('    Three outcomes for eight inputs and no rule distinguishing them:')
print('    a loud crash, a silent accept, and a silent nan/inf poisoning an')
print('    aggregate. None of the eight is a conformance case.')

print()
print('--- S3e `key` is a RESERVED name inside the aggregate namespace ---')
K = H + '| r_0001 |  10 | 12.00 |                    |\n| r_0002 |  10 | 12.00 |                    |\n\n' \
    + 'key := sum(qty)\ngrand := sum(total)\n'
show('an aggregate a user named `key`', K)
print("    `key := sum(qty)` matches the function-form regex, name=='key', so it")
print("    is swallowed as a KEY DECLARATION with key column 'qty' -- and then")
print("    enforces uniqueness on qty, refusing a legal table. The aggregate")
print("    named `key` never appears in the output and nothing says so.")
