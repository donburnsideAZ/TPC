"""
Project model for TPC.

A project is a Python codebase that TPC manages. Projects have:
- A location on disk (the project folder)
- A .tpc/ folder containing config and state
- An invisible git repo for version tracking
- Metadata about what we're building

The user never sees .tpc/ or .git/ - they just see their code.
"""

import json
import subprocess
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import Optional


def _subprocess_args() -> dict:
    """
    Get platform-specific subprocess arguments.
    
    On Windows, this prevents console windows from popping up
    when running git commands from a frozen PyInstaller executable.
    """
    kwargs = {}
    if sys.platform == "win32":
        # CREATE_NO_WINDOW = 0x08000000
        # This prevents the console window from appearing
        kwargs["creationflags"] = 0x08000000
    return kwargs


# Default location for new projects
DEFAULT_PROJECTS_ROOT = Path.home() / "Documents" / "TPC Projects"

# Registry for tracking projects outside the default location
TPC_CONFIG_DIR = Path.home() / ".tpc"
KNOWN_PROJECTS_FILE = TPC_CONFIG_DIR / "known_projects.json"



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
    TPC_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
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


def remove_from_tpc(path: Path) -> tuple[bool, str]:
    """
    Remove a project from TPC management without deleting any user files.
    
    This:
    - Deletes the .tpc/ folder (TPC's config)
    - Removes from known_projects.json registry
    - Does NOT touch .git/, source files, or anything else
    
    Returns (success, message).
    """
    import shutil
    
    tpc_dir = path / ".tpc"
    
    try:
        # Remove from registry first (even if .tpc doesn't exist)
        unregister_project_path(path)
        
        # Remove .tpc folder if it exists
        if tpc_dir.exists():
            shutil.rmtree(tpc_dir)
            return True, f"Removed '{path.name}' from TPC. Your files are still there."
        else:
            return True, f"Removed '{path.name}' from TPC registry."
            
    except PermissionError:
        return False, f"Permission denied. Can't remove .tpc folder from {path}"
    except Exception as e:
        return False, f"Something went wrong: {e}"


def get_config_dir() -> Path:
    """Get the TPC config directory path (~/.tpc)."""
    return TPC_CONFIG_DIR


def cleanup_stale_projects() -> tuple[int, list[str]]:
    """
    Remove stale entries from the project registry.

    A project is stale if:
    - The project folder no longer exists, OR
    - The .tpc/project.json config doesn't exist

    Returns (count_removed, list_of_removed_paths).
    """
    stale = []
    paths = get_known_project_paths()

    for path in paths:
        is_stale = False

        if not path.exists():
            is_stale = True
        else:
            tpc_config = path / ".tpc" / "project.json"
            if not tpc_config.exists():
                is_stale = True

        if is_stale:
            stale.append(str(path))

    for path_str in stale:
        unregister_project_path(Path(path_str))

    return len(stale), stale


def get_orphan_folders(root: Optional[Path] = None) -> list[Path]:
    """
    Find folders in the TPC Projects directory that look like failed/incomplete projects.

    An orphan folder:
    - Exists in the TPC Projects directory
    - Has no .tpc config folder
    - Is not a recognized system folder

    Returns list of orphan folder paths.
    """
    if root is None:
        root = DEFAULT_PROJECTS_ROOT

    if not root.exists():
        return []

    orphans = []
    ignore = {'.DS_Store', 'Thumbs.db', '.git', '__pycache__', 'node_modules'}

    try:
        for item in root.iterdir():
            if item.name in ignore or item.name.startswith('.'):
                continue

            if item.is_dir():
                tpc_config = item / ".tpc" / "project.json"
                if not tpc_config.exists():
                    orphans.append(item)
    except PermissionError:
        pass

    return orphans


