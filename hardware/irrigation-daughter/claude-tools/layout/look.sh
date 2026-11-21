#!/bin/bash
# Mac: render the board's fab/courtyard/silk layers (and optionally copper) to out/look.png for a visual check.
# qlmanage crops a landscape page to a square, so the SVG is wrapped in a square viewBox first. Usage: look.sh [layers]
CLI=/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli
L="$(cd "$(dirname "$0")" && pwd)"; D=$L/../../daughter; O=$L/out; mkdir -p $O
LAY=${1:-F.Fab,F.Courtyard,Edge.Cuts,F.Silkscreen}
$CLI pcb export svg --layers $LAY --exclude-drawing-sheet --page-size-mode 2 --mode-single -o $O/look.svg $D/irrigation_daughter.kicad_pcb > /dev/null 2>&1
python3 - "$O/look.svg" <<'PY'
import re, sys
p = sys.argv[1]; s = open(p).read()
vb = [float(x) for x in re.search(r'viewBox="([\d.\- ]+)"', s).group(1).split()]
side = max(vb[2], vb[3])
nv = f'{vb[0]-(side-vb[2])/2} {vb[1]-(side-vb[3])/2} {side} {side}'
s = re.sub(r'viewBox="[\d.\- ]+"', f'viewBox="{nv}"', s, count=1)
s = re.sub(r'(<svg[^>]*?)width="[^"]*"', r'\1width="2000"', s, count=1)
s = re.sub(r'(<svg[^>]*?)height="[^"]*"', r'\1height="2000"', s, count=1)
s = s.replace('<svg', '<svg style="background:white"', 1)
open(p.replace('.svg', '_sq.svg'), 'w').write(s)
PY
rm -f $O/look_sq.svg.png; qlmanage -t -s 2000 -o $O $O/look_sq.svg > /dev/null 2>&1; mv $O/look_sq.svg.png $O/look.png; echo $O/look.png
