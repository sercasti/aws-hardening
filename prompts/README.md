# Prompts para agentes de IA

Acá vive el material que la audiencia de la charla puede usar el lunes a la mañana sin instalar nada. Cada archivo es un prompt listo para copiar y pegar en tu agente favorito (Claude, GPT, Kiro, Cursor, Gemini, lo que uses).

## El patrón

Todos los prompts siguen la misma estructura:

1. **Rol.** Le decimos al agente qué papel está jugando (auditor de seguridad cloud, revisor de IaC, etc.).
2. **Contexto.** Qué información tiene a mano (tu repo, tu cuenta AWS read-only, tu inventario).
3. **Tarea.** Qué tiene que hacer exactamente.
4. **Output esperado.** El formato del reporte. Si no especificás, te tira texto plano y vas a tener que parsearlo a mano.
5. **Guardrails.** Qué NO tiene que hacer.

Esta estructura no es opcional. Si saltás el guardrail explícito, el agente eventualmente va a hacer algo que no querías.

## Cuál usar para qué

| Prompt | Cuándo usarlo | Tiempo estimado |
|--------|---------------|-----------------|
| [`security-review.md`](./security-review.md) | Tu auditoría base de Nivel 0. Lo corrés el lunes para saber dónde estás parado. | 5 a 15 minutos |
| [`iam-audit.md`](./iam-audit.md) | Cuando sospechás que hay policies demasiado permisivas en tu cuenta. | 10 a 20 minutos |
| [`scp-design.md`](./scp-design.md) | Cuando estás listo para escribir tu primera SCP. El boss de Nivel 2. | 30 a 60 minutos |
| [`blast-radius.md`](./blast-radius.md) | Antes de aplicar un cambio que toca varias cuentas. Te dice qué se rompe si fallás. | 5 minutos |
| [`incident-triage.md`](./incident-triage.md) | Cuando GuardDuty te tira un finding y no sabés por dónde empezar. | 2 a 5 minutos |
| [`pr-review.md`](./pr-review.md) | Cuando tu compañero abre una PR de infra y querés un second opinion antes de aprobarla. | 1 a 3 minutos |
| [`spec-from-scratch.md`](./spec-from-scratch.md) | Para arrancar a escribir tu propio `spec/nivel-X/SPEC.md` para tu organización. | 30 minutos |

## Cómo correrlos

### Opción A: chat directo (sin instalar nada)

1. Abrí Claude (claude.ai), ChatGPT, Gemini, lo que uses.
2. Copiá el contenido del archivo `.md` correspondiente.
3. Pegalo en el chat.
4. Reemplazá las partes entre `[corchetes]` por tu información (cuenta AWS ID, región, repo path).
5. Cargá los archivos relevantes (terraform, IAM dump, etc.) si el prompt los pide.

### Opción B: agentes con acceso a tu cuenta AWS (más potente)

Si usás Kiro, Claude Code, Cursor, Aider, o cualquier agente con tools, podés darle acceso read-only a tu cuenta AWS. Las instrucciones por agente están en [`../demos/`](../demos).

### Opción C: localmente con un wrapper de Bedrock (más privado)

Si no querés mandar datos de tu infra a una API pública, podés correr los prompts vía Bedrock dentro de tu propia cuenta AWS. Ejemplo en [`../assessment-cli/`](../assessment-cli).

## Reglas de uso

1. **Nunca le pegues credenciales activas al prompt.** Si necesitás compartir algo que parece sensible, anonimizalo. Los modelos de proveedores comerciales NO almacenan tus prompts en su corpus de entrenamiento si usás los planes business/enterprise, pero el principio es: si no se lo dirías a un consultor externo, no se lo pegues al agente.
2. **Cargá el inventario, no la cuenta.** En lugar de darle acceso al agente, exportá `aws iam get-account-authorization-details > iam.json` y pegáselo. Es más rápido y deja un audit trail.
3. **Verificá lo que te devuelve.** Los agentes alucinan. Un finding que el agente reporta puede ser falso positivo. Validá los críticos antes de actuar.
4. **Iterá.** Si el output no te sirve, pegale el output de vuelta y decile qué te faltó. El segundo prompt suele ser dos veces más útil que el primero.

## Contribuir

¿Tenés un prompt que te funcionó mejor? PR welcome. Formato: usá la estructura de los 5 puntos arriba.
