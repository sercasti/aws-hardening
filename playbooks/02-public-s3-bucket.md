# Playbook 02: S3 bucket público accidental

> Un bucket S3 se hizo público sin que nadie quisiera. Quizás un developer cambió ACL para hacer un test rápido, quizás un Terraform mal escrito flipped el block_public_access, quizás un ingreso del IDS detectó accesos no esperados. Este playbook minimiza la ventana de exposición.

## Trigger

- **GuardDuty finding** `Policy:S3/BucketAnonymousAccessGranted` o `Policy:S3/BucketPublicAccessGranted`.
- **AWS Config rule** que detecta buckets con `block_public_access` deshabilitado.
- **Macie finding** que indica data sensible accesible públicamente.
- Reporte humano (vio un screenshot, encontró un link compartido externamente).
- **CloudWatch alarm** sobre `NumberOfPublicBuckets` > 0 (custom metric).

## Severity

- **Critical** si el bucket contiene data clasificada como `sensitive`, PII, financial data, o credenciales.
- **High** si el contenido es desconocido (asumir lo peor hasta confirmar).
- **Medium** si el contenido es público intencional (assets web, documentación) y el "incident" es un FP.

## SLA

- **Detection a Containment**: 1 hora.
- **Containment a Eradication**: 4 horas.
- **Recovery**: variable.
- **Post-mortem**: 1 semana.

## Pasos

### 1. Triage (5 minutos)

**Confirmá que el bucket es público y qué contiene.**

```bash
# Verificar block public access del bucket
aws s3api get-public-access-block --bucket [BUCKET_NAME]

# Verificar policy del bucket
aws s3api get-bucket-policy --bucket [BUCKET_NAME] 2>/dev/null

# Verificar ACL del bucket
aws s3api get-bucket-acl --bucket [BUCKET_NAME]

# Listar contenido (primeros 20 archivos)
aws s3 ls s3://[BUCKET_NAME] --recursive --max-items 20
```

**Clasificá el contenido:**

- ¿Hay archivos con extensión sospechosa? (`.env`, `.key`, `.pem`, `.sql`, `*-backup*`, archivos sin extensión grandes)
- ¿Hay tags en el bucket que indiquen `data-classification=sensitive`?
- ¿Hay objetos con `Content-Type` que indica documents (PDF, XLS, DOC)?

**Si el contenido es claramente público intencional** (ej. bucket con tag `purpose=public-asset`, contiene solo imágenes/CSS/JS de un sitio):

- Cerrar como FP.
- Tag de exception en el bucket para futuros findings.
- Documentar en `exceptions.md` si todavía no estaba.

**Si NO es público intencional, o no estás seguro:** proceder a containment.

### 2. Containment (15 minutos)

**A. Bloquear acceso público inmediatamente.**

```bash
# Aplicar block public access al bucket
aws s3api put-public-access-block \
  --bucket [BUCKET_NAME] \
  --public-access-block-configuration \
  "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"
```

Verificación:

```bash
aws s3api get-public-access-block --bucket [BUCKET_NAME]
# Esperado: los 4 valores en true
```

**B. Si la policy del bucket tiene Allow con Principal "*", quitarla.**

```bash
# Capturar la policy actual primero (para evidencia)
aws s3api get-bucket-policy --bucket [BUCKET_NAME] > old-policy-evidence.json

# Borrar la policy
aws s3api delete-bucket-policy --bucket [BUCKET_NAME]
```

Si la policy tiene Allow legítimos mezclados con un Allow público, **NO** borres toda la policy. Editá y remové solo el Statement del Allow público.

**C. Si los objetos individuales tienen ACL `public-read`, quitarlos.**

```bash
# Listar objetos con ACL pública
aws s3api list-objects --bucket [BUCKET_NAME] --max-items 100 | \
  jq -r '.Contents[].Key' | while read key; do
    acl=$(aws s3api get-object-acl --bucket [BUCKET_NAME] --key "$key" \
      --query 'Grants[?Grantee.URI==`http://acs.amazonaws.com/groups/global/AllUsers`]')
    if [ "$acl" != "[]" ]; then
      echo "PUBLIC: $key"
    fi
  done

# Para cada objeto público, cambiar ACL a private
aws s3api put-object-acl --bucket [BUCKET_NAME] --key [KEY] --acl private
```

### 3. Eradication (30 minutos)

**A. Determinar quién hizo público el bucket.**

```bash
# CloudTrail lookup para acciones que afectan public access en este bucket
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=ResourceName,AttributeValue=[BUCKET_NAME] \
  --start-time '2026-05-20T00:00:00Z' \
  | jq '.Events[] | select(.EventName == "PutBucketAcl" or .EventName == "PutBucketPolicy" or .EventName == "DeletePublicAccessBlock" or .EventName == "PutPublicAccessBlock")'
