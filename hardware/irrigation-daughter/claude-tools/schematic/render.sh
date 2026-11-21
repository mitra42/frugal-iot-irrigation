#!/bin/bash
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
D="$(cd "$(dirname "$0")/../../daughter" && pwd)"
mkdir -p $D/../claude-tools/schematic/out; cd $D && $CLI sch export pdf -o ../claude-tools/schematic/out/new.pdf irrigation_daughter.kicad_sch > /dev/null 2>&1
echo rendered
