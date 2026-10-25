#!/bin/bash
# Mac: schematic -> netlist -> measure -> place -> build PCB -> netclasses -> DRC + renders. Sentinel out/pipeline.done
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
L=/Users/mitra/Claude/frugal-layout/irrigation-layout-oct-2026/claude-tools/layout; T=$L/../schematic
mkdir -p $L/out; rm -f $L/out/pipeline.done; LOG=$L/out/pipeline.log
(
  set -x
  if [ "$1" = "--sch" ]; then
    cd $T && $PY buildlib.py && bash run_draw.sh && grep -E "VERIFY|ERC" out/draw.log && bash run_kicad.sh; shift
  fi
  cd $L && $PY fpmeasure.py 2>&1 | grep -v assert
  /usr/bin/python3 place.py "${1:-80}"
  $PY build_pcb.py 2>&1 | grep -v -e assert -e traits
  /usr/bin/python3 netclasses.py
  bash drc.sh
) > $LOG 2>&1
touch $L/out/pipeline.done
