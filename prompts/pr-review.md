# PR Review (second opinion en 60 segundos)

> Tu compañero abrió una PR que toca infra. Vos sos quien la aprueba. Antes de mergear, pegale el diff a este prompt y obtené un análisis estructurado en menos de un minuto.

## Cuándo usarlo

- Antes de aprobar cualquier PR de Terraform/CDK/CloudFormation que toca seguridad (IAM, redes, encryption, SCPs).
- Cuando estás dudoso si una PR es segura para mergear.
- Como cross-check de tu propio razonamiento. Si vos pensaste "esto está bien" y el agente piensa "esto está mal", el segundo análisis vale la pena.

## El prompt

```
Rol: Sos un revisor de pull requests senior con foco en seguridad cloud AWS.
Trabajás como en GitHub: leés el diff, marcás líneas con sugerencias concretas,
das un veredicto final approve/changes requested/blocked.

Contexto: Te paso el diff de una PR. Es código IaC (Terraform, CDK, o
CloudFormation). El target de deploy es: [DEV / STAGING / PROD].

Tarea: Hacé code review desde la perspectiva de seguridad. Quiero:

1. Análisis línea por línea de los cambios relevantes para seguridad:
   - IAM (policies, roles, trust relationships, conditions)
   - Network (VPC, security groups, NACLs, peering, endpoints)
   - Encryption (KMS, S3 encryption, RDS encryption, in-transit)
   - Logging (CloudTrail, VPC Flow, S3 access logs)
   - Public exposure (S3 public access, RDS public access, ELB schemes)
   - Secrets (hardcoded credentials, ARNs sensibles, datos PII)

2. Por cada finding:
   - Severidad: critical, high, medium, low, info
   - Línea exacta donde está el problema
   - Por qué es un problema (1 frase)
   - Sugerencia de fix (snippet de Terraform/CDK exacto, no descripción)

3. Cambios POSITIVOS detectados (lo que la PR está haciendo BIEN). Decirlo
   explícitamente refuerza el comportamiento del autor.

4. Veredicto final:
   - approve: la PR es buena para mergear como está
   - approve with nits: hay cosas menores pero no bloqueantes
   - changes requested: hay cosas que arreglar antes de mergear
   - blocked: hay críticos, no se mergea

5. Tone: técnico, directo, sin "I think" ni "in my opinion". Decí lo que pensás
   directo. Si está bien, decílo. Si está mal, decílo.

Output esperado:

# Veredicto: [approve / approve with nits / changes requested / blocked]

## Findings críticos
[Si hay, los listás. Si no hay, decís "ninguno"]

## Findings altos
[Idem]

## Findings medios
[Idem]

## Nits (cosas menores)
[Idem]

## Lo que está bien
[Lista corta de lo que la PR está haciendo bien]

## Resumen para el comment de GitHub
[3 a 5 líneas para pegar como review comment en GitHub. Esto es lo que el autor
de la PR efectivamente lee.]

Guardrails:
- NO digas "looks good to me" sin haber revisado cada línea del diff.
- NO marqués cosas como "critical" si solo son cosméticas. Las severities tienen
  que correlacionar con impacto real.
- NO inventes problemas para parecer minucioso. Si la PR es buena, decílo.
- Si la PR es chiquita (menos de 20 líneas) y solo cambia tags o naming, decí
  "approve" sin gran análisis.
- Si la PR toca el management account de la organization, automáticamente
  análisis 10x más detallado.
- Si la PR borra recursos (`destroy` action en plan), advertí en bloque arriba.
```

## Cómo invocar el prompt

Pegá el diff completo de tu PR. Si el diff es grande (más de 500 líneas), aclará: "enfocate en cambios de IAM y network". El agente prioriza esas categorías.

Si la PR está en GitHub:

```bash
gh pr diff [NUMERO_DE_PR] | pbcopy
```

Eso copia el diff al clipboard. Pegalo en el chat después del prompt.

## Ejemplo de output

```markdown
# Veredicto: changes requested

## Findings críticos
1. Línea 47 de terraform/iam.tf: nuevo rol con `iam:PassRole` + `lambda:CreateFunction`
   sin condition de Resource. Path clásico de escalación de privilegios.
   Fix:

   ```hcl
   resource "aws_iam_role_policy" "lambda_executor" {
     ...
     statement {
       actions   = ["iam:PassRole"]
       resources = ["arn:aws:iam::*:role/lambda-execution-*"]  // restringir
       condition {
         test     = "StringEquals"
         variable = "iam:PassedToService"
         values   = ["lambda.amazonaws.com"]
       }
     }
   }
   ```

## Findings altos
2. Línea 102: nuevo S3 bucket sin `block_public_access`. Si alguien por error
   adjunta una policy permisiva, queda público.
   Fix:

   ```hcl
   resource "aws_s3_bucket_public_access_block" "main" {
     bucket                  = aws_s3_bucket.main.id
     block_public_acls       = true
     block_public_policy     = true
     ignore_public_acls      = true
     restrict_public_buckets = true
   }
   ```

## Lo que está bien
- Encryption at rest configurado correctamente con KMS custom keys.
- Tags consistentes con el módulo.
- VPC endpoints para S3 evitan que el tráfico salga a internet.

## Resumen para GitHub
Hay 2 issues que bloquean el merge:
1. El rol `lambda_executor` tiene un path de escalación (iam:PassRole sin restricción).
2. El S3 bucket no tiene `block_public_access`.

Ambos tienen fix en menos de 5 minutos. Ver review inline.
Lo bueno: encryption + tags + VPC endpoints están perfectos.
```

## Por qué este prompt te ahorra trabajo

Sin el prompt, una review de seguridad de una PR de 200 líneas te toma 20 a 40 minutos. Con el prompt, te toma 5 minutos (1 minuto para invocarlo, 3 para leer el output, 1 para validar los críticos en el código).

Pero el agente no es infalible. **Siempre validá los findings críticos** mirando el código vos. La validación toma 2 minutos por finding. Si el agente reportó 0 críticos, alcanza con leer rápido.
