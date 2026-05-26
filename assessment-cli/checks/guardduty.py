"""Check: GuardDuty habilitado en todas las regions activas."""
from .base import Check


class GuardDutyCheck(Check):
    name = "guardduty"
    level = 1
    description = "Verifica GuardDuty habilitado en regions activas"

    def run(self, session, regions):
        enabled_regions = []
        disabled_regions = []
        suspended_regions = []
        errors = []

        for region in regions:
            try:
                gd = session.client("guardduty", region_name=region)
                detectors = gd.list_detectors().get("DetectorIds", [])
                if not detectors:
                    disabled_regions.append(region)
                    continue

                for detector_id in detectors:
                    detector = gd.get_detector(DetectorId=detector_id)
                    status = detector.get("Status", "UNKNOWN")
                    if status == "ENABLED":
                        enabled_regions.append(region)
                    else:
                        suspended_regions.append(f"{region}({status})")

            except Exception as e:
                errors.append(f"{region}: {e}")

        if disabled_regions or suspended_regions:
            issues_summary = []
            if disabled_regions:
                issues_summary.append(f"DISABLED en: {', '.join(disabled_regions)}")
            if suspended_regions:
                issues_summary.append(f"SUSPENDED en: {', '.join(suspended_regions)}")

            remediation_lines = [
                f"aws guardduty create-detector --enable --region {r}"
                for r in disabled_regions
            ]

            return self.failed(
                "; ".join(issues_summary),
                remediation="\n".join(remediation_lines),
                evidence={
                    "enabled_in": enabled_regions,
                    "disabled_in": disabled_regions,
                    "suspended_in": suspended_regions,
                },
                severity="critical",
            )

        if errors:
            return self.warned(
                f"GuardDuty habilitado en {len(enabled_regions)} regions, errores en otras: {'; '.join(errors)}",
            )

        return self.passed(
            f"GuardDuty habilitado en {len(enabled_regions)} region(s)",
            evidence={"enabled_regions": enabled_regions},
            severity="critical",
        )
