# Demos

> Ejemplos concretos del flywheel pattern aplicado con distintos agentes. Cada subfolder muestra el MISMO problema resuelto con una tool distinta, así podés evaluar cuál se ajusta a tu workflow.

## Filosofía: agnóstico de herramienta

La tesis del talk es: cualquier engineer + 2 agentes = mejora iterativa de seguridad. La elección de Kiro, Claude Code, o Cursor es menos importante que el patrón.

Cada demo resuelve el mismo escenario:

**Escenario:** Tenés una cuenta AWS con varias misconfigurations típicas (root sin MFA, GuardDuty deshabilitado, IMDSv1, S3 público accidental, IAM roles con permisos excesivos). Querés evaluar el estado, priorizar, y resolver los issues en una sesión.

Cada demo muestra:

1. **Cómo darle contexto al agente** (SPEC.md, prompts, archivos).
2. **El loop** (escanear, priorizar, arreglar, validar).
3. **Output esperado** (PR, comentarios, plan de acción).

## Subfolders

```
demos/
├── kiro/                    # Demo con Kiro (spec mode)
├── claude-code/             # Demo con Claude Code (terminal-based)
└── cursor/                  # Demo con Cursor (IDE-based)
```

## Setup común

Antes de correr cualquier demo necesitás:

```bash
# AWS credentials con SecurityAudit + ViewOnlyAccess al menos
aws sts get-caller-identity

# Clonar el repo
git clone https://github.com/sercasti/aws-hardening
cd aws-hardening

# Generar un assessment baseline
cd assessment-cli
pip install -r requirements.txt
python assessment.py --format json --output /tmp/baseline.json
```

Ese baseline es el input principal para el agente.

## Comparativa rápida

| Aspecto | Kiro | Claude Code | Cursor |
|---|---|---|---|
| Tipo | Spec-first | Terminal agent | IDE-integrated |
| Fortaleza | Specs explícitos | Multi-paso autónomo | Edits inline en código |
| Mejor para | Plan formal pre-código | Refactors grandes, IR | Cambios incrementales |
| Cost | Free tier | Free + paid tiers | Subscription |
| Curva aprendizaje | Media | Baja | Baja |

**Mi recomendación:**

- **Kiro** si tu organización valora process: define spec, alinea, ejecuta.
- **Claude Code** si vas a hacer cambios autónomos de varios archivos.
- **Cursor** si querés intervenir mientras el agente edita.

Mezclá libremente. No hay una respuesta correcta.

## El loop en cada demo

```
        ┌──────────────┐
        │   ESCANEAR   │  python assessment.py → baseline.json
        └──────┬───────┘
               ↓
        ┌──────────────┐
        │  PRIORIZAR   │  Agente lee baseline + maturity model → plan.md
        └──────┬───────┘
               ↓
        ┌──────────────┐
        │   ARREGLAR   │  Agente genera fixes (SCP, Terraform, ticket)
        └──────┬───────┘
               ↓
        ┌──────────────┐
        │   MERGEAR    │  Engineer review + PR (agente colabora)
        └──────┬───────┘
               ↓
        (volver a ESCANEAR)
```

Cada demo te lleva por una vuelta completa de este loop, con la tool elegida.

## Output esperado

Después de correr cualquiera de las demos, deberías tener:

1. `plan.md` con findings priorizados.
2. `terraform/` o `scps/` con los fixes generados.
3. Un PR con los cambios (en repo local o forkeado).
4. Un re-scan que muestra el progreso (maturity score subido).

## Limitaciones

- Las demos usan una cuenta sandbox. No corras contra producción sin entender qué hace cada fix.
- Los agentes pueden cometer errores. Cada PR debe ser revisado por humano.
- Cada agente tiene tools diferentes. Algunos generan código mejor que otros para casos específicos.

## Recursos

- [Kiro docs](https://kiro.dev/)
- [Claude Code docs](https://docs.claude.com/en/docs/claude-code)
- [Cursor docs](https://docs.cursor.com/)
- [Aider (alternativa terminal)](https://aider.chat/)
