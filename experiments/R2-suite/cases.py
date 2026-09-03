"""Conformance cases, declared as DATA so an independent implementation can
consume them without importing our code.

Categories:
  parse       input -> accepted, or refused with a reason
  roundtrip   render(parse(x)) == x
  eval        input -> expected computed values
  merge       base/ours/theirs -> expected git outcome AND expected values
  confluence  several merge orders -> one outcome
  drift       v1/v2 -> expected meaning-drift findings
"""

T = """| id     | item     | qty | unit  | total = qty * unit |
| ------ | -------- | --: | ----: | -----------------: |
| r_0001 | widget   |  10 | 12.00 |                    |
| r_0002 | gadget   |  20 |  6.00 |                    |
| r_0003 | sprocket |   8 | 15.00 |                    |
| r_0004 | flange   |   5 | 24.00 |                    |

key   := id
grand := sum(total)
"""

LEDGER = """| id     | date | amount | balance = cumulative(amount) |
| ------ | ---: | -----: | ---------------------------: |
| r_0001 |    1 | 100.00 |                              |
| r_0002 |    3 | -30.00 |                              |
| r_0003 |    5 |  50.00 |                              |

key   := id
order := by(date)
final := max(balance)
"""

def ins(t, after, line):
    L = t.splitlines(); i = next(i for i, l in enumerate(L) if after in l)
    L.insert(i + 1, line); return '\n'.join(L) + '\n'

def addcol(t, name, tag):
    L = []
    for i, l in enumerate(t.splitlines()):
        if not l.startswith('|'): L.append(l)
        elif i == 0: L.append(l + f' {name} |')
        elif i == 1: L.append(l + ' --- |')
        else: L.append(l + f' {tag}{i} |')
    return '\n'.join(L) + '\n'

ROW = '| {id} | {item:8} | {qty:3} | {unit} |                    |'

PARSE = [
 # (id, input, expected refusal substring or None for "must accept")
 ('parse/valid',            T, None),
 ('parse/ledger',           LEDGER, None),
 ('parse/conflict-markers', T.replace('| r_0002 | gadget   |  20 |  6.00 |                    |',
     '<<<<<<< HEAD\n| r_0002 | gadget   |  20 |  6.00 |                    |\n=======\n'
     '| r_0002 | gadget   |  40 |  6.00 |                    |\n>>>>>>> b'), 'conflict marker'),
 ('parse/dup-column',       T.replace('| unit  |', '| qty   |'), 'duplicate column'),
 ('parse/dup-aggregate',    T + 'grand := sum(qty)\n', 'duplicate aggregate'),
 ('parse/dup-key-decl',     T + 'key := item\n', 'duplicate key declaration'),
 ('parse/dup-row-id',       ins(T, 'r_0001', ROW.format(id='r_0001', item='dup', qty=1, unit='1.00')),
                            'duplicate key'),
 ('parse/field-count',      ins(T, 'r_0001', '| r_0009 | short | 1 |'), 'fields'),
 ('parse/align-mismatch',   T.replace('| ------ | -------- | --: | ----: | -----------------: |',
                                      '| ------ | -------- | --: | ----: | ---: | ---: |'), 'alignment row'),
 ('parse/rowrel-no-order',  LEDGER.replace('order := by(date)\n', ''), 'row order'),
 ('parse/order-unknown-col', LEDGER.replace('order := by(date)', 'order := by(nope)'), 'no column'),
 ('parse/bad-declaration',  T + 'oops := \n', 'malformed declaration'),
 ('parse/nfd-name-collision',
    T.replace('key   := id', 'café := sum(qty)\ncafé := sum(total)\nkey   := id'),
    'duplicate aggregate'),
 ('parse/empty',            '', 'no table'),
]

ROUNDTRIP = [
 ('roundtrip/basic',   T),
 ('roundtrip/ledger',  LEDGER),
 ('roundtrip/no-trailing-newline', T.rstrip('\n')),
 ('roundtrip/crlf',    T.replace('\n', '\r\n')),
 ('roundtrip/wide',    addcol(addcol(T, 'a', 'x'), 'b', 'y')),
]

