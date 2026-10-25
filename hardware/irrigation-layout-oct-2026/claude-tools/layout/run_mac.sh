#!/bin/bash
# Run a layout script on the Mac with KiCad's python, detached; sentinel layout/out/<script>.done, log .log
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
L=/Users/mitra/Claude/frugal-layout/irrigation-layout-oct-2026/claude-tools/layout
mkdir -p $L/out; n=$(basename "$1" .py); rm -f $L/out/$n.done
( cd $L && $PY "$@" > out/$n.log 2>&1; echo "exit $?" >> out/$n.log; touch out/$n.done ) > /dev/null 2>&1 &
echo started $n
