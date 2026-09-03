#!/usr/bin/env python3
"""Which of the spec's eleven refusals work on PLAIN CSV, with no migration?

This is the question that decides whether a validator can ship before a format.
Input: an ordinary .csv plus an optional tiny sidecar declaring key/order.
"""
import csv, sys, io, unicodedata, os, json

CONFLICT = ('<<<<<<<', '=======', '>>>>>>>', '|||||||')

def check(path, sidecar=None):
    errs = []
    raw = open(path, 'rb').read()
    try: text = raw.decode('utf-8')
    except UnicodeDecodeError as e: return [f'not valid UTF-8: {e}']
    if raw[:3] == b'\xef\xbb\xbf': errs.append('BOM present')
    if unicodedata.normalize('NFC', text) != text:
        errs.append('identifiers are not NFC-normalised')
    for n, l in enumerate(text.splitlines(), 1):                      # R1
        if l.startswith(CONFLICT):
            errs.append(f'line {n}: unresolved conflict marker'); break
    rows = list(csv.reader(io.StringIO(text)))
    if not rows: return errs + ['no table']                            # R11
    hdr = rows[0]
    seen = set()
    for c in hdr:                                                      # R2
        if c in seen: errs.append(f'duplicate column name {c!r}')
        seen.add(c)
    for n, r in enumerate(rows[1:], 2):                                # R6
        if len(r) != len(hdr):
            errs.append(f'line {n}: {len(r)} fields, header has {len(hdr)}')
    decl = json.load(open(sidecar)) if sidecar and os.path.exists(sidecar) else {}
    key, order = decl.get('key'), decl.get('order')
    if key:
        if key not in hdr: errs.append(f'key column {key!r} is not in the header')
        else:                                                          # R5
            i = hdr.index(key); ids = [r[i] for r in rows[1:] if len(r) > i]
            dup = {x for x in ids if ids.count(x) > 1}
            for d in sorted(dup): errs.append(f'duplicate key {key}={d!r}')
    if order and order not in hdr:                                     # R9
        errs.append(f'order column {order!r} is not in the header')
    return errs

if __name__ == '__main__':
    e = check(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else None)
    for x in e: print('  REFUSED:', x)
    print(f'  {len(e)} problem(s)')
    sys.exit(1 if e else 0)
