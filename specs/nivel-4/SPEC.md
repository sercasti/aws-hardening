# Spec — Nivel 4: La Ciudadela

> Tiempo de implementación: 1 a 3 trimestres. Costo recurrente: alto (decenas a cientos de miles USD/año si hay red team interno). Boss fight: red team y blue team reales corriendo en cadencia con métricas que llegan al board.

## Visión

En Nivel 4 la seguridad deja de ser un departamento y se vuelve una disciplina operada por toda la organización. Threat modeling antes de cada feature, red/blue team exercises mensuales, threat hunting proactivo, métricas de seguridad en los OKRs del equipo. Ciudadela = "fortaleza con su propio ejército dentro". No estamos solo defendiendo, estamos practicando la defensa.

## Principios

1. **Practicamos los ataques que nos pueden venir, antes de que vengan.** No por paranoia, por preparación.
2. **El red team busca, el blue team responde, el purple team mide el delta.** Y la org aprende del delta.
3. **Threat modeling es obligatorio para cualquier feature que toca data sensible.** No es opcional, no es solo para "los productos críticos".
4. **Métricas viven en el dashboard del board, no en una carpeta de Confluence.** Si el CEO no ve el número, no importa.
5. **La seguridad es responsabilidad de cada equipo, no del equipo de seguridad.** El equipo de seguridad lidera, capacita, audita; no ejecuta por todos los demás.

## Controles obligatorios

### Practice

#### PRA.1: Red team interno o externo recurrente

- **Estado deseado:** Equipo dedicado (interno) o contratista (externo) que corre exercises de penetration testing al menos trimestralmente.
- **Scope:** Cuentas AWS de producción, aplicaciones críticas, supply chain (dependencias de terceros).
- **Verificación:** Reports trimestrales + tickets de remediation.
- **Severidad si falla:** high (no es Nivel 4 sin esto)

#### PRA.2: Blue team con runbooks practicados

- **Estado deseado:** Equipo (puede ser el mismo SRE/SecOps) que entrena la respuesta a los ataques del red team.
- **Verificación:** Post-mortems de cada exercise + métricas de detección (¿qué fue detectado en cuánto tiempo?).
- **Severidad si falla:** high

#### PRA.3: Purple team exercises mensuales

- **Estado deseado:** Reunión mensual entre red y blue: red explica el ataque, blue explica cómo lo detectó (o no), juntos identifican gaps en detección.
- **Verificación:** Calendar + meeting notes + tickets de mejoras.
- **Severidad si falla:** medium

#### PRA.4: Threat hunting proactivo trimestral

- **Estado deseado:** Alguien (puede ser blue team) dedica 1 semana por trimestre a buscar comportamiento anómalo que las alertas no detectaron.
- **Verificación:** Reportes de threat hunts + findings.
- **Severidad si falla:** medium

### Process

#### PRO.3: Threat modeling integrado en design reviews

- **Estado deseado:** Cualquier feature/system que maneja data sensible (PII, financial data, credentials) tiene threat model documentado antes de ir a producción.
- **Framework:** STRIDE o variante. PASTA si la org es grande.
- **Verificación:** PRs de design docs incluyen sección "Threat Model".
- **Severidad si falla:** high

#### PRO.4: Security champions program

- **Estado deseado:** Cada equipo de producto tiene al menos un "security champion" capacitado, que sirve de puente con el security team.
- **Verificación:** Lista de champions, sesiones de training mensuales.
- **Severidad si falla:** medium

#### PRO.5: Incident response retrospective discipline

- **Estado deseado:** Cada incident (sev1, sev2) tiene retro documentado dentro de 1 semana, con action items asignados y trackeados.
- **Verificación:** Repo de retros + tickets de action items con due dates.
- **Severidad si falla:** high

### Metrics

#### MET.1: Security metrics en OKRs del equipo

- **Estado deseado:** El equipo de seguridad tiene OKRs medibles, comunicados al board.
- **Ejemplos de métricas:**
  - MTTD: tiempo medio de detección de incidents críticos. Target: <10 min.
  - MTTR: tiempo medio de respuesta a incidents críticos. Target: <1 hora.
  - Coverage: % de assets críticos cubiertos por monitoring. Target: 100%.
  - Drift: % de cuentas que pasan todos los controles de Nivel 1-3. Target: >95%.
  - Patch lag: días desde release de patch crítico hasta deploy. Target: <7 días.
- **Verificación:** OKR doc del equipo, reportado mensualmente al board.
- **Severidad si falla:** high

#### MET.2: Security cost as % of total infrastructure cost

- **Estado deseado:** Medido, reportado, justificado al CFO.
- **Verificación:** Dashboard mensual.
- **Por qué importa:** Cuando llegue el momento de pedir presupuesto para más seguridad, vas a necesitar datos.

### Maturity

