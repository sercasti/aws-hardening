# Playbook 03: Escalación de privilegios IAM

> Detectaste que una identidad (usuario IAM o rol) escaló de permisos limitados a permisos elevados. Puede ser un atacante explotando un path de escalación, o un developer haciendo cambios sin review. Este playbook contiene la situación rápido.

## Trigger

- **GuardDuty finding** `Discovery:IAMUser/AnomalousBehavior` o `CredentialAccess:IAMUser/AnomalousBehavior`.
- **CloudTrail event** `AttachUserPolicy`, `PutUserPolicy`, `CreatePolicyVersion`, `UpdateAssumeRolePolicy` desde una identidad inesperada.
- **IAM Access Analyzer finding** sobre cross-account access no aprobado.
- Reporte del PR review prompt detectando una policy peligrosa post-merge.
- Detección manual durante revisión rutinaria.

## Severity

- **Critical** si la identidad escaló a `*:*` o policies equivalentes (PowerUserAccess, AdministratorAccess).
- **High** si la identidad sumó permisos sensibles (iam:*, organizations:*, kms:*, ec2:*).
- **Medium** si la escalación es a permisos limitados (ej. sumó s3:GetObject en buckets específicos).

## SLA

- **Detection a Containment**: 30 minutos.
- **Containment a Eradication**: 2 horas.
- **Recovery**: 4 horas.
- **Post-mortem**: 1 semana.

## Pasos

### 1. Triage (5 minutos)

**Confirmar la escalación.**

```bash
# Listar las policies actuales de la identidad
aws iam list-attached-user-policies --user-name [USERNAME]
aws iam list-user-policies --user-name [USERNAME]
aws iam list-groups-for-user --user-name [USERNAME]

# Para un rol:
aws iam list-attached-role-policies --role-name [ROLENAME]
aws iam list-role-policies --role-name [ROLENAME]

# Si la identidad asume otros roles vía trust policy:
aws iam get-role --role-name [ROLENAME] --query 'Role.AssumeRolePolicyDocument'
```

**Comparar con la última snapshot conocida.**

```bash
# Si tenés snapshots regulares en S3 (Nivel 2-3):
aws s3 cp s3://[YOUR_AUDIT_BUCKET]/iam-snapshots/[YESTERDAY].json -

# Diff manual con el estado actual
diff <(aws iam get-account-authorization-details) <(cat yesterday.json) | head -100
```

**Si tu organización todavía no tiene snapshots IAM:**

Usá CloudTrail para reconstruir:

```bash
aws cloudtrail lookup-events \
  --lookup-attributes \
  AttributeKey=ResourceName,AttributeValue=[USERNAME or ROLENAME] \
  --start-time '2026-05-20T00:00:00Z' \
  --max-items 100 \
  | jq '.Events[] | select(.EventName | startswith("Attach") or startswith("Put") or startswith("Update") or startswith("Create"))'
```

**Decidir:** ¿Es escalación legítima (un cambio aprobado) o anómala?

- **Legítima:** existe ticket/PR de cambio. Cerrar como FP, pero ajustar el detection threshold.
- **Anómala:** no hay ticket/PR. Continuar a containment.

### 2. Containment (15 minutos)

**A. Revertir las policies recientes a su estado previo.**

```bash
# Identificar qué policies se agregaron en las últimas 24 horas
NEW_POLICIES=$(aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=[USERNAME] \
  --start-time '2026-05-25T00:00:00Z' \
  | jq -r '.Events[] | select(.EventName == "AttachUserPolicy") | .Resources[].ResourceName' | sort -u)

# Desadjuntar cada una
for policy in $NEW_POLICIES; do
  aws iam detach-user-policy --user-name [USERNAME] --policy-arn "$policy"
done
```

**B. Si la identidad es la del usuario que ejecutó la escalación (auto-escalación):**

Asumir que la credencial está comprometida. Activar [Playbook 01](./01-leaked-credentials.md).

**C. Si la identidad es un rol asumido por un servicio:**

- Identificar qué servicio (Lambda, EC2, Batch, etc.).
- Si fue un Lambda, examinar el código que assumió el rol.
- Si fue una EC2, isolar la instancia (network ACL para bloquear egress).

**D. Bloquear el path de escalación.**

Si el path fue, por ejemplo, "iam:PassRole + lambda:CreateFunction":

- Identificar la policy que permite ese path.
- Reducir su scope (Resource más restrictivo, Condition más estricto, NotResource para excluir patrones peligrosos).
- Aplicar la corrección.

### 3. Eradication (30 minutos)

**A. Inventariar qué hizo la identidad con sus privilegios elevados.**

```bash
# CloudTrail lookup desde el momento de la escalación
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=[USERNAME] \
  --start-time '[TIMESTAMP_OF_ESCALATION]' \
  --max-items 1000 \
  > escalation-activity.json

# Filtrar acciones que solo eran posibles después de la escalación
jq '.Events[] | select(.EventName != "Get*" and .EventName != "List*" and .EventName != "Describe*")' escalation-activity.json
```

