#!/bin/bash
# Mac: Freerouting in rounds, each round starting from the last one's result (merge.py), as the LoRa board's loop.sh
# but local. Needs FR=<dir with freerouting-2.1.0.jar + Route.class> and JAVA (Java 21+; 2.1.0 runs on 25).
# loop_local.sh in.dsn tag rounds passes   -> <tag>_<n>.ses, <tag>.progress
B=$1; T=$2; R=${3:-4}; P=${4:-25}; H="$(cd "$(dirname "$0")" && pwd)"
JAVA=${JAVA:-/opt/homebrew/opt/openjdk@25/bin/java}
cp $B ${T}_0.dsn; : > ${T}.progress
for r in $(seq 1 $R); do
  perl -e "alarm shift; exec @ARGV" 1500 $JAVA -Xmx4g -cp $FR/freerouting-2.1.0.jar:$FR Route ${T}_$((r-1)).dsn ${T}_$r.ses $P > ${T}_$r.log 2>&1
  best=$(grep '^pass' ${T}_$r.log | sort -t' ' -k4 -n | head -1)
  echo "round $r: $best" >> ${T}.progress
  echo "$best" | grep -q "incomplete 0" && break
  python3 $H/merge.py ${T}_0.dsn ${T}_$r.ses ${T}_$r.dsn > /dev/null
done
echo done >> ${T}.progress
