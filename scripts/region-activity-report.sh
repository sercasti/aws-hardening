#!/usr/bin/env bash
#
# region-activity-report.sh — Reporte de actividad en una región AWS específica.
#
# Usage:
#   ./region-activity-report.sh [REGION] [--hours N]

set -euo pipefail

REGION=${1:-}
HOURS=48

while [ $# -gt 0 ]; do
  case $1 in
    --hours) HOURS="$2"; shift 2 ;;
    -*) echo "Unknown flag: $1" >&2; exit 1 ;;
    *) shift ;;
  esac
done

if [ -z "$REGION" ]; then
  echo "Usage: $0 [REGION] [--hours N]" >&2
  exit 1
fi

START_TIME=$(date -u -d "$HOURS hours ago" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-${HOURS}H +%Y-%m-%dT%H:%M:%SZ)

cat <<EOF
================================================================================
REGION ACTIVITY REPORT: $REGION
================================================================================
Window: last ${HOURS}h (since $START_TIME)
Started: $(date -u)
EOF

echo ""
echo "## EC2 Instances activas"
aws ec2 describe-instances --region "$REGION" \
  --filters "Name=instance-state-name,Values=running,stopped" \
  --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,LaunchTime,State.Name,Tags[?Key==`Name`]|[0].Value]' \
  --output table 2>/dev/null || echo "  Error o sin instancias"

echo ""
echo "## RDS Instances"
aws rds describe-db-instances --region "$REGION" \
  --query 'DBInstances[*].[DBInstanceIdentifier,DBInstanceClass,Engine,DBInstanceStatus]' \
  --output table 2>/dev/null || echo "  Error o sin instances"

echo ""
echo "## S3 Buckets creados recientemente"
aws s3api list-buckets --query "Buckets[?CreationDate>='${START_TIME}'].[Name, CreationDate]" --output table 2>/dev/null

echo ""
echo "## EBS Snapshots recientes (de mi cuenta)"
aws ec2 describe-snapshots --region "$REGION" --owner-ids self \
  --query "Snapshots[?StartTime>='${START_TIME}'].[SnapshotId,VolumeSize,StartTime,Description]" \
  --output table 2>/dev/null || echo "  Sin snapshots recientes"

echo ""
echo "## RunInstances events en esta región (últimas ${HOURS}h)"
aws cloudtrail lookup-events --region "$REGION" \
  --lookup-attributes AttributeKey=EventName,AttributeValue=RunInstances \
  --start-time "$START_TIME" \
  --max-items 50 2>/dev/null \
  | jq -c '.Events[] | {Time: .EventTime, User: .Username, IP: .SourceIPAddress}'

echo ""
echo "## CreateBucket events"
aws cloudtrail lookup-events --region "$REGION" \
  --lookup-attributes AttributeKey=EventName,AttributeValue=CreateBucket \
  --start-time "$START_TIME" \
  --max-items 50 2>/dev/null \
  | jq -c '.Events[] | {Time: .EventTime, User: .Username, Bucket: (.Resources[]? | .ResourceName)}'

echo ""
echo "## Estimación de costo de la región (último día)"
YESTERDAY=$(date -u -d 'yesterday' +%Y-%m-%d 2>/dev/null || date -u -v-1d +%Y-%m-%d)
TODAY=$(date -u +%Y-%m-%d)
aws ce get-cost-and-usage \
  --time-period "Start=$YESTERDAY,End=$TODAY" \
  --granularity DAILY \
  --metrics UnblendedCost \
  --filter "{\"Dimensions\":{\"Key\":\"REGION\",\"Values\":[\"$REGION\"]}}" \
  --query 'ResultsByTime[].Total.UnblendedCost' 2>/dev/null \
  | jq '.' || echo "  No pude calcular costo"

echo ""
echo "================================================================================"
echo "Si la actividad NO es esperada en esta región:"
echo "  1. Identificá la identidad (CloudTrail Username)"
echo "  2. Aplicá [Playbook 04]: SCP de region restriction temporal"
echo "  3. Stop instances (NO terminate) para preservar evidencia"
echo "  4. Snapshot de volúmenes"
echo "================================================================================"
