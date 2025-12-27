"""
Project model for TPC v3.

A project is a Python codebase that TPC manages. Projects have:
- A location on disk (the project folder)
- A .tpc/ folder containing config and snapshots
- Simple folder-based versioning (no Git!)

The user sees their code + version history. That's it.
"""

import json
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional

from .snapshots import SnapshotManager, Snapshot, SnapshotResult


def _subprocess_args() -> dict:
    """
    Get platform-specific subprocess arguments.
    
    On Windows, this prevents console windows from popping up
    when running commands from a frozen PyInstaller executable.
    """
    kwargs = {}
    if sys.platform == "win32":
        kwargs["creationflags"] = 0x08000000
    return kwargs


# Default location for new projects
DEFAULT_PROJECTS_ROOT = Path.home() / "TPC Projects"

# Registry for tracking projects outside the default location
TPC_CONFIG_DIR = Path.home() / ".tpc"
KNOWN_PROJECTS_FILE = TPC_CONFIG_DIR / "known_projects.json"

# Old config locations (for migration)
OLD_CONFIG_DIR = Path.home() / ".ptc"
OLD_DEFAULT_ROOT = Path.home() / "Documents" / "TPC Projects"


def migrate_global_config() -> bool:
    """
    Migrate global config from ~/.ptc to ~/.tpc if needed.
    Returns True if migration occurred.
    """
    if TPC_CONFIG_DIR.exists() or not OLD_CONFIG_DIR.exists():
        return False
    
    try:
        OLD_CONFIG_DIR.rename(TPC_CONFIG_DIR)
        return True
    except Exception:
        try:
            import shutil
            shutil.copytree(OLD_CONFIG_DIR, TPC_CONFIG_DIR)
            shutil.rmtree(OLD_CONFIG_DIR)
            return True
        except Exception:
            return False


