# Blast Radius (antes de aplicar cualquier cambio)

> Cinco minutos de este prompt te evitan un incidente. Le pasás un cambio propuesto (PR, SCP, policy update) y te dice qué se rompe si la mandás.

## Cuándo usarlo

- Antes de aplicar cualquier SCP en enforce mode.
- Antes de mergear una PR de Terraform que toca IAM o redes.
- Antes de rotar una credencial que múltiples servicios consumen.
- Antes de cambiar el bucket policy de un S3 que escuchan otras cuentas.

## La regla

Si el blast radius calculado supera 1 cuenta, el cambio NO se aplica unilateral. Va al humano (Slack, change advisory board, on-call meeting) antes del merge.

## El prompt

```
Rol: Sos un Site Reliability Engineer con foco en blast radius assessment para
cambios de infraestructura AWS. Tu trabajo es responder, en menos de 5 minutos,
qué se rompe si aplicamos un cambio propuesto.

Contexto: Voy a darte:
1. El cambio propuesto (PR diff, SCP JSON, policy update, comando AWS CLI, lo
   que sea).
2. Mi inventario actual: cuentas, regiones, workloads críticos.
3. Las dependencias conocidas entre workloads (lo que sé yo, no lo que no sé).

Tarea: Calculame el blast radius. Quiero saber:

1. Qué workloads se ven afectados, directamente.
2. Qué workloads se ven afectados, transitivamente (a través de IAM cross-account,
   shared resources, etc.).
3. Estimación de severidad por workload:
   - critical: workload se cae completamente
   - high: workload pierde funcionalidad parcial
   - medium: workload sigue funcionando pero hay degradación o latencia
   - low: cambio cosmético, no impacta runtime
4. Estimación de detección:
   - immediate: monitoring lo detecta en menos de 5 minutos
   - delayed: tarda 1 hora o más
   - silent: solo se descubre cuando un usuario se queja
5. Estimación de rollback:
   - trivial: un comando, menos de 5 minutos
   - moderate: requiere coordinación, 30 minutos a 2 horas
   - hard: requiere restaurar desde backup, varias horas
   - irreversible: pérdida de datos permanente

Output esperado:

# Resumen
[1 línea: blast radius level (low/medium/high/extreme), recomendación
(aplicar / aplicar con monitoreo / esperar coordinación / NO aplicar)]

# Workloads afectados directos
[Tabla: workload, cuenta, severidad, justificación de una frase]

# Workloads afectados transitivos
[Misma tabla, con la cadena de dependencia explícita]

# Cuándo aplicar
[ventana sugerida: ahora, próximo deploy window, fin de semana, never]

# Antes de aplicar
[Lista de gates a tener resueltos antes del merge]

# Plan de rollback
[Pasos concretos para revertir]

# Comunicación previa requerida
[Quién tiene que saber antes: equipos, canales]

Guardrails:
- NO subestimes el blast radius. Si tenés dudas, sumalo a la severidad, no lo
  bajes.
- Si el cambio toca CloudTrail, GuardDuty, IAM root, o el organization
  management account, marcalo como "extreme" automáticamente.
- Si el cambio toca redes (VPC, route tables, security groups) en producción,
  marcalo como mínimo "high".
- NO digas "depende de tu setup". Si te falta data, pedí el comando específico
  para obtenerla.
- Si encontrás que el cambio en cuestión no se puede revertir sin recrear el
  recurso, decílo BIEN GRANDE arriba del reporte.
```

## Mi inventario (template)

Para no copiar y pegar este header cada vez, mantenelo en un archivo `inventory.md` en tu directorio:

```markdown
# Inventario

## Cuentas
- 111111111111 (prod): EKS prod cluster, RDS Postgres prod, S3 data lake
- 222222222222 (staging): EKS staging, RDS Postgres staging, S3 logs
- 333333333333 (dev): Lambda + DynamoDB + S3 dev
- 444444444444 (security): GuardDuty admin, centralized logging, IAM Identity Center
- 555555555555 (sandbox): playground, low constraint

## Regiones
- us-east-1: principal, todos los workloads
- eu-west-1: secundario, prod tiene DR ahí

## Dependencias críticas
- prod EKS asume role en security para escribir logs
- staging y dev consumen Parameter Store en prod (para acceder a APIs externas
  compartidas)
- dev tiene VPC peering con prod (para integration tests)

## Pipelines
- GitHub Actions deployea a dev en cada PR merge a main
- Deploy a staging es manual via GitHub Actions
- Deploy a prod requiere approval de SRE on-call
```

Cuando uses el prompt, pegale primero este inventario, después el cambio propuesto.

## Ejemplo de uso

Cambio propuesto:

```hcl
resource "aws_iam_policy" "lambda_execution" {
  name = "lambda-execution"
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Effect = "Allow"
      Action = ["s3:*"]
      Resource = "*"
    }]
  })
}
```

Output esperado del prompt: blast radius "high", porque "s3:*" en Resource "*" significa que cualquier lambda que asuma este role tiene acceso a todos los buckets de la cuenta, incluyendo logs centralizados, backups, y data sensible. Recomendación: NO aplicar, ajustar Resource a los buckets específicos.

## Iterando

Si el agente dice "high" pero crees que es overkill:

```
Justificame por qué el blast radius es high y no medium. Asumiendo que esta
lambda solo lee del bucket X, ¿qué escenario hipotético hace que el blast
radius sea high?
```

El agente tiene que explicar el escenario de explotación. Si no puede, el rating baja. Si puede y el escenario es plausible, te quedó claro por qué.
