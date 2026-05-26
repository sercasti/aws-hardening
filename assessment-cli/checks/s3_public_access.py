"""Check: S3 block public access a nivel cuenta y bucket-by-bucket."""
from .base import Check


class S3PublicAccessCheck(Check):
    name = "s3_public_access"
    level = 1
    description = "Verifica block public access global y por bucket"

    def run(self, session, regions):
        s3control = session.client("s3control")
        s3 = session.client("s3")

        # Account-level
        try:
            sts = session.client("sts")
            account_id = sts.get_caller_identity()["Account"]
            account_block = s3control.get_public_access_block(AccountId=account_id)
            block_config = account_block.get("PublicAccessBlockConfiguration", {})
            all_blocked = all([
                block_config.get("BlockPublicAcls"),
                block_config.get("IgnorePublicAcls"),
                block_config.get("BlockPublicPolicy"),
                block_config.get("RestrictPublicBuckets"),
            ])
        except s3control.exceptions.NoSuchPublicAccessBlockConfiguration:
            all_blocked = False
        except Exception as e:
            return self.warned(f"No pude verificar account-level block: {e}")

        # Bucket-level
        try:
            buckets = s3.list_buckets().get("Buckets", [])
            buckets_missing_block = []
            public_buckets = []

            for bucket in buckets:
                bucket_name = bucket["Name"]
                try:
                    pab = s3.get_public_access_block(Bucket=bucket_name)
                    pab_config = pab.get("PublicAccessBlockConfiguration", {})
                    bucket_blocked = all([
                        pab_config.get("BlockPublicAcls"),
                        pab_config.get("IgnorePublicAcls"),
                        pab_config.get("BlockPublicPolicy"),
                        pab_config.get("RestrictPublicBuckets"),
                    ])
                    if not bucket_blocked:
                        buckets_missing_block.append(bucket_name)
                except s3.exceptions.ClientError as e:
                    if "NoSuchPublicAccessBlockConfiguration" in str(e):
                        buckets_missing_block.append(bucket_name)
                except Exception:
                    pass

                # Check policy status
                try:
                    status = s3.get_bucket_policy_status(Bucket=bucket_name)
                    if status.get("PolicyStatus", {}).get("IsPublic"):
                        public_buckets.append(bucket_name)
                except Exception:
                    pass

        except Exception as e:
            return self.warned(f"No pude listar buckets: {e}")

        # Resolve
        if not all_blocked or public_buckets:
            issues = []
            if not all_blocked:
                issues.append("account-level block NO totalmente activo")
            if public_buckets:
                issues.append(f"buckets publicos: {len(public_buckets)} ({', '.join(public_buckets[:3])}{'...' if len(public_buckets) > 3 else ''})")

            return self.failed(
                "; ".join(issues),
                remediation=(
                    f"aws s3control put-public-access-block "
                    f"--account-id {account_id} "
                    f"--public-access-block-configuration "
                    f"BlockPublicAcls=true,IgnorePublicAcls=true,"
                    f"BlockPublicPolicy=true,RestrictPublicBuckets=true"
                ),
                severity="critical",
                evidence={
                    "account_all_blocked": all_blocked,
                    "public_buckets": public_buckets,
                    "buckets_missing_block": buckets_missing_block,
                },
            )

        if buckets_missing_block:
            return self.warned(
                f"Account-level OK pero {len(buckets_missing_block)} bucket(s) sin block individual",
                remediation="Aplicar block_public_access en cada bucket. Defense in depth.",
                severity="medium",
                evidence={"buckets_missing": buckets_missing_block[:10]},
            )

        return self.passed(
            f"Block public access activo a nivel cuenta y en {len(buckets)} bucket(s)",
            severity="critical",
        )
