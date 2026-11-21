#!/bin/bash
# Mac: route what a patch to an already-routed board left open (patch_power.py, D87-D89), keeping every existing
# track and via fixed. Two halves, because Freerouting runs in between:
#   route_patch.sh prep    -> out/board_r.dsn; then: route/loop_local.sh out/board_r.dsn out/p 4 25
#   route_patch.sh import out/p_N.ses -> board = zone-less copy + routing + snapshot restored + pours, then DRC
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
L="$(cd "$(dirname "$0")" && pwd)"; cd $L; mkdir -p out; B=../../esp32_io_board/esp32_io_board.kicad_pcb
q() { $PY "$@" 2>&1 | grep -v -e assert -e traits -e swig; }
if [ "$1" = prep ]; then
  cp $B out/before_route_patch.kicad_pcb
  q copper_snap.py save out/patch_snap.json && q nozone_dsn.py && python3 dsn_prep.py \
    && (cd route && python3 dsn_classes.py ../out/board_r.dsn ../out/board_r.dsn) && echo prep ok
elif [ "$1" = import ]; then
  cp out/nozone.kicad_pcb $B && cp "$2" out/routed.ses \
    && q import_ses.py && q copper_snap.py restore out/patch_snap.json && q pour.py && bash drc.sh \
    && python3 drcsum.py out/drc.json
fi
