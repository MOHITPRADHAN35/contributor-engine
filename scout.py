"""
Scout Module
Queries GitHub for open issues across target repositories, filters out assigned
or already-PR'd issues, and calculates a solvability heuristic score.
"""

import json
import re
import subprocess
from typing import Any, Dict, List, Optional


def run_gh_command(cmd: List[str]) -> Optional[Any]:
    """Execute a GitHub CLI command and parse JSON output safely."""
    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=True,
        )
        return json.loads(proc.stdout)
    except Exception:
        return None


def calculate_solvability_score(body: str, labels: List[str]) -> int:
    """Compute a 0-100 score indicating how well-defined and solvable the issue is."""
    score = 30  # Baseline

    if not body:
        return 10

    # Mentions code blocks
    if "```" in body:
        score += 20

    # Mentions file paths or line numbers (e.g. .py, .yaml, .ts)
    if re.search(r"[\w\-/]+\.(py|ts|tsx|json|yaml|yml|md)\b", body):
        score += 20

    # Mentions an exception or error log
    if re.search(r"(Error|Exception|Traceback|failed|AssertionError)", body, re.IGNORECASE):
        score += 15

    # Mentions a clear proposed fix or reproduction
    if re.search(r"(proposed fix|repro|reproduce|expected behavior|workaround)", body, re.IGNORECASE):
        score += 15

    # Label bonuses
    lower_labels = [l.lower() for l in labels]
    if "good first issue" in lower_labels:
        score += 10
    if "help wanted" in lower_labels:
        score += 5

    return min(score, 100)


def check_existing_pr(repo: str, issue_number: int) -> bool:
    """Check if an open Pull Request already references this issue."""
    prs = run_gh_command([
        "gh", "pr", "list",
        "--repo", repo,
        "--state", "open",
        "--search", str(issue_number),
        "--json", "number,title"
    ])
    return bool(prs and len(prs) > 0)


def scan_repository(repo: str, labels: List[str], limit_per_label: int = 5) -> List[Dict[str, Any]]:
    """Scan a single repository for actionable, unassigned, un-PR'd issues."""
    candidates = []
    seen_urls = set()

    for label in labels:
        cmd = [
            "gh", "issue", "list",
            "--repo", repo,
            "--state", "open",
            "--label", label,
            "--limit", str(limit_per_label),
            "--json", "number,title,url,body,labels,createdAt,assignees,comments"
        ]
        issues = run_gh_command(cmd) or []
        for iss in issues:
            url = iss.get("url")
            if not url or url in seen_urls:
                continue

            # Skip assigned issues
            if iss.get("assignees"):
                continue

            # Check for existing PR
            iss_num = iss.get("number")
            if check_existing_pr(repo, iss_num):
                continue

            raw_labels = [l.get("name") for l in iss.get("labels", []) if isinstance(l, dict)]
            body = iss.get("body", "") or ""
            score = calculate_solvability_score(body, raw_labels)

            seen_urls.add(url)
            candidates.append({
                "repo": repo,
                "number": iss_num,
                "title": iss.get("title", ""),
                "url": url,
                "body": body,
                "labels": raw_labels,
                "created_at": iss.get("createdAt", "")[:10],
                "num_comments": len(iss.get("comments", [])),
                "score": score,
            })

    return sorted(candidates, key=lambda x: x["score"], reverse=True)
