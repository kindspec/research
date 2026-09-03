#!/usr/bin/env python3
"""N1: namespaces the mechanical audit did not enumerate.

Same method as experiments/X3-namespaces/audit.py -- construct a collision two
ways, record git and the parser -- reusing that file's own parsers so the
comparison is exact.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from audit import git_collide, parse_tbl, parse_canvas, parse_md, TBL

# a canvas with room between the bindings, so an adjacency conflict cannot be
# mistaken for a namespace collision
CANVAS = '''node api   "API Gateway"
node auth  "Auth Service"
node db    "Postgres"
node queue "Rabbit"
node cache "Redis"
node work  "Worker"
edge api -> auth
edge auth -> db
edge api -> queue
edge queue -> work
edge work -> cache
edge work -> db

@layout
'''

CASES = []

# 1. .tbl -- the DECLARATION KEYWORD namespace overlaps the AGGREGATE namespace
NOKEY = TBL.replace('key   := id\n', '')
KEYAGG = NOKEY.replace('grand := sum(total)', 'grand := sum(total)\nkey := sum(qty)')
CASES.append(('.tbl', 'declaration keyword vs aggregate name',
              NOKEY, KEYAGG, NOKEY, parse_tbl,
              "`key := sum(qty)` is swallowed as a KEY DECLARATION (name=='key' "
              "wins before the aggregate branch). The aggregate silently vanishes."))

# 2. .tbl -- the AGGREGATE FUNCTION namespace: an unknown function is dropped
CASES.append(('.tbl', 'aggregate function name',
              TBL, TBL.replace('grand := sum(total)', 'grand := mean(total)'), TBL, parse_tbl,
              "`mean` is not sum/count/min/max, so `grand` is never written to the "
              "output dict. `{{ t.tbl#grand }}` resolves to nothing, silently."))

# 3. .canvas -- EDGE IDENTITY. An edge has no name; (a,b) is its identity, and
#    nothing enforces uniqueness on it.
CASES.append(('.canvas', 'edge identity (a -> b)',
              CANVAS,
              CANVAS.replace('edge api -> auth', 'edge api -> auth "authenticates"'),
              CANVAS.replace('edge work -> db', 'edge work -> db\nedge api -> auth "logs in"'),
              parse_canvas,
              "two edges api->auth with two different labels. One relationship, "
              "two bindings, no name to collide on."))

# 4. .canvas -- the ANCHOR REFERENCES inside an @layout override
CASES.append(('.canvas', '@layout anchor reference',
              CANVAS + 'db { below: auth }\n',
              CANVAS + 'db { below: auth }\n',
              CANVAS.replace('auth', 'sso ') + 'db { below: auth }\n',
              parse_canvas,
              "parse_canvas checks that the layout KEY is a known node and never "
              "checks the anchor on the right-hand side."))

# 5. .canvas -- PROPERTY NAMES inside one override
CASES.append(('.canvas', '@layout property name',
              CANVAS + 'db { below: auth }\n',
              CANVAS + 'db { below: auth, below: api }\n',
              CANVAS + 'db { below: auth }\n',
              parse_canvas,
              "two values for `below` on ONE line. Co-location does not help: git "
              "sees one line, and the parser never looks inside the braces."))

print(f"{'format':9} {'namespace':38} {'git':10} {'parser on merged result':34} verdict")
print('-'*118)
bad = 0
for fmt, ns, base, ours, theirs, parser, note in CASES:
    fn = {'.tbl':'a.tbl','.md':'a.md','.canvas':'a.canvas'}[fmt]
    status, merged = git_collide(fn, base, ours, theirs)
    perr = parser(merged)
    if status == 'CONFLICT': v = 'SAFE (co-located)'
    elif perr:               v = 'SAFE (validated)'
    else:                    v = 'UNPROTECTED'; bad += 1
    print(f'{fmt:9} {ns:38} {status:10} {(perr or "(accepted)")[:32]:34} {v}')
    print(f'{"":9} {"":38} {note}')
print('-'*118)
print(f'{bad} of {len(CASES)} namespaces protected by NEITHER co-location nor validation.')
print('None of the five appears in X3-namespace-audit.md. Its count is 11 of 11 safe;')
print(f'these are {len(CASES)} more namespaces in the SAME three formats.')
