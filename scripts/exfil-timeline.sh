#!/usr/bin/env bash
#
# exfil-timeline.sh — Genera timeline de actividad de una identidad sospechosa de exfil.
#
# Usage:
#   ./exfil-timeline.sh [IDENTITY] [--start DATE]

set -euo pipefail

IDENTITY=${1:-}
START=""

while [ $# -gt 0 ]; do
  case $1 in
    --start) START="$2"; shift 2 ;;
    -*) echo "Unknown flag: $1" >&2; exit 1 ;;
    *) shift ;;
  esac
done

if [ -z "$IDENTITY" ]; then
  echo "Usage: $0 [IDENTITY] [--start YYYY-MM-DD]" >&2
  exit 1
fi

if [ -z "$START" ]; then
  START=$(date -u -d "7 days ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-7d +%Y-%m-%dT%H:%M:%SZ)
else
  START="${START}T00:00:00Z"
fi

cat <<EOF
================================================================================
EXFIL TIMELINE: $IDENTITY
================================================================================
Window since: $START
EOF

TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

aws cloudtrail lookup-events \
  --lookup-attributes "AttributeKey=Username,AttributeValue=$IDENTITY" \
  --start-time "$START" \
  --max-items 5000 > "$TMPFILE"

TOTAL=$(jq '.Events | length' "$TMPFILE")
echo "Total events: $TOTAL"

echo ""
echo "## Actividad por hora"
jq -r '.Events[] | .EventTime' "$TMPFILE" | cut -dT -f1-2 | cut -d: -f1 | sort | uniq -c | sort -rn | head -20

echo ""
echo "## Read-heavy actions (potencial exfil S3)"
jq -c '.Events[] | select(.EventName == "GetObject") | {Time: .EventTime, Bucket: (.Resources[0].ResourceName // "unknown" | split("/")[0])}' "$TMPFILE" | head -30
echo ""
echo "Total GetObject events: $(jq '[.Events[] | select(.EventName == "GetObject")] | length' "$TMPFILE")"

echo ""
echo "## Listing actions (reconnaissance)"
jq -c '.Events[] | select(.EventName | test("^List")) | {Time: .EventTime, Event: .EventName}' "$TMPFILE" | head -30

echo ""
echo "## Snapshot/Copy actions (potencial exfil de data persistente)"
jq -c '.Events[] | select(.EventName | test("(CreateSnapshot|CopySnapshot|ModifyDBSnapshotAttribute|ModifySnapshotAttribute|CopyDBSnapshot)")) | {Time: .EventTime, Event: .EventName, Params: .RequestParameters}' "$TMPFILE"

echo ""
echo "## IPs source con su uso"
jq -r '.Events[] | .SourceIPAddress // "unknown"' "$TMPFILE" | sort | uniq -c | sort -rn | head -10

echo ""
echo "## Buckets accedidos"
jq -r '.Events[] | select(.EventName == "GetObject") | .Resources[]? | select(.ResourceType == "AWS::S3::Object") | .ResourceName' "$TMPFILE" | awk -F/ '{print $1}' | sort | uniq -c | sort -rn | head -20

echo ""
echo "## Estimación de bytes (cuando disponible)"
TOTAL_BYTES=$(jq '[.Events[].AdditionalEventData.bytesTransferredOut // 0] | add' "$TMPFILE" 2>/dev/null || echo "0")
echo "Bytes egresados (approximado): $TOTAL_BYTES"
if [ "$TOTAL_BYTES" -gt 1000000000 ]; then
  echo ">> CRÍTICO: más de 1 GB egresado <<"
fi

echo ""
echo "================================================================================"
echo "Próximos pasos si confirmás exfil:"
echo "  1. [Playbook 08] containment inmediato"
echo "  2. Cuantificar data: lista exacta de objetos exfiltrados"
echo "  3. Notificar legal/CISO si data sensible"
echo "  4. Notificación regulatoria si GDPR/LGPD/CCPA aplican"
echo "================================================================================"
