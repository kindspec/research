#!/bin/sh
# Runs every red-team reproduction. From experiments/.
set -e
for s in R1-table/t1_namespace.py R1-table/t2_rowid.py R1-table/t3_shift.py \
         R1-table/t4_numbers.py R1-table/t5_formulas.py \
         R1-prev/p1_running.py R1-prev/p3_prev_is_a_coordinate.py R1-prev/p4_confluence.py \
         R1-prev/p2_reorder_lost.py \
         R1-derivation/d1_meaning_drift.py R1-derivation/d2_cache.py \
         R1-canvas/c1_canvas.py R1-canvas/c2_graphviz.py \
         R1-doc/m1_namespaces.py R1-doc/m2_blocks.py \
         R1-suite/s1_suite_holes.py; do
  echo; echo "######## $s"
  ( cd "$(dirname "$s")" && python3 "$(basename "$s")" ) || echo "(exited non-zero)"
done
