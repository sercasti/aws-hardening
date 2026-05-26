"""Check: EC2 instances usando IMDSv2."""
from .base import Check


class IMDSv2Check(Check):
    name = "imdsv2"
    level = 2
    description = "Verifica que EC2 instances usen IMDSv2 (no v1)"

    def run(self, session, regions):
        instances_using_v1 = []
        instances_using_v2 = 0
        instances_optional = []
        total = 0

        for region in regions:
            try:
                ec2 = session.client("ec2", region_name=region)
                paginator = ec2.get_paginator("describe_instances")
                for page in paginator.paginate(Filters=[{"Name": "instance-state-name", "Values": ["running", "stopped"]}]):
                    for reservation in page.get("Reservations", []):
                        for instance in reservation.get("Instances", []):
                            total += 1
                            metadata_options = instance.get("MetadataOptions", {})
                            http_tokens = metadata_options.get("HttpTokens")
                            if http_tokens == "required":
                                instances_using_v2 += 1
                            elif http_tokens == "optional":
                                instances_optional.append({
                                    "region": region,
                                    "instance_id": instance["InstanceId"],
                                    "type": instance.get("InstanceType"),
                                })
                            else:
                                instances_using_v1.append({
                                    "region": region,
                                    "instance_id": instance["InstanceId"],
                                    "type": instance.get("InstanceType"),
                                })
            except Exception:
                continue

        if total == 0:
            return self.passed("No hay EC2 instances en las regions escaneadas", severity="low")

        all_v1_or_optional = instances_using_v1 + instances_optional
        if all_v1_or_optional:
            return self.failed(
                f"{len(all_v1_or_optional)}/{total} instances con IMDSv2 NO obligatorio (vulnerable a SSRF)",
                remediation=(
                    "Para cada instance:\n"
                    "aws ec2 modify-instance-metadata-options "
                    "--instance-id [ID] --http-tokens required "
                    "--http-put-response-hop-limit 2 --region [REGION]"
                ),
                severity="high",
                evidence={
                    "v1_required": instances_using_v1[:5],
                    "optional": instances_optional[:5],
                },
            )

        return self.passed(
            f"Las {total} instances usan IMDSv2 obligatorio",
            severity="high",
        )
