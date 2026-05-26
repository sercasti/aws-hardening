# Quickstart: tu primera hora con este repo

> Si nunca corriste el loop, este es el camino más corto desde "abrí el repo" hasta "vi mi maturity score subir".

## Pre-requisitos

- Una cuenta AWS de sandbox (NO uses producción la primera vez).
- AWS CLI configurada con credenciales de la cuenta sandbox.
- Python 3.10+.
- 1 hora.
- Un agente AI: Claude Code, Kiro, o Cursor (cualquiera funciona).

## Paso 1: clonar e instalar (5 min)

```bash
git clone https://github.com/sercasti/aws-hardening
cd aws-hardening
cd assessment-cli
pip install -r requirements.txt
```

## Paso 2: generar tu baseline (5 min)

```bash
# Verificar que tenés credenciales
aws sts get-caller-identity

# Generar baseline
python assessment.py --format markdown --output ../baseline.md

# Ver el resultado
cat ../baseline.md
```

Vas a ver algo así:

```
# AWS Security Assessment Report

- Account ID: 123456789012
- Maturity Score: 1.3 / 4

## Nivel 1: El Despertar
| Status | Check | Mensaje |
|---|---|---|
| PASS | mfa_root | Root user tiene MFA |
| FAIL | guardduty | DISABLED en sa-east-1 |
| FAIL | cost_anomaly | No hay monitors |
...
```

Si ves "PASS" en todos los checks de Nivel 1, felicitaciones, ya estás. Pasá al Paso 6.

Si ves "FAIL" o "WARN" en algunos, continuamos.

## Paso 3: leer el spec del Nivel 1 (5 min)

```bash
cd ..
cat specs/nivel-1/SPEC.md | head -100
```

Ese archivo dice qué controles debería cubrir Nivel 1. Tu baseline te dijo cuáles están sin cubrir.

## Paso 4: dejar que un agente arme el plan (10 min)

Abrí tu agente favorito en la raíz del repo. Pasale:

```
Lee specs/nivel-1/SPEC.md y baseline.md.

Tarea: para cada check con status FAIL o WARN en el baseline:
1. Identificá qué control del SPEC.md cubre.
2. Generá la acción concreta (comando AWS CLI o pasos).
3. Estimá esfuerzo y blast radius.
4. Priorizá por (severity * impacto) / esfuerzo.

Output: plan.md con la priorización. NO ejecutes nada todavía.
```

El agente va a generar `plan.md`. Leelo.

## Paso 5: aplicar el primer fix (15 min)

Del plan.md, mirá el item #1. Algo así:

```
[1] CRITICAL — GuardDuty deshabilitado en sa-east-1
    Esfuerzo: 5 min
    Blast radius: ninguno
    Comando:
      aws guardduty create-detector --enable --region sa-east-1
    Verificación:
      aws guardduty list-detectors --region sa-east-1
```

Pasos:

1. **Leé el comando.** Entendé qué hace. Si no lo entendés, preguntale al agente.
2. **Ejecutalo.**
3. **Ejecutá la verificación.** Confirmá que el cambio quedó.

Si todo OK, marcá el item en plan.md como hecho.

Repetí para los items 2 y 3 del plan.

## Paso 6: re-scan (5 min)

```bash
cd assessment-cli
python assessment.py --format markdown --output ../baseline-v2.md
cd ..
```

Ahora hacé un diff con el baseline original:

```bash
diff baseline.md baseline-v2.md
```

Tu maturity score debería haber subido. Si subió: estás en el loop.

## Paso 7: documentar lo que NO automatizaste (10 min)

Items que requieren process change (ej. migrar IAM users a SSO) no se resuelven con un comando. Documentá:

```bash
cat > pending.md <<EOF
# Pending tasks

## Process changes
- [ ] Migrar 3 IAM users humanos a Identity Center
  - Owner: [tu nombre]
  - Target: 2026-06-15
  - Pasos:
    1. Provisionar usuarios en Identity Center
    2. Mapear permission sets
    3. Coordinar con cada usuario para login
    4. Después de 1 semana de uso SSO, deshabilitar IAM user
EOF
```

## Paso 8: agendar el próximo loop (5 min)

El loop no es one-shot. Agendá:

- **Semanal:** correr el assessment, ver si subiste o bajaste de maturity score.
- **Mensual:** revisar pending.md, qué se completó, qué no.
- **Trimestral:** spec review, hay controles nuevos que querés agregar?

Podés hacer el primer scheduled task con cron:

```bash
# Crontab line: corre cada lunes a las 9am
0 9 * * 1 cd ~/work/aws-hardening && python assessment-cli/assessment.py --format markdown --output runs/$(date +\%Y-\%m-\%d).md
```

## Siguiente nivel

Una vez que tu Nivel 1 está en 100%:

1. Leé `specs/nivel-2/SPEC.md`.
2. Diseñá tu primer SCP (ver `templates/scps/`).
3. Aplicá el SCP en audit-mode (a sandbox primero).
4. Después de 2 semanas, mové a prod.

Pasos 1-3 con agente toman 2 horas. Paso 4 requiere paciencia.

## Si algo sale mal

### El comando del agente falló

Pasale el error al agente, pediéle que diagnostique.

### El agente generó un comando peligroso

Bien hecho por revisar. Pediéle que reformule con menor blast radius. Mostrale lo que te preocupó.

### El re-scan no muestra mejora

Verificá:
- ¿El cambio se aplicó realmente?
- ¿Estás scanneando las mismas regiones?
- ¿Hubo un cache de assessment? Re-corré.

### La cuenta sandbox no es representativa

Es una feature, no un bug. La primera vuelta es para aprender el loop. Una vez aprendido, aplicalo a cuentas reales con cuidado.

## Recursos

- Si te trabás: [docs/the-loop-architecture.md](docs/the-loop-architecture.md)
- Si querés entender el modelo: [docs/maturity-model-overview.md](docs/maturity-model-overview.md)
- Si querés ver una demo paso a paso: [demos/kiro/example-output.md](demos/kiro/example-output.md)
- Si pasó un incidente: [playbooks/](playbooks/)