def migrate_project_config(project_path: Path) -> bool:
    """
    Migrate a project's config from .ptc to .tpc if needed.
    Returns True if migration occurred.
    """
    old_dir = project_path / ".ptc"
    new_dir = project_path / ".tpc"
    
    if new_dir.exists() or not old_dir.exists():
        return False
    
    try:
        old_dir.rename(new_dir)
        return True
    except Exception:
        return False


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
    """Add a project path to the registry."""
    TPC_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    
    paths = get_known_project_paths()
    
    if path not in paths:
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
    Remove a project from TPC management without deleting user files.
    
    Deletes .tpc/ folder and removes from registry.
    Does NOT touch source files.
    """
    import shutil
    
    tpc_dir = path / ".tpc"
    
    try:
        unregister_project_path(path)
        
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
            ptc_config = path / ".ptc" / "project.json"
            if not tpc_config.exists() and not ptc_config.exists():
                is_stale = True
        
        if is_stale:
            stale.append(str(path))
    
    for path_str in stale:
        unregister_project_path(Path(path_str))
    
    return len(stale), stale


def get_orphan_folders(root: Optional[Path] = None) -> list[Path]:
    """
    Find folders in TPC Projects that look like incomplete projects.
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
                ptc_config = item / ".ptc" / "project.json"
                
                if not tpc_config.exists() and not ptc_config.exists():
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
    python_version: str = "3.12"
    created: str = field(default_factory=lambda: datetime.now().isoformat())
    github_repo: Optional[str] = None
    icon_path: Optional[str] = None  # Persisted icon path
    snapshot_limit: int = 10
    ignore_patterns: list[str] = field(default_factory=list)
    
    def __post_init__(self):
        """Initialize the snapshot manager."""
        self._snapshot_manager: Optional[SnapshotManager] = None
    
    @property
    def snapshot_manager(self) -> SnapshotManager:
        """Get or create the snapshot manager for this project."""
        if self._snapshot_manager is None:
            self._snapshot_manager = SnapshotManager(self.path, self.snapshot_limit)
            if self.ignore_patterns:
                self._snapshot_manager.set_custom_ignores(self.ignore_patterns)
        return self._snapshot_manager
    
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
    def has_snapshots(self) -> bool:
        """Check if this project has any snapshots."""
        return len(self.snapshot_manager.list_snapshots()) > 0
    
    @property
    def has_unsaved_changes(self) -> bool:
        """
        Check if there are changes since the last snapshot.
        
        For now, this always returns True if no snapshots exist,
        or False if snapshots exist (user should check history).
        
        A more sophisticated implementation could compare file
        modification times against the latest snapshot.
        """
        # Simple implementation: if snapshots exist, we can't easily detect changes
        # without doing a full file comparison. Just return False.
        # The UI will always allow saving a new version.
        return not self.has_snapshots
    
    def save_config(self) -> None:
        """Save project configuration to .tpc/project.json."""
        self.tpc_dir.mkdir(parents=True, exist_ok=True)
        
        config = {
            "name": self.name,
            "main_file": self.main_file,
            "description": self.description,
            "python_version": self.python_version,
            "created": self.created,
            "github_repo": self.github_repo,
            "icon_path": self.icon_path,
            "snapshot_limit": self.snapshot_limit,
            "ignore_patterns": self.ignore_patterns,
        }
        
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)
    
    @classmethod
    def load(cls, path: Path) -> "Project":
        """Load a project from a directory containing .tpc/project.json."""
        migrate_project_config(path)
        
        tpc_dir = path / ".tpc"
        config_file = tpc_dir / "project.json"
        
        if not config_file.exists():
            raise ValueError(f"No TPC project found at {path}")
        
        with open(config_file) as f:
            config = json.load(f)
        
        project = cls(
            name=config["name"],
            path=path,
            main_file=config.get("main_file", "main.py"),
            description=config.get("description", ""),
            python_version=config.get("python_version", "3.12"),
            created=config.get("created", datetime.now().isoformat()),
            github_repo=config.get("github_repo"),
            icon_path=config.get("icon_path"),
            snapshot_limit=config.get("snapshot_limit", 10),
            ignore_patterns=config.get("ignore_patterns", []),
        )
        
        return project
    
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
        - Starter main.py if none exists
        - Initial snapshot
        """
        if location is None:
            location = DEFAULT_PROJECTS_ROOT
        
        project_path = location / name
        project_path.mkdir(parents=True, exist_ok=True)
        
        project = cls(
            name=name,
            path=project_path,
            main_file=main_file,
            description=description,
        )
        
        project.save_config()
        
        # Create starter main.py if it doesn't exist
        main_path = project_path / main_file
        if not main_path.exists():
            main_path.write_text(f'''#!/usr/bin/env python3
"""
{name}
{description if description else "A new project."}

