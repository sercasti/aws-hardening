"""Check: IAM Access Analyzer habilitado."""
from .base import Check


class AccessAnalyzerCheck(Check):
    name = "access_analyzer"
    level = 1
    description = "Verifica IAM Access Analyzer activo"

    def run(self, session, regions):
        analyzers_found = []
        active_findings_total = 0

        for region in regions:
            try:
                aa = session.client("accessanalyzer", region_name=region)
                analyzers = aa.list_analyzers().get("analyzers", [])
                for a in analyzers:
                    if a.get("status") == "ACTIVE":
                        analyzers_found.append({
                            "region": region,
                            "name": a["name"],
                            "type": a["type"],
                        })
                        # contar findings activos
                        try:
                            findings_response = aa.list_findings(
                                analyzerArn=a["arn"],
                                filter={"status": {"eq": ["ACTIVE"]}},
                            )
                            active_findings_total += len(findings_response.get("findings", []))
                        except Exception:
                            pass
            except Exception:
                continue

        if not analyzers_found:
            return self.failed(
                "IAM Access Analyzer NO habilitado",
                remediation=(
                    "aws accessanalyzer create-analyzer "
                    "--analyzer-name org-analyzer "
                    "--type ORGANIZATION"
                ),
                severity="high",
            )

        msg = f"Access Analyzer activo ({len(analyzers_found)} analyzers)"
        if active_findings_total > 0:
            msg += f", {active_findings_total} findings activos"

        if active_findings_total > 5:
            return self.warned(
                msg + ". Revisar findings",
                remediation="Ir a IAM Access Analyzer en la consola y revisar cada finding",
                severity="medium",
                evidence={"analyzers": analyzers_found, "active_findings": active_findings_total},
            )

        return self.passed(
            msg,
            evidence={"analyzers": analyzers_found},
            severity="high",
        )
