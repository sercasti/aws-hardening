# Contributing

> Este repo es companion de un talk pero también es un proyecto vivo. Bienvenidos PRs, issues, y feedback.

## Tipos de contribución que ayudan

### 1. Nuevos prompts validados

Tenés un prompt que usás todos los días para tareas de seguridad AWS y que funciona bien? Mandalo en `prompts/`. Estructura:

- Frontmatter con rol, contexto, output esperado.
- Ejemplo de input y output real.
- Si tiene caveats, anotarlos.

### 2. Specs por industria o vertical

Los specs actuales son genéricos. Si tenés specs probados en una industria específica (healthcare, fintech, ecommerce), un fork del Nivel N con anotaciones es oro:

- `specs/nivel-2/healthcare-overlay.md`
- `specs/nivel-3/pci-overlay.md`

### 3. Playbooks adicionales

Tenés un playbook de IR para un caso que no está cubierto? Bienvenido. Casos que faltarían:

- AWS Lambda compromise.
- ECS/EKS pod compromise.
- Bedrock prompt injection abuse.
- AWS Org-level account takeover.

Seguí la estructura de los 8 playbooks existentes.

### 4. Checks adicionales en assessment-cli

Hay un control que tu org chequea regularmente y no está en la CLI? Agregalo:

1. Nuevo archivo en `assessment-cli/checks/`.
2. Heredá de `Check`.
3. Implementá `run(session, regions)`.
4. Registralo en `assessment.py`.
5. Tests si podés.

### 5. Demos en otras tools

Las demos actuales cubren Kiro, Claude Code, Cursor. Si usás otra (Aider, Continue.dev, Cline, etc.), un nuevo subfolder en `demos/` siguiendo el mismo patrón es bienvenido.

### 6. Traducciones

El repo está en español argentino con términos técnicos en inglés. Si querés un overlay en otro idioma (portugués brasileño, inglés, etc.) es bienvenido siempre que mantengas la estructura.

## Cómo contribuir

```bash
# Fork el repo
gh repo fork sercasti/aws-hardening

# Clone tu fork
git clone https://github.com/[your-user]/aws-hardening
cd aws-hardening

# Branch
git checkout -b feature/mi-contribucion

# Cambios

# Commit
git commit -m "feat(prompts): añadir prompt para audit de Secrets Manager"

# Push
git push -u origin feature/mi-contribucion

# PR
gh pr create
```

## Estilo de los textos

- **Voz directa**, instructiva. "Hacé X" no "se podría hacer X".
- **Español argentino** o español neutral. Usá "vos" si estás cómodo, "tú" si preferís.
- **Términos técnicos en inglés** sin traducir (SCP, baseline, IMDSv2). NO traducir "service control policy" como "política de control de servicio".
- **Sin em-dashes** (—). Usar comas, puntos, o dos puntos.
- **Sin frases huecas**. Evitá "es importante recordar que" o "como podemos ver". Decí la cosa directamente.

## Estilo de código

### Python (assessment-cli)

- Black formatter, default settings.
- Type hints donde ayudan.
- Docstrings cortos.

### JSON (SCPs, IAM policies)

- Indentación de 2 espacios.
- Statements ordenados por importancia.
- `Sid` descriptivo en cada Statement.

### Terraform

- Modules en `modules/`.
- Variables con descripción y validation.
- `terraform fmt` antes de commit.

### Bash

- Shebang siempre: `#!/usr/bin/env bash`.
- `set -euo pipefail` al inicio.
- Variables en `UPPER_CASE` si son constantes globales, `lower_case` si son locales.

## Review checklist

Antes de mergear un PR, validá:

- [ ] Sin em-dashes en el contenido (`—` o `–`).
- [ ] Sin información sensible (account IDs reales, ARNs reales, keys).
- [ ] Archivos JSON validan (`jq . file.json`).
- [ ] Archivos Python no tienen syntax errors (`python -m py_compile`).
- [ ] Links internos funcionan.
- [ ] El estilo coincide con archivos existentes.

## Cosas que NO contribuir

- ❌ **Tus credenciales AWS, account IDs reales, IPs reales.** Usá placeholders (`123456789012`, `[ACCOUNT_ID]`, `192.0.2.1`).
- ❌ **Templates comerciales con licencia restrictiva.** Si el contenido tiene licencia, mejor un link a la fuente.
- ❌ **Conclusiones genéricas o boilerplate.** "AWS security is important." Sí lo es. Pero no agrega valor.
- ❌ **Tools propietarias sin caveats.** Si una tool requiere subscripción, decir el costo aproximado.

## Roadmap

Las cosas que están en mi backlog (orden no estricto):

- [ ] Agregar 4 playbooks más (Lambda, EKS, Bedrock, account takeover).
- [ ] Multi-account scanning en assessment-cli (AssumeRole automático).
- [ ] Templates en CDK (TypeScript y Python) para los SCPs.
- [ ] Demo con Aider y Continue.dev.
- [ ] Overlay para fintech (PCI, Open Banking).
- [ ] Integration con Slack/Teams para notificaciones (templates).

## Licencia

MIT. Ver [LICENSE](LICENSE).

## Contacto

- Issues en GitHub.
- Twitter/X: [@sercasti](https://twitter.com/sercasti)
- LinkedIn: [Sergio Castiñeyras](https://linkedin.com/in/sergiocastineyras)

Si querés hablar del modelo, los patterns, o cómo aplicar esto en tu org, ping. Cuando hay tiempo, contesto.
