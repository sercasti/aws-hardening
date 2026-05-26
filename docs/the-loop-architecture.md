# El loop: cómo funciona en arquitectura

> La tesis del talk: cualquier engineer + 2 agentes = mejora iterativa de seguridad. Acá te muestro la arquitectura del loop, qué hace cada agente, y cómo encaja con tu workflow existente.

## El loop, simplificado

```
              ┌─────────────────────┐
              │   ESCANEAR          │ ← agentes/CLI
              │  (Audit Agent)      │
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   PRIORIZAR         │ ← LLM con contexto
              │  (LLM + maturity)   │   del maturity model
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   ARREGLAR          │ ← engineer + agente
              │  (Fix Agent)        │   (review-first)
              └──────────┬──────────┘
                         │
                         ▼
              ┌─────────────────────┐
              │   MERGEAR / VALIDAR │ ← PR review por
              │  (Review Agent)     │   segundo agente
              └──────────┬──────────┘
                         │
                         └──── re-iniciar
```

## Por qué dos agentes (no uno)

Si usás un solo agente:

1. Genera código.
2. "Pasa" su propio review.
3. Mergeás.
4. Después descubrís el bug.

Si usás dos agentes:

1. Agente A genera código.
2. Agente B revisa (con prompt distinto, contexto distinto).
3. Diff de opiniones se vuelve input para vos.
4. Vos decidís.

Esto es análogo a code review humano. La diferencia: el segundo agente está disponible 24/7, no se cansa, no tiene su ego invertido en su propio código.

## Los tres agentes (mínimo viable)

### 1. Audit Agent (Escanear)

**Job:** observar el estado actual de la cuenta y emitir hallazgos en formato estructurado.

**No es:** un LLM solo. Combina:

- Llamadas a APIs de AWS (boto3, AWS CLI).
- Reglas de evaluación (¿está habilitado X? ¿coincide con criterio Y?).
- Output estructurado consumible por LLMs y dashboards.

**Implementaciones:**

- `assessment-cli/` en este repo (Python).
- Prowler, ScoutSuite, CloudFox para más profundidad.
- Steampipe para queries ad-hoc.

**Frecuencia:** cada vez que querés un baseline. Puede ser scheduled (daily) o on-demand.

### 2. Fix Agent (Arreglar)

**Job:** dado un hallazgo, proponer cambios concretos. Generar el código, terraform, CLI commands, o ticket.

**No es:** un ejecutor ciego. Su output requiere review humano.

**Implementaciones:**

- Cualquier agente coding-capable: Claude Code, Kiro, Cursor, Aider.
- Con MCP servers para integraciones (Slack, Jira, AWS).

**Input:** hallazgo del Audit Agent + contexto del repo (templates, specs, ejemplos).

**Output:**

- Para fixes triviales (habilitar feature, configurar setting): comando AWS CLI con verificación.
- Para fixes a infra-as-code: PR con cambios en Terraform/CDK.
- Para fixes process-related: ticket en Jira/Linear con descripción.

### 3. Review Agent (Mergear)

**Job:** dado un PR (o cambios propuestos), evaluar si está bien antes de mergear.

**No es:** el mismo agente que generó el código (para evitar el "agree con uno mismo" failure mode).

**Implementaciones:**

- Mismo tool que Fix pero con prompt distinto.
- O un setup CI/CD con LLM as code reviewer (acción en GitHub Actions, etc).

**Input:** PR + contexto del repo + criterios de review (los específicos a tu org).

**Output:**

- Approve.
- Request changes con detalles concretos.
- Comments con preguntas/sugerencias.

## El loop completo, paso a paso

### Step 1: Audit Agent corre

```bash
# Cron diario, o on-demand
python assessment-cli/assessment.py --format json --output baseline.json
```

Output: JSON estructurado con maturity score, gaps, evidence.

### Step 2: LLM lee y prioriza

Prompt al LLM:

```
Acá tenés baseline.json y specs/nivel-1/SPEC.md.

Tarea: priorizar los gaps según:
1. Severity (critical > high > medium > low).
2. Effort (cuántas horas).
3. Blast radius (que riesgo de romper algo).

Output: plan.md con top 5 acciones, comando exacto para cada una, verificación.
```

Output: plan.md priorizado.

### Step 3: Fix Agent ejecuta

Para items con blast radius "ninguno":

```bash
aws guardduty create-detector --enable --region sa-east-1
# Verificación
aws guardduty list-detectors --region sa-east-1
```

Para items con blast radius "bajo" o más:

```bash
# Generar PR
git checkout -b fix/imdsv2-baseline
# (cambios)
git commit -m "..."
gh pr create
```

