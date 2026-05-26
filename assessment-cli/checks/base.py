"""Base check class for security maturity assessment."""
from dataclasses import dataclass, field
from typing import Optional


class Check:
    """Base class for all security checks.

    Subclasses must set:
    - name: short snake_case identifier
    - level: 1, 2, 3, or 4 (maturity model level)
    - description: one-line description

    And must implement:
    - run(session, regions) -> dict with status, message, severity, etc.
    """
    name: str = "base"
    level: int = 1
    description: str = "Base check"

    def run(self, session, regions):
        raise NotImplementedError

    @staticmethod
    def passed(message, evidence=None, severity="low"):
        return {
            "status": "pass",
            "message": message,
            "severity": severity,
            "remediation": None,
            "evidence": evidence or {},
        }

    @staticmethod
    def failed(message, remediation=None, evidence=None, severity="high"):
        return {
            "status": "fail",
            "message": message,
            "severity": severity,
            "remediation": remediation,
            "evidence": evidence or {},
        }

    @staticmethod
    def warned(message, remediation=None, evidence=None, severity="medium"):
        return {
            "status": "warn",
            "message": message,
            "severity": severity,
            "remediation": remediation,
            "evidence": evidence or {},
        }
