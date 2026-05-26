# Scripts

> Scripts de automatización para los playbooks de Incident Response. Fase 2 ("Asistido"): humano corre el script, script hace queries y acciones rutinarias, humano decide próximos pasos.

## Filosofía

Estos scripts NO automatizan la respuesta. Automatizan la recopilación de información que necesitás para decidir.

Cuando GuardDuty te despierta a las 3am, no querés escribir 12 comandos AWS CLI. Querés un comando que te dé contexto completo en 10 segundos.

## Scripts

### `triage-public-bucket.sh`

Para [Playbook 02](../playbooks/02-public-s3-bucket.md).

```bash
./triage-public-bucket.sh [BUCKET_NAME]
```

Output: estado actual del bucket, listado de objetos públicos, quién lo hizo público (CloudTrail), tags relevantes.

### `iam-activity-report.sh`

Para [Playbook 03](../playbooks/03-iam-privilege-escalation.md).

```bash
./iam-activity-report.sh [USERNAME] --hours 24
```

Output: acciones de la identidad en últimas N horas, policies modificadas, recursos creados, IPs usadas.

### `region-activity-report.sh`

Para [Playbook 04](../playbooks/04-unauthorized-region-activity.md).

```bash
./region-activity-report.sh ap-south-1 --hours 48
```

Output: recursos activos en la región, costo del período, lanzamientos recientes, identidades involucradas.

### `cost-spike-triage.sh`

Para [Playbook 05](../playbooks/05-cost-anomaly.md).

```bash
./cost-spike-triage.sh --start 2026-05-25 --end 2026-05-27
```

Output: servicios con spike, regiones afectadas, identidades, posibles causas.

### `isolate-instance.sh`

Para [Playbook 06](../playbooks/06-compromised-ec2.md).

```bash
./isolate-instance.sh i-0abcdef1234567890
```

Output: aplica quarantine SG, snapshot de volúmenes, revoca sesiones del role. Persiste evidencia en `/tmp/ir-[INSTANCE_ID]-[TIMESTAMP]/`.

### `cross-account-audit.sh`

Para [Playbook 07](../playbooks/07-cross-account-anomaly.md).

```bash
./cross-account-audit.sh [ROLE_NAME] --days 30
```

Output: lista de cuentas source que asumieron el rol, identidades, frecuencia, acciones realizadas.

### `exfil-timeline.sh`

Para [Playbook 08](../playbooks/08-data-exfiltration.md).

```bash
./exfil-timeline.sh [IDENTITY] --start 2026-05-25
```

Output: timeline de acciones, IPs, recursos accedidos. Cálculo aproximado de bytes egresados.

## Requirements

```bash
# AWS CLI v2
aws --version

# jq
jq --version

# Permisos: SecurityAudit + ReadOnlyAccess + acceso a CloudTrail Lookup
```

## Convenciones

- Cada script imprime un banner al inicio con la acción que va a tomar.
- Si el script va a ejecutar algo destructivo, pide confirmación explícita.
- Outputs van a stdout para que puedas pipe.
- Errors a stderr.
- Exit codes: 0 = OK, 1 = error, 2 = no encontrado, 3 = unauthorized.

## Cómo agregar uno nuevo

Template en [`_template.sh`](./_template.sh). Patrón:

```bash
#!/usr/bin/env bash
set -euo pipefail

# Args parsing
INPUT=${1:-}
if [ -z "$INPUT" ]; then
  echo "Usage: $0 [INPUT]" >&2
  exit 1
fi

# Banner
cat <<EOF
=== Script: nombre ===
Input: $INPUT
Started: $(date -u)
EOF

# Acciones
# ...

# Resumen
echo "Done."
```
