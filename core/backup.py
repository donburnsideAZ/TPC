"""
GitHub backup for TPC v3.

One-way push to GitHub - your local project is the truth,
GitHub is just offsite backup for safety.

No pulling, no sync status, no merge conflicts.
Just: "Backup Now" → files go to GitHub.
"""

import subprocess
import sys
import os
from pathlib import Path
from dataclasses import dataclass
from typing import Optional, Callable
from datetime import datetime

from .github import (
    get_github_token,
    get_github_username,
    has_github_credentials,
    inject_credentials,
    normalize_github_url,
)


def _subprocess_args() -> dict:
    """Platform-specific subprocess args (hide console on Windows)."""
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x08000000
    return kwargs


@dataclass
class BackupResult:
    """Result of a backup operation."""
    success: bool
    message: str
    files_backed_up: int = 0
    
    @classmethod
    def error(cls, message: str) -> "BackupResult":
        return cls(success=False, message=message)
    
    @classmethod
    def ok(cls, message: str, files: int = 0) -> "BackupResult":
        return cls(success=True, message=message, files_backed_up=files)


def is_git_installed() -> bool:
    """Check if git is available."""
    try:
        result = subprocess.run(
            ["git", "--version"],
            capture_output=True,
            text=True,
            timeout=5,
            **_subprocess_args()
        )
        return result.returncode == 0
    except (subprocess.SubprocessError, FileNotFoundError, OSError):
        return False


def has_git_repo(project_path: Path) -> bool:
    """Check if the project has a git repository."""
    return (project_path / ".git").is_dir()


def init_git_repo(project_path: Path) -> tuple[bool, str]:
    """
    Initialize a git repository for the project.
    
    Creates .gitignore with sensible defaults.
    """
    if has_git_repo(project_path):
        return True, "Git repository already exists"
    
    try:
        # Initialize repo
        result = subprocess.run(
            ["git", "init"],
            cwd=project_path,
            capture_output=True,
            text=True,
            **_subprocess_args()
        )
        
        if result.returncode != 0:
            return False, f"Failed to initialize git: {result.stderr}"
        
        # Create .gitignore if it doesn't exist
        gitignore = project_path / ".gitignore"
        if not gitignore.exists():
            gitignore.write_text("""# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
venv/
.venv/
ENV/
env/

# TPC
.tpc/snapshots/

# Build outputs
dist/
build/
*.spec
TPC Builds/

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db

# Logs and databases
*.log
*.sqlite
*.db
""")
        
        return True, "Git repository initialized"
        
    except Exception as e:
        return False, f"Error: {e}"


def set_git_remote(project_path: Path, remote_url: str) -> tuple[bool, str]:
    """Set or update the origin remote URL."""
    if not has_git_repo(project_path):
        return False, "No git repository"
    
    try:
        # Check if origin exists
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project_path,
            capture_output=True,
            text=True,
            **_subprocess_args()
        )
        
        if result.returncode == 0:
            # Update existing
            subprocess.run(
                ["git", "remote", "set-url", "origin", remote_url],
                cwd=project_path,
                capture_output=True,
                **_subprocess_args()
            )
        else:
            # Add new
            subprocess.run(
                ["git", "remote", "add", "origin", remote_url],
                cwd=project_path,
                capture_output=True,
                **_subprocess_args()
            )
        
        return True, "Remote configured"
        
    except Exception as e:
        return False, f"Error: {e}"


