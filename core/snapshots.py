"""
Snapshot-based versioning for TPC v3.

Simple, folder-based version control. No Git, no branches, no merge conflicts.
Just timestamped copies of your project that you can see, understand, and restore.

Snapshots live in: .tpc/snapshots/YYYY-MM-DD_HHMM_Optional-Note/
"""

import json
import shutil
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field
from typing import Optional, Callable
import fnmatch


# Default patterns to ignore when creating snapshots
DEFAULT_IGNORE_PATTERNS = [
    # Python
    "__pycache__/",
    "*.pyc",
    "*.pyo",
    "*.pyd",
    ".Python",
    "*.py[cod]",
    "*$py.class",
    
    # Virtual environments
    "venv/",
    ".venv/",
    "env/",
    ".env/",
    "ENV/",
    
    # Git (legacy, if still present)
    ".git/",
    
    # TPC internal
    ".tpc/snapshots/",  # Don't snapshot the snapshots!
    "TPC Builds/",
    
    # Build artifacts
    "build/",
    "dist/",
    "*.spec",
    "*.egg-info/",
    
    # IDE/Editor
    ".idea/",
    ".vscode/",
    "*.swp",
    "*.swo",
    "*~",
    
    # OS files
    ".DS_Store",
    "Thumbs.db",
    "desktop.ini",
    
    # Node (in case of mixed projects)
    "node_modules/",
    
    # Common large/generated files
    "*.log",
    "*.sqlite",
    "*.db",
]


@dataclass
class Snapshot:
    """Represents a single snapshot of a project."""
    name: str  # Folder name (YYYY-MM-DD_HHMM_Note)
    path: Path  # Full path to snapshot folder
    created: datetime
    note: str
    file_count: int
    total_size: int  # bytes
    
    @property
    def display_name(self) -> str:
        """Human-readable name for the snapshot."""
        return self.note if self.note else f"Snapshot {self.created.strftime('%Y-%m-%d %H:%M')}"
    
    @property
    def relative_time(self) -> str:
        """Human-readable relative time (e.g., 'Today at 2:30 PM')."""
        now = datetime.now()
        diff = now - self.created
        
        if diff.days == 0:
            return f"Today at {self.created.strftime('%I:%M %p')}"
        elif diff.days == 1:
            return f"Yesterday at {self.created.strftime('%I:%M %p')}"
        elif diff.days < 7:
            return self.created.strftime('%A at %I:%M %p')  # "Monday at 2:30 PM"
        else:
            return self.created.strftime('%b %d, %Y at %I:%M %p')
    
    @property
    def size_display(self) -> str:
        """Human-readable file size."""
        size = self.total_size
        for unit in ['B', 'KB', 'MB', 'GB']:
            if size < 1024:
                return f"{size:.1f} {unit}"
            size /= 1024
        return f"{size:.1f} TB"


@dataclass
class SnapshotResult:
    """Result of a snapshot operation."""
    success: bool
    message: str
    snapshot: Optional[Snapshot] = None
    deleted_old: Optional[str] = None  # Name of deleted snapshot if limit reached


