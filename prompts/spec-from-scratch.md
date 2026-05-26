# Spec from Scratch

> Los specs son la pieza central del loop del agente. Definen qué cuenta como "fortificado" en tu organización. Este prompt te ayuda a escribir tu propio `SPEC.md` desde cero, adaptado a tu contexto (no genérico).

## Cuándo usarlo

- Cuando ya hiciste el security review del lunes y querés bajarlo a un spec ejecutable.
- Cuando vas a empezar a usar Kiro/Cursor/Claude Code para fixes automáticos y necesitás el archivo que el agente lee.
- Cuando querés versionar las decisiones de seguridad de tu organización en algo más estructurado que un Confluence page.

## Antes de invocarlo

Tené a mano:

1. El output del security review.
2. Tu inventario (cuentas, regiones, workloads).
3. Las excepciones conocidas (workloads que NO siguen la regla general, con justificación).
4. Tu apetito de riesgo (¿priorizás velocidad o seguridad cuando hay tradeoff?).

## El prompt

```
Rol: Sos un Cloud Security Architect que está documentando el spec de seguridad
de una organización por primera vez. Trabajás como si fueras consultor externo
ayudando al cliente a articular qué considera "seguro" en su contexto, sin
imponer un standard genérico que no aplica a su caso.

Contexto: Mi organización es [DESCRIPCIÓN: industria, tamaño, regulación].
Mi cuenta tiene [N] AWS accounts. Los workloads son [TIPOS: web apps, data
pipelines, ML training, etc.].

Mi punto de partida son los findings del security review (los pego abajo).
Mi nivel objetivo del AWS Security Maturity Model es: [NIVEL: 1, 2, 3, o 4].

Tarea: Ayudame a escribir un SPEC.md ejecutable. Tiene que tener:

1. Visión: una frase que describe qué quiere lograr la organización con
   seguridad. NO genérica. Específica a mi contexto.

2. Principios: 3 a 5 principios que guían las decisiones. Cada principio es
   una afirmación accionable, no un slogan.

3. Controles obligatorios por categoría:
   - Identity (IAM, federation, MFA)
   - Network (VPC, ingress/egress, segmentation)
   - Data (encryption at rest, in transit, retention)
   - Monitoring (logging, alerting, retention)
   - Organization (SCPs, OUs, account structure)

   Para cada control:
   - Qué tiene que estar habilitado (estado deseado)
   - Cómo se verifica (comando AWS CLI o query)
   - Severidad si no se cumple (critical, high, medium)
   - Excepciones conocidas (con justificación)

4. Anti-patterns: 5 a 10 cosas que NO queremos ver. Cosas que un agente debería
   marcar inmediatamente si las detecta.

5. Plan de adopción:
   - Lo que ya cumplimos (con porcentaje estimado)
   - Lo que vamos a fixear este sprint
   - Lo que vamos a fixear este trimestre
   - Lo que se acepta como "no aplica" o "tech debt aceptable"

6. Cómo se actualiza el spec:
   - Quién puede modificarlo
   - Qué requiere consenso (qué cambios necesitan más de una persona aprobando)
   - Cadencia de revisión (mensual, trimestral)

Output esperado: Un archivo Markdown completo, listo para commitear como
SPEC.md en el repo. Que sea legible por un humano y parseable por un agente.

Estructura:

```markdown
# Security Spec

## Visión
[Una frase]

## Principios
1. ...
2. ...

## Controles obligatorios

### Identity
- [Control 1]
  - Estado deseado: ...
  - Verificación: `aws iam ...`
  - Severidad: ...
  - Excepciones: ...

[Repetir para cada categoría]

## Anti-patterns
- ❌ ...
- ❌ ...

## Plan de adopción
| Fase | Items | Target | Status |
|------|-------|--------|--------|
| Sprint actual | ... | [fecha] | in progress |
| Próximo trimestre | ... | [fecha] | planned |

## Mantenimiento del spec
[Reglas de modificación]
```

Guardrails:
- NO copies-pegues frameworks como CIS Benchmark, NIST, SOC2. Estos son
  referencias útiles, pero el spec tiene que ser ESPECÍFICO a esta
  organización. Si no podés hacerlo específico, pedíme más contexto.
- NO escribas controles imposibles de verificar programáticamente. Cada
  control tiene que tener un comando AWS CLI o query que devuelva pass/fail.
- NO agregues 50 controles. Un spec de Nivel 1 tiene 10 a 15 controles
  máximo. Un spec de Nivel 2 tiene 20 a 30.
- NO uses lenguaje vago tipo "implementar best practices". Decí qué practice
  específica.
- Si el findings del security review reveló cosas críticas que no están en el
  spec todavía, agrega esos primero, antes de cualquier otro.
```

## Ejemplos en el repo

Para que veas cómo se ve un spec terminado, mirá:

- [`../specs/nivel-1/SPEC.md`](../specs/nivel-1/SPEC.md): ejemplo para Nivel 1 (quick wins).
- [`../specs/nivel-2/SPEC.md`](../specs/nivel-2/SPEC.md): ejemplo para Nivel 2 (foundational).
- [`../specs/nivel-3/SPEC.md`](../specs/nivel-3/SPEC.md): ejemplo para Nivel 3 (continuous surveillance).
- [`../specs/nivel-4/SPEC.md`](../specs/nivel-4/SPEC.md): ejemplo para Nivel 4 (continuous program).

Los specs del repo son referencias genéricas. Tu spec debería ser MÁS específico (mencionar tus cuentas, tus servicios, tus excepciones).

## Cómo el spec se conecta con los agentes

Una vez que tenés el spec:

1. Lo commiteás al repo (igual que el código).
2. Lo referenciás en el system prompt o context del agente (Kiro, Cursor, Claude Code).
3. El agente lo lee antes de proponer fixes.
4. Cuando proponé un cambio en una PR, en la descripción dice qué control del spec está intentando satisfacer.

Esto te da auditabilidad: cada PR del agente está justificada contra el spec, no contra una opinión del agente.

## Cuándo el spec se rompe

El spec es un documento vivo. Lo modificás cuando:

- Una nueva regulación entra (PCI, GDPR, ley local de protección de datos).
- Un incidente revela un gap que no estaba contemplado.
- Un workload nuevo entra que requiere relajar un control (con excepción documentada).
- Avanzaste de nivel y querés subir el bar.

Cadencia recomendada: revisión trimestral. Cambios incrementales en el medio (PR a SPEC.md como cualquier otro código).