@dataclass
class Project:
    """Represents a TPC-managed project."""
    
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
    def tpc_dir(self) -> Path:
        """The hidden .tpc config directory."""
        return self.path / ".tpc"
    
    @property
    def config_file(self) -> Path:
        """The project.json config file."""
        return self.tpc_dir / "project.json"
    
    @property
    def main_file_path(self) -> Path:
        """Full path to the main Python file."""
        return self.path / self.main_file
    
    @property
    def has_git(self) -> bool:
        """Check if this project has git initialized."""
        return (self.path / ".git").exists()
    
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
            , **_subprocess_args())
            return bool(result.stdout.strip())
        except Exception:
            return False
    
    def reinitialize_git(self) -> tuple[bool, str]:
        """
        Reinitialize git tracking for this project.
        
        Use this when .git folder was deleted but .tpc config still exists.
        Creates a fresh git repo and saves the first version.
        
        Returns (success, message).
        """
        if self.has_git:
            return False, "Git is already initialized."
        
        try:
            # Initialize git
            self._init_git()
            
            # Check if it worked
            if not self.has_git:
                return False, "Couldn't initialize git. Check folder permissions."
            
            # Save first version
            self.save_version("Restored version tracking")
            
            return True, "Version tracking restored! Your current files are now saved as the first version."
            
        except Exception as e:
            return False, f"Something went wrong: {e}"
    
    def save_config(self) -> None:
        """Save project configuration to .tpc/project.json."""
        self.tpc_dir.mkdir(parents=True, exist_ok=True)
        
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
        """Load a project from a directory containing .tpc/project.json."""
        tpc_dir = path / ".tpc"
        config_file = tpc_dir / "project.json"
        
        if not config_file.exists():
            raise ValueError(f"No TPC project found at {path}")
        
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
        - .tpc/ config directory
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