class SnapshotManager:
    """
    Manages snapshots for a TPC project.
    
    Usage:
        manager = SnapshotManager(project_path)
        
        # Create a snapshot
        result = manager.create_snapshot("Before big refactor")
        
        # List snapshots
        snapshots = manager.list_snapshots()
        
        # Restore a snapshot
        result = manager.restore_snapshot(snapshot)
    """
    
    def __init__(self, project_path: Path, snapshot_limit: int = 10):
        self.project_path = project_path
        self.snapshot_limit = snapshot_limit
        self.snapshots_dir = project_path / ".tpc" / "snapshots"
        self._custom_ignores: list[str] = []
    
    def set_custom_ignores(self, patterns: list[str]) -> None:
        """Set additional ignore patterns from project config."""
        self._custom_ignores = patterns
    
    def _should_ignore(self, path: Path, relative_to: Path) -> bool:
        """Check if a path should be ignored based on patterns."""
        try:
            rel_path = path.relative_to(relative_to)
            rel_str = str(rel_path)
            
            # Check if it's inside the .tpc folder (always ignore snapshots)
            if rel_str.startswith(".tpc/snapshots") or rel_str.startswith(".tpc\\snapshots"):
                return True
            
            # Combine default and custom patterns
            all_patterns = DEFAULT_IGNORE_PATTERNS + self._custom_ignores
            
            for pattern in all_patterns:
                # Handle directory patterns (ending with /)
                if pattern.endswith('/'):
                    dir_pattern = pattern[:-1]
                    # Check if any part of the path matches
                    for part in rel_path.parts:
                        if fnmatch.fnmatch(part, dir_pattern):
                            return True
                    # Also check the full relative path
                    if fnmatch.fnmatch(rel_str, f"*{dir_pattern}*"):
                        return True
                else:
                    # File pattern - match against filename or full path
                    if fnmatch.fnmatch(path.name, pattern):
                        return True
                    if fnmatch.fnmatch(rel_str, pattern):
                        return True
            
            return False
        except ValueError:
            # Path is not relative to project
            return True
    
    def _generate_snapshot_name(self, note: str = "") -> str:
        """Generate a snapshot folder name."""
        timestamp = datetime.now().strftime("%Y-%m-%d_%H%M")
        
        if note:
            # Sanitize the note for use in folder name
            safe_note = "".join(c if c.isalnum() or c in " -_" else "" for c in note)
            safe_note = safe_note.strip().replace(" ", "-")[:50]  # Max 50 chars
            return f"{timestamp}_{safe_note}"
        else:
            return timestamp
    
    def _calculate_dir_size(self, path: Path) -> tuple[int, int]:
        """Calculate total size and file count of a directory."""
        total_size = 0
        file_count = 0
        
        try:
            for item in path.rglob("*"):
                if item.is_file():
                    try:
                        total_size += item.stat().st_size
                        file_count += 1
                    except (OSError, PermissionError):
                        pass
        except (OSError, PermissionError):
            pass
        
        return total_size, file_count
    
    def _load_snapshot_metadata(self, snapshot_path: Path) -> Optional[dict]:
        """Load metadata from a snapshot's _snapshot.json file."""
        meta_file = snapshot_path / "_snapshot.json"
        if meta_file.exists():
            try:
                with open(meta_file) as f:
                    return json.load(f)
            except:
                pass
        return None
    
    def _save_snapshot_metadata(self, snapshot_path: Path, note: str, file_count: int, total_size: int) -> None:
        """Save metadata to a snapshot's _snapshot.json file."""
        meta = {
            "created": datetime.now().isoformat(),
            "note": note,
            "project_path": str(self.project_path),
            "file_count": file_count,
            "total_size": total_size
        }
        
        meta_file = snapshot_path / "_snapshot.json"
        with open(meta_file, "w") as f:
            json.dump(meta, f, indent=2)
    
    def create_snapshot(self, note: str = "", progress_callback: Optional[Callable[[str], None]] = None) -> SnapshotResult:
        """
        Create a new snapshot of the current project state.
        
        Args:
            note: Optional description for this snapshot
            progress_callback: Optional callback for progress updates
            
        Returns:
            SnapshotResult with success status and snapshot info
        """
        def report(msg: str):
            if progress_callback:
                progress_callback(msg)
        
        report("Preparing snapshot...")
        
        # Ensure snapshots directory exists
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate snapshot name
        snapshot_name = self._generate_snapshot_name(note)
        snapshot_path = self.snapshots_dir / snapshot_name
        
        # Check if we need to delete an old snapshot
        deleted_old = None
        existing = self.list_snapshots()
        if len(existing) >= self.snapshot_limit:
            # Delete oldest (last in list, since list is sorted newest first)
            oldest = existing[-1]
            try:
                shutil.rmtree(oldest.path)
                deleted_old = oldest.display_name
                report(f"Removed old snapshot: {deleted_old}")
            except Exception as e:
                return SnapshotResult(
                    success=False,
                    message=f"Couldn't remove old snapshot: {e}"
                )
        
        report("Copying files...")
        
        try:
            # Create the snapshot directory
            snapshot_path.mkdir(parents=True, exist_ok=True)
            
            # Copy all files that aren't ignored
            file_count = 0
            total_size = 0
            
            for item in self.project_path.rglob("*"):
                if self._should_ignore(item, self.project_path):
                    continue
                
                if item.is_file():
                    # Calculate relative path
                    rel_path = item.relative_to(self.project_path)
                    dest = snapshot_path / rel_path
                    
                    # Create parent directories
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy the file
                    try:
                        shutil.copy2(item, dest)
                        file_count += 1
                        total_size += item.stat().st_size
                    except (OSError, PermissionError) as e:
                        # Skip files we can't read, but continue
                        pass
            
            # Save metadata
            self._save_snapshot_metadata(snapshot_path, note, file_count, total_size)
            
            report("Snapshot complete!")
            
            snapshot = Snapshot(
                name=snapshot_name,
                path=snapshot_path,
                created=datetime.now(),
                note=note,
                file_count=file_count,
                total_size=total_size
            )
            
            return SnapshotResult(
                success=True,
                message=f"Saved snapshot with {file_count} files",
                snapshot=snapshot,
                deleted_old=deleted_old
            )
            
        except Exception as e:
            # Clean up failed snapshot
            if snapshot_path.exists():
                try:
                    shutil.rmtree(snapshot_path)
                except:
                    pass
            
            return SnapshotResult(
                success=False,
                message=f"Snapshot failed: {e}"
            )
    
    def list_snapshots(self) -> list[Snapshot]:
        """
        List all snapshots for this project.
        
        Returns list sorted by date (newest first).
        """
        snapshots = []
        
        if not self.snapshots_dir.exists():
            return snapshots
        
        for item in self.snapshots_dir.iterdir():
            if not item.is_dir():
                continue
            
            if item.name.startswith("_"):
                continue  # Skip special folders like _pre_restore backups
            
            # Try to load metadata
            meta = self._load_snapshot_metadata(item)
            
            if meta:
                try:
                    created = datetime.fromisoformat(meta["created"])
                except:
                    created = datetime.fromtimestamp(item.stat().st_mtime)
                
                note = meta.get("note", "")
                file_count = meta.get("file_count", 0)
                total_size = meta.get("total_size", 0)
            else:
                # No metadata - reconstruct from folder name and stats
                created = datetime.fromtimestamp(item.stat().st_mtime)
                
                # Try to parse note from folder name
                parts = item.name.split("_", 2)
                note = parts[2].replace("-", " ") if len(parts) > 2 else ""
                
                # Calculate size
                total_size, file_count = self._calculate_dir_size(item)
            
            snapshots.append(Snapshot(
                name=item.name,
                path=item,
                created=created,
                note=note,
                file_count=file_count,
                total_size=total_size
            ))
        
        # Sort by created date, newest first
        snapshots.sort(key=lambda s: s.created, reverse=True)
        
        return snapshots
    
    def restore_snapshot(self, snapshot: Snapshot, progress_callback: Optional[Callable[[str], None]] = None) -> SnapshotResult:
        """
        Restore project to a previous snapshot state.
        
        This:
        1. Creates a safety backup of current state
        2. Clears the working directory (except .tpc/)
        3. Copies snapshot contents back
        
        Args:
            snapshot: The snapshot to restore
            progress_callback: Optional callback for progress updates
            
        Returns:
            SnapshotResult with success status
        """
        def report(msg: str):
            if progress_callback:
                progress_callback(msg)
        
        if not snapshot.path.exists():
            return SnapshotResult(
                success=False,
                message="Snapshot no longer exists"
            )
        
        report("Creating safety backup...")
        
        # Create safety backup first
        safety_name = f"_pre_restore_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        safety_path = self.snapshots_dir / safety_name
        
        try:
            safety_path.mkdir(parents=True, exist_ok=True)
            
            # Copy current state to safety backup
            for item in self.project_path.rglob("*"):
                if self._should_ignore(item, self.project_path):
                    continue
                
                if item.is_file():
                    rel_path = item.relative_to(self.project_path)
                    dest = safety_path / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    try:
                        shutil.copy2(item, dest)
                    except:
                        pass
            
        except Exception as e:
            return SnapshotResult(
                success=False,
                message=f"Couldn't create safety backup: {e}"
            )
        
        report("Clearing current files...")
        
        try:
            # Delete current files (except .tpc/)
            for item in self.project_path.iterdir():
                if item.name == ".tpc":
                    continue  # Never delete the config folder
                
                if item.is_file():
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            
        except Exception as e:
            return SnapshotResult(
                success=False,
                message=f"Couldn't clear current files: {e}"
            )
        
        report("Restoring snapshot...")
        
        try:
            # Copy snapshot contents to project
            for item in snapshot.path.rglob("*"):
                if item.name == "_snapshot.json":
                    continue  # Don't copy metadata file
                
                if item.is_file():
                    rel_path = item.relative_to(snapshot.path)
                    dest = self.project_path / rel_path
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(item, dest)
            
            report("Restore complete!")
            
            return SnapshotResult(
                success=True,
                message=f"Restored to '{snapshot.display_name}'"
            )
            
        except Exception as e:
            # Try to restore from safety backup
            report("Restore failed, recovering from safety backup...")
            try:
                for item in safety_path.rglob("*"):
                    if item.is_file():
                        rel_path = item.relative_to(safety_path)
                        dest = self.project_path / rel_path
                        dest.parent.mkdir(parents=True, exist_ok=True)
                        shutil.copy2(item, dest)
            except:
                pass
            
            return SnapshotResult(
                success=False,
                message=f"Restore failed: {e}. Your files have been recovered."
            )
    
    def delete_snapshot(self, snapshot: Snapshot) -> SnapshotResult:
        """Delete a specific snapshot."""
        if not snapshot.path.exists():
            return SnapshotResult(
                success=False,
                message="Snapshot doesn't exist"
            )
        
        try:
            shutil.rmtree(snapshot.path)
            return SnapshotResult(
                success=True,
                message=f"Deleted '{snapshot.display_name}'"
            )
        except Exception as e:
            return SnapshotResult(
                success=False,
                message=f"Couldn't delete snapshot: {e}"
            )
    
    def cleanup_safety_backups(self, max_age_hours: int = 24) -> int:
        """
        Remove old safety backups (created during restore operations).
        
        Returns count of backups removed.
        """
        if not self.snapshots_dir.exists():
            return 0
        
        removed = 0
        cutoff = datetime.now().timestamp() - (max_age_hours * 3600)
        
        for item in self.snapshots_dir.iterdir():
            if item.is_dir() and item.name.startswith("_pre_restore_"):
                try:
                    if item.stat().st_mtime < cutoff:
                        shutil.rmtree(item)
                        removed += 1
                except:
                    pass
        
        return removed
    
    def get_snapshot_by_name(self, name: str) -> Optional[Snapshot]:
        """Find a snapshot by its folder name."""
        for snapshot in self.list_snapshots():
            if snapshot.name == name:
                return snapshot
        return None


# Convenience functions for use without instantiating the class

def create_project_snapshot(project_path: Path, note: str = "", snapshot_limit: int = 10) -> SnapshotResult:
    """Create a snapshot for a project."""
    manager = SnapshotManager(project_path, snapshot_limit)
    return manager.create_snapshot(note)


def list_project_snapshots(project_path: Path) -> list[Snapshot]:
    """List all snapshots for a project."""
    manager = SnapshotManager(project_path)
    return manager.list_snapshots()


def restore_project_snapshot(project_path: Path, snapshot_name: str) -> SnapshotResult:
    """Restore a project to a specific snapshot."""
    manager = SnapshotManager(project_path)
    snapshot = manager.get_snapshot_by_name(snapshot_name)
    if not snapshot:
        return SnapshotResult(success=False, message=f"Snapshot '{snapshot_name}' not found")
    return manager.restore_snapshot(snapshot)
