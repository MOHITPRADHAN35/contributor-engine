"""
Sandbox Module
Manages isolated git environments: forking, cloning, branch creation,
running tests, and PR submission via the GitHub CLI.
"""

import os
import re
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Tuple


class SandboxManager:
    def __init__(self, base_dir: str = ".sandboxes", user_handle: str = "MOHITPRADHAN35"):
        self.base_dir = Path(base_dir).resolve()
        self.user_handle = user_handle
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _repo_folder_name(self, repo: str) -> str:
        return repo.replace("/", "_")

    def get_sandbox_path(self, repo: str) -> Path:
        return self.base_dir / self._repo_folder_name(repo)

    def fork_repository(self, repo: str) -> Tuple[bool, str]:
        """Fork repository to user account if not already forked."""
        cmd = ["gh", "repo", "fork", repo, "--clone=false"]
        proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        if proc.returncode == 0:
            return True, f"Fork verified: https://github.com/{self.user_handle}/{repo.split('/')[-1]}"
        return False, proc.stderr.strip()

    def clone_sandbox(self, repo: str, branch_name: Optional[str] = None) -> Tuple[bool, Path, str]:
        """Clone fork into an isolated sandbox folder with depth 1."""
        target_path = self.get_sandbox_path(repo)
        repo_name = repo.split("/")[-1]
        fork_url = f"https://github.com/{self.user_handle}/{repo_name}.git"

        if not target_path.exists():
            self.fork_repository(repo)
            cmd = ["git", "clone", "--depth", "1", fork_url, str(target_path)]
            proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
            if proc.returncode != 0:
                return False, target_path, f"Git clone failed: {proc.stderr.strip()}"

        # If branch specified, create and switch to it
        if branch_name:
            cmd = ["git", "checkout", "-b", branch_name]
            subprocess.run(cmd, cwd=str(target_path), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)

        return True, target_path, f"Sandbox ready at {target_path}"

    def get_diff(self, repo: str) -> str:
        """Get git diff from the sandbox repo."""
        target_path = self.get_sandbox_path(repo)
        if not target_path.exists():
            return "Sandbox does not exist."
        proc = subprocess.run(["git", "diff"], cwd=str(target_path), capture_output=True, text=True, encoding="utf-8", errors="replace")
        return proc.stdout.strip()

    def find_pr_template(self, repo: str) -> Optional[str]:
        """Find and read PR template if present."""
        target_path = self.get_sandbox_path(repo)
        for pattern in [
            ".github/pull_request_template.md",
            ".github/PULL_REQUEST_TEMPLATE.md",
            "pull_request_template.md",
        ]:
            tpl_path = target_path / pattern
            if tpl_path.exists():
                try:
                    return tpl_path.read_text(encoding="utf-8", errors="replace")
                except Exception:
                    pass
        return None

    def commit_and_push(self, repo: str, branch: str, message: str) -> Tuple[bool, str]:
        """Stage, commit, and push changes to user fork."""
        target_path = self.get_sandbox_path(repo)
        if not target_path.exists():
            return False, "Sandbox does not exist."

        subprocess.run(["git", "add", "."], cwd=str(target_path), capture_output=True, check=False)
        commit_res = subprocess.run(
            ["git", "commit", "-m", message],
            cwd=str(target_path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if commit_res.returncode != 0 and "nothing to commit" in commit_res.stdout:
            return False, "Nothing to commit. No changes detected."

        push_res = subprocess.run(
            ["git", "push", "-u", "origin", branch],
            cwd=str(target_path),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
        if push_res.returncode != 0:
            return False, f"Push failed: {push_res.stderr.strip()}"

        return True, f"Successfully pushed {branch} to {self.user_handle}/{repo.split('/')[-1]}"

    def create_pull_request(
        self,
        repo: str,
        branch: str,
        title: str,
        body: str,
        base_branch: str = "main",
        dry_run: bool = False,
    ) -> Tuple[bool, str]:
        """Create a Pull Request against the upstream repository."""
        target_path = self.get_sandbox_path(repo)
        cmd = [
            "gh", "pr", "create",
            "--repo", repo,
            "--head", f"{self.user_handle}:{branch}",
            "--base", base_branch,
            "--title", title,
            "--body", body,
        ]
        if dry_run:
            cmd.append("--dry-run")

        proc = subprocess.run(cmd, cwd=str(target_path), capture_output=True, text=True, encoding="utf-8", errors="replace", check=False)
        if proc.returncode == 0:
            return True, proc.stdout.strip()
        return False, proc.stderr.strip()

    def clean_sandbox(self, repo: Optional[str] = None):
        """Remove one or all sandbox directories."""
        if repo:
            target_path = self.get_sandbox_path(repo)
            if target_path.exists():
                shutil.rmtree(target_path, ignore_errors=True)
        else:
            if self.base_dir.exists():
                shutil.rmtree(self.base_dir, ignore_errors=True)
                self.base_dir.mkdir(parents=True, exist_ok=True)
