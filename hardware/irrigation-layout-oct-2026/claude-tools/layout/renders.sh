#!/bin/bash
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
D=/Users/mitra/Claude/frugal-layout/irrigation-layout-oct-2026/esp32_io_board
O=$D/../claude-tools/layout/out; mkdir -p $O; rm -f $O/renders.done
cd $D
$CLI pcb render --side top --width 2400 --height 2000 --quality high --floor -o $O/render_top.png esp32_io_board.kicad_pcb > $O/renders.log 2>&1
$CLI pcb render --side bottom --width 2400 --height 2000 --quality high --floor -o $O/render_bottom.png esp32_io_board.kicad_pcb >> $O/renders.log 2>&1
$CLI pcb export pdf --mode-single --layers F.Cu,F.Silkscreen,Edge.Cuts --drill-shape-opt 2 -o $O/copper_top.pdf esp32_io_board.kicad_pcb >> $O/renders.log 2>&1
$CLI pcb export pdf --mode-single --layers B.Cu,Edge.Cuts --mirror --drill-shape-opt 2 -o $O/copper_bottom.pdf esp32_io_board.kicad_pcb >> $O/renders.log 2>&1
touch $O/renders.done
