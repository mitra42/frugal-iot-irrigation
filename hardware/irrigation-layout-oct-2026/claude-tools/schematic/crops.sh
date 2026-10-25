#!/bin/bash
PY=/Applications/KiCad/KiCad.app/Contents/Frameworks/Python.framework/Versions/Current/bin/python3
T=/Users/mitra/Claude/frugal-layout/irrigation-layout-oct-2026/claude-tools/schematic
rm -rf $T/out/crops; mkdir -p $T/out/crops
cd $T && $PY block_crops.py ../../esp32_io_board/esp32_io_board.kicad_sch out/crops > out/crops.log 2>&1
echo done
