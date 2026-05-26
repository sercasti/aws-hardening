# Playbook 08: Exfiltración de data

> El peor de los escenarios: data salió de tu perímetro. Puede ser S3 bulk download, RDS snapshot copy a otra cuenta, EBS volume share público, secretos en logs. Este playbook te ayuda a contener, medir el alcance, y manejar la crisis.

## Trigger

- **GuardDuty finding** `Exfiltration:S3/AnomalousBehavior` o `Exfiltration:S3/MaliciousIPCaller`.
- **GuardDuty finding** `Stealth:IAMUser/CloudTrailLoggingDisabled` (atacante intenta tapar exfil).
- **Macie finding** de objetos sensibles accedidos por identidades inesperadas.
- **VPC Flow Logs anomaly**: outbound transfer masivo a IPs externas.
- **CloudTrail event** `CopyDBSnapshot`, `ModifyDBSnapshotAttribute`, `ModifySnapshotAttribute` con target en otra cuenta.
- Reporte externo: cliente, vendor, o threat intel reporta que ven tu data afuera.

## Severity

**Critical por default.** No hay versión "low" de exfil confirmada.

Subdivisiones:

- **Critical+**: PII de clientes, financial data, secretos de producción.
- **Critical**: data interna sensible (códigos fuente, schemas, configs).
- **High**: data no sensible pero confidencial (planes internos, documentos).

## SLA

- **Detection a Containment**: 30 minutos.
- **Containment a comms inicial**: 1 hora (legal, exec, CISO).
- **Eradication**: 8 horas.
- **Customer notification (si aplica)**: 24 a 72 horas dependiendo de jurisdicción.
- **Post-mortem**: 1 semana, pero el regulatory response puede extenderse meses.

## Pasos

### 1. Triage (10 minutos)

**A. Confirmar el evento de exfil.**

Tres preguntas para responder:

1. **¿Qué se copió/transferió?**
2. **¿A dónde?**
3. **¿Cuándo empezó?**

```bash
# Caso S3
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=GetObject \
  --start-time '[INCIDENT_START]' \
  --max-items 1000 \
  > exfil-s3.json

# Cantidad de objetos por bucket
jq '.Events[] | .Resources[] | select(.ResourceType == "AWS::S3::Object") | .ResourceName' exfil-s3.json \
  | awk -F/ '{print $1}' | sort | uniq -c | sort -rn

# Identidad que hizo los GetObject
jq '.Events[] | .Username' exfil-s3.json | sort | uniq -c | sort -rn
```

```bash
# Caso RDS snapshot
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ModifyDBSnapshotAttribute \
  --start-time '[INCIDENT_START]' \
  --max-items 100 | \
  jq '.Events[] | {Time: .EventTime, User: .Username, Snapshot: .Resources[].ResourceName, Params: .RequestParameters}'
```

```bash
# Caso EBS snapshot
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=ModifySnapshotAttribute \
  --start-time '[INCIDENT_START]' \
  --max-items 100
```

```bash
# Caso VPC outbound
# Si tenés Athena sobre VPC Flow Logs
SELECT
  srcaddr,
  dstaddr,
  SUM(bytes) as bytes_out
FROM vpc_flow_logs
WHERE start_time >= '[INCIDENT_START]'
  AND action = 'ACCEPT'
  AND NOT regexp_like(dstaddr, '^10\.|^172\.|^192\.168\.')
GROUP BY srcaddr, dstaddr
HAVING SUM(bytes) > 1000000000
ORDER BY bytes_out DESC;
```

**B. Cuantificar el volumen.**

Esto es clave para legal/comms. No es lo mismo "1 archivo" que "1TB".

```bash
# Bytes totales transferidos (approximación)
jq '[.Events[].AdditionalEventData.bytesTransferredOut // 0] | add' exfil-s3.json
```

### 2. Containment (30 minutos)

**A. Cortar la identidad responsable.**

Si fue una IAM identity:

```bash
# IAM user: deshabilitar y revocar
aws iam update-access-key --user-name [USER] --access-key-id [KEY] --status Inactive
aws iam put-user-policy \
  --user-name [USER] \
  --policy-name AWSRevokeOlderSessions \
  --policy-document file://revoke-sessions.json
```

Si fue un rol:

```bash
# Trust policy temporal que deniega
aws iam update-assume-role-policy --role-name [ROLE] \
  --policy-document '{"Version":"2012-10-17","Statement":[{"Effect":"Deny","Principal":"*","Action":"sts:AssumeRole"}]}'

# Revocar sesiones
aws iam put-role-policy --role-name [ROLE] \
  --policy-name AWSRevokeOlderSessions \
  --policy-document file://revoke-sessions.json
```

**B. Cortar el path de egress.**

Si el atacante está activamente copiando:

