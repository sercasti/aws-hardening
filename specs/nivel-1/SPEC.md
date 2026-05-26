# Spec — Nivel 1: El Despertar

> Tiempo de implementación: 1 día. Costo recurrente: 0 USD. Boss fight: encontrar y darle dueño a las cuentas huérfanas de tu organización.

## Visión

En Nivel 1 cerramos los riesgos triviales que cualquiera puede explotar con una API key y una hora. No requiere herramientas, no requiere especialistas, no requiere presupuesto. Es la línea base mínima de la cual NO se baja.

## Principios

1. **Lo que se puede cerrar en una hora, se cierra en una hora.** Si un control toma más de una hora, es Nivel 2 o superior.
2. **Lo que es gratis, se aplica.** Costo no es excusa para no estar en Nivel 1.
3. **Todo lo nuevo nace en Nivel 1.** Cuentas creadas hoy ya tienen estos controles, no se difieren.
4. **El root account es sagrado.** Cero uso operativo, cero access keys, MFA siempre.
5. **Logs son no negociables.** Si algo no está logueado, no pasó. Y si no podemos verlo, no podemos defenderlo.

## Controles obligatorios

### Identity

#### IAM.1: MFA en el root user de cada cuenta

- **Estado deseado:** Hardware o virtual MFA habilitado en root, ninguna sesión sin MFA aceptada.
- **Verificación:**

  ```bash
  aws iam get-account-summary --query 'SummaryMap.AccountMFAEnabled'
  # Esperado: 1
  ```

- **Severidad si falla:** critical
- **Excepciones:** ninguna

#### IAM.2: Cero access keys en el root user

- **Estado deseado:** El root no tiene access keys.
- **Verificación:**

  ```bash
  aws iam get-account-summary --query 'SummaryMap.AccountAccessKeysPresent'
  # Esperado: 0
  ```

- **Severidad si falla:** critical
- **Excepciones:** ninguna. Si crees que necesitás keys del root para algo, no lo necesitás.

#### IAM.3: MFA habilitado en todos los usuarios IAM humanos

- **Estado deseado:** Cualquier usuario IAM marcado como humano (sin tag `purpose=service`) tiene MFA.
- **Verificación:**

  ```bash
  aws iam list-users --query 'Users[*].UserName' --output text | \
    xargs -n1 -I{} aws iam list-mfa-devices --user-name {} \
    --query 'MFADevices[*].SerialNumber'
  ```

- **Severidad si falla:** high
- **Excepciones:** Service accounts marcados con tag `purpose=service`. La migración correcta es a IAM Identity Center (Nivel 2), no a usuarios IAM humanos.

#### IAM.4: Password policy fuerte

- **Estado deseado:** mínimo 14 caracteres, requiere símbolos/números/upper/lower, expira en 90 días, no reusar últimas 24.
- **Verificación:**

  ```bash
  aws iam get-account-password-policy
  ```

- **Severidad si falla:** medium

### Monitoring

#### LOG.1: CloudTrail habilitado en todas las regiones

- **Estado deseado:** Trail multi-región, captura management events + data events relevantes (S3 GetObject en buckets sensibles, Lambda Invoke).
- **Verificación:**

  ```bash
  aws cloudtrail describe-trails --include-shadow-trails \
    --query 'trailList[?IsMultiRegionTrail==`true`]'
  ```

- **Severidad si falla:** critical
- **Excepciones:** ninguna

#### LOG.2: CloudTrail log file validation habilitado

- **Estado deseado:** Validación de integridad habilitada para detectar tampering.
- **Verificación:**

  ```bash
  aws cloudtrail get-trail-status --name [TRAIL_NAME]
  # LogFileValidationEnabled: true
  ```

- **Severidad si falla:** medium

#### LOG.3: GuardDuty habilitado en todas las regiones donde tenés recursos

- **Estado deseado:** Detector activo en cada región con servicios desplegados.
- **Verificación:**

  ```bash
  aws guardduty list-detectors
  # Debe existir al menos uno por región activa
  ```

- **Severidad si falla:** high
- **Excepciones:** Regiones sin recursos (no se activa, ahorras costo).

#### LOG.4: Cost Anomaly Detection configurado, con destino humano

- **Estado deseado:** Detector activo, alertas a un canal que un humano efectivamente lee (no a un mailbox compartido que nadie revisa).
- **Verificación:**

  ```bash
  aws ce get-anomaly-monitors
  aws ce get-anomaly-subscriptions
  ```

