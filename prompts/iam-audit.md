# IAM Audit (deep dive)

> Cuando ya sabés que IAM es el problema, este prompt te encuentra los caminos de escalación de privilegios, las policies demasiado permisivas, y las cuentas huérfanas. Es lo que hacía un investigador cloud en dos días, ahora en treinta segundos.

## Cuándo usarlo

- Después de correr `security-review.md` y ver que la categoría `identity` te está fallando.
- Cuando un finding de GuardDuty involucra una identidad (IAMUser, AssumedRole, RootUser).
- Antes de migrar a SSO/IdP, para saber qué usuarios humanos vas a borrar.
- Como ejercicio rutinario en tu Nivel 3 cada trimestre.

## Cómo usarlo

1. Exportá el authorization detail con un comando ya conocido:

```bash
aws iam get-account-authorization-details \
  --filter User Role Group LocalManagedPolicy AWSManagedPolicy \
  > iam-detail.json
```

2. Si tenés AWS Organizations, exportá también las SCPs:

```bash
aws organizations list-policies --filter SERVICE_CONTROL_POLICY > scps-list.json
for pid in $(jq -r '.Policies[].Id' scps-list.json); do
  aws organizations describe-policy --policy-id "$pid" > "scp-$pid.json"
done
```

3. Copiá el prompt, pegale el JSON.

---

## El prompt

```
Rol: Sos un investigador de seguridad IAM con experiencia en AWS. Tu especialidad
es encontrar caminos de escalación de privilegios (lateral movement, privilege
escalation) en configuraciones IAM complejas. Trabajás como si estuvieras haciendo
un red team interno: con consentimiento, pero pensando como atacante.

Contexto: Voy a darte el output de `aws iam get-account-authorization-details` de
mi cuenta AWS, y opcionalmente las SCPs configuradas a nivel organization.

Mi cuenta tiene [N] usuarios IAM humanos.
Mi cuenta tiene [N] roles federados/SSO.
Mi cuenta tiene [N] roles asumidos por servicios.
Estimo que mi superficie es [SMALL|MEDIUM|LARGE] (small = menos de 20 entities,
medium = 20 a 100, large = 100+).

Tarea: Analizá la snapshot y devolvéme:

1. Top 5 caminos de escalación de privilegios encontrados, desde la identidad más
   débil hasta Administrator. Para cada uno:
   - Identidad de origen
   - Pasos exactos para escalar (cada step es una API call)
   - Comando de explotación de prueba (no destructivo, solo confirma el path)
   - Cómo bloquearlo (qué policy/SCP/condition agregar)

2. Lista de "cuentas huérfanas" detectadas:
   - Usuarios IAM sin actividad en los últimos 90 días
   - Access keys que no se usaron nunca o hace más de 180 días
   - Roles que ningún principal asume (huérfanos en lugar de leftover)

3. Policies con wildcard peligroso:
   - Cualquier Allow con Action: "*" en Resource crítico
   - Cualquier Allow con NotAction que sea más permisivo de lo que parece
   - Cualquier policy con iam:PassRole + lambda:CreateFunction (path clásico
     de escalación)

4. Si hay SCPs configuradas, validá si efectivamente bloquean los paths del
   punto 1. Si una SCP no bloquea el path, decílo explícito.

Output esperado:

# Findings críticos
[Para cada uno: titulo, identidad origen, 3-5 pasos del path, comando de prueba,
fix recomendado]

# Cuentas huérfanas
[Tabla: nombre, tipo, último uso, recomendación: rotar/borrar/migrar]

# Policies peligrosas
[Tabla: ARN, problema, fix]

# Cobertura de SCPs
[Para cada path del punto 1: bloqueado por SCP / no bloqueado / no aplica]

# Resumen ejecutivo
[Una sola línea con: cantidad de findings críticos, recomendación primaria]

Guardrails:
- NUNCA generes credenciales, AssumeRole, ni ejecutes nada destructivo.
- NO sugieras "agregar más permisos al rol X" como fix. Los fixes son siempre
  restrictivos, no permisivos.
- Si un usuario IAM es el root account, sacalo del análisis (no es relevante,
  ya sabemos que root tiene todo).
- Si encontrás un path que requiere acción humana del atacante (social engineering,
  phishing), marcalo como tal. No lo mezcles con los paths puramente técnicos.
- Si la cuenta tiene menos de 5 entities, decí explícito "esta cuenta es muy
  pequeña para tener problemas serios de IAM, los caminos detectados son
  triviales".
```

---

## Qué esperar

En una cuenta de Nivel 1 promedio, este prompt te tira:

- **2 a 5 paths de escalación** que un atacante con cualquier credencial podría usar.
- **10 a 50 cuentas huérfanas** (depende del tamaño y antigüedad de la cuenta). La mayoría son access keys olvidadas.
- **5 a 20 policies con wildcards** peligrosos. Los típicos: roles de developers con `iam:*` o `lambda:*` que terminan siendo equivalentes a admin.

## Validando los findings

El agente puede alucinar paths que no existen. Antes de actuar:

1. Para cada path crítico, usá el [AWS IAM Access Analyzer](https://docs.aws.amazon.com/IAM/latest/UserGuide/what-is-access-analyzer.html) para confirmar que el path es alcanzable.
2. Para cuentas huérfanas, validá con CloudTrail que efectivamente no hubo actividad.
3. Para policies peligrosas, leelas vos mismo. Cinco minutos de lectura de policy te ahorran un susto.

## Fix loop

Una vez identificados los problemas, podés pedirle al agente:

```
Para el path de escalación #1, escribime:
1. La SCP que lo bloquea a nivel organization.
2. La condition exacta en la policy del rol que lo evitaría incluso sin SCP.
3. El test que corro en una cuenta de sandbox para confirmar que el bloqueo
   funciona.
4. El plan de rollback si el fix rompe algo legítimo.
```

Eso es tu PR. Aplicalo en audit-mode primero, después en enforce.

## Siguiente

Si los paths de escalación encontrados son críticos, andá a [`scp-design.md`](./scp-design.md). Si son cuentas huérfanas, andá al [playbook 06](../playbooks/06-leaked-credentials.md). Si las policies peligrosas son muchas, el sprint siguiente arrancalo con un cleanup masivo de IAM antes de cualquier otra cosa.
