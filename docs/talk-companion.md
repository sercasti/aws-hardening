# Talk companion: del deck al repo

> Si viste el talk en AWS Community Day Chile 2026 y querés profundizar en algún slide, esta es la guía. Cada sección del deck mapea a archivos específicos de este repo.

## Slide 1-5: Setup del problema

**Lo que cubrí:** Mi perfil, contexto de la charla, audiencia objetivo, por qué este tema importa en 2026.

**No hay archivos en el repo asociados. Si querés más contexto:**

- Sobre el modelo de Goldfarb: [docs/maturity-model-overview.md](maturity-model-overview.md)
- Sobre el patrón del loop: [docs/the-loop-architecture.md](the-loop-architecture.md)

## Slide 6-10: El estado actual del cloud security

**Lo que cubrí:** Datos de IBM Cost of a Data Breach, Verizon DBIR. La distribución de causas: misconfig vs vulnerability vs human error.

**Stats que mencioné (todas verificables):**

- Tiempo promedio para detectar un breach en cloud: 277 días (IBM 2024 report).
- % de breaches por misconfig: ~25% (Verizon DBIR 2024).
- Costo promedio de breach cloud: USD 4.45M (IBM 2024).

**Profundizar:**

- Lectura recomendada: [IBM Cost of a Data Breach](https://www.ibm.com/security/data-breach), [Verizon DBIR](https://www.verizon.com/business/resources/reports/dbir/).

## Slide 11-15: El AWS Security Maturity Model

**Lo que cubrí:** Los 4 niveles del modelo de Darío Goldfarb, los boss fights de cada uno, costos esperados, tiempo.

**Archivos relevantes:**

- [docs/maturity-model-overview.md](maturity-model-overview.md): one-pager del modelo.
- [specs/nivel-1/SPEC.md](../specs/nivel-1/SPEC.md): detalle del Nivel 1.
- [specs/nivel-2/SPEC.md](../specs/nivel-2/SPEC.md): detalle del Nivel 2.
- [specs/nivel-3/SPEC.md](../specs/nivel-3/SPEC.md): detalle del Nivel 3.
- [specs/nivel-4/SPEC.md](../specs/nivel-4/SPEC.md): detalle del Nivel 4.

**El modelo original:** [maturitymodel.security.aws.dev](https://maturitymodel.security.aws.dev). Crédito a Darío.

## Slide 16-18: Quick wins del Nivel 1

**Lo que cubrí:** MFA en root, GuardDuty, Cost Anomaly, CloudTrail. Por qué empezás por ahí.

**Archivos relevantes:**

- [specs/nivel-1/SPEC.md](../specs/nivel-1/SPEC.md): los 8 controles del Nivel 1.
- [QUICKSTART.md](../QUICKSTART.md): hands-on para cubrir Nivel 1 en una hora.

## Slide 19: Inspección agéntica full-stack

**Lo que cubrí:** El ejemplo de "le pedís a tu agente que audite tu repo full-stack y te genera un PR plan en 5 minutos".

**Archivos relevantes:**

- [prompts/security-review.md](../prompts/security-review.md): el prompt para hacer audit completo.
- [prompts/iam-audit.md](../prompts/iam-audit.md): variante específica para IAM.
- [prompts/pr-review.md](../prompts/pr-review.md): para que el agente sea second opinion.

## Slide 20: El flywheel pattern

**Lo que cubrí:** Las 4 etapas del loop: Escanear → Priorizar → Arreglar → Mergear.

**Archivos relevantes:**

- [docs/the-loop-architecture.md](the-loop-architecture.md): explicación detallada del loop.
- [docs/agent-handoff-guide.md](agent-handoff-guide.md): cómo coordinar entre tools.
- [assessment-cli/](../assessment-cli/): la herramienta de "Escanear".
- [prompts/](../prompts/): los prompts de "Priorizar" y "Arreglar".

## Slide 21: La demo de Kiro

**Lo que cubrí:** Kiro leyendo el SPEC del Nivel 1, generando plan, mostrando el primer item.

**Archivos relevantes:**

- [demos/kiro/](../demos/kiro/): el README completo de la demo.
- [demos/kiro/example-repo/](../demos/kiro/example-repo/): el mock-up que cargué en Kiro.
- [demos/kiro/example-output.md](../demos/kiro/example-output.md): transcript completo de una sesión.

**Si querés probar con otros agentes:**

- [demos/claude-code/](../demos/claude-code/): variante con Claude Code.
- [demos/cursor/](../demos/cursor/): variante con Cursor.

## Slide 22: El flywheel en producción

**Lo que cubrí:** Después de la demo, cómo se ve esto en una org real corriendo continuo.

**Archivos relevantes:**

- [scripts/](../scripts/): scripts asistidos (Fase 2 de automatización).
- [playbooks/](../playbooks/): IR runbooks (lo que viene cuando algo pasa).

## Slide 23: Tres cosas para el lunes

**Lo que cubrí:** Acciones concretas que cualquier engineer puede hacer en su próximo día laborable.

**Las tres cosas (recap):**

1. **MFA en root** (90 segundos).
2. **Elegí un ítem de Nivel 2 y agendalo para tu próximo sprint** (10 minutos).
3. **Corré el prompt de security-review.md** contra tu repo (1 hora).

**Archivos relevantes:**

- [README.md](../README.md): la versión punteada de estas tres cosas.
- [QUICKSTART.md](../QUICKSTART.md): walkthrough completo.

## Slide 24: Recursos y next steps

**Lo que cubrí:** Enlaces al repo, al modelo de Goldfarb, a las tools.

**Recursos clave:**

- Este repo: [github.com/sercasti/aws-hardening](https://github.com/sercasti/aws-hardening)
- Modelo de madurez: [maturitymodel.security.aws.dev](https://maturitymodel.security.aws.dev)
- Mi LinkedIn: [linkedin.com/in/sercasti](https://linkedin.com/in/sercasti)
- Anti-patterns que vimos: [docs/anti-patterns.md](anti-patterns.md)

## Slide 25: Q&A

**Preguntas comunes que recibo:**

### "¿Esto reemplaza a Security Hub / Prowler / ScoutSuite?"

No. La CLI de `assessment-cli/` es un baseline rápido. Para profundidad, usá las tools establecidas. Ver [assessment-cli/README.md#filosofía](../assessment-cli/README.md).

### "¿Funciona en GCP / Azure?"

El patrón sí (escanear → priorizar → arreglar → mergear). Las tools específicas (scripts, SCPs, assessment-cli) son AWS. Hay equivalentes en otros clouds.

### "¿Cuánto cuesta correr esto?"

- Tooling: $0 (free tier de AWS cubre Nivel 1, prompts son LLM tokens).
- Tiempo de engineer: 1 hora/semana en steady state.
- LLM tokens por loop: $1-5.

### "¿Qué pasa con compliance (PCI, SOC2, ISO)?"

El maturity model NO es un compliance framework, pero los controles de Nivel 1-2 cubren ~60% de SOC2 Common Criteria, ~50% de PCI requisitos básicos. Para compliance específico, ver overlays (cuando los publique).

### "¿Cuál es el role del Security Engineer en esto?"

Cambia. En lugar de hacer el work manualmente, define los specs, audita los outputs del agente, y se ocupa de los casos que requieren juicio (architecture, threat modeling, incident response). El work repetitivo lo hacen los agentes + engineers de producto.

### "¿Y si mi org no tiene Security Engineer?"

Mejor todavía. Este repo está específicamente pensado para esa org. Cualquier engineer del equipo puede correr el loop.

### "¿No es peligroso dejar que un agente toque infra?"

Sí, si no hay guardrails. Por eso los specs, los PRs como gate, el rollback documentado. El humano siempre en el loop.

## Si no viste el talk

Los slides están en [`talk/`](../talk/) (PDF + speaker notes). El video estará en el canal de YouTube de AWS Community Day Chile en ~2 semanas.

## Feedback

Si tenés feedback del talk (cosas que no quedaron claras, ejemplos que ayudarían, etc.), abrí un issue en el repo o mandame un mensaje. La próxima versión del talk va a incorporar lo que aprenda.
