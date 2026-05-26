# Playbook 07: Anomalía cross-account

> Un rol está siendo asumido desde una cuenta no esperada, o desde una cuenta tuya pero por una identidad sospechosa. Cross-account es el path favorito de atacantes sofisticados porque cruza boundaries que tu detection no siempre cubre.

## Trigger

- **GuardDuty finding** `UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS` o `UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.InsideAWS`.
- **IAM Access Analyzer** detecta un trust policy nuevo que permite a una cuenta no aprobada.
- **CloudTrail event** `AssumeRole` desde una cuenta source no listada en tu account inventory.
- **CloudTrail event** `UpdateAssumeRolePolicy` agregando un Principal de cuenta externa.
- Detección manual: revisás los roles y ves uno con trust hacia `arn:aws:iam::[CUENTA_DESCONOCIDA]:root`.

## Severity

- **Critical** si la cuenta source es externa a tu Organization Y el rol tiene permisos elevados (`*:*`, `iam:*`, `s3:GetObject` sobre buckets sensibles).
- **High** si la cuenta source es interna pero el patrón de uso es anómalo (rol nunca asumido desde esa cuenta antes).
- **Medium** si es interno y los permisos son limitados.

## SLA

- **Detection a Containment**: 30 minutos.
- **Containment a Eradication**: 4 horas.
- **Recovery**: 8 horas.
- **Post-mortem**: 1 semana.

## Pasos

### 1. Triage (10 minutos)

**A. Caracterizar la trust policy.**

```bash
ROLE_NAME="[ROLE_NAME]"

aws iam get-role --role-name $ROLE_NAME \
  --query 'Role.AssumeRolePolicyDocument'
```

Buscar:

- **Principal con cuentas externas** (`arn:aws:iam::[ACCOUNT]:root`).
- **Principal con `"AWS": "*"`** (cualquier identidad AWS del mundo). Si no hay Condition, esto es game over.
- **Condition con `sts:ExternalId`** ausente o débil (string corto y predecible).
- **Condition con `aws:SourceAccount`** ausente cuando debería estar.

**B. Identificar quién está asumiendo el rol.**

```bash
# Eventos de AssumeRole recientes
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=$ROLE_NAME \
  --start-time '2026-05-20T00:00:00Z' \
  --max-items 100 \
  | jq '.Events[] | select(.EventName == "AssumeRole") | {Time: .EventTime, SourceAccount: .UserIdentity.AccountId, SourceUser: .UserIdentity.UserName, SourceArn: .UserIdentity.Arn, SourceIP: .SourceIPAddress}'
```

Mirá:

- `SourceAccount`: ¿es una cuenta de tu Organization? ¿es una cuenta de un partner conocido (vendor MSP/SI)?
- `SourceArn`: ¿es un usuario o un rol? Si es un rol, ¿de qué servicio?
- `SourceIP`: ¿es una IP corporativa, una IP de AWS, una IP residencial sospechosa?

**C. Listar accounts inventory.**

```bash
# Si tenés Organizations
aws organizations list-accounts --query 'Accounts[].[Id,Name,Status]' --output table

# Tu account inventory ground truth debería estar en algún registro (Confluence, Notion, gitops). Cruzalo.
```

Si la cuenta source NO está en tu inventory, es high severity automático.

### 2. Containment (15 minutos)

**A. Cortar el acceso modificando la trust policy.**

```bash
# Backup primero
aws iam get-role --role-name $ROLE_NAME \
  --query 'Role.AssumeRolePolicyDocument' > trust-policy-backup.json

# Aplicar trust policy temporal que bloquea TODO
cat > trust-policy-block.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Principal": "*",
    "Action": "sts:AssumeRole"
  }]
}
EOF

aws iam update-assume-role-policy \
  --role-name $ROLE_NAME \
  --policy-document file://trust-policy-block.json
```

Esto deja el rol existente pero nadie puede asumirlo nuevamente. Si workloads legítimos lo necesitan, vas a saberlo en minutos (alertas de tus apps). Eso es informativo, no malo.

**B. Revocar sesiones activas.**

```bash
# Igual al patrón del Playbook 06
NOW=$(date -u +%Y-%m-%dT%H:%M:%SZ)

cat > revoke-sessions.json <<EOF
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
  --role-name $ROLE_NAME \
  --policy-name AWSRevokeOlderSessions \
  --policy-document file://revoke-sessions.json
```

**C. Si la cuenta source es externa y sospechosa, considerar bloqueo a nivel Organization.**

Si tu Organization permite el bloqueo de cuentas externas vía SCP, aplicalo. Si no, lo mejor es la trust policy del rol que ya hicimos.

### 3. Eradication (30 a 90 minutos)

**A. Auditar lo que hizo la identidad mientras asumió el rol.**

```bash
# Sesiones del rol en el período sospechoso
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=$ROLE_NAME \
  --start-time '[INCIDENT_START]' \
  --max-items 1000 \
  > role-activity.json

# Filtrar acciones que NO son read-only
jq '.Events[] | select(.EventName != ("Get*", "List*", "Describe*", "Head*"))' role-activity.json | head -100
```

**B. Si el rol tiene `iam:*` o equivalente, buscar identidades creadas por el atacante.**

Patrón típico: el atacante asume un rol con `iam:*`, crea un usuario IAM nuevo con `AdministratorAccess` como backdoor, luego puede dejar de usar el rol comprometido.

