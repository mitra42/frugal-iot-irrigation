#!/bin/bash
T="$(cd "$(dirname "$0")" && pwd)"
mkdir -p $T/out; rm -f $T/out/draw.done
( bash $T/run_draw.sh "$@"; touch $T/out/draw.done ) > /dev/null 2>&1 &
echo started
