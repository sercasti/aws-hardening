# Constraints organizacionales (Demo)

> Constraints de la org ficticia "demo-startup" usada en la demo del talk.

## Compañía

- **Nombre:** demo-startup
- **Tamaño:** 20 personas
- **Stage:** Series A, fintech LATAM
- **AWS spend mensual:** ~USD 8000
- **Cuentas AWS:** 4 (prod, staging, dev, sandbox) bajo una Organization

## Compliance & jurisdicción

- **Industria:** fintech (regulada en LATAM).
- **Jurisdicciones:** Argentina, Chile, Uruguay. Brasil próximo (Q3).
- **Frameworks aplicables:** ISO 27001 (en proceso), LGPD (Brasil future), Ley 25.326 (Argentina).
- **PCI-DSS:** NO aplica directo (terceriza pagos via Stripe).

## Constraints técnicas

### Region restriction

- **Permitidas:** us-east-1 (apps + RDS prod), sa-east-1 (DR + analytics).
- **NUNCA usar:** otras regiones. La consola debe loguear AccessDenied si alguien intenta.

### Tagging

Tags obligatorios en cada recurso:
- `Environment`: sandbox | dev | staging | prod
- `Owner`: email de la persona responsable
- `CostCenter`: engineering | data | ops

Si falta un tag, el recurso debe poder ser deshabilitado por un workflow nocturno (no eliminado, solo stopped).

### Identidades

- **Cero IAM users humanos.** Todo es Identity Center.
- **IAM users programáticos:** permitidos solo para CI/CD, con tag `purpose=ci-cd` y access keys rotadas cada 90 días.
- **Roles cross-account:** solo con ExternalId fuerte (32+ chars).

### Encryption

- **At rest:** todo (S3, RDS, EBS) con customer-managed CMKs.
- **In transit:** TLS 1.2 mínimo. TLS 1.3 preferido.
- **KMS rotation:** habilitado en todas las CMKs.

### Logging

- **CloudTrail:** multi-region, file integrity, encriptado con CMK, bucket dedicado en cuenta de logging separada.
- **VPC Flow Logs:** en todos los VPCs, format full, destino S3.
- **Application logs:** centralizados via OpenSearch (futuro), por ahora CloudWatch Logs por cuenta.

## Constraints process

### Cambios a producción

- **PR + 2 approvers** obligatorio.
- **Approvers:** 1 del equipo de la app, 1 de Platform.
- **Pre-merge checks:** terraform plan, security review (LLM como segundo opinion), test coverage > 80%.
- **Deploy:** GitHub Actions con OIDC (no long-lived credentials).

### Cambios a seguridad

- **SCPs:** PR con 1 approver de Platform.
- **IAM policies:** PR con 1 approver de Platform.
- **Rollout:** sandbox → dev → staging → prod, mínimo 1 semana entre stages.

### Incident response

- **On-call:** 2 personas en rotación semanal (Platform team).
- **Severity 1 (Critical):** page on-call inmediatamente.
- **Severity 2 (High):** ticket alta prioridad, on-call atiende en 4 horas.
- **Severity 3 (Medium):** ticket normal, próximo business day.
- **Post-mortem:** obligatorio para sev1 y sev2.

## Excepciones conocidas

Ninguna activa en este momento. Si necesitás una excepción, ver `templates/scp-exception-template.md`.

## Risk appetite

- **Velocity > 0 cost de seguridad** EXCEPTO en producción.
- En producción: **rather slow & secure than fast & risky**.
- En sandbox/dev: **fast & loose OK** mientras no se exfile data ni se generen costos no esperados.

## Quién es quién

- **Platform/SecOps:** equipo de 2 (founders + 1 senior). Dueños de la Organization.
- **Engineering:** 8 personas, 3 squads de producto.
- **Ops:** 2 personas, on-call + customer support.
- **Data:** 2 personas (analytics + ML).

## Para el agente

Cuando generes plans para esta org:

1. Asumí los constraints de arriba.
2. Prioriza fixes que NO requieren stakeholder coordination (los podés hacer en 1 día).
3. Para los que requieren coordination, generá ticket con stakeholders y target date.
4. NUNCA propongas saltarse el process de PR para producción.
5. Comentá si algún control entra en conflicto con el risk appetite (ej. SCPs muy estrictos pueden frenar dev).
