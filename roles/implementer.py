"""Implementer role: modifies bundle repo with git publication.

Per ADR-0015/ADR-0016:
- Uses git_workspace capability for commit + push
- Target workspace is the bundle repo ephemeral clone
- Hallucination gate enforced by git_workspace (no changes = failure)
- Artifact URI points to remote repo, not ephemeral workspace
"""
from __future__ import annotations

from palimpsest.runtime.roles import JobSpec, context_spec, role


@role(
    name="implementer",
    description="Factorio bundle implementer (modifies bundle repo with git publication)",
    needs=["git_workspace"],  # ADR-0016: capability for git commit + push
    role_type="worker",  # ADR-0016: hallucination gate = no changes = failure
    min_cost=0.1,
    recommended_cost=0.5,
    max_cost=2.0,
)
def implementer(**params) -> JobSpec:
    """Factorio Lua script implementer role definition.
    
    Per ADR-0015/ADR-0016:
    - git_workspace capability handles clone (setup) and commit+push (finalize)
    - Bash tool's cwd lands in target_workspace (bundle repo clone)
    - No explicit preparation_fn/publication_fn (capability handles it)
    - Hallucination gate: git diff --cached --quiet = no changes = failure
    - Serialization enforced by bundle scheduling (max_concurrent_jobs=1)
    
    The implementer creates/modifies Lua scripts in factorio/scripts/.
    Git workspace capability will:
      1. Clone bundle repo to ephemeral workspace (setup)
      2. After agent work: git add -A, commit, push (finalize)
      3. Emit artifact.published with URI pointing to remote repo
    """
    return JobSpec(
        context_fn=context_spec(
            system="factorio/prompts/implementer.md",
            sections=[{"type": "factorio_scripts"}],
        ),
        tools=["bash"],  # Only bash for file operations
        # No preparation_fn - capability setup handles workspace
        # No publication_fn - capability finalize handles git push
    )