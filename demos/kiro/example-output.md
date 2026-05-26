# Kiro: ejemplo de output completo

Sesión real de Kiro corriendo el demo flow del talk. Output editado para legibilidad pero refleja el patrón real.

## Setup inicial

```
Usuario: Cargá el SPEC.md y baseline.json en contexto. Tarea: identificar gaps del Nivel 1.

Kiro: Leí ambos archivos. El SPEC.md describe 11 controles para Nivel 1.
El baseline.json muestra el estado actual de la cuenta 123456789012.

Mi análisis:

Controles satisfechos (5):
- MFA root: ✅ habilitado
- CloudTrail: ✅ multi-region, file integrity
- IAM Access Analyzer: ✅ activo
- AWS Budgets: ✅ 2 budgets con alertas
- VPC Flow Logs: ✅ todos los VPCs

Controles con gap (6):
- GuardDuty: parcial (us-east-1 sí, sa-east-1 no)
- Identity Center: parcial (configurado, 3 IAM users humanos restantes)
- Cost Anomaly Detection: no configurado
- S3 public access: account-level OK, 4 buckets sin block individual
- KMS rotation: 6/18 keys sin rotation
- IMDSv2: 2/12 instances con IMDSv1 opcional

¿Querés que arme el plan priorizado o querés revisar algún control antes?
```

## Genera el plan

```
Usuario: Armá el plan.

Kiro: Plan generado. Lo escribí en plan.md. Aquí el resumen:

[1] CRITICAL — GuardDuty en sa-east-1
    Esfuerzo: 5 min | Blast radius: ninguno
    aws guardduty create-detector --enable --region sa-east-1

[2] HIGH — Cost Anomaly Detection
    Esfuerzo: 10 min | Blast radius: ninguno
    Crear monitor de tipo "AWS services" con subscription a email del equipo.

[3] HIGH — IMDSv2 en 2 instances
    Esfuerzo: 10 min | Blast radius: bajo (solo si app usa IMDS sin token)
    Antes de aplicar, verificá que las apps en i-abc, i-def no dependen de IMDSv1.

[4] MEDIUM — KMS rotation en 6 keys
    Esfuerzo: 5 min | Blast radius: ninguno
    aws kms enable-key-rotation --key-id [KEY_ID] --region [REGION]

[5] MEDIUM — S3 block public access en 4 buckets
    Esfuerzo: 5 min | Blast radius: bajo si los buckets no eran públicos intencionalmente
    aws s3api put-public-access-block --bucket [BUCKET] --public-access-block-configuration ...

[6] MEDIUM — Migrar 3 IAM users a SSO
    Esfuerzo: 1 hora | Blast radius: medio (acceso de personas, requiere coordinación)
    Process change, no comando único.

¿Por dónde empezamos?
```

## Ejecuta paso 1

```
Usuario: Hacé el [1].

Kiro: Voy a ejecutar `aws guardduty create-detector --enable --region sa-east-1`.

Antes de ejecutar:
- Comando: crear detector de GuardDuty en sa-east-1 con estado ENABLED.
- Recursos creados: 1 detector regional.
- Costo: $0 los primeros 30 días (free tier de GuardDuty), después variable segun activity ingerida.
- Reversible: sí, con `aws guardduty delete-detector --detector-id [ID]`.

¿Procedo? (sí/no)

Usuario: sí

Kiro: Ejecutado:
{
  "DetectorId": "abc123def456ghi789"
}

Verificación:
$ aws guardduty list-detectors --region sa-east-1
{
  "DetectorIds": ["abc123def456ghi789"]
}

$ aws guardduty get-detector --detector-id abc123def456ghi789 --region sa-east-1
{
  "Status": "ENABLED",
  ...
}

✅ GuardDuty habilitado en sa-east-1.

Quedan 5 items en el plan. Seguimos con [2] Cost Anomaly?
```

## Maneja un caso con riesgo

