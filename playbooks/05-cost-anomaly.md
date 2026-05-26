# Playbook 05: Spike de costo súbito

> Costo súbito puede ser un developer haciendo algo nuevo, una migración planeada, una factura mal calibrada de un servicio, o un compromiso activo. Este playbook te dice cómo distinguir cuál es cuál en menos de 4 horas.

## Trigger

- **Cost Anomaly Detection** alerta de spike (configurada en Nivel 1).
- **Budget alert** sobrepasado.
- **CFO/Finance** llama porque vio la factura del último día.
- Detección manual durante review de billing dashboard.

## Severity

- **Critical** si el spike es >10x el baseline diario.
- **High** si es 3x a 10x.
- **Medium** si es 1.5x a 3x.

Nota: severity es PROVISIONAL hasta el triage. Un spike de 100x puede ser un FP (un developer corriendo training de ML legítimo) o puede ser un atacante (mining). Severity definitiva post-triage.

## SLA

- **Detection a Triage**: 1 hora.
- **Triage a Decisión**: 4 horas.
- **Si es incident, eradication**: 4 a 8 horas.

## Pasos

### 1. Triage (15 minutos)

**A. Caracterizar el spike: por servicio y región.**

```bash
# Cost Explorer query (CLI)
aws ce get-cost-and-usage \
  --time-period Start=2026-05-25,End=2026-05-27 \
  --granularity DAILY \
  --metrics UnblendedCost \
  --group-by Type=DIMENSION,Key=SERVICE \
  --group-by Type=DIMENSION,Key=REGION
```

Mirá:

- ¿Qué servicio aumentó? (EC2, RDS, Bedrock, etc.)
- ¿En qué región?
- ¿Qué porcentaje del costo total representa el aumento?
- ¿Cuándo empezó? (hora específica)

**B. Buscar correlación con eventos.**

```bash
# Listar deploys/cambios recientes en CloudTrail
aws cloudtrail lookup-events \
  --lookup-attributes AttributeKey=EventName,AttributeValue=RunInstances \
  --start-time '2026-05-25T00:00:00Z' \
  --max-items 50 \
  | jq '.Events[] | {Time: .EventTime, User: .Username, Type: .Resources[0].ResourceName}'
```

Cruzar con:

- ¿Hay deploy programado en ese horario?
- ¿Algún equipo notificó migración?
- ¿Hubo Trigger de auto-scaling legítimo?

**C. Bandera roja patterns:**

- Spike en **horario fuera de oficina**, sin deploy programado.
- Spike en **una región sin actividad esperada**.
- Spike en **servicios GPU** (`p3.*`, `p4.*`, `g4.*`, etc.).
- Spike en **outbound data transfer** (señal de exfiltración).
- Spike en **NAT Gateway data processed** (egress masivo).

### 2. Decisión inicial (5 min)

**Camino A: Causa legítima identificada.**

- Documentá la causa.
- Si fue un deploy mal calibrado, ticket de cleanup.
- Si fue un servicio nuevo no presupuestado, conversación con el equipo dueño.
- Cerrar como FP, ajustar threshold si era inadecuado.

**Camino B: Causa NO identificada o sospechosa.**

- Continuar a containment con severity High mínimo.

### 3. Containment (30 minutos, si es Camino B)

**A. Activar SCP de region restriction si el spike es en región no esperada.**

Ver [Playbook 04](./04-unauthorized-region-activity.md).

**B. Si el spike es de EC2 GPU o cantidades sospechosas:**

```bash
# Listar instances en la región del spike
aws ec2 describe-instances --region [REGION] \
  --filters "Name=instance-state-name,Values=running" \
  --query 'Reservations[*].Instances[*].[InstanceId,InstanceType,LaunchTime,Tags]' \
  | head -50

# Para las que parecen sospechosas (GPU, sin tags, recién lanzadas):
# - Snapshot del volume para forensics
aws ec2 create-snapshot --volume-id [VOLUME_ID] --description "IR-snapshot"

# Stop la instance (no terminate)
aws ec2 stop-instances --instance-ids [INSTANCE_ID]
```

**C. Si el spike es de outbound data transfer:**

```bash
# VPC Flow Logs query (si tenés Athena configurado)
SELECT
  srcaddr,
  dstaddr,
  SUM(bytes) as total_bytes
FROM vpc_flow_logs
WHERE start_time >= '2026-05-25 00:00:00'
  AND action = 'ACCEPT'
GROUP BY srcaddr, dstaddr
ORDER BY total_bytes DESC
LIMIT 20;
```

