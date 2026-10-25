#!/bin/bash
# Run on the Mac: DRC with schematic parity + renders of the board.
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
D=/Users/mitra/Claude/frugal-layout/irrigation-layout-oct-2026/esp32_io_board
O=$D/../claude-tools/layout/out; mkdir -p $O
cd $D
$CLI pcb drc --format json --schematic-parity --severity-all -o $O/drc.json esp32_io_board.kicad_pcb > $O/drc.log 2>&1
$CLI pcb export svg --layers F.Cu,B.Cu,F.Silkscreen,F.Fab,F.Courtyard,Edge.Cuts --exclude-drawing-sheet --page-size-mode 2 --mode-single -o $O/board.svg esp32_io_board.kicad_pcb > $O/svg.log 2>&1
$CLI pcb export pdf --mode-single --layers F.Fab,F.Courtyard,F.Silkscreen,Edge.Cuts,F.Cu --include-border-title -o $O/placement.pdf esp32_io_board.kicad_pcb > $O/pdf.log 2>&1
touch $O/drc.done
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb render --side top --width 2400 --height 2000 --quality high --floor -o $O/render_top.png esp32_io_board.kicad_pcb > $O/render.log 2>&1
touch $O/drc.done
