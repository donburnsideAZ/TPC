"""
Project model for PTC.

A project is a Python codebase that PTC manages. Projects have:
- A location on disk (the project folder)
- A .ptc/ folder containing config and state
- An invisible git repo for version tracking
- Metadata about what we're building

The user never sees .ptc/ or .git/ - they just see their code.
"""

import json
import subprocess
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional


# Default location for new projects
DEFAULT_PROJECTS_ROOT = Path.home() / "Documents" / "PTC Projects"

# Registry for tracking projects outside the default location
PTC_CONFIG_DIR = Path.home() / ".ptc"
KNOWN_PROJECTS_FILE = PTC_CONFIG_DIR / "known_projects.json"


def get_known_project_paths() -> list[Path]:
    """Get list of project paths from the registry."""
    if not KNOWN_PROJECTS_FILE.exists():
        return []
    
    try:
        with open(KNOWN_PROJECTS_FILE) as f:
            data = json.load(f)
            return [Path(p) for p in data.get("projects", [])]
    except Exception:
        return []


def register_project_path(path: Path) -> None:
    """Add a project path to the registry (for projects outside default location)."""
    PTC_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    paths = get_known_project_paths()
    
    # Only add if not already registered and not in default location
    if path not in paths and not str(path).startswith(str(DEFAULT_PROJECTS_ROOT)):
        paths.append(path)
        
        with open(KNOWN_PROJECTS_FILE, "w") as f:
            json.dump({"projects": [str(p) for p in paths]}, f, indent=2)


def unregister_project_path(path: Path) -> None:
    """Remove a project path from the registry."""
    paths = get_known_project_paths()
    
    if path in paths:
        paths.remove(path)
        
        with open(KNOWN_PROJECTS_FILE, "w") as f:
            json.dump({"projects": [str(p) for p in paths]}, f, indent=2)


