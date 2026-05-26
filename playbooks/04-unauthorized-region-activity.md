# Playbook 04: Actividad en región no aprobada

> Apareció actividad en una región que tu organización no usa. Generalmente significa criptominería con tus credenciales, exfiltración, o reconnaissance. Este playbook contiene el blast radius rápido.

## Trigger

- **GuardDuty finding** `CryptoCurrency:EC2/BitcoinTool.B!DNS` o similar.
- **Cost Anomaly Detection** spike en una región nueva.
- **CloudTrail** detecta `RunInstances` en región sin recursos esperados.
- **Custom CloudWatch alarm** sobre `aws.events` con region not in approved list.

## Severity

**High** por default. Sube a **Critical** si:

- La actividad es en múltiples cuentas simultáneamente.
- Los recursos creados son `p3.*`, `p4.*`, `g4.*` (GPU, indica mining serio).
- Hay exfiltración de data en paralelo (RDS snapshot copy, S3 GetObject masivo).

## SLA

- **Detection a Containment**: 2 horas.
- **Containment a Eradication**: 4 horas.
- **Recovery**: 6 horas.
- **Post-mortem**: 1 semana.

## Pasos

### 1. Triage (10 minutos)

**Confirmar actividad real en la región.**

```bash
# Reemplazá REGION con la región sospechosa (ej. ap-south-1)
aws ec2 describe-instances --region [REGION] \
  --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,LaunchTime,State.Name]'

aws ec2 describe-snapshots --region [REGION] \
  --owner-ids self \
  --query 'Snapshots[*].[SnapshotId,VolumeSize,StartTime]'

aws rds describe-db-instances --region [REGION] \
  --query 'DBInstances[*].[DBInstanceIdentifier,DBInstanceClass,DBInstanceStatus]'

aws s3api list-buckets --region [REGION] \
  --query 'Buckets[?CreationDate>=`2026-05-20`]'
```

**Mirar el inventario de la región:**

- ¿Hay instancias activas?
- ¿De qué tipo? (Los `p*.*xlarge`, `g*.*xlarge`, `x1e.*` son banderas rojas: usados para mining/AI training con costo alto)
- ¿Cuándo se lanzaron?
- ¿Quién las lanzó? (CloudTrail)

```bash
# Lookup quien lanzó las instancias
aws cloudtrail lookup-events --region [REGION] \
  --lookup-attributes AttributeKey=EventName,AttributeValue=RunInstances \
  --max-items 50 \
  | jq '.Events[] | {Time: .EventTime, User: .Username, IP: .SourceIPAddress}'
```

### 2. Containment (15 minutos)

**A. Frenar el sangrado de costo: stop instances primero, después terminate.**

```bash
# Stop primero (preserva el volume para forensics)
INSTANCES=$(aws ec2 describe-instances --region [REGION] \
  --filters "Name=instance-state-name,Values=running" \
  --query 'Reservations[].Instances[].InstanceId' --output text)

for instance in $INSTANCES; do
  aws ec2 stop-instances --region [REGION] --instance-ids "$instance"
done
```

**B. Identificar la credencial usada para crear los recursos.**

CloudTrail te dice qué identidad (`Username`) creó los recursos. Esa identidad es la comprometida.

- Si es un IAM user: activar [Playbook 01](./01-leaked-credentials.md).
- Si es un rol asumido: identificar quién lo asumió (`AssumeRole` event) y trace upstream.

**C. Bloquear la región vía SCP temporal.**

```bash
# SCP que bloquea todas las acciones en la región sospechosa
cat > deny-region-temp.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Action": "*",
    "Resource": "*",
    "Condition": {
      "StringEquals": {
        "aws:RequestedRegion": ["[REGION]"]
      }
    }
  }]
}
EOF

aws organizations create-policy \
  --content file://deny-region-temp.json \
  --description "Temporary deny for incident response" \
  --name DenyRegionTempIR \
  --type SERVICE_CONTROL_POLICY

# Attach a la cuenta afectada
aws organizations attach-policy \
  --policy-id [POLICY_ID] \
  --target-id [ACCOUNT_ID]
```

Esta SCP impide que el atacante levante MÁS recursos en esa región mientras investigás.

### 3. Eradication (30 minutos)

**A. Inventariar y eliminar todos los recursos del atacante.**

```bash
# Listar todos los servicios activos en la región
for service in ec2 rds elasticache eks ecs lambda dynamodb; do
  echo "=== $service ==="
  aws "$service" describe-* --region [REGION] 2>/dev/null | jq '.' || true
done
```

Por cada recurso encontrado:

1. Snapshot/backup para evidencia.
2. Terminate/delete.

