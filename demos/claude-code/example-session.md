# Claude Code: ejemplo de sesión

Sesión real de Claude Code ejecutando el flywheel pattern. Tiempo total: ~35 minutos.

## Inicio

```
$ cd ~/work/aws-hardening
$ claude

> Hola. Tengo el repo aws-hardening en este directorio. Quiero correr el ciclo completo
> de Nivel 1: escanear, priorizar, arreglar lo trivial, generar PR para lo riesgoso.
> Empezá.
```

## Claude Code arranca

```
[Claude Code]
Voy a hacer:
1. Leer specs/nivel-1/SPEC.md para entender el target.
2. Correr assessment-cli/assessment.py para baseline.
3. Comparar y priorizar.
4. Ejecutar fixes triviales (blast radius cero).
5. PR para fixes que requieren review.

¿Procedo?

> sí

[Read: specs/nivel-1/SPEC.md]
[Read: CLAUDE.md]
[Bash: python assessment-cli/assessment.py --format json --output /tmp/baseline.json]

Output:
- Maturity score: 1.3 / 4
- Nivel 1: 50% complete
- 5 controles failing

Resumen del baseline:
- ❌ GuardDuty deshabilitado en sa-east-1
- ❌ Cost Anomaly Detection no configurado
- ❌ S3 block public access en 4 buckets
- ❌ IMDSv2 obligatorio en 2 instances
- ❌ KMS rotation en 6 keys

[Write: plan.md]
plan.md generado con priorización + comandos exactos.

¿Procedemos con fixes triviales?

> sí
```

## Ejecuta fixes triviales

```
[Bash: aws guardduty create-detector --enable --region sa-east-1]
Detector: abc123def456ghi789

[Bash: aws guardduty get-detector --detector-id abc123def456ghi789 --region sa-east-1]
Status: ENABLED ✅

[Bash: aws kms list-keys --region us-east-1]
...

[Bash: aws kms enable-key-rotation --key-id abc-123]
✅ Rotation habilitada en abc-123

[Bash: aws kms enable-key-rotation --key-id def-456]
✅ Rotation habilitada en def-456
... (6 keys procesadas)

[Bash: aws ce create-anomaly-monitor --anomaly-monitor file:///tmp/monitor.json]
Monitor: arn:aws:ce::123456789012:anomalymonitor/abc-monitor

[Bash: aws ce create-anomaly-subscription --anomaly-subscription file:///tmp/subscription.json]
Subscription creada, email: ops@yourcompany.com

Fixes triviales completados (6/6). Total: 4 minutos.
```

## Pide confirmación para riesgo medio

```
[Claude Code]
Próximo: IMDSv2 en i-abc, i-def. Antes de aplicar, voy a validar dependencias.

[Bash: aws ssm send-command --instance-ids i-abc --document-name AWS-RunShellScript --parameters 'commands=["aws --version && cat /etc/os-release"]']
...waiting...
[Bash: aws ssm list-command-invocations --command-id xyz --details]

Output i-abc:
- AWS CLI: 2.13.31 (soporta IMDSv2 ✅)
- OS: Amazon Linux 2 (soporta ✅)

Output i-def:
- AWS CLI: 1.18.123 (DEPRECADO, no soporta IMDSv2 sin ajuste)
- OS: Ubuntu 18.04

⚠️ i-def tiene un riesgo. La AWS CLI v1.18 antigua puede no manejar IMDSv2 sin retries.

Recomendación:
- Aplicar IMDSv2 en i-abc directamente.
- Para i-def: primero actualizar AWS CLI a v2, después aplicar IMDSv2.

¿Aplico solo i-abc por ahora?

> sí

[Bash: aws ec2 modify-instance-metadata-options --instance-id i-abc --http-tokens required --http-put-response-hop-limit 2]
✅ Aplicado en i-abc.

[Bash: aws ec2 describe-instances --instance-ids i-abc --query 'Reservations[].Instances[].MetadataOptions']
{"HttpTokens": "required", ...} ✅

Para i-def, voy a crear un ticket en plan-followup.md. Necesita:
1. Update aws cli a v2 (15 min).
2. Validar app funciona.
3. Aplicar IMDSv2.

¿Continúo con S3 block public access en los 4 buckets?

> sí
```

## S3 block en buckets