Created with TPC - Track Pack Click
"""


def main():
    print("Hello from {name}!")


if __name__ == "__main__":
    main()
''')
        
        # Create initial snapshot
        project.save_version("Initial project setup")
        
        # Register in known projects
        register_project_path(project_path)
        
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
        Adopt an existing script into a TPC project.
        """
        import shutil
        
        if location is None:
            location = DEFAULT_PROJECTS_ROOT
        
        project_path = location / name
        project_path.mkdir(parents=True, exist_ok=True)
        
        # Copy the main file
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
        
        project.save_config()
        
        # Create initial snapshot
        project.save_version(f"Adopted from {source_file}")
        
        # Register project
        register_project_path(project_path)
        
        # Clean up original if requested
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
        """
        if not folder.is_dir():
            raise ValueError(f"Not a directory: {folder}")
        
        if (folder / ".tpc" / "project.json").exists():
            raise ValueError("This folder is already a TPC project")
        
        project = cls(
            name=name,
            path=folder,
            main_file=main_file,
            description=description or f"Imported from {folder.name}",
        )
        
        project.save_config()
        
        # Register this project
        register_project_path(folder)
        
        # Create initial snapshot
        project.save_version("Imported into TPC")
        
        return project
    
    # === Version Management (Snapshots) ===
    
    def save_version(self, note: str = "") -> SnapshotResult:
        """
        Save the current state as a new version (snapshot).
        
        Args:
            note: Optional description for this version
            
        Returns:
            SnapshotResult with success status
        """
        return self.snapshot_manager.create_snapshot(note)
    
    def get_version_history(self) -> list[Snapshot]:
        """
        Get the version history (list of snapshots).
        
        Returns list sorted by date (newest first).
        """
        return self.snapshot_manager.list_snapshots()
    
    def restore_version(self, snapshot: Snapshot) -> SnapshotResult:
        """
        Restore to a previous version.
        
        Creates a safety backup first, then restores.
        """
        return self.snapshot_manager.restore_snapshot(snapshot)
    
    def get_snapshot_count(self) -> tuple[int, int]:
        """Get (current_count, max_count) for snapshots."""
        return len(self.get_version_history()), self.snapshot_limit
    
    # === GitHub Backup (Simplified) ===
    
    def has_github_backup(self) -> bool:
        """Check if this project has GitHub backup configured."""
        return bool(self.github_repo)
    
    def get_last_backup_date(self) -> Optional[datetime]:
        """
        Get the date of the last GitHub backup.
        
        Stored in .tpc/project.json as 'last_backup'.
        """
        try:
            with open(self.config_file) as f:
                config = json.load(f)
                if "last_backup" in config:
                    return datetime.fromisoformat(config["last_backup"])
        except:
            pass
        return None
    
    def set_last_backup_date(self, date: Optional[datetime] = None) -> None:
        """Record the date of a backup to GitHub."""
        if date is None:
            date = datetime.now()
        
        try:
            with open(self.config_file) as f:
                config = json.load(f)
        except:
            config = {}
        
        config["last_backup"] = date.isoformat()
        
        with open(self.config_file, "w") as f:
            json.dump(config, f, indent=2)
    
    # === Launch ===
    
    def launch(self):
        """Launch the main Python file. Returns Popen object."""
        import subprocess
        return subprocess.Popen(
            ["python3", self.main_file],
            cwd=self.path,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )


def find_tpc_projects(root: Optional[Path] = None) -> list[Project]:
    """
    Find all TPC projects under a given root directory,
    plus any registered projects from other locations.
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
    
    # Also check old default location
    roots_to_check = [root]
    if OLD_DEFAULT_ROOT.exists() and OLD_DEFAULT_ROOT != root:
        roots_to_check.append(OLD_DEFAULT_ROOT)
    
    projects = []
    seen_paths = set()
    
    for check_root in roots_to_check:
        if not check_root.exists():
            continue
            
        for tpc_dir in check_root.rglob(".tpc"):
            if tpc_dir.is_dir() and (tpc_dir / "project.json").exists():
                project_path = tpc_dir.parent
                if project_path not in seen_paths:
                    try:
                        project = Project.load(project_path)
                        projects.append(project)
                        seen_paths.add(project_path)
                    except Exception:
                        pass
        
        # Also check for old .ptc folders
        for ptc_dir in check_root.rglob(".ptc"):
            if ptc_dir.is_dir() and (ptc_dir / "project.json").exists():
                project_path = ptc_dir.parent
                if project_path not in seen_paths:
                    try:
                        project = Project.load(project_path)
                        projects.append(project)
                        seen_paths.add(project_path)
                    except Exception:
                        pass
    
    # Check registered projects
    for project_path in get_known_project_paths():
        if project_path not in seen_paths and project_path.exists():
            tpc_config = project_path / ".tpc" / "project.json"
            ptc_config = project_path / ".ptc" / "project.json"
            if tpc_config.exists() or ptc_config.exists():
                try:
                    project = Project.load(project_path)
                    projects.append(project)
                    seen_paths.add(project_path)
                except Exception:
                    pass
    
    projects.sort(key=lambda p: p.name.lower())
    
    return projects
