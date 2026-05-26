#!/usr/bin/env bash
#
# cost-spike-triage.sh — Triage rápido de un spike de costo.
#
# Usage:
#   ./cost-spike-triage.sh --start 2026-05-25 --end 2026-05-27

set -euo pipefail

START=""
END=""

while [ $# -gt 0 ]; do
  case $1 in
    --start) START="$2"; shift 2 ;;
    --end) END="$2"; shift 2 ;;
    -*) echo "Unknown flag: $1" >&2; exit 1 ;;
    *) shift ;;
  esac
done

if [ -z "$START" ] || [ -z "$END" ]; then
  echo "Usage: $0 --start YYYY-MM-DD --end YYYY-MM-DD" >&2
  exit 1
fi

cat <<EOF
================================================================================
COST SPIKE TRIAGE
================================================================================
Period: $START to $END
Started: $(date -u)
EOF

echo ""
echo "## Costo total por servicio"
aws ce get-cost-and-usage \
  --time-period "Start=$START,End=$END" \
  --granularity DAILY \
  --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --query 'ResultsByTime[].{Date:TimePeriod.Start,Groups:Groups}' 2>/dev/null

echo ""
echo "## Top 10 servicios con mayor costo"
aws ce get-cost-and-usage \
  --time-period "Start=$START,End=$END" \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE 2>/dev/null \
  | jq -r '.ResultsByTime[].Groups[] | [.Keys[0], .Metrics.UnblendedCost.Amount] | @tsv' \
  | sort -k2 -rn | head -10

echo ""
echo "## Costo por región"
aws ce get-cost-and-usage \
  --time-period "Start=$START,End=$END" \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=REGION 2>/dev/null \
  | jq -r '.ResultsByTime[].Groups[] | [.Keys[0], .Metrics.UnblendedCost.Amount] | @tsv' \
  | sort -k2 -rn

echo ""
echo "## Costo por instance type (EC2)"
aws ce get-cost-and-usage \
  --time-period "Start=$START,End=$END" \
  --granularity MONTHLY \
  --metrics UnblendedCost \
  --filter "{\"Dimensions\":{\"Key\":\"SERVICE\",\"Values\":[\"Amazon Elastic Compute Cloud - Compute\"]}}" \
  --group-by Type=DIMENSION,Key=INSTANCE_TYPE 2>/dev/null \
  | jq -r '.ResultsByTime[].Groups[] | [.Keys[0], .Metrics.UnblendedCost.Amount] | @tsv' \
  | sort -k2 -rn | head -10

echo ""
echo "## RunInstances events en el período"
START_ISO="${START}T00:00:00Z"
END_ISO="${END}T23:59:59Z"
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=RunInstances \
  --start-time "$START_ISO" \
  --end-time "$END_ISO" \
  --max-items 100 2>/dev/null \
  | jq -c '.Events[] | {Time: .EventTime, User: .Username, Region: .AwsRegion, IP: .SourceIPAddress}' \
  | head -50

echo ""
echo "================================================================================"
echo "Bandera roja patterns a chequear:"
echo "  - Costo concentrado en región no esperada → [Playbook 04]"
echo "  - Spike en GPU instances (p3/p4/g4) → mining?"
echo "  - Spike en NAT Gateway data → exfil?"
echo "  - Spike fuera de horario de oficina → credencial comprometida?"
echo "================================================================================"
