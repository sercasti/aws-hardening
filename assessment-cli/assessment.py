#!/usr/bin/env python3
"""
AWS Security Maturity Model assessment CLI.

Escanea una cuenta AWS y emite reporte estructurado del nivel de madurez.
Pensado para correr en menos de 5 minutos y dar un baseline accionable.
"""
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

import boto3
import click
from rich.console import Console
from rich.table import Table

from checks.access_analyzer import AccessAnalyzerCheck
from checks.budgets import BudgetsCheck
from checks.cloudtrail import CloudTrailCheck
from checks.cost_anomaly import CostAnomalyCheck
from checks.guardduty import GuardDutyCheck
from checks.identity_center import IdentityCenterCheck
from checks.imdsv2 import IMDSv2Check
from checks.kms_rotation import KMSRotationCheck
from checks.mfa_root import MFARootCheck
from checks.s3_public_access import S3PublicAccessCheck
from checks.scps import SCPsCheck
from checks.security_hub import SecurityHubCheck
from checks.vpc_flow_logs import VPCFlowLogsCheck

CHECKS = [
    MFARootCheck(),
    CloudTrailCheck(),
    GuardDutyCheck(),
    IdentityCenterCheck(),
    AccessAnalyzerCheck(),
    CostAnomalyCheck(),
    BudgetsCheck(),
    S3PublicAccessCheck(),
    SCPsCheck(),
    KMSRotationCheck(),
    VPCFlowLogsCheck(),
    IMDSv2Check(),
    SecurityHubCheck(),
]

console = Console()


def run_all_checks(session, regions, level_filter=None, check_filter=None):
    """Run all registered checks against the session, return list of results."""
    results = []
    for check in CHECKS:
        if level_filter and check.level != level_filter:
            continue
        if check_filter and check.name not in check_filter:
            continue
        try:
            console.print(f"[dim]Running {check.name}...[/dim]")
            result = check.run(session, regions)
            result["check"] = check.name
            result["level"] = check.level
            result["description"] = check.description
            results.append(result)
        except Exception as e:
            results.append({
                "check": check.name,
                "level": check.level,
                "description": check.description,
                "status": "error",
                "message": f"Check crashed: {e}",
                "severity": "unknown",
                "remediation": None,
                "evidence": {},
            })
    return results


def compute_summary(results):
    """Compute maturity score and per-level completion."""
    by_level = {1: [], 2: [], 3: [], 4: []}
    for r in results:
        by_level[r["level"]].append(r)

    summary = {
        "total": len(results),
        "pass": sum(1 for r in results if r["status"] == "pass"),
        "fail": sum(1 for r in results if r["status"] == "fail"),
        "warn": sum(1 for r in results if r["status"] == "warn"),
        "error": sum(1 for r in results if r["status"] == "error"),
    }

    level_completion = {}
    for level, checks in by_level.items():
        if not checks:
            level_completion[level] = None
            continue
        passes = sum(1 for r in checks if r["status"] == "pass")
        level_completion[level] = round(passes / len(checks), 2)

    valid_levels = [v for v in level_completion.values() if v is not None]
    if valid_levels:
        maturity_score = round(sum(valid_levels) * 4 / len(valid_levels), 1)
    else:
        maturity_score = 0.0

    summary["maturity_score"] = maturity_score
    summary["level_1_completion"] = level_completion.get(1)
    summary["level_2_completion"] = level_completion.get(2)
    summary["level_3_completion"] = level_completion.get(3)
    summary["level_4_completion"] = level_completion.get(4)

    return summary


def prioritize_actions(results):
    """Rank failed/warned checks by impact + ease."""
    failed = [r for r in results if r["status"] in ("fail", "warn")]
    severity_order = {"critical": 0, "high": 1, "medium": 2, "low": 3, "unknown": 4}
    failed.sort(key=lambda r: (severity_order.get(r.get("severity", "unknown"), 4), r["level"]))
    actions = []
    for rank, r in enumerate(failed[:20], start=1):
        actions.append({
            "rank": rank,
            "check": r["check"],
            "level": r["level"],
            "severity": r.get("severity"),
            "action": r.get("remediation", r.get("message")),
        })
    return actions