**B. Para cada acción del atacante (si lo es), revertir.**

Lista típica de acciones a revertir:

- **Recursos creados**: terminate después de evidencia capturada.
- **Backdoors plantados**: detectar nuevos IAM users/keys/roles, eliminar.
- **CloudTrail tampering**: si se modificó logging, restaurar.
- **SCPs modificadas**: revert al estado anterior.

**C. Search para persistence mechanisms.**

Atacantes sofisticados dejan persistence. Buscar:

```bash
# Usuarios IAM creados recientemente
aws iam list-users --query 'Users[?CreateDate>=`2026-05-25`]'

# Access keys creadas recientemente
aws iam list-users | jq -r '.Users[].UserName' | while read user; do
  aws iam list-access-keys --user-name "$user" \
    --query "AccessKeyMetadata[?CreateDate>=\`2026-05-25\`]"
done

# Trust policies modificadas para permitir nuevas identidades
aws iam list-roles | jq -r '.Roles[] | select(.AssumeRolePolicyDocument | contains("AWS"))' \
  | jq '.AssumeRolePolicyDocument.Statement[]' | grep -i Principal

# Cross-account roles nuevos
aws iam list-roles | jq -r '.Roles[] | select(.AssumeRolePolicyDocument | contains("arn:aws:iam"))' \
  | grep -v "$(aws sts get-caller-identity --query Account --output text)"
```

### 4. Recovery

**A. Restaurar permisos legítimos del usuario.**

Si el usuario es legítimo y sus permisos previos eran correctos:

- Re-attach las policies originales.
- Validar que puede hacer su trabajo.

**B. Comunicación.**

- Al usuario (si era legítimo, explicar qué se cambió y por qué).
- Al equipo de SRE/SecOps (post en #security-incident).
- Al management si la severidad fue critical.

**C. Si hay sospecha de compromise externo:**

- Activar full incident response (más allá de IAM).
- Considerar contractar IR externo (CrowdStrike, Mandiant, etc.) si la escalación fue extensa.

### 5. Post-mortem (1 semana)

Foco en:

1. **Path de escalación.** ¿Cuál fue exactamente el camino? Documentar para futuros.
2. **¿Por qué existía ese path?** Configuración legacy, falta de SCPs, IAM Access Analyzer no usado.
3. **¿Por qué no se detectó antes?** ¿GuardDuty estaba habilitado? ¿Por qué no triggereó?
4. **Action items.**
   - Bloquear ese path con SCP.
   - Habilitar GuardDuty si no estaba.
   - Implementar Access Analyzer si no estaba.
   - Consider IAM session policies para roles sensibles.
   - Snapshots regulares de IAM para detectar drift.

## Anti-patterns

- ❌ **Revertir cambios sin capturar evidencia.** Si fue un atacante, perdés trazabilidad de lo que hizo.
- ❌ **Asumir que es FP "porque es nuestro developer".** Quizás el developer está comprometido. Investigá.
- ❌ **Detach todas las policies "para estar seguros".** El usuario va a llamar furioso porque no puede trabajar. Revertí a estado conocido, no a vacío.
- ❌ **No buscar persistence.** Si revertís solo la escalación visible pero el atacante creó backdoors, vuelve mañana.

## Automatización

### Fase 1: Manual

Humano sigue el playbook.

### Fase 2: Asistido

Script que toma `USERNAME` y genera reporte de actividad:

```bash
./scripts/iam-activity-report.sh [USERNAME] --hours 24
# Output: acciones recientes, policies modificadas, recursos creados/modificados
```

### Fase 3: Semi-automático

EventBridge rule sobre `AttachUserPolicy` con condition (anomalía: usuario rara vez modificado en últimos 90 días):

```
Trigger: CloudTrail event
   ↓
Lambda 1: Check si la modificación fue aprobada (via PR/ticket)
   ↓
Lambda 2: Si NO aprobada, snapshot del estado actual
   ↓
Lambda 3: Notificar on-call con resumen
   ↓
Human: investiga, decide revertir o aprobar
```

### Fase 4: Automático

Solo recomendado en cuentas no críticas (sandbox). En prod, mantener humano en el loop.

## Métricas

- **MTTD**: tiempo entre escalación y detección.
- **MTTC**: tiempo entre detección y contención.
- **Number of paths blocked per quarter**: progreso del programa.
- **False positive rate**: si >30%, el detection es inaccionable.

## Recursos

- [Pacu (AWS exploitation framework)](https://github.com/RhinoSecurityLabs/pacu) - útil para entender qué busca un atacante.
- [IAM Access Analyzer](https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html)
- [Cloudfox](https://github.com/BishopFox/cloudfox) - tool de red team para encontrar paths.
- [AWS Security Maturity Model: IAM section](https://maturitymodel.security.aws.dev)