**Atención a:**

- **VPC peering connections** desde la región atacada a otras (exfil path).
- **S3 buckets** creados en la región (pueden tener data exfiltrada).
- **IAM users/roles** creados (persistence).
- **Lambdas** programadas (backdoor para re-entrar).

**B. Buscar evidencia de exfiltración.**

```bash
# CloudTrail lookup para s3:GetObject masivo
aws cloudtrail lookup-events --region [REGION] \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
  --start-time '[INCIDENT_START]' \
  --max-items 1000 \
  > exfil-check.json

# Contar objetos por bucket
jq '.Events[] | .Resources[] | select(.ResourceType == "AWS::S3::Object") | .ResourceName' exfil-check.json | sort | uniq -c | sort -rn | head -20
```

Si hay GetObject masivo de buckets sensibles, asumí exfil real. Activar comms/legal.

**C. Buscar persistence mechanisms.**

Igual que en [Playbook 03](./03-iam-privilege-escalation.md), buscá:

- Nuevos usuarios IAM.
- Nuevos roles con cross-account trust.
- Nuevas access keys.
- Lambdas con triggers en EventBridge.
- CloudFormation stacks (atacantes los usan para persistencia "limpia").

### 4. Recovery

**A. Una vez confirmado que no hay actividad activa, quitar la SCP temporal.**

Si tenés controles de region restriction permanentes (Nivel 2 ORG.4), aplicalos ahora. Si no, considerá esta como prioridad alta post-incident.

**B. Restaurar workloads legítimos.**

Si la cuenta tiene workloads en otras regiones que dependen de la región afectada (cross-region replication, multi-region setups), validar que siguen operacionales.

**C. Comunicación.**

- A management si la severidad fue critical.
- A clientes si hubo exfiltración confirmada.
- A regulators si aplican leyes de notificación.

### 5. Post-mortem (1 semana)

Énfasis en:

1. **Cómo entró el atacante.** Identificá la credencial comprometida y el vector inicial.
2. **Cuánto tiempo estuvo dentro.** Diff entre primer evento sospechoso y detección.
3. **Qué costos generó.** Suma de la billing en la región afectada durante el período del incidente.
4. **Si hubo exfiltración.** Sí/no/inconcluso, con justificación.
5. **Action items.**
   - SCP de region restriction permanente.
   - Cost Anomaly Detection con threshold bajo para regiones no-usadas.
   - GuardDuty habilitado en TODAS las regiones (no solo las activas).
   - Process review: cómo se filtró la credencial.

## Anti-patterns

- ❌ **Terminate instances inmediatamente sin snapshot.** Pierdes evidencia forensic.
- ❌ **Asumir que es solo mining y no exfil.** Atacantes sofisticados hacen ambos.
- ❌ **Quitar la SCP de region restriction "porque rompe builds".** Si rompe builds, los builds están mal escritos. Arreglar builds, no quitar la SCP.
- ❌ **No buscar persistence.** El mining es ruidoso (señuelo). La persistence es silenciosa (el ataque real).

## Automatización

### Fase 1: Manual

Humano sigue el playbook.

### Fase 2: Asistido

Script que toma una región y genera reporte de toda actividad:

```bash
./scripts/region-activity-report.sh ap-south-1 --hours 48
# Output: recursos activos, costo, lanzamientos, identidades involucradas
```

### Fase 3: Semi-automático

EventBridge rule sobre Cost Anomaly Detection con condition (region not in approved list):

```
Trigger: cost anomaly en región no aprobada
   ↓
Lambda 1: Aplicar SCP temporal de region restriction
   ↓
Lambda 2: Stop (no terminate) todas las instances en la región
   ↓
Lambda 3: Notificar on-call con resumen
   ↓
Human: investiga, decide eradication
```

### Fase 4: Automático

No recomendado. La decisión de terminate de recursos requiere humano (puede haber workload legítimo desconocido).

## Métricas

- **MTTD**: cuánto tarda en detectarse una región no esperada.
- **Cost of incident**: dólares quemados por el atacante.
- **Time to contain**: tiempo entre detección y SCP aplicada.
- **Recurrence**: ¿la cuenta vuelve a tener este tipo de incident?

## Recursos

- [GuardDuty CryptoCurrency findings](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-ec2.html)
- [AWS Cost Anomaly Detection](https://docs.aws.amazon.com/cost-management/latest/userguide/getting-started-ad.html)
- [SCP for region restriction (example)](../templates/scps/03-deny-region-outside-list.json)
- [Pacu module: cryptominer simulation](https://github.com/RhinoSecurityLabs/pacu)
