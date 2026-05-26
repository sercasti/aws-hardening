# Security Review (Nivel 0, el lunes a la mañana)

> Este es el prompt principal del repo. Si solo vas a correr uno, corré este. Te devuelve dónde estás parado en el AWS Security Maturity Model y qué arreglar primero.

## Cómo usarlo

1. Exportá una snapshot de tu cuenta AWS en read-only:

```bash
mkdir -p audit-snapshot
aws iam get-account-authorization-details > audit-snapshot/iam.json
aws cloudtrail describe-trails --include-shadow-trails > audit-snapshot/cloudtrail.json
aws guardduty list-detectors > audit-snapshot/guardduty.json
aws s3api list-buckets > audit-snapshot/s3.json
aws ec2 describe-instances --query 'Reservations[*].Instances[*].[InstanceId,MetadataOptions]' > audit-snapshot/ec2-metadata.json
aws organizations describe-organization > audit-snapshot/organization.json 2>/dev/null || echo '{}' > audit-snapshot/organization.json
aws organizations list-policies --filter SERVICE_CONTROL_POLICY > audit-snapshot/scps.json 2>/dev/null || echo '{}' > audit-snapshot/scps.json
```

(Si no tenés `aws organizations` permisos, los últimos dos los saltás. Es normal en cuentas standalone.)

2. Copiá el prompt de abajo. Pegalo en Claude, GPT, Gemini, Kiro, lo que uses.

3. Cuando el agente te pida los archivos, pegalos uno por uno o subilos como adjuntos.

4. Reemplazá los `[corchetes]` con tu info.

5. Leé el reporte. Validá los findings críticos antes de actuar.

---

## El prompt

```
Rol: Sos un auditor senior de seguridad cloud especializado en AWS, con experiencia
en el AWS Security Maturity Model (https://maturitymodel.security.aws.dev). Hablás
español neutro, técnico pero directo.

Contexto: Voy a darte una snapshot de mi cuenta AWS con:
- iam.json: output de aws iam get-account-authorization-details
- cloudtrail.json: configuración de trails
- guardduty.json: detectores configurados
- s3.json: buckets en la cuenta
- ec2-metadata.json: instancias y sus configuraciones de IMDS
- organization.json: información de AWS Organizations (puede estar vacío)
- scps.json: SCPs desplegadas (puede estar vacío)

Mi cuenta AWS es [ACCOUNT_ID] en la región principal [REGION] ([ej: us-east-1]).
Mi organización tiene [N] cuentas en total ([ej: 3]).
Mi sector es [SECTOR] ([ej: fintech, ecommerce, SaaS B2B, gobierno, edtech]).
Mi tamaño de equipo de plataforma es [N] personas.

Tarea: Auditá la snapshot y devolvéme un reporte priorizado de findings. Para cada
finding, mapealo al nivel del AWS Security Maturity Model que está fallando
(0, 1, 2, 3, 4) y dame:

1. Severidad: critical, high, medium, low
2. Categoría: identity, network, data, monitoring, organization
3. Descripción del finding en una frase
4. Por qué importa, en una frase, con el escenario de explotación
5. Cómo arreglarlo, con el comando AWS CLI o el bloque de Terraform/CDK exacto
6. Tiempo estimado para fixearlo
7. Si requiere coordinación con otros equipos (sí/no) y con cuáles

Output esperado: Una tabla Markdown ordenada por severidad, después prosa con los
top 3 findings explicados en profundidad. Al final, un score del 0 al 4 indicando
en qué nivel del maturity model está la cuenta hoy, con justificación de una frase.

Guardrails:
- NO inventes findings que no podés confirmar desde la snapshot. Si te falta data,
  pedí el comando AWS CLI específico que necesitarías.
- NO recomiendes herramientas comerciales pagas a menos que te pregunte
  específicamente. Quedate en herramientas nativas de AWS y open source.
- NO me digas que "deberíamos contratar un especialista". El punto de este ejercicio
  es resolverlo sin uno.
- Si encontrás algo que es severidad critical, ponelo en una sección aparte ARRIBA
  de la tabla, no enterrado en el medio.
- Si no encontrás findings críticos, decílo explícitamente. No inventes urgencia
  para parecer útil.
```

---

## Qué esperar del reporte

Un buen output de este prompt en una cuenta de Nivel 0-1 promedio te va a devolver entre 8 y 15 findings. Los típicos:

- **Critical**: Root user sin MFA. Access keys del root activas. Cuentas sin CloudTrail. Buckets S3 con bloqueo público desactivado y ACLs abiertas.
- **High**: GuardDuty deshabilitado. Sin IAM Access Analyzer. SCPs no configuradas. EC2 con IMDSv1 habilitado.
- **Medium**: Tags inconsistentes. Sin retención en CloudTrail. KMS keys sin rotación.
- **Low**: Falta de tags, naming inconsistente, regiones no usadas con servicios activos.

Si el reporte te tira más de 25 findings, probablemente el agente está siendo paranoico. Mirá los de severidad critical y high primero. El resto puede esperar al sprint siguiente.

## Iterando

Después de leer el reporte, podés volver al chat y pedir:

```
Para el finding "X", dame el código Terraform completo, las consideraciones de
rollback, y qué tests correr antes de aplicarlo. Asumí que estoy usando Terraform
1.7 con AWS provider 5.x.
```

Eso te genera el fix completo, no solo el snippet. Iterás hasta tener un plan ejecutable.

## Próximo paso

Una vez que tengas el reporte:

1. Filtrá los findings de severidad critical y high.
2. Para los 3 más críticos, usá [`scp-design.md`](./scp-design.md) o [`iam-audit.md`](./iam-audit.md) según corresponda para hacer deep-dive.
3. Para los demás, agendalos como tickets en tu próximo sprint usando los specs en [`../specs/`](../specs).