@dataclass
class Project:
    """Represents a PTC-managed project."""
    
    name: str
    path: Path
    main_file: str = "main.py"
    description: str = ""
    python_version: str = "3.11"
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    github_repo: Optional[str] = None
    
    # Runtime state (not persisted)
    _has_unsaved_changes: bool = field(default=False, repr=False)
    
    @property
    def ptc_dir(self) -> Path:
        """The hidden .ptc config directory."""
        return self.path / ".ptc"
    
    @property
    def config_file(self) -> Path:
        """The project.json config file."""
        return self.ptc_dir / "project.json"
    
    @property
    def main_file_path(self) -> Path:
        """Full path to the main Python file."""
        return self.path / self.main_file
    
    @property
    def has_unsaved_changes(self) -> bool:
        """Check if there are uncommitted changes."""
        if not (self.path / ".git").exists():
            return False
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.path,
                capture_output=True,
                text=True
            )
            return bool(result.stdout.strip())
        except Exception:
            return False
    
    def save_config(self) -> None:
        """Save project configuration to .ptc/project.json."""
        self.ptc_dir.mkdir(parents=True, exist_ok=True)
        
        # Load existing config to preserve handled_branches
        existing = {}
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    existing = json.load(f)
            except:
                pass
        
        # Only persist the config fields, not runtime state
        config = {
            "name": self.name,
            "main_file": self.main_file,
            "description": self.description,
            "python_version": self.python_version,
            "created": self.created,
            "github_repo": self.github_repo,
        }
        
        # Preserve handled_branches if it exists
        if "handled_branches" in existing:
            config["handled_branches"] = existing["handled_branches"]
        
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> "Project":
        """Load a project from a directory containing .ptc/project.json."""
        ptc_dir = path / ".ptc"
        config_file = ptc_dir / "project.json"
        
        if not config_file.exists():
            raise ValueError(f"No PTC project found at {path}")
        
        with open(config_file) as f:
            config = json.load(f)
        
        return cls(
            name=config["name"],
            path=path,
            main_file=config.get("main_file", "main.py"),
            description=config.get("description", ""),
            python_version=config.get("python_version", "3.11"),
            created=config.get("created", datetime.now().isoformat()),
            github_repo=config.get("github_repo"),
        )
    
    @classmethod
    def create_new(
        cls,
        name: str,
        location: Optional[Path] = None,
        description: str = "",
        main_file: str = "main.py",
    ) -> "Project":
        """
        Create a new project from scratch.
        
        Sets up:
        - Project folder structure
        - .ptc/ config directory
        - Git repo (silently)
        - Starter main.py if none exists
        """
        if location is None:
            location = DEFAULT_PROJECTS_ROOT
        
        project_path = location / name
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Create the project instance
        project = cls(
            name=name,
            path=project_path,
            main_file=main_file,
            description=description,
        )
        
        # Save config
        project.save_config()
        
        # Create starter main.py if it doesn't exist
        main_path = project_path / main_file
        if not main_path.exists():
            main_path.write_text(f'''#!/usr/bin/env python3
"""
{name}
{description if description else "A new project."}

Created with PTC - Pack Track Click
"""


def main():
    print("Hello from {name}!")


if __name__ == "__main__":
    main()
''')
        
        # Initialize git silently
        project._init_git()
        
        # Save first version
        project.save_version("Initial project setup")
        
        return project
    
    @classmethod
    def adopt(
        cls,
        source_file: Path,
        name: str,
        location: Optional[Path] = None,
        additional_files: Optional[list[Path]] = None,
        delete_original: bool = False,
    ) -> "Project":
        """
        Adopt an existing script into a proper PTC project.
        
        The rescue mission - take that Downloads folder script and
        give it a real home.
        """
        if location is None:
            location = DEFAULT_PROJECTS_ROOT
        
        project_path = location / name
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Copy the main file
        import shutil
        dest_file = project_path / source_file.name
        shutil.copy2(source_file, dest_file)
        
        # Copy any additional files
        if additional_files:
            for f in additional_files:
                if f.is_file():
                    shutil.copy2(f, project_path / f.name)
                elif f.is_dir():
                    shutil.copytree(f, project_path / f.name)
        
        # Create the project
        project = cls(
            name=name,
            path=project_path,
            main_file=source_file.name,
            description=f"Adopted from {source_file.parent.name}",
        )
        
        # Save config
        project.save_config()
        
        # Initialize git
        project._init_git()
        
        # Save first version
        project.save_version(f"Adopted from {source_file}")
        
        # Optionally clean up the original
        if delete_original:
            source_file.unlink()
            if additional_files:
                for f in additional_files:
                    if f.exists():
                        if f.is_file():
                            f.unlink()
                        else:
                            shutil.rmtree(f)
        
        return project
    
    @classmethod
    def import_existing(
        cls,
        folder: Path,
        name: str,
        main_file: str = "main.py",
        description: str = "",
    ) -> "Project":
        """
        Import an existing project folder into PTC management.
        
        Unlike adopt, this doesn't copy anything - it wraps the folder
        in-place. If the folder already has git history, we keep it.
        """
        if not folder.is_dir():
            raise ValueError(f"Not a directory: {folder}")
        
        # Check if already a PTC project
        if (folder / ".ptc" / "project.json").exists():
            raise ValueError("This folder is already a PTC project")
        
        # Create the project instance
        project = cls(
            name=name,
            path=folder,
            main_file=main_file,
            description=description or f"Imported from {folder.name}",
        )
        
        # Save config (creates .ptc/ folder)
        project.save_config()
        
        # Register this project so it shows up in the sidebar
        register_project_path(folder)
        
        # Initialize git only if it doesn't exist
        if not (folder / ".git").exists():
            project._init_git()
            project.save_version("Imported into PTC")
        else:
            # Git exists - just make sure .ptc is tracked
            # Stage just the .ptc folder if there are no other changes
            try:
                subprocess.run(
                    ["git", "add", ".ptc/"],
                    cwd=folder,
                    capture_output=True,
                    check=True
                )
                # Only commit if .ptc was actually added
                result = subprocess.run(
                    ["git", "status", "--porcelain", ".ptc/"],
                    cwd=folder,
                    capture_output=True,
                    text=True
                )
                if result.stdout.strip():
                    subprocess.run(
                        ["git", "commit", "-m", "Added PTC project config"],
                        cwd=folder,
                        capture_output=True,
                        check=True
                    )
            except Exception:
                pass  # Not fatal if this fails
        
        return project
    
    def _init_git(self) -> None:
        """Initialize a git repository silently."""
        git_dir = self.path / ".git"
        if git_dir.exists():
            return
        
        try:
            subprocess.run(
                ["git", "init"],
                cwd=self.path,
                capture_output=True,
                check=True
            )
            
            # Create a .gitignore
            gitignore = self.path / ".gitignore"
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

# PTC build outputs
dist/
build/
*.spec

