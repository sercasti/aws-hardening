# Demo: Cursor

> Cursor es un IDE forkeado de VS Code con AI integrada. Su fortaleza es trabajar inline con el código: editás como en cualquier IDE, pero podés invocar al agente con cmd+K o el chat lateral. Para infra-as-code esto se siente natural.

## Por qué Cursor

- **Inline editing**: ves los diffs en tiempo real, aceptás/rechazás por bloque.
- **Codebase awareness**: indexa el repo entero, así puede referenciar archivos sin que se los pases.
- **Composer mode**: para tareas multi-archivo, podés decir "crear los 7 SCPs en templates/scps/" y los genera todos.
- **Familiar UI**: si venís de VS Code, no hay curva.

## Setup

```bash
# Descargar e instalar Cursor desde https://cursor.com/
# Abrir el repo
cursor ~/work/aws-hardening
```

Cursor va a indexar el repo (toma 30 segundos para repos chicos).

## Demo step-by-step

### Paso 1: Setup del contexto

En lugar de pasar archivos manualmente, usá los keywords de Cursor:

- `@codebase` → da contexto del repo entero.
- `@files specs/nivel-1/SPEC.md` → archivo específico.
- `@docs https://maturitymodel.security.aws.dev` → URL como context.

### Paso 2: Generar plan con Composer

Abrí Composer (cmd+i) y escribí:

```
@codebase @files specs/nivel-1/SPEC.md /tmp/baseline.json

Identifica gaps entre el baseline y los controles del Nivel 1. Generá:
1. plan.md con la priorización.
2. Para cada item en el plan, un archivo separado en scripts/fixes/ con el comando exacto y verificación.

Output esperado: 1 plan.md + N scripts ejecutables.
```

Composer va a generar todos los archivos en paralelo. Vas a ver:

```
Composer changes:
+ plan.md (new)
+ scripts/fixes/01-guardduty-sa-east-1.sh (new)
+ scripts/fixes/02-cost-anomaly.sh (new)
+ scripts/fixes/03-imdsv2-instances.sh (new)
+ scripts/fixes/04-kms-rotation.sh (new)
+ scripts/fixes/05-s3-block.sh (new)
```

### Paso 3: Revisar diffs

Cursor muestra cada cambio en el editor con el diff. Aceptás (cmd+enter) o pedís cambios:

```
En 03-imdsv2-instances.sh, agregá un check previo de aws cli version
antes de aplicar el cambio.
```

Cursor edita inline. Aceptás el nuevo diff.

### Paso 4: Aplicar cambios uno por uno

Para cambios triviales, ejecutalos desde la terminal de Cursor (cmd+J):

```bash
bash scripts/fixes/01-guardduty-sa-east-1.sh
bash scripts/fixes/04-kms-rotation.sh
```

Para cambios riesgosos, usá el chat lateral con el script abierto:

```
Voy a aplicar este IMDSv2 script. Antes:
- Mostrame los riesgos.
- Hacé un dry-run con --query y mostrame qué pasaría.
```

### Paso 5: PR mode

Cursor tiene buen workflow git:

1. `cmd+shift+G` → opens source control.
2. Stage los cambios.
3. Pedí a Cursor commit message:
   ```
   Generá commit message para los cambios staged.
   ```
4. Cursor genera algo como:
   ```
   feat(security): baseline de Nivel 1 — GuardDuty, KMS, Cost Anomaly

   Cambios:
   - Habilita GuardDuty en sa-east-1
   - Activa rotation en 6 KMS keys
   - Crea Cost Anomaly monitor con subscription
   - Aplica S3 block public access en 4 buckets

   Cierra issues:
   - #45 (GuardDuty gap)
   - #47 (KMS rotation)
   ```

### Paso 6: Composer para SCPs (Nivel 2)

Para crear los 7 SCPs del Nivel 2:

```
@files templates/scps/

Generá los SCPs faltantes basados en specs/nivel-2/SPEC.md. Para cada SCP:
1. Archivo JSON en templates/scps/.
2. Test en tests/scps/ que verifica que bloquea lo correcto.
3. README.md actualizado.
```

Composer genera todos los files en paralelo. Revisás los diffs, aceptás los que están bien.

## Tips para usar Cursor bien

### Rules en .cursor/rules

Creá `.cursor/rules/aws-security.mdc`:

```markdown
---
description: AWS security context for this repo
---

# AWS Security Context

- Este repo es companion al talk "Securing AWS workloads at scale with AI agents"
- Specs por nivel del Security Maturity Model en specs/
- Templates en templates/
- Cuando generes SCPs, siempre incluí exception para role BreakGlass
- Cuando generes Terraform, usá modules de aws-modules/ y nunca hardcode account IDs
- Para cualquier cambio destructivo (Deny SCPs, terminate, delete), generá PR no apliques directo
- Validá cada cambio AWS con un comando de verificación
```

Cursor aplica estas reglas en todas las generaciones.

### Cursor + Claude Code en paralelo

Setup que funciona bien:

- Cursor abierto en el repo para editing rápido.
- Claude Code en terminal split para tareas autónomas largas.

Mientras Cursor te ayuda inline a editar un archivo, Claude Code corre un audit completo en background.

### Multi-file refactor

```
@codebase

Refactorizá todos los archivos en assessment-cli/checks/ para que:
1. Hereden de una base class común.
2. Tengan un método self.test() que valida el check funciona en una cuenta mock.
3. Documenten el output esperado en docstring.

Hacelo para los 13 checks en paralelo.
```

Composer mode es bueno para esto. Ve los 13 diffs en paralelo, aceptás/rechazás.

## Limitaciones

- **Costos de Cursor**: subscription mensual. Para uso esporádico, considerá las alternativas.
- **Indexado a veces falla**: en repos enormes (>100k files) el codebase context se vuelve lento. No es nuestro caso pero saberlo.
- **Tab completion puede ser intrusivo**: para infra-as-code, conviene apagarlo en archivos `.tf` para no aceptar suggestions ciegamente.

## Comparación con Kiro y Claude Code

| Tarea | Kiro | Claude Code | Cursor |
|---|---|---|---|
| Audit baseline | ✅ ideal | ✅ ideal | OK pero no nativo |
| Generar plan.md | ✅ ideal (spec-aligned) | ✅ ideal | ✅ bueno |
| Aplicar fixes triviales | ✅ con confirmación | ✅ autónomo | OK pero terminal manual |
| Crear N archivos similares | OK | ✅ ideal | ✅ Composer es perfecto |
| Edits inline | Limitado | ❌ terminal-only | ✅ ideal |
| Multi-step autónomo | ✅ | ✅ ideal | OK con Composer |
| PR review | OK | ✅ ideal | ✅ ideal |

**Mi sugerencia:** mezclá. Cursor para edits que necesitan tu input directo (cambios a templates, ajustes a JSON, refactors guiados). Claude Code o Kiro para tareas largas y autónomas (audit, apply, re-scan).

## Recursos

- [Cursor docs](https://docs.cursor.com/)
- [Composer mode](https://docs.cursor.com/composer)
- [Rules](https://docs.cursor.com/context/rules)
- [Codebase context (@codebase)](https://docs.cursor.com/context/codebase)
