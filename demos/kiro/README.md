# Demo: Kiro

> Esta es la demo que mostré en el talk. Kiro tiene un spec mode que se alinea conceptualmente con los niveles del Security Maturity Model: declarás lo que querés en un spec, Kiro propone los pasos, vos aprobás, ejecuta.

## Por qué Kiro

- **Spec mode**: tu `SPEC.md` es el contrato. Kiro lo lee y genera todo lo demás (tasks, código, tests) en alineación.
- **Plan-first**: antes de tocar nada, Kiro te muestra qué va a hacer. Reducís riesgo de "el agente borró producción mientras yo no miraba".
- **AWS-friendly**: tiene awareness nativa de servicios AWS y sus configs típicas.

## Setup

```bash
# Instalar Kiro
# (Sigue las instrucciones de https://kiro.dev/)

# Configurar tu folder de trabajo
mkdir -p ~/work/aws-hardening-demo
cd ~/work/aws-hardening-demo

# Copiar el spec del nivel que querés alcanzar
cp ../aws-hardening/specs/nivel-1/SPEC.md .

# Copiar el baseline assessment
cp /tmp/baseline.json .
```

## Demo step-by-step

### Paso 1: Darle contexto a Kiro

Abrí Kiro en `~/work/aws-hardening-demo` y pasale como contexto:

- `SPEC.md` (el nivel que querés alcanzar)
- `baseline.json` (estado actual de tu cuenta)

### Paso 2: Prompt inicial

```
Lee el baseline.json y el SPEC.md de Nivel 1.

Tarea:
1. Identifica qué controles del SPEC.md ya están en place segun el baseline.
2. Identifica qué controles faltan o están parciales.
3. Priorizá los gaps por: severity, esfuerzo, blast radius.
4. Generá un plan.md con la lista priorizada y, para cada item, el comando AWS CLI o pasos exactos para resolverlo.

NO ejecutes nada todavía. Solo plan.
```

Kiro va a generar `plan.md` con algo así:

```markdown
# Plan de remediación: Nivel 1

## Gap 1: GuardDuty deshabilitado en sa-east-1
- Severidad: Critical
- Esfuerzo: 5 min
- Blast radius: ninguno (habilitar es seguro)
- Acción:
  aws guardduty create-detector --enable --region sa-east-1

## Gap 2: Cost Anomaly Detection no configurado
- Severidad: High
- Esfuerzo: 10 min
- Blast radius: ninguno
- Acción:
  - Crear monitor via consola (Cost Management → Cost Anomaly Detection)
  - O via CLI:
    aws ce create-anomaly-monitor --anomaly-monitor file://monitor.json
...
```

### Paso 3: Ejecutar interactivamente

```
Ejecutemos Gap 1. Antes de correr el comando:
1. Mostrame qué hace exactamente.
2. Confirmá que no impacta otros recursos.
3. Ejecutalo y mostrame el resultado.
```

Kiro va a:

1. Explicar que `create-detector --enable` crea un detector pasivo (sin samples).
2. Confirmar que no afecta otros recursos.
3. Esperar tu aprobación.
4. Ejecutar.
5. Verificar que GuardDuty quedó habilitado.

### Paso 4: Avanzar nivel

Después de cubrir Nivel 1:

```
Re-ejecutar el assessment:
python ../aws-hardening/assessment-cli/assessment.py --output baseline-v2.json

Ahora pasale el nuevo baseline + SPEC del Nivel 2.
```

### Paso 5: Validar el progreso

```
Comparame baseline.json (antes) con baseline-v2.json (después).

Show me:
- Maturity score: antes vs después.
- Checks que pasaron de fail a pass.
- Checks que siguen failing.
- Próximas acciones recomendadas.
```

## Tips para usar Kiro bien

### Specs claros

El spec es el contrato. Si tu spec dice "queremos buenas prácticas de seguridad", Kiro tiene que adivinar. Si dice "habilitar GuardDuty en sa-east-1, us-east-1; bloquear public S3 buckets via SCP; rotar KMS keys cada 365 días", Kiro tiene una guía exacta.

### Plan antes de ejecutar

Siempre pedí plan primero. Ejecutá paso a paso. Resistí la tentación de decir "hacé todo".

### Outputs verificables

Cada acción debería terminar con una verificación:

```
Después de cada cambio, mostrame:
1. Comando AWS CLI para verificar que el cambio quedó aplicado.
2. Resultado esperado.
3. Ejecutá la verificación y mostrá output.
```

## Limitaciones que vas a encontrar

- **Kiro no tiene tus credenciales por default.** Si querés que ejecute comandos AWS, configurá tu CLI antes y permitilo ejecutar.
- **No reemplaza tu juicio.** Si te propone aplicar un SCP, vos validás que no rompe nada en producción.
- **Las explicaciones que da pueden ser superficiales en algunos AWS features ultra-específicos.** Cruzar con la doc oficial cuando el cambio es crítico.

## Ejemplo completo de output

Ver [`example-output.md`](./example-output.md) para una sesión completa con Kiro, paso a paso.

## Recursos

- [Kiro docs](https://kiro.dev/)
- [Specs en Kiro](https://kiro.dev/docs/specs)
- [Best practices](https://kiro.dev/docs/best-practices)
