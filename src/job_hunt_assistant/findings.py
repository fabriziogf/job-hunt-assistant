"""Shared findings model — chapter-cited issues any skill can emit.

Several skills (Resume linter, Cover Letter linter, and later Networking /
Negotiation) report rule violations the same way: a list of issues, each tagged
with a severity and the playbook chapter it comes from. That shared shape lives
here so it isn't reinvented per skill.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Severity(str, Enum):
    """How much a finding matters.

    - ERROR: something the playbook says actively gets you rejected.
    - WARNING: a rule violation worth fixing before sending.
    - INFO: an observation or opportunity.
    """

    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class Finding(BaseModel):
    """A single issue, traceable back to a playbook chapter."""

    code: str
    severity: Severity
    message: str
    chapter: int
    where: str | None = None  # human-readable location


class FindingsReport(BaseModel):
    """A set of findings with convenience accessors."""

    findings: list[Finding] = Field(default_factory=list)

    @property
    def errors(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.ERROR]

    @property
    def warnings(self) -> list[Finding]:
        return [f for f in self.findings if f.severity is Severity.WARNING]

    @property
    def has_errors(self) -> bool:
        return bool(self.errors)

    def by_code(self, code: str) -> list[Finding]:
        return [f for f in self.findings if f.code == code]
