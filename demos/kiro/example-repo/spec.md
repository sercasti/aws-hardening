# Spec del Nivel 1 (Demo)

> Spec simplificado para demo en vivo. NO usar como spec real de tu organización.

## Target: Nivel 1 — El Despertar

### Controles obligatorios

1. **MFA en usuario root**
   - Tipo: Hardware MFA preferido, virtual MFA aceptable como mínimo.
   - Verificación: `aws iam get-account-summary` muestra `AccountMFAEnabled: 1`.

2. **CloudTrail multi-region**
   - Multi-region trail activo.
   - File integrity validation habilitada.
   - Log file encryption con CMK customer-managed.
   - Verificación: `aws cloudtrail describe-trails`.

3. **GuardDuty habilitado**
   - En las regiones: us-east-1, sa-east-1.
   - Status: ENABLED.
   - Findings export a S3 (no solo en consola).
   - Verificación: `aws guardduty list-detectors --region [REGION]`.

4. **Cost Anomaly Detection**
   - Al menos 1 monitor de tipo "AWS services".
   - Subscription con email del equipo ops.
   - Threshold: $50 (esta org es chica).
   - Verificación: `aws ce get-anomaly-monitors`.

5. **AWS Budgets**
   - Al menos 1 budget mensual.
   - Notification a 80% y 100%.
   - Verificación: `aws budgets describe-budgets`.

6. **S3 Block Public Access**
   - A nivel cuenta: 4 settings en TRUE.
   - A nivel bucket: 4 settings en TRUE para todos los buckets.
   - Verificación: `aws s3control get-public-access-block`.

7. **Identity Center**
   - SSO configurado.
   - Cero IAM users humanos (solo programáticos para CI/CD).
   - Verificación: `aws sso-admin list-instances`.

8. **IAM Access Analyzer**
   - Activo a nivel cuenta (organización si aplica).
   - Verificación: `aws accessanalyzer list-analyzers`.

### Constraints organizacionales

- **Region restriction**: us-east-1, sa-east-1. Cualquier otra requiere ticket de excepción.
- **Tag obligatorio**: Environment (sandbox/dev/staging/prod), Owner (email), CostCenter.
- **Roles cross-account**: solo con ExternalId fuerte (32+ chars).
- **Production**: tag Environment=prod requiere PR + 2 approvers para cualquier cambio destructivo.

### Boss fight de Nivel 1

Después de cubrir los 8 controles, el último paso para "salir" de Nivel 1:

> Identificá y deshabilitá todas las cuentas IAM humanas inactivas (sin login en últimos 90 días) o sin dueño conocido.

Si no podés hacer eso (porque no tenés inventory de quién es dueño de qué cuenta), tu Nivel 1 no está completo, independientemente de los otros 8 controles.

### Próximo nivel

Una vez completado Nivel 1, leé `specs/nivel-2/SPEC.md` para los Cimientos (SCPs, IAM baseline, KMS rotation).

### Notas para la demo

- Esta spec es la versión MVP. La spec real tiene más detalles en cada control.
- En la demo, Kiro va a usar esta spec + baseline-mock.json para generar el plan.
- El plan que Kiro genera va a tener fixes concretos por gap.
