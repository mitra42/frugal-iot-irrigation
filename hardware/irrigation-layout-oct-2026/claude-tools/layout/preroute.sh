#!/bin/bash
# Mac: placement.json -> board ready for Freerouting (D82). build_pcb -> net classes -> valve_route (fixed
# high-current copper) -> prep_route (GND fan-out, out/board.dsn) -> copper_snap save -> dsn_prep -> dsn_classes.
# Result: out/board_r.dsn, out/before_import.kicad_pcb (the board real_unrouted.sh / post_route.sh import into).
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
L="$(cd "$(dirname "$0")" && pwd)"; cd $L; mkdir -p out
q() { $PY "$@" 2>&1 | grep -v -e assert -e traits -e swig; }
q build_pcb.py && python3 netclasses.py && q valve_route.py && q prep_route.py && q copper_snap.py save \
  && python3 dsn_prep.py && (cd route && python3 dsn_classes.py ../out/board_r.dsn ../out/board_r.dsn) \
  && cp ../../esp32_io_board/esp32_io_board.kicad_pcb out/before_import.kicad_pcb && echo preroute ok
