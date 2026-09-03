# D10 agent-edit experiments

Measures how locatable an edit target is, per document representation.
See `design-findings/D10-interfaces.md` §3.4.

    python3 gen.py && python3 measure.py && python3 anchor.py   # measurements 1-3
    python3 gen2.py                                             # R1 / R6 fixtures
    python3 survival.py                                         # measurement 5

Metrics:
- line uniqueness: fraction of lines usable as a search/replace anchor at all
- minimum unique anchor: smallest contiguous line window that occurs once
- anchor survival: does a captured anchor still exist after an UNRELATED edit
  (the metric that actually matters; the other two can mislead)
