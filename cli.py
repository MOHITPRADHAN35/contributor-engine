"""
CLI Interface for the Open Source Contributor Engine.
Provides commands for scanning, inspecting, sandboxing, and creating PRs.
"""

import argparse
import sys
from pathlib import Path
from typing import List, Optional

import yaml
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from .sandbox import SandboxManager
from .scout import scan_repository

console = Console()


def load_config() -> dict:
    config_path = Path(__file__).parent / "config.yaml"
    if config_path.exists():
        with open(config_path, "r", encoding="utf-8") as f:
            return yaml.safe_load(f) or {}
    return {}


def cmd_scan(args, config: dict):
    """Scan repositories for actionable contribution opportunities."""
    target_repos = [args.repo] if args.repo else [r["name"] for r in config.get("repositories", [])]
    labels = config.get("target_labels", ["good first issue", "help wanted", "bug"])
    min_score = args.min_score

    console.print(Panel(f"[bold cyan]Scanning {len(target_repos)} target repositories for unassigned, un-PR'd issues...[/bold cyan]"))

    all_candidates = []
    with console.status("[bold green]Querying GitHub CLI...[/bold green]"):
        for repo in target_repos:
            candidates = scan_repository(repo, labels, limit_per_label=args.limit)
            all_candidates.extend(candidates)

    filtered = [c for c in all_candidates if c["score"] >= min_score]
    filtered.sort(key=lambda x: x["score"], reverse=True)

    if not filtered:
        console.print("[yellow]No issues found meeting the score threshold. Try lowering --min-score.[/yellow]")
        return

    table = Table(title="[bold magenta]Top Open Source Contribution Candidates[/bold magenta]", show_header=True, header_style="bold cyan")
    table.add_column("Score", style="bold yellow", justify="center", width=7)
    table.add_column("Repo", style="bold green", width=24)
    table.add_column("#", style="cyan", justify="right", width=6)
    table.add_column("Title", style="white", min_width=35)
    table.add_column("Labels", style="dim", width=22)
    table.add_column("Created", style="dim", width=12)

    for item in filtered[:args.top]:
        labels_str = ", ".join(item["labels"][:2])
        table.add_row(
            f"{item['score']}/100",
            item["repo"],
            str(item["number"]),
            item["title"][:50] + ("..." if len(item["title"]) > 50 else ""),
            labels_str,
            item["created_at"],
        )

    console.print(table)
    console.print(f"\n[bold green]Found {len(filtered)} opportunities.[/bold green] Use [cyan]python -m tools.contributor_engine view <repo> <number>[/cyan] to inspect details.")


def cmd_view(args):
    """Inspect full issue details and check target files."""
    import subprocess
    import json

    cmd = ["gh", "issue", "view", str(args.number), "--repo", args.repo, "--json", "number,title,body,labels,createdAt,url"]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
    if proc.returncode != 0 or not proc.stdout:
        console.print(f"[red]Failed to fetch issue: {proc.stderr}[/red]")
        return

    data = json.loads(proc.stdout)
    title = data.get("title", "")
    body = data.get("body", "")
    url = data.get("url", "")
    labels = [l.get("name") for l in data.get("labels", [])]

    console.print(Panel(f"[bold cyan]#{args.number}: {title}[/bold cyan]\n[dim]{url}[/dim]\nLabels: {', '.join(labels)}"))
    console.print("\n[bold]Description:[/bold]")
    console.print(body[:2000] + ("\n... [truncated]" if len(body) > 2000 else ""))


def cmd_prepare(args, config: dict):
    """Fork repo, create sandbox, and check out branch."""
    manager = SandboxManager(
        base_dir=config.get("sandbox_dir", ".sandboxes"),
        user_handle=config.get("user_handle", "MOHITPRADHAN35"),
    )
    branch = args.branch or f"fix/issue-{args.number}"
    console.print(f"[cyan]Forking & preparing sandbox for {args.repo} on branch {branch}...[/cyan]")
    ok, path, msg = manager.clone_sandbox(args.repo, branch_name=branch)
    if ok:
        console.print(f"[bold green]✔ {msg}[/bold green]")
        template = manager.find_pr_template(args.repo)
        if template:
            console.print("[dim]PR Template found in repository.[/dim]")
    else:
        console.print(f"[bold red]✘ {msg}[/bold red]")


