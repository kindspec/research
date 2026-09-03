#!/usr/bin/env python3
"""R2: NEW mutants run against the UNMODIFIED conformance suite.

Same harness contract as conformance/mutants.py: patch one line of ref_tbl.py,
run runner.py against the patched module, and report a mutant that produces
zero failures as a HOLE. Every mutant below is a plausible implementation bug.
"""
import subprocess, sys, os

MUTANTS = {
 # --- the tiebreak the whole confluence claim rests on -----------------------
 'no-tiebreak-at-all':
   ("try: return (0, float(r[order]), str(r.get(key, '')))",
    "try: return (0, float(r[order]))"),
 'tiebreak-reversed':
   ("try: return (0, float(r[order]), str(r.get(key, '')))",
    "try: return (0, float(r[order]), [-ord(ch) for ch in str(r.get(key, ''))])"),
 'non-numeric-order-sorts-by-id-only':
   ("except (ValueError, TypeError): return (1, 0.0, str(r[order]) + str(r.get(key, '')))",
    "except (ValueError, TypeError): return (1, 0.0, str(r.get(key, '')))"),
 # --- two of the three row-relative operators are never exercised -----------
 'prior-always-blank':
   ("elif fn == 'prior':    r[nm] = prev if prev is not None else ''",
    "elif fn == 'prior':    r[nm] = ''"),
 'delta-first-row-is-the-value':
   ("elif fn == 'delta':    r[nm] = (v - prev) if prev is not None else ''",
    "elif fn == 'delta':    r[nm] = v"),
 'delta-is-negated':
   ("elif fn == 'delta':    r[nm] = (v - prev) if prev is not None else ''",
    "elif fn == 'delta':    r[nm] = (prev - v) if prev is not None else ''"),
 # --- aggregate functions -----------------------------------------------------
 'count-off-by-one':
   ("elif fn == 'count': out[nm] = len(vals)", "elif fn == 'count': out[nm] = len(vals) - 1"),
 'count-ignores-blanks':
   ("elif fn == 'count': out[nm] = len(vals)",
    "elif fn == 'count': out[nm] = len([v for v in vals if v != ''])"),
 'unknown-aggregate-function-silently-becomes-sum':
   ("elif fn == 'sum':   out[nm] = sum(float(v) for v in vals if v != '')",
    "elif fn not in ('count','min','max'): out[nm] = sum(float(v) for v in vals if v != '')"),
 'sum-crashes-on-a-blank-cell':
   ("elif fn == 'sum':   out[nm] = sum(float(v) for v in vals if v != '')",
    "elif fn == 'sum':   out[nm] = sum(float(v) for v in vals)"),
 # --- I3's headline promise: a blank cell is NEVER zero ----------------------
 'blank-cell-in-a-real-column-is-zero':
   ("        v = env.get(node.id, '')",
    "        v = env.get(node.id, '')\n        if node.id in env and v == '': return 0.0"),
 # --- numeric coercion, entirely unspecified and entirely untested -----------
 'float-accepts-thousands-separators':
   ("        return float(v)", "        return float(str(v).replace(',', ''))"),
 'strip-only-ascii-spaces':
   ("def split_row(l): return [c.strip() for c in l.strip().strip('|').split('|')]",
    "def split_row(l): return [c.strip(' ') for c in l.strip().strip('|').split('|')]"),
 # --- dependency order between computed columns is header POSITION -----------
 'computed-columns-evaluated-in-reverse-header-order':
   ("        for nm, expr in formulas.items():\n            if any(re.search",
    "        for nm, expr in reversed(list(formulas.items())):\n            if any(re.search"),
 # --- namespaces the suite tests for `key` but not for `order` ---------------
 'allow-duplicate-order-declaration':
   ("if order is not None: raise Malformed(f'line {n}: duplicate order declaration')", "pass"),
 'order-none-is-ignored':
   ("            order = arg if fn == 'by' else None", "            order = arg"),
 # --- a data row that looks like an alignment row is silently dropped --------
 'is-align-matches-any-dashed-cell':
   ("def is_align(l): return all(re.fullmatch(r':?-{2,}:?', c) for c in split_row(l) if c != '')",
    "def is_align(l): return any(re.fullmatch(r':?-{2,}:?', c) for c in split_row(l) if c != '')"),
 # --- CONTROLS: these MUST be killed, or the harness is broken ---------------
 'CONTROL-drop-every-third-row':
   ("rows.append(dict(zip(cols, v)))", "if len(rows) % 3 != 2: rows.append(dict(zip(cols, v)))"),
 'CONTROL-render-reverses-rows':
   ("    row_raws = [lines[i] for i in tbl_idx[2:]]",
    "    row_raws = [lines[i] for i in tbl_idx[2:]][::-1]"),
}

def main():
    src = open('ref_tbl.py').read()
    survived, killed, stale = [], [], []
    for name, (old, new) in MUTANTS.items():
        if old not in src:
            stale.append(name); print(f'  ??  {name:52} PATTERN NOT FOUND'); continue
        mod = 'mut_' + ''.join(ch if ch.isalnum() else '_' for ch in name)
        open(mod + '.py','w').write(src.replace(old, new, 1))
        r = subprocess.run([sys.executable,'runner.py',mod], capture_output=True, text=True)
        os.remove(mod + '.py')
        n, saw = 0, False
        for line in r.stdout.splitlines():
            if line.startswith('TOTAL FAILURES:'): n = int(line.split(':')[1]); saw = True
        if not saw: n = 1                      # a crash counts as killed
        (killed if n > 0 else survived).append(name)
        print(f'  {"killed  " if n>0 else "SURVIVED"} {name:52} ({n} case(s) failed)')
    subprocess.run(['rm','-rf','__pycache__'])
    print(f'\n{len(killed)} killed, {len(survived)} SURVIVED, {len(stale)} stale')
    for s in survived: print(f'  hole: nothing in the suite detects "{s}"')
    return 0

if __name__ == '__main__': sys.exit(main())
