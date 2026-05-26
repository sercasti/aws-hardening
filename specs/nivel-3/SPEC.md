# Spec — Nivel 3: La Atalaya

> Tiempo de implementación: 1 a 2 meses. Costo recurrente: bajo (cientos de USD/mes). Boss fight: automatizar tu primer playbook de incident response end-to-end.

## Visión

En Nivel 3 dejamos de ser reactivos. Telemetría continua, detección con baselines, alerting que llega a humanos despiertos, y al menos un playbook de IR automatizado. Atalaya = "vigilancia desde altura". El equipo ya no se entera por Twitter de que pasó algo en su cuenta.

## Principios

1. **Detectar es solo el primer paso.** Si detectás y no respondés, es como no detectar.
2. **Telemetría se centraliza.** Logs de todas las cuentas van a un destino único (cuenta security), no a cada cuenta independientemente.
3. **El primer playbook automático es el escalón crítico.** Hasta que tengas uno funcionando, estás en Nivel 2.5.
4. **No es "más data, mejor".** La señal/ruido importa más que el volumen. Si tus alertas tienen >20% de falsos positivos, NADIE las lee.
5. **Threat hunting es proactivo.** Una vez por trimestre, alguien busca lo que las alertas no encontraron.

## Controles obligatorios

### Monitoring

#### MON.1: Security Hub habilitado, agregando findings de GuardDuty/Inspector/Macie/Config

- **Estado deseado:** Security Hub activo en todas las regiones, con integraciones a las herramientas relevantes. Dashboard único donde ver todo.
- **Verificación:**

  ```bash
  aws securityhub describe-hub
  aws securityhub list-enabled-products-for-import
  ```

- **Severidad si falla:** high

#### MON.2: Centralized logging architecture

- **Estado deseado:** Cuenta security recibe CloudTrail, VPC Flow Logs, GuardDuty findings, Security Hub findings de todas las cuentas miembro.
- **Implementación:** Org Trail + Org GuardDuty con delegated admin en cuenta security.
- **Verificación:**

  ```bash
  aws cloudtrail describe-trails --include-shadow-trails | grep IsOrganizationTrail
  ```

- **Severidad si falla:** critical

#### MON.3: SIEM o data lake para query de logs

- **Estado deseado:** Athena sobre los logs centralizados (low cost), o un SIEM dedicado (Splunk, Datadog, Wazuh, etc.).
- **Por qué importa:** Sin query capability, los logs son un cementerio. Cuando ocurre un incidente, necesitás responder "¿quién hizo qué entre la hora X e Y?" en minutos, no en horas.
- **Verificación:** Existencia de queries documentadas y testeadas.
- **Severidad si falla:** high

#### MON.4: Detective habilitado (opcional, recomendado)

- **Estado deseado:** Amazon Detective activo en cuenta security, integrado con GuardDuty.
- **Por qué importa:** Te ahorra horas de trabajo de correlación en cada incidente.
- **Severidad si falla:** medium

### Response

#### RES.1: Alerting routing a humanos despiertos

- **Estado deseado:** Findings de severidad critical/high van a un sistema de paging (PagerDuty, OpsGenie). Medium van a un canal de Slack que el equipo lee. Low se acumulan en dashboard para review semanal.
- **Verificación:** Test manual: triggerear un finding ficticio y validar que llega al destino correcto.
- **Severidad si falla:** critical
- **Anti-pattern:** "Mandamos todo a un email genérico que revisa el manager los lunes." Esto no es alerting, es archivo.

#### RES.2: Runbooks documentados para los 10 findings más comunes de GuardDuty

- **Estado deseado:** Documentación accesible con "qué hacer si ves finding X" para los tipos más frecuentes.
- **Verificación:** Existencia + práctica trimestral (game day).
- **Severidad si falla:** high

#### RES.3: Primer playbook automatizado en producción

- **Estado deseado:** Al menos un finding common (ej. credencial filtrada) tiene respuesta automática end-to-end (rotación, revocación, notificación, ticket).
- **Verificación:** Test del playbook en sandbox + log de ejecuciones en producción.
- **Severidad si falla:** high (boss fight de este nivel)

### Detection

#### DET.1: Custom GuardDuty findings habilitados

- **Estado deseado:** Threat intel feeds custom configurados con IOCs específicos del negocio (IPs internas conocidas, ranges sospechosos).
- **Verificación:**

  ```bash
  aws guardduty list-threat-intel-sets --detector-id [DETECTOR_ID]
  ```

- **Severidad si falla:** medium

#### DET.2: VPC Flow Logs habilitados con queries documentadas

- **Estado deseado:** Flow logs en s3, con queries Athena ya escritas para responder "¿hubo data exfil desde X?", "¿qué IPs externas conectó Y?", etc.
- **Verificación:** Existencia de queries en `playbooks/queries/`.
- **Severidad si falla:** medium

#### DET.3: Macie escaneando buckets con data sensible

