#!/bin/bash
# Mac: everything after Freerouting, in the order that produced the V0.1 board (replaces the fix_cycle* scripts).
#   import SES -> GND pours -> grid stitching -> island vias (+ drop router GND traces on B.Cu)
#   -> dangling-stub removal + GND pad rescue -> join detached pour groups -> refdes placement -> DRC.
# Each step is its own process (pcbnew SWIG landmines); a backup is kept before each mutating step.
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
L=/Users/mitra/Claude/frugal-layout/irrigation-layout-oct-2026/claude-tools/layout
B=$L/../../esp32_io_board/esp32_io_board.kicad_pcb
mkdir -p $L/out; rm -f $L/out/post_route.done
step() { cp $B $L/out/before_$1.kicad_pcb; $PY $2 2>&1 | grep -v -e assert -e traits -e swig; }
( cd $L
  step import import_ses.py
  step pour pour.py
  step stitch post_fix.py;  $PY fill.py >/dev/null 2>&1; bash drc.sh
  step islands fix2.py;     $PY fill.py >/dev/null 2>&1; bash drc.sh
  step rescue rescue.py;    $PY fill.py >/dev/null 2>&1
  step join "islands2.py --fix"; $PY fill.py >/dev/null 2>&1
  step silk silk.py
  bash drc.sh; python3 drcsum.py out/drc.json
) > $L/out/post_route.log 2>&1
touch $L/out/post_route.done
