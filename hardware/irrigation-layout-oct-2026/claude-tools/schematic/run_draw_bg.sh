#!/bin/bash
T=/Users/mitra/Claude/frugal-layout/irrigation-layout-oct-2026/claude-tools/schematic
mkdir -p $T/out; rm -f $T/out/draw.done
( bash $T/run_draw.sh "$@"; touch $T/out/draw.done ) > /dev/null 2>&1 &
echo started
