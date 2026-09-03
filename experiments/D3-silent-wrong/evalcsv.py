#!/usr/bin/env python3
"""Minimal A1-style formula evaluator for CSV, enough to score merge correctness."""
import csv, re, sys
def colnum(s):
    n=0
    for ch in s: n=n*26+(ord(ch.upper())-64)
    return n-1
def load(p):
    return list(csv.reader(open(p)))
def cell(g,ref):
    m=re.fullmatch(r'([A-Za-z]+)(\d+)',ref); c=colnum(m.group(1)); r=int(m.group(2))-1
    if r>=len(g) or c>=len(g[r]): return ''
    return g[r][c]
def ev(g,v,depth=0):
    v=v.strip()
    if depth>20: return float('nan')
    if not v.startswith('='):
        try: return float(v)
        except: return 0.0
    e=v[1:]
    def rng(m):
        a,b=m.group(1),m.group(2)
        m1=re.fullmatch(r'([A-Za-z]+)(\d+)',a); m2=re.fullmatch(r'([A-Za-z]+)(\d+)',b)
        c1,r1=colnum(m1.group(1)),int(m1.group(2)); c2,r2=colnum(m2.group(1)),int(m2.group(2))
        t=0.0
        for r in range(r1,r2+1):
            for c in range(c1,c2+1):
                t+=ev(g,cell(g,chr(65+c)+str(r)),depth+1)
        return repr(t)
    e=re.sub(r'SUM\(([A-Z]+\d+):([A-Z]+\d+)\)',rng,e)
    e=re.sub(r'\b([A-Z]+\d+)\b',lambda m:repr(ev(g,cell(g,m.group(1)),depth+1)),e)
    try: return float(eval(e,{"__builtins__":{}},{}))
    except Exception: return float('nan')
if __name__=='__main__':
    g=load(sys.argv[1]); tgt=sys.argv[2]
    print(ev(g,cell(g,tgt)))