Created with TPC - Pack Track Click
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
        Adopt an existing script into a proper TPC project.
        
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
        Import an existing project folder into TPC management.

        Unlike adopt, this doesn't copy anything - it wraps the folder
        in-place. If the folder already has git history, we keep it.
        """
        if not folder.is_dir():
            raise ValueError(f"Not a directory: {folder}")

        if (folder / ".tpc" / "project.json").exists():
            raise ValueError("This folder is already a TPC project")
        
        # Create the project instance
        project = cls(
            name=name,
            path=folder,
            main_file=main_file,
            description=description or f"Imported from {folder.name}",
        )
        
        # Save config (creates .tpc/ folder)
        project.save_config()
        
        # Register this project so it shows up in the sidebar
        register_project_path(folder)
        
        # Initialize git only if it doesn't exist
        if not (folder / ".git").exists():
            project._init_git()
            project.save_version("Imported into TPC")
        else:
            # Git exists - just make sure .tpc is tracked
            # Stage just the .tpc folder if there are no other changes
            try:
                subprocess.run(
                    ["git", "add", ".tpc/"],
                    cwd=folder,
                    capture_output=True,
                    check=True
                , **_subprocess_args())
                # Only commit if .tpc was actually added
                result = subprocess.run(
                    ["git", "status", "--porcelain", ".tpc/"],
                    cwd=folder,
                    capture_output=True,
                    text=True
                , **_subprocess_args())
                if result.stdout.strip():
                    subprocess.run(
                        ["git", "commit", "-m", "Added TPC project config"],
                        cwd=folder,
                        capture_output=True,
                        check=True
                    , **_subprocess_args())
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
            , **_subprocess_args())
            
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

# TPC build outputs
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
    
    def save_version(self, message: Optional[str] = None) -> tuple[bool, str]:
        """
        Save the current state as a version (git commit).
        
        Returns (success, status_message) where status_message is:
        - "saved" if successful
        - "nothing_to_save" if no changes
        - "needs_identity" if git needs user.name/user.email configured
        - "error: <details>" for other failures
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
            , **_subprocess_args())
            
            # Check if there's anything to commit
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.path,
                capture_output=True,
                text=True
            , **_subprocess_args())
            
            if not result.stdout.strip():
                return False, "nothing_to_save"
            
            # Commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=self.path,
                capture_output=True,
                text=True
            , **_subprocess_args())
            
            if result.returncode == 0:
                return True, "saved"
            else:
                # Check for identity error
                stderr = result.stderr.lower()
                if "please tell me who you are" in stderr or "user.name" in stderr or "user.email" in stderr:
                    return False, "needs_identity"
                else:
                    return False, f"error: {result.stderr.strip()}"
            
        except subprocess.CalledProcessError as e:
            stderr = e.stderr.decode() if isinstance(e.stderr, bytes) else str(e.stderr)
            if "please tell me who you are" in stderr.lower() or "user.name" in stderr.lower():
                return False, "needs_identity"
            return False, f"error: {stderr}"
        except Exception as e:
            print(f"Warning: Could not save version: {e}")
            return False, f"error: {e}"
    
    def configure_git_identity(self, name: str, email: str) -> tuple[bool, str]:
        """
        Configure git user.name and user.email for this repository.
        
        Returns (success, message).
        """
        try:
            subprocess.run(
                ["git", "config", "user.name", name],
                cwd=self.path,
                capture_output=True,
                check=True
            , **_subprocess_args())
            
            subprocess.run(
                ["git", "config", "user.email", email],
                cwd=self.path,
                capture_output=True,
                check=True
            , **_subprocess_args())
            
            return True, "Identity configured"
        except Exception as e:
            return False, f"Failed to configure git identity: {e}"
    
    def get_version_history(self) -> list[dict]:
        """Get the version history (git log) as a list of dicts."""
        try:
            result = subprocess.run(
                ["git", "log", "--pretty=format:%H|%s|%ai", "-n", "50"],
                cwd=self.path,
                capture_output=True,
                text=True,
                check=True
            , **_subprocess_args())
            
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
    
    def restore_to_version(self, commit_hash: str, original_message: str = "") -> tuple[bool, str]:
        """
        Restore the project to a previous version.
        
        This doesn't delete history - it creates a NEW commit that matches
        the state of the old commit. You can always restore forward again.
        
        Args:
            commit_hash: The git commit hash to restore to
            original_message: The original commit message (for the new commit message)
        
        Returns (success, message).
        """
        if not (self.path / ".git").exists():
            return False, "No version history found"
        
        # Check for unsaved changes
        if self.has_unsaved_changes:
            return False, "You have unsaved changes. Save a version first, then restore."
        
        try:
            # First, verify the commit exists
            result = subprocess.run(
                ["git", "cat-file", "-t", commit_hash],
                cwd=self.path,
                capture_output=True,
                text=True
            , **_subprocess_args())
            
            if result.returncode != 0:
                return False, "That version no longer exists"
            
            # Checkout all files from that commit (but stay on current branch)
            # This overwrites working directory with the old version's files
            result = subprocess.run(
                ["git", "checkout", commit_hash, "--", "."],
                cwd=self.path,
                capture_output=True,
                text=True
            , **_subprocess_args())
            
            if result.returncode != 0:
                return False, f"Couldn't restore files: {result.stderr.strip()}"
            
            # Now commit this as a new version
            if original_message:
                restore_message = f"Restored to: {original_message}"
            else:
                restore_message = f"Restored to version {commit_hash[:7]}"
            
            # Stage all the restored files
            subprocess.run(
                ["git", "add", "-A"],
                cwd=self.path,
                capture_output=True,
                check=True
            , **_subprocess_args())
            
            # Commit the restoration
            subprocess.run(
                ["git", "commit", "-m", restore_message],
                cwd=self.path,
                capture_output=True,
                check=True
            , **_subprocess_args())
            
            return True, f"Restored! Your files now match '{original_message or commit_hash[:7]}'"
            
        except subprocess.CalledProcessError as e:
            return False, f"Restore failed: {e.stderr if e.stderr else str(e)}"
        except Exception as e:
            return False, f"Something went wrong: {e}"
    
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
            , **_subprocess_args())
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
            , **_subprocess_args())
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
                , **_subprocess_args())
            else:
                # Add new remote
                subprocess.run(
                    ["git", "remote", "add", "origin", url],
                    cwd=self.path,
                    capture_output=True,
                    check=True
                , **_subprocess_args())
            
            # Save to project config too
            self.github_repo = url
            self.save_config()
            
            return True, "Remote configured successfully"
            
        except subprocess.CalledProcessError as e:
            return False, f"Failed to set remote: {e.stderr}"
        except Exception as e:
            return False, f"Error: {e}"
    
    def get_last_push_date(self) -> str | None:
        """
        Get the date of the last push to remote.
        
        Returns a human-friendly date string like "Dec 20" or "Today at 3:45 PM",
        or None if never pushed or can't determine.
        """
        if not (self.path / ".git").exists():
            return None
        
        if not self.has_remote():
            return None
        
        try:
            # Get the current branch
            current_branch = self.get_current_branch()
            if not current_branch:
                return None
            
            # Check if remote branch exists and get its date
            result = subprocess.run(
                ["git", "log", "-1", "--format=%ci", f"origin/{current_branch}"],
                cwd=self.path,
                capture_output=True,
                text=True,
                timeout=5,
                **_subprocess_args()
            )
            
            if result.returncode != 0 or not result.stdout.strip():
                return None
            
            # Parse the date
            from datetime import datetime, timezone
            date_str = result.stdout.strip()
            
            # Git format is like: 2025-12-20 15:30:45 -0700
            try:
                # Parse without timezone for simplicity
                dt = datetime.strptime(date_str[:19], "%Y-%m-%d %H:%M:%S")
                now = datetime.now()
                
                # Format based on how recent
                if dt.date() == now.date():
                    return f"Today at {dt.strftime('%I:%M %p').lstrip('0')}"
                elif (now - dt).days == 1:
                    return f"Yesterday at {dt.strftime('%I:%M %p').lstrip('0')}"
                elif (now - dt).days < 7:
                    return dt.strftime("%A")  # Day name
                else:
                    return dt.strftime("%b %d")  # Dec 20
                    
            except ValueError:
                return date_str[:10]  # Just return the date part
                
        except subprocess.TimeoutExpired:
            return None
        except Exception:
            return None
    
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
            from core.github import run_git_with_auth, has_github_credentials
            
            if has_github_credentials():
                run_git_with_auth(
                    ["fetch", "origin"],
                    cwd=self.path,
                    timeout=30
                )
            else:
                subprocess.run(
                    ["git", "fetch", "origin"],
                    cwd=self.path,
                    capture_output=True,
                    timeout=30  # Don't hang forever
                , **_subprocess_args())
            
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
            , **_subprocess_args())
            
            if result.returncode != 0:
                # No upstream set - we have commits but haven't pushed yet
                result = subprocess.run(
                    ["git", "rev-list", "--count", "HEAD"],
                    cwd=self.path,
                    capture_output=True,
                    text=True
                , **_subprocess_args())
                local_commits = int(result.stdout.strip()) if result.returncode == 0 else 0
                return {"connected": True, "ahead": local_commits, "behind": 0, "status": "ahead" if local_commits > 0 else "synced"}
            
            # Get ahead/behind counts
            result = subprocess.run(
                ["git", "rev-list", "--left-right", "--count", f"HEAD...origin/{current_branch}"],
                cwd=self.path,
                capture_output=True,
                text=True,
                check=True
            , **_subprocess_args())
            
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
        Special message "DIVERGED" indicates histories have diverged and user needs to choose.
        """
        from core.github import run_git_with_auth, has_github_credentials
        
        if not (self.path / ".git").exists():
            return False, "No git repository found"
        
        if not self.has_remote():
            return False, "No GitHub remote configured. Connect to GitHub first."
        
        current_branch = self.get_current_branch()
        if not current_branch:
            return False, "Couldn't determine current branch"
        
        if not has_github_credentials():
            return False, "GitHub not connected. Go to Settings → GitHub to sign in."
        
        try:
            # Push with upstream tracking using authenticated git
            result = run_git_with_auth(
                ["push", "-u", "origin", current_branch],
                cwd=self.path,
                timeout=60
            )
            
            if result.returncode == 0:
                return True, "Pushed successfully!"
            else:
                error = result.stderr.strip()
                if "rejected" in error.lower() or "non-fast-forward" in error.lower():
                    # Special return value to trigger conflict resolution dialog
                    return False, "DIVERGED"
                elif "authentication" in error.lower() or "permission" in error.lower() or "403" in error:
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
        from core.github import run_git_with_auth, has_github_credentials
        
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
        
        if not has_github_credentials():
            return False, "GitHub not connected. Go to Settings → GitHub to sign in."
        
        try:
            result = run_git_with_auth(
                ["pull", "origin", current_branch],
                cwd=self.path,
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
                elif "authentication" in error.lower() or "403" in error:
                    return False, "Authentication failed. Check your GitHub settings."
                else:
                    return False, f"Pull failed: {error}"
                    
        except subprocess.TimeoutExpired:
            return False, "Pull timed out. Check your internet connection."
        except Exception as e:
            return False, f"Error: {e}"
    
    def force_push_to_github(self) -> tuple[bool, str]:
        """
        Force push current branch to GitHub, overwriting remote history.
        
        Use this when local is the "truth" and remote has garbage/old commits.
        
        Returns (success, message).
        """
        from core.github import run_git_with_auth, has_github_credentials
        
        if not (self.path / ".git").exists():
            return False, "No git repository found"
        
        if not self.has_remote():
            return False, "No GitHub remote configured."
        
        current_branch = self.get_current_branch()
        if not current_branch:
            return False, "Couldn't determine current branch"
        
        if not has_github_credentials():
            return False, "GitHub not connected. Go to Settings → GitHub to sign in."
        
        try:
            # Force push - this overwrites remote history
            result = run_git_with_auth(
                ["push", "--force", "-u", "origin", current_branch],
                cwd=self.path,
                timeout=60
            )
            
            if result.returncode == 0:
                return True, "Force pushed successfully! GitHub now matches your local version."
            else:
                error = result.stderr.strip()
                if "authentication" in error.lower() or "permission" in error.lower() or "403" in error:
                    return False, "Authentication failed. Check your GitHub settings."
                else:
                    return False, f"Force push failed: {error}"
                    
        except subprocess.TimeoutExpired:
            return False, "Push timed out. Check your internet connection."
        except Exception as e:
            return False, f"Error: {e}"
    
    def reset_to_remote(self) -> tuple[bool, str]:
        """
        Reset local to match remote, discarding local commits.
        
        Use this when remote is the "truth" and local has garbage/old commits.
        
        Returns (success, message).
        """
        from core.github import run_git_with_auth, has_github_credentials
        
        if not (self.path / ".git").exists():
            return False, "No git repository found"
        
        if not self.has_remote():
            return False, "No GitHub remote configured."
        
        current_branch = self.get_current_branch()
        if not current_branch:
            return False, "Couldn't determine current branch"
        
        if not has_github_credentials():
            return False, "GitHub not connected. Go to Settings → GitHub to sign in."
        
        try:
            # First fetch to get latest remote state
            run_git_with_auth(
                ["fetch", "origin"],
                cwd=self.path,
                timeout=30
            )
            
            # Hard reset to remote branch
            result = subprocess.run(
                ["git", "reset", "--hard", f"origin/{current_branch}"],
                cwd=self.path,
                capture_output=True,
                text=True,
                timeout=30
            , **_subprocess_args())
            
            if result.returncode == 0:
                return True, "Reset successful! Your local files now match GitHub."
            else:
                error = result.stderr.strip()
                return False, f"Reset failed: {error}"
                    
        except subprocess.TimeoutExpired:
            return False, "Operation timed out. Check your internet connection."
        except Exception as e:
            return False, f"Error: {e}"
    
    def get_unmerged_claude_branches(self) -> list[dict]:
        """
        Find remote Claude branches that have commits not in main.
        DEPRECATED: Use get_unmerged_remote_branches() instead.
        """
        return self.get_unmerged_remote_branches(filter_prefix="refs/remotes/origin/claude/")
    
    def get_unmerged_remote_branches(self, filter_prefix: str = None) -> list[dict]:
        """
        Find remote branches that have commits not in main.
        
        Args:
            filter_prefix: Optional prefix to filter branches (e.g., "refs/remotes/origin/claude/")
                          If None, returns ALL remote branches except main/master.
        
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
            from core.github import run_git_with_auth, has_github_credentials
            
            if has_github_credentials():
                run_git_with_auth(
                    ["fetch", "origin"],
                    cwd=self.path,
                    timeout=30
                )
            else:
                subprocess.run(
                    ["git", "fetch", "origin"],
                    cwd=self.path,
                    capture_output=True,
                    timeout=30
                , **_subprocess_args())
            
            main_name = self.get_main_branch_name()
            
            # Get all remote branches with their info
            # If filter_prefix is provided, only get those branches
            # Otherwise get all refs/remotes/origin/*
            ref_pattern = filter_prefix if filter_prefix else "refs/remotes/origin/"
            
            result = subprocess.run(
                ["git", "for-each-ref", 
                 "--sort=-committerdate",
                 "--format=%(refname:short)|%(committerdate:relative)|%(subject)",
                 ref_pattern],
                cwd=self.path,
                capture_output=True,
                text=True,
                check=True
            , **_subprocess_args())
            
            if not result.stdout.strip():
                return []
            
            unmerged = []
            
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                
                parts = line.split("|", 2)
                if len(parts) < 3:
                    continue
                
                branch = parts[0]  # e.g., origin/claude/some-branch-name or origin/feature-x
                date = parts[1]
                message = parts[2]
                
                # Skip main/master and HEAD
                branch_short = branch.replace("origin/", "")
                if branch_short in ("main", "master", "HEAD"):
                    continue
                
                # Check if this branch has commits not in main
                count_result = subprocess.run(
                    ["git", "rev-list", "--count", f"origin/{main_name}..{branch}"],
                    cwd=self.path,
                    capture_output=True,
                    text=True
                , **_subprocess_args())
                
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
            , **_subprocess_args())
            
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
                    , **_subprocess_args())
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
        
        self.tpc_dir.mkdir(parents=True, exist_ok=True)
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
            , **_subprocess_args())
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
            , **_subprocess_args())
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
            , **_subprocess_args())
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
        Preserves .tpc config if it doesn't exist on target branch.
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
                , **_subprocess_args())
            
            # Switch to main
            result = subprocess.run(
                ["git", "checkout", main_name],
                cwd=self.path,
                capture_output=True,
                text=True
            , **_subprocess_args())
            
            if result.returncode != 0:
                error = result.stderr.strip()
                return False, f"Couldn't switch branches: {error}"
            
            # Check if .tpc config exists on this branch
            if not self.config_file.exists():
                # Recreate the config on this branch
                self.tpc_dir.mkdir(parents=True, exist_ok=True)
                
                import json
                with open(self.config_file, "w") as f:
                    json.dump(current_config, f, indent=2)
                
                # Commit the config to this branch
                subprocess.run(
                    ["git", "add", ".tpc/"],
                    cwd=self.path,
                    capture_output=True,
                    check=True
                , **_subprocess_args())
                subprocess.run(
                    ["git", "commit", "-m", "Added TPC project config"],
                    cwd=self.path,
                    capture_output=True,
                    check=True
                , **_subprocess_args())
            
            return True, f"Switched to {main_name}"
            
        except Exception as e:
            return False, f"Something went wrong: {e}"


