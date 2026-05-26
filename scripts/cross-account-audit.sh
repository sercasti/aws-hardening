#!/usr/bin/env bash
#
# cross-account-audit.sh — Audita el uso cross-account de un rol IAM.
#
# Usage:
#   ./cross-account-audit.sh [ROLE_NAME] [--days N]

set -euo pipefail

ROLE_NAME=${1:-}
DAYS=30

while [ $# -gt 0 ]; do
  case $1 in
    --days) DAYS="$2"; shift 2 ;;
    -*) echo "Unknown flag: $1" >&2; exit 1 ;;
    *) shift ;;
  esac
done

if [ -z "$ROLE_NAME" ]; then
  echo "Usage: $0 [ROLE_NAME] [--days N]" >&2
  exit 1
fi

START_TIME=$(date -u -d "$DAYS days ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-${DAYS}d +%Y-%m-%dT%H:%M:%SZ)

cat <<EOF
================================================================================
CROSS-ACCOUNT AUDIT: $ROLE_NAME
================================================================================
Window: last ${DAYS} days (since $START_TIME)
EOF

echo ""
echo "## Trust policy actual"
aws iam get-role --role-name "$ROLE_NAME" \
  --query 'Role.AssumeRolePolicyDocument' 2>/dev/null | jq '.'

echo ""
echo "## AssumeRole events"
TMPFILE=$(mktemp)
trap "rm -f $TMPFILE" EXIT

aws cloudtrail lookup-events \
  --lookup-attributes "AttributeKey=ResourceName,AttributeValue=$ROLE_NAME" \
  --start-time "$START_TIME" \
  --max-items 1000 > "$TMPFILE"

TOTAL=$(jq '.Events | length' "$TMPFILE")
echo "Total events: $TOTAL"

echo ""
echo "## Cuentas source que asumieron este rol"
jq -r '.Events[] | select(.EventName == "AssumeRole") | .UserIdentity.AccountId // "unknown"' "$TMPFILE" \
  | sort | uniq -c | sort -rn

echo ""
echo "## Identidades source (top 20)"
jq -r '.Events[] | select(.EventName == "AssumeRole") | .UserIdentity.Arn // "unknown"' "$TMPFILE" \
  | sort | uniq -c | sort -rn | head -20

echo ""
echo "## IPs source (top 20)"
jq -r '.Events[] | select(.EventName == "AssumeRole") | .SourceIPAddress // "unknown"' "$TMPFILE" \
  | sort | uniq -c | sort -rn | head -20

echo ""
echo "## Eventos con ExternalId presente vs ausente"
WITH_EXT=$(jq '[.Events[] | select(.EventName == "AssumeRole") | select(.RequestParameters.externalId)] | length' "$TMPFILE")
WITHOUT_EXT=$(jq '[.Events[] | select(.EventName == "AssumeRole") | select(.RequestParameters.externalId == null)] | length' "$TMPFILE")
echo "Con ExternalId: $WITH_EXT"
echo "Sin ExternalId: $WITHOUT_EXT"

echo ""
echo "## Acciones realizadas mientras se asumió el rol"
echo "(filtrando acciones write/modify)"
jq -c '.Events[] | select(.Username == "'"$ROLE_NAME"'") | select(.EventName | test("^(Create|Put|Update|Delete|Attach|Detach|Modify)")) | {Time: .EventTime, Event: .EventName, IP: .SourceIPAddress}' "$TMPFILE" | head -30

echo ""
echo "================================================================================"
echo "Heurísticas:"
echo "  - Sin ExternalId pero con Principal de cuenta externa → confused deputy risk"
echo "  - Multiples cuentas source no esperadas → trust policy demasiado abierta"
echo "  - IPs residenciales → posible compromise de la cuenta source"
echo "  - Acciones write desde rol asumido externamente → revisar permisos del rol"
echo "================================================================================"
