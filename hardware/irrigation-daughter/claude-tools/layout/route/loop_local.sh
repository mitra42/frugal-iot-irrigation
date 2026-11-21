#!/bin/bash
# Mac: Freerouting in rounds, each round starting from the last one's result (merge.py), as the LoRa board's loop.sh
# but local. FR = dir holding freerouting-2.1.0.jar, default ~/tools/freerouting (kept outside every repo: it is
# 67 MB and anyone can fetch it from the Freerouting GitHub releases). JAVA: Java 21+; 2.1.0 runs on 25.
# Route.java (beside this script) is compiled into out/route_classes/ when missing or older than its source.
# loop_local.sh in.dsn tag rounds passes   -> <tag>_<n>.ses, <tag>.progress
B=$1; T=$2; R=${3:-4}; P=${4:-25}; H="$(cd "$(dirname "$0")" && pwd)"
JAVA=${JAVA:-/opt/homebrew/opt/openjdk@25/bin/java}
FR=${FR:-$HOME/tools/freerouting}; JAR=$FR/freerouting-2.1.0.jar; CLS=out/route_classes
[ -f $JAR ] || { echo "no $JAR - download freerouting-2.1.0.jar from github.com/freerouting/freerouting/releases"; exit 1; }
if [ ! -f $CLS/Route.class ] || [ $H/Route.java -nt $CLS/Route.class ]; then
  mkdir -p $CLS && $(dirname $JAVA)/javac -cp $JAR -d $CLS $H/Route.java || exit 1
fi
cp $B ${T}_0.dsn; : > ${T}.progress
for r in $(seq 1 $R); do
  perl -e "alarm shift; exec @ARGV" 1500 $JAVA -Xmx4g -cp $JAR:$CLS Route ${T}_$((r-1)).dsn ${T}_$r.ses $P > ${T}_$r.log 2>&1
  best=$(grep '^pass' ${T}_$r.log | sort -t' ' -k4 -n | head -1)
  echo "round $r: $best" >> ${T}.progress
  echo "$best" | grep -q "incomplete 0" && break
  python3 $H/merge.py ${T}_0.dsn ${T}_$r.ses ${T}_$r.dsn > /dev/null
done
echo done >> ${T}.progress
