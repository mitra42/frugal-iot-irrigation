#!/bin/bash
# Mac: non-destructive end-to-end check from empty out/ folders: schematic regen + verify, exports, live prices,
# cost estimate, DRC + fabrication files, renders. Does NOT touch the routed PCB. Sentinel: claude-tools/selftest.done
C=/Users/mitra/Claude/frugal-layout/irrigation-layout-oct-2026/claude-tools
rm -f $C/selftest.done
( set -x
  cd $C/schematic && bash run_draw.sh && grep -E "netlist matches|ERC|VERIFY" out/draw.log
  bash run_kicad.sh
  bash jlc_dump.sh; for i in $(seq 1 60); do [ -f out/jlc.done ] && break; sleep 2; done
  python3 cost_estimate.py > ../../COST-ESTIMATE.txt && tail -n +1 ../../COST-ESTIMATE.txt | grep -E "^TOTAL|^Per board" | head -2
  bash ../layout/fab.sh && python3 ../layout/drcsum.py ../layout/out/drc.json | head -3
  python3 ../layout/jlc_files.py | head -3
  bash ../layout/renders.sh && ls ../layout/out
) > /tmp/selftest.log 2>&1
cp /tmp/selftest.log $C/selftest.log; touch $C/selftest.done
