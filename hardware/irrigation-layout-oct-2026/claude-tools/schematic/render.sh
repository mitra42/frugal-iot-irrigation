#!/bin/bash
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
D=/Users/mitra/Claude/frugal-layout/irrigation-layout-oct-2026/esp32_io_board
mkdir -p $D/../claude-tools/schematic/out; cd $D && $CLI sch export pdf -o ../claude-tools/schematic/out/new.pdf esp32_io_board.kicad_sch > /dev/null 2>&1
echo rendered