#### MAT.1: Continuous compliance against multiple frameworks

- **Estado deseado:** Mapping de los controles del SPEC contra frameworks externos (SOC 2, ISO 27001, PCI DSS, frameworks locales).
- **Verificación:** Matrix de mapping documentada + audits internos.
- **Severidad si falla:** medium

#### MAT.2: Security architecture review board

- **Estado deseado:** Comité que revisa cambios arquitectónicos significativos antes de implementar (nuevos servicios, nuevas regiones, integraciones con terceros).
- **Verificación:** Calendar + ADRs (Architecture Decision Records) firmados.
- **Severidad si falla:** medium

#### MAT.3: Vendor security assessments

- **Estado deseado:** Cada vendor externo que tiene acceso a data sensible pasa por un assessment antes de integrarse.
- **Verificación:** Checklist + cuestionario firmado por el vendor + due diligence.
- **Severidad si falla:** high

## Anti-patterns

- ❌ Red team que solo reporta findings pero nunca se cierran
- ❌ Threat modeling como "checkbox" sin reviewers entrenados
- ❌ Métricas que el board nunca lee
- ❌ Security champions que nunca fueron capacitados (solo título)
- ❌ Post-mortems sin action items asignados
- ❌ Game days que se cancelan
- ❌ "Estamos en Nivel 4" sin haber tenido NINGÚN incident en los últimos 12 meses (señal de falta de visibilidad, no de seguridad perfecta)

## Métricas de éxito

Estás en Nivel 4 cuando:

- Tu MTTD para critical findings está por debajo de 10 minutos.
- Tu MTTR para critical findings está por debajo de 1 hora.
- Tu red team corrió al menos 4 exercises en los últimos 12 meses.
- Tu blue team detectó al menos 50% de los exercises del red team antes del debrief.
- Las métricas de seguridad están en el dashboard del board.
- Tenés security champions en >80% de los equipos de producto.

## Boss fight: red team y blue team reales

**El problema:** Montar capacidades reales de red team y blue team requiere inversión sostenida (gente especializada cuesta caro, herramientas cuestan caro, programas de entrenamiento cuestan caro).

**El método:**

### Opción A: Red team interno

- 2 a 4 personas dedicadas, perfil senior, conocimiento de AWS profundo.
- Salario competitivo: USD 150k+/año cada uno (varía por región).
- Toolset: Pacu, Stratus Red Team, Atomic Red Team, custom tooling.
- Training continuo: SANS courses, OffSec certs, BlackHat.
- Beneficios: contexto continuo, ataques específicos a tu organización.
- Costo total estimado: USD 700k a 1.5M/año (gente + tools + training).

### Opción B: Red team externo (más común)

- Contratás un servicio profesional (Bishop Fox, NCC Group, GuidePoint, otros).
- Engagement típico: 2 a 4 semanas, 1 a 2 veces por año.
- Costo: USD 50k a 200k por engagement.
- Beneficios: perspective externa, sin sesgos internos, profesionales especializados.
- Limitación: no tienen el contexto continuo de tu org.

### Opción C: Híbrido

- 1 persona interna como red team lead.
- Contratás externos para deep dives específicos.
- Equilibrio entre conocimiento interno y perspectiva fresca.

**El blue team:** No necesariamente requiere headcount nuevo. El SRE/SecOps team existente, capacitado adecuadamente, puede ser blue team. Lo que sí requiere es:

- Tiempo protegido (no se pueden hacer game days entre incident responses).
- Tooling de detección actualizado (Security Hub + SIEM + Detective).
- Permission para "pause" en exercises para profundizar en gaps.

**El purple team:** No es un team aparte. Es una reunión mensual entre red y blue. Quien la facilita es un security engineer senior que sintetiza los gaps.

### Reportar al board

Una vez que tenés el programa funcionando, el reporte al board debe contener:

1. **Health.** Estamos haciendo los exercises planeados.
2. **Findings.** Qué encontró el red team, qué se cerró, qué queda abierto.
3. **Improvements.** Qué cambió en infrastructure/process gracias a los exercises.
4. **Risk.** Qué riesgo aceptamos explícitamente (compromise we made).

**El reporte trimestral no es opcional.** Sin él, el board no entiende por qué la inversión en seguridad vale. Y sin la inversión, no hay Nivel 4.

## Y después?

No hay Nivel 5 oficial. Pero hay industrias con regulaciones específicas (bancos, salud, defensa) donde Nivel 4 es solo el baseline. Para esos casos, la siguiente frontera es:

- Cumplir frameworks específicos (FedRAMP High, FFIEC, HIPAA, PCI DSS Level 1).
- Tener auditorías externas continuas.
- Operar en data centers con compliance específica.

Pero ese es un viaje en sí mismo, fuera del scope del AWS Security Maturity Model genérico.