Las IPs `dstaddr` externas con TBs de datos son candidatas a exfil. Blocking them via security group/NACL.

### 4. Eradication (variable, 2 a 6 horas)

**A. Eliminar los recursos del atacante.**

Igual que en [Playbook 04](./04-unauthorized-region-activity.md):

- Snapshot para forensics.
- Terminate/delete.
- Buscar persistence mechanisms.

**B. Si confirmaste credencial comprometida:**

Activar [Playbook 01](./01-leaked-credentials.md) para esa identidad.

**C. Restaurar billing baseline.**

Una vez eliminados los recursos del atacante, el costo debería volver al baseline en 24 a 48 horas (depende de billing cycles).

### 5. Recovery

**A. Análisis de costo total del incident.**

```bash
# Costo del período del incidente
aws ce get-cost-and-usage \
  --time-period Start=[INCIDENT_START],End=[INCIDENT_END] \
  --granularity DAILY \
  --metrics UnblendedCost
```

Diferencia con el baseline = costo del incidente.

**B. Si el costo fue significativo:**

- AWS Support case con detalles. AWS suele dar credit por compromisos.
- Documentación de impacto financiero.
- Si hubo exfil, costos secundarios (notificaciones, remediation a clientes, multas regulatorias).

**C. Comunicación.**

- Al CFO/Finance: costos del incident, mitigación, prevención futura.
- Al equipo dueño de la credencial: por qué ocurrió, qué cambia.
- A management: severity y mitigación.

### 6. Post-mortem (1 semana)

Énfasis en:

1. **Costo total.** Sumar billing del período + tiempo de equipo en responder + impacto secundario.
2. **Cómo entró el atacante.** El root cause de la credencial comprometida.
3. **Por qué no se detectó antes.** ¿Cost Anomaly threshold estaba bien? ¿Por qué pasó tiempo?
4. **Qué hubiera prevenido el incident.** SCPs, MFA, rotación de keys, etc.
5. **Action items.**
   - Mejoras al detection.
   - Mejoras al containment.
   - Mejoras al process de credencial management.

## Anti-patterns

- ❌ **Cerrar como FP porque "el spike no fue tan grande".** Mining y exfil de baja intensidad pueden ser de baja magnitud pero sostenidos.
- ❌ **Llamar al CFO antes de hacer triage técnico.** Generás pánico organizacional innecesario.
- ❌ **Stop instances y olvidarse.** Sin snapshot, sin investigación de credencial, sin búsqueda de persistence: el atacante vuelve.
- ❌ **No pedirle credit a AWS.** Para compromisos confirmados, AWS suele cubrir parte del costo.

## Automatización

### Fase 1: Manual

Humano sigue el playbook.

### Fase 2: Asistido

Script que da triage rápido:

```bash
./scripts/cost-spike-triage.sh --start 2026-05-25 --end 2026-05-27
# Output: services con spike, regions afectadas, identidades involucradas
```

### Fase 3: Semi-automático

EventBridge sobre Cost Anomaly + correlation con CloudTrail:

```
Trigger: Cost Anomaly Detection
   ↓
Lambda 1: Caracterizar spike (servicio, región, monto)
   ↓
Lambda 2: Buscar correlación con deploys/changes recientes
   ↓
Lambda 3: Si NO hay correlation, snapshot de recursos sospechosos
   ↓
Lambda 4: Notificar on-call con triage report
   ↓
Human: decide siguiente paso
```

### Fase 4: Automático

No recomendado para este playbook. La diferencia entre "spike legítimo" y "spike sospechoso" requiere contexto humano.

## Métricas

- **Time to detect**: tiempo entre primer cargo anómalo y alerta.
- **Time to triage**: tiempo entre alerta y decisión Camino A/B.
- **Cost of incident**: dólares atribuibles al incident.
- **AWS credit obtenido**: porcentaje del costo cubierto post-claim.

## Recursos

- [AWS Cost Anomaly Detection](https://docs.aws.amazon.com/cost-management/latest/userguide/getting-started-ad.html)
- [AWS Compute Optimizer](https://docs.aws.amazon.com/compute-optimizer/)
- [CUR (Cost and Usage Report) en Athena](https://docs.aws.amazon.com/cur/latest/userguide/cur-query-athena.html)
- [AWS Support: claim por compromise](https://aws.amazon.com/premiumsupport/)
