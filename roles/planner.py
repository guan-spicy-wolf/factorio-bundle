"""Planner role: analyzes tasks and spawns child jobs.

Per ADR-0015:
- Entry role for external triggers
- Analyzes task goal and spawns appropriate child roles
- No git workspace needed (analysis only)
- Uses spawn tool to create implementer/evaluator/optimizer child jobs
"""
from __future__ import annotations

from palimpsest.config import WorkspaceConfig
from palimpsest.runtime.roles import JobSpec, context_spec, role


def planner_preparation(**kwargs) -> WorkspaceConfig:
    """Planner doesn't need a git workspace.

    Returns:
        WorkspaceConfig with empty repo (analysis only)
    """
    return WorkspaceConfig(repo="", new_branch=False)


def planner_publication(**kwargs) -> tuple[None, list]:
    """Planner doesn't produce git commits.

    Output is the spawn decisions in summary field.

    Returns:
        (None, []) - no git ref, no artifact bindings
    """
    return None, []


planner_publication.__publication_strategy__ = "skip"


@role(
    name="planner",
    description="Factorio bundle planner (analyzes tasks and spawns child roles)",
    role_type="planner",  # No hallucination gate (no git changes expected)
    min_cost=0.1,
    recommended_cost=0.3,
    max_cost=0.5,
)
def planner(**params) -> JobSpec:
    """Factorio planner role definition.

    Per MVP architecture:
    - Receives external trigger goal
    - Analyzes task requirements
    - Uses spawn tool to create child jobs:
      - implementer: for code changes
      - evaluator: for review/evaluation
      - optimizer: for tool evolution
    - Monitors child job results

    Expected role_params:
        goal: The task description from external trigger
        bundle: Bundle name (factorio)
        budget: Time budget for planning
    """
    return JobSpec(
        preparation_fn=planner_preparation,
        context_fn=context_spec(
            system="factorio/prompts/planner.md",
            sections=[],  # Planner doesn't need script listing
        ),
        publication_fn=planner_publication,
        tools=["spawn"],  # Spawn tool for child job creation
    )