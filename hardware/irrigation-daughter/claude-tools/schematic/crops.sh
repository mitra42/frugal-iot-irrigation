#!/bin/bash
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
T="$(cd "$(dirname "$0")" && pwd)"
rm -rf $T/out/crops; mkdir -p $T/out/crops
cd $T && $PY block_crops.py ../../daughter/irrigation_daughter.kicad_sch out/crops > out/crops.log 2>&1
echo done
