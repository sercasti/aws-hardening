"""Check: SCPs activos en Organization."""
from .base import Check


class SCPsCheck(Check):
    name = "scps"
    level = 2
    description = "Verifica SCPs activos cubriendo controles basicos"

    def run(self, session, regions):
        org = session.client("organizations")
        try:
            root_response = org.list_roots()
            roots = root_response.get("Roots", [])
            if not roots:
                return self.warned("Cuenta no esta en Organization o no es manager")
            root_id = roots[0]["Id"]
        except Exception as e:
            return self.warned(f"No estoy en una Organization o no tengo permisos: {e}")

        try:
            policies = org.list_policies(Filter="SERVICE_CONTROL_POLICY")
            scps = policies.get("Policies", [])

            # Excluir la FullAWSAccess default
            custom_scps = [p for p in scps if p["Name"] != "FullAWSAccess"]

            if not custom_scps:
                return self.failed(
                    "No hay SCPs custom configurados",
                    remediation=(
                        "Empezar con 2-3 SCPs basicos:\n"
                        "1. Deny disable CloudTrail (templates/scps/01-...)\n"
                        "2. Deny disable GuardDuty (templates/scps/02-...)\n"
                        "3. Deny region outside list (templates/scps/03-...)\n"
                        "Aplicar primero a OU de sandbox/dev, despues prod"
                    ),
                    severity="high",
                )

            # Verificar si los SCPs basicos comunes estan presentes
            basic_controls = {
                "cloudtrail": False,
                "guardduty": False,
                "region": False,
                "imdsv2": False,
                "root": False,
            }

            for scp in custom_scps:
                policy_detail = org.describe_policy(PolicyId=scp["Id"])
                content = policy_detail["Policy"]["Content"].lower()
                if "cloudtrail:stoplogging" in content or "cloudtrail:deletetrail" in content:
                    basic_controls["cloudtrail"] = True
                if "guardduty:deletedetector" in content or "guardduty:updatedetector" in content:
                    basic_controls["guardduty"] = True
                if "aws:requestedregion" in content:
                    basic_controls["region"] = True
                if "ec2:metadatahttptokens" in content:
                    basic_controls["imdsv2"] = True
                if "principalarn" in content and ":root" in content:
                    basic_controls["root"] = True

            missing_controls = [k for k, v in basic_controls.items() if not v]
            if missing_controls:
                return self.warned(
                    f"{len(custom_scps)} SCPs custom pero faltan controles: {', '.join(missing_controls)}",
                    remediation=f"Agregar SCPs para: {', '.join(missing_controls)}",
                    severity="medium",
                    evidence={"controls_covered": basic_controls},
                )

            return self.passed(
                f"{len(custom_scps)} SCPs custom con controles basicos cubiertos",
                evidence={"controls_covered": basic_controls},
                severity="high",
            )

        except Exception as e:
            return self.warned(f"Error verificando SCPs: {e}")
