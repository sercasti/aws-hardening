"""Check: KMS CMKs con rotation habilitada."""
from .base import Check


class KMSRotationCheck(Check):
    name = "kms_rotation"
    level = 2
    description = "Verifica KMS rotation en CMKs customer-managed"

    def run(self, session, regions):
        keys_with_rotation = 0
        keys_without_rotation = []
        total_customer_keys = 0

        for region in regions:
            try:
                kms = session.client("kms", region_name=region)
                paginator = kms.get_paginator("list_keys")
                for page in paginator.paginate():
                    for key in page.get("Keys", []):
                        try:
                            metadata = kms.describe_key(KeyId=key["KeyId"])
                            key_meta = metadata.get("KeyMetadata", {})
                            if key_meta.get("KeyManager") != "CUSTOMER":
                                continue
                            if key_meta.get("KeyState") in ("PendingDeletion", "PendingImport"):
                                continue
                            total_customer_keys += 1
                            rotation = kms.get_key_rotation_status(KeyId=key["KeyId"])
                            if rotation.get("KeyRotationEnabled"):
                                keys_with_rotation += 1
                            else:
                                keys_without_rotation.append({
                                    "region": region,
                                    "key_id": key["KeyId"],
                                    "alias": key_meta.get("Description", "(no description)"),
                                })
                        except Exception:
                            continue
            except Exception:
                continue

        if total_customer_keys == 0:
            return self.passed(
                "No hay customer-managed CMKs (cuenta nueva o uso AWS-managed)",
                severity="low",
            )

        if keys_without_rotation:
            return self.failed(
                f"{len(keys_without_rotation)}/{total_customer_keys} keys sin rotation",
                remediation=(
                    "Para cada key:\n"
                    "aws kms enable-key-rotation --key-id [KEY_ID] --region [REGION]"
                ),
                severity="medium",
                evidence={"keys_without_rotation": keys_without_rotation[:5]},
            )

        return self.passed(
            f"Las {total_customer_keys} customer-managed keys tienen rotation",
            severity="medium",
        )
