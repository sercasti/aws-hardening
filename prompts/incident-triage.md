# Incident Triage

> GuardDuty te tira un finding a las 3 AM. ¿Es un incidente real o un falso positivo? Este prompt te triages en menos de 5 minutos para saber si tenés que despertar al equipo o esperar a la mañana.

## Cuándo usarlo

- Cuando GuardDuty, Security Hub, Inspector, o cualquier herramienta te tira un finding y no estás seguro de la severidad real.
- Cuando un usuario reporta "algo raro" en AWS y necesitás validar si hay incidente.
- Cuando un compañero te llama porque "vio algo en CloudTrail que no debería estar".

## La prioridad

Este prompt NO reemplaza al playbook de incident response. Su rol es decidir si activás el playbook o no. Si después del triage el output dice "incident confirmed", andá a `../playbooks/` y ejecutá el playbook que corresponda.

## El prompt

```
Rol: Sos un security incident responder senior, con experiencia en AWS y en
manejo de findings de GuardDuty, Security Hub, Inspector, y reportes de usuarios.
Tu trabajo es triage rápido: en menos de 5 minutos, decidir si esto es incidente
o ruido, y comunicárselo claro al on-call.

Contexto: Voy a darte:
1. El finding crudo (JSON de GuardDuty, screenshot del console, mensaje de Slack,
   lo que sea).
2. Información de contexto que pueda recordar en este momento:
   - Cambios recientes en la cuenta (deploys, migraciones, nuevos servicios)
   - Quién está de guardia
   - Si es horario laboral o fuera de horario
   - Si es weekday o weekend

Tarea: Triage en 5 pasos:

1. Clasificación inicial:
   - true positive (es real)
   - false positive (es ruido conocido)
   - unknown (necesitamos más info)

2. Severidad real (no la que dice GuardDuty, la que vos calculás):
   - sev1: parar todo, comunicar inmediato, ejecutar playbook
   - sev2: ejecutar playbook en horas, no días
   - sev3: planificar fix en sprint, no urgente
   - sev4: no es incidente, es backlog técnico

3. Cuestionario rápido para confirmar (5 preguntas máximo):
   - Lista de preguntas concretas con comandos AWS CLI para responderlas.
   - Cada pregunta tiene que ayudar a decidir entre true/false positive.

4. Si después de las preguntas todavía es "unknown", qué tools/logs revisar:
   - CloudTrail con filtros específicos
   - VPC Flow Logs con queries específicos
   - GuardDuty extended findings
   - S3 access logs

5. Decisión y comunicación:
   - Mensaje exacto para mandar al canal on-call (Slack-friendly, en español).
   - Si es sev1 o sev2, también el playbook a ejecutar (link a archivo en este
     repo, ej. ../playbooks/01-leaked-credentials.md).

Output esperado:

# Triage Result

**Clasificación:** [true/false positive/unknown]
**Severidad:** [sev1/sev2/sev3/sev4]

## Cuestionario de confirmación
1. [Pregunta] → `[comando AWS CLI]`
2. ...

## Si responden afirmativamente
[Acciones inmediatas]

## Si responden negativamente
[Cierre del finding como FP, con justificación]

## Comunicación al on-call
```
[Mensaje exacto, copy-paste ready]
```

## Próximo paso
[Playbook a ejecutar o cerrar como FP]

Guardrails:
- NO clasifiques nada como "false positive" sin justificar en una frase por qué.
- NO subestimes severidad para evitar despertar al on-call. Si tenés duda,
  subí la severidad.
- Si el finding involucra el root user, automáticamente sev1, sin importar
  el contexto.
- Si el finding involucra exfiltración de datos (S3 GetObject masivo, RDS
  snapshot copy a cuenta externa), automáticamente sev1.
- Si el finding es de tipo "Recon" (enumeración de IAM, S3 buckets, etc.) Y la
  fuente es interna (un rol legítimo), probablemente FP. Si la fuente es
  externa (IP desconocida), sev2 mínimo.
- NO sugieras "esperar a ver si pasa algo más". El triage decide ahora.
```

## Ejemplo de triage exitoso

Input: GuardDuty finding `UnauthorizedAccess:IAMUser/MaliciousIPCaller.Custom`, severidad MEDIUM, originado desde IP 198.51.100.42, usuario `developer-juan`.

Output esperado del prompt:

```
Triage Result

Clasificación: unknown
Severidad: sev2

Cuestionario:
1. ¿198.51.100.42 está en nuestra lista de IPs aprobadas (VPN, oficina, AWS Direct
   Connect)?
   → grep -r "198.51.100.42" terraform/network/

2. ¿developer-juan estaba haciendo despliegues legítimos en ese horario?
   → aws cloudtrail lookup-events --lookup-attributes \
     AttributeKey=Username,AttributeValue=developer-juan \
     --max-items 50 --start-time '2026-05-26T03:00:00Z'

3. ¿Hubo otras acciones desde esa IP en CloudTrail en las últimas 24 horas?
   → aws cloudtrail lookup-events --lookup-attributes \
     AttributeKey=AccessKeyId,AttributeValue=AKIA... \
     --max-items 100

Si responden afirmativamente (IP aprobada Y juan activo Y solo lecturas): FP, cerrar.

Si responden negativamente o ambiguo: sev1, ejecutar
../playbooks/01-leaked-credentials.md para developer-juan.

Comunicación al on-call:

> 🚨 GuardDuty finding `UnauthorizedAccess:IAMUser/MaliciousIPCaller` para
> developer-juan desde 198.51.100.42. Sev unknown hasta confirmar 3 preguntas
> (ver triage). Ejecutando preguntas, ETA 5 min.
```

## Cómo evoluciona tu uso

- **Semana 1:** lo usás cada finding. Te ayuda a no perder tiempo.
- **Mes 1:** ya reconocés los FPs comunes de memoria, lo usás solo para los unknowns.
- **Trimestre 1:** automatizás los FPs comunes con EventBridge rules (les ponés `SuppressFinding: true` automáticamente). El prompt queda para los casos raros.
