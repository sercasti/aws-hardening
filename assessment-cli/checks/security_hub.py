"""Check: Security Hub habilitado y standards activos."""
from .base import Check


class SecurityHubCheck(Check):
    name = "security_hub"
    level = 3
    description = "Verifica Security Hub habilitado con standards activos"

    def run(self, session, regions):
        regions_enabled = []
        regions_disabled = []
        standards_enabled_global = set()

        for region in regions:
            try:
                sh = session.client("securityhub", region_name=region)
                hub = sh.describe_hub()
                regions_enabled.append(region)

                try:
                    standards = sh.get_enabled_standards().get("StandardsSubscriptions", [])
                    for s in standards:
                        arn = s.get("StandardsArn", "")
                        if "aws-foundational" in arn:
                            standards_enabled_global.add("AWS Foundational")
                        elif "cis-aws-foundations" in arn:
                            standards_enabled_global.add("CIS Foundations")
                        elif "pci-dss" in arn:
                            standards_enabled_global.add("PCI DSS")
                        elif "nist-800-53" in arn:
                            standards_enabled_global.add("NIST 800-53")
                except Exception:
                    pass

            except sh.exceptions.InvalidAccessException:
                regions_disabled.append(region)
            except Exception:
                regions_disabled.append(region)

        if not regions_enabled:
            return self.failed(
                "Security Hub no habilitado en ninguna region",
                remediation=(
                    "Para cada region:\n"
                    "aws securityhub enable-security-hub --region [REGION]\n"
                    "Despues habilitar standards desde la consola"
                ),
                severity="high",
            )

        if regions_disabled:
            return self.warned(
                f"Security Hub activo en {len(regions_enabled)} region(s), faltan: {', '.join(regions_disabled)}",
                remediation=f"Habilitar en: {', '.join(regions_disabled)}",
                severity="medium",
                evidence={
                    "enabled_in": regions_enabled,
                    "standards": list(standards_enabled_global),
                },
            )

        if not standards_enabled_global:
            return self.warned(
                "Security Hub habilitado pero sin standards activos",
                remediation="Habilitar al menos AWS Foundational Security Best Practices",
                severity="medium",
            )

        return self.passed(
            f"Security Hub activo en {len(regions_enabled)} region(s) con {len(standards_enabled_global)} standard(s)",
            evidence={
                "regions": regions_enabled,
                "standards": list(standards_enabled_global),
            },
            severity="medium",
        )
