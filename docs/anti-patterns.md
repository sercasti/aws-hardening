# Anti-patterns: errores comunes en hardening AWS

> Lista curada de errores que vi (o cometí) en proyectos de hardening. Agrupada por dominio. Cada anti-pattern tiene por qué pasa, las consecuencias, y cómo evitarlo.

## Identity & access

### "Compartir credenciales por Slack para resolver rápido"

**Por qué pasa:** Urgencia. Engineer A necesita acceso, no tiene tiempo de configurar SSO.

**Consecuencias:** La credencial queda en Slack history para siempre. Si Slack se compromete (o el workspace de Slack se inactiva mal), tu credencial sigue afuera.

**Cómo evitarlo:** Identity Center con permission sets temporales. Si el engineer A no debería tener acceso ahora, no debería tenerlo nunca.

### "IAM users con AdministratorAccess para developers"

**Por qué pasa:** Es lo más fácil. Funciona para todo.

**Consecuencias:** Cualquier comprometimento del developer compromete toda la cuenta. PR malicioso a tu repo de IaC = atacante asume el rol.

**Cómo evitarlo:** Least privilege. Si el developer no usa `iam:*`, no se lo des. Tools como IAM Access Analyzer Last-Accessed te muestran qué realmente usaron en 90 días.

### "Long-lived access keys"

**Por qué pasa:** Es lo más simple para CI/CD legacy. Rotar es trabajo.

**Consecuencias:** Key leaked = atacante autenticado por meses. Las keys aparecen en GitHub público con scanning automatizado.

**Cómo evitarlo:** OIDC para CI/CD (GitHub Actions, GitLab CI, Bitbucket Pipelines tienen integración nativa). Para humanos: SSO + session tokens cortos.

### "El IAM role tiene todo el bundle por las dudas"

**Por qué pasa:** Engineer no sabe qué permisos exactos necesita la app, así que pone `s3:*, ec2:*, kms:*` "para que ande".

**Consecuencias:** SSRF en la app permite al atacante usar todos esos permisos.

**Cómo evitarlo:** IAM Access Analyzer "Last-Accessed". Después de 30 días, revisa qué usó la app realmente. Trim el role a eso.

## Logging & detection

### "GuardDuty solo en us-east-1"

**Por qué pasa:** Es donde están los recursos visibles. Las otras regiones "no tienen nada".

**Consecuencias:** Atacante levanta mining en ap-south-1, descubierto un mes después por el billing alert. GuardDuty habría detectado en horas.

**Cómo evitarlo:** GuardDuty habilitado en TODAS las regions, no solo las activas. El costo de regiones sin activity es ~$0.

### "CloudTrail sin file integrity validation"

**Por qué pasa:** No se sabía que existía. La default check no lo activa.

**Consecuencias:** Atacante con permisos puede modificar logs históricos (`PutObject` a la key del log file). Sin integrity check, no detectás.

**Cómo evitarlo:** `--enable-log-file-validation` al crear el trail. Y SCP que bloquea `cloudtrail:StopLogging`.

### "Logs solo en CloudWatch Logs (no exportados)"

**Por qué pasa:** Más simple. Vienen ya en la consola.

**Consecuencias:** Si el atacante compromete la cuenta, puede borrar log groups. Sin export a otra cuenta, perdés evidencia.

**Cómo evitarlo:** Subscription filter de CloudWatch Logs a S3 en una cuenta separada (logging account). El atacante de la cuenta source no puede tocar la cuenta destino.

### "Alertas a un email de un dueño que se fue"

**Por qué pasa:** Persona armó el setup, se fue, nadie actualizó.

**Consecuencias:** Alertas legítimas no llegan. El siguiente incidente se entera por un cliente o la factura.

**Cómo evitarlo:** Alertas a una lista (`ops@`, `security@`), no a una persona. Auditar las subscriptions trimestralmente.

## Network & data

### "S3 bucket público para servir archivos del sitio"

**Por qué pasa:** Es la solución obvia. Funciona.

**Consecuencias:** Cuando un developer accidentalmente sube algo sensible (config, dump de BD), se hace público sin que nadie note.

**Cómo evitarlo:** CloudFront en frente de S3 con OAC. El bucket queda privado, CloudFront sirve público. Beneficio extra: CDN.

