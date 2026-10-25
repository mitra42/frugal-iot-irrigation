#!/bin/bash
# Run on the Mac: fetch JLCPCB records for every LCSC code in out/bom.csv -> out/jlc_prices.json
cd "$(dirname "$0")"
mkdir -p out; rm -f out/jlc.done
( /usr/bin/python3 -c "
import csv, jlc_query as j
codes = sorted({r['LCSC'] for r in csv.DictReader(open('out/bom.csv')) if r['LCSC']})
j.dump(codes, 'out/jlc_prices.json')" > out/jlc_dump.log 2>&1; touch out/jlc.done ) > /dev/null 2>&1 &
echo started
