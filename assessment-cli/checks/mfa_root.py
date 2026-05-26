"""Check: MFA habilitado en usuario root."""
from .base import Check


class MFARootCheck(Check):
    name = "mfa_root"
    level = 1
    description = "Verifica que el usuario root tenga MFA habilitado"

    def run(self, session, regions):
        iam = session.client("iam")
        try:
            summary = iam.get_account_summary()
            mfa_devices = summary["SummaryMap"].get("AccountMFAEnabled", 0)

            if mfa_devices == 0:
                return self.failed(
                    "Root user NO tiene MFA habilitado",
                    remediation=(
                        "1. Login como root\n"
                        "2. IAM Console → Security credentials\n"
                        "3. Activar MFA. Idealmente hardware key (Yubikey)\n"
                        "4. Guardar el device en lugar fisico seguro"
                    ),
                    severity="critical",
                )

            # Verificar tipo: hardware o virtual
            try:
                root_creds = iam.get_account_authorization_details()
                # Esta API no devuelve detalle del tipo de MFA del root.
                # Para eso necesitas signin con root, no scrappable.
                return self.passed(
                    "Root user tiene MFA habilitado (tipo no determinable via API)",
                    severity="critical",
                )
            except Exception:
                return self.passed(
                    "Root user tiene MFA habilitado",
                    severity="critical",
                )

        except Exception as e:
            return self.warned(
                f"No pude verificar MFA del root: {e}",
                severity="critical",
            )