### "VPC sin Flow Logs"

**Por qué pasa:** Costo percibido (los Flow Logs cuestan algo).

**Consecuencias:** Cuando hay exfil, no podés determinar volumen ni destinos.

**Cómo evitarlo:** Flow Logs a S3 con compresión. Costo real: ~$0.50 por TB de log. Vale cada centavo en un incident.

### "Outbound a internet abierto desde private subnets"

**Por qué pasa:** "Las apps necesitan llamar APIs externas, NAT Gateway abierto es lo más simple."

**Consecuencias:** Exfil de data se ve igual que tráfico legítimo. SSRF en la app puede llamar instance metadata o servicios internos.

**Cómo evitarlo:** Egress controlado: VPC endpoints para servicios AWS internos, proxy con allowlist para externos. NAT Gateway solo para casos justificados.

### "RDS publicly accessible: true"

**Por qué pasa:** Engineer prueba conectividad desde su laptop, se queda así.

**Consecuencias:** Tu BD está exposed a internet. Scanners la encuentran en horas.

**Cómo evitarlo:** SCP que bloquea `rds:ModifyDBInstance` cuando `PubliclyAccessible=true`. Y proxy bastion o SSM Session Manager para acceso temporal.

## Cost & monitoring

### "Sin budget alerts"

**Por qué pasa:** No se configuraron al setup. Después nadie se acuerda.

**Consecuencias:** Mining attack o app con leak puede generar $50k antes que alguien note (vía factura mensual).

**Cómo evitarlo:** Budget alerts mensual + Cost Anomaly Detection con threshold bajo. Mínimo $50 monitor por servicio.

### "Cost Anomaly threshold demasiado alto"

**Por qué pasa:** Configurado al setup cuando la cuenta era chica. Org creció, threshold quedó relativo.

**Consecuencias:** El threshold protege de mining pero no de SaaS bills no-deseados o regions con activity sospechosa de baja intensidad.

**Cómo evitarlo:** Threshold como % del baseline, no fijo. Re-evaluar trimestralmente.

### "Tag policy sin enforcement"

**Por qué pasa:** Aplicada como guideline, no como SCP.

**Consecuencias:** Tags faltantes en recursos significan: no podés atribuir costo, no podés auditar dueño, no podés aplicar lifecycle.

**Cómo evitarlo:** Tag policy + SCP que bloquea creación sin tags obligatorios. Pain inicial, sanity de largo plazo.

## SCPs

### "SCPs aplicados directamente a producción"

**Por qué pasa:** "Es un cambio chico, no rompe nada."

**Consecuencias:** Rompe un caso edge que nadie tenía documentado. CI/CD frenado, equipo de producto frenado, leadership furioso.

**Cómo evitarlo:** Rollout sandbox → dev → prod, 1 a 2 semanas entre stages. SCPs siempre con rollback plan documentado.

### "SCPs con Allow exhaustivo"

**Por qué pasa:** "Para estar seguros de no romper nada, voy a permitir TODO lo que veo."

**Consecuencias:** El SCP no protege nada. Es boilerplate.

**Cómo evitarlo:** Deny específico de acciones peligrosas + Allow implícito de lo demás. Más simple, más efectivo.

### "Quitar SCPs cuando rompen builds"

**Por qué pasa:** Pressure del equipo de producto.

**Consecuencias:** El SCP existía por una razón. Sin él, la razón vuelve.

**Cómo evitarlo:** Documentar la excepción (ver `templates/scp-exception-template.md`). Investigar por qué el build necesita el path bloqueado. Frecuentemente el build es lo que está mal.

## Incident response

### "Cerrar el ticket sin post-mortem"

**Por qué pasa:** Resuelto el síntoma. "No vale la pena."

**Consecuencias:** Sin entender la causa, vuelve a pasar. La segunda vez es más grave.

**Cómo evitarlo:** Post-mortem obligatorio para Sev1 y Sev2. Sin foco en blame. Foco en process & technical changes.

### "Borrar evidencia para 'cerrar más rápido'"

**Por qué pasa:** Limpieza percibida. Eficiencia.

**Consecuencias:** Sin evidencia, no podés probar qué pasó (regulatorio), no podés mejorar (post-mortem queda inconcluso).

