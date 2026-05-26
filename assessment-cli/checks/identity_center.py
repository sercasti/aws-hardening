"""Check: Identity Center (SSO) configurado, IAM users minimizados."""
from .base import Check


class IdentityCenterCheck(Check):
    name = "identity_center"
    level = 1
    description = "Verifica Identity Center activo y IAM users minimizados"

    def run(self, session, regions):
        try:
            sso_admin = session.client("sso-admin")
            instances = sso_admin.list_instances().get("Instances", [])
            sso_enabled = len(instances) > 0
        except Exception:
            sso_enabled = False

        iam = session.client("iam")
        try:
            response = iam.list_users()
            users = response.get("Users", [])
            users_with_password = []
            users_with_keys = []

            for user in users:
                username = user["UserName"]
                try:
                    iam.get_login_profile(UserName=username)
                    users_with_password.append(username)
                except iam.exceptions.NoSuchEntityException:
                    pass

                keys = iam.list_access_keys(UserName=username).get("AccessKeyMetadata", [])
                active_keys = [k for k in keys if k.get("Status") == "Active"]
                if active_keys:
                    users_with_keys.append(username)

            total_iam_users = len(users)
            human_iam_users = set(users_with_password)
            programmatic_iam_users = set(users_with_keys) - human_iam_users

        except Exception as e:
            return self.warned(f"No pude listar IAM users: {e}")

        if not sso_enabled and total_iam_users > 0:
            return self.failed(
                f"No hay Identity Center y hay {total_iam_users} IAM users locales",
                remediation=(
                    "1. Habilitar Identity Center desde la consola\n"
                    "2. Configurar identity source (Active Directory, Okta, o local)\n"
                    "3. Migrar usuarios humanos a SSO\n"
                    "4. Despues de migracion, deshabilitar IAM users humanos"
                ),
                severity="high",
                evidence={
                    "iam_users_with_password": list(human_iam_users),
                    "iam_users_with_keys": list(programmatic_iam_users),
                },
            )

        if sso_enabled and human_iam_users:
            return self.warned(
                f"Identity Center activo, pero todavia hay {len(human_iam_users)} IAM users humanos",
                remediation="Migrar usuarios restantes a SSO y eliminar IAM users",
                severity="medium",
                evidence={"iam_users_remaining": list(human_iam_users)},
            )

        if sso_enabled:
            return self.passed(
                f"Identity Center activo. {len(programmatic_iam_users)} IAM users programaticos solamente",
                evidence={"programmatic_iam_users": list(programmatic_iam_users)},
                severity="high",
            )

        return self.passed(
            "No hay IAM users locales (cuenta nueva o ya migrada)",
            severity="high",
        )
