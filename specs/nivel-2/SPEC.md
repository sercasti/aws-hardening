# Spec — Nivel 2: Los Cimientos

> Tiempo de implementación: 1 semana de trabajo técnico, 2 a 6 semanas de coordinación. Costo recurrente: 0 USD. Boss fight: tu primera SCP en enforce sin romper producción.

## Visión

En Nivel 2 pasamos de proteger una cuenta a proteger la organización. SCPs, IMDSv2, KMS, cero secrets en código, federación con SSO/IdP. Es donde la mayoría de las empresas se traba, pero no por dificultad técnica: por dificultad política.

## Principios

1. **Los controles viven a nivel organización, no a nivel cuenta.** Lo que se puede aplicar como SCP, se aplica como SCP. Lo que no, se documenta.
2. **Cero usuarios IAM humanos.** Toda persona accede vía SSO/IdP federado. Los usuarios IAM solo existen para servicios y workloads automatizados.
3. **Secrets no viven en código ni en variables de entorno.** Viven en Secrets Manager, Parameter Store con encryption, o (mejor) en federación con tu IdP.
4. **El metadata service no es accesible vía proxy.** IMDSv2 obligatorio. Sin excepciones.
5. **Lo que vamos a aplicar como deny, lo aplicamos primero como audit-mode.** Mínimo dos semanas en audit antes de pasar a enforce.

## Controles obligatorios

### Organization

#### ORG.2: AWS Organizations configurada con OUs

- **Estado deseado:** Organization activa, OUs separan dev/staging/prod y opcionalmente sandbox/security.
- **Verificación:**

  ```bash
  aws organizations describe-organization
  aws organizations list-roots
  aws organizations list-organizational-units-for-parent --parent-id [ROOT_ID]
  ```

- **Severidad si falla:** high
- **Excepciones:** Empresas con una sola cuenta (justificadas en `exceptions.md`).

#### ORG.3: SCP base aplicada al root de la organization

- **Estado deseado:** Una SCP mínima en root que bloquea acciones críticas en TODAS las cuentas.
- **Controles incluidos en la SCP base:**
  - Deny `iam:DeleteRole` para roles con tag `protected=true`
  - Deny `cloudtrail:Stop*`, `cloudtrail:Delete*`
  - Deny `guardduty:Disassociate*`, `guardduty:Delete*`
  - Deny `kms:ScheduleKeyDeletion` para keys con tag `protected=true`
  - Deny `aws:CalledVia` desde regiones no aprobadas
- **Verificación:**

  ```bash
  aws organizations list-policies --filter SERVICE_CONTROL_POLICY
  aws organizations list-targets-for-policy --policy-id [POLICY_ID]
  ```

- **Severidad si falla:** high
- **Boss fight:** ver "Boss fight" abajo.

#### ORG.4: SCP de region restriction

- **Estado deseado:** SCP que bloquea operaciones en regiones que la organización no aprobó. Por ejemplo, si solo operás en us-east-1 y eu-west-1, el resto está cerrado.
- **Por qué importa:** Atacantes suelen abrir EC2 instances en regiones que no monitoreás (ap-south-1, sa-east-1) para criptominería. Restringir regiones cierra esa puerta.
- **Verificación:**

  ```bash
  aws organizations list-policies --filter SERVICE_CONTROL_POLICY | grep -i region
  ```

- **Severidad si falla:** medium
- **Excepciones:** Servicios globales (IAM, CloudFront, Route53) deben quedar permitidos.

### Identity

#### IAM.5: IAM Identity Center configurado (SSO)

- **Estado deseado:** Identity Center activo, integrado con el IdP corporativo (Okta, Azure AD, Google Workspace).
- **Verificación:**

  ```bash
  aws sso-admin list-instances
  ```

- **Severidad si falla:** high
- **Por qué importa:** Sin SSO, cada onboarding/offboarding requiere tocar IAM manualmente. Con SSO, todo es automático.

#### IAM.6: Cero usuarios IAM humanos

- **Estado deseado:** Listado de usuarios IAM solo contiene service accounts (tag `purpose=service`).
- **Verificación:**

  ```bash
  aws iam list-users --query 'Users[?Tags[?Key==`purpose` && Value==`service`]]'
  # Diff con: aws iam list-users
  # Cualquier user sin tag `purpose=service` es un usuario humano (anti-pattern)
  ```

- **Severidad si falla:** high
- **Transición:** Si actualmente tenés usuarios IAM humanos, el path es:
  1. Configurar SSO.
  2. Crear permission sets equivalentes a las policies actuales.
  3. Asignar grupos del IdP a permission sets.
  4. Migrar usuarios uno por uno, verificando que pueden hacer su trabajo.
  5. Borrar los usuarios IAM viejos.

#### IAM.7: Roles federados con session tags

- **Estado deseado:** Los roles asumidos vía SSO incluyen session tags con info del usuario (email, department).
- **Por qué importa:** Permite auditar quién hizo qué sin tener que correlacionar entre IdP y CloudTrail.
- **Verificación:**

  ```bash
  aws iam list-roles --query 'Roles[?contains(AssumeRolePolicyDocument, `aws:PrincipalTag`)]'
  ```

- **Severidad si falla:** medium

### Network

#### NET.1: IMDSv2 obligatorio en todas las EC2

- **Estado deseado:** Todas las EC2 corren con `HttpTokens: required`.
- **Verificación:**

  ```bash
  aws ec2 describe-instances --query \
    'Reservations[*].Instances[?MetadataOptions.HttpTokens==`optional`].[InstanceId]'
  # Esperado: array vacío
  ```

