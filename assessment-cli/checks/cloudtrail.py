"""Check: CloudTrail habilitado, multi-region, file integrity."""
from .base import Check


class CloudTrailCheck(Check):
    name = "cloudtrail"
    level = 1
    description = "Verifica CloudTrail multi-region con file integrity"

    def run(self, session, regions):
        ct = session.client("cloudtrail")
        try:
            response = ct.describe_trails(includeShadowTrails=False)
            trails = response.get("trailList", [])

            if not trails:
                return self.failed(
                    "No hay CloudTrail configurado",
                    remediation=(
                        "aws cloudtrail create-trail --name org-trail "
                        "--s3-bucket-name [BUCKET] --is-multi-region-trail "
                        "--enable-log-file-validation"
                    ),
                    severity="critical",
                )

            multi_region_trails = [t for t in trails if t.get("IsMultiRegionTrail")]
            if not multi_region_trails:
                return self.failed(
                    f"Hay {len(trails)} trail(s) pero ninguno es multi-region",
                    remediation="aws cloudtrail update-trail --name [TRAIL] --is-multi-region-trail",
                    severity="critical",
                    evidence={"trails": [t["Name"] for t in trails]},
                )

            # Verificar logging activo
            issues = []
            for trail in multi_region_trails:
                status = ct.get_trail_status(Name=trail["TrailARN"])
                if not status.get("IsLogging"):
                    issues.append(f"Trail {trail['Name']} no esta logueando")
                if not trail.get("LogFileValidationEnabled"):
                    issues.append(f"Trail {trail['Name']} no tiene file integrity")

            if issues:
                return self.warned(
                    "; ".join(issues),
                    remediation="Revisar trails y activar logging + file validation",
                    severity="high",
                )

            return self.passed(
                f"{len(multi_region_trails)} multi-region trail(s) activo(s) con file integrity",
                evidence={"trails": [t["Name"] for t in multi_region_trails]},
                severity="critical",
            )

        except Exception as e:
            return self.warned(f"Error verificando CloudTrail: {e}")