**Cómo evitarlo:** Snapshot/backup primero, después containment/eradication. Tag `do-not-delete` con fecha de retención.

### "Mantener al atacante en la cuenta mientras decidimos"

**Por qué pasa:** "Queremos ver qué hace para entender."

**Consecuencias:** Cada minuto adicional puede ser más exfil, más persistence. Tu observación es cara.

**Cómo evitarlo:** Containment rápido (revoke credentials, isolate networks). Si querés watching, hacelo en honeypot o test environment, no en prod.

### "Comunicar internamente por Slack durante incident grave"

**Por qué pasa:** Slack es lo más rápido.

**Consecuencias:** Si el atacante tiene acceso a Slack, lee tu plan de respuesta en tiempo real.

**Cómo evitarlo:** Out-of-band: Signal grupal, llamada por teléfono, war room físico. Slack solo para coordinación de bajo nivel.

## Cultural

### "Security es problema del equipo de Security"

**Por qué pasa:** División tradicional de responsabilidades. "No es mi job."

**Consecuencias:** El equipo de Security se vuelve un bottleneck. Engineering desarrolla con shortcuts que después Security tiene que cazar.

**Cómo evitarlo:** Security embedded en cada equipo (champion model). Security team facilita, no aprueba todo.

### "Auditorías una vez al año"

**Por qué pasa:** Modelo legacy heredado de compliance world.

**Consecuencias:** Drift acumulado durante 12 meses. Audit produce 200 findings imposibles de remediar.

**Cómo evitarlo:** Continuous control monitoring. El drift se detecta en horas, no en meses.

### "El CTO no entiende, no quiero proponer"

**Por qué pasa:** Engineers asumen que leadership no va a apoyar.

**Consecuencias:** Iniciativas de seguridad nunca se aprueban porque nunca se proponen.

**Cómo evitarlo:** Framing en business terms. "Esto reduce el riesgo de costo no esperado por X" en lugar de "esto es best practice". CTOs entienden ROI.

### "Toolset cambia cada año, nada queda"

**Por qué pasa:** Hype cycle. Nueva tool aparece, se compra, se abandona.

**Consecuencias:** Engineers se cansan de aprender tools. Nada queda integrado.

**Cómo evitarlo:** Foco en process, no en tools. Una vez que el process está, las tools son intercambiables.

## AI agents (relevante para este repo)

### "El agente generó código, lo mergeo"

**Por qué pasa:** Fatiga de revisión. El agente "sabe más".

**Consecuencias:** Bug del agente entra a prod. Si era SCP, rompe la Organization. Si era IAM, abre paths de escalación.

**Cómo evitarlo:** Cada output del agente requiere review. Aunque sea 30 segundos. La revisión cierra los gaps donde el agente alucina.

### "Pasarle credenciales reales al agente"

**Por qué pasa:** Es lo más simple. Funciona.

**Consecuencias:** Si el prompt es manipulado (prompt injection), el agente puede ejecutar acciones inesperadas. Si el agente loguea, las credenciales quedan en el log.

**Cómo evitarlo:** Roles temporales con least privilege. Si el agente solo necesita ver, dale ReadOnly. Si necesita modificar, role con `aws:RequestTag` constraint.

### "Sin specs, esperar que el agente decida"

**Por qué pasa:** Specs son trabajo.

**Consecuencias:** El agente decide por defaults genéricos que no se ajustan a tu org. Cuando el output no sirve, culpás al agente.

**Cómo evitarlo:** Specs como contrato. Sin spec, el agente no tiene cómo hacer bien las cosas que importan en tu contexto.

### "Un solo agente para review y generación"

**Por qué pasa:** Más simple.

**Consecuencias:** El agente "aprueba" su propio código. Cierre del loop sin segundo opinion.

**Cómo evitarlo:** Dos agentes (o uno con dos prompts MUY distintos). Si discrepan, vos decidís.

## Conclusión

Los anti-patterns no son fallas individuales. Son patrones del sistema: las decisiones racionales en el momento se acumulan en mal estado global.

La buena noticia: los anti-patterns son recurrentes. Una vez que los identificás, los podés evitar (o al menos hacer la elección consciente de aceptarlos).

Si hay anti-patterns que sufriste y no están acá, abrí un PR. Más cobertura ayuda a más gente.
