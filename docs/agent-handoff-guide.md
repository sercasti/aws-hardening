# Cómo pasar contexto entre agentes

> El "secreto" de hacer que un agente de seguridad funcione bien no es el modelo o el prompt. Es el contexto que le pasás. Esta guía explica cómo estructurar el contexto, cuándo cambiar de agente, y cómo hacer handoff sin perder información.

## Por qué importa

Un agente sin contexto te da respuestas genéricas:

> "Para mejorar seguridad en AWS, habilitá CloudTrail y GuardDuty."

Un agente con contexto te da respuestas accionables:

> "En tu cuenta 123456789012, GuardDuty está habilitado en us-east-1 pero no en sa-east-1. Tu spec del Nivel 1 require sa-east-1. El comando para habilitar es: ..."

La diferencia es el contexto que tenía a mano: tu account ID, regions, spec target, estado actual.

## Tipos de contexto

### 1. Specs (qué querés)

Un spec describe el estado deseado de tu infraestructura. NO describe cómo llegar, describe el target.

Ejemplo:

```markdown
# Nivel 1: El Despertar

Target state:
- MFA en root: hardware MFA habilitado
- CloudTrail: multi-region, file integrity, S3 bucket dedicado
- GuardDuty: ENABLED en us-east-1, sa-east-1
- ...
```

**Cuándo usarlo:** siempre. Es el contrato base.

### 2. Baseline (qué tenés)

Output del Audit Agent. Estructura objetiva del estado actual.

```json
{
  "metadata": { ... },
  "results": [
    { "check": "guardduty", "status": "fail", ... }
  ],
  "summary": { "maturity_score": 1.3 }
}
```

**Cuándo usarlo:** al inicio de cada sesión. Sin esto, el agente no sabe qué cambiar.

### 3. Constraints (qué NO podés hacer)

Restricciones de tu organización que el agente debe respetar.

```markdown
# Constraints organizacionales

- Producción es OU "prod". Cualquier cambio a producción requiere PR + 2 approvers.
- Region permitidas: us-east-1, sa-east-1. NUNCA proponer otras.
- Tag obligatorio en todos los recursos: Environment, Owner, CostCenter.
- KMS keys: solo customer-managed. Nunca aws/...
- Outbound a internet desde VPCs prod: solo via NAT Gateway + outbound proxy.
```

**Cuándo usarlo:** persistente en el repo (CLAUDE.md, .cursor/rules, etc.).

### 4. Vocabulario (qué significa qué)

Términos específicos de tu org que el agente no puede adivinar.

```markdown
# Vocabulario

- "Producción" = OU prod, accounts con tag Environment=production
- "Sandbox" = OU sandbox, accounts con tag Environment=sandbox o sin tag
- "Critical workload" = tag Criticality=critical
- "BG" = break-glass role para emergencias
- "PsTeam" = Platform Security Team, dueños de SCPs
```

**Cuándo usarlo:** en CLAUDE.md o spec global.

### 5. Memoria de sesiones anteriores

Decisions tomadas en sesiones previas que afectan futuras.

```markdown
# Decisiones recientes

2026-05-20: Decidimos NO habilitar Macie por costo. Re-evaluar en Q3.
2026-05-22: SCP de region restriction está pausado. Build pipeline de ML team usa us-east-1.
2026-05-24: i-def quedó con IMDSv1 hasta upgrade de AWS CLI. Owner: ops-jane@.
```

**Cuándo usarlo:** sesiones largas o continuas, para no repetir decisiones.

## Estructura recomendada de repo

```
your-repo/
├── CLAUDE.md                    # Agente lee esto siempre
├── .cursor/rules/               # Para Cursor
├── specs/
│   ├── nivel-1.md
│   ├── nivel-2.md
│   └── ...
├── constraints.md               # Constraints organizacionales
├── vocabulary.md                # Glosario de términos
├── decisions.md                 # Memoria de decisions
└── runs/                        # Outputs de sesiones (no commited)
    ├── 2026-05-24-audit.json
    ├── 2026-05-24-plan.md
    └── ...
```

## CLAUDE.md como punto de entrada

`CLAUDE.md` es el archivo que Claude Code (y otros agentes) leen al iniciar. Usalo como índice:

```markdown
# Este repo: aws-hardening

Companion del talk "Securing AWS workloads at scale".

## Contexto

- Org: Caylent
- Cuentas AWS: ver `accounts.md`
- Regions permitidas: us-east-1, sa-east-1
- Critical workloads: tag `Criticality=critical`

## Cómo trabajar acá

1. Para audit: correr `python assessment-cli/assessment.py`.
2. Para plan: leer `specs/nivel-N.md` + el baseline más reciente.
3. Para fixes: ver `templates/` para patrones.
4. Para IR: ver `playbooks/`.

## Constraints

- Nunca proponer fixes que requieran credenciales de root.
- Para SCPs: siempre PR, nunca apply directo.
- Validá cada cambio con verificación post-hoc.

## Lecturas recomendadas

- `docs/maturity-model-overview.md`
- `docs/the-loop-architecture.md`
- `prompts/security-review.md` (cuando quieras un review)
```

