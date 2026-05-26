# Incident Response Playbooks

> Cuando algo se rompe a las 3 AM, no querés estar improvisando. Estos son los playbooks: pasos a pasos para los incidents más comunes en AWS, escritos para que un on-call senior los ejecute sin pensar.

## Cuándo usar un playbook

- Cuando detectaste un incidente (vía GuardDuty, Security Hub, Cost Anomaly, o reporte humano) y necesitás responder rápido.
- Como base para automatizar la respuesta (Nivel 3 del maturity model).
- Como training: el equipo simula incidents usando los playbooks para entrenarse.

## Cómo está organizado un playbook

Cada archivo sigue la misma estructura:

```markdown
# Playbook X: [nombre del incident]

## Trigger
Cómo se detecta este incident.

## Severity
Cuál es la severidad inicial (puede subir/bajar durante el triage).

## SLA
Tiempo objetivo para contener y resolver.

## Pasos

### 1. Triage (5 min)
Confirmar que es real.

### 2. Contención (15 min)
Frenar la sangría.

### 3. Erradicación (30 min)
Sacar la amenaza.

### 4. Recovery (variable)
Volver a operación normal.

### 5. Post-mortem (1 semana)
Retro y action items.

## Anti-patterns
Errores comunes durante la respuesta.

## Automatización
Cómo automatizar este playbook completo o parcial.

## Métricas
Qué medir post-incidente.
```

## Catálogo

| ID | Incident | Severidad típica | Tiempo objetivo de respuesta |
|----|----------|------------------|------------------------------|
| [01](./01-leaked-credentials.md) | Credenciales filtradas en GitHub/repos públicos | critical | 30 min |
| [02](./02-public-s3-bucket.md) | S3 bucket público accidental | high | 1 hora |
| [03](./03-iam-privilege-escalation.md) | Escalación de privilegios IAM | critical | 30 min |
| [04](./04-unauthorized-region-activity.md) | Actividad en región no aprobada (mining clásico) | high | 2 horas |
| [05](./05-cost-anomaly.md) | Spike de costo súbito (señal de compromiso) | high | 4 horas |
| [06](./06-compromised-ec2.md) | EC2 comprometida (malware, mining, exfil) | critical | 1 hora |
| [07](./07-cross-account-anomaly.md) | Acceso cross-account no esperado | high | 1 hora |
| [08](./08-data-exfiltration.md) | Exfiltración de datos detectada | critical | 30 min |

## Reglas generales

Reglas que aplican a CUALQUIER playbook, no importa cuál:

### Antes de actuar

1. **Confirmá que es real.** El primer paso siempre es triage. Acción precipitada sobre un falso positivo te genera incidente operacional sin un incidente de seguridad de fondo.
2. **Comunicá temprano.** Antes de empezar a contener, mandá un mensaje al canal #security-incident: "Investigando finding X, severity Y, ETA primera update Z minutos." Esto preempts las preguntas.
3. **Tomá nota.** Cada acción que tomás, escribilo. Después en el post-mortem vas a necesitar reconstruir.

### Durante la respuesta

4. **No rotes credenciales antes de saber el scope.** Si rotás demasiado pronto, el atacante se escapa con la copia vieja antes de que entiendas qué hizo.
5. **Preservá evidencia.** Snapshot de EC2 antes de terminate. Logs de CloudTrail antes de que GuardDuty roteen. S3 versioning antes de borrar.
6. **No le tires del cable.** Aislar es mejor que destruir. Network ACL para bloquear tráfico es mejor que terminate de la instancia.

### Después

7. **Post-mortem en menos de 1 semana.** Caliente, no frío. Memoria fresca, blames bajos.
8. **Action items con dueño y fecha.** Sin esto, los retros son terapia, no mejora.
9. **Compartí lecciones.** Si otra cuenta puede aprender de tu incident, compartí (anonimizado si hace falta).

## Anti-patterns globales

- ❌ Ejecutar pasos del playbook sin confirmar que el incidente es real (FP devastador).
- ❌ Comunicar al canal "all-hands" cuando todavía estás en triage (genera pánico innecesario).
- ❌ Borrar evidencia "para limpiar" sin haber capturado snapshots.
- ❌ Reusar credenciales rotadas en cuentas diferentes (paranoia + esfuerzo extra, sin beneficio).
- ❌ Hacer post-mortems donde se busca culpable en lugar de causa raíz.

## Cómo armar tu propio playbook

Los playbooks de este repo son baseline. Tu organización tiene incidents específicos que no están acá. Para escribir el tuyo:

1. Identificá el tipo de incident (basado en historial real o threat model).
2. Definí el trigger más claro posible (qué finding o evento dispara el playbook).
3. Escribí los 5 pasos en su versión más simple.
4. Practicá en un game day antes de ponerlo en producción.
5. Iterá basado en el game day.

Tiempo de un playbook nuevo: de 1 a 2 semanas de elaboración, 1 game day para validar, 1 sprint para automatizar parcialmente. Total: 1 mes desde la idea hasta operacional.

## Automatización (Nivel 3)

Los playbooks bien escritos son la base para automatizar respuesta. La progresión típica:

1. **Manual.** Humano ejecuta cada paso siguiendo el doc.
2. **Asistido.** Humano ejecuta, pero scripts hacen lo repetitivo (snapshots, query de logs, notificación).
3. **Semi-automático.** Lambda hace los pasos low-risk (notificar, ticket, log capture). Humano hace los high-risk (rotation, terminate, isolation).
4. **Automático.** Step Function ejecuta todo end-to-end. Humano revisa post-hoc.

NO saltees pasos. La automatización sin haber pasado por manual y asistido es la receta para playbooks que destruyen producción.

## Próximo

Si querés ver un playbook ya automatizado end-to-end como referencia, mirá [`01-leaked-credentials.md`](./01-leaked-credentials.md). Es el más completo del repo y muestra la progresión de manual a automático.