def backup_to_github(
    project_path: Path,
    remote_url: str,
    message: Optional[str] = None,
    progress_callback: Optional[Callable[[str], None]] = None
) -> BackupResult:
    """
    Backup the project to GitHub.
    
    This is a one-way push:
    1. Initialize git if needed
    2. Stage all files
    3. Commit with timestamp
    4. Force push to remote
    
    Args:
        project_path: Path to the project folder
        remote_url: GitHub repository URL
        message: Optional commit message (auto-generated if not provided)
        progress_callback: Optional callback for progress updates
    
    Returns:
        BackupResult with success/failure info
    """
    def progress(msg: str):
        if progress_callback:
            progress_callback(msg)
    
    # Check prerequisites
    if not is_git_installed():
        return BackupResult.error(
            "Git is not installed.\n\n"
            "GitHub backup requires Git. Install it from:\n"
            "• Mac: Run 'xcode-select --install' in Terminal\n"
            "• Windows: Download from git-scm.com"
        )
    
    if not has_github_credentials():
        return BackupResult.error(
            "GitHub not connected.\n\n"
            "Go to Settings → GitHub to sign in first."
        )
    
    # Initialize git if needed
    progress("Preparing backup...")
    if not has_git_repo(project_path):
        success, msg = init_git_repo(project_path)
        if not success:
            return BackupResult.error(f"Couldn't initialize repository: {msg}")
    
    # Set remote
    clean_url = normalize_github_url(remote_url)
    success, msg = set_git_remote(project_path, clean_url)
    if not success:
        return BackupResult.error(f"Couldn't configure remote: {msg}")
    
    try:
        # Stage all files
        progress("Staging files...")
        result = subprocess.run(
            ["git", "add", "-A"],
            cwd=project_path,
            capture_output=True,
            text=True,
            **_subprocess_args()
        )
        
        if result.returncode != 0:
            return BackupResult.error(f"Couldn't stage files: {result.stderr}")
        
        # Check if there's anything to commit
        result = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=project_path,
            capture_output=True,
            text=True,
            **_subprocess_args()
        )
        
        files_changed = len([l for l in result.stdout.strip().split("\n") if l])
        
        if files_changed > 0:
            # Commit
            progress("Creating backup snapshot...")
            if not message:
                message = f"TPC Backup - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=project_path,
                capture_output=True,
                text=True,
                **_subprocess_args()
            )
            
            # Commit can "fail" if nothing to commit, that's ok
            if result.returncode != 0 and "nothing to commit" not in result.stdout.lower():
                return BackupResult.error(f"Couldn't create commit: {result.stderr}")
        
        # Get current branch name
        result = subprocess.run(
            ["git", "branch", "--show-current"],
            cwd=project_path,
            capture_output=True,
            text=True,
            **_subprocess_args()
        )
        
        branch = result.stdout.strip() or "main"
        
        # If branch is empty (fresh repo), create initial commit and set branch
        if not branch:
            branch = "main"
            subprocess.run(
                ["git", "checkout", "-b", "main"],
                cwd=project_path,
                capture_output=True,
                **_subprocess_args()
            )
        
        # Push with credentials
        progress("Uploading to GitHub...")
        
        username = get_github_username()
        token = get_github_token()
        
        # Use credential-embedded URL for push
        auth_url = inject_credentials(clean_url, username, token)
        
        # Push (force to handle any divergence - local is truth)
        result = subprocess.run(
            ["git", "push", "-u", "--force", auth_url, branch],
            cwd=project_path,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
            **_subprocess_args()
        )
        
        if result.returncode != 0:
            error = result.stderr.strip()
            
            if "not found" in error.lower() or "404" in error:
                return BackupResult.error(
                    "Repository not found.\n\n"
                    "Make sure the repository exists on GitHub and you have access."
                )
            elif "authentication" in error.lower() or "403" in error or "401" in error:
                return BackupResult.error(
                    "Authentication failed.\n\n"
                    "Check your GitHub token in Settings → GitHub."
                )
            elif "permission" in error.lower():
                return BackupResult.error(
                    "Permission denied.\n\n"
                    "Make sure your token has 'repo' permission."
                )
            else:
                return BackupResult.error(f"Push failed: {error}")
        
        return BackupResult.ok(
            f"Backed up successfully!",
            files=files_changed
        )
        
    except subprocess.TimeoutExpired:
        return BackupResult.error(
            "Backup timed out.\n\n"
            "Check your internet connection and try again."
        )
    except Exception as e:
        return BackupResult.error(f"Unexpected error: {e}")


def get_backup_status(project_path: Path, remote_url: str) -> dict:
    """
    Get basic backup status info.
    
    Returns dict with:
    - has_repo: bool
    - has_remote: bool
    - has_commits: bool
    - last_commit_date: Optional[datetime]
    """
    status = {
        "has_repo": False,
        "has_remote": False,
        "has_commits": False,
        "last_commit_date": None,
    }
    
    if not has_git_repo(project_path):
        return status
    
    status["has_repo"] = True
    
    try:
        # Check for remote
        result = subprocess.run(
            ["git", "remote", "get-url", "origin"],
            cwd=project_path,
            capture_output=True,
            text=True,
            **_subprocess_args()
        )
        status["has_remote"] = result.returncode == 0
        
        # Check for commits
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=project_path,
            capture_output=True,
            text=True,
            **_subprocess_args()
        )
        status["has_commits"] = result.returncode == 0
        
        if status["has_commits"]:
            # Get last commit date
            result = subprocess.run(
                ["git", "log", "-1", "--format=%aI"],
                cwd=project_path,
                capture_output=True,
                text=True,
                **_subprocess_args()
            )
            
            if result.returncode == 0 and result.stdout.strip():
                try:
                    date_str = result.stdout.strip()
                    # Handle timezone offset format
                    if "+" in date_str or date_str.endswith("Z"):
                        date_str = date_str.split("+")[0].replace("Z", "")
                    status["last_commit_date"] = datetime.fromisoformat(date_str)
                except:
                    pass
        
    except Exception:
        pass
    
    return status
