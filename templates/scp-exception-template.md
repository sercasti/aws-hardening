# SCP Exception Registry

> Cuando un SCP rompe un caso de uso legítimo, NO quites el SCP. Documentá la excepción acá, ajustá el SCP, y revisá cada 90 días.

## Por qué documentar excepciones

Una excepción sin documentar tiene dos consecuencias:

1. Nadie sabe por qué existe. En 3 meses, alguien la "limpia" y rompe algo.
2. Se acumulan. En 1 año tenés 30 excepciones, nadie sabe cuáles son válidas, y los SCPs ya no protegen lo que deberían.

Una excepción documentada tiene un dueño, una razón, una fecha de revisión, y un plan para quitarla.

## Template por excepción

```markdown
## EXC-[NUMERO]: [Titulo corto]

- **SCP afectado:** [scp/03-deny-region-outside-list.json]
- **Excepción técnica:** [ARN específico, OU específica, tag específico]
- **Solicitante:** [Persona o equipo]
- **Aprobado por:** [SecOps lead]
- **Fecha de creación:** [YYYY-MM-DD]
- **Fecha de revisión:** [YYYY-MM-DD, máx 90 días]
- **Razón de la excepción:**
  [Explicación clara del caso de uso. Por qué este caso no puede cumplir el SCP. Qué se intentó antes de aceptar la excepción.]
- **Riesgo residual:**
  [Qué riesgo aceptás al permitir esta excepción. Concreto, no vago.]
- **Mitigaciones compensatorias:**
  [Qué tenés en su lugar. Logging extra, alertas específicas, review manual, etc.]
- **Plan de salida:**
  [Cómo y cuándo vas a poder quitar la excepción. Si "nunca", justificar.]
```

## Ejemplo

### EXC-001: ML training en us-east-1 desde cuenta sandbox

- **SCP afectado:** `scp/03-deny-region-outside-list.json`
- **Excepción técnica:** Account ID `123456789012`, etiqueta `purpose=ml-research`
- **Solicitante:** Equipo Data Science (Carla Sánchez)
- **Aprobado por:** SecOps lead (Diego Rodríguez), 2026-04-15
- **Fecha de creación:** 2026-04-15
- **Fecha de revisión:** 2026-07-15
- **Razón de la excepción:**
  El equipo de Data Science usa SageMaker training jobs con datasets públicos en us-east-1. Mover los datasets a sa-east-1 (nuestra región aprobada) tendría costo de transferencia significativo y latencia mayor en pulls de Hugging Face. La cuenta sandbox está aislada de prod (sin VPC peering, sin shared roles).
- **Riesgo residual:**
  Si un atacante compromete una credencial del equipo, puede lanzar recursos costosos en us-east-1 sin que GuardDuty de prod los vea (GuardDuty está activado por cuenta).
- **Mitigaciones compensatorias:**
  - GuardDuty habilitado en la cuenta sandbox específicamente en us-east-1.
  - Cost Anomaly Detection con threshold de USD 100/día (en lugar del default).
  - Las credenciales del equipo rotan cada 7 días via Identity Center.
  - No hay roles que la cuenta sandbox pueda asumir en prod.
- **Plan de salida:**
  Q3 2026: evaluar si SageMaker en sa-east-1 puede acceder a Hugging Face directo (depende de feature availability AWS). Si sí, migrar y cerrar la excepción.

## Excepciones activas

| ID | Titulo | SCP | Solicitante | Revisión | Estado |
|---|---|---|---|---|---|
| EXC-001 | ML training en us-east-1 | 03-deny-region | Data Science | 2026-07-15 | Active |

## Excepciones cerradas

| ID | Titulo | Fecha cierre | Razón |
|---|---|---|---|
| | | | |

## Proceso

### Solicitar excepción

1. Llenar el template.
2. PR al repo de gobierno cloud.
3. Discutir en el próximo standup de SecOps (máx 1 semana).
4. Si se aprueba, mergear. Si no, comentar razones y proponer alternativa.

### Aprobar excepción

Criterios:

1. **¿Hay alternativa técnica que cumple el SCP?** Si la respuesta razonable es sí, no se aprueba.
2. **¿El riesgo residual es manejable?** Con las mitigaciones, ¿es comparable al riesgo si cumpliera el SCP?
3. **¿Hay plan de salida realista?** "Nunca vamos a poder salir" rara vez es la respuesta correcta.

### Revisar excepción

Cada 90 días, el dueño debe:

1. Confirmar que la excepción sigue siendo necesaria.
2. Actualizar el plan de salida con progreso.
3. Confirmar que las mitigaciones siguen activas.

Si la respuesta a 1 es "no", cerrar la excepción. Si en la revisión #3 (270 días) todavía no hay plan claro de salida, escalada a leadership.

### Cerrar excepción

Cuando ya no es necesaria:

1. Verificar que ningún workload depende de la excepción (testear).
2. Quitar el ARN/tag de la condición del SCP.
3. Documentar en la tabla de "Excepciones cerradas".

## Anti-patterns

- ❌ **"Es solo por una semana".** En tu organización, "una semana" significa 18 meses. Documentá igual.
- ❌ **"No vale la pena documentar, es algo simple".** Algo simple que nadie entiende en 6 meses te cuesta horas de archaeology.
- ❌ **Excepciones sin dueño.** Si nadie responde por la excepción, debería ser cerrada.
- ❌ **Excepciones sin plan de salida.** Tendés a olvidar y la excepción es permanente. Plan de salida obligatorio.