def cmd_diff(args, config: dict):
    """Show git diff in the sandbox."""
    manager = SandboxManager(
        base_dir=config.get("sandbox_dir", ".sandboxes"),
        user_handle=config.get("user_handle", "MOHITPRADHAN35"),
    )
    diff = manager.get_diff(args.repo)
    if not diff:
        console.print("[yellow]No changes detected in sandbox.[/yellow]")
    else:
        console.print(Panel(diff, title=f"Git Diff: {args.repo}"))


def cmd_submit(args, config: dict):
    """Commit changes and open a Pull Request."""
    manager = SandboxManager(
        base_dir=config.get("sandbox_dir", ".sandboxes"),
        user_handle=config.get("user_handle", "MOHITPRADHAN35"),
    )
    branch = args.branch
    console.print(f"[cyan]Committing and pushing branch '{branch}'...[/cyan]")
    push_ok, push_msg = manager.commit_and_push(args.repo, branch, args.title)
    if not push_ok and "Nothing to commit" not in push_msg:
        console.print(f"[bold red]✘ {push_msg}[/bold red]")
        return

    console.print(f"[cyan]Creating Pull Request on {args.repo}...[/cyan]")
    pr_ok, pr_msg = manager.create_pull_request(
        args.repo,
        branch,
        args.title,
        args.body,
        base_branch=args.base,
        dry_run=args.dry_run,
    )
    if pr_ok:
        console.print(f"[bold green]✔ Pull Request Created successfully![/bold green]\n{pr_msg}")
    else:
        console.print(f"[bold red]✘ PR creation failed: {pr_msg}[/bold red]")


def cmd_clean(args, config: dict):
    """Clean up sandboxes."""
    manager = SandboxManager(
        base_dir=config.get("sandbox_dir", ".sandboxes"),
        user_handle=config.get("user_handle", "MOHITPRADHAN35"),
    )
    manager.clean_sandbox(args.repo)
    console.print(f"[green]Cleaned sandbox(es) successfully.[/green]")


def main():
    config = load_config()
    parser = argparse.ArgumentParser(description="Autonomous Open Source Contributor Engine")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # Scan command
    scan_p = subparsers.add_parser("scan", help="Scan repos for solvable contribution candidates")
    scan_p.add_argument("--repo", type=str, help="Specific repo to scan (e.g. qdrant/fastembed)")
    scan_p.add_argument("--limit", type=int, default=5, help="Issues to fetch per label")
    scan_p.add_argument("--top", type=int, default=15, help="Number of results to display")
    scan_p.add_argument("--min-score", type=int, default=40, help="Minimum solvability score (0-100)")

    # View command
    view_p = subparsers.add_parser("view", help="View full issue description")
    view_p.add_argument("repo", type=str, help="Repository name (e.g. qdrant/fastembed)")
    view_p.add_argument("number", type=int, help="Issue number")

    # Prepare command
    prep_p = subparsers.add_parser("prepare", help="Fork and sandbox a repo for an issue")
    prep_p.add_argument("repo", type=str, help="Repository name")
    prep_p.add_argument("number", type=int, help="Issue number")
    prep_p.add_argument("--branch", type=str, help="Custom branch name")

    # Diff command
    diff_p = subparsers.add_parser("diff", help="View current git diff in sandbox")
    diff_p.add_argument("repo", type=str, help="Repository name")

    # Submit command
    sub_p = subparsers.add_parser("submit", help="Commit, push and open a Pull Request")
    sub_p.add_argument("repo", type=str, help="Repository name")
    sub_p.add_argument("--branch", type=str, required=True, help="Git branch name")
    sub_p.add_argument("--title", type=str, required=True, help="PR Title")
    sub_p.add_argument("--body", type=str, required=True, help="PR Description / Body")
    sub_p.add_argument("--base", type=str, default="main", help="Base branch (default: main)")
    sub_p.add_argument("--dry-run", action="store_true", help="Dry run PR creation")

    # Clean command
    clean_p = subparsers.add_parser("clean", help="Clean sandbox directories")
    clean_p.add_argument("--repo", type=str, help="Clean specific repo sandbox")

    args = parser.parse_args()

    if args.command == "scan":
        cmd_scan(args, config)
    elif args.command == "view":
        cmd_view(args)
    elif args.command == "prepare":
        cmd_prepare(args, config)
    elif args.command == "diff":
        cmd_diff(args, config)
    elif args.command == "submit":
        cmd_submit(args, config)
    elif args.command == "clean":
        cmd_clean(args, config)


if __name__ == "__main__":
    main()
