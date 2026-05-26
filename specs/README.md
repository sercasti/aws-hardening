# Specs del modelo de madurez

Los specs son el contrato entre tu organización y el agente. Definen qué cuenta como "fortificado" en cada nivel del AWS Security Maturity Model.

## Por qué specs y no prompts

Los prompts son ad-hoc. Los corrés, te devuelve algo, no queda traza. Si dos personas corren el mismo prompt en momentos diferentes, pueden obtener resultados distintos.

Los specs son persistentes. Viven en el repo. Tienen historia de git. Los modificás vía pull request, con review. El agente los lee antes de proponer cambios, y cuando propone una PR, cita qué control del spec está intentando satisfacer.

Esto te da:

1. **Reproducibilidad.** Dos personas corriendo el agente contra el mismo spec en el mismo estado de la cuenta obtienen el mismo resultado.
2. **Auditabilidad.** Cada PR del agente está justificada contra una línea específica del spec.
3. **Evolución controlada.** El spec se modifica con review. No hay deriva silenciosa.
4. **Onboarding.** Un dev nuevo entiende qué espera la organización leyendo el spec, no preguntando.

## Cuál nivel arrancar

Si nunca hiciste hardening sistemático, arrancá con [`nivel-1/SPEC.md`](./nivel-1/SPEC.md). En un día y sin presupuesto te llevás el 80% de los riesgos básicos.

Si ya cumplís Nivel 1 sólidamente (auditado por el assessment CLI), pasá a [`nivel-2/SPEC.md`](./nivel-2/SPEC.md). Acá es donde se pone difícil políticamente, no técnicamente.

Nivel 3 y 4 son recorridos de meses, no de sprint. Los specs están acá para que sepas dónde vas.

## Cómo se lee un SPEC.md

Cada archivo sigue la misma estructura:

```markdown
# Spec - Nivel X

## Visión
Una frase

## Principios
3 a 5 principios accionables

## Controles obligatorios
Por categoría (identity, network, data, monitoring, organization).
Cada uno con: estado deseado, comando de verificación, severidad si no se cumple.

## Anti-patterns
Cosas que el agente debería marcar inmediatamente.

## Métricas de éxito
Cómo sabés que estás en este nivel.

## Boss fight
El obstáculo más difícil de este nivel. Cómo superarlo.
```

## Cómo lo usa el agente

Tres formas, de menos a más integrada:

### Forma A: copia y pega

Abrís el SPEC.md, lo copiás, lo pegás en el chat con tu agente preferido, le decís "auditá mi cuenta contra este spec". Funciona con cualquier modelo de cualquier proveedor.

### Forma B: file reference

Si usás un agente con file access (Kiro, Cursor, Claude Code), apuntás el SPEC.md como archivo de contexto. El agente lo lee antes de cualquier propuesta. Ejemplo:

```bash
claude code --context-file specs/nivel-1/SPEC.md
```

### Forma C: spec mode (Kiro)

Kiro tiene un modo donde el SPEC.md es la "intent" del trabajo. El agente solo propone cambios que mueven el estado actual hacia lo que define el spec. Esto te da bounds duros: no puede inventar tareas, solo cerrar gaps contra el spec.

Ver [`../demos/kiro/`](../demos/kiro) para el setup completo.

## Cómo escribir tu propio spec

Los specs del repo son referencias. Tu organización tiene contexto que estos specs no contemplan: workloads específicos, regulaciones particulares, excepciones legítimas.

Para escribir tu propio spec, andá a [`../prompts/spec-from-scratch.md`](../prompts/spec-from-scratch.md). Es el prompt que te guía a escribir un SPEC.md específico a tu organización, no genérico.

## Versionado

Los specs del repo se actualizan trimestralmente. Cada update va a un PR con changelog. Si seguís un spec específico de este repo, fijá la versión en tu fork para evitar drift inesperado:

```bash
git submodule add -b v2026.Q2 https://github.com/sercasti/aws-hardening.git specs
```

(Las tags `vYYYY.QN` se publican cada release.)