# IDE
.idea/
.vscode/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
""")
        except Exception as e:
            # Git init failed - not fatal, just means no version control
            print(f"Warning: Could not initialize git: {e}")
    
    def save_version(self, message: Optional[str] = None) -> bool:
        """
        Save the current state as a version (git commit).
        
        Returns True if a version was saved, False if nothing to save.
        """
        if message is None:
            message = f"Saved at {datetime.now().strftime('%Y-%m-%d %H:%M')}"
        
        try:
            # Stage all changes
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.path,
                capture_output=True,
                check=True
            )
            
            # Check if there's anything to commit
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.path,
                capture_output=True,
                text=True
            )
            
            if not result.stdout.strip():
                return False  # Nothing to commit
            
            # Commit
            subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.path,
                capture_output=True,
                check=True
            )
            
            return True
            
        except Exception as e:
            print(f"Warning: Could not save version: {e}")
            return False
    
    def get_version_history(self) -> list[dict]:
        """Get the version history (git log) as a list of dicts."""
        try:
            result = subprocess.run(
                ["git", "log", "--pretty=format:%H|%s|%ai", "-n", "50"],
                cwd=self.path,
                capture_output=True,
                text=True,
                check=True
            )
            
            history = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("|", 2)
                    if len(parts) == 3:
                        history.append({
                            "hash": parts[0],
                            "message": parts[1],
                            "date": parts[2],
                        })
            
            return history
            
        except Exception:
            return []
    
    def launch(self) -> subprocess.Popen:
        """Launch the main Python file."""
        return subprocess.Popen(
            ["python3", self.main_file],
            cwd=self.path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
    
    # === GitHub Integration ===
    
    def has_remote(self) -> bool:
        """Check if this project has a GitHub remote configured."""
        if not (self.path / ".git").exists():
            return False
        
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.path,
                capture_output=True,
                text=True
            )
            return result.returncode == 0
        except Exception:
            return False
    
    def get_remote_url(self) -> Optional[str]:
        """Get the URL of the origin remote."""
        if not (self.path / ".git").exists():
            return None
        
        try:
            result = subprocess.run(
                ["git", "remote", "get-url", "origin"],
                cwd=self.path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip()
        except Exception:
            return None
    
    def set_remote(self, url: str) -> tuple[bool, str]:
        """
        Set or update the origin remote URL.
        
        Returns (success, message).
        """
        if not (self.path / ".git").exists():
            return False, "No git repository found"
        
        try:
            # Check if origin already exists
            if self.has_remote():
                # Update existing remote
                subprocess.run(
                    ["git", "remote", "set-url", "origin", url],
                    cwd=self.path,
                    capture_output=True,
                    check=True
                )
            else:
                # Add new remote
                subprocess.run(
                    ["git", "remote", "add", "origin", url],
                    cwd=self.path,
                    capture_output=True,
                    check=True
                )
            
            # Save to project config too
            self.github_repo = url
            self.save_config()
            
            return True, "Remote configured successfully"
            
        except subprocess.CalledProcessError as e:
            return False, f"Failed to set remote: {e.stderr}"
        except Exception as e:
            return False, f"Error: {e}"
    
    def get_sync_status(self) -> dict:
        """
        Get the sync status with the remote.
        
        Returns dict with:
        - connected: bool (has remote)
        - ahead: int (commits ahead of remote)
        - behind: int (commits behind remote)
        - status: str ('synced', 'ahead', 'behind', 'diverged', 'no_remote', 'error')
        """
        if not (self.path / ".git").exists():
            return {"connected": False, "ahead": 0, "behind": 0, "status": "no_remote"}
        
        if not self.has_remote():
            return {"connected": False, "ahead": 0, "behind": 0, "status": "no_remote"}
        
        try:
            # Fetch to get latest remote info (but don't merge)
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=self.path,
                capture_output=True,
                timeout=30  # Don't hang forever
            )
            
            # Get current branch
            current_branch = self.get_current_branch()
            if not current_branch:
                return {"connected": True, "ahead": 0, "behind": 0, "status": "error"}
            
            # Check if upstream is set
            result = subprocess.run(
                ["git", "rev-parse", "--abbrev-ref", f"{current_branch}@{{upstream}}"],
                cwd=self.path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                # No upstream set - we have commits but haven't pushed yet
                result = subprocess.run(
                    ["git", "rev-list", "--count", "HEAD"],
                    cwd=self.path,
                    capture_output=True,
                    text=True
                )
                local_commits = int(result.stdout.strip()) if result.returncode == 0 else 0
                return {"connected": True, "ahead": local_commits, "behind": 0, "status": "ahead" if local_commits > 0 else "synced"}
            
            # Get ahead/behind counts
            result = subprocess.run(
                ["git", "rev-list", "--left-right", "--count", f"HEAD...origin/{current_branch}"],
                cwd=self.path,
                capture_output=True,
                text=True,
                check=True
            )
            
            parts = result.stdout.strip().split()
            ahead = int(parts[0]) if len(parts) > 0 else 0
            behind = int(parts[1]) if len(parts) > 1 else 0
            
            if ahead == 0 and behind == 0:
                status = "synced"
            elif ahead > 0 and behind == 0:
                status = "ahead"
            elif ahead == 0 and behind > 0:
                status = "behind"
            else:
                status = "diverged"
            
            return {"connected": True, "ahead": ahead, "behind": behind, "status": status}
            
        except subprocess.TimeoutExpired:
            return {"connected": True, "ahead": 0, "behind": 0, "status": "error"}
        except Exception:
            return {"connected": True, "ahead": 0, "behind": 0, "status": "error"}
    
    def push_to_github(self) -> tuple[bool, str]:
        """
        Push current branch to GitHub.
        
        Returns (success, message).
        """
        if not (self.path / ".git").exists():
            return False, "No git repository found"
        
        if not self.has_remote():
            return False, "No GitHub remote configured. Connect to GitHub first."
        
        current_branch = self.get_current_branch()
        if not current_branch:
            return False, "Couldn't determine current branch"
        
        try:
            # Push with upstream tracking
            result = subprocess.run(
                ["git", "push", "-u", "origin", current_branch],
                cwd=self.path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                return True, "Pushed successfully!"
            else:
                error = result.stderr.strip()
                if "rejected" in error.lower():
                    return False, "Push rejected - the remote has changes you don't have. Pull first."
                elif "authentication" in error.lower() or "permission" in error.lower():
                    return False, "Authentication failed. Check your GitHub settings."
                else:
                    return False, f"Push failed: {error}"
                    
        except subprocess.TimeoutExpired:
            return False, "Push timed out. Check your internet connection."
        except Exception as e:
            return False, f"Error: {e}"
    
    def pull_from_github(self) -> tuple[bool, str]:
        """
        Pull latest changes from GitHub.
        
        Returns (success, message).
        """
        if not (self.path / ".git").exists():
            return False, "No git repository found"
        
        if not self.has_remote():
            return False, "No GitHub remote configured. Connect to GitHub first."
        
        # Check for unsaved changes
        if self.has_unsaved_changes:
            return False, "You have unsaved changes. Save a version first, then pull."
        
        current_branch = self.get_current_branch()
        if not current_branch:
            return False, "Couldn't determine current branch"
        
        try:
            result = subprocess.run(
                ["git", "pull", "origin", current_branch],
                cwd=self.path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if "Already up to date" in output:
                    return True, "Already up to date!"
                else:
                    return True, "Pulled latest changes!"
            else:
                error = result.stderr.strip()
                if "conflict" in error.lower():
                    return False, "Merge conflict detected. This needs manual resolution."
                elif "authentication" in error.lower():
                    return False, "Authentication failed. Check your GitHub settings."
                else:
                    return False, f"Pull failed: {error}"
                    
        except subprocess.TimeoutExpired:
            return False, "Pull timed out. Check your internet connection."
        except Exception as e:
            return False, f"Error: {e}"
    
    def get_unmerged_claude_branches(self) -> list[dict]:
        """
        Find remote Claude branches that have commits not in main.
        
        Returns list of dicts with:
        - branch: str (branch name)
        - date: str (relative date like "6 minutes ago")
        - message: str (last commit message)
        - commits_ahead: int (how many commits ahead of main)
        """
        if not (self.path / ".git").exists():
            return []
        
        if not self.has_remote():
            return []
        
        try:
            # Fetch latest
            subprocess.run(
                ["git", "fetch", "origin"],
                cwd=self.path,
                capture_output=True,
                timeout=30
            )
            
            main_name = self.get_main_branch_name()
            
            # Get all remote claude branches with their info
            result = subprocess.run(
                ["git", "for-each-ref", 
                 "--sort=-committerdate",
                 "--format=%(refname:short)|%(committerdate:relative)|%(subject)",
                 "refs/remotes/origin/claude/"],
                cwd=self.path,
                capture_output=True,
                text=True,
                check=True
            )
            
            if not result.stdout.strip():
                return []
            
            unmerged = []
            
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                
                parts = line.split("|", 2)
                if len(parts) < 3:
                    continue
                
                branch = parts[0]  # e.g., origin/claude/some-branch-name
                date = parts[1]
                message = parts[2]
                
                # Check if this branch has commits not in main
                count_result = subprocess.run(
                    ["git", "rev-list", "--count", f"origin/{main_name}..{branch}"],
                    cwd=self.path,
                    capture_output=True,
                    text=True
                )
                
                if count_result.returncode == 0:
                    commits_ahead = int(count_result.stdout.strip())
                    
                    if commits_ahead > 0:
                        # Strip origin/ prefix for display
                        display_branch = branch.replace("origin/", "")
                        
                        unmerged.append({
                            "branch": branch,  # Full ref for git commands
                            "display_name": display_branch,  # Friendly name for UI
                            "date": date,
                            "message": message[:60] + "..." if len(message) > 60 else message,
                            "commits_ahead": commits_ahead
                        })
            
            return unmerged
            
        except subprocess.TimeoutExpired:
            return []
        except Exception:
            return []
    
    def merge_branch(self, branch: str) -> tuple[bool, str]:
        """
        Merge a branch into the current branch.
        
        Args:
            branch: Full branch ref (e.g., origin/claude/some-branch)
        
        Returns (success, message).
        """
        if not (self.path / ".git").exists():
            return False, "No git repository found"
        
        # Check for unsaved changes
        if self.has_unsaved_changes:
            return False, "You have unsaved changes. Save a version first."
        
        try:
            result = subprocess.run(
                ["git", "merge", branch],
                cwd=self.path,
                capture_output=True,
                text=True,
                timeout=60
            )
            
            if result.returncode == 0:
                output = result.stdout.strip()
                if "Already up to date" in output:
                    return True, "Already up to date - nothing to merge."
                else:
                    return True, "Merged successfully!"
            else:
                error = result.stderr.strip()
                if "conflict" in error.lower() or "CONFLICT" in result.stdout:
                    # Abort the merge to restore clean state
                    subprocess.run(
                        ["git", "merge", "--abort"],
                        cwd=self.path,
                        capture_output=True
                    )
                    return False, "Merge conflict detected. This branch has changes that conflict with yours."
                else:
                    return False, f"Merge failed: {error}"
                    
        except subprocess.TimeoutExpired:
            return False, "Merge timed out."
        except Exception as e:
            return False, f"Error: {e}"
    
    # === Handled Branches (for Claude branch tracking) ===
    
    def get_handled_branches(self) -> dict:
        """Get the dictionary of handled Claude branches from project config."""
        if not self.config_file.exists():
            return {}
        
        try:
            with open(self.config_file) as f:
                config = json.load(f)
                return config.get("handled_branches", {})
        except:
            return {}
    
    def mark_branch_handled(self, branch: str, action: str) -> None:
        """
        Mark a Claude branch as handled (merged or ignored).
        
        Args:
            branch: Full branch ref (e.g., origin/claude/some-branch)
            action: Either "merged" or "ignored"
        """
        commit_hash = self._get_branch_head(branch)
        
        config = {}
        if self.config_file.exists():
            try:
                with open(self.config_file) as f:
                    config = json.load(f)
            except:
                pass
        
        if "handled_branches" not in config:
            config["handled_branches"] = {}
        
        config["handled_branches"][branch] = {
            "action": action,
            "timestamp": datetime.now().isoformat(),
            "last_commit": commit_hash
        }
        
        self.ptc_dir.mkdir(parents=True, exist_ok=True)
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)
    
    def _get_branch_head(self, branch: str) -> Optional[str]:
        """Get the commit hash at the head of a branch."""
        if not (self.path / ".git").exists():
            return None
        
        try:
            result = subprocess.run(
                ["git", "rev-parse", branch],
                cwd=self.path,
                capture_output=True,
                text=True,
                timeout=10
            )
            if result.returncode == 0:
                return result.stdout.strip()[:12]
            return None
        except:
            return None
    
    def is_branch_handled(self, branch: str) -> tuple[bool, Optional[str]]:
        """
        Check if a branch was already handled.
        
        Returns (is_handled, action) where action is "merged", "ignored", or None.
        Branch is unhandled if it has new commits since we handled it.
        """
        handled = self.get_handled_branches()
        
        if branch not in handled:
            return False, None
        
        info = handled[branch]
        last_handled_commit = info.get("last_commit")
        current_commit = self._get_branch_head(branch)
        
        if current_commit and last_handled_commit:
            if current_commit != last_handled_commit:
                return False, None
        
        return True, info.get("action")
    
    # === Branch Management ===
    
    def get_current_branch(self) -> Optional[str]:
        """Get the name of the current git branch."""
        if not (self.path / ".git").exists():
            return None
        
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.path,
                capture_output=True,
                text=True,
                check=True
            )
            return result.stdout.strip() or None
        except Exception:
            return None
    
    def get_main_branch_name(self) -> str:
        """Figure out if this repo uses 'main' or 'master'."""
        if not (self.path / ".git").exists():
            return "main"
        
        try:
            # Check which branches exist
            result = subprocess.run(
                ["git", "branch", "--list"],
                cwd=self.path,
                capture_output=True,
                text=True,
                check=True
            )
            branches = [b.strip().lstrip("* ") for b in result.stdout.strip().split("\n")]
            
            if "main" in branches:
                return "main"
            elif "master" in branches:
                return "master"
            else:
                return "main"  # Default assumption
        except Exception:
            return "main"
    
    def is_on_main_branch(self) -> bool:
        """Check if we're on the main/master branch."""
        current = self.get_current_branch()
        if current is None:
            return True  # No git, no branch problems
        
        main_name = self.get_main_branch_name()
        return current == main_name
    
    def switch_to_main(self, force: bool = False) -> tuple[bool, str]:
        """
        Switch back to the main branch.
        
        Returns (success, message).
        If there are uncommitted changes and force=False, returns failure.
        Preserves .ptc config if it doesn't exist on target branch.
        """
        if not (self.path / ".git").exists():
            return False, "No git repository found"
        
        # Check for uncommitted changes
        if self.has_unsaved_changes and not force:
            return False, "You have unsaved changes. Save a version first, or they'll be lost."
        
        main_name = self.get_main_branch_name()
        
        # Save current config in case we need to restore it
        current_config = {
            "name": self.name,
            "main_file": self.main_file,
            "description": self.description,
            "python_version": self.python_version,
            "created": self.created,
            "github_repo": self.github_repo,
        }
        
        try:
            # Stash any changes if forcing
            if force and self.has_unsaved_changes:
                subprocess.run(
                    ["git", "stash"],
                    cwd=self.path,
                    capture_output=True,
                    check=True
                )
            
            # Switch to main
            result = subprocess.run(
                ["git", "checkout", main_name],
                cwd=self.path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                error = result.stderr.strip()
                return False, f"Couldn't switch branches: {error}"
            
            # Check if .ptc config exists on this branch
            if not self.config_file.exists():
                # Recreate the config on this branch
                self.ptc_dir.mkdir(parents=True, exist_ok=True)
                
                import json
                with open(self.config_file, "w") as f:
                    json.dump(current_config, f, indent=2)
                
                # Commit the config to this branch
                subprocess.run(
                    ["git", "add", ".ptc/"],
                    cwd=self.path,
                    capture_output=True,
                    check=True
                )
                subprocess.run(
                    ["git", "commit", "-m", "Added PTC project config"],
                    cwd=self.path,
                    capture_output=True,
                    check=True
                )
            
            return True, f"Switched to {main_name}"
            
        except Exception as e:
            return False, f"Something went wrong: {e}"


def find_ptc_projects(root: Optional[Path] = None) -> list[Project]:
    """
    Find all PTC projects under a given root directory,
    plus any registered projects from other locations.
    
    Searches for directories containing .ptc/project.json
    """
    if root is None:
        root = DEFAULT_PROJECTS_ROOT
    
    projects = []
    seen_paths = set()
    
    # Search the default/provided root
    if root.exists():
        for ptc_dir in root.rglob(".ptc"):
            if ptc_dir.is_dir() and (ptc_dir / "project.json").exists():
                project_path = ptc_dir.parent
                if project_path not in seen_paths:
                    try:
                        project = Project.load(project_path)
                        projects.append(project)
                        seen_paths.add(project_path)
                    except Exception:
                        pass  # Skip invalid projects
    
    # Also check registered projects (imports from other locations)
    for project_path in get_known_project_paths():
        if project_path not in seen_paths and project_path.exists():
            ptc_config = project_path / ".ptc" / "project.json"
            if ptc_config.exists():
                try:
                    project = Project.load(project_path)
                    projects.append(project)
                    seen_paths.add(project_path)
                except Exception:
                    pass  # Skip invalid projects
    
    # Sort by name
    projects.sort(key=lambda p: p.name.lower())
    
    return projects
