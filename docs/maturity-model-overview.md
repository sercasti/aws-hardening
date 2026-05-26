# El Security Maturity Model en una página

> Resumen del modelo de Darío Goldfarb (Senior PSA en AWS), adaptado al tono y vocabulario del talk. El modelo original vive en [maturitymodel.security.aws.dev](https://maturitymodel.security.aws.dev).

## Por qué el modelo

El modelo existe para responder a una pregunta que aparece todos los días en cualquier equipo cloud:

> "¿Por dónde empiezo con seguridad?"

Antes de tener el modelo, las respuestas eran:

- "Empezá por todo lo que dice CIS." (paraliza a cualquiera).
- "Empezá por lo que más te asusta." (subjetivo, lleva a sobrecorregir).
- "Contratá un consultor." (caro, no escalable).
- "Después del próximo incidente." (caro de otra manera).

El modelo provee una secuencia ordenada de niveles, cada uno con criterio claro de "listo" y dependencia explícita en el anterior.

## Los 4 niveles

```
┌─────────────────────────────────────────────────────────────┐
│  Nivel 1: El Despertar (Awakening)                          │
│  Ves lo que está pasando. Quick wins. Dias.                 │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Nivel 2: Los Cimientos (Foundational)                      │
│  Configurás lo crítico. SCPs, IAM baseline. Semanas.        │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Nivel 3: La Atalaya (Continuous Surveillance)              │
│  Vigilancia continua, detection-as-code, IR runbooks. Meses │
└─────────────────────────────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│  Nivel 4: La Ciudadela (Continuous Program)                 │
│  Programa continuo. Red/blue team, métricas, gov. Trimestre │
└─────────────────────────────────────────────────────────────┘
```

## Nivel 1: El Despertar

**Pregunta que responde:** "¿Qué tengo? ¿Quién está dentro?"

**Controles principales:**

- MFA habilitada en el usuario root.
- CloudTrail multi-region con file integrity.
- GuardDuty activado en todas las regions usadas.
- IAM Access Analyzer activo.
- Cost Anomaly Detection con alertas.
- AWS Budgets configurados.
- S3 block public access a nivel cuenta.
- Identity Center configurado (no IAM users humanos).

**Costo:** $0 (todo free tier o incluido).

**Tiempo:** 1 a 5 días de un engineer.

**Boss fight (criterio de "listo"):** detectar y desactivar todas las cuentas IAM humanas inactivas o sin dueño en tu cuenta. Si no podés hacer eso, no estás en Nivel 1.

**Filosofía del nivel:** después de Nivel 1, dormís mejor. No porque la cuenta esté blindada, sino porque cualquier cosa rara va a generar una alerta.

## Nivel 2: Los Cimientos

**Pregunta que responde:** "¿Cómo evito errores comunes?"

**Controles principales:**

- Service Control Policies (SCPs) básicos:
  - Deny disable CloudTrail.
  - Deny disable GuardDuty.
  - Deny regions fuera de la lista permitida.
  - Require IMDSv2.
  - Deny root user actions.
  - Deny IAM user creation.
  - Deny make S3 public.
- IAM baseline policies adjuntas a roles.
- KMS rotation habilitada en CMKs customer-managed.
- VPC Flow Logs en todos los VPCs.
- IMDSv2 obligatorio en todas las EC2.

**Costo:** $0 (SCPs son gratis; algunos servicios pueden generar costos secundarios).

**Tiempo:** 1 a 4 semanas. La parte que tarda no es el código del SCP. Es el rollout (audit → dev → prod) y el ajuste de excepciones.

**Boss fight:** aplicar tu primer SCP a producción sin romper builds ni deploys. Si no podés, falta process o falta entendimiento.

**Filosofía del nivel:** los errores van a pasar. Tu trabajo es hacerlos imposibles antes de que ocurran.

## Nivel 3: La Atalaya

**Pregunta que responde:** "¿Cómo me entero rápido cuando algo pasa?"

**Controles principales:**

- AWS Security Hub habilitado en todas las regions, con aggregator.
- Detection-as-code (rules versionadas en git).
- Logs centralizados (un solo bucket S3 receptor de CloudTrail, VPC Flow Logs, app logs).
- AWS Config rules para drift detection.
- Macie para data discovery (si manejás PII).
- Playbooks de Incident Response documentados (ver `/playbooks/`).
- On-call rotation definido.

**Costo:** $ (Security Hub, Macie, Config tienen costos por evaluación/escaneo).

**Tiempo:** 1 a 3 meses. La automation toma tiempo de hacer bien.

**Boss fight:** automatizar tu primer playbook de IR de punta a punta. Cuando GuardDuty detecte un finding del tipo X, una Lambda hace Y, notifica Z, y vos recibís el reporte para revisar al día siguiente.

**Filosofía del nivel:** detectás rápido (minutos, no semanas) y respondés rápido. Los humanos se enfocan en decisiones, no en clicks.

## Nivel 4: La Ciudadela

**Pregunta que responde:** "¿Cómo lo sostengo, mejoro, y demuestro que funciona?"

**Controles principales:**

- Métricas de seguridad reportadas continuamente.
- Red team ejercicios trimestrales (interno o externo).
- Blue team con runbook actualizado mensualmente.
- Continuous control monitoring (no point-in-time audits).
- Threat modeling integrado al SDLC.
- Compliance automation (si aplica tu industria).
- Governance: roles definidos, accountability clara, escalation paths.
- Cultura: security champions en cada equipo de producto.

**Costo:** $$ (red team externo, tools de continuous monitoring, tiempo de gente).

**Tiempo:** continuo. Nunca llegás a Nivel 4 y parás. Estás en Nivel 4 manteniendo el nivel.

**Boss fight:** ningún incident grave en los últimos 12 meses, con métricas para probarlo. Y cuando hubo incidents menores, tiempo de respuesta menor a SLA. Y el equipo siente que la seguridad acelera su trabajo, no que lo frena.

**Filosofía del nivel:** la seguridad es un atributo continuo del sistema, no una tarea separada. Está embebida en cómo se construye.

## Cómo medirte

Cada nivel tiene una proporción de completitud:

```
Score = (controles en place / total de controles del nivel)
```

Y el maturity score general:

```
Maturity = promedio_ponderado(completitud por nivel)
```

La CLI en `/assessment-cli/` te calcula esto automáticamente.

**Targets pragmáticos:**

- 100% de Nivel 1 antes de invertir tiempo en Nivel 2.
- 80% de Nivel 2 antes de Nivel 3.
- 70% de Nivel 3 antes de Nivel 4.

No vale "tenemos Security Hub habilitado, entonces estamos en Nivel 3". Si el Nivel 1 está al 50%, primero terminás Nivel 1.

## Anti-patterns clásicos

- ❌ **"Saltearse niveles".** Aplicar Security Hub sin tener Nivel 1 al 100%: tu Security Hub te alerta sobre cosas que ya deberías saber.
- ❌ **"Solo automation, sin process".** Lambdas hacen cosas, pero nadie sabe por qué.
- ❌ **"Solo process, sin automation".** Compliance papers en Confluence, ningún control técnico que los apoye.
- ❌ **"Achievement unlocked, nunca más miramos".** Sin re-evaluación periódica, los controles drift.

## Referencias

- [Modelo original (Darío Goldfarb)](https://maturitymodel.security.aws.dev)
- [AWS Security Hub](https://aws.amazon.com/security-hub/)
- [CIS AWS Foundations Benchmark](https://www.cisecurity.org/benchmark/amazon_web_services)
- Specs detalladas en este repo: [`/specs/`](../specs/)