def find_tpc_projects(root: Optional[Path] = None) -> list[Project]:
    """
    Find all TPC projects under a given root directory,
    plus any registered projects from other locations.

    Searches for directories containing .tpc/project.json.

    TPC 2.0: Uses the configured projects_root from config.json
    instead of hardcoded DEFAULT_PROJECTS_ROOT.
    """
    if root is None:
        try:
            from .config import get_config
            config = get_config()
            if config.projects_root:
                root = config.get_projects_path()
            else:
                root = DEFAULT_PROJECTS_ROOT
        except ImportError:
            root = DEFAULT_PROJECTS_ROOT

    projects = []
    seen_paths = set()

    if root.exists():
        for tpc_dir in root.rglob(".tpc"):
            if tpc_dir.is_dir() and (tpc_dir / "project.json").exists():
                project_path = tpc_dir.parent
                if project_path not in seen_paths:
                    try:
                        project = Project.load(project_path)
                        projects.append(project)
                        seen_paths.add(project_path)
                    except Exception:
                        pass

    # Also check registered projects
    for project_path in get_known_project_paths():
        if project_path not in seen_paths and project_path.exists():
            tpc_config = project_path / ".tpc" / "project.json"
            if tpc_config.exists():
                try:
                    project = Project.load(project_path)
                    projects.append(project)
                    seen_paths.add(project_path)
                except Exception:
                    pass

    projects.sort(key=lambda p: p.name.lower())

    return projects
