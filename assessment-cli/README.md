# Assessment CLI

> CLI que escanea una cuenta AWS y emite un reporte estructurado del nivel actual del Security Maturity Model. Pensada como punto de partida del flywheel: lo que esta CLI no detecta, lo agregamos al SPEC.

## Cómo funciona

```
   ┌────────────────────────────────┐
   │  python assessment.py          │
   │  --account [ID]                │
   │  --regions us-east-1,sa-east-1 │
   └──────────────┬─────────────────┘
                  ▼
   ┌────────────────────────────────┐
   │  Por cada check:               │
   │  - Query a AWS APIs            │
   │  - Evaluar contra criterio     │
   │  - Emitir Pass/Fail/Warning    │
   └──────────────┬─────────────────┘
                  ▼
   ┌────────────────────────────────┐
   │  Output:                       │
   │  - JSON (machine-readable)     │
   │  - Markdown (human report)     │
   │  - Maturity score (1-4)        │
   └────────────────────────────────┘
```

## Instalación

```bash
git clone https://github.com/sercasti/aws-hardening
cd aws-hardening/assessment-cli
pip install -r requirements.txt

# Asegurate que tu CLI de AWS tiene credenciales con readonly access (ViewOnlyAccess + SecurityAudit)
aws sts get-caller-identity
```

## Uso

```bash
# Assessment completo
python assessment.py --output report.md

# Solo Nivel 1
python assessment.py --level 1

# Output como JSON para consumir desde otro script o LLM
python assessment.py --format json --output report.json

# Solo ciertos checks
python assessment.py --checks mfa_root,cloudtrail,guardduty
```

### Output esperado

```
================================================================================
AWS Security Assessment Report
================================================================================
Account ID: 123456789012
Account Alias: production
Region scan: us-east-1, sa-east-1
Timestamp: 2026-05-26T14:23:11Z
Total checks: 24

NIVEL 1 — EL DESPERTAR                        [12/15 PASS]
================================================================================
[PASS]    MFA en root                          Hardware MFA detected
[PASS]    CloudTrail multi-region              Enabled in all 17 regions
[FAIL]    GuardDuty                            DISABLED in sa-east-1
[WARN]    Identity Center                      Configured but 3 IAM users still active
[PASS]    IAM Access Analyzer                  Enabled, 2 active findings
[FAIL]    Cost Anomaly Detection               No monitors configured
[PASS]    Budget alerts                        2 budgets, alerts to ops@
[PASS]    S3 block public access (account)     Enabled
[WARN]    S3 block public access (buckets)     8/12 buckets, 4 missing
[FAIL]    Default region restriction           No SCP, instances in 9 regions
...

NIVEL 2 — LOS CIMIENTOS                       [3/8 PASS]
================================================================================
[FAIL]    SCP en place                         No active SCPs in Organization
[FAIL]    IAM baseline policies                No baseline policies attached
[WARN]    KMS rotation                         12/18 keys rotation enabled
[PASS]    VPC Flow Logs                        Enabled on all VPCs
...

NIVEL 3 — LA ATALAYA                          [1/6 PASS]
================================================================================
[FAIL]    Security Hub                         Not enabled
[FAIL]    Centralized logging                  Logs scattered across accounts
...

NIVEL 4 — LA CIUDADELA                        [0/4 PASS]
================================================================================
[FAIL]    Detection-as-code                    No automated detection rules in source control
...

================================================================================
MATURITY SCORE: 1.5 / 4
================================================================================

Action items prioritizados:
1. Habilitar GuardDuty en sa-east-1 (5 min, 0 USD, Critical impact)
2. Configurar Cost Anomaly Detection (10 min, 0 USD, High impact)
3. Aplicar S3 block public access en 4 buckets missing (30 min, 0 USD, High impact)
...
```

## Checks incluidos

### Nivel 1: El Despertar

- `mfa_root.py` — verifica MFA en usuario root.
- `cloudtrail.py` — verifica CloudTrail multi-region y file integrity.
- `guardduty.py` — verifica GuardDuty en todas las regions activas.
- `identity_center.py` — verifica que SSO está configurado.
- `access_analyzer.py` — verifica IAM Access Analyzer activo.
- `cost_anomaly.py` — verifica Cost Anomaly Detection.
- `budgets.py` — verifica budget alerts.
- `s3_public_access.py` — verifica block public access a nivel cuenta y buckets.

### Nivel 2: Los Cimientos