```bash
# Aplicar S3 bucket policy temporal que deny GetObject
cat > deny-temp.json <<EOF
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Deny",
    "Principal": "*",
    "Action": "s3:GetObject",
    "Resource": "arn:aws:s3:::[BUCKET]/*",
    "Condition": {
      "StringNotEquals": {
        "aws:PrincipalArn": "[ALLOWLIST_ARN_OF_LEGITIMATE_APPS]"
      }
    }
  }]
}
EOF

aws s3api put-bucket-policy --bucket [BUCKET] --policy file://deny-temp.json
```

**C. Si el caso es snapshot compartido a otra cuenta, revocar el share.**

```bash
# RDS snapshot
aws rds modify-db-snapshot-attribute \
  --db-snapshot-identifier [SNAPSHOT_ID] \
  --attribute-name restore \
  --values-to-remove [ACCOUNT_ID_ATACANTE]

# EBS snapshot
aws ec2 modify-snapshot-attribute \
  --snapshot-id [SNAPSHOT_ID] \
  --attribute createVolumePermission \
  --operation-type remove \
  --user-ids [ACCOUNT_ID_ATACANTE]
```

**Nota:** si el atacante ya copió el snapshot a su cuenta, revocar el share NO recupera la data. El daño está hecho. Pero impide que más data salga si quedaron snapshots adicionales compartidos.

### 3. Investigación profunda (2 a 6 horas)

**A. Reconstruir la timeline exacta.**

Documentar:

- **T0**: primera acción anómala (puede ser días antes del trigger).
- **T1**: primera exfil.
- **T2**: pico de exfil.
- **T3**: detección.
- **T4**: containment aplicado.

```bash
# Buscar el primer uso anómalo de la identidad
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=Username,AttributeValue=[IDENTITY] \
  --start-time '2026-05-01T00:00:00Z' \
  --max-items 5000 \
  > full-timeline.json

# Visualizar por hora
jq '.Events[] | .EventTime' full-timeline.json | cut -d'T' -f1 | sort | uniq -c
```

**B. Determinar el alcance preciso de la data.**

Si fueron S3 GetObjects, lista exhaustiva:

```bash
jq '.Events[] | .Resources[] | select(.ResourceType == "AWS::S3::Object") | .ResourceName' exfil-s3.json | sort -u > exfiltrated-objects.txt
wc -l exfiltrated-objects.txt
```

Por cada objeto, ¿qué contiene? Si tenés Macie corriendo o etiquetas de classification, esto es rápido. Si no, sample 10 objetos y clasificá manualmente:

- PII?
- Credenciales?
- Código fuente?
- Documentos internos?

**C. Identificar el vector inicial.**

¿Cómo entró el atacante? Posibilidades comunes:

1. **Credencial leak (Playbook 01).** AWS key en GitHub público.
2. **Phishing a un usuario** con consola access.
3. **Vulnerabilidad de aplicación** (SSRF que robó credenciales del IMDS).
4. **Supply chain attack** (paquete npm comprometido en build).
5. **Cuenta de partner comprometida** (cross-account, Playbook 07).

Si todavía no sabés el vector, no podés cerrar el incidente.

**D. Buscar otras identidades/recursos comprometidos.**

El atacante rara vez se queda en una sola identidad. Buscar:

```bash
# IPs que se conectaron en el período
aws cloudtrail lookup-events \
  --start-time '[INCIDENT_START]' \
  --max-items 5000 \
  | jq '.Events[] | .SourceIPAddress' | sort | uniq -c | sort -rn | head -20

# Cruzar con la IP del atacante: ¿qué otras identidades usaron esa IP?
ATTACKER_IP="[IP]"
aws cloudtrail lookup-events \
  --start-time '[INCIDENT_START]' \
  --max-items 5000 \
  | jq ".Events[] | select(.SourceIPAddress == \"$ATTACKER_IP\") | .Username" | sort -u
```

### 4. Comms y legal (paralelo a investigación)

**A. Notificación interna inmediata.**

- CISO/Security lead.
- Legal counsel.
- CEO/exec sponsor.
- Comms team.

**Reglas:**

- No usar email ni chat normal para discutir detalles del breach (puede estar comprometido). Usar canal seguro (Signal grupal, llamada).
- No publicar nada externamente hasta que legal apruebe.
- No prometer timelines de comms a clientes hasta tener datos sólidos.

**B. Customer/regulator notification.**

Dependiendo de la jurisdicción y data type:

| Jurisdicción | Ley | Plazo |
|---|---|---|
| EU | GDPR | 72 horas |
| Brasil | LGPD | "razonable", interpretado 72 horas |
| California | CCPA | "sin demora indebida" |
| US federal (varias industrias) | HIPAA, GLBA, SEC 4-day rule | variable |
| Chile | Ley 21.719 (2026) | 72 horas datos sensibles |
| Argentina | Ley 25.326 + nueva normativa AAIP | variable |

