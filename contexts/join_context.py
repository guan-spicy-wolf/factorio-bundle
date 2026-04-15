"""Join context provider for continuation planners.

Per ADR-0006: Renders child task results for planner join mode.
Queries pasloe for events related to child_task_ids and formats them.

Usage in planner.py:
    context_fn=context_spec(
        system="prompts/planner-join.md",
        sections=[{"type": "join_context"}],
    )
"""
from __future__ import annotations

import json
import os
import urllib.request
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from yoitsu_contracts.config import EventStoreConfig, JobConfig


def join_context(
    *,
    job_config: JobConfig,
    eventstore: EventStoreConfig,
    **_,
) -> str:
    """Render join context with child task results.

    Args:
        job_config: JobConfig with join.child_task_ids
        eventstore: EventStoreConfig for querying pasloe

    Returns:
        Markdown-formatted join context with child task results.
    """
    join_cfg = job_config.join
    if not join_cfg or not join_cfg.child_task_ids:
        return ""

    # Query pasloe for child task events
    base_url = eventstore.url or os.environ.get("PASLOE_URL", "http://127.0.0.1:8000")
    api_key_env = eventstore.api_key_env or "PASLOE_API_KEY"
    api_key = os.environ.get(api_key_env, "")

    results = _fetch_child_results(base_url, api_key, join_cfg.child_task_ids)

    if not results:
        return "## Child Tasks\nNo child task results available."

    parts = ["## Child Tasks\n\n"]

    for task_id, result in results.items():
        status = result.get("status", "unknown")
        status_icon = "✓" if status == "completed" else "✗" if status == "failed" else "~"
        role = result.get("role", "unknown")
        summary = result.get("summary", "")

        parts.append(f"### {task_id} `{role}` {status_icon} {status}\n")
        if summary:
            # Truncate long summaries
            summary_text = str(summary)[:800]
            if len(str(summary)) > 800:
                summary_text += "\n... (truncated)"
            parts.append(f"**Summary:**\n{summary_text}\n")

        # Include git_ref if available (for PR creation)
        git_ref = result.get("git_ref")
        if git_ref:
            parts.append(f"**Git ref:** `{git_ref}`\n")

        parts.append("\n")

    if join_cfg.parent_summary:
        parts.append("---\n\n")
        parts.append("## Original Goal\n\n")
        parts.append(join_cfg.parent_summary)

    return "".join(parts)


def _fetch_child_results(
    base_url: str,
    api_key: str,
    child_task_ids: list[str],
) -> dict[str, dict]:
    """Query pasloe for child task completion events.

    Returns dict mapping task_id to result dict with:
        - status: completed/failed/partial
        - role: role name
        - summary: result summary
        - git_ref: branch:sha if available
    """
    results: dict[str, dict] = {}

    headers = {}
    if api_key:
        headers["X-API-Key"] = api_key

    for task_id in child_task_ids:
        # Query for agent.job.completed and agent.job.failed events for this task
        # Use task_id as filter - the job_id pattern is parent-child format
        try:
            # First get completed events
            completed_url = f"{base_url}/events?limit=20&order=desc&type=agent.job.completed"
            req = urllib.request.Request(completed_url, headers=headers)
            with urllib.request.urlopen(req, timeout=10) as resp:
                completed_events = json.loads(resp.read().decode("utf-8"))

            # Find matching event by task_id in data
            for event in completed_events:
                data = event.get("data", {})
                job_id = data.get("job_id", "")
                # Match by task_id prefix in job_id (task_id format: parent/child_hash)
                if task_id in job_id or job_id.startswith(task_id.replace("/", "-")):
                    results[task_id] = {
                        "status": "completed",
                        "role": _extract_role(job_id),
                        "summary": data.get("summary", ""),
                        "git_ref": data.get("git_ref", ""),
                    }
                    break

            if task_id not in results:
                # Check for failed events
                failed_url = f"{base_url}/events?limit=20&order=desc&type=agent.job.failed"
                req = urllib.request.Request(failed_url, headers=headers)
                with urllib.request.urlopen(req, timeout=10) as resp:
                    failed_events = json.loads(resp.read().decode("utf-8"))

                for event in failed_events:
                    data = event.get("data", {})
                    job_id = data.get("job_id", "")
                    if task_id in job_id or job_id.startswith(task_id.replace("/", "-")):
                        results[task_id] = {
                            "status": "failed",
                            "role": _extract_role(job_id),
                            "summary": data.get("error", "") or data.get("summary", ""),
                        }
                        break

        except Exception as e:
            # Log error but don't fail the job
            results[task_id] = {
                "status": "unknown",
                "role": "unknown",
                "summary": f"Failed to fetch results: {e}",
            }

    return results


def _extract_role(job_id: str) -> str:
    """Extract role from job_id pattern.

    Job IDs follow patterns like:
    - 069dfabc-root-cxyz-evaluator
    - 069dfabc/eval-evaluator
    The last segment after the final '-' or '/' is typically the role.
    """
    # Handle both dash and slash separators
    segments = job_id.replace("/", "-").split("-")
    for seg in reversed(segments):
        if seg in ("evaluator", "implementer", "optimizer", "worker", "planner"):
            return seg
    return segments[-1] if segments else "unknown"