### Step 4: Review Agent revisa

Cuando el PR se abre:

```yaml
# .github/workflows/pr-security-review.yml
name: PR security review
on:
  pull_request:
    paths:
      - 'terraform/scps/**'
      - 'terraform/iam/**'
jobs:
  review:
    runs-on: ubuntu-latest
    steps:
      - uses: anthropics/claude-pr-action@v1
        with:
          prompt: |
            Revisa este PR como Security Senior.
            Focus: SCPs y IAM policies.
            Output: comment con findings.
          model: claude-opus-4-6
```

El Review Agent comenta en el PR. Vos decidís.

### Step 5: Loop

Una vez mergeado y desplegado el cambio, el Audit Agent en su próxima corrida va a ver el progreso. El loop continúa.

## Composición: el patrón de equipo

Una progresión común:

**Stage 1: Un humano + un agente (modo aprendizaje).**

```
Engineer --interactúa con-- Claude Code
```

El engineer aprende a darle contexto, prompts efectivos. El agente hace todo el trabajo bajo guía.

**Stage 2: Un humano + dos agentes (modo seguro).**

```
                ┌─ Fix Agent (genera) ─┐
Engineer ──────┤                        ├─── PR ──── Engineer reviews
                └─ Review Agent ────────┘
```

El engineer revisa la diff de opiniones. Decide.

**Stage 3: Dos humanos + tres agentes (modo producción).**

```
                ┌─ Audit Agent (scheduled) ──┐
                │                              │
                ↓                              ↓
        Security Eng ←──── plan.md ──── Engineer
                                              │
                                              ↓
                                        Fix Agent
                                              │
                                              ↓
                          PR ─── Review Agent + Security Eng
```

Roles claros: el engineer aplica fixes, el Security Eng valida.

## Constraints importantes

### El humano nunca sale del loop

Hay tentación de "automatizar el loop entero". No lo hagas. Los casos donde el agente se equivoca son los más caros. El humano en el loop reduce el cost de errors a $0.

### El humano no escala

Pero el humano no puede revisar 100 PRs por día. La automation libera al humano para los casos que realmente requieren juicio. Los items con blast radius cero (habilitar GuardDuty) deberían pasar sin review humano.

### Specs son el contrato

Sin spec, el agente decide qué es "seguro". Sus decisiones pueden no ser las que tu org tomaría. El spec captura el contexto que el agente no tiene.

### Verificación post-cambio es obligatoria

Cada acción del Fix Agent debería terminar con un comando de verificación. "Lo apliqué" no es suficiente; "lo apliqué y verifiqué que quedó como esperaba" sí.

## Costos típicos

**Tiempo (engineer):**

- Setup inicial: 1 día (instalar tools, configurar credentials, indexar repo).
- Por loop (post-setup): 30 a 60 min para Nivel 1 completo.
- Mantenimiento: 1 hora/semana.

**Tokens (LLM):**

- Audit: 0 (es CLI, no LLM).
- Priorizar: ~5k tokens.
- Fix: ~20k a 100k tokens por sesión.
- Review: ~10k tokens por PR.

A precios actuales: ~$1 a $5 por loop completo.

**Comparado con el equivalente manual:**

- Hacer el mismo work sin agentes: 6 a 12 horas de un Senior Security Engineer.
- A $100/hora: $600 a $1200.

ROI: 100x a 1000x. Y mejora cada vez que iterás (los specs se afinan, los prompts se afinan, los templates se afinan).

## Anti-patterns

- ❌ **"Voy a hacer todo el loop con un solo agente para ahorrar tokens".** Perdés el value del peer review.
- ❌ **"El agente debería decidir solo, soy un manager".** Hasta que rompa producción.
- ❌ **"No tengo specs porque mi org es pequeña".** Los specs no son para tu org. Son para que el agente entienda tu org.
- ❌ **"El agente generó el código, lo mergeo sin leer".** No. Nunca.

## Cómo arrancar

1. Instalá `assessment-cli/` en tu cuenta sandbox.
2. Generá baseline.json.
3. Abrí Claude Code (o tu agente favorito).
4. Pedile que lea baseline + spec del Nivel 1 y arme plan.
5. Aplicá 1 fix. Validá. Aplicá el siguiente.
6. Después de 5 fixes, re-corré assessment.
7. Si el maturity score subió: estás en el loop.

El primer loop es siempre el más caro (setup). Los siguientes son inmediatos.

## Referencias

- [Specs en este repo](../specs/)
- [Prompts probados](../prompts/)
- [Templates](../templates/)
- [Demos](../demos/)