# file order deliberately DIFFERENT from declared order, and a value that
# depends on the ordering: the running minimum dips only if order is honoured.
SCRAMBLED = """| id     | date | amount | balance = cumulative(amount) |
| ------ | ---: | -----: | ---------------------------: |
| r_0003 |    5 | 200.00 |                              |
| r_0001 |    1 |  10.00 |                              |
| r_0002 |    3 | -60.00 |                              |

key   := id
order := by(date)
low   := min(balance)
high  := max(balance)
"""

EVAL = [
 ('eval/order-sensitive-min',  SCRAMBLED, {'low': -50.0, 'high': 150.0}),
 ('eval/basic',        T,      {'grand': 480.0}),
 ('eval/cumulative',   LEDGER, {'final': 120.0}),
 ('eval/broken-ref',   T.replace('| unit  |', '| price |'), {'grand': '#REF!(unit)'}),
 ('eval/missing-agg-col', T.replace('grand := sum(total)', 'grand := sum(nope)'),
                       {'grand': '#REF!(nope)'}),
 ('eval/order-independent', LEDGER, {'final': 120.0}),
]

MERGE = [
 # (id, base, ours, theirs, expected 'clean'|'conflict', expected values or None)
 ('merge/distant-row-inserts', T,
    ins(T, 'r_0001', ROW.format(id='r_0005', item='cog', qty=4, unit='25.00')),
    ins(T, 'r_0004', ROW.format(id='r_0006', item='bolt', qty=10, unit=' 8.00')),
    'clean', {'grand': 660.0}),
 ('merge/same-cell-edit', T,
    T.replace('|  20 |  6.00 |', '|  99 |  6.00 |'),
    T.replace('|  20 |  6.00 |', '|  21 |  6.00 |'),
    'conflict', None),
 ('merge/disjoint-cell-edits', T,
    T.replace('|  10 | 12.00 |', '|  11 | 12.00 |'),
    T.replace('|   5 | 24.00 |', '|   6 | 24.00 |'),
    'clean', {'grand': 516.0}),
 ('merge/column-name-collision', T, addcol(T, 'code', 'A'), addcol(T, 'code', 'B'),
    'conflict', None),
 ('merge/duplicate-row-id', T,
    ins(T, 'r_0001', ROW.format(id='r_0009', item='alpha', qty=1, unit=' 1.00')),
    ins(T, 'r_0004', ROW.format(id='r_0009', item='beta', qty=2, unit=' 1.00')),
    'clean', 'MUST_REFUSE'),
 ('merge/scattered-aggregate', T,
    T.replace('key   := id', 'subtotal := sum(qty)\nkey   := id'),
    T + 'subtotal := sum(total)\n',
    'clean', 'MUST_REFUSE'),
 ('merge/ledger-inserts', LEDGER,
    ins(LEDGER, 'r_0001', '| r_0005 |    2 |  11.00 |                              |'),
    ins(LEDGER, 'r_0003', '| r_0006 |    6 |   7.00 |                              |'),
    'clean', {'final': 138.0}),
 ('merge/backdated-appended-last', LEDGER,
    ins(LEDGER, 'r_0003', '| r_0007 |    0 | 500.00 |                              |'),
    ins(LEDGER, 'r_0001', '| r_0008 |    4 |   3.00 |                              |'),
    'clean', {'final': 623.0}),
]

CONFLUENCE = [
 ('confluence/ledger-three-way', LEDGER, [
    ins(LEDGER, 'r_0001', '| r_0005 |    2 |  11.00 |                              |'),
    ins(LEDGER, 'r_0003', '| r_0006 |    6 |   7.00 |                              |'),
    ins(LEDGER, 'r_0002', '| r_0009 |    4 |   1.00 |                              |'),
 ]),
]

DRIFT = [
 ('drift/rename-swap',
   T.replace('| total = qty * unit |', '| total = qty * unit | net = total * 0.8 |')
    .replace('-----------------: |', '-----------------: | ----------------: |')
    .replace('   |                    |', '   |                    |                   |'),
   None, True),   # filled in by the runner: v2 is derived below
]
