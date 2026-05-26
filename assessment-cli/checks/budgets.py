"""Check: AWS Budgets con alerts configurados."""
from .base import Check


class BudgetsCheck(Check):
    name = "budgets"
    level = 1
    description = "Verifica AWS Budgets con notifications"

    def run(self, session, regions):
        try:
            sts = session.client("sts")
            account_id = sts.get_caller_identity()["Account"]
        except Exception as e:
            return self.warned(f"No pude obtener account ID: {e}")

        budgets = session.client("budgets", region_name="us-east-1")
        try:
            response = budgets.describe_budgets(AccountId=account_id)
            budgets_list = response.get("Budgets", [])

            if not budgets_list:
                return self.failed(
                    "No hay AWS Budgets configurados",
                    remediation=(
                        "1. AWS Budgets Console → Create budget\n"
                        "2. Type: Cost budget, monthly\n"
                        "3. Threshold: 80% del expected monthly\n"
                        "4. Notify: ops@yourcompany"
                    ),
                    severity="medium",
                )

            # Verificar si tienen notifications
            budgets_with_notifications = 0
            for budget in budgets_list:
                budget_name = budget["BudgetName"]
                try:
                    notifications = budgets.describe_notifications_for_budget(
                        AccountId=account_id,
                        BudgetName=budget_name,
                    ).get("Notifications", [])
                    if notifications:
                        budgets_with_notifications += 1
                except Exception:
                    pass

            if budgets_with_notifications < len(budgets_list):
                return self.warned(
                    f"{len(budgets_list)} budgets, solo {budgets_with_notifications} con notifications",
                    remediation="Agregar al menos una notification por budget",
                    severity="medium",
                )

            return self.passed(
                f"{len(budgets_list)} budget(s) con notifications",
                severity="medium",
            )

        except Exception as e:
            return self.warned(f"Error verificando budgets: {e}")
