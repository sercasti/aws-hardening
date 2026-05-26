# Demo: Claude Code

> Claude Code corre en tu terminal y puede leer/modificar archivos, ejecutar comandos, y orquestar tareas multi-paso. Es el approach más "autónomo" de las tres opciones: declarás el objetivo, Claude Code itera hasta resolverlo.

## Por qué Claude Code

- **Multi-step autonomous**: podés decir "evaluá la cuenta, generá plan, aplicá los fixes triviales, abrí PR para los riesgosos" y Claude Code lo ejecuta de punta a punta.
- **Tool use nativo**: ejecuta AWS CLI, lee outputs, decide siguientes pasos.
- **PR-friendly**: genera commits con mensajes descriptivos, abre PRs con descripciones de qué cambia y por qué.

## Setup

```bash
# Instalar Claude Code (https://docs.claude.com/en/docs/claude-code)
npm install -g @anthropic-ai/claude-code

# Verificar
claude --version

# Configurar credentials AWS
aws sts get-caller-identity

# Posicionarte en el folder del proyecto
cd ~/work/aws-hardening
```

## Demo step-by-step

### Paso 1: Iniciar Claude Code

```bash
cd ~/work/aws-hardening
claude
```

### Paso 2: Darle contexto

```
Tengo un repo con specs por nivel (specs/nivel-1/SPEC.md hasta nivel-4/) y una CLI de assessment (assessment-cli/).

Tarea inicial:
1. Lee specs/nivel-1/SPEC.md.
2. Corré la CLI: python assessment-cli/assessment.py --format json --output baseline.json.
3. Identifica gaps entre baseline.json y los controles del Nivel 1.
4. Generá un plan priorizado en plan.md.

NO ejecutes fixes todavía.
```

### Paso 3: Claude Code ejecuta

Claude Code va a:

1. Leer el SPEC con `Read`.
2. Ejecutar `python assessment-cli/...` con `Bash`.
3. Parsear el JSON.
4. Generar `plan.md` con `Write`.
5. Mostrarte un resumen.

### Paso 4: Decidir qué automatizar

Una vez generado el plan, decisión por item:

```
Para el plan.md generado:
- Items con blast radius "ninguno" (GuardDuty, Cost Anomaly, KMS rotation): ejecutalos directamente.
- Items con blast radius "bajo" (IMDSv2, S3 block en buckets): pedime confirmación antes de cada uno.
- Items con blast radius "medio o alto" (migración a SSO, SCPs): generá un PR/ticket, no ejecutes.
```

### Paso 5: Claude Code ejecuta el plan diferenciado

Para los items low-risk:

```
[Claude Code]: Ejecutando aws guardduty create-detector --enable --region sa-east-1
✅ Detector creado: abc123def456ghi789

[Claude Code]: Ejecutando aws ce create-anomaly-monitor ...
✅ Monitor creado, subscription pendiente de configurar.

[Claude Code]: Para crear subscription, necesito un email. Por defecto uso ops@yourcompany.com. Confirmá o pasame otro.
```

Para items con confirmación:

```
[Claude Code]: Voy a aplicar IMDSv2 en i-abc. Antes:
- Validé que la instance tiene AWS CLI v2.13 (compatible).
- La instance está en una subnet privada con role WebServerRole.
- Sin logs de uso de IMDSv1 en últimos 7 días.

Comando: aws ec2 modify-instance-metadata-options --instance-id i-abc --http-tokens required

¿Procedo? [y/n]
```

Para items que requieren PR:

```
[Claude Code]: Para el SCP de Nivel 2, voy a generar un PR.

Files a crear:
- terraform/scps/01-deny-disable-cloudtrail.tf (copiado de templates/)
- terraform/scps/02-deny-disable-guardduty.tf

Branch: feature/baseline-scps
Commit: "feat(scps): añadir SCPs básicos de protección de logging"

PR creado: https://github.com/[org]/[repo]/pull/123

¿Mergear ahora o esperar review?
```

### Paso 6: Re-scan automático

```
Re-corré el assessment y mostrame el diff con baseline.json.
```

Claude Code genera baseline-v2.json, hace el diff, te muestra qué mejoró.

## Tips para usar Claude Code bien

### Slash commands custom

Creá un `.claude/commands/scan.md` en tu repo:

```markdown
# /scan

Corré el assessment, generá baseline.json, mostrame el resumen.
```

Ahora en cualquier sesión podés decir `/scan` y se ejecuta el flow.

Otros comandos útiles:

```
.claude/commands/
├── scan.md
├── plan.md
├── apply-safe.md
├── apply-risky.md
├── pr-review.md
```

### CLAUDE.md en el repo

Cláude Code lee `CLAUDE.md` automáticamente al iniciar. Aprovechalo para constraints persistentes:

```markdown
# Constraints para este repo

- Nunca ejecutes comandos AWS que destruyan recursos sin confirmación explícita.
- Para SCPs, siempre generá PR. Nunca aplicar directamente a la Organization.
- Si un cambio afecta producción (tag Environment=production), generá PR con label `needs-security-review`.
- Validá outputs después de cada cambio AWS con un comando de verificación.
- Logs y outputs van a /tmp/runs/ (gitignored).
```

### Subagents

Para tareas largas (Nivel 3+), usá subagents:

```
Hacé un audit completo de Nivel 3 usando un subagent dedicado. El subagent debe:
1. Leer specs/nivel-3/SPEC.md.
2. Auditar Security Hub, AWS Config rules, centralized logging.
3. Producir un report en /tmp/level3-audit.md.
4. Volver con el report.

Mientras el subagent corre, vos seguí con otros items del Nivel 1 que queden.
```

## Limitaciones

- **Costos de tokens**: tareas largas consumen tokens. Para sessions de 1 hora, monitoreá.
- **Credentials**: Claude Code usa tu AWS CLI configurada. Si tenés múltiples profiles, pasale `--profile` explícito.
- **No reemplaza tu juicio**: en cambios irreversibles, Claude Code respeta tu workflow pero vos validás.

## Ejemplo completo

Ver [`example-session.md`](./example-session.md) para una sesión real punta a punta.

## Recursos

- [Claude Code docs](https://docs.claude.com/en/docs/claude-code)
- [Slash commands](https://docs.claude.com/en/docs/claude-code/slash-commands)
- [Subagents](https://docs.claude.com/en/docs/claude-code/subagents)
- [Hooks (pre/post commit, pre/post bash)](https://docs.claude.com/en/docs/claude-code/hooks)
