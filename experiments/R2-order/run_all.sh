#!/bin/sh
# All R2 reproductions. Run from experiments/.
set -e
cd "$(dirname "$0")/.."
for f in R2-order/o1_string_dates.py R2-order/o2_ties.py R2-order/o3_computed_order.py \
         R2-order/o4_confluence.py; do
  echo "=== $f"; (cd R2-order && python3 "$(basename $f)"); done
for f in d1_false_positives d2_false_negatives d3_merge d4_rename_fixpoint; do
  echo "=== R2-drift/$f.py"; (cd R2-drift && python3 $f.py); done
for f in new_mutants s2_mutants_are_real s3_live_defects s4_roundtrip_vacuous s5_cases_and_ci; do
  echo "=== R2-suite/$f.py"; (cd R2-suite && python3 $f.py); done
for f in n1_missed n2_paths; do
  echo "=== R2-namespaces/$f.py"; (cd R2-namespaces && python3 $f.py); done
