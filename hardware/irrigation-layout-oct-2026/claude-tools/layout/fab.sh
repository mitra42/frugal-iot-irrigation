#!/bin/bash
# Mac: DRC + raw fabrication outputs into out/fab/ (then jlc_files.py packs them into ../../fabrication/). Sentinel out/fab.done
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
D=/Users/mitra/Claude/frugal-layout/irrigation-layout-oct-2026/esp32_io_board
F=$D/../claude-tools/layout/out/fab; O=$D/../claude-tools/layout/out
mkdir -p $O; rm -f $O/fab.done; mkdir -p $F/gerbers
cd $D
(
$CLI pcb drc --format json --schematic-parity --severity-all -o $O/drc.json esp32_io_board.kicad_pcb
rm -f $F/gerbers/*
$CLI pcb export gerbers --layers F.Cu,B.Cu,F.Paste,B.Paste,F.Silkscreen,B.Silkscreen,F.Mask,B.Mask,Edge.Cuts \
     --subtract-soldermask --no-protel-ext -o $F/gerbers/ esp32_io_board.kicad_pcb
$CLI pcb export drill --format excellon --excellon-units mm --excellon-separate-th --generate-map --map-format gerberx2 \
     -o $F/gerbers/ esp32_io_board.kicad_pcb
$CLI pcb export pos --format csv --units mm --side both --exclude-dnp -o $F/pos_kicad.csv esp32_io_board.kicad_pcb
$CLI sch export bom --fields 'Reference,Value,Footprint,LCSC,${DNP}' --labels 'Refs,Value,Footprint,LCSC,DNP' \
     --group-by 'Value,Footprint,LCSC,${DNP}' -o $F/bom_kicad.csv esp32_io_board.kicad_sch
$CLI pcb render --side top --width 2400 --height 2000 --quality high --floor -o $O/render_top.png esp32_io_board.kicad_pcb
) > $O/fab.log 2>&1
touch $O/fab.done