- **Severidad si falla:** high
- **Por qué importa:** Sin IMDSv2, un bug en una web app (SSRF) puede leer credenciales del EC2 desde el metadata service. Caso Capital One 2019, 100M registros, multa de 80M USD.
- **Cómo migrar:** Modify-instance-metadata-options en cada instancia. Para nuevas instancias, default en el launch template.

#### NET.2: VPC endpoints para servicios sensibles

- **Estado deseado:** S3, DynamoDB, KMS, Secrets Manager se acceden vía VPC endpoint, no via internet gateway.
- **Verificación:**

  ```bash
  aws ec2 describe-vpc-endpoints
  ```

- **Severidad si falla:** medium
- **Por qué importa:** Sin VPC endpoints, el tráfico a estos servicios pasa por internet, sumando una superficie de ataque innecesaria.

### Data

#### DAT.3: KMS keys rotadas anualmente

- **Estado deseado:** `Annual key rotation` habilitado en todas las KMS keys de uso recurrente.
- **Verificación:**

  ```bash
  aws kms list-keys --query 'Keys[*].KeyId' --output text | \
    xargs -n1 -I{} aws kms get-key-rotation-status --key-id {}
  ```

- **Severidad si falla:** medium

#### DAT.4: Cero secrets en código

- **Estado deseado:** Pre-commit hook con `git-secrets` o `detect-secrets`. CI pipeline corre `trufflehog` en cada PR.
- **Verificación:** Manual + en cada PR.
- **Severidad si falla:** critical (si se detecta uno, es incident, no warning)

#### DAT.5: Secrets viven en Secrets Manager o Parameter Store con KMS

- **Estado deseado:** Las apps acceden a credenciales vía SDK, no vía variables de entorno con valores hardcodeados.
- **Verificación:** Code review + grep por patrones comunes (`os.getenv('PASSWORD')`, etc.)
- **Severidad si falla:** high

## Anti-patterns

- ❌ Usuarios IAM humanos (después de habilitar SSO)
- ❌ EC2 con IMDSv1
- ❌ Buckets S3 accedidos via internet gateway en lugar de VPC endpoint
- ❌ Secrets en variables de entorno en el código fuente
- ❌ Roles con `AssumeRolePolicyDocument` que permite `Principal: "*"`
- ❌ SCPs en enforce sin haber pasado por audit mode 2 semanas mínimo
- ❌ KMS keys sin rotación habilitada
- ❌ Regiones no usadas con servicios activos (señal de actividad anómala)

## Métricas de éxito

Estás en Nivel 2 cuando:

- Tenés AWS Organizations + OUs estructuradas.
- La SCP base está en enforce sin tickets de "se rompió X" en las últimas 4 semanas.
- SSO está activo y todos los humanos lo usan.
- 100% de tus EC2 corren con IMDSv2.
- Tu pipeline bloquea PRs con secrets hardcodeados.
- Tenés un proceso documentado para pedir excepción a una SCP.

## Boss fight: la primera SCP sin romper prod

**El problema:** SCPs son deny policies a nivel organización. Si aplicás una SCP en enforce que bloquea algo que un workload legítimo está usando, se rompe ese workload. Inmediatamente.

**El antipattern:** "Voy a aplicar la SCP en enforce el viernes a la noche para no molestar a nadie". El viernes a la noche es cuando NO hay nadie para arreglar lo que se rompe.

**El método correcto (audit-mode primero):**

1. Diseñá la SCP usando [`../prompts/scp-design.md`](../../prompts/scp-design.md). El prompt genera la SCP + tests + plan de audit/enforce/rollback.

2. Aplicá la SCP a una OU de sandbox (no a prod). Confirmá que se carga.

3. Cambiá la SCP de "Deny" a "Audit Mode". Esto se hace con CloudTrail filters: las llamadas que la SCP bloquearía las marcamos como `AccessDenied` en CloudTrail con un tag específico, pero NO se bloquean realmente. Conceptualmente: la SCP genera evidence sin enforcement.

   Implementación práctica: aplicás la SCP a una OU específica y mirás CloudTrail por 2 semanas. Si ves AccessDenied de la SCP en operaciones legítimas, ajustás.

4. Después de 2 semanas sin falsos positivos, expandís la SCP a más OUs, una por vez.

5. Cuando llegues a producción, comunicá con el equipo de SRE 48 horas antes. No por la SCP, sino por si algo se rompe igual.

6. Aplicá la SCP en horario laboral, con el equipo presente. NO en horario fuera de oficina.

**El rollback:** Una SCP se quita en menos de 1 minuto: detach desde la OU/cuenta. Si tu rollback toma más, está mal diseñado el procedimiento.

**El secret del proceso:** Las excepciones son la regla, no la excepción. Vas a tener workloads legítimos que chocan con tu SCP. Documentá las excepciones con justificación en `exceptions.md`. Las excepciones se revisan trimestralmente (a veces el workload se modifica y la excepción ya no es necesaria).

Ver template de excepción en [`../../templates/scp-exception-template.md`](../../templates/scp-exception-template.md).

## Próximo nivel

Cuando cumplas Nivel 2, andá a [`../nivel-3/SPEC.md`](../nivel-3/SPEC.md).

Allí pasamos de "controles preventivos" a "telemetría más respuesta". Detección, alerting, primer playbook automático.