- `scps.py` — verifica que hay SCPs activos y cuáles.
- `iam_baseline.py` — verifica baseline policies.
- `kms_rotation.py` — verifica rotation enabled en CMKs.
- `vpc_flow_logs.py` — verifica VPC Flow Logs.
- `imdsv2.py` — verifica que EC2 instances usan IMDSv2.

### Nivel 3: La Atalaya

- `security_hub.py` — verifica Security Hub habilitado y aggregator.
- `centralized_logging.py` — verifica logging centralizado.
- `config_rules.py` — verifica AWS Config rules de seguridad.

### Nivel 4: La Ciudadela

- `detection_as_code.py` — verifica si hay detection rules en git.
- `automated_response.py` — verifica si hay Lambdas/StepFunctions de IR.

## Cómo agregar un check

```python
# assessment-cli/checks/mi_check.py

from .base import Check, CheckResult, Severity

class MiCheck(Check):
    name = "mi_check"
    level = 1
    description = "Verifica que mi config esta como deberia"

    def run(self, session):
        # session es boto3.Session con credenciales
        client = session.client('servicio')
        try:
            response = client.algo()
            if self._es_correcto(response):
                return CheckResult.passed("Configuracion correcta")
            else:
                return CheckResult.failed(
                    "Configuracion mal",
                    remediation="Hacé X, Y, Z"
                )
        except Exception as e:
            return CheckResult.warned(f"No pude verificar: {e}")

    def _es_correcto(self, response):
        return response.get('CampoCritico') == 'valor_esperado'
```

Y registrarlo:

```python
# assessment-cli/assessment.py
from checks.mi_check import MiCheck

CHECKS = [
    # ...
    MiCheck(),
]
```

## Filosofía

Esta CLI NO pretende reemplazar Security Hub, Prowler, ScoutSuite, ni AWS Foundational Security Best Practices. Existe para:

1. Dar un baseline rápido sin configurar nada de infra.
2. Producir un output que LLMs pueden consumir directo para priorizar acciones.
3. Permitir custom checks que tu org necesita y que tools comerciales no cubren.

Para profundizar, usá las tools establecidas:

- [Prowler](https://github.com/prowler-cloud/prowler) — el más completo para AWS.
- [ScoutSuite](https://github.com/nccgroup/ScoutSuite) — multi-cloud.
- [Steampipe](https://steampipe.io/) — queries SQL sobre tu cuenta.
- [AWS Security Hub](https://aws.amazon.com/security-hub/) — el primer-party.

## Output JSON schema

```json
{
  "metadata": {
    "account_id": "123456789012",
    "account_alias": "production",
    "timestamp": "2026-05-26T14:23:11Z",
    "regions_scanned": ["us-east-1", "sa-east-1"],
    "checks_run": 24
  },
  "results": [
    {
      "check": "mfa_root",
      "level": 1,
      "status": "pass",
      "message": "Hardware MFA detected",
      "severity": "critical",
      "remediation": null,
      "evidence": {
        "mfa_devices": ["arn:aws:iam::..."]
      }
    },
    {
      "check": "guardduty",
      "level": 1,
      "status": "fail",
      "message": "DISABLED in sa-east-1",
      "severity": "critical",
      "remediation": "Ejecutar: aws guardduty create-detector --enable --region sa-east-1",
      "evidence": {
        "regions_enabled": ["us-east-1"],
        "regions_disabled": ["sa-east-1"]
      }
    }
  ],
  "summary": {
    "total": 24,
    "pass": 16,
    "fail": 6,
    "warn": 2,
    "maturity_score": 1.5,
    "level_1_completion": 0.8,
    "level_2_completion": 0.375,
    "level_3_completion": 0.166,
    "level_4_completion": 0.0
  },
  "prioritized_actions": [
    {
      "rank": 1,
      "check": "guardduty",
      "effort": "5 minutes",
      "cost_usd": 0,
      "impact": "critical",
      "action": "Habilitar GuardDuty en sa-east-1"
    }
  ]
}
```

Este JSON está pensado para que un LLM lo consuma y arme un plan, o para que un dashboard lo grafica.

## Limitaciones

- Solo escanea las regions que le pasás. No detecta uso en regions ocultas.
- Algunos checks requieren permisos elevados (ej. Organizations). Si tu sesión no los tiene, esos checks dan WARN.
- No detecta misconfigurations a nivel app (XSS, SQL injection, etc.). Para eso usá DAST/SAST específicos.

## Roadmap

- [ ] Output como SARIF para integration con security platforms.
- [ ] Mode incremental: solo report changes since last run.
- [ ] Integration con Slack para notify on degradation.
- [ ] Multi-account scanning con AssumeRole automático.
- [ ] Custom checks loading desde un folder externo.
