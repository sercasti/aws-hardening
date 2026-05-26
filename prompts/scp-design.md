# SCP Design (boss fight de Nivel 2)

> Tu primera SCP es la pelea más dura del modelo de madurez. Técnicamente son diez líneas de JSON. Políticamente es donde se pelean tres equipos. Este prompt te ayuda a escribir la primera sin romper producción.

## Cuándo usarlo

- Cuando ya tenés AWS Organizations configurada y querés tu primera SCP de verdad.
- Cuando un finding del audit del lunes te dice "Sin SCPs desplegadas".
- Cuando un compañero abrió una PR proponiendo una SCP y querés un second opinion antes de aprobarla.

## Lo que NO hace este prompt

No te aplica la SCP. La SCP la desplegás vos a mano (audit-mode primero, después enforce). El prompt te diseña la SCP, te explica los efectos, y te dice cómo testearla.

## Cómo usarlo

1. Mirá el output de tu [`security-review.md`](./security-review.md). Identificá el riesgo más alto que querés bloquear.
2. Hacé un inventario de qué workloads tenés y en qué cuentas. Algo así:

```
- Cuenta dev (us-east-1, us-west-2): lambdas + dynamodb + s3
- Cuenta staging (us-east-1): EKS + RDS Postgres + s3
- Cuenta prod (us-east-1, eu-west-1): EKS + RDS Postgres + s3 + CloudFront
- Cuenta security (us-east-1): centralized logs, GuardDuty admin
- Cuenta sandbox (us-east-1): para experimentos, low constraint
```

3. Copiá el prompt, completá los `[corchetes]`, pegale el inventario.

---

## El prompt

```
Rol: Sos un Cloud Security Architect senior con foco en AWS Organizations y
Service Control Policies. Tu experiencia es en empresas medianas (50 a 500
empleados) que están migrando de cuentas standalone a una organización con
guardrails. Hablás español, sos directo, evitás corporate speak.

Contexto: Estoy escribiendo mi primera SCP. Mi organización tiene [N] cuentas:

[inventario completo de cuentas, workloads, regiones que usás]

El riesgo que quiero bloquear es: [DESCRIPCIÓN DEL RIESGO].

Ejemplos de riesgos típicos:
- "Que un developer borre CloudTrail por accidente o malicia."
- "Que cualquiera cree recursos fuera de las regiones aprobadas."
- "Que se creen usuarios IAM humanos cuando deberíamos estar en SSO."
- "Que se desactive GuardDuty."
- "Que se acceda a la cuenta sin MFA."
- "Que un workload de dev mueva data a prod sin pasar por el pipeline."

Tarea: Diseñame la SCP que bloquea ese riesgo. Quiero:

1. La SCP en JSON, válida y testeada contra la sintaxis de SCPs (no IAM regular,
   las SCPs tienen restricciones).
2. La lista de OUs o cuentas donde aplicarla. Si me recomendás aplicarla a "todo
   menos sandbox", explicá por qué sandbox queda fuera.
3. Tests a correr ANTES de aplicar en enforce:
   - Comandos AWS CLI específicos que prueben que la SCP bloquea lo que tiene
     que bloquear.
   - Comandos AWS CLI que prueben que NO bloquea lo legítimo.
4. Procedimiento de audit-mode:
   - Cómo configurarla para que solo loguee, no bloquee, durante 2 semanas.
   - Qué logs revisar en ese período (CloudTrail con error code AccessDenied
     filtrando por la SCP).
   - Métrica de éxito: qué número de "false positives" es aceptable antes de
     pasarla a enforce.
5. Procedimiento de rollback:
   - Cómo desactivarla rápido si algo se rompe en producción.
   - Tiempo estimado para revertir.
6. Excepción documentada:
   - Si algún equipo legítimo va a chocar con esta SCP, ¿cuál es el proceso
     para pedir una excepción? Template del request.

Output esperado:

# SCP propuesta

```json
[JSON acá]
```

# Aplicar en estas OUs/cuentas
[Lista]

# Tests pre-deploy
[Comandos]

# Audit-mode (2 semanas)
[Procedimiento]

# Enforce
[Procedimiento]

# Rollback
[Procedimiento]

# Excepciones
[Template]

# Riesgos del fix mismo
[Lista de cosas que esta SCP podría romper si no la testeás bien]

Guardrails:
- NO me pongas la SCP en una sola línea ininteligible. Formatéala con indentación
  clara.
- NO uses Action: "*" en el Allow. Las SCPs por default permiten todo, no necesitan
  un Allow global.
- Si el riesgo que quiero bloquear es "que se acceda sin MFA", usá la condition
  aws:MultiFactorAuthPresent, NO el rol de root. (Es un error común que confunde
  ambos.)
- Si la SCP que te pido podría romper la federación con SSO/IdP, advertilo
  EXPLÍCITAMENTE antes del JSON.
- NO recomendes la SCP "DenyAll" para staging. Es una opción atómica que rompe
  todo. Quédate en SCPs específicas que bloquean exactamente lo que pedí.
- Si el riesgo es ambiguo o tiene tres interpretaciones posibles, pedíme que
  precise antes de generar el JSON.
```

---

## Qué esperar

Un buen output de este prompt te tira:

- **Una SCP de 15-40 líneas** que efectivamente bloquea lo que pediste.
- **2-5 tests CLI** para validar el comportamiento.
- **Un procedimiento de audit-mode** con métricas claras.
- **Un rollback procedure** que toma 5 minutos.

Si el output te tira una SCP de 200 líneas, probablemente está intentando ser demasiado ambiciosa. Pedile que la divida en 3 SCPs más chicas.

## Ejemplos en este repo

En [`../templates/scps/`](../templates/scps) tenemos SCPs ya escritas para los riesgos más comunes. Usalos como punto de partida y modificá lo necesario.

## La conversación con el CTO

Cuando ya tengas la SCP diseñada y testeada en audit-mode, el siguiente paso es defenderla ante quien aprueba cambios en producción. Te ayuda usar:

```
Generame una explicación de 3 párrafos para mi CTO, sobre por qué deberíamos
aplicar esta SCP en producción. Estructura:
1. El riesgo que mitigamos (concreto, sin FUD).
2. Lo que cambia para los developers (sí cambia algo, decílo).
3. Costo de implementación (siempre cero en SCPs, pero explicalo).

Tono: directo, sin marketing speak, asumí que el CTO es técnico.
```

Eso te genera el email/Slack post para conseguir el go-ahead. Lo iterás dos veces y lo enviás.

## Loop

1. Diseñar SCP (este prompt).
2. Validar tests.
3. Defender ante stakeholders.
4. Audit-mode por dos semanas.
5. Revisar logs, ajustar si hay falsos positivos.
6. Enforce.
7. Documentar excepciones aceptadas.

El ciclo completo, para una SCP simple, son 3 a 4 semanas. La segunda SCP la hacés en una semana. La quinta en dos días. La curva de aprendizaje es empinada pero corta.
