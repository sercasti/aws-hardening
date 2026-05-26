# Playbook 01: Credenciales filtradas

> Una credencial AWS apareció en GitHub, en un repo público, en un log de CI, en un screenshot, en Pastebin, o donde sea que no debería. Es el incident más común y el que tiene playbook más maduro de la industria.

## Trigger

Cualquiera de estos eventos:

- **AWS Health Dashboard** te notifica que detectaron una credencial filtrada (servicio que AWS provee gratis).
- **GitHub Push Protection** bloquea un commit con credenciales.
- **Truffhog/git-secrets/Gitleaks** en tu CI pipeline detecta el secret.
- Un reporte externo (un usuario te dice "vi tu key en Stack Overflow").
- **GuardDuty finding** `UnauthorizedAccess:IAMUser/InstanceCredentialExfiltration.OutsideAWS` (señal post-leak).

## Severity

**Critical** por default. Razones para bajar a high:

- La credencial es de un service account en sandbox con scope limitado.
- La credencial ya estaba rotada antes del leak (señal de proceso maduro).
- La credencial nunca fue usada (creada y filtrada sin haberse activado).

## SLA

- **Detection a Containment**: 30 minutos.
- **Containment a Eradication**: 2 horas.
- **Eradication a Recovery**: 4 horas.
- **Post-mortem**: 1 semana.

## Pasos

### 1. Triage (5 minutos)

**Confirmá que la credencial es real y está activa.**

```bash
# Reemplazá ACCESS_KEY_ID con el ID filtrado
aws iam get-access-key-last-used --access-key-id AKIAEXAMPLE...

# Output relevante:
# - UserName: a quién pertenece la key
# - LastUsedDate: cuándo se usó por última vez
# - Region: dónde se usó
```

**Si la key NO existe en tu cuenta:** Probablemente es FP. Documentá y cerrá. (Pero validá que no sea de otra cuenta de tu organización.)

**Si la key existe y `LastUsedDate` es del pasado lejano (>30 días):** Es real pero menos urgente. Continuá a Containment.

**Si la key existe y `LastUsedDate` es reciente (<24 horas):** Bandera roja. Es posible que el atacante ya esté usándola. Acelerá el playbook.

### 2. Containment (15 minutos)

**A. Aislar la credencial sin destruirla todavía.**

```bash
# Desactivar la key, NO borrarla aún (preservamos evidencia)
aws iam update-access-key \
  --access-key-id AKIAEXAMPLE... \
  --status Inactive \
  --user-name [USERNAME]
```

Verificación:

```bash
aws iam list-access-keys --user-name [USERNAME] \
  --query 'AccessKeyMetadata[?AccessKeyId==`AKIAEXAMPLE...`].Status'
# Esperado: ["Inactive"]
```

**B. Revocar sesiones activas que esa key haya iniciado.**

```bash
# Para usuarios IAM, revocar todas las sesiones temporales activas
aws iam put-user-policy \
  --user-name [USERNAME] \
  --policy-name DenyAllUntilFurther \
  --policy-document file://deny-all.json

# Contenido de deny-all.json:
# {
#   "Version": "2012-10-17",
#   "Statement": [
#     {
#       "Effect": "Deny",
#       "Action": "*",
#       "Resource": "*",
#       "Condition": {
#         "DateLessThan": {
#           "aws:TokenIssueTime": "2026-05-26T15:00:00Z"  # ahora
#         }
#       }
#     }
#   ]
# }
```

Esto invalida cualquier sesión temporal que ya estaba activa, sin desactivar permisos futuros legítimos.

**C. Identificar el alcance: qué pudo hacer el atacante con esta key.**

```bash
# Listar las policies del usuario
aws iam list-attached-user-policies --user-name [USERNAME]
aws iam list-user-policies --user-name [USERNAME]
aws iam list-groups-for-user --user-name [USERNAME]

# Obtener policies efectivas
aws iam simulate-principal-policy \
  --policy-source-arn arn:aws:iam::ACCOUNT:user/USERNAME \
  --action-names "s3:*" "iam:*" "ec2:*"
```

### 3. Eradication (30 minutos)

**A. Inventariar qué hizo la credencial.**

```bash
# CloudTrail lookup para esa access key, últimas 24 horas
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=AccessKeyId,AttributeValue=AKIAEXAMPLE... \
  --start-time '2026-05-25T00:00:00Z' \
  --max-items 1000 \
  > leaked-key-activity.json

# Filtrar acciones interesantes
jq '.Events[] | select(.EventName != "ListBuckets" and .EventName != "Get*")' leaked-key-activity.json
```

Mirá específicamente:

- Creación de recursos nuevos (EC2 instances, RDS, IAM users).
- Uso de servicios cross-account (`sts:AssumeRole` a otras cuentas).
- Modificación de logging (`cloudtrail:Stop*`, `s3:PutBucketLogging`).
- Lectura masiva de S3 (`s3:GetObject` en buckets sensibles).
- Cambios en IAM (`iam:CreateUser`, `iam:AttachUserPolicy`).

**B. Si hay actividad sospechosa, deshacer cada cambio.**

Para cada acción del atacante:

- **EC2 instances creadas**: terminate después de snapshot para forensics.
- **IAM users/keys creados**: delete después de captura del manifest.
- **Buckets creados**: delete (probablemente para stash de datos).
- **Roles modificados**: revert a configuración previa (CloudTrail tiene el "before" state).

