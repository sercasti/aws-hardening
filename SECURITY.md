# Security Policy

## Reportar vulnerabilidades

Si encontrás una vulnerabilidad en este repo (en los scripts, en el código de assessment-cli, en algún template), por favor NO abras un issue público.

Mandalo por mail a: sergio.castineyras@caylent.com

### Qué incluir

- Descripción del issue.
- Reproducción paso a paso.
- Impacto potencial (qué podría hacer un atacante).
- Sugerencia de fix si tenés una.

### Qué esperar

- Acuse de recibo en 48 horas.
- Análisis y plan de remediación dentro de 1 semana.
- Fix mergeado dentro de 2 semanas para issues high/critical.
- Credit en el changelog si lo querés.

## Scope

Vulnerabilidades en:

- Scripts de `scripts/` que ejecutan comandos AWS.
- Código de `assessment-cli/`.
- Templates de SCP/IAM/KMS que podrían tener defectos.
- Prompts que podrían ser explotables (prompt injection vectors).

### Out of scope

- Issues en AWS services en sí mismos (reportá a AWS).
- Issues en herramientas third-party (Kiro, Claude Code, Cursor).
- Issues en este repo que requieran acceso privilegiado previo (asumimos que el clone es seguro).

## Best practices al usar este repo

Si vas a aplicar este repo a tu cuenta AWS:

1. **Cuenta sandbox primero.** Nunca corras un script de IR contra producción sin entender qué hace.
2. **Read the script.** Antes de ejecutar `isolate-instance.sh`, leelo. Tomá 5 minutos.
3. **Credenciales mínimas.** No le pases credenciales de root al agente.
4. **Logs locales.** Outputs de scripts no commitearlos al repo.
5. **Branch protections.** Si forkeás este repo y lo usás internamente, configurá branch protection.

## Disclosure pública

Si reportás una vuln y querés disclosure público, lo coordinamos. Default: disclosure después de 30 días del fix mergeado, con credit al reportero.

Si la vuln es high/critical y afecta gente que ya usa el repo en prod, podemos hacer disclosure más rápido (CVE si aplica).