- **Estado deseado:** Macie habilitado para buckets con tag `data-classification=sensitive`. Findings revisados mensualmente.
- **Verificación:**

  ```bash
  aws macie2 list-classification-jobs
  ```

- **Severidad si falla:** medium

### Process

#### PRO.1: Game days trimestrales

- **Estado deseado:** Una vez por trimestre, el equipo corre un simulacro: un finding ficticio inyectado, el on-call ejecuta el playbook, se mide tiempo de respuesta.
- **Verificación:** Calendar entries + post-mortem doc.
- **Severidad si falla:** medium

#### PRO.2: Métricas de respuesta

- **Estado deseado:** MTTD (Mean Time to Detect) y MTTR (Mean Time to Respond) medidos.
- **Targets sugeridos:**
  - MTTD: <15 min para critical findings
  - MTTR: <2 horas para critical findings
- **Verificación:** Dashboard con números actualizados.

## Anti-patterns

- ❌ Logs en cada cuenta individualmente (sin centralizar)
- ❌ Alertas a emails que nadie lee
- ❌ "Tenemos GuardDuty" sin tener proceso de respuesta
- ❌ Findings de Security Hub sin owner asignado
- ❌ Game days que se cancelan porque "estamos ocupados con cosas reales"
- ❌ Playbooks que nunca se testearon
- ❌ Threshold de alerting tan bajo que el on-call lo desactiva por noise

## Métricas de éxito

Estás en Nivel 3 cuando:

- Tenés centralized logging funcionando.
- MTTD para critical findings está por debajo de 15 min en promedio (último mes).
- MTTR para critical findings está por debajo de 2 horas.
- Tu primer playbook automatizado ya manejó al menos 3 findings reales (no de prueba) sin intervención humana.
- Corriste 2 game days en el último año.

## Boss fight: el primer playbook automático

**El problema:** Pasar de "responder manualmente" a "responder automáticamente" requiere confianza en la automatización. Un playbook mal diseñado puede generar más daño que la amenaza que estás respondiendo (ej. matar un servicio legítimo creyendo que es comprometido).

**El método:**

1. **Elegí el playbook adecuado para empezar.** No el más complejo. El más SEGURO. La rotación de credenciales filtradas es ideal porque:
   - El fix (rotar) es reversible (genera nuevas credenciales).
   - Es predecible (input claro, output claro).
   - El impacto de un falso positivo es bajo (apenas rotás credenciales que no necesitabas rotar).

2. **Diseñá el playbook como código.** EventBridge rule → Step Functions → Lambdas individuales por step. NO un mega-script.

3. **Cada step es reversible.** Si el step 3 falla, los steps 1 y 2 dejan el sistema en estado consistente (no a medio camino).

4. **Audit trail explícito.** Cada step del playbook escribe a CloudTrail/Audit DB. Si después el playbook actuó mal, podés reconstruir qué hizo.

5. **Dry-run mode.** Antes de poner el playbook en enforce, corrélo en modo "log only" por 2 semanas. Cada vez que el trigger se dispara, escribe lo que HARÍA, pero no lo hace. Vos validás manualmente que las decisiones del playbook son correctas.

6. **Stagger rollout.** Activá el playbook en sandbox primero, después dev, después staging, después prod. Si en algún paso falla, podés frenar antes de impactar prod.

7. **Métrica de salud.** El playbook reporta a un dashboard cuántas veces se ejecutó por semana. Si saltas de 2 a 200 ejecuciones de un día para otro, algo anda mal (puede ser un atacante intentando triggerar tu playbook como DoS).

**Ejemplo concreto:** Playbook "credencial filtrada en GitHub":

- Trigger: GitHub Push Protection alert via webhook → EventBridge.
- Step 1: Identificar qué credencial fue filtrada (parsear payload).
- Step 2: Rotar la credencial (call IAM API, generar nueva).
- Step 3: Actualizar Secrets Manager con la nueva credencial.
- Step 4: Invalidar la vieja con CreateAccessKey + DeleteAccessKey con grace period.
- Step 5: Notificar al developer que la filtró (Slack DM).
- Step 6: Crear ticket en Jira para retro.
- Step 7: Si la credencial vieja se intentó usar después del rotado, alertar como CRITICAL (alguien tiene la key vieja y la está probando).

Tiempo de implementación de este playbook: 1 a 2 sprints. Después de tenerlo funcionando, podés clonar la estructura para playbooks similares (S3 público accidental, etc.).

Ver implementación de ejemplo en [`../../playbooks/01-leaked-credentials.md`](../../playbooks/01-leaked-credentials.md).

## Próximo nivel

Cuando cumplas Nivel 3, andá a [`../nivel-4/SPEC.md`](../nivel-4/SPEC.md).

Allí dejamos de ser solo defensivos: red team interno, threat hunting proactivo, métricas en los OKRs del equipo. La seguridad pasa a ser una disciplina operada continuamente, no un departamento separado.
