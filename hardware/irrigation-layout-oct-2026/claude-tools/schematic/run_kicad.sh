#!/bin/bash
# Run on the Mac. ERC + netlist + PDF + SVG for the schematic.
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
D=/Users/mitra/Claude/frugal-layout/irrigation-layout-oct-2026/esp32_io_board
O=$D/../claude-tools/schematic/out
mkdir -p $O
cd $D
$CLI sch erc --format json --severity-all -o $O/erc.json esp32_io_board.kicad_sch > $O/erc.log 2>&1
$CLI sch erc --units mm --severity-all -o $O/erc.rpt esp32_io_board.kicad_sch >> $O/erc.log 2>&1
$CLI sch export netlist --format kicadxml -o $O/netlist.xml esp32_io_board.kicad_sch > $O/net.log 2>&1
$CLI sch export pdf -o $O/schematic.pdf esp32_io_board.kicad_sch > $O/pdf.log 2>&1
echo done
# review artefacts
$CLI sch export bom --fields 'Reference,Value,MPN,LCSC,Footprint,${QUANTITY},${DNP},Note' \
  --labels 'Refs,Value,MPN,LCSC,Footprint,Qty,DNP,Note' --group-by 'Value,MPN,LCSC,Footprint,${DNP}' \
  -o $O/bom.csv esp32_io_board.kicad_sch > $O/bom.log 2>&1
cp $O/schematic.pdf $D/../SCHEMATIC.pdf
cp $O/bom.csv $D/../BOM.csv
echo bom