```bash
# Listar usuarios creados desde la fecha del compromise
aws iam list-users --query "Users[?CreateDate>=\`[INCIDENT_START_DATE]\`]"

# Access keys creadas
aws iam list-users | jq -r '.Users[].UserName' | while read user; do
  aws iam list-access-keys --user-name "$user" \
    --query "AccessKeyMetadata[?CreateDate>=\`[INCIDENT_START_DATE]\`]"
done

# Roles con trust policy modificada en la ventana
aws iam list-roles | jq -r '.Roles[].RoleName' | while read role; do
  last_used=$(aws iam get-role --role-name "$role" --query 'Role.RoleLastUsed.LastUsedDate' --output text 2>/dev/null)
  echo "$role: last used $last_used"
done | grep "2026-05"
```

**C. Si el atacante exfiltró credenciales temporales del rol, ya pueden estar afuera.**

Cuando una identidad asume un rol, recibe `AccessKeyId`, `SecretAccessKey`, y `SessionToken`. Si el atacante exfiltró estas credenciales, las puede usar desde cualquier lugar mientras no expiren. La revocación de sesiones (paso B del Containment) las invalida.

**D. Buscar persistence en otros recursos.**

- **Lambda functions** con triggers de EventBridge que mantienen acceso.
- **CloudFormation stacks** creados desde el compromise.
- **EventBridge rules** que disparan acciones inesperadas.
- **AWS Config remediation actions** modificadas para no remediar.

### 4. Recovery

**A. Restaurar la trust policy del rol si era legítimo.**

Si el rol tenía un uso legítimo y la trust policy original estaba bien configurada (con ExternalId, Condition correcta, Principal específico):

```bash
# Validar que el contenido del backup es lo que esperás
cat trust-policy-backup.json

# Restaurar
aws iam update-assume-role-policy \
  --role-name $ROLE_NAME \
  --policy-document file://trust-policy-backup.json
```

**B. Si la trust policy estaba mal configurada, rediseñarla.**

Patrón seguro para cross-account roles:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Principal": {
      "AWS": "arn:aws:iam::[TRUSTED_ACCOUNT]:role/[SPECIFIC_ROLE]"
    },
    "Action": "sts:AssumeRole",
    "Condition": {
      "StringEquals": {
        "sts:ExternalId": "[STRONG_RANDOM_STRING_AT_LEAST_32_CHARS]"
      },
      "IpAddress": {
        "aws:SourceIp": ["[CIDR_DE_LA_CUENTA_TRUSTED]"]
      }
    }
  }]
}
```

Reglas:

1. **Principal específico**, no `*` ni `:root`.
2. **ExternalId obligatorio** para integrations de terceros.
3. **Condition de SourceIp o SourceVpce** si conocés el origen.
4. **Permisos del rol mínimos** (no `AdministratorAccess` para integrations).

**C. Comunicación.**

- Al equipo dueño del rol.
- Al equipo de SecOps.
- Si fue una cuenta externa de partner, escalada con ellos.

### 5. Post-mortem (1 semana)

Énfasis en:

1. **¿De dónde vino la trust policy original?** ¿Quién la creó? ¿Hubo PR review? ¿Por qué pasó?
2. **¿Cuánto tiempo estuvo abierto el path?** Diff entre creación del rol y detección del abuse.
3. **¿La cuenta source es legítima?** Si es un vendor con relación contractual, evaluar madurez de su lado.
4. **Action items.**
   - SCP que bloquea trust policies con `Principal: "AWS": "*"` o sin Condition.
   - IAM Access Analyzer habilitado en TODAS las cuentas.
   - PR review obligatorio para cambios a trust policies.
   - Inventory de cross-account roles documentado y revisado trimestralmente.

## Anti-patterns

- ❌ **Mantener trust policies con `"Principal": "AWS": "*"`.** Sin Condition, cualquier cuenta del mundo puede asumir.
- ❌ **ExternalId débil o ausente.** Para integrations de terceros, ExternalId es la única defensa contra confused deputy.
- ❌ **No revisar quién asume el rol regularmente.** Roles con trust hacia cuentas que ya no son partners.
- ❌ **Asumir que cuentas internas de la Organization son confiables.** Si una de tus cuentas dev se compromete, el atacante puede pivotar a prod vía cross-account roles mal configurados.

## Automatización

### Fase 1: Manual

Humano sigue el playbook.

### Fase 2: Asistido

Script que toma un rol y emite reporte de uso cross-account:

```bash
./scripts/cross-account-audit.sh [ROLE_NAME] --days 30
# Output: cuentas source, identidades, frecuencia, acciones realizadas
```

### Fase 3: Semi-automático

EventBridge sobre IAM Access Analyzer findings de cross-account:

```
Trigger: Access Analyzer finding (external access)
   ↓
Lambda 1: Validar si el finding está en allowlist de partners conocidos
   ↓
Lambda 2: Si NO está en allowlist, snapshot de la trust policy
   ↓
Lambda 3: Notificar on-call con detalles
   ↓
Human: investiga, decide allowlist o eradication
```

### Fase 4: Automático

No recomendado. La distinción entre "vendor legítimo con configuración insegura" y "atacante" requiere humano.

## Métricas

- **Cross-account roles totales por cuenta**: si crece sin control, problema de inventory.
- **Roles con `Principal: "*"` o sin Condition**: debería ser cero.
- **MTTD de access pattern anómalo**: tiempo entre primer abuse y detección.
- **% de cross-account roles con ExternalId**: para integrations externas, debe ser 100%.

## Recursos

- [IAM Access Analyzer external access](https://docs.aws.amazon.com/IAM/latest/UserGuide/access-analyzer-findings.html)
- [Confused Deputy problem](https://docs.aws.amazon.com/IAM/latest/UserGuide/confused-deputy.html)
- [AWS cross-account role best practices](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_roles_create_for-user_externalid.html)
- [Cloudfox cross-account discovery](https://github.com/BishopFox/cloudfox)
