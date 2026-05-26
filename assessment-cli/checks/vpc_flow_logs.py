"""Check: VPC Flow Logs habilitados en todos los VPCs."""
from .base import Check


class VPCFlowLogsCheck(Check):
    name = "vpc_flow_logs"
    level = 2
    description = "Verifica VPC Flow Logs activos en todos los VPCs"

    def run(self, session, regions):
        vpcs_without_logs = []
        vpcs_with_logs = 0
        total_vpcs = 0

        for region in regions:
            try:
                ec2 = session.client("ec2", region_name=region)
                vpcs = ec2.describe_vpcs().get("Vpcs", [])
                flow_logs = ec2.describe_flow_logs().get("FlowLogs", [])
                vpcs_with_logs_set = {fl["ResourceId"] for fl in flow_logs
                                       if fl.get("ResourceId", "").startswith("vpc-")
                                       and fl.get("FlowLogStatus") == "ACTIVE"}

                for vpc in vpcs:
                    total_vpcs += 1
                    if vpc["VpcId"] in vpcs_with_logs_set:
                        vpcs_with_logs += 1
                    else:
                        vpcs_without_logs.append({
                            "region": region,
                            "vpc_id": vpc["VpcId"],
                            "cidr": vpc.get("CidrBlock"),
                        })
            except Exception:
                continue

        if total_vpcs == 0:
            return self.warned("No se encontraron VPCs en las regiones escaneadas")

        if vpcs_without_logs:
            return self.failed(
                f"{len(vpcs_without_logs)}/{total_vpcs} VPCs sin Flow Logs",
                remediation=(
                    "Para cada VPC:\n"
                    "aws ec2 create-flow-logs --resource-type VPC "
                    "--resource-ids [VPC_ID] --traffic-type ALL "
                    "--log-destination-type s3 "
                    "--log-destination arn:aws:s3:::[LOG_BUCKET]"
                ),
                severity="high",
                evidence={"vpcs_without_logs": vpcs_without_logs[:5]},
            )

        return self.passed(
            f"Todos los {total_vpcs} VPCs tienen Flow Logs activos",
            severity="high",
        )
