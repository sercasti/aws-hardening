#!/usr/bin/env bash
#
# iam-activity-report.sh — Reporte de actividad de una identidad IAM en CloudTrail.
#
# Usage:
#   ./iam-activity-report.sh [USERNAME] [--hours N]
#
# Default hours: 24

set -euo pipefail

USERNAME=${1:-}
HOURS=24

while [ $# -gt 0 ]; do
  case $1 in
    --hours) HOURS="$2"; shift 2 ;;
    -*) echo "Unknown flag: $1" >&2; exit 1 ;;
    *) shift ;;
  esac
done

if [ -z "$USERNAME" ]; then
  echo "Usage: $0 [USERNAME] [--hours N]" >&2
  exit 1
fi

START_TIME=$(date -u -d "$HOURS hours ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-${HOURS}H +%Y-%m-%dT%H:%M:%SZ)

cat <<EOF
================================================================================
IAM ACTIVITY REPORT
================================================================================
Username:    $USERNAME
Window:      last ${HOURS}h (since $START_TIME)
Started:     $(date -u)
EOF

TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

aws cloudtrail lookup-events \
  --lookup-attributes "AttributeKey=Username,AttributeValue=$USERNAME" \
  --start-time "$START_TIME" \
  --max-items 1000 > "$TMPFILE"

TOTAL=$(jq '.Events | length' "$TMPFILE")
echo ""
echo "Total eventos: $TOTAL"

if [ "$TOTAL" -eq 0 ]; then
  echo "No hay actividad. Identidad inactiva o nombre incorrecto."
  exit 0
fi

echo ""
echo "## Top APIs llamadas"
jq -r '.Events[] | .EventName' "$TMPFILE" | sort | uniq -c | sort -rn | head -20

echo ""
echo "## IPs de origen"
jq -r '.Events[] | .SourceIPAddress // "unknown"' "$TMPFILE" | sort | uniq -c | sort -rn

echo ""
echo "## Modificaciones IAM (Attach/Put/Update/Create)"
jq -c '.Events[] | select(.EventName | test("^(Attach|Put|Update|Create|Delete)")) | {Time: .EventTime, Event: .EventName, Resources: ([.Resources[]? | .ResourceName] | join(","))}' "$TMPFILE"

echo ""
echo "## Acciones sobre datos sensibles"
jq -c '.Events[] | select(.EventName | test("(GetSecretValue|GetParameter|Decrypt|GetObject|GetSnapshot)")) | {Time: .EventTime, Event: .EventName, Resources: ([.Resources[]? | .ResourceName] | join(","))}' "$TMPFILE" | head -20

echo ""
echo "## Recursos creados"
jq -c '.Events[] | select(.EventName | test("^(Create|Run)")) | {Time: .EventTime, Event: .EventName, Resources: ([.Resources[]? | .ResourceName] | join(","))}' "$TMPFILE"

echo ""
echo "## Errors (acceso denegado)"
jq -c '.Events[] | select(.ErrorCode != null) | {Time: .EventTime, Event: .EventName, Error: .ErrorCode, Message: .ErrorMessage}' "$TMPFILE"

echo ""
echo "================================================================================"
echo "Heurísticas para evaluar:"
echo "  - Bandera roja: errors AccessDenied seguidos de un Attach/Put (reconnaissance)"
echo "  - Bandera roja: IPs distintas a las normales del usuario"
echo "  - Bandera roja: Create/Run en regiones no usuales"
echo "  - Bandera roja: GetSecretValue, Decrypt masivos"
echo "================================================================================"
