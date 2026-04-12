"""Tool repetition analyzer for Factorio bundle.

Per ADR-0017: Bundle-provided analyzer reads events from pasloe and returns
observation data. Trenni loads and calls this analyzer, emits observation events.

This analyzer reads agent.tool.exec events for a job and detects repetitive
tool call patterns.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import logging

logger = logging.getLogger(__name__)


@dataclass
class RepetitionFinding:
    """Finding from pattern detection: repetitive tool usage."""
    tool_name: str
    call_count: int
    arg_pattern: str
    similarity: float


def analyze(job_events: list[dict]) -> list[dict]:
    """Analyze tool call patterns from job events.
    
    Args:
        job_events: List of events for this job (from pasloe query)
            - agent.tool.exec: {tool_name, arguments_preview, job_id}
            - agent.job.completed: {summary, status}
    
    Returns:
        List of observation data dicts (will be emitted as observation.* events)
    """
    # Extract tool.exec events
    tool_execs = [
        evt for evt in job_events
        if evt.get("type") == "agent.tool.exec"
    ]
    
    if not tool_execs:
        return []
    
    # Group by tool_name, count calls
    tool_counts: dict[str, int] = {}
    tool_args: dict[str, list[str]] = {}
    
    for evt in tool_execs:
        tool_name = evt.get("data", {}).get("tool_name", "")
        args_preview = evt.get("data", {}).get("arguments_preview", "")
        if tool_name:
            tool_counts[tool_name] = tool_counts.get(tool_name, 0) + 1
            tool_args.setdefault(tool_name, []).append(args_preview)
    
    # For dispatcher tools (factorio_call_script), extract script name from args
    findings = []
    for tool_name, count in tool_counts.items():
        if count < 5:
            continue  # Threshold: 5+ calls
        
        # For factorio_call_script, extract script name from args
        arg_pattern = ""
        similarity = 0.0
        
        if tool_name == "factorio_call_script":
            # Extract script name from arguments_preview
            script_names = []
            for args in tool_args.get(tool_name, []):
                # Parse args_preview to find script name
                # Format: {'name': 'actions.spawn', ...} or name="actions.spawn"
                try:
                    # Try JSON-like parse
                    if args.startswith("{"):
                        parsed = json.loads(args.replace("'", '"'))
                        script_names.append(parsed.get("name", ""))
                    else:
                        # Try to extract from string
                        import re
                        match = re.search(r'name["\']?\s*[:=]\s*["\']([^"\']+)["\']', args)
                        if match:
                            script_names.append(match.group(1))
                except Exception:
                    pass
            
            # Use most common script name as arg_pattern
            if script_names:
                from collections import Counter
                most_common = Counter(script_names).most_common(1)
                if most_common:
                    arg_pattern = most_common[0][0]
                    # Similarity: ratio of calls using this script
                    similarity = most_common[0][1] / count
        else:
            # Generic tool: use tool_name as pattern
            arg_pattern = tool_name
            similarity = 1.0
        
        findings.append({
            "tool_name": f"{tool_name}({arg_pattern})" if arg_pattern else tool_name,
            "call_count": count,
            "arg_pattern": arg_pattern,
            "similarity": similarity,
        })
    
    return findings


# Analyzer metadata for Trenni discovery
ANALYZER_NAME = "tool_repetition"
ANALYZER_VERSION = "0.1.0"  # Will be replaced by bundle_sha at runtime