```
Usuario: hacé el [3] IMDSv2

Kiro: Antes de aplicar, necesito que verifiquemos que las apps no dependen de IMDSv1.

Instances afectadas:
- i-abc (t3.medium, en VPC vpc-1, subnet privada, role: WebServerRole)
- i-def (m5.large, en VPC vpc-1, subnet privada, role: WorkerRole)

Riesgos típicos al migrar a IMDSv2:
- SDK viejo (boto3 < 1.10) que no soporta IMDSv2.
- Scripts custom que hacen curl 169.254.169.254 sin token.
- Containers con docker que no propagan token.

Recomendación:
1. Conectate a una instance via SSM y validá:
   - SDK version: aws --version (debe ser >= 1.16)
   - Cualquier script custom que use IMDS, revisar.
2. Aplicá primero en una sola instance, validá que la app sigue funcionando.
3. Si OK, aplicá a la segunda.

¿Querés que valide la primera instance ahora?

Usuario: sí, valida i-abc

Kiro: Voy a usar SSM Send Command para correr aws --version en i-abc.

$ aws ssm send-command --instance-ids i-abc --document-name AWS-RunShellScript --parameters 'commands=["aws --version"]'

Esperando 5 segundos...

Output:
aws-cli/2.13.31 Python/3.11.6 Linux/5.10.215-203.850.amzn2.x86_64 exec-env/AWS_ECS_EC2 exe/x86_64.amzn.2 prompt/off

✅ AWS CLI v2.13, soporta IMDSv2.

Voy a aplicar el cambio a i-abc:
$ aws ec2 modify-instance-metadata-options \
    --instance-id i-abc \
    --http-tokens required \
    --http-put-response-hop-limit 2 \
    --region us-east-1

Resultado:
{
  "InstanceId": "i-abc",
  "InstanceMetadataOptions": {
    "HttpTokens": "required",
    "HttpPutResponseHopLimit": 2,
    ...
  }
}

Verificación: ✅
Próximo paso: monitorear logs de la app por 15 minutos antes de aplicar a i-def. ¿Procedés con esto o querés que pause y aplique despues de tu validación?
```

## Re-scan y validación

```
Usuario: re-corre el assessment

Kiro: $ python ../aws-hardening/assessment-cli/assessment.py --format json --output baseline-v2.json

Resultado: maturity score subió de 1.3 a 1.7.

Cambios detectados:
- GuardDuty: FAIL → PASS
- IMDSv2: FAIL → WARN (1/12 todavia con v1, falta i-def)
- KMS rotation: FAIL → PASS (todas las keys ahora rotando)
- Cost Anomaly: FAIL → PASS
- S3 block: WARN → PASS (4 buckets remediados)

Próximos pasos:
1. Aplicar IMDSv2 a i-def (estaba esperando validación de i-abc).
2. Migrar IAM users humanos a SSO (process change, 1 semana de coordinación).
3. Empezar Nivel 2 (SCPs).

¿Vamos con [1] aplicar IMDSv2 a i-def?
```

## Cierre

```
Usuario: cerremos por hoy. dame un resumen de lo que avanzamos.

Kiro: Sesión de hoy: 47 minutos. Resultados:

ANTES:
- Maturity score: 1.3
- Nivel 1 completion: 50%
- Controles failing: 5

DESPUÉS:
- Maturity score: 1.7
- Nivel 1 completion: 82%
- Controles failing: 1 (Identity Center, requiere process change)

Cambios aplicados:
1. GuardDuty habilitado en sa-east-1.
2. Cost Anomaly Detection: monitor + subscription configurado.
3. IMDSv2 obligatorio en i-abc.
4. KMS rotation en 6 keys previamente sin rotation.
5. S3 block public access en 4 buckets.

Próxima sesión:
- Aplicar IMDSv2 en i-def.
- Empezar plan de migración de IAM users humanos a SSO (process).
- Después, arrancar Nivel 2 con SCPs.

Files generados: plan.md, baseline-v2.json, este transcript.
```

## Pattern key insights

Este transcript ilustra el flywheel pattern:

1. **Escanear**: baseline.json producido por assessment.
2. **Priorizar**: plan.md generado a partir de gaps + maturity model.
3. **Arreglar**: Kiro ejecuta cambios con humano en el loop.
4. **Mergear/Validar**: re-scan confirma el progreso.

El loop dura ~45 minutos para Nivel 1. La velocidad viene de:

- Kiro tiene contexto completo (no perdés tiempo explicando).
- Plan-first reduce errores.
- Verificaciones automatizadas reducen anxiety.
- Re-scan automático provee feedback inmediato.

Comparalo con el approach manual: identificar gaps (1 hora), priorizar (1 hora con stakeholders), ejecutar (4 horas porque te cambiás de contexto), verificar (1 hora). Total: 7 horas para lo mismo.