def render_markdown(metadata, results, summary, actions):
    """Generate human-friendly markdown report."""
    out = []
    out.append("# AWS Security Assessment Report")
    out.append("")
    out.append(f"- **Account ID:** {metadata['account_id']}")
    out.append(f"- **Timestamp:** {metadata['timestamp']}")
    out.append(f"- **Regions scanned:** {', '.join(metadata['regions_scanned'])}")
    out.append(f"- **Total checks:** {metadata['checks_run']}")
    out.append("")
    out.append(f"## Maturity Score: **{summary['maturity_score']} / 4**")
    out.append("")
    out.append("| Nivel | Completitud |")
    out.append("|---|---|")
    for i in range(1, 5):
        completion = summary.get(f"level_{i}_completion")
        completion_str = f"{int(completion*100)}%" if completion is not None else "N/A"
        out.append(f"| Nivel {i} | {completion_str} |")
    out.append("")

    for level in range(1, 5):
        level_results = [r for r in results if r["level"] == level]
        if not level_results:
            continue
        level_name = ["", "El Despertar", "Los Cimientos", "La Atalaya", "La Ciudadela"][level]
        out.append(f"## Nivel {level}: {level_name}")
        out.append("")
        out.append("| Status | Check | Mensaje |")
        out.append("|---|---|---|")
        for r in level_results:
            status_icon = {"pass": "PASS", "fail": "FAIL", "warn": "WARN", "error": "ERR"}[r["status"]]
            out.append(f"| {status_icon} | `{r['check']}` | {r['message']} |")
        out.append("")

    out.append("## Action items prioritizados")
    out.append("")
    for a in actions:
        out.append(f"{a['rank']}. **[Nivel {a['level']}]** `{a['check']}`: {a['action']}")
    out.append("")
    return "\n".join(out)


def render_terminal(results, summary):
    """Render to terminal with rich tables."""
    for level in range(1, 5):
        level_results = [r for r in results if r["level"] == level]
        if not level_results:
            continue
        level_name = ["", "El Despertar", "Los Cimientos", "La Atalaya", "La Ciudadela"][level]
        table = Table(title=f"Nivel {level}: {level_name}")
        table.add_column("Status", style="bold")
        table.add_column("Check")
        table.add_column("Message", overflow="fold")
        for r in level_results:
            color = {"pass": "green", "fail": "red", "warn": "yellow", "error": "magenta"}[r["status"]]
            status = f"[{color}]{r['status'].upper()}[/{color}]"
            table.add_row(status, r["check"], r["message"])
        console.print(table)
        console.print()
    console.print(f"\n[bold]Maturity Score: {summary['maturity_score']} / 4[/bold]\n")


@click.command()
@click.option("--regions", default="us-east-1,sa-east-1", help="Comma-separated regions to scan.")
@click.option("--level", type=int, default=None, help="Run only checks for this level (1-4).")
@click.option("--checks", default=None, help="Comma-separated check names to run.")
@click.option("--output", default=None, help="File to write output.")
@click.option("--format", "output_format", type=click.Choice(["markdown", "json", "terminal"]),
              default="terminal")
@click.option("--profile", default=None, help="AWS profile to use.")
def main(regions, level, checks, output, output_format, profile):
    """Run AWS security maturity assessment."""
    region_list = [r.strip() for r in regions.split(",")]
    check_list = [c.strip() for c in checks.split(",")] if checks else None

    if profile:
        session = boto3.Session(profile_name=profile)
    else:
        session = boto3.Session()

    try:
        sts = session.client("sts")
        identity = sts.get_caller_identity()
        account_id = identity["Account"]
    except Exception as e:
        console.print(f"[red]No pude obtener identidad AWS: {e}[/red]")
        sys.exit(1)

    metadata = {
        "account_id": account_id,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "regions_scanned": region_list,
    }

    console.print(f"[bold]Starting assessment for account {account_id}[/bold]\n")
    results = run_all_checks(session, region_list, level_filter=level, check_filter=check_list)
    summary = compute_summary(results)
    actions = prioritize_actions(results)
    metadata["checks_run"] = len(results)

    final = {
        "metadata": metadata,
        "results": results,
        "summary": summary,
        "prioritized_actions": actions,
    }

    if output_format == "terminal":
        render_terminal(results, summary)
    elif output_format == "markdown":
        content = render_markdown(metadata, results, summary, actions)
        if output:
            Path(output).write_text(content)
            console.print(f"[green]Reporte escrito en {output}[/green]")
        else:
            print(content)
    elif output_format == "json":
        content = json.dumps(final, indent=2, default=str)
        if output:
            Path(output).write_text(content)
            console.print(f"[green]JSON escrito en {output}[/green]")
        else:
            print(content)


if __name__ == "__main__":
    main()
