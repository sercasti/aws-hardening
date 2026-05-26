# Templates

> Templates listos para copiar y adaptar. SCPs, IAM baselines, KMS defaults. Cada template viene con su explicación de qué hace, cuándo aplicarlo, qué riesgo trae, y cómo testearlo.

## Filosofía

Los templates NO son drop-in. Son punto de partida. Tu organización tiene contexto que estos templates no conocen: regiones aprobadas, partners legítimos, casos de uso específicos. Tu trabajo es:

1. Leer el template.
2. Entenderlo (si no, leer las anotaciones en el archivo).
3. Adaptarlo a tu contexto.
4. Testearlo en audit-mode antes de enforce.
5. Documentar excepciones.

Cualquier template aplicado sin entender lo que hace va a romper algo, antes o después.

## Estructura

```
templates/
├── scps/                          # Service Control Policies
│   ├── 01-deny-disable-cloudtrail.json
│   ├── 02-deny-disable-guardduty.json
│   ├── 03-deny-region-outside-list.json
│   ├── 04-require-imdsv2.json
│   ├── 05-deny-root-user.json
│   ├── 06-deny-iam-user-creation.json
│   └── 07-deny-make-s3-public.json
├── iam-baseline/                  # Policies IAM mínimas
│   ├── readonly-auditor.json
│   ├── break-glass-emergency.json
│   └── deny-dangerous-actions.json
├── kms-defaults/                  # Configuración KMS recomendada
│   ├── cmk-default-policy.json
│   └── rotation-enabled.tf
└── scp-exception-template.md      # Template para documentar excepciones
```

## Cómo aplicar SCPs

### Workflow recomendado

```
1. Diseñar el SCP
   ↓
2. Aplicar en sandbox account (audit mode = Effect: Allow + tag specific)
   ↓
3. Esperar 2 semanas, monitorear CloudTrail por accidentales bloqueos
   ↓
4. Si todo OK, mover a Effect: Deny
   ↓
5. Aplicar a OU de dev
   ↓
6. Esperar 1 semana
   ↓
7. Aplicar a OU de prod
   ↓
8. Documentar en `scp-exceptions.md` cualquier excepción
```

Más detalles en [`/specs/nivel-2/SPEC.md`](../specs/nivel-2/SPEC.md).

### Audit-mode vs enforce-mode

AWS SCPs son binarias (Allow/Deny), no tienen audit-mode nativo. Para simular:

**Opción A: Effect: Allow restrictivo.**

Definí un Allow que solo permite las acciones que querés permitir. El resto se deniega implícitamente. Para audit, agregá una condición que SOLO aplica el deny en una OU específica:

```json
{
  "Statement": [{
    "Effect": "Deny",
    "Action": "ec2:RunInstances",
    "Resource": "*",
    "Condition": {
      "StringNotEquals": {
        "aws:RequestTag/Environment": ["dev", "staging", "prod"]
      },
      "StringEquals": {
        "aws:PrincipalAccount": "[SANDBOX_ACCOUNT_ID]"
      }
    }
  }]
}
```

**Opción B: CloudTrail logging analysis.**

Aplicar el SCP en una sub-OU primero. CloudTrail logueará los AccessDenied. Si después de 1 semana hay 0 denials de identidades legítimas, el SCP es seguro de expandir.

### Rollback rápido

Si un SCP rompe producción:

```bash
# Detach inmediato
aws organizations detach-policy \
  --policy-id [POLICY_ID] \
  --target-id [OU_OR_ACCOUNT]

# El efecto es instantáneo (segundos)
```

Tu plan de rollback debe estar documentado ANTES de aplicar el SCP.

## SCPs incluidos

### 01-deny-disable-cloudtrail.json

**Qué hace:** Impide que cualquier identidad (excepto el OrgRoot) detenga, borre, o modifique CloudTrail.

**Cuándo aplicar:** Siempre. Es el control #1 después de habilitar CloudTrail.

**Riesgo:** Bajo. Workloads legítimos no necesitan modificar CloudTrail. Si alguien lo necesita, requiere break-glass.

### 02-deny-disable-guardduty.json

**Qué hace:** Impide deshabilitar GuardDuty o modificar sus detector settings.

**Cuándo aplicar:** Después de habilitar GuardDuty en todas las cuentas.

**Riesgo:** Bajo. Similar al anterior.

### 03-deny-region-outside-list.json

**Qué hace:** Bloquea todas las API calls a regiones fuera de la lista permitida.