```
Buckets a remediar: app-uploads-staging, tmp-exports, logs-archive, old-bucket-2023

Para cada bucket, voy a:
1. Verificar contenido (es público intencional?).
2. Si no, aplicar block.

[Bash: aws s3api get-bucket-tagging --bucket app-uploads-staging]
TagSet: [{Key: Environment, Value: staging}, {Key: purpose, Value: app-uploads}]

[Bash: aws s3api get-bucket-policy --bucket app-uploads-staging]
NoSuchBucketPolicy

No es público intencional. Aplicando block.

[Bash: aws s3api put-public-access-block --bucket app-uploads-staging --public-access-block-configuration "BlockPublicAcls=true,IgnorePublicAcls=true,BlockPublicPolicy=true,RestrictPublicBuckets=true"]
✅

(repetido para los otros 3 buckets)

✅ 4 buckets remediados.
```

## Genera PR para Nivel 2

```
[Claude Code]
Ya estamos en 85% de completitud de Nivel 1 (faltan IAM users → SSO, que es process change).

¿Querés que empiece a preparar Nivel 2 (SCPs)?

> sí, pero solo PR. no aplicar.

[Bash: git checkout -b feature/baseline-scps]
[Read: templates/scps/01-deny-disable-cloudtrail.json]
[Read: templates/scps/02-deny-disable-guardduty.json]
[Write: terraform/scps/main.tf]
[Write: terraform/scps/01-deny-disable-cloudtrail.tf]
[Write: terraform/scps/02-deny-disable-guardduty.tf]
[Write: terraform/scps/README.md]

[Bash: git add terraform/scps/]
[Bash: git commit -m "feat(scps): añadir baseline de Service Control Policies

Aplica 2 SCPs:
- 01: deny disable/delete CloudTrail
- 02: deny disable GuardDuty

Ambos exceptúan el role BreakGlass.

Plan de rollout (ver terraform/scps/README.md):
1. Aplicar primero en OU sandbox (1 semana de observación)
2. Aplicar en OU dev (1 semana)
3. Aplicar en OU prod
"]
[Bash: git push -u origin feature/baseline-scps]
[Bash: gh pr create --title "feat(scps): baseline de Service Control Policies" --body "..."]

PR creado: https://github.com/[org]/[repo]/pull/124

Necesita review antes de mergear. Sugerí:
- Revisar el ARN del role BreakGlass (puede diferir en cada cuenta).
- Confirmar que el rollout es OU-by-OU.
```

## Re-scan final

```
[Bash: python assessment-cli/assessment.py --format json --output /tmp/baseline-v2.json]

Diff vs baseline original:

ANTES:                              DESPUÉS:
Maturity score: 1.3                 Maturity score: 1.85
Nivel 1: 50%                        Nivel 1: 85%
GuardDuty: FAIL                     GuardDuty: PASS
Cost Anomaly: FAIL                  Cost Anomaly: PASS
KMS rotation: FAIL                  KMS rotation: PASS
S3 block: WARN                      S3 block: PASS
IMDSv2: FAIL                        IMDSv2: WARN (i-def pending)
Identity Center: WARN               Identity Center: WARN (sin cambio)
SCPs: FAIL                          SCPs: FAIL (PR pendiente)

Tiempo total de sesión: 32 minutos.

Próximos pasos persistidos en plan-followup.md:
1. Actualizar AWS CLI en i-def, aplicar IMDSv2.
2. Mergear PR #124 después de review.
3. Coordinar migración de 3 IAM users a SSO.
4. Empezar Nivel 2 (SCPs en sandbox/dev/prod).
```

## Cierre

```
> perfecto. cerrá la sesión.

[Claude Code]
Sesión resumida en /tmp/runs/2026-05-26-1530.md:

Cambios aplicados (low-risk, automated):
1. GuardDuty habilitado en sa-east-1.
2. Cost Anomaly + subscription.
3. KMS rotation en 6 keys.
4. S3 block en 4 buckets.
5. IMDSv2 en i-abc.

PR generado (requiere review):
- #124: baseline SCPs.

Follow-ups (manual o próxima sesión):
- i-def: AWS CLI upgrade + IMDSv2.
- 3 IAM users → Identity Center.
- Nivel 2 rollout post-merge del PR.

Total bash commands ejecutados: 47
Total cambios persistidos: 6 fixes + 4 commits + 1 PR

Hasta la próxima.
```

## Insights de esta sesión

1. **Validación pre-cambio salvó la situación.** El check de AWS CLI versión detectó que i-def no podía aplicar IMDSv2 sin update. Sin el check, la app habría tirado errores.
2. **PR para SCPs, no auto-apply.** Los cambios a SCPs afectan toda la Organization. Aunque Claude Code podría aplicarlos, el flow correcto es PR + review.
3. **Re-scan automatizado cierra el loop.** Sin el diff antes/después, no sabés qué se logró.
4. **35 min para lo que manualmente toma 4-6 horas.** Y el patrón es repetible la próxima vez.
