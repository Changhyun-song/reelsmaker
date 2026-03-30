"""QA engine — orchestrates rule checks and collects issues.

Pure function: receives QAContext, returns list of QAIssue.
For future Claude-based critic, add a separate async critic function
and merge its results with the rule-based issues.
"""

from __future__ import annotations

from shared.qa.rules import RULE_REGISTRY, QAContext
from shared.schemas.qa import QAIssue


def run_all_checks(
    ctx: QAContext,
    only_checks: list[str] | None = None,
) -> list[QAIssue]:
    """Run all (or filtered) QA checks and return issues.

    Args:
        ctx: Pre-fetched project data for inspection.
        only_checks: Optional list of check names to run. None = all.

    Returns:
        List of QAIssue instances (not yet persisted).
    """
    issues: list[QAIssue] = []

    for name, check_fn in RULE_REGISTRY:
        if only_checks and name not in only_checks:
            continue
        try:
            result = check_fn(ctx)
            issues.extend(result)
        except Exception as exc:
            issues.append(QAIssue(
                scope="project",
                target_type="project",
                target_id=ctx.project_id,
                check_type=f"{name}_error",
                severity="warning",
                message=f"QA 규칙 '{name}' 실행 중 오류: {exc}",
                source="rule",
            ))

    return issues