**C. Borrar la access key comprometida (después de captura).**

```bash
# Borrarla solo después de capturar toda la evidencia
aws iam delete-access-key \
  --access-key-id AKIAEXAMPLE... \
  --user-name [USERNAME]
```

**D. Generar credenciales nuevas si el usuario las necesita.**

```bash
aws iam create-access-key --user-name [USERNAME]
# Guardarlas en Secrets Manager o entregarlas vía canal seguro al user
```

### 4. Recovery (variable, 1 a 4 horas)

**A. Restaurar workloads legítimos que usaban la credencial vieja.**

- Identificar qué aplicación/script usaba la key (típicamente lo sabe el dueño del user).
- Reemplazar la credencial vieja con la nueva en Secrets Manager.
- Reiniciar los servicios afectados.
- Validar que vuelven a funcionar.

**B. Confirmar que ya no hay actividad sospechosa.**

Volvé a correr el query de CloudTrail. La key vieja ya no debería aparecer. Si aparece, alguien siguió intentando usarla (cosa esperable). Si las keys NUEVAS aparecen en lugares inesperados, sigue habiendo compromiso.

**C. Comunicación.**

- Al user dueño: cómo, cuándo, qué se hizo, qué necesita hacer él.
- Al equipo: post en #security-incident con resumen.
- Si la key estaba en un repo público y la org tiene compromisos de transparencia con clientes: notificación a stakeholders.

### 5. Post-mortem (1 semana)

Doc de retro con estos puntos mínimos:

1. **Timeline.** Cada evento con timestamp UTC.
2. **Root cause.** Por qué la key terminó pública (típicamente: hardcoded, .env committeado, screenshot, etc.).
3. **Detection.** ¿Cuánto tardamos en detectar? ¿Fue por nuestro tooling o por uno externo?
4. **Response time.** ¿Cumplimos el SLA? Si no, por qué.
5. **Impact.** ¿Hubo data exfil? ¿Costo de los recursos creados por el atacante?
6. **Action items.**
   - Técnicos: ¿qué tooling falta para prevenir esto?
   - Procesales: ¿qué change en process evita el escenario?
   - Capacitación: ¿quién más necesita saber esto para no repetir?

## Anti-patterns

- ❌ **Borrar la access key sin desactivarla primero.** Pierdes la trazabilidad de cuándo se usó por última vez.
- ❌ **Rotar la key sin haber identificado el scope.** Si todavía no sabés qué hizo el atacante, no la rotes (puede tener una sesión activa).
- ❌ **No avisarle al user dueño.** Genera frustración y el próximo leak es de él mismo, porque está enojado.
- ❌ **Limpiar evidencia "para que se vea ordenado".** Te quedas sin material para el post-mortem.
- ❌ **Post-mortem con foco en "quién filtró la key".** Foco siempre en "cómo evitamos que vuelva a pasar", no en culpa.

## Automatización

Este playbook se automatiza en 3 fases:

### Fase 1: Manual (Nivel 1-2)

Todo lo de arriba lo hace un humano. Bien documentado, practicado en game day.

### Fase 2: Asistido (Nivel 2-3)

Script que toma el `ACCESS_KEY_ID` como input y ejecuta los queries de triage automáticamente:

```bash
./scripts/triage-leaked-key.sh AKIAEXAMPLE...
# Output: state, owner, last used, scope, actividad en últimas 24h
```

El humano lee el output y decide los siguientes pasos.

### Fase 3: Semi-automático (Nivel 3)

EventBridge rule + Step Function que reacciona automáticamente:

```
Trigger: AWS Health Dashboard event con tipo "AWS_RISK_CREDENTIALS_EXPOSED"
   ↓
Lambda 1: Identificar la key, captar metadata
   ↓
Lambda 2: Desactivar la key (NO borrar)
   ↓
Lambda 3: Query CloudTrail últimas 24h, generar reporte
   ↓
Lambda 4: Crear ticket en Jira con el reporte
   ↓
Lambda 5: Notificar al user dueño + on-call vía Slack
   ↓
Human: revisa reporte, decide eradication steps
```

Los steps de eradication (terminate de recursos, delete de usuarios creados por atacante) se mantienen manuales hasta Nivel 4.

### Fase 4: Automático (Nivel 4)

Step Function completa con todos los pasos, incluyendo eradication. Solo el post-mortem queda manual.

## Métricas

Track de incident en incident:

- **MTTD**: Tiempo entre el leak real y la detección.
- **MTTR**: Tiempo entre detección y containment completo.
- **Recurrence rate**: ¿Es el mismo user/equipo el que filtró keys repetidamente? Si sí, hay un gap de process/training en ese equipo.
- **Cost of incident**: Recursos creados por atacante + tiempo del equipo en responder.

## Recursos

- [AWS docs: Credenciales comprometidas](https://docs.aws.amazon.com/IAM/latest/UserGuide/id_credentials_compromised.html)
- [AWS Health Dashboard: AWS_RISK_CREDENTIALS_EXPOSED event](https://docs.aws.amazon.com/health/latest/ug/aws-health-concepts-terms.html)
- [GitHub Secret Scanning](https://docs.github.com/en/code-security/secret-scanning)
- [git-secrets](https://github.com/awslabs/git-secrets)
- [Truffhog](https://github.com/trufflesecurity/trufflehog)
