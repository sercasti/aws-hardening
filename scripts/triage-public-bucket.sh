#!/usr/bin/env bash
#
# triage-public-bucket.sh — Triage rápido de un bucket S3 sospechoso de ser público.
#
# Usage:
#   ./triage-public-bucket.sh [BUCKET_NAME]
#
# Output:
#   - Estado actual del bucket (PAB, policy, ACL)
#   - Listado de objetos (primeros 20)
#   - Quién hizo el bucket público (CloudTrail)
#   - Tags

set -euo pipefail

BUCKET=${1:-}
if [ -z "$BUCKET" ]; then
  echo "Usage: $0 [BUCKET_NAME]" >&2
  exit 1
fi

cat <<EOF
================================================================================
TRIAGE: $BUCKET
Started: $(date -u)
================================================================================
EOF

echo ""
echo "## Public Access Block (account-level + bucket-level)"
echo "Account-level:"
aws s3control get-public-access-block --account-id "$(aws sts get-caller-identity --query Account --output text)" 2>/dev/null \
  | jq '.PublicAccessBlockConfiguration' || echo "  (no PAB at account level)"

echo ""
echo "Bucket-level:"
aws s3api get-public-access-block --bucket "$BUCKET" 2>/dev/null \
  | jq '.PublicAccessBlockConfiguration' || echo "  (no PAB on bucket)"

echo ""
echo "## Bucket Policy"
aws s3api get-bucket-policy --bucket "$BUCKET" 2>/dev/null \
  | jq -r '.Policy' | jq '.' || echo "  (no policy)"

echo ""
echo "## Bucket ACL"
aws s3api get-bucket-acl --bucket "$BUCKET" \
  | jq '.Grants'

echo ""
echo "## Tags"
aws s3api get-bucket-tagging --bucket "$BUCKET" 2>/dev/null \
  | jq '.TagSet' || echo "  (no tags)"

echo ""
echo "## Objects (first 20)"
aws s3 ls "s3://$BUCKET" --recursive --human-readable | head -20

echo ""
echo "## Quién hizo público el bucket? (CloudTrail, últimos 7 días)"
START_TIME=$(date -u -d '7 days ago' +%Y-%m-%dT%H:%M:%SZ 2>/dev/null || date -u -v-7d +%Y-%m-%dT%H:%M:%SZ)

aws cloudtrail lookup-events \
  --lookup-attributes "AttributeKey=ResourceName,AttributeValue=$BUCKET" \
  --start-time "$START_TIME" \
  --max-items 100 2>/dev/null \
  | jq -c '.Events[] | select(.EventName | test("PutBucketAcl|PutBucketPolicy|DeletePublicAccessBlock|PutPublicAccessBlock")) | {Time: .EventTime, Event: .EventName, User: .Username, IP: .SourceIPAddress}'

echo ""
echo "## Recomendación de acción inmediata"
echo "  Si no es un bucket público intencional:"
echo "  aws s3api put-public-access-block --bucket $BUCKET \\"
echo "    --public-access-block-configuration \\"
echo "    'BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true'"
echo ""
echo "  Si es intencional:"
echo "  Agregar tag purpose=public-asset y documentar la excepción."
echo ""
echo "================================================================================"
