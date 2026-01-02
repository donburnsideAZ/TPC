"""
Configuration management for TPC 2.0.

Handles app-level settings stored in ~/.tpc/config.json.
Project-specific settings stay in each project's .tpc/project.json.

TPC 2.0: Cloud-first configuration with optional GitHub backup.
"""

import json
from pathlib import Path
from dataclasses import dataclass, field, asdict
from datetime import datetime
from typing import Optional


# Global config location
TPC_CONFIG_DIR = Path.home() / ".tpc"
TPC_CONFIG_FILE = TPC_CONFIG_DIR / "config.json"


@dataclass
class TPCConfig:
    """
    Application-wide TPC configuration.
    
    Stored in ~/.tpc/config.json
    """
    
    # Where projects live (the full path including "TPC Projects")
    projects_root: str = ""
    
    # Which cloud service (if any) - for display purposes
    cloud_service: Optional[str] = None
    
    # GitHub settings (optional backup)
    github_username: Optional[str] = None
    backup_reminder: str = "weekly"  # "never", "weekly", "daily"
    last_backup_reminder: Optional[str] = None  # ISO date
    
    # First run completed?
    setup_complete: bool = False
    
    # When config was last modified
    last_modified: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def save(self) -> bool:
        """Save config to disk."""
        try:
            TPC_CONFIG_DIR.mkdir(parents=True, exist_ok=True)
            
            self.last_modified = datetime.now().isoformat()
            
            # Convert to dict, handling None values
            data = {
                "projects_root": self.projects_root,
                "cloud_service": self.cloud_service,
                "github_username": self.github_username,
                "backup_reminder": self.backup_reminder,
                "last_backup_reminder": self.last_backup_reminder,
                "setup_complete": self.setup_complete,
                "last_modified": self.last_modified,
            }
            
            with open(TPC_CONFIG_FILE, "w") as f:
                json.dump(data, f, indent=2)
            
            return True
        except Exception as e:
            print(f"Failed to save config: {e}")
            return False
    
    @classmethod
    def load(cls) -> "TPCConfig":
        """Load config from disk, or return defaults if none exists."""
        if not TPC_CONFIG_FILE.exists():
            return cls()
        
        try:
            with open(TPC_CONFIG_FILE) as f:
                data = json.load(f)
            
            return cls(
                projects_root=data.get("projects_root", ""),
                cloud_service=data.get("cloud_service"),
                github_username=data.get("github_username"),
                backup_reminder=data.get("backup_reminder", "weekly"),
                last_backup_reminder=data.get("last_backup_reminder"),
                setup_complete=data.get("setup_complete", False),
                last_modified=data.get("last_modified", datetime.now().isoformat())
            )
        except Exception as e:
            print(f"Failed to load config: {e}")
            return cls()
    
    def get_projects_path(self) -> Path:
        """Get the projects root as a Path object."""
        if self.projects_root:
            return Path(self.projects_root).expanduser()
        else:
            # Fallback to legacy default
            return Path.home() / "Documents" / "TPC Projects"
    
    def is_first_run(self) -> bool:
        """Check if this is the first run (no config or setup not complete)."""
        return not self.setup_complete or not self.projects_root
    
    def should_show_backup_reminder(self) -> bool:
        """Check if we should show a backup reminder."""
        if self.backup_reminder == "never":
            return False
        
        if not self.last_backup_reminder:
            return True  # Never reminded before
        
        try:
            last_reminder = datetime.fromisoformat(self.last_backup_reminder)
            days_since = (datetime.now() - last_reminder).days
            
            if self.backup_reminder == "daily":
                return days_since >= 1
            elif self.backup_reminder == "weekly":
                return days_since >= 7
            
        except ValueError:
            return True
        
        return False
    
    def mark_backup_reminded(self):
        """Mark that we've shown a backup reminder."""
        self.last_backup_reminder = datetime.now().isoformat()
        self.save()


def get_config() -> TPCConfig:
    """Get the current TPC configuration."""
    return TPCConfig.load()


def save_config(config: TPCConfig) -> bool:
    """Save TPC configuration."""
    return config.save()


def is_first_run() -> bool:
    """Quick check if this is first run."""
    return get_config().is_first_run()


def complete_first_run(projects_path: Path, cloud_service: Optional[str] = None) -> TPCConfig:
    """
    Mark first run as complete and save initial config.
    
    Args:
        projects_path: Full path to TPC Projects folder
        cloud_service: Name of cloud service if applicable
    
    Returns:
        The saved config
    """
    config = TPCConfig(
        projects_root=str(projects_path),
        cloud_service=cloud_service,
        setup_complete=True
    )
    config.save()
    return config


def get_projects_root() -> Path:
    """Get the projects root directory."""
    return get_config().get_projects_path()


def update_projects_location(projects_path: Path, cloud_service: Optional[str] = None) -> bool:
    """
    Update the projects location.
    
    Called from Settings when user changes location.
    """
    config = get_config()
    config.projects_root = str(projects_path)
    config.cloud_service = cloud_service
    return config.save()


def get_config_dir() -> Path:
    """Get the TPC config directory (~/.tpc)."""
    return TPC_CONFIG_DIR