## Handoff entre agentes

A veces vas a usar varios agentes en un workflow. Por ejemplo:

1. Claude Code corre audit y genera plan.
2. Pasás el plan a Cursor para editar templates.
3. Volvés a Claude Code para apply.

Para que esto funcione, el agente B debe poder leer lo que el agente A produjo.

### Patrón 1: archivos como interface

El agente A escribe archivos. El agente B los lee.

```bash
# Claude Code (Agent A):
"Generá plan.md con priorización"
→ writes plan.md

# Cursor (Agent B):
"@files plan.md
Generá los Terraform files para los items 1-3 del plan."
→ reads plan.md, writes terraform/...

# Claude Code (Agent A):
"Aplicá los Terraform files que están en terraform/"
→ reads terraform/, applies
```

Esto funciona porque los agentes coordinan via filesystem.

### Patrón 2: contexto explícito al cambiar

Cuando cambiás de agente, pasá el contexto explícito:

```
Cursor, voy a pasarte una sesión que arranqué en Claude Code.

Contexto:
- Audit corrido el 2026-05-24, baseline en /tmp/baseline.json
- Plan priorizado en plan.md
- Items 1, 2, 4 ya aplicados
- Item 3 (SCPs) requiere PR; vamos a generar el código acá

Tarea: leer items 3 del plan, generar SCPs en templates/scps/.
```

### Patrón 3: estado en repo

Si tu sesión va a durar varios días, persistí el estado en un archivo del repo:

```markdown
# Estado actual del proyecto

Última sesión: 2026-05-24
Por: Sergio + Claude Code

## En progreso

- Nivel 1: 85% completo
- Nivel 2: 0%

## Pending

- [ ] IMDSv2 en i-def (requiere AWS CLI upgrade)
- [ ] Migrar 3 IAM users humanos a SSO
- [ ] PR #124 SCPs baseline pendiente de review

## Decisions tomadas

- Macie: descartado por costo, re-evaluar Q3.
- SCP region restriction: en hold hasta ML team migre.
```

Cada nueva sesión arranca leyendo este archivo. Sin él, repetirías las mismas conversaciones cada vez.

## Cuándo cambiar de agente

### Cambiá a Claude Code cuando:

- Necesitás autonomous multi-step.
- La tarea require coordinar varios comandos AWS.
- Estás haciendo IR (responder a un incidente).

### Cambiá a Cursor cuando:

- Necesitás editar varios archivos en paralelo.
- Querés ver diffs inline mientras editás.
- Estás refactoreando Terraform/CDK.

### Cambiá a Kiro cuando:

- Necesitás planning formal antes de código.
- Querés alineación spec → tasks → código.
- Estás en una conversación de definición (no de implementación).

### NO cambies cuando:

- El agente actual está progresando bien.
- El cambio rompería el flow.
- No tenés tiempo para reorientar al nuevo agente.

## Errores comunes

### 1. Asumir que el agente recuerda

Los agentes (la mayoría) no tienen memoria entre sesiones. Si en la sesión anterior decidiste algo, anotalo. Si no, la próxima sesión va a re-decidir.

### 2. Pasarle demasiado contexto

Si le pasás 50 archivos al agente, va a perderse. Pasá lo mínimo necesario para la tarea.

### 3. No validar lo que produjo

El agente puede generar código que se ve bien pero está mal. Validá:

- Para JSON/YAML: que parsea.
- Para Terraform: `terraform validate`.
- Para shell: `shellcheck`.
- Para Python: que corre sin sintaxis errors.

### 4. Trustear que entendió el contexto

Si pasás un SPEC, pediéle que te confirme qué entendió antes de ejecutar:

```
Antes de actuar:
1. Resumime en 2 líneas qué dice el spec.
2. Identificá 1 cosa que el spec NO te dice y que vas a tener que inferir.
3. Esperá mi confirmación antes de proceder.
```

Si entendió mal, ahorraste hora de re-trabajo.

## Patrón: el "5-minute briefing"

Al inicio de cada sesión nueva con un agente, hacé un briefing:

```
Sesión nueva. Pasame:

1. Lee CLAUDE.md.
2. Lee decisions.md.
3. Lee la última run en runs/.
4. Resumí en 3 líneas: dónde estamos, qué decidimos last time, qué hay pendiente.
5. Confirmá que vas a seguir las constraints en constraints.md.
6. Esperá mi instrucción.
```

5 minutos al inicio te ahorran 30 minutos de aclaraciones después.

## Conclusión

El contexto es la diferencia entre un agente que te ayuda y uno que te frustra. Invertí en estructurarlo, mantenerlo actualizado, y pasarlo bien entre tools. Lo que NO está en el contexto, el agente lo inventa. Y lo que el agente inventa, generalmente está mal.