**Reglas:**

- Legal define el contenido exacto de la notificación.
- No notificar sin datos confirmados (rumores generan caos).
- La notificación debe ser específica: qué data, cuántos afectados, qué pueden hacer ellos.

**C. Documentar todo.**

Cada acción tomada, con timestamp, autor, comando ejecutado, resultado. Va a ser requerido por:

- Auditores internos.
- Reguladores.
- Posibles litigios.
- Insurance claim si tenés cyber insurance.

### 5. Eradication y Recovery

**A. Eliminar al atacante completamente.**

- Identidades comprometidas: deshabilitadas/eliminadas.
- Backdoors: encontrados y eliminados (ver Playbook 03 y 04).
- Cuentas/recursos no autorizados creados por el atacante: eliminados.

**B. Rotar TODO secreto que pudo haber sido visto.**

Aunque no haya evidencia directa, rotación preventiva:

- Database passwords.
- API keys de terceros.
- KMS keys (rotación si están en CMKs).
- Certificados.
- Application secrets en Secrets Manager / Parameter Store.

**C. Cerrar el vector inicial.**

- Si fue credencial leak: revisar todos los repos por más leaks, rotar todas las keys de servicio.
- Si fue SSRF: parche de la app, IMDSv2 enforcement.
- Si fue phishing: review de access patterns, MFA donde no había.

### 6. Post-mortem (1 semana, pero continúa)

Para exfil, el post-mortem es más profundo que otros:

1. **Cronología completa.** Cada minuto importante.
2. **Data afectada.** Lista de campos/registros con clasificación.
3. **Identidades involucradas.** Comprometidas y atacante.
4. **Vector inicial.** Causa raíz exacta.
5. **Por qué tardamos en detectar.** Detection coverage gaps.
6. **Acciones tomadas.** Y por qué cada una.
7. **Action items.**
   - **Inmediatos**: lo que rompió, parchar.
   - **Mediano plazo**: detection mejorada.
   - **Largo plazo**: cambios arquitectónicos.

Y separadamente, **regulatory action items**:

- Notificación a reguladores cumplida.
- Comunicación a usuarios cumplida.
- Reporte forensic externo (si fue requerido).
- Mejoras al programa de seguridad documentadas para auditores.

## Anti-patterns

- ❌ **Esperar hasta tener "todos los datos" para notificar.** Las leyes tienen plazos. Notificá con lo que tenés, actualizá después.
- ❌ **No traer legal temprano.** Cada decisión tiene implicaciones legales. Legal debe estar en la sala desde la hora 1.
- ❌ **Comunicar internamente sin canal seguro.** El atacante puede estar leyendo tu Slack.
- ❌ **Borrar evidencia "para que no se vea mal".** Es delito en muchas jurisdicciones y multiplica el daño.
- ❌ **Asumir que como cortaste el acceso, no van a usar la data afuera.** La data exfiltrada ya está afuera. Tu trabajo es minimizar el daño futuro.

## Automatización

### Fase 1: Manual

Humano sigue el playbook.

### Fase 2: Asistido

Scripts que aceleran investigación:

```bash
./scripts/exfil-timeline.sh [IDENTITY] --start [DATE]
# Output: timeline de acciones, IPs, recursos accedidos
```

### Fase 3: Semi-automático

EventBridge sobre GuardDuty Exfiltration findings:

```
Trigger: GuardDuty Exfiltration finding
   ↓
Lambda 1: Snapshot del estado actual (CloudTrail dump, identidad usada)
   ↓
Lambda 2: Aplicar Deny temporal a la identidad
   ↓
Lambda 3: Notificar on-call con Sev1 (page)
   ↓
Lambda 4: Iniciar incident war room (Slack channel privado)
   ↓
Human: investiga full
```

### Fase 4: Automático

NO recomendado. Las decisiones de comms, legal, y customer notification requieren humanos con autoridad.

## Métricas

- **MTTD**: cuánto tarda en detectarse el patrón de exfil.
- **MTTC**: cuánto tarda el containment.
- **Records affected**: registros únicos exfiltrados.
- **Notification compliance**: % de notificaciones dentro del plazo legal.
- **Recurrence**: ¿el mismo vector se vuelve a usar?

## Recursos

- [GuardDuty Exfiltration findings](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-s3.html)
- [Macie sensitive data discovery](https://docs.aws.amazon.com/macie/latest/user/discovery-overview.html)
- [GDPR breach notification](https://gdpr.eu/article-33-notification-of-a-personal-data-breach/)
- [LGPD breach notification (Brasil)](https://www.gov.br/anpd/pt-br)
- [Ley 21.719 Chile (en vigor 2026)](https://www.bcn.cl/leychile/navegar?idNorma=1206353)
- [AWS Customer Incident Response Team](https://aws.amazon.com/security/customer-incident-response/)