```

Output relevante:

- `EventTime`: cuándo se hizo público.
- `Username`: quién (o qué service account) lo hizo.
- `SourceIPAddress`: desde dónde.
- `RequestParameters`: qué exactamente se modificó.

**B. Si la acción fue por un atacante (no por un usuario legítimo):**

- Activar [Playbook 01](./01-leaked-credentials.md) para la identidad usada.
- Validar que esa identidad no haya modificado otros buckets.

**C. Si la acción fue por un usuario legítimo (developer making a mistake):**

- Conversación con el developer sobre por qué pasó.
- Si hay un Terraform/CDK que generó esto, repararlo (`block_public_access` debería estar siempre en `true` en módulo base).
- Considerar agregar un SCP que bloquee `s3:PutPublicAccessBlock` con condition (Nivel 2-3).

**D. Determinar el alcance del leak.**

Si el bucket estuvo público por X horas, asumimos que:

- Bots scanners ya lo descubrieron y leyeron el contenido.
- El contenido puede estar copiado en sitios de leak (Pastebin, dark web, archive.org).
- Cualquier dato sensible debe considerarse comprometido.

Para data PII o credenciales:

- Notificación legal/compliance.
- Rotación de credenciales que estaban en el bucket.
- En jurisdicciones con leyes de notificación (GDPR, LGPD): clock empieza ahora.

### 4. Recovery

**Restaurar el bucket a estado operacional.**

Si era un bucket legítimo de aplicación interna:

- Aplicar el bucket policy correcta.
- Si hay servicios que lo consumían, validar que pueden seguir accediendo.
- Restaurar tags y configuración.

Si era un bucket que NO debería existir (creado por error):

- Mover el contenido a un bucket privado correcto.
- Borrar el bucket vacío.

### 5. Post-mortem (1 semana)

Particular énfasis en:

1. **Cómo se hizo público.** Causa exacta: ¿Terraform mal escrito? ACL manualmente cambiada? Política aplicada sin review?
2. **Por qué no se detectó antes.** ¿GuardDuty estaba habilitado en esa región? ¿Por qué pasó tiempo entre que se hizo público y la alerta?
3. **Qué data se expuso.** Lo más concreto posible. Si no se sabe, decirlo.
4. **Action items.**
   - Técnicos: ¿agregamos block public access a nivel cuenta? ¿SCP para evitar?
   - Procesales: ¿review obligatoria para PRs que tocan S3?
   - Compliance: ¿hace falta notificación regulatoria?

## Anti-patterns

- ❌ **Borrar todo el bucket en pánico.** Pérdida de evidencia y de data legítima.
- ❌ **Asumir que como nadie reportó nada, no se vio.** Bots scanners pasan cada hora.
- ❌ **Castigar al developer.** El process falló, no la persona. Foco en process.
- ❌ **Cerrar el incident sin determinar quién lo hizo público.** Sin conocer la causa, va a volver a pasar.

## Automatización

### Fase 1: Manual

Humano sigue el playbook.

### Fase 2: Asistido

Script que recibe el bucket name y ejecuta los queries de triage:

```bash
./scripts/triage-public-bucket.sh [BUCKET_NAME]
# Output: estado actual, contenido sumario, quién lo hizo público, cuándo
```

### Fase 3: Semi-automático

EventBridge rule sobre GuardDuty finding `Policy:S3/BucketAnonymousAccessGranted`:

```
Trigger: GuardDuty finding
   ↓
Lambda 1: Aplicar block_public_access automáticamente
   ↓
Lambda 2: Capturar policy y ACL actuales para evidencia
   ↓
Lambda 3: Snapshot del bucket (lista de objetos) para evidencia
   ↓
Lambda 4: Notificar on-call con resumen + link a evidencia
   ↓
Human: investiga, decide próximos pasos
```

**Importante:** El Lambda 1 que aplica `block_public_access` es seguro porque NO destruye nada. Si el bucket era público intencionalmente, vas a recibir un finding pero el rollback es trivial.

### Fase 4: Automático

Step Function que ejecuta containment + eradication completos. Solo dejá al humano la decisión de "este bucket era legítimo, restaurar policy" o "este bucket no debería existir, mover y borrar".

## Métricas

- **MTTD**: tiempo entre que se hizo público y la alerta.
- **MTTC**: tiempo entre alerta y containment.
- **Public exposure window**: tiempo total que estuvo público.
- **Buckets affected per quarter**: si más de 2-3 por trimestre, hay problema de process.

## Recursos

- [AWS S3 block public access](https://docs.aws.amazon.com/AmazonS3/latest/userguide/access-control-block-public-access.html)
- [GuardDuty S3 findings](https://docs.aws.amazon.com/guardduty/latest/ug/guardduty_finding-types-s3.html)
- [Macie classification](https://docs.aws.amazon.com/macie/latest/user/data-classification.html)
- [Terraform block public access](https://registry.terraform.io/providers/hashicorp/aws/latest/docs/resources/s3_bucket_public_access_block)