**Cuándo aplicar:** Cuando tu organización tiene 1-3 regiones aprobadas. Antes de aplicar, definí qué regiones son.

**Riesgo:** Medio. Puede romper services que tienen endpoints globales (CloudFront, IAM, Organizations). El SCP excluye esos. Validá tu uso primero.

### 04-require-imdsv2.json

**Qué hace:** Fuerza que `RunInstances` use IMDSv2 (token-based metadata) en lugar de IMDSv1 (vulnerable a SSRF).

**Cuándo aplicar:** Siempre. IMDSv1 es un riesgo de seguridad conocido.

**Riesgo:** Bajo si los AMIs/aplicaciones soportan IMDSv2. La mayoría sí (cualquier AMI o app de últimos 4 años).

### 05-deny-root-user.json

**Qué hace:** Bloquea cualquier acción del usuario root excepto las pocas que solo el root puede hacer (gestionar billing, cerrar la cuenta).

**Cuándo aplicar:** Después de configurar MFA en root y SSO/Identity Center para uso operacional.

**Riesgo:** Si necesitás root para algo, vas a tener que detach temporal. Documentar el proceso.

### 06-deny-iam-user-creation.json

**Qué hace:** Bloquea `CreateUser`, `CreateLoginProfile`, `CreateAccessKey`.

**Cuándo aplicar:** Después de migrar a SSO/Identity Center. No deberías tener IAM users de larga vida.

**Riesgo:** Si tu organización todavía usa IAM users, esto los congela. Hacer la migración primero.

### 07-deny-make-s3-public.json

**Qué hace:** Bloquea `PutBucketAcl` con ACL public, `PutBucketPolicy` con Principal `*`, y `DeletePublicAccessBlock`.

**Cuándo aplicar:** Siempre. La excepción de buckets públicos legítimos (CDN, website) se maneja por tag o por OU.

**Riesgo:** Bajo. Si tenés buckets públicos legítimos, etiquetalos y exceptualos.

## IAM Baseline

### readonly-auditor.json

Rol que permite leer toda la cuenta pero no modificar nada. Para auditors, compliance, y agents de assessment.

### break-glass-emergency.json

Rol con AdministratorAccess para emergencias. Solo asumible con MFA hardware key. CloudTrail-logged y alertado a Slack. Usar solo cuando todo lo demás falla.

### deny-dangerous-actions.json

Policy que niega acciones peligrosas (ej. `iam:CreateUser`, `iam:DeleteRole`, `ec2:TerminateInstances` sobre tags=production) incluso si están permitidas por otra policy. Adjuntar a todos los developer roles.

## KMS Defaults

### cmk-default-policy.json

Key policy template para CMKs. Defaults seguros:

- Solo el rol creador y el rol consumidor pueden usar.
- Rotación habilitada.
- Deletion protection (7 días mínimo).

### rotation-enabled.tf

Terraform module para crear CMKs con rotación automática habilitada por default.

## Exceptions

Cuando aplicás un SCP y descubrís un caso legítimo que rompe:

1. Documentá en `templates/scp-exceptions.md` (template en este folder).
2. Si la excepción es por una cuenta específica: aplicá el SCP a una OU sin esa cuenta.
3. Si la excepción es por una identidad específica: agregá Condition `aws:PrincipalArn` que la excluye.
4. Si la excepción es temporal: poné fecha de expiración en el documento. Auditar trimestralmente.

NO simplemente quites el SCP "porque rompe". Si rompe, hay algo mal: la app, el SCP, o el conocimiento del equipo. Investigar antes de quitar.

## Validación

Cada SCP debería tener tests. Ejemplo con AWS CLI:

```bash
# Bash test que verifica que un Action está bloqueado
# Se corre con credenciales con privilegios elevados pero limitados por el SCP

aws cloudtrail stop-logging --name [TRAIL] --dry-run 2>&1 | grep -i "denied" && echo "PASS: SCP bloquea StopLogging" || echo "FAIL: SCP no bloqueó"
```

Una librería más robusta: [aws-iam-policy-tester](https://github.com/iann0036/iam-floyd).

## Recursos

- [AWS SCP examples](https://docs.aws.amazon.com/organizations/latest/userguide/orgs_manage_policies_scps_examples.html)
- [SCP strategies](https://aws.amazon.com/blogs/security/how-to-use-service-control-policies-to-set-permission-guardrails-across-accounts-in-your-aws-organization/)
- [Steampipe (queries to validate state)](https://steampipe.io/)
- [Wellington Chevreuil's SCP examples](https://github.com/awslabs/aws-service-control-policy-examples)
