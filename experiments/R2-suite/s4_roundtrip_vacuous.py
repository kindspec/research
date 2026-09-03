#!/usr/bin/env python3
"""S4: is `render(structure(b)) == b` non-tautological now?

X4 claims the tautology is gone because `render` reconstructs from the parsed
structure. But `structure()` stores the RAW LINES (`header_raw`, `align_raw`,
`row_raws`, `tail`, `prefix`) and `render()` concatenates them. The parsed
entity map (`cols`, `formulas`, `rows`, `decls`, `order`, `key`) is carried
along and NEVER USED by render. So round-trip still cannot see a parse bug.
"""
import subprocess, sys, os
import ref_tbl as R, cases as C

print('--- S4a a `structure`/`render` pair that understands NOTHING ---')
src = open('ref_tbl.py').read()
blind = src.replace(
  "def render(st):", "def render(st):\n    return st['raw']\ndef _dead(st):") \
   .replace("    cols, formulas, rows, decls, order, key = parse(text)\n"
            "    tbl_idx = [i for i, l in enumerate(lines) if l.strip().startswith('|')]",
            "    return {'raw': text}\n    tbl_idx = []")
open('blind_impl.py','w').write(blind)
import importlib; importlib.invalidate_caches()
import blind_impl as B
ok = sum(B.render(B.structure(t)) == t for _, t in C.ROUNDTRIP)
print(f'    structure(text) -> {{"raw": text}};  render(st) -> st["raw"]')
print(f'    roundtrip cases passed: {ok}/{len(C.ROUNDTRIP)}')
print('    It does not parse, does not find a table, does not know what a column')
print('    is. All five round-trip cases are green. The law is still satisfiable')
print('    by a parser that understands nothing -- exactly R1 section 3.')

print()
print('--- S4b and conversely: garble the ENTITY MAP, round-trip stays green ---')
garbled = src.replace("        v = split_row(l)\n        if len(v) != len(cols):",
                      "        v = split_row(l); v[2:] = v[2:][::-1]\n        if len(v) != len(cols):")
assert garbled != src
open('garbled_impl.py','w').write(garbled)
importlib.invalidate_caches(); import garbled_impl as G
for cid, t in C.ROUNDTRIP:
    try: r = G.render(G.structure(t)) == t
    except Exception as e: r = f'{type(e).__name__}'
    print(f'    roundtrip {cid:34} exact={r}')
print('    every cell after the first two is bound to the WRONG column name:')
print('      reference eval:', R.evaluate(C.T)[1], '  garbled eval:', G.evaluate(C.T)[1])
print('    Round-trip is byte-exact regardless: render never consults `cols`,')
print('    `formulas` or `rows`. Five green round-trip cases over a parser whose')
print('    entity map is wrong for every row.')

print()
print('--- S4c what the round-trip cases DO catch: only render() itself ---')
print('    Both mutants killed by round-trip in X4 -- render-drops-tail and')
print('    render-drops-alignment -- mutate render, not parse. The law tests')
print('    the renderer against the raw-line store, not the parser.')
for f in ('blind_impl.py','garbled_impl.py'): os.path.exists(f) and os.remove(f)
subprocess.run(['rm','-rf','__pycache__'])

print()
print('--- S4d a real file the round-trip law LOSES (live defect) ---')
INTERLEAVED = ('| id | qty |\n| -- | --: |\n| r_1 |  1 |\n'
               '\n| r_2 |  2 |\n\nkey := id\ng := sum(qty)\n')
try:
    out = R.render(R.structure(INTERLEAVED))
    print(f'    {len(INTERLEAVED)}B in, {len(out)}B out, exact={out == INTERLEAVED}')
    print('    lost:', repr(INTERLEAVED.replace(out, '')) if out in INTERLEAVED else 'reordered')
except Exception as e: print('   ', type(e).__name__, e)
print('    A blank line inside the table is dropped on render: row_raws takes only')
print('    the lines AT table indices and tail starts after the LAST one.')
