#!/usr/bin/env python3
"""A suspending scheduler + constructive-trace rebuilder, ~50 lines, then four
adversarial tests aimed at BREAKING the 'one engine unifies everything' claim.
"""
import hashlib, time, random, sys

class Cycle(Exception): pass

class Engine:
    def __init__(self, rules):
        self.rules = rules          # key -> callable(fetch) -> value
        self.cache = {}             # trace-key -> value  (constructive trace)
        self.stack = []             # suspending scheduler's demand stack
        self.stats = {'hit':0,'miss':0,'run':0}
    def build(self, key):
        if key in self.stack:
            raise Cycle(" -> ".join(self.stack + [key]))
        self.stack.append(key)
        try:
            deps = {}
            def fetch(k):            # dependencies DISCOVERED here, dynamically
                v = self.build(k); deps[k] = v; return v
            probe = self.rules[key](fetch)          # run once to learn deps
            tk = hashlib.sha256(repr((key, sorted(deps.items()))).encode()).hexdigest()[:12]
            if tk in self.cache:
                self.stats['hit'] += 1; return self.cache[tk]
            self.stats['miss'] += 1; self.stats['run'] += 1
            self.cache[tk] = probe
            return probe
        finally:
            self.stack.pop()

# ---------- TEST 1: a CYCLE ----------
print("=== TEST 1  cycle (spreadsheets allow iterative calc; build systems do not) ===")
e = Engine({'a': lambda f: f('b') + 1, 'b': lambda f: f('a') + 1})
try: e.build('a')
except Cycle as c: print("  suspending scheduler DETECTS it:", c)
print("  Excel, by contrast, has File>Options>Formulas>Enable iterative calculation.")

# ---------- TEST 2: a DYNAMIC DEPENDENCY (the INDIRECT case) ----------
print("\n=== TEST 2  dynamic dependency: which input to read is itself computed ===")
data = {'which': 'q1', 'q1': 100, 'q2': 250}
rules = {k: (lambda k: (lambda f: data[k]))(k) for k in data}
rules['total'] = lambda f: f(f('which'))     # <-- key computed at runtime
e = Engine(rules); print("  total =", e.build('total'), " stats", e.stats)
data['which'] = 'q2'
e2 = Engine(rules); print("  after which:=q2 -> total =", e2.build('total'))
print("  VERDICT: handled. A topological scheduler cannot do this; a suspending one can.")

# ---------- TEST 3: NON-DETERMINISM ----------
print("\n=== TEST 3  non-determinism (NOW(), RAND(), a network fetch) ===")
rules = {'now': lambda f: time.time(), 'stamp': lambda f: f('now')}
e = Engine(rules)
a = e.build('stamp'); time.sleep(0.05)
b = e.build('stamp')
print(f"  first={a!r}\n  second={b!r}\n  identical={a==b}  cache={e.stats}")
print("  VERDICT: BROKEN. `now` has NO inputs, so its trace key is constant and the")
print("  first value is cached forever. Constructive traces assume determinism.")

# ---------- TEST 4: COST OF HASHING ----------
print("\n=== TEST 4  cost of hashing inputs ===")
for mb in (1, 64, 256):
    blob = random.randbytes(mb*1024*1024)
    t0=time.perf_counter(); hashlib.sha256(blob).hexdigest(); dt=time.perf_counter()-t0
    print(f"  sha256 of {mb:4d} MB : {dt*1000:8.1f} ms  ({mb/dt:6.0f} MB/s)")
