#!/usr/bin/env bash
#
# isolate-instance.sh — Aisla una instancia EC2 sospechosa SIN destruir evidencia.
#
# Usage:
#   ./isolate-instance.sh i-0abcdef1234567890
#
# Acciones:
#   1. Crea security group "quarantine" sin egress
#   2. Snapshot de todos los EBS volumes (etiquetados como evidencia)
#   3. Aplica el SG de quarantine a la instancia
#   4. Revoca sesiones del IAM role (si tiene)
#
# Output: directorio /tmp/ir-[INSTANCE_ID]-[TIMESTAMP]/ con todo el contexto

set -euo pipefail

INSTANCE_ID=${1:-}
if [ -z "$INSTANCE_ID" ]; then
  echo "Usage: $0 [INSTANCE_ID]" >&2
  exit 1
fi

TIMESTAMP=$(date -u +%Y%m%d-%H%M%S)
EVIDENCE_DIR="/tmp/ir-${INSTANCE_ID}-${TIMESTAMP}"
mkdir -p "$EVIDENCE_DIR"

cat <<EOF | tee "$EVIDENCE_DIR/banner.txt"
================================================================================
ISOLATE INSTANCE — INCIDENT RESPONSE
================================================================================
Instance ID:   $INSTANCE_ID
Started at:    $(date -u)
Evidence dir:  $EVIDENCE_DIR

This script will:
  1. Describe the instance (saved as evidence)
  2. Create a quarantine SG (no egress)
  3. Snapshot all EBS volumes
  4. Replace the SG of the instance with quarantine SG
  5. Revoke IAM role sessions (if role attached)

The instance will REMAIN RUNNING (process state preserved).
You will need to perform forensics separately.

================================================================================
EOF

echo ""
read -p "Confirmás aplicar isolation a $INSTANCE_ID? (yes/no): " confirm
if [ "$confirm" != "yes" ]; then
  echo "Aborted."
  exit 0
fi

echo ""
echo "[1/5] Describiendo la instancia..."
aws ec2 describe-instances --instance-ids "$INSTANCE_ID" \
  > "$EVIDENCE_DIR/instance-describe.json"

VPC_ID=$(jq -r '.Reservations[0].Instances[0].VpcId' "$EVIDENCE_DIR/instance-describe.json")
ROLE_ARN=$(jq -r '.Reservations[0].Instances[0].IamInstanceProfile.Arn // empty' "$EVIDENCE_DIR/instance-describe.json")
ORIGINAL_SGS=$(jq -r '.Reservations[0].Instances[0].SecurityGroups[].GroupId' "$EVIDENCE_DIR/instance-describe.json")

echo "  VPC: $VPC_ID"
echo "  Role ARN: ${ROLE_ARN:-none}"
echo "  Original SGs: $ORIGINAL_SGS"
echo "$ORIGINAL_SGS" > "$EVIDENCE_DIR/original-sgs.txt"

echo ""
echo "[2/5] Creando quarantine security group..."
QUARANTINE_SG=$(aws ec2 create-security-group \
  --group-name "quarantine-ir-${TIMESTAMP}" \
  --description "IR quarantine for ${INSTANCE_ID}" \
  --vpc-id "$VPC_ID" \
  --query 'GroupId' --output text)

aws ec2 revoke-security-group-egress \
  --group-id "$QUARANTINE_SG" \
  --protocol -1 --port -1 --cidr 0.0.0.0/0 2>/dev/null || true

echo "  Quarantine SG: $QUARANTINE_SG"
echo "$QUARANTINE_SG" > "$EVIDENCE_DIR/quarantine-sg.txt"

echo ""
echo "[3/5] Snapshot de volúmenes..."
VOLUMES=$(jq -r '.Reservations[0].Instances[0].BlockDeviceMappings[].Ebs.VolumeId' "$EVIDENCE_DIR/instance-describe.json")
for vol in $VOLUMES; do
  SNAPSHOT_ID=$(aws ec2 create-snapshot \
    --volume-id "$vol" \
    --description "IR-snapshot-${INSTANCE_ID}-${TIMESTAMP}" \
    --tag-specifications "ResourceType=snapshot,Tags=[{Key=incident,Value=${TIMESTAMP}},{Key=instance,Value=${INSTANCE_ID}},{Key=do-not-delete,Value=true}]" \
    --query 'SnapshotId' --output text)
  echo "  $vol → $SNAPSHOT_ID"
  echo "$vol $SNAPSHOT_ID" >> "$EVIDENCE_DIR/snapshots.txt"
done

echo ""
echo "[4/5] Aplicando quarantine SG..."
aws ec2 modify-instance-attribute \
  --instance-id "$INSTANCE_ID" \
  --groups "$QUARANTINE_SG"
echo "  Aplicado. La instancia ya no puede hablar con nada."

echo ""
echo "[5/5] Revocando sesiones del role..."
if [ -n "$ROLE_ARN" ]; then
  ROLE_NAME=$(echo "$ROLE_ARN" | awk -F/ '{print $NF}')
  NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)
  cat > "$EVIDENCE_DIR/revoke-sessions.json" <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": "*",
    "Resource": "*",
    "Condition": {
      "DateLessThan": {
        "aws:TokenIssueTime": "$NOW"
      }
    }
  }]
}
EOF
  aws iam put-role-policy \
    --role-name "$ROLE_NAME" \
    --policy-name "AWSRevokeOlderSessions" \
    --policy-document "file://$EVIDENCE_DIR/revoke-sessions.json"
  echo "  Sesiones del role $ROLE_NAME revocadas."
else
  echo "  No hay role asociado, skip."
fi

echo ""
cat <<EOF | tee "$EVIDENCE_DIR/summary.txt"
================================================================================
ISOLATION COMPLETE
================================================================================
Instance:      $INSTANCE_ID (RUNNING, isolated)
Quarantine SG: $QUARANTINE_SG
Snapshots:     $(wc -l < "$EVIDENCE_DIR/snapshots.txt") volumes snapshotted
Role:          ${ROLE_NAME:-none} (sessions revoked)

Next steps:
  1. Investigá las snapshots (attach a una instance forensic separada)
  2. Mirá CloudTrail por las acciones de la identidad/role
  3. Revisá GuardDuty findings asociados
  4. Si confirmás compromise: documentá el vector y empezá [Playbook 06] eradication

Evidence in: $EVIDENCE_DIR
================================================================================
EOF