- **Severidad si falla:** medium
- **Anti-pattern:** Mandar las alertas a `aws-alerts@empresa.com` que nadie lee. Mejor: canal de Slack del equipo SRE.

#### LOG.5: IAM Access Analyzer habilitado

- **Estado deseado:** Analyzer activo, findings revisados al menos mensualmente.
- **Verificación:**

  ```bash
  aws accessanalyzer list-analyzers
  ```

- **Severidad si falla:** medium

### Data

#### DAT.1: S3 buckets con block public access habilitado

- **Estado deseado:** A nivel cuenta, `block_public_access` aplica a todos los buckets.
- **Verificación:**

  ```bash
  aws s3control get-public-access-block --account-id [ACCOUNT_ID]
  ```

- **Severidad si falla:** critical
- **Excepciones:** Buckets explícitamente pensados para hosting estático público (con tag `purpose=public-asset`). Excepciones documentadas en `exceptions.md`.

#### DAT.2: S3 buckets con encryption at rest

- **Estado deseado:** Todos los buckets con encryption default (SSE-S3 mínimo, KMS preferido para buckets con data sensible).
- **Verificación:** Buckets sin encryption se detectan vía S3 API o checkov.
- **Severidad si falla:** high

### Organization

#### ORG.1: Cuentas huérfanas inventariadas

- **Estado deseado:** Toda cuenta AWS tiene un owner (humano identificable, no "el equipo X"). Owner registrado en tag `owner` de la cuenta.
- **Verificación:**

  ```bash
  aws organizations list-accounts --query 'Accounts[*].[Id,Name,Tags]'
  ```

- **Severidad si falla:** critical (boss fight de Nivel 1)
- **Por qué importa:** Una cuenta huérfana es un riesgo doble. Nadie la monitorea, nadie sabe qué corre adentro, y nadie va a notar cuando un atacante la usa.

## Anti-patterns

Cosas que el agente debería marcar inmediatamente:

- ❌ Root user con access keys
- ❌ Cuentas sin MFA en root
- ❌ S3 buckets con ACL `public-read` o `public-read-write`
- ❌ CloudTrail no configurado o configurado solo en una región
- ❌ GuardDuty deshabilitado en una región con workloads
- ❌ Usuarios IAM humanos con `*:*` en alguna policy
- ❌ Cualquier credencial hardcodeada en código (lo detecta git secrets scan)
- ❌ Security groups con `0.0.0.0/0` en puertos SSH (22) o RDP (3389)

## Métricas de éxito

Estás en Nivel 1 cuando:

- 100% de tus cuentas pasan los controles ID.1 a DAT.2.
- Tenés inventario completo de cuentas, cada una con owner identificable.
- Tu equipo ejecutó al menos una revisión completa del IAM Access Analyzer.
- Configuraste GuardDuty en cada región activa y el on-call ya respondió al menos a un finding (real o de prueba).

## Boss fight: cuentas huérfanas

El control más difícil de Nivel 1 no es técnico, es político.

**El problema:** Empresas medianas suelen tener 5 a 50 cuentas AWS. Muchas fueron creadas hace años, con tarjeta de crédito personal, por algún experimento que nunca se cerró. Encontrar al "dueño" de esa cuenta requiere hablar con gente, revisar billing, mirar quién paga.

**El método:**

1. Listá todas las cuentas en tu organization. Si no tenés AWS Organizations, esto es señal de que tenés que armarla primero (es Nivel 2 técnicamente, pero te ayuda para Nivel 1).
2. Por cada cuenta, identificá:
   - Email asociado
   - Último login
   - Servicios activos (qué corre adentro)
   - Costo mensual
3. Para cada cuenta sin owner claro:
   - Mandá un email/Slack al departamento al que parece pertenecer.
   - Si nadie responde en 2 semanas, escalá al CFO (que paga la factura).
   - Si en 1 mes nadie reclama: candidata a cerrar.
4. Para cerrar una cuenta huérfana:
   - Snapshot completo de los recursos (por si después aparece el dueño).
   - Notificación de 30 días.
   - Cierre definitivo.

**Tiempo esperado:** Una organización mediana cierra esto en 1 a 3 meses, no en un día. La parte técnica es trivial; la coordinación es lo difícil.

## Próximo nivel

Cuando cumplas Nivel 1, andá a [`../nivel-2/SPEC.md`](../nivel-2/SPEC.md).

Allí el desafío deja de ser técnico y se vuelve organizacional: la primera SCP que mandás puede tirarte 12 servicios. La técnica para no romper producción ya está documentada.
