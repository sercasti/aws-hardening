"""Check: Cost Anomaly Detection configurado."""
from .base import Check


class CostAnomalyCheck(Check):
    name = "cost_anomaly"
    level = 1
    description = "Verifica Cost Anomaly Detection con monitores activos"

    def run(self, session, regions):
        ce = session.client("ce", region_name="us-east-1")
        try:
            response = ce.get_anomaly_monitors()
            monitors = response.get("AnomalyMonitors", [])

            if not monitors:
                return self.failed(
                    "No hay Cost Anomaly Monitors configurados",
                    remediation=(
                        "1. Cost Management Console → Cost Anomaly Detection\n"
                        "2. Create monitor → Type: AWS services\n"
                        "3. Configurar subscription con threshold (recomendado: $100)\n"
                        "4. Notify a email/slack del equipo"
                    ),
                    severity="high",
                )

            # Verificar que hay subscriptions
            subs_response = ce.get_anomaly_subscriptions()
            subscriptions = subs_response.get("AnomalySubscriptions", [])

            if not subscriptions:
                return self.warned(
                    f"{len(monitors)} monitor(s) sin subscriptions (alertas no llegan)",
                    remediation="Configurar al menos una subscription para recibir alertas",
                    severity="medium",
                    evidence={"monitors": len(monitors)},
                )

            return self.passed(
                f"Cost Anomaly: {len(monitors)} monitor(s), {len(subscriptions)} subscription(s)",
                evidence={
                    "monitors": len(monitors),
                    "subscriptions": len(subscriptions),
                },
                severity="medium",
            )

        except Exception as e:
            return self.warned(f"No pude verificar Cost Anomaly: {e}